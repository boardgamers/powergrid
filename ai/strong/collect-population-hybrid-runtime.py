"""Collect the same guarded runtime jobs; no submission, cancellation or retry."""
import argparse
import ast
from datetime import datetime,timezone
import json
from pathlib import Path
import re

from huggingface_hub import HfApi,hf_hub_download
from strategic_collection import ROOT,read,write,digest
from population_policy_verification import extract_verified,verify_evaluation


def collect(players):
    code_hashes={str(path.relative_to(ROOT)):digest(path) for path in
        [Path(__file__),ROOT/'ai/strong/population_policy_verification.py']}
    case=f'population-hybrid-runtime-v2-{players}p'
    guard_path=ROOT/'ai/runs/population-hybrid-runtime-launches-v2'/(case+'.json')
    guard=read(guard_path);assert guard['stage']=='launched'
    protocol=read(ROOT/'ai/strong/population-hybrid-development-protocol-v1.json')
    assert digest(ROOT/'ai/strong/population-hybrid-development-protocol-v1.json')==guard['protocol_sha256']
    source=guard['source'];assert source==read(ROOT/'ai/strong/population-hybrid-source-v2.json')
    assert all(digest(ROOT/name)==sha for name,sha in source['overlays'].items())
    api=HfApi();job=api.inspect_job(job_id=guard['job_id'])
    status={'case':case,'job_id':guard['job_id'],'authoritative_status':job.status.stage,
        'checked_at':datetime.now(timezone.utc).isoformat(),'guard_sha256':digest(guard_path),
        'qualification_eligible':False,'reserved_final_seeds_used':False}
    base=ROOT/'ai/runs/population-hybrid-runtime-collected-v2'/case;base.mkdir(parents=True,exist_ok=True)
    write(base/'status.json',status)
    if job.status.stage not in ['COMPLETED','ERROR']:return status
    logs='\n'.join(str(row) for row in api.fetch_job_logs(job_id=guard['job_id']))
    (base/'job.log').write_text(logs)
    if job.status.stage!='COMPLETED':return {**status,'failed':True,'log_sha256':digest(base/'job.log')}
    receipts=[]
    for line in logs.splitlines():
        if not line.startswith("{'players':"):continue
        value=ast.literal_eval(line)
        if isinstance(value,dict) and 'evidence' in value:receipts.append(value)
    assert len(receipts)==1,'Missing or ambiguous terminal evidence receipt'
    receipt=receipts[0];evidence=receipt['evidence']
    assert evidence['repo']=='coyotte508/powergrid-ai-germany-v1'
    assert evidence['archive_path']=='archives/'+case+'.tgz'
    assert re.fullmatch('[a-f0-9]{40}',evidence['revision'])
    assert evidence['remote_archive_verified'] is True and evidence['format']=='tar.gz'
    archive=Path(hf_hub_download(evidence['repo'],evidence['archive_path'],revision=evidence['revision']))
    assert digest(archive)==evidence['archive_sha256']
    out=base/'artifacts'
    if not out.exists():extracted=extract_verified(archive,out)
    else:
        manifest=read(out/'manifest.json')
        assert {str(p.relative_to(out)) for p in out.rglob('*') if p.is_file()}==set(manifest)|{'manifest.json'}
        assert all(digest(out/name)==sha for name,sha in manifest.items())
        extracted={'files':len(manifest)+1,'archive_sha256':digest(archive),'manifest_sha256':digest(out/'manifest.json')}
    assert extracted['manifest_sha256']==evidence['manifest_sha256'] and extracted['files']==evidence['archived_files']
    check=read(out/'runtime-check.json');assert {k:v for k,v in receipt.items() if k!='evidence'}==check
    expected={'players':players,'stage':'complete','source_revision':source['revision'],
        'source_sha256':source['sha256'],'protocol_sha256':guard['protocol_sha256'],
        'model_pin':protocol['model_pin'],'arm':'combined','opponent':'search_geo','deals':1,
        'workers':8,'samples':8,'search_workers':1,'games':4*players,'game_caps':0,'rollout_caps':0,
        'qualification_eligible':False,'reserved_final_seeds_used':False}
    assert all(check[k]==v for k,v in expected.items())
    summary=verify_evaluation(out/'evaluation',{'players':players,'arm':'combined','opponent':'search_geo',
        'opponent_model':None,'opponent_sha256':None,'model_sha256':protocol['model_pin']['files']['inference64.onnx'],
        'seed':protocol['smoke_seed_template'].format(players=players),'start':0,'deals':1,
        'samples':8,'workers':8,'search_workers':1,'runtime':'/workspace',
        'output':'/workspace/ai/runs/'+case+'/evaluation'})
    assert check['evaluation_seconds']==summary['wall_seconds']
    assert check['decisions']==summary['counts']['decisions'] and check['rollouts']==summary['counts']['rollouts']
    assert all(digest(ROOT/name)==sha for name,sha in code_hashes.items()), 'Collector changed during verification'
    record={**status,'verified':True,'source':source,'evidence':evidence,'summary':summary,
        'runtime_check_sha256':digest(out/'runtime-check.json'),
        'verifier_sha256':code_hashes['ai/strong/population_policy_verification.py'],
        'collector_sha256':code_hashes['ai/strong/collect-population-hybrid-runtime.py'],'strength_eligible':False,
        'scope':'One paired endpoint runtime deal, excluded from strength comparisons. Every saved decision is checked; means, choices, pairing and terminal credits are recomputed. This is not an independent replay of every simulated trajectory.'}
    write(base/'verified.json',record)
    return record


if __name__=='__main__':
    parser=argparse.ArgumentParser(__doc__);parser.add_argument('players',type=int,choices=[2,6]);args=parser.parse_args()
    result=collect(args.players)
    print(json.dumps({k:v for k,v in result.items() if k in ['case','job_id','authoritative_status','verified','failed','summary']},indent=2))
