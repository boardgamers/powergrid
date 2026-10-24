"""Collect every fixed public-world diagnostic shard before comparing policies."""
import argparse
import ast
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
import re

import numpy as np
from huggingface_hub import HfApi, hf_hub_download
from strategic_collection import ROOT,read,write,digest
from population_policy_verification import extract_verified

STRONG=ROOT/'ai/strong'
def load(name,file):
    spec=importlib.util.spec_from_file_location(name,STRONG/file)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
probe=load('reference_v2_probe','probe-reference-opponents-v2.py')
launcher=load('reference_v2_launcher','launch-reference-opponents-v2.py')
GUARDS=ROOT/'ai/runs/reference-opponent-launches-v2'
COLLECTED=ROOT/'ai/runs/reference-opponent-collected-v2'
COMPARISON=STRONG/'reference-opponent-comparison-v2.json'
_contract=None


def contract(refresh=False):
    global _contract
    if _contract is not None and not refresh:
        assert digest(probe.OUT/'protocol.json')==_contract[1]['protocol_sha256']
        return _contract
    p=read(probe.OUT/'protocol.json');probe.validate(p)
    descriptor=read(STRONG/'reference-opponent-pilot-evidence-v2.json')
    assert descriptor['protocol_sha256']==digest(probe.OUT/'protocol.json')
    assert descriptor['remote_archive_verified'] and descriptor['six_player_sealed_failure_repaired']
    n=descriptor['admission']['worlds_per_job']
    cases=[{'root':root,'begin':begin,'worlds':n,
            'case':f'reference-opponent-full-v2-root-{root}-worlds-{begin}-{begin+n}'}
           for begin in range(0,64,n) for root in [2,0,1,3,4,5,6]]
    assert len(cases)==descriptor['admission']['jobs']
    _contract=(p,descriptor,cases)
    return _contract


def identity(case):
    p,d,cases=contract();row=next(r for r in cases if r['case']==case)
    guard=read(GUARDS/(case+'.json'))
    assert guard['stage']=='launched' and all(guard[k]==row[k] for k in row)
    assert guard['protocol_sha256']==d['protocol_sha256']
    assert guard['pilot_evidence']=={k:d[k] for k in ('repo','revision','archive_path','archive_sha256')}
    assert guard['source']==read(STRONG/'population-hybrid-development-source-v1.json')
    return p,d,row,guard


def inspect(case):
    _,_,_,guard=identity(case)
    job=HfApi().inspect_job(job_id=guard['job_id'])
    return {'case':case,'job_id':guard['job_id'],'stage':job.status.stage,
            'checked_at':datetime.now(timezone.utc).isoformat()}


def verify_artifacts(case,artifacts,evidence):
    p,d,row,guard=identity(case)
    manifest=read(artifacts/'manifest.json')
    assert {str(f.relative_to(artifacts)) for f in artifacts.rglob('*') if f.is_file()}==set(manifest)|{'manifest.json'}
    assert all(digest(artifacts/name)==sha for name,sha in manifest.items())
    assert digest(artifacts/'manifest.json')==evidence['manifest_sha256']
    assert len(manifest)+1==evidence['archived_files']
    status=read(artifacts/'status.json');result=read(artifacts/'result.json')
    assert status['stage']=='complete' and all(status[k]==row[k] for k in row)
    assert status['original_protocol_sha256']==result['protocol_sha256']==d['protocol_sha256']
    assert status['model_sha256']==p['model_sha256']
    assert status['job_runner_sha256']==digest(STRONG/'reference-opponent-job-v2.py')
    assert status['source_revision']==guard['source']['revision'] and status['source_sha256']==guard['source']['sha256']
    assert status['evidence_revision']==d['revision'] and status['evidence_sha256']==d['archive_sha256']
    assert status['runtime_binding']=='/workspace'
    assert status['qualification_eligible'] is status['reserved_final_seeds_used'] is False
    assert result['root']==row['root'] and result['begin']==row['begin'] and result['count']==row['worlds']
    assert result['mode']=='reference_opponent_v1' and result['options']==p['roots'][row['root']]['options']
    checks=probe.verify_rows(p,row['root'],result['mode'],row['begin'],row['worlds'],result['rows'])
    assert checks==read(artifacts/'result.check.json')
    assert checks['rollouts']==status['rollouts']==2*row['worlds'] and checks['caps']==status['caps']==0
    prefix=row['begin']==0 and row['root'] in p['pilot_roots']
    assert status['pilot_prefix_exact'] is prefix
    if prefix:assert result['rows'][:4]==read(probe.OUT/f"pilot-{row['root']}.json")['rows']
    return checks


def verified(case):
    file=COLLECTED/case/'verified.json'
    if not file.exists():return None
    _,d,row,guard=identity(case);receipt=read(file)
    assert receipt['verified'] and receipt['stage']=='COMPLETED'
    assert receipt['case']==case and receipt['job_id']==guard['job_id']
    assert receipt['guard_sha256']==digest(GUARDS/(case+'.json'))
    assert receipt['protocol_sha256']==d['protocol_sha256']
    assert receipt['row']==row
    assert all(digest(ROOT/name)==sha for name,sha in receipt['code_hashes'].items())
    return receipt


