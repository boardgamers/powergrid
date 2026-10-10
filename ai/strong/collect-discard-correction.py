"""Independently inspect trained tensors, model selection and exported behavior."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import numpy as np
import torch
from huggingface_hub import hf_hub_download
from model import policy_from_checkpoint
from discard_correction_data import load_rows, arrays, metrics

ROOT=Path(__file__).resolve().parents[2]
read=lambda p:json.loads(Path(p).read_text())
digest=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,d):Path(p).write_text(json.dumps(d,indent=2)+'\n')


def main():
    p=argparse.ArgumentParser(__doc__);p.add_argument('revision');p.add_argument('output',type=Path)
    p.add_argument('--data',type=Path,default=ROOT/'ai/runs/discard-training-labels-verified-v1');a=p.parse_args()
    assert re.fullmatch('[a-f0-9]{40}',a.revision)
    torch.set_num_threads(1)
    protocol_path=ROOT/'ai/strong/discard-correction-protocol-v1.json';protocol=read(protocol_path)
    source=read(ROOT/'ai/strong/discard-correction-source-v1.json')
    out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
    prefix='runs/discard-correction-v1'
    def fetch(name):
        assert not Path(name).is_absolute() and '..' not in Path(name).parts
        target=out/name;target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes(Path(hf_hub_download(protocol['repo'],prefix+'/'+name,revision=a.revision)).read_bytes())
        return target
    status=read(fetch('training-check.json'))
    for k,v in {'status':'complete','protocol_sha256':digest(protocol_path),'source_revision':source['revision'],
        'source_sha256':source['sha256'],'training_location':'HF Jobs','qualification_eligible':False}.items():assert status[k]==v,k
    assert set(status['runs'])=={str(s) for s in protocol['seeds']}
    for name,sha in status['artifacts'].items():assert digest(fetch(name))==sha,name
    for n,pin in protocol['data'].items():
        for name,sha in pin['sha256'].items():assert digest(a.data/f'{n}p'/name)==sha
    rows=load_rows(a.data,protocol)
    pin=protocol['parent'];parent_path=hf_hub_download(protocol['repo'],pin['path'],revision=pin['revision'])
    assert digest(parent_path)==pin['sha256']
    parent=torch.load(parent_path,map_location='cpu',weights_only=True)
    summaries={}
    for seed in protocol['seeds']:
        folder=out/str(seed);history=read(folder/'metrics.json');training=read(folder/'training.json')
        assert training==status['runs'][str(seed)] and training['seed']==seed
        assert training['training_device']=='cuda' and training['tf32'] is False and training['parent_tensors_identical']
        assert training['train_roots']==2527 and training['validation_roots']==834
        assert [r['epoch'] for r in history]==list(range(0,protocol['epochs']+1,protocol['evaluate_every']))
        for row in history:
            assert row['updates']==row['epoch']*10
            assert row['train']['roots']==2527 and row['validation']['roots']==834
        selected=min(history,key=lambda r:r['validation']['weighted_simulated_regret'])
        assert training['best_epoch']==selected['epoch'] and training['updates']==1200
        best=torch.load(folder/'best.pt',map_location='cpu',weights_only=True)
        latest=torch.load(folder/'latest.pt',map_location='cpu',weights_only=True)
        for name,cp in [('best',best),('latest',latest)]:
            for k,v in {'architecture':'multiplayer_discard_correction','feature_revision':protocol['feature_revision'],
                'state_dim':1216,'action_dim':100,'seed':seed,'parent_frozen':True,'training_device':'cuda',
                'protocol_sha256':digest(protocol_path),'parent':pin,'data':protocol['data'],'model_args':{'margin':protocol['margin']},
                'epoch':selected['epoch'] if name=='best' else protocol['epochs']}.items():assert cp[k]==v,(name,k)
            assert all(t.dtype==torch.float32 and torch.isfinite(t).all() for t in cp['state_dict'].values())
            assert all(torch.equal(cp['state_dict']['parent.'+k],v) for k,v in parent['state_dict'].items())
            policy_from_checkpoint(cp)
        derivative=torch.load(folder/'derivative/inference64.pt',map_location='cpu',weights_only=True)
        assert derivative['inference_only'] and derivative['inference_precision']=='float64'
        assert derivative['inference_transform']=='float64-exp-div-silu-v1'
        assert derivative['numerical_derivative']['source_checkpoint_sha256']==digest(folder/'best.pt')
        assert derivative['state_dict'].keys()==best['state_dict'].keys()
        assert all(torch.equal(t,best['state_dict'][k]) for k,t in derivative['state_dict'].items())
        net=policy_from_checkpoint(derivative).eval();recomputed={}
        for split in ['train','validation']:
            subset=[r for r in rows if r['split']==split];data=arrays(subset)
            with torch.inference_mode():
                scores=torch.cat([net.policy.head(torch.from_numpy(data['state'][i:i+256]).double(),
                    torch.from_numpy(data['actions'][i:i+256]).double()) for i in range(0,len(subset),256)]).numpy()
            result=metrics(scores,data,subset,protocol['margin']);recomputed[split]=result
            assert result['changed']==selected[split]['changed'], 'Export precision changes label choices'
            for metric in ['weighted_simulated_regret','weighted_simulated_gain']:
                assert abs(result[metric]-selected[split][metric])<=1e-7,(split,metric)
            assert result['by_players']==selected[split]['by_players']
        for label,command in {
            'parity':['check-export.py',str(folder/'derivative/inference64.pt'),str(folder/'derivative/inference64.onnx'),str(ROOT/'ai/runs/multiplayer-serving-fixtures.jsonl')],
            'scope-parity':['check-discard-correction.py',str(folder/'derivative/inference64.pt'),str(folder/'derivative/inference64.onnx'),str(ROOT/'ai/runs/multiplayer-serving-fixtures.jsonl'),'--data',str(a.data.resolve())],
            'serving':['benchmark-serving.py',str(folder/'derivative/inference64.onnx'),str(ROOT/'ai/runs/multiplayer-serving-fixtures.jsonl')]}.items():
            with (folder/('independent-'+label+'.log')).open('w') as log:
                subprocess.run([sys.executable,str(ROOT/'ai/strong'/command[0]),*command[1:],'--output',str(folder/('independent-'+label+'.json'))],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,check=True)
        parity,scope,serving=[read(folder/('independent-'+k+'.json')) for k in ['parity','scope-parity','serving']]
        assert parity['positions']==scope['positions']==serving['positions']==2553
        assert scope['labels_strict_parity']==3361 and parity['all_actions_match'] and serving['all_moves_legal']
        assert scope['unchanged_other_actions']==2544
        summaries[str(seed)]={'training':training,'selected_epoch':selected['epoch'],'recomputed':recomputed,
            'parity':parity,'scope':scope,'serving':serving,'parent_tensors_identical':True,
            'model_sha256':digest(folder/'derivative/inference64.onnx'),'best_checkpoint_sha256':digest(folder/'best.pt')}
        print({'seed':seed,'selected_epoch':selected['epoch'],'validation':recomputed['validation'],'verified':True},flush=True)
    summary={'revision':a.revision,'prefix':prefix,'source_revision':source['revision'],'protocol_sha256':digest(protocol_path),
        'seeds':summaries,'qualification_eligible':False,'scope':'Valid learned exports and conditional label fit only. Fresh complete-game comparisons and full strength gate still required.'}
    write(out/'verified.json',summary)


if __name__=='__main__':main()
