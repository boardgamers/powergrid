"""Submit two bounded HF capture calibration jobs; never launch full collection."""
import argparse
from datetime import datetime, timezone
import fcntl
import hashlib
import json
from pathlib import Path

from huggingface_hub import HfApi, get_token
from strategic_collection import ROOT, read, write, digest

STRONG=ROOT/'ai/strong'
SOURCE=STRONG/'opponent-surrogate-source-v1.json'
PROTOCOL=STRONG/'opponent-surrogate-collection-protocol-v1.json'
PREFLIGHT=ROOT/'ai/runs/opponent-surrogate-source-preflight-v1.json'
LAYOUT=ROOT/'ai/runs/opponent-surrogate-source-prepared-v1/layout-check.json'
PLAN=STRONG/'opponent-surrogate-runtime-admission-v1.json'
GUARDS=ROOT/'ai/runs/opponent-surrogate-runtime-launches-v1'
BOOTSTRAP=r'''
set -euo pipefail
apt-get update -qq
apt-get install -y --no-install-recommends libstdc++6 libgomp1 ca-certificates >/dev/null
python -m pip install --quiet --timeout 120 --retries 5 huggingface_hub==2.0.0 onnxruntime==1.30.0 numpy==2.4.6
mkdir -p /workspace
python - <<'INNER'
import urllib.request,tarfile,os,hashlib,json
from pathlib import Path
from huggingface_hub import hf_hub_download
urllib.request.urlretrieve('https://nodejs.org/dist/v24.14.0/node-v24.14.0-linux-x64.tar.xz','/tmp/node.tar.xz')
with tarfile.open('/tmp/node.tar.xz') as bundle:bundle.extractall('/opt',filter='data')
file=hf_hub_download('coyotte508/powergrid-ai-training-v1',os.environ['SOURCE_ARCHIVE'],repo_type='dataset',revision=os.environ['SOURCE_REVISION'])
assert hashlib.sha256(Path(file).read_bytes()).hexdigest()==os.environ['SOURCE_SHA256']
with tarfile.open(file) as bundle:bundle.extractall('/workspace',filter='data')
root=Path('/workspace')
manifest=root/'opponent-surrogate-source-manifest.json'
assert hashlib.sha256(manifest.read_bytes()).hexdigest()==os.environ['SOURCE_MANIFEST_SHA256']
files=json.loads(manifest.read_text())
assert len(files)==int(os.environ['SOURCE_MANIFEST_FILES'])
assert all(hashlib.sha256((root/name).read_bytes()).hexdigest()==sha for name,sha in files.items())
INNER
export PATH=/opt/node-v24.14.0-linux-x64/bin:$PATH
cd /workspace
python -u ai/strong/opponent-surrogate-collection-job-v1.py "$PLAYERS" 0 1 --mode runtime
'''


def prerequisites():
    source,protocol,proof,layout=map(read,(SOURCE,PROTOCOL,PREFLIGHT,LAYOUT))
    assert source['remote_archive_verified'] and source['unchanged_base_files']==1463
    assert source['protocol_sha256']==digest(PROTOCOL) and source['preflight_sha256']==digest(PREFLIGHT)
    assert digest(ROOT/'ai/runs'/source['archive'])==source['sha256']
    assert all(digest(ROOT/name)==sha for name,sha in source['new_files'].items())
    assert all(digest(ROOT/name)==sha for name,sha in proof['tested_code_hashes'].items())
    assert proof['complete'] and proof['real_preflight_games']==proof['exact_twins']==8
    assert proof['caps']==0 and proof['contract_tests']==3 and proof['wrapper_boundary_tests']==2
    assert layout['source_sha256']==source['sha256'] and layout['package_imports_correct']
    assert layout['exact_policy_requests']==20
    assert protocol['initial_runtime']=={'players':[2,6],'deals':1,'games':32,'paired_executions':64,
                                        'outcomes_excluded_from_training_and_strength':True}
    return source,protocol


