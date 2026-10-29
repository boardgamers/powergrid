"""HF GPU training for one fixed arm, retaining all four prescribed seeds."""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import time
import numpy as np
import torch
from model_nomination_discount_v1 import initialize,ARCHITECTURE
from model_policy_iteration import ensemble_advantages
from strategic_correction_targets import regression_loss


def digest(path):
    with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def read(path):return json.loads(Path(path).read_text())
def write(path,data):Path(path).write_text(json.dumps(data,indent=2,allow_nan=False)+'\n')


def metrics(scores,data,ids,all_legal,margin):
    scores=np.asarray(scores,np.float64);p=data['proposal_index'][ids];n=np.arange(len(ids))
    delta=scores-scores[n,p,None];allowed=data['mask'][ids] if all_legal else data['old_mask'][ids]
    choices=np.where(allowed,delta,-1e9).argmax(1)
    choices=np.where(delta[n,choices]>margin,choices,p)
    target=data['target'][ids];achieved=target[n,choices]
    best=np.where(data['mask'][ids],target,-1e9).max(1);changes=choices!=p
    nonparent=allowed&(np.arange(scores.shape[1])[None]!=p[:,None]);weights=data['precision'][ids]*nonparent
    loss=(((delta-target)**2*weights).sum(1)/np.maximum(weights.sum(1),1e-12)).mean()
    return {'roots':len(ids),'weighted_mse':float(loss),'mean_simulated_regret':float((best-achieved).mean()),
        'mean_simulated_advantage':float(achieved.mean()),'changes':int(changes.sum()),
        'negative_changes':int(((achieved<0)&changes).sum()),
        'half_a_advantage':float(data['target_a'][ids][n,choices].mean()),
        'half_b_advantage':float(data['target_b'][ids][n,choices].mean()),
        'scope':'Conditional sampled continuation targets, not full-game wins.'}


