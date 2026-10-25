"""Verify immutable collection shards and index the complete split-preserving corpus."""
import argparse
import ast
from collections import Counter
from datetime import datetime,timezone
import importlib.util
import json
from pathlib import Path
import re

from huggingface_hub import HfApi,hf_hub_download
from strategic_collection import ROOT,read,write,digest
from population_policy_verification import extract_verified
from opponent_surrogate_verification_v1 import verify_artifacts

STRONG=ROOT/'ai/strong'
spec=importlib.util.spec_from_file_location('surrogate_collection_launcher',STRONG/'launch-opponent-surrogate-collection-v1.py')
launcher=importlib.util.module_from_spec(spec);spec.loader.exec_module(launcher)
COLLECTED=ROOT/'ai/runs/opponent-surrogate-collection-collected-v1'
INDEX=STRONG/'opponent-surrogate-collection-results-v1.json'
ACTIVE={'RUNNING','SCHEDULING'}
FAILED={'ERROR','FAILED','TIMEOUT','CANCELED','CANCELLED','DELETED'}


def code_hashes():
    return {**launcher.dependencies(),**{str(p.relative_to(ROOT)):digest(p) for p in
            [Path(__file__),STRONG/'opponent_surrogate_verification_v1.py',STRONG/'population_policy_verification.py']}}


def identity(case):
    plan,source,row=launcher.admission(case)
    path=launcher.GUARDS/(case+'.json');guard=read(path)
    assert guard['stage']=='launched' and guard['case']==case and guard['row']==row
    assert guard['source']==source and guard['admission']==plan['admission']
    assert guard['plan_sha256']==digest(launcher.PLAN) and guard['protocol_sha256']==digest(launcher.PROTOCOL)
    assert guard['qualification_eligible'] is False and re.fullmatch('[a-f0-9]{24}',guard['job_id'])
    return plan,source,row,path,guard


def inspect(case):
    _,_,_,path,guard=identity(case)
    job=HfApi().inspect_job(job_id=guard['job_id'])
    return {'case':case,'job_id':guard['job_id'],'authoritative_status':job.status.stage,
            'checked_at':datetime.now(timezone.utc).isoformat(),'guard_sha256':digest(path)}


def verify_review(artifacts,row,source,protocol,evidence):
    review=verify_artifacts(artifacts,protocol,source,row['players'],row['start'],row['end'],'collection',evidence)
    assert review['games']==row['games'] and review['twin_games']==row['twins'] and review['caps']==0
    assert review['split_games']=={row['split']:row['games']}
    assert review['training_eligible'] is (row['split']=='train')
    assert review['training_rows']==(review['teacher_rows'] if row['split']=='train' else 0)
    return review


def verified_receipt(case,full=False):
    path=COLLECTED/case/'verified.json'
    if not path.exists():return None
    plan,source,row,guard_path,guard=identity(case)
    value=read(path)
    assert value['verified'] is True and value['authoritative_status']=='COMPLETED'
    assert value['job_id']==guard['job_id'] and value['guard_sha256']==digest(guard_path)
    assert value['row']==row and value['source']==source and value['plan_sha256']==digest(launcher.PLAN)
    assert value['protocol_sha256']==digest(launcher.PROTOCOL) and value['code_hashes']==code_hashes()
    assert value['evidence']['remote_archive_verified'] is True and value['review']['complete']
    assert value['review']['games']==row['games'] and value['review']['caps']==0
    for key in ('gradients','qualification_eligible','reserved_final_seeds_used'):assert value[key] is False
    if full:
        assert verify_review(path.parent/'artifacts',row,source,read(launcher.PROTOCOL),value['evidence'])==value['review']
    return value