def prepare():
    source,protocol=prerequisites()
    capture=read(STRONG/'reference-opponent-capture-evidence-v1.json')
    assert capture['remote_archive_verified'] and capture['caps']==0
    worst=max(row['paired_probe_seconds'] for row in capture['cells'])
    # Fourfold local-time margin and three waves of eight paired 6p cases.
    estimate=900+4*3*worst
    assert estimate < 4*3600
    plan={'created_at':datetime.now(timezone.utc).isoformat(),'source_sha256':source['sha256'],
          'source_descriptor_sha256':digest(SOURCE),'protocol_sha256':digest(PROTOCOL),
          'preflight_sha256':digest(PREFLIGHT),'layout_check_sha256':digest(LAYOUT),
          'launcher_sha256':digest(__file__),'bootstrap_sha256':hashlib.sha256(BOOTSTRAP.encode()).hexdigest(),
          'players':[2,6],'jobs':2,'games':32,'paired_executions':64,'workers':8,
          'flavor':'cpu-upgrade','vcpus':8,'ram_gb':32,'timeout_hours':4,'max_concurrent':2,
          'local_worst_paired_case_seconds':worst,'estimated_calibration_seconds':estimate,
          'budget_scope':'Bounded calibration only. Local HX370 time is not an HF bound. Runtime jobs measure CPU, wall time, memory and output bytes before a full collection plan is admitted. No gradients or playing-strength estimates.',
          'collection_admitted':False,'automatic_retries':False,'gradients':False,
          'qualification_eligible':False,'reserved_final_seeds_used':False}
    with PLAN.open('x') as f: json.dump(plan,f,indent=2);f.write('\n')
    print({k:plan[k] for k in ('jobs','games','paired_executions','flavor','timeout_hours','collection_admitted')})


def launch(players,execute):
    assert type(players) is int and players in (2,6)
    source,_=prerequisites()
    plan=read(PLAN)
    assert plan['source_descriptor_sha256']==digest(SOURCE) and plan['protocol_sha256']==digest(PROTOCOL)
    assert plan['preflight_sha256']==digest(PREFLIGHT) and plan['layout_check_sha256']==digest(LAYOUT)
    assert plan['launcher_sha256']==digest(__file__) and plan['bootstrap_sha256']==hashlib.sha256(BOOTSTRAP.encode()).hexdigest()
    assert plan['players']==[2,6] and plan['jobs']==plan['max_concurrent']==2 and plan['collection_admitted'] is False
    case=f'opponent-surrogate-runtime-v1-{players}p-0-1'
    if not execute:
        print({'case':case,'admitted':True,'execute':False,'plan_sha256':digest(PLAN)})
        return
    token=get_token()
    assert token
    GUARDS.mkdir(exist_ok=True)
    with (GUARDS/'.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        guard=GUARDS/(case+'.json')
        if guard.exists():
            previous=read(guard)
            assert previous['stage']=='launched', 'Reconcile uncertain original submission; never resubmit'
            assert previous['plan_sha256']==digest(PLAN)
            job=HfApi().inspect_job(job_id=previous['job_id'])
            print({'case':case,'existing_job_id':previous['job_id'],'authoritative_status':job.status.stage})
            return
        active=0
        for path in GUARDS.glob('*.json'):
            old=read(path)
            assert old['stage']=='launched' and old['plan_sha256']==digest(PLAN)
            stage=HfApi().inspect_job(job_id=old['job_id']).status.stage
            assert stage in ('RUNNING','SCHEDULING','COMPLETED'), 'Inspect the original failed or uncertain job'
            active+=stage!='COMPLETED'
        assert active<2
        record={'case':case,'stage':'launch_intent','created_at':datetime.now(timezone.utc).isoformat(),
                'players':players,'plan_sha256':digest(PLAN),'source':source,'qualification_eligible':False}
        with guard.open('x') as f:json.dump(record,f,indent=2)
        try:
            env={'SOURCE_ARCHIVE':source['archive'],'SOURCE_REVISION':source['revision'],'SOURCE_SHA256':source['sha256'],
                 'SOURCE_MANIFEST_SHA256':source['manifest_sha256'],'SOURCE_MANIFEST_FILES':str(source['manifest_files']),
                 'PROTOCOL_SHA256':digest(PROTOCOL),'PLAYERS':str(players),'HF_HUB_DISABLE_PROGRESS_BARS':'1'}
            job=HfApi().run_job(image='python:3.11-slim-bookworm',command=['bash','-lc',BOOTSTRAP],
                flavor=plan['flavor'],timeout=f"{plan['timeout_hours']}h",name=case,
                secrets={'HF_TOKEN':token},env=env,
                labels={'project':'powergrid-ai','stage':'opponent-surrogate-runtime-v1','case':case})
            record.update(stage='launched',job_id=job.id)
        except BaseException as error:
            record.update(stage='launch_unknown',error=type(error).__name__+': '+str(error))
            raise
        finally:write(guard,record)
    print({'case':case,'job_id':record['job_id']},flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(__doc__)
    sub=p.add_subparsers(dest='command',required=True)
    sub.add_parser('prepare')
    cmd=sub.add_parser('launch');cmd.add_argument('players',type=int,choices=[2,6]);cmd.add_argument('--execute',action='store_true')
    a=p.parse_args()
    if a.command=='prepare':prepare()
    else:launch(a.players,a.execute)
