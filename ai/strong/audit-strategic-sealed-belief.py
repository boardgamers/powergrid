"""Read-only public sealed-bid belief diagnostic; no gradients or label changes."""
from collections import defaultdict
import gzip
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import numpy as np
from huggingface_hub import hf_hub_download

ROOT=Path(__file__).resolve().parents[2]
read=lambda p:json.loads(p.read_text())
digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
FROZEN=ROOT/'ai/runs/strategic-correction-source-v1'


def main():
    source=read(ROOT/'ai/strong/strategic-correction-source-v1.json')
    archive=Path(hf_hub_download('coyotte508/powergrid-ai-training-v1',source['archive'],repo_type='dataset',revision=source['revision']))
    assert digest(archive)==source['sha256']
    with tarfile.open(archive) as bundle:
        for member in bundle.getmembers():
            if member.isfile():assert digest(FROZEN/member.name)==hashlib.sha256(bundle.extractfile(member).read()).hexdigest()
    roots_pin=read(FROZEN/'ai/strong/strategic-teacher-training-roots-v1.json')
    roots_path=FROZEN/roots_pin['file'];assert digest(roots_path)==roots_pin['sha256']
    with gzip.open(roots_path,'rt') as f:roots=[r for r in map(json.loads,f) if r['sealed'] and r['decision']=='bid']
    assert len(roots)==320
    sys.path.insert(0,str(FROZEN/'ai'))
    from infer import Model
    pin=read(ROOT/'ai/strong/strategic-correction-screen-pins-v1/parent.json')
    model_path=Path(hf_hub_download(pin['repo'],pin['prefix']+'/inference64.onnx',revision=pin['revision']))
    assert digest(model_path)==pin['files']['inference64.onnx'];model=Model(model_path)
    out=ROOT/'ai/runs/strategic-sealed-belief-audit-v1';out.mkdir(exist_ok=False)
    env=os.environ.copy();env['POWERGRID_FROZEN_RUNTIME']=str(FROZEN)
    proc=subprocess.Popen(['node',str(ROOT/'ai/strong/audit-sealed-belief-worker.cjs')],env=env,
        stdin=subprocess.PIPE,stdout=subprocess.PIPE,text=True,bufsize=1)
    records=[];root_records=[]
    try:
        for root in roots:
            proc.stdin.write(json.dumps({**root['request'],'rootId':root['rootId']})+'\n');proc.stdin.flush()
            row=json.loads(proc.stdout.readline());assert 'error' not in row,row.get('error')
            x=row['original'];assert x['moves']==root['legal']
            assert model.predict(x['state'],x['actions'])[0]==root['model_proposal']
            root_records.append({'rootId':root['rootId'],'players':root['players'],'already_committed':row['already_committed']})
            for p in row['opponents']:
                x=p.pop('encoded');index,_=model.predict(x['state'],x['actions']);p['neural']=x['moves'][index]
                assert p['neural']['name'] in ['Pass','Bid']
                records.append({**{k:root[k] for k in ['rootId','players','split','variant','mode','deal']},**p})
    finally:
        proc.terminate();proc.wait(timeout=5);proc.stdin.close();proc.stdout.close()
    groups=defaultdict(list)
    for r in records:
        for name in ['all',str(r['players'])+'p',r['split'],r['variant']]:groups[name].append(r)
    stats={}
    for name,rows in groups.items():
        stats[name]={'opponent_prompts':len(rows),'roots':len({r['rootId'] for r in rows}),
            'uniform_mean_bid':float(np.mean([r['uniform_mean'] for r in rows])),
            'policies':{policy:{'mean_bid_including_pass':float(np.mean([0 if r[policy]['name']=='Pass' else r[policy]['data'] for r in rows])),
                'passes':sum(r[policy]['name']=='Pass' for r in rows),
                'passes_where_sampler_forces_positive_bid':sum(r[policy]['name']=='Pass' and r['sampled_nonzero'] for r in rows)}
                for policy in ['neural','economic']}}
    raw=out/'opponent-prompts.jsonl.gz'
    with gzip.open(raw,'wt') as f:
        for r in records:f.write(json.dumps(r)+'\n')
    report={'source':source,'root_pin':roots_pin['sha256'],'parent':pin,'roots':len(roots),
        'roots_with_committed_opponents':sum(r['already_committed']>0 for r in root_records),
        'opponent_prompts':len(records),'groups':stats,'roots_detail':root_records,
        'source_files':{p.relative_to(FROZEN).as_posix():digest(p) for p in [FROZEN/'engine/dist/src/analysis.js',FROZEN/'ai/strong/economics.cjs']},
        'audit_files':{p.relative_to(ROOT).as_posix():digest(p) for p in [Path(__file__),ROOT/'ai/strong/audit-sealed-belief-worker.cjs']},
        'raw_sha256':digest(raw),'public_replay_feature_parity':True,'hidden_data_mutation_invariance':True,
        'gradients':False,'qualification_eligible':False,
        'scope':'Hypothetical frozen-policy bids at reconstructed public prompts, not observed historical hidden bids. Economic tie breaking fixed at 0.5. Uniform mean is analytic. Post-hoc diagnostic, no causal claim or label replacement.'}
    for path in [out/'audit.json',ROOT/'ai/strong/strategic-sealed-belief-audit-v1.json']:path.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ['roots','roots_with_committed_opponents','opponent_prompts','groups']},indent=2))


if __name__=='__main__':main()