def main():
    parser=argparse.ArgumentParser(__doc__);parser.add_argument('--bundle',type=Path,required=True)
    parser.add_argument('--arm',required=True);parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--upload',action='store_true');a=parser.parse_args()
    assert os.environ.get('POWERGRID_HF_TRAINING')=='1' and torch.cuda.is_available(),'Gradients only on HF GPU Jobs'
    bundle=a.bundle.resolve();out=a.output.resolve();assert not out.exists()
    design=read(bundle/'design.json');report=read(bundle/'data/report.json')
    assert digest(bundle/'data/report.json')==design['data_report_sha256']
    assert digest(bundle/'parent.pt')==design['parent_sha256']
    assert all(digest(bundle/'data'/f)==sha for f,sha in report['files'].items())
    arm=next(r for r in design['arms'] if r['name']==a.arm)
    data=dict(np.load(bundle/'data/data.npz',allow_pickle=False));meta=read(bundle/'data/metadata.json')
    assert len(meta)==5770 and data['train'].sum()==4326
    assert np.array_equal(data['train'],[r['split']=='train' for r in meta])
    assert all(r['split']==('validation' if r['deal'] in (0,4,8,12) else 'train') for r in meta)
    parent=torch.load(bundle/'parent.pt',map_location='cpu',weights_only=True)
    torch.set_num_threads(4);torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False
    splits={'train':np.flatnonzero(data['train']),'validation':np.flatnonzero(~data['train'])}
    args={'discount_inputs':arm['discount_inputs'],'all_legal':arm['all_legal'],'heads':1,
          'margin':design['margin'],'disagreement_penalty':0.}
    net=initialize(parent,**args).cuda().eval();out.mkdir();start=time.monotonic()
    tensors={k:torch.from_numpy(data[k].astype(np.float32) if k in ('target','precision') else data[k]).cuda()
             for k in ('state','actions','mask','old_mask','proposal_index','target','precision')}
    t=tensors
    with torch.inference_mode():
        contexts=[];embeddings=[]
        for begin in range(0,len(meta),256):
            context,embedding=net.embeddings(t['state'][begin:begin+256],t['actions'][begin:begin+256])
            contexts.append(context);embeddings.append(embedding)
        # Clone outside inference mode below so constants may be saved for head backprop.
        context=torch.cat(contexts);embedding=torch.cat(embeddings)
    t['context']=context.clone();t['embedding']=embedding.clone()
    initial=copy.deepcopy(net.heads[0].state_dict());members=[];member_scores=[];history={}
    selection_mask=t['mask'] if arm['all_legal'] else t['old_mask']
    torch.cuda.reset_peak_memory_stats()
    for seed in design['seeds']:
        torch.manual_seed(seed);rng=np.random.default_rng(seed);net.heads[0].load_state_dict(initial)
        optimizer=torch.optim.AdamW(net.heads[0].parameters(),lr=design['learning_rate'],weight_decay=design['weight_decay'])
        best=float('inf');best_state=None;best_epoch=None;updates=0;records=[];seed_start=time.monotonic()
        for epoch in range(design['epochs']+1):
            if epoch:
                net.heads[0].train()
                order=rng.permutation(splits['train'])
                for begin in range(0,len(order),design['batch_size']):
                    ids=torch.as_tensor(order[begin:begin+design['batch_size']],device='cuda')
                    scores=net.score_heads(t['context'][ids],t['embedding'][ids],t['state'][ids],t['actions'][ids])[0]
                    loss=regression_loss(scores,t['target'][ids],t['precision'][ids],selection_mask[ids],t['proposal_index'][ids])
                    assert torch.isfinite(loss);optimizer.zero_grad(set_to_none=True);loss.backward()
                    norm=torch.nn.utils.clip_grad_norm_(net.heads[0].parameters(),design['max_grad_norm'])
                    assert torch.isfinite(norm);optimizer.step();updates+=1
            if epoch%design['evaluate_every']==0:
                net.heads[0].eval();pred=[]
                with torch.inference_mode():
                    for begin in range(0,len(meta),256):
                        sl=slice(begin,begin+256)
                        pred.append(net.score_heads(t['context'][sl],t['embedding'][sl],t['state'][sl],t['actions'][sl])[0].cpu().numpy())
                scores=np.concatenate(pred);row={'epoch':epoch,'updates':updates}
                for split,ids in splits.items():row[split]=metrics(scores[ids],data,ids,arm['all_legal'],design['margin'])
                key=row['validation']['mean_simulated_regret']
                if key<best:
                    best=key;best_epoch=epoch;best_state={k:v.detach().cpu().clone() for k,v in net.heads[0].state_dict().items()}
                records.append(row)
                print(json.dumps({'arm':a.arm,'seed':seed,'epoch':epoch,'validation':row['validation']}),flush=True)
        assert best_state is not None
        assert all(torch.equal(v.cpu(),parent['state_dict'][k]) for k,v in net.parent.state_dict().items())
        assert not any(p.requires_grad or p.grad is not None for p in net.parent.parameters())
        if not arm['discount_inputs']:
            assert not torch.count_nonzero(best_state['discount_state.weight']) and not torch.count_nonzero(best_state['nomination_price.weight'])
        torch.save({'head_state':best_state,'seed':seed,'epoch':best_epoch,'updates':updates,
                    'parent_sha256':design['parent_sha256'],'design_sha256':digest(bundle/'design.json')},out/f'head-{seed}.pt')
        net.heads[0].load_state_dict(best_state);pred=[]
        with torch.inference_mode():
            for begin in range(0,len(meta),256):
                sl=slice(begin,begin+256);pred.append(net.score_heads(t['context'][sl],t['embedding'][sl],t['state'][sl],t['actions'][sl])[0].cpu())
        member_scores.append(torch.cat(pred));members.append({'seed':seed,'best_epoch':best_epoch,'updates':updates,'seconds':time.monotonic()-seed_start})
        history[str(seed)]=records;write(out/'history.json',history)
    combined=initialize(parent,**{**args,'heads':4,'disagreement_penalty':design['ensemble_disagreement_penalty']})
    for head,seed in zip(combined.heads,design['seeds']):head.load_state_dict(torch.load(out/f'head-{seed}.pt',weights_only=True)['head_state'])
    cp={'architecture':ARCHITECTURE,'feature_revision':'4.4-auction-discount','state_dim':1218,'action_dim':103,
        'model_args':{**args,'heads':4,'disagreement_penalty':design['ensemble_disagreement_penalty']},
        'state_dict':combined.state_dict(),'seeds':design['seeds'],'members':members,
        'parent_sha256':design['parent_sha256'],'design_sha256':digest(bundle/'design.json'),
        'data_report_sha256':digest(bundle/'data/report.json'),'parent_frozen':True,'qualified':False}
    torch.save(cp,out/'ensemble.pt')
    ensemble=ensemble_advantages(torch.stack(member_scores),torch.from_numpy(data['proposal_index']),design['ensemble_disagreement_penalty']).numpy()
    measurements={split:metrics(ensemble[ids],data,ids,arm['all_legal'],design['margin']) for split,ids in splits.items()}
    result={'complete':True,'arm':arm,'members':members,'new_gradient_updates':sum(m['updates'] for m in members),
        'seconds':time.monotonic()-start,'gpu':torch.cuda.get_device_name(),'max_allocated_bytes':torch.cuda.max_memory_allocated(),
        'parent_tensors_identical':True,'metrics':measurements,'ensemble_sha256':digest(out/'ensemble.pt'),
        'design_sha256':digest(bundle/'design.json'),'data_report_sha256':digest(bundle/'data/report.json'),
        'training_location':'HF Jobs','training_device':'cuda','qualified':False,'reserved_final_seeds_used':False}
    write(out/'training.json',result);write(out/'manifest.json',{p.name:digest(p) for p in sorted(out.iterdir()) if p.is_file()})
    if a.upload:
        import sys;sys.path.insert(0,str(bundle/'transport'))
        from checkpoint_bucket_archives_v3 import upload_directory
        from huggingface_hub import HfApi
        receipt=upload_directory(out,bundle/'upload-ledgers',HfApi())
        print(json.dumps({'training_complete':True,'arm':a.arm,'bucket_evidence':receipt,'metrics':measurements}),flush=True)


if __name__=='__main__':main()