def collect(case):
    old=verified(case)
    if old:return old
    p,d,row,guard=identity(case);status=inspect(case)
    assert status['stage']=='COMPLETED','Only complete jobs can supply diagnostic outcomes'
    out=COLLECTED/case;out.mkdir(parents=True,exist_ok=True)
    logs='\n'.join(str(line) for line in HfApi().fetch_job_logs(job_id=status['job_id']))
    (out/'job.log').write_text(logs)
    receipts=[]
    for line in logs.splitlines():
        if not line.startswith('{'):continue
        try:item=ast.literal_eval(line)
        except (ValueError,SyntaxError):continue
        if isinstance(item,dict) and item.get('status',{}).get('case')==case and 'evidence' in item:receipts.append(item)
    assert len(receipts)==1,'Missing/ambiguous job evidence; inspect the existing job, never resubmit'
    receipt=receipts[0];evidence=receipt['evidence']
    assert evidence['repo']=='coyotte508/powergrid-ai-germany-v1' and evidence['remote_archive_verified']
    assert evidence['archive_path']==f'archives/{case}.tgz' and re.fullmatch('[a-f0-9]{40}',evidence['revision'])
    archive=Path(hf_hub_download(evidence['repo'],evidence['archive_path'],revision=evidence['revision']))
    assert digest(archive)==evidence['archive_sha256']
    artifacts=out/'artifacts'
    if not artifacts.exists():extract_verified(archive,artifacts)
    checks=verify_artifacts(case,artifacts,evidence)
    assert receipt['status']==read(artifacts/'status.json')
    hashes={str(file.relative_to(ROOT)):digest(file) for file in [
        Path(__file__),Path(probe.__file__),STRONG/'population_policy_verification.py',STRONG/'reference-opponent-job-v2.py']}
    result={**status,'verified':True,'row':row,'guard_sha256':digest(GUARDS/(case+'.json')),
            'protocol_sha256':d['protocol_sha256'],'summary':checks,'evidence':evidence,'code_hashes':hashes,
            'qualification_eligible':False,'reserved_final_seeds_used':False}
    write(out/'verified.json',result);return result


def compare():
    p,d,cases=contract(refresh=True);all_rows={i:[] for i in range(7)};provenance={}
    assert {file.stem for file in GUARDS.glob('*.json')}=={r['case'] for r in cases}
    for row in cases:
        case=row['case'];receipt=verified(case);assert receipt is not None
        artifacts=COLLECTED/case/'artifacts'
        assert verify_artifacts(case,artifacts,receipt['evidence'])==receipt['summary']
        all_rows[row['root']].extend(read(artifacts/'result.json')['rows'])
        provenance[case]={'job_id':receipt['job_id'],'verified_sha256':digest(COLLECTED/case/'verified.json'),
                          'evidence':receipt['evidence']}
    comparisons=[]
    for i,rows in all_rows.items():
        root=p['roots'][i];baseline,selected=root['options'];old=read(probe.OLD/f'root-{i}-result.json')['search']
        rows.sort(key=lambda r:(r['sample'],root['options'].index(r['actionIndex'])))
        rows=[{**r,'env':index} for index,r in enumerate(rows)]
        checks=probe.verify_rows(p,i,'reference_opponent_v1',0,64,rows)
        values={action:np.array([r['value'] for r in rows if r['actionIndex']==action]) for action in root['options']}
        reference=values[selected]-values[baseline]
        mixture=np.array(old['sampleOutcomes'][str(selected)])-np.array(old['sampleOutcomes'][str(baseline)])
        heldout=np.stack([mixture[8:],reference[8:],reference[8:]-mixture[8:]],axis=1)
        blocks=heldout.reshape(14,4,3).mean(axis=1)
        rng=np.random.default_rng(12347);boot=blocks[rng.integers(14,size=(10000,14))].mean(axis=1)
        comparisons.append({'root':i,'label':root['label'],'opponent':root['opponent'],
            'baseline_index':baseline,'selected_index':selected,
            'fixed_selected_action':root['original_decision']['move'],'fixed_options':root['options'],
            'mixture_world_margins':mixture.tolist(),'reference_world_margins':reference.tolist(),
            'original_eight_world_means':{'mixture':float(mixture[:8].mean()),'reference':float(reference[:8].mean())},
            'heldout_56_world_means':dict(zip(['mixture','reference','reference_minus_mixture'],heldout.mean(axis=0).tolist())),
            'paired_block_bootstrap_95':{name:np.quantile(boot[:,j],[.025,.975]).tolist()
                for j,name in enumerate(['mixture','reference','reference_minus_mixture'])},
            'checks':checks})
    result={'complete':True,'roots':7,'reference_continuations':896,'protocol_sha256':d['protocol_sha256'],
            'pilot_evidence_revision':d['revision'],'comparisons':comparisons,'provenance':provenance,
            'primary':p['primary'],'uncertainty':p['uncertainty'],'limitations':p['limitations'],
            'gradients':False,'new_strength_games':0,'candidate_selected':False,
            'qualification_eligible':False,'reserved_final_seeds_used':False}
    if COMPARISON.exists():assert read(COMPARISON)==result
    else:write(COMPARISON,result)
    return {'complete':True,'roots':7,'reference_continuations':896,'comparison_sha256':digest(COMPARISON)}


if __name__=='__main__':
    parser=argparse.ArgumentParser(__doc__);parser.add_argument('operation',choices=['inspect','collect','compare'])
    parser.add_argument('case',nargs='?');args=parser.parse_args()
    result=compare() if args.operation=='compare' else globals()[args.operation](args.case)
    print(json.dumps({k:v for k,v in result.items() if k not in ('evidence','code_hashes')},indent=2))
