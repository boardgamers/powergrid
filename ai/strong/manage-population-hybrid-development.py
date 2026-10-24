"""Guarded submission/collection for the fixed 8,400-game hybrid screen."""
import argparse
import ast
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

from huggingface_hub import HfApi,get_token,hf_hub_download
from strategic_collection import ROOT,read,write,digest
from population_hybrid_development import PROTOCOL,SOURCE,PLAN,validate_plan,verify_job
from population_policy_verification import extract_verified

GUARDS=ROOT/'ai/runs/population-hybrid-development-launches-v1'
COLLECTED=ROOT/'ai/runs/population-hybrid-development-collected-v1'

BOOTSTRAP='''
set -euo pipefail
apt-get update -qq
apt-get install -y --no-install-recommends libstdc++6 libgomp1 ca-certificates >/dev/null
python -m pip install --quiet --timeout 120 --retries 5 huggingface_hub==2.0.0 onnxruntime==1.30.0 numpy==2.4.6
mkdir -p /workspace
python - <<'INNER'
import urllib.request,tarfile,os,hashlib
from pathlib import Path
from huggingface_hub import hf_hub_download
urllib.request.urlretrieve('https://nodejs.org/dist/v24.14.0/node-v24.14.0-linux-x64.tar.xz','/tmp/node.tar.xz')
with tarfile.open('/tmp/node.tar.xz') as bundle:bundle.extractall('/opt',filter='data')
path=hf_hub_download('coyotte508/powergrid-ai-training-v1',os.environ['SOURCE_ARCHIVE'],repo_type='dataset',revision=os.environ['SOURCE_REVISION'])
assert hashlib.sha256(Path(path).read_bytes()).hexdigest()==os.environ['SOURCE_SHA256']
with tarfile.open(path) as bundle:bundle.extractall('/workspace',filter='data')
INNER
export PATH=/opt/node-v24.14.0-linux-x64/bin:$PATH
cd /workspace
python -u ai/strong/population-hybrid-development-job.py "$ARM" "$PLAYERS" "$OPPONENT" "$START" "$END"
'''


def admission(case):
    plan=read(PLAN);protocol=read(PROTOCOL);source=read(SOURCE)
    validate_plan(plan,protocol)
    assert plan['source']==source and source['protocol_sha256']==plan['protocol_sha256']==digest(PROTOCOL)
    assert all(digest(ROOT/name)==sha for name,sha in source['overlays'].items())
    assert all(digest(ROOT/name)==sha for name,sha in plan['dependency_hashes'].items())
    rows=[row for row in plan['shards'] if row['case']==case];assert len(rows)==1
    assert plan['admission']['admitted'] and plan['admission']['timeout_hours']<=12
    return plan,source,rows[0]


def launch(case,execute=False):
    plan,source,row=admission(case)
    record={'case':case,'stage':'launch_intent','created_at':datetime.now(timezone.utc).isoformat(),
        'row':row,'source':source,'plan_sha256':digest(PLAN),'protocol_sha256':digest(PROTOCOL),
        'flavor':plan['admission']['flavor'],'timeout_hours':plan['admission']['timeout_hours'],
        'bootstrap_sha256':hashlib.sha256(BOOTSTRAP.encode()).hexdigest(),
        'qualification_eligible':False,'reserved_final_seeds_used':False}
    if not execute:return {**record,'execute':False}
    env=os.environ.copy();env['HF_TOKEN']=get_token() or env.get('HF_TOKEN') or '';assert env['HF_TOKEN']
    GUARDS.mkdir(exist_ok=True);guard=GUARDS/(case+'.json')
    with guard.open('x') as stream:json.dump(record,stream,indent=2)
    cmd=['hf','jobs','run','--detach','--flavor',record['flavor'],'--timeout',str(record['timeout_hours'])+'h',
        '--secrets','HF_TOKEN','--label','project=powergrid-ai','--label','stage=population-hybrid-development-v1','--label','case='+case]
    fields={'SOURCE_ARCHIVE':source['archive'],'SOURCE_REVISION':source['revision'],'SOURCE_SHA256':source['sha256'],
        'PROTOCOL_SHA256':digest(PROTOCOL),'ARM':row['arm'],'PLAYERS':str(row['players']),
        'OPPONENT':row['opponent'],'START':str(row['start']),'END':str(row['end']),'HF_HUB_DISABLE_PROGRESS_BARS':'1'}
    for key,value in fields.items():cmd+=['--env',key+'='+value]
    cmd+=['--','python:3.11-slim-bookworm','bash','-lc',BOOTSTRAP]
    try:
        run=subprocess.run(cmd,cwd=ROOT,env=env,capture_output=True,text=True,check=True)
        guard.with_suffix('.log').write_text(run.stdout+run.stderr)
        ids=set(re.findall(r'\b[a-f0-9]{24}\b',run.stdout));assert len(ids)==1,'Reconcile ambiguous submission; never repeat it automatically'
        record.update(stage='launched',job_id=ids.pop())
    except BaseException as error:
        record.update(stage='launch_unknown',error=type(error).__name__+': '+str(error));raise
    finally:write(guard,record)
    return record