def collect(case):
    _,source,row,_,_=identity(case);hashes=code_hashes()
    status=inspect(case);folder=COLLECTED/case;folder.mkdir(parents=True,exist_ok=True)
    write(folder/'status.json',status)
    if status['authoritative_status']!='COMPLETED':return status
    log='\n'.join(str(line) for line in HfApi().fetch_job_logs(job_id=status['job_id'],follow=False))
    (folder/'job.log').write_text(log)
    receipts=[]
    for line in log.splitlines():
        if not line.startswith('{'):continue
        try:r=ast.literal_eval(line)
        except (ValueError,SyntaxError):continue
        if isinstance(r,dict) and isinstance(r.get('status'),dict) and r['status'].get('case')==case and 'evidence' in r:receipts.append(r)
    assert len(receipts)==1, 'Missing/ambiguous upload receipt; inspect original job, never resubmit'
    receipt=receipts[0];evidence=receipt['evidence']
    assert evidence['repo']=='coyotte508/powergrid-ai-germany-v1' and evidence['archive_path']==f'archives/{case}.tgz'
    assert re.fullmatch('[a-f0-9]{40}',evidence['revision']) and evidence['remote_archive_verified'] is True
    assert evidence['format']=='tar.gz'
    archive=Path(hf_hub_download(evidence['repo'],evidence['archive_path'],revision=evidence['revision']))
    assert digest(archive)==evidence['archive_sha256']
    artifacts=folder/'artifacts'
    if not artifacts.exists():extract_verified(archive,artifacts)
    assert read(artifacts/'job.json')==receipt['status']
    review=verify_review(artifacts,row,source,read(launcher.PROTOCOL),evidence)
    assert hashes==code_hashes()
    result={**status,'verified':True,'source':source,'row':row,'evidence':evidence,'review':review,
            'plan_sha256':digest(launcher.PLAN),'protocol_sha256':digest(launcher.PROTOCOL),'code_hashes':hashes,
            'gradients':False,'qualification_eligible':False,'reserved_final_seeds_used':False,
            'teacher_replay_scope':'Every raw record independently checked here; the frozen HF worker re-encodes all records and replays the first/last strategic calls in every game. Complete endpoint calibration also repeated those calls locally. Full-corpus teacher searches are not rerun a second time on the host.'}
    write(folder/'verified.json',result)
    return result


def index():
    plan,protocol=read(launcher.PLAN),read(launcher.PROTOCOL)
    launcher.validate_plan(plan,protocol)
    assert all((COLLECTED/r['case']/'verified.json').exists() for r in plan['shards']), 'Every fixed collection shard must verify first'
    hashes=code_hashes();cases={};splits=Counter();phase_rows=Counter();games=twins=rows=0
    identities=set();jobs=set()
    for shard in plan['shards']:
        value=verified_receipt(shard['case'],full=True)
        assert value['job_id'] not in jobs;jobs.add(value['job_id'])
        review=value['review'];games+=review['games'];twins+=review['twin_games'];rows+=review['teacher_rows']
        splits[shard['split']]+=review['games']
        for cell in review['cells']:
            key=(cell['players'],cell['deal'],cell['seat'],cell['rule']);assert key not in identities;identities.add(key)
            assert cell['split']==shard['split']
            for phase,count in cell['phase_rows'].items():
                phase_rows[f"{cell['split']}/{cell['players']}p/{cell['rule']}/{phase}"]+=count
        cases[shard['case']]={'row':shard,'job_id':value['job_id'],'verified_sha256':digest(COLLECTED/shard['case']/'verified.json'),
                              'evidence':value['evidence'],'teacher_rows':review['teacher_rows'],
                              'teacher_rollouts':review['teacher_rollouts'],'public_replays':review['public_replays'],
                              'runtime':review['runtime'],'raw_evidence_bytes':review['raw_evidence_bytes']}
    assert identities=={(n,d,s,r) for n in range(2,7) for d in range(32) for s in range(n) for r in range(4)}
    assert games==2560 and twins==640 and splits=={'train':1920,'validation':320,'test':320}
    assert hashes==code_hashes()
    result={'complete':True,'games':games,'twins':twins,'teacher_rows':rows,'split_games':dict(splits),
            'phase_rows':dict(phase_rows),'cases':cases,'source':plan['source'],'plan_sha256':digest(launcher.PLAN),
            'protocol_sha256':digest(launcher.PROTOCOL),'code_hashes':hashes,'gradients':False,
            'qualification_eligible':False,'reserved_final_seeds_used':False,
            'scope':'Complete public opponent-behaviour corpus. Whole-deal splits are fixed; test labels cannot select models. Every raw archive remains pinned at its immutable HF revision/hash. This is not evidence of playing-strength improvement.'}
    with INDEX.open('x') as f:json.dump(result,f,indent=2,allow_nan=False);f.write('\n')
    return {'complete':True,'games':games,'teacher_rows':rows,'index_sha256':digest(INDEX)}


if __name__=='__main__':
    p=argparse.ArgumentParser(__doc__);p.add_argument('operation',choices=['inspect','collect','index']);p.add_argument('case',nargs='?')
    a=p.parse_args();r=index() if a.operation=='index' else globals()[a.operation](a.case)
    print(json.dumps({k:v for k,v in r.items() if k in ('case','job_id','authoritative_status','verified','complete','games','teacher_rows','index_sha256')}))
