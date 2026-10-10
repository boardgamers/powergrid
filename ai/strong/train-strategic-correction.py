"""HF-only strategic correction training after the complete label manifest is frozen."""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import numpy as np
import torch
from huggingface_hub import HfApi, hf_hub_download
from model_strategic import StrategicPolicy, FEATURE_REVISION, STATE_DIM, ACTION_DIM
from strategic_correction_data import load, arrays, metrics
from strategic_correction_targets import regression_loss

ROOT = Path(__file__).resolve().parents[2]
def read(p): return json.loads(Path(p).read_text())
def write(p,x): Path(p).write_text(json.dumps(x,indent=2)+'\n')
def digest(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def train(seed, rows, parent, out, design, manifest_hash):
    torch.manual_seed(seed)
    np.random.seed(seed)
    net = StrategicPolicy(design['margin'],design['parent_margin']).cuda()
    net.parent.load_state_dict(parent['state_dict'])
    assert all(not p.requires_grad for p in net.parent.parameters())
    original = {k:v.clone() for k,v in parent['state_dict'].items()}
    split_rows = {s:[r for r in rows if r['split']==s] for s in ['train','validation']}
    assert len(split_rows['train'])==1440 and len(split_rows['validation'])==480
    data = {s:arrays(r) for s,r in split_rows.items()}
    tensors = {s:{k:torch.from_numpy(x).cuda() for k,x in d.items()} for s,d in data.items()}
    # Frozen embeddings can be cached. They are recomputed normally in exported inference.
    with torch.no_grad():
        for t in tensors.values():
            t['context'],t['action_embedding'] = net.embeddings(t['state'],t['actions'])
    optimizer = torch.optim.AdamW(net.head.parameters(),lr=design['learning_rate'],weight_decay=design['weight_decay'])
    rng = np.random.default_rng(seed)
    out.mkdir(exist_ok=False)
    best,best_epoch,best_state = float('inf'),None,None
    history,updates = [],0
    started = time.monotonic()
    torch.cuda.reset_peak_memory_stats()

    def save(name,epoch,state):
        assert all(torch.equal(net.parent.state_dict()[k].cpu(),v) for k,v in original.items())
        cp = {'state_dict':{'parent.'+k:v for k,v in original.items()} |
              {'head.'+k:v.detach().cpu().clone() for k,v in state.items()},
            'architecture':'multiplayer_strategic_correction',
            'model_args':{'margin':design['margin'],'parent_margin':design['parent_margin']},
            'feature_revision':FEATURE_REVISION,'state_dim':STATE_DIM,'action_dim':ACTION_DIM,
            'seed':seed,'epoch':epoch,'updates':updates,'parent':design['parent'],
            'design_sha256':digest(ROOT/'ai/strong/strategic-correction-design-v1.json'),
            'data_manifest_sha256':manifest_hash,'parent_frozen':True,'training_device':'cuda',
            'qualification_eligible':False}
        torch.save(cp,out/name)

    for epoch in range(design['epochs']+1):
        if epoch:
            net.head.train()
            t = tensors['train']
            order = rng.permutation(len(split_rows['train']))
            for begin in range(0,len(order),design['batch_size']):
                ids = torch.as_tensor(order[begin:begin+design['batch_size']],device='cuda')
                scores = net.head(t['context'][ids],t['action_embedding'][ids],t['state'][ids],t['actions'][ids])
                loss = regression_loss(scores,t['target'][ids],t['precision'][ids],t['mask'][ids],t['proposal_index'][ids])
                assert torch.isfinite(loss)
                optimizer.zero_grad(set_to_none=True)
                loss.backward()
                norm = torch.nn.utils.clip_grad_norm_(net.head.parameters(),design['max_grad_norm'])
                assert torch.isfinite(norm)
                optimizer.step()
                updates += 1
        if epoch % design['evaluate_every'] == 0:
            net.head.eval()
            result = {'epoch':epoch,'updates':updates,'seconds':time.monotonic()-started}
            with torch.inference_mode():
                for split,t in tensors.items():
                    scores = net.head(t['context'],t['action_embedding'],t['state'],t['actions']).cpu().numpy()
                    result[split] = metrics(scores,data[split],split_rows[split],design['margin'])
            key = result['validation']['mean_simulated_regret']
            if key < best:
                best,best_epoch,best_state = key,epoch,copy.deepcopy(net.head.state_dict())
                save('best.pt',epoch,best_state)
            history.append(result)
            write(out/'metrics.json',history)
            print({'seed':seed,'epoch':epoch,'best_epoch':best_epoch,'validation':result['validation']},flush=True)
    save('latest.pt',design['epochs'],net.head.state_dict())
    torch.save(optimizer.state_dict(),out/'optimizer.pt')
    report = {'seed':seed,'best_epoch':best_epoch,'updates':updates,'seconds':time.monotonic()-started,
        'gpu':torch.cuda.get_device_name(),'max_allocated_bytes':torch.cuda.max_memory_allocated(),
        'head_parameters':sum(p.numel() for p in net.head.parameters()),'parent_tensors_identical':True,
        'train_roots':1440,'validation_roots':480,'training_location':'HF Jobs','qualification_eligible':False}
    write(out/'training.json',report)
    return report


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('manifest',type=Path)
    parser.add_argument('output',type=Path)
    parser.add_argument('--upload',action='store_true')
    args = parser.parse_args()
    assert os.environ.get('POWERGRID_HF_TRAINING')=='1','Run gradients on HF Jobs only'
    assert os.environ.get('SOURCE_REVISION') and os.environ.get('SOURCE_SHA256') and torch.cuda.is_available()
    torch.set_num_threads(4)
    torch.backends.cuda.matmul.allow_tf32=False
    torch.backends.cudnn.allow_tf32=False
    design_path=ROOT/'ai/strong/strategic-correction-design-v1.json'
    design,manifest=read(design_path),read(args.manifest)
    # A source build must pin these hashes before any job is admitted.
    assert os.environ['DESIGN_SHA256']==digest(design_path)
    assert os.environ['DATA_MANIFEST_SHA256']==digest(args.manifest)
    source={'revision':os.environ['SOURCE_REVISION'],'sha256':os.environ['SOURCE_SHA256']}
    out=args.output.resolve()
    out.mkdir(parents=True,exist_ok=False)
    status={'status':'running','source_revision':source['revision'],'source_sha256':source['sha256'],
        'design_sha256':digest(design_path),'manifest_sha256':digest(args.manifest),
        'training_location':'HF Jobs','qualification_eligible':False}
    try:
        rows=load(manifest,design)
        pin=design['parent']
        parent_path=Path(hf_hub_download(pin['repo'],pin['path'],revision=pin['revision']))
        assert digest(parent_path)==pin['sha256']
        parent=torch.load(parent_path,map_location='cpu',weights_only=True)
        assert parent['architecture']==pin['architecture'] and parent['seed']==pin['seed'] and parent['epoch']==pin['epoch']
        assert not parent.get('inference_only',False)
        write(out/'data-summary.json',{'roots':len(rows),'split_counts':{'train':1440,'validation':480},
            'root_ids':[r['rootId'] for r in rows],'manifest_sha256':digest(args.manifest)})
        reports={}
        for seed in design['seeds']:
            directory=out/str(seed)
            reports[str(seed)]=train(seed,rows,parent,directory,design,digest(args.manifest))
            fixtures=ROOT/'ai/strong/fixtures/multiplayer-serving-v1.jsonl'
            for script,arguments in [
                ('export-inference64.py',[directory/'best.pt',directory/'derivative']),
                ('check-export.py',[directory/'derivative/inference64.pt',directory/'derivative/inference64.onnx',fixtures,'--output',directory/'parity.json']),
                ('benchmark-serving.py',[directory/'derivative/inference64.onnx',fixtures,'--output',directory/'serving.json'])]:
                with (directory/(script+'.log')).open('w') as f:
                    subprocess.run([sys.executable,str(ROOT/'ai/strong'/script),*map(str,arguments)],cwd=ROOT,stdout=f,stderr=subprocess.STDOUT,check=True)
            parity,serving=read(directory/'parity.json'),read(directory/'serving.json')
            assert parity['positions']==serving['positions']==2553 and parity['all_actions_match'] and serving['all_moves_legal']
        status.update(status='complete',runs=reports)
    except BaseException as error:
        status.update(status='failed',error=type(error).__name__+': '+str(error))
        raise
    finally:
        status['artifacts']={str(p.relative_to(out)):digest(p) for p in out.rglob('*') if p.is_file()}
        write(out/'training-check.json',status)
        if args.upload:
            HfApi().upload_folder(repo_id=design['parent']['repo'],folder_path=out,path_in_repo='runs/strategic-correction-v1')
        print(status,flush=True)


if __name__=='__main__':
    main()