def inspect(case):
    plan,source,row=admission(case);guard_path=GUARDS/(case+'.json');guard=read(guard_path)
    assert guard['stage']=='launched' and guard['plan_sha256']==digest(PLAN)
    assert guard['source']==source and guard['row']==row
    job=HfApi().inspect_job(job_id=guard['job_id'])
    return {'case':case,'job_id':guard['job_id'],'authoritative_status':job.status.stage,
        'checked_at':datetime.now(timezone.utc).isoformat(),'guard_sha256':digest(guard_path)}


def verified_receipt(case):
    """Validate saved collection identity before a resumed coordinator trusts it."""
    plan,source,row=admission(case)
    path=COLLECTED/case/'verified.json'
    if not path.exists():return None
    checked=read(path);guard=read(GUARDS/(case+'.json'))
    assert guard['stage']=='launched' and guard['plan_sha256']==digest(PLAN)
    assert guard['row']==row and guard['source']==source
    assert checked['verified'] is True and checked['authoritative_status']=='COMPLETED'
    assert checked['job_id']==guard['job_id'] and checked['guard_sha256']==digest(GUARDS/(case+'.json'))
    assert checked['row']==row and checked['source']==source and checked['plan_sha256']==digest(PLAN)
    assert checked['protocol_sha256']==digest(PROTOCOL)
    assert all(digest(ROOT/name)==sha for name,sha in checked['code_hashes'].items())
    assert checked['summary']['games']==row['games'] and checked['summary']['all_receipts_verified']
    # Full artifact/decision verification is repeated by the final comparator.
    return checked


def collect(case):
    plan,source,row=admission(case)
    hashes={str(p.relative_to(ROOT)):digest(p) for p in
        [Path(__file__),ROOT/'ai/strong/population_policy_verification.py',ROOT/'ai/strong/population_hybrid_development.py']}
    status=inspect(case);out=COLLECTED/case;out.mkdir(parents=True,exist_ok=True);write(out/'status.json',status)
    if status['authoritative_status'] not in ['COMPLETED','ERROR']:return status
    logs='\n'.join(str(r) for r in HfApi().fetch_job_logs(job_id=status['job_id']));(out/'job.log').write_text(logs)
    if status['authoritative_status']!='COMPLETED':return {**status,'failed':True}
    receipts=[]
    for line in logs.splitlines():
        if not line.startswith('{'):continue
        try:value=ast.literal_eval(line)
        except (ValueError,SyntaxError):continue
        if isinstance(value,dict) and value.get('case')==case and 'evidence' in value:receipts.append(value)
    assert len(receipts)==1,'Missing or ambiguous job evidence'
    receipt=receipts[0];evidence=receipt['evidence'];assert receipt['stage']=='complete'
    assert evidence['repo']=='coyotte508/powergrid-ai-germany-v1'
    assert evidence['archive_path']=='archives/'+case+'.tgz' and re.fullmatch('[a-f0-9]{40}',evidence['revision'])
    assert evidence['remote_archive_verified'] is True
    archive=Path(hf_hub_download(evidence['repo'],evidence['archive_path'],revision=evidence['revision']))
    assert digest(archive)==evidence['archive_sha256']
    artifacts=out/'artifacts'
    if not artifacts.exists():extract_verified(archive,artifacts)
    manifest=read(artifacts/'manifest.json')
    assert {str(p.relative_to(artifacts)) for p in artifacts.rglob('*') if p.is_file()}==set(manifest)|{'manifest.json'}
    assert all(digest(artifacts/name)==sha for name,sha in manifest.items())
    assert digest(artifacts/'manifest.json')==evidence['manifest_sha256'] and len(manifest)+1==evidence['archived_files']
    assert {k:v for k,v in receipt.items() if k!='evidence'}==read(artifacts/'development-check.json')
    summary=verify_job(artifacts,row,source,read(PROTOCOL))
    assert all(digest(ROOT/name)==sha for name,sha in hashes.items())
    checked={**status,'verified':True,'row':row,'source':source,'evidence':evidence,'summary':summary,
        'code_hashes':hashes,'plan_sha256':digest(PLAN),'protocol_sha256':digest(PROTOCOL),
        'qualification_eligible':False,'reserved_final_seeds_used':False}
    write(out/'verified.json',checked);return checked


if __name__=='__main__':
    parser=argparse.ArgumentParser(__doc__);parser.add_argument('operation',choices=['launch','inspect','collect']);parser.add_argument('case');parser.add_argument('--execute',action='store_true')
    args=parser.parse_args();result=launch(args.case,args.execute) if args.operation=='launch' else globals()[args.operation](args.case)
    print(json.dumps({k:v for k,v in result.items() if k in ['case','job_id','stage','authoritative_status','verified','failed','execute','summary']},indent=2))
