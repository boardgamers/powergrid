"""HF-only gradient training of a small discard head; unchanged parent tensors."""
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
from model_discard import DiscardPolicy, FEATURE_REVISION, STATE_DIM, ACTION_DIM
from discard_correction_data import load_rows, arrays, metrics

ROOT = Path(__file__).resolve().parents[2]
def read(p): return json.loads(Path(p).read_text())
def write(p, x): Path(p).write_text(json.dumps(x, indent=2) + '\n')
def digest(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def prepare(out, protocol):
    for n in range(2, 7):
        target = out / 'data' / f'{n}p'
        subprocess.run([sys.executable, str(ROOT / 'ai/strong/verify-discard-training-labels.py'),
            str(n), protocol['data'][str(n)]['revision'], str(target)], cwd=ROOT, check=True)
    return load_rows(out / 'data', protocol)


def train(seed, all_rows, parent, out, protocol):
    torch.manual_seed(seed); np.random.seed(seed)
    net = DiscardPolicy(protocol['margin']).cuda()
    net.parent.load_state_dict(parent['state_dict'])
    assert all(not p.requires_grad for p in net.parent.parameters())
    original = {k: v.clone() for k, v in parent['state_dict'].items()}
    rows = {s: [r for r in all_rows if r['split'] == s] for s in ['train', 'validation']}
    data = {s: arrays(rows[s]) for s in rows}
    tensors = {s: {k: torch.from_numpy(v).cuda() for k, v in d.items()} for s, d in data.items()}
    optimizer = torch.optim.AdamW(net.head.parameters(), lr=protocol['learning_rate'], weight_decay=protocol['weight_decay'])
    history, best, best_state, best_epoch = [], float('inf'), None, None
    out.mkdir(exist_ok=False)
    start = time.monotonic(); updates = 0
    torch.cuda.reset_peak_memory_stats()
    rng = np.random.default_rng(seed)

    @torch.inference_mode()
    def evaluate(epoch):
        net.eval()
        result = {'epoch': epoch, 'updates': updates, 'seconds': time.monotonic() - start}
        for split in rows:
            t = tensors[split]
            q = torch.cat([net.head(t['state'][i:i+512], t['actions'][i:i+512]) for i in range(0, len(rows[split]), 512)]).cpu().numpy()
            result[split] = metrics(q, data[split], rows[split], protocol['margin'])
        return result

    def save(name, epoch, state):
        assert all(torch.equal(net.parent.state_dict()[k].cpu(), v) for k, v in original.items()), 'Frozen parent drift'
        cp = {'state_dict': {'parent.' + k: v for k, v in original.items()} |
              {'head.' + k: v.clone().cpu() for k, v in state.items()},
              'architecture': 'multiplayer_discard_correction', 'model_args': {'margin': protocol['margin']},
              'feature_revision': FEATURE_REVISION, 'state_dim': STATE_DIM, 'action_dim': ACTION_DIM,
              'seed': seed, 'epoch': epoch, 'training_device': 'cuda',
              'protocol_sha256': digest(ROOT / 'ai/strong/discard-correction-protocol-v1.json'),
              'parent': protocol['parent'], 'data': protocol['data'], 'parent_frozen': True,
              'qualification_eligible': False}
        torch.save(cp, out / name)

    for epoch in range(protocol['epochs'] + 1):
        if epoch:
            net.head.train()
            d = tensors['train']; size = len(rows['train'])
            for begin in range(0, size, protocol['batch_size']):
                if begin == 0: order = rng.permutation(size)
                ids = torch.as_tensor(order[begin:begin+protocol['batch_size']], device='cuda')
                q, m = net.head(d['state'][ids], d['actions'][ids]), d['mask'][ids]
                target = d['target'][ids]
                q = q - (q * m).sum(1, keepdim=True) / m.sum(1, keepdim=True)
                target = target - (target * m).sum(1, keepdim=True) / m.sum(1, keepdim=True)
                errors = (((q - target) ** 2) * m).sum(1) / m.sum(1)
                loss = (errors * d['weights'][ids]).sum() * size / len(ids)
                assert torch.isfinite(loss)
                optimizer.zero_grad(set_to_none=True); loss.backward()
                grad = torch.nn.utils.clip_grad_norm_(net.head.parameters(), protocol['max_grad_norm'])
                assert torch.isfinite(grad)
                optimizer.step(); updates += 1
        if epoch % protocol['evaluate_every'] == 0:
            result = evaluate(epoch); history.append(result)
            key = result['validation']['weighted_simulated_regret']
            if key < best:
                best, best_epoch = key, epoch
                best_state = copy.deepcopy(net.head.state_dict())
                save('best.pt', epoch, best_state)
            write(out / 'metrics.json', history)
            print({'seed': seed, 'epoch': epoch, 'validation': result['validation'], 'best_epoch': best_epoch}, flush=True)
    save('latest.pt', protocol['epochs'], net.head.state_dict())
    torch.save(optimizer.state_dict(), out / 'optimizer.pt')
    torch.cuda.synchronize()
    report = {'seed': seed, 'best_epoch': best_epoch, 'updates': updates, 'seconds': time.monotonic()-start,
        'train_roots': len(rows['train']), 'validation_roots': len(rows['validation']),
        'gpu': torch.cuda.get_device_name(), 'max_allocated_bytes': torch.cuda.max_memory_allocated(),
        'head_parameters': sum(p.numel() for p in net.head.parameters()), 'parent_tensors_identical': True,
        'training_device': 'cuda', 'tf32': False, 'qualification_eligible': False}
    write(out / 'training.json', report)
    return report


def main():
    p=argparse.ArgumentParser(__doc__);p.add_argument('output', type=Path);p.add_argument('--upload',action='store_true');a=p.parse_args()
    assert os.environ.get('POWERGRID_HF_TRAINING') == '1', 'Run gradients on HF Jobs only'
    assert os.environ.get('SOURCE_REVISION') and os.environ.get('SOURCE_SHA256') and torch.cuda.is_available()
    torch.set_num_threads(4);torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False
    protocol_path=ROOT/'ai/strong/discard-correction-protocol-v1.json';protocol=read(protocol_path)
    out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
    status={'status':'running','protocol_sha256':digest(protocol_path),'source_revision':os.environ['SOURCE_REVISION'],
        'source_sha256':os.environ['SOURCE_SHA256'],'qualification_eligible':False,'training_location':'HF Jobs'}
    try:
        rows=prepare(out,protocol)
        pin=protocol['parent'];path=hf_hub_download(protocol['repo'],pin['path'],revision=pin['revision'])
        assert digest(path)==pin['sha256']
        parent=torch.load(path,map_location='cpu',weights_only=True)
        assert parent['architecture']==pin['architecture'] and parent['update']==pin['update']
        assert parent.get('inference_only',False) is False
        reports={}
        for seed in protocol['seeds']:
            directory=out/str(seed)
            reports[str(seed)]=train(seed,rows,parent,directory,protocol)
            for filename, args in [('export-inference64.py',[str(directory/'best.pt'),str(directory/'derivative')]),
                ('check-export.py',[str(directory/'derivative/inference64.pt'),str(directory/'derivative/inference64.onnx'),str(ROOT/'ai/strong/fixtures/multiplayer-serving-v1.jsonl'),'--output',str(directory/'parity.json')]),
                ('check-discard-correction.py',[str(directory/'derivative/inference64.pt'),str(directory/'derivative/inference64.onnx'),str(ROOT/'ai/strong/fixtures/multiplayer-serving-v1.jsonl'),'--data',str(out/'data'),'--output',str(directory/'scope-parity.json')]),
                ('benchmark-serving.py',[str(directory/'derivative/inference64.onnx'),str(ROOT/'ai/strong/fixtures/multiplayer-serving-v1.jsonl'),'--output',str(directory/'serving.json')])]:
                with (directory/(filename+'.log')).open('w') as log:
                    subprocess.run([sys.executable,str(ROOT/'ai/strong'/filename),*args],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,check=True)
            parity,serving=read(directory/'parity.json'),read(directory/'serving.json')
            assert parity['positions']==serving['positions']==2553
            assert parity['all_actions_match'] and serving['all_moves_legal']
        status.update(status='complete',runs=reports)
    except BaseException as error:
        status.update(status='failed',error=type(error).__name__+': '+str(error));raise
    finally:
        status['artifacts']={str(f.relative_to(out)):digest(f) for f in out.rglob('*') if f.is_file() and 'data' not in f.relative_to(out).parts}
        write(out/'training-check.json',status)
        if a.upload:
            HfApi().upload_folder(repo_id=protocol['repo'],folder_path=out,path_in_repo='runs/discard-correction-v1',ignore_patterns=['data/**'])
        print(status,flush=True)


if __name__=='__main__':main()
