"""Single-attempt HF runtime pilots; exact source guards and independent collection.

Never selects a policy, submits a development grid, retries or replaces a job.
"""
import argparse
from datetime import datetime,timezone
import fcntl
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tarfile

from huggingface_hub import HfApi,get_token,hf_hub_download
from public_policy_development_job_v1 import digest,read,write
from population_policy_verification import extract_verified
from conservative_auction_bootstrap_recovery_v1 import cached_bootstrap

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'ai/runs/resource-turn-runtime-hf-v1'
SOURCE=ROOT/'ai/strong/resource-turn-runtime-source-v1.json'
RESULT=ROOT/'ai/strong/resource-turn-runtime-results-v1.json'
ARCHIVE=ROOT/'ai/runs/strong-source-resource-turn-runtime-v1.tgz'
REPO='coyotte508/powergrid-ai-training-v1'
CACHE=ROOT/'ai/strong/node-runtime-cache-v1.json'
TEST=ROOT/'ai/runs/resource-turn-runtime-tests-v1.json'


def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);value=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value);return value


preflight=module('resource_runtime_preflight',Path(__file__).with_name('prepare-resource-turn-runtime-v1.py'))
original=module('original_runtime_bootstrap',Path(__file__).with_name('manage-public-policy-development-hf-v1.py'))
BOOTSTRAP=cached_bootstrap(original.BOOTSTRAP.split('python -u -B /workspace/source/public_policy_development_job_v1.py')[0]+r'''
python -u -B /workspace/source/resource_turn_runtime_job_v1.py \
  --source /workspace/source --manifest-sha256 "$SOURCE_MANIFEST_SHA256" \
  --job "$PILOT_JOB" --output "/workspace/output/$PILOT_NAME" \
  --source-revision "$SOURCE_REVISION" --source-archive-sha256 "$SOURCE_SHA256" --execute --upload
''',read(CACHE))


def now():return datetime.now(timezone.utc).isoformat()


def save(path,value):
    with Path(path).open('x') as stream:json.dump(value,stream,indent=2,allow_nan=False);stream.write('\n')


def prerequisites():
    prep=preflight.pinned();proof=read(preflight.OUT/'verified.json')
    assert proof['passed'] and proof['jobs_dry_validated']==7 and proof['recorded_games_replayed']==8
    assert proof['exact_decisions']==1360 and proof['source_manifest_sha256']==prep['source_manifest_sha256']
    assert proof['prepared_sha256']==digest(preflight.OUT/'prepared.json')
    assert proof['control_manifest_sha256']==digest(preflight.OUT/'local-control/manifest.json')
    assert proof['control_status_sha256']==digest(preflight.OUT/'local-control/status.json')
    return prep,read(preflight.PROTOCOL)


def prepare():
    prep,protocol=prerequisites()
    assert not OUT.exists() and not ARCHIVE.exists() and not SOURCE.exists(),'Inspect existing preparation/source before retrying'
    OUT.mkdir();root=preflight.OUT/'source';pins=read(root/'source-manifest.json')
    with tarfile.open(ARCHIVE,'w:gz') as bundle:
        for name in sorted(set(pins)|{'source-manifest.json'}):
            path=root/name;assert path.is_file() and not path.is_symlink()
            info=bundle.gettarinfo(path,arcname=name);info.uid=info.gid=info.mtime=0;info.uname=info.gname=''
            with path.open('rb') as stream:bundle.addfile(info,stream)
    rows=[{'file':name,'job':job,'job_spec_sha256':digest(root/name)}
        for name,job in protocol['jobs'].items() if not job['control']]
    assert len(rows)==6 and sum(r['job']['games'] for r in rows)==96
    p={'created_at':now(),'archive':ARCHIVE.name,'sha256':digest(ARCHIVE),'bytes':ARCHIVE.stat().st_size,
        'source_manifest_sha256':prep['source_manifest_sha256'],'source_files':prep['source_files'],
        'protocol_sha256':prep['protocol_sha256'],'entry_sha256':prep['entry_sha256'],
        'artifact_descriptor_sha256':prep['artifact_descriptor_sha256'],'artifact_manifest_sha256':prep['artifact_manifest_sha256'],
        'preparation_sha256':digest(preflight.OUT/'prepared.json'),'preflight_sha256':digest(preflight.OUT/'verified.json'),
        'launcher_sha256':digest(__file__),'bootstrap_sha256':hashlib.sha256(BOOTSTRAP.encode()).hexdigest(),
        'node_cache_descriptor_sha256':digest(CACHE),'node_cache':read(CACHE),
        'rows':rows,'flavor':protocol['flavor'],'timeout':protocol['timeout'],'max_concurrent_jobs':6,
        'resource_estimate':protocol['resource_estimate'],'games':96,
        'scope':'runtime-only','automatic_retries':False,'new_strength_games':0,
        'qualification_eligible':False,'reserved_final_seeds_used':False}
    save(OUT/'prepared.json',p)
    return {'prepared':True,'jobs':6,'games':96,'timeout':p['timeout'],'archive_sha256':p['sha256']}


def prepared():
    prerequisites();p=read(OUT/'prepared.json')
    assert digest(ARCHIVE)==p['sha256'] and digest(__file__)==p['launcher_sha256']
    assert digest(preflight.OUT/'verified.json')==p['preflight_sha256'] and digest(CACHE)==p['node_cache_descriptor_sha256']
    assert hashlib.sha256(BOOTSTRAP.encode()).hexdigest()==p['bootstrap_sha256']
    return p


def upload():
    p=prepared()
    with (OUT/'.upload.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        if SOURCE.exists():return {'existing_source_revision':source_checked()['revision']}
        assert not (OUT/'upload-intent.json').exists(),'Inspect prior unknown upload; do not repeat it'
        api=HfApi();assert api.repo_info(REPO,repo_type='dataset').private
        assert not api.file_exists(REPO,p['archive'],repo_type='dataset'),'Inspect existing remote source'
        save(OUT/'upload-intent.json',{'created_at':now(),'archive':p['archive'],'sha256':p['sha256']})
        commit=api.upload_file(repo_id=REPO,repo_type='dataset',path_or_fileobj=ARCHIVE,path_in_repo=p['archive'])
        receipt={'repo':REPO,'revision':commit.oid,'archive':p['archive'],'sha256':p['sha256']}
        save(OUT/'upload-receipt.json',receipt)
        assert digest(hf_hub_download(REPO,p['archive'],repo_type='dataset',revision=commit.oid))==p['sha256']
        save(SOURCE,{**p,**receipt,'hf_preparation_sha256':digest(OUT/'prepared.json'),'remote_archive_verified':True})
        return receipt


def source_checked():
    p=prepared();source=read(SOURCE)
    assert source['remote_archive_verified'] and source['hf_preparation_sha256']==digest(OUT/'prepared.json')
    assert all(source[key]==value for key,value in p.items())
    return source


def environment(source,row):
    return {'SOURCE_ARCHIVE':source['archive'],'SOURCE_REVISION':source['revision'],
        'SOURCE_SHA256':source['sha256'],'SOURCE_MANIFEST_SHA256':source['source_manifest_sha256'],
        'PILOT_JOB':row['file'],'PILOT_NAME':row['job']['name'],
        'HF_HUB_DISABLE_PROGRESS_BARS':'1','PYTHONDONTWRITEBYTECODE':'1'}


def launch_once(api,directory,source,row,token):
    assert row in source['rows'] and not row['job']['control'],'Unadmitted runtime cell'
    directory=Path(directory)
    with (directory/'.launch.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);path=directory/'launch.json'
        if path.exists():
            guard=read(path)
            assert guard['stage']=='launched' and guard['source']==source and guard['row']==row,'Inspect original uncertain or changed launch'
            assert re.fullmatch('[a-f0-9]{24}',guard['job_id']);return guard
        guard={'stage':'launch_intent','created_at':now(),'source':source,'row':row};save(path,guard)
        try:
            remote=api.run_job(image='python:3.11-slim-bookworm',command=['bash','-lc',BOOTSTRAP],
                flavor=source['flavor'],timeout=source['timeout'],name=row['job']['name'],
                env=environment(source,row),secrets={'HF_TOKEN':token},
                labels={'project':'powergrid-ai','stage':'resource-turn-runtime-v1'})
            assert re.fullmatch('[a-f0-9]{24}',remote.id),'Invalid returned handle'
            guard.update(stage='launched',job_id=remote.id)
        except BaseException as error:
            guard.update(stage='launch_unknown',failure_type=type(error).__name__);raise
        finally:write(path,guard)
        return guard


def launch(execute=False):
    source=source_checked();proof=read(TEST)
    assert proof['passed'] and proof['tests']==8
    assert all(digest(ROOT/name)==sha for name,sha in proof['code_hashes'].items())
    if not execute:return {'execute':False,'jobs':6,'games':96,'scope':'runtime-only'}
    token=get_token();assert token;submitted=[]
    for row in source['rows']:
        folder=OUT/row['job']['name'];folder.mkdir(exist_ok=True)
        guard=launch_once(HfApi(),folder,source,row,token)
        item={'name':row['job']['name'],'job_id':guard['job_id'],'stage':guard['stage']}
        submitted.append(item);print(json.dumps(item),flush=True)
    return {'original_jobs':submitted,'new_strength_games':0,'automatic_retries':False}


def verify_artifacts(folder,source,row,evidence,audit_directory):
    pins=read(folder/'manifest.json')
    assert digest(folder/'manifest.json')==evidence['manifest_sha256']
    assert set(pins)|{'manifest.json'}=={str(p.relative_to(folder)) for p in folder.rglob('*') if p.is_file()}
    assert all(digest(folder/name)==sha for name,sha in pins.items())
    assert len(pins)+1==evidence['archived_files']
    job=row['job'];status=read(folder/'status.json');artifact=preflight.OUT/'source/artifact'
    expected={key:source[key] for key in ('source_manifest_sha256','protocol_sha256','entry_sha256',
        'artifact_descriptor_sha256','artifact_manifest_sha256')}
    expected.update(job_spec_sha256=row['job_spec_sha256'],source_revision=source['revision'],source_archive_sha256=source['sha256'],job=job)
    assert status['provenance']==expected and status['case']==job['name'] and status['scope']=='runtime-only'
    assert status['stage']=='complete' and status['games']==job['games'] and status['replay'] is None
    assert status['gradient_updates']==status['new_strength_games']==0
    assert status['automatic_retries'] is status['qualification_eligible'] is status['reserved_final_seeds_used'] is False
    assert digest(folder/'source-manifest.json')==source['source_manifest_sha256']
    assert digest(folder/'job-spec.json')==row['job_spec_sha256']
    report=read(folder/'evaluation/evaluation.json');original_audit=read(folder/'evaluation/independent-audit.json')
    assert digest(folder/'evaluation/evaluation.json')==status['evaluation_sha256']
    assert digest(folder/'evaluation/independent-audit.json')==status['audit_sha256']
    assert report['all_complete'] and not report['errors']
    assert report['completed_games']==report['expected_games']==len(report['results'])==job['games']
    expected_config={key:job[key] for key in ('mode','players','opponent','seed','start','deals','workers')}
    expected_config.update(artifact='/workspace/source/artifact',output=f"/workspace/output/{job['name']}/evaluation",
        descriptor_sha256=source['artifact_descriptor_sha256'])
    assert report['config']==expected_config
    m=status['measurement']
    assert all(math.isfinite(m[k]) and m[k]>0 for k in ('seconds','cpu_seconds','sampled_peak_total_rss_bytes','memory_samples'))
    assert m['memory_sampling_period_seconds']==.2 and m['includes_startup_and_validation']
    audit_directory.mkdir(exist_ok=False)
    for path in (folder/'evaluation').glob('decisions-*.jsonl'):shutil.copy2(path,audit_directory/path.name)
    code="""import json,sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.argv[1])/'policy'))
from resource_turn_full_audit_v3 import audit
r=json.loads(Path(sys.argv[2]).read_text())
config={**r['config'],'artifact':sys.argv[1],'output':sys.argv[3]}
result=audit(config,r['results'])
Path(sys.argv[3],'result.json').write_text(json.dumps(result,indent=2)+'\\n')
"""
    with (audit_directory/'driver.log').open('x') as log:
        subprocess.run([sys.executable,'-u','-B','-c',code,str(artifact),str(folder/'evaluation/evaluation.json'),str(audit_directory)],
            cwd='/tmp',stdout=log,stderr=subprocess.STDOUT,check=True)
    review=read(audit_directory/'result.json');assert review==original_audit
    assert review['games']==job['games'] and review['counts']==status['counts'] and review['counts']['rollout_caps']==0
    return {'games':job['games'],'audit':review,'measurement':m,'independent_audit_sha256':digest(audit_directory/'result.json')}


def collect():
    source=source_checked();results=[];states=[]
    with (OUT/'.collect.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        for row in source['rows']:
            name=row['job']['name'];folder=OUT/name;guard=read(folder/'launch.json')
            assert guard['stage']=='launched' and guard['source']==source and guard['row']==row
            if (folder/'verified.json').exists():
                result=read(folder/'verified.json')
                assert result['guard_sha256']==digest(folder/'launch.json') and result['job_id']==guard['job_id']
                assert result['source_sha256']==digest(SOURCE) and result['row']==row
                assert result['review']['independent_audit_sha256']==digest(folder/'independent-audit/result.json')
                results.append(result);continue
            api=HfApi();info=api.inspect_job(job_id=guard['job_id']);stage=info.status.stage
            assert info.command==['bash','-lc',BOOTSTRAP] and info.docker_image=='python:3.11-slim-bookworm'
            assert info.flavor==source['flavor'] and all(info.environment.get(k)==v for k,v in environment(source,row).items())
            state={'checked_at':now(),'job_id':guard['job_id'],'stage':stage,'name':name}
            states.append(state);write(folder/'status.json',state);print(json.dumps(state),flush=True)
            if stage in ('SCHEDULING','RUNNING','QUEUED','STARTING'):continue
            log=folder/'job.log'
            if not log.exists():log.write_text('\n'.join(str(line) for line in api.fetch_job_logs(job_id=guard['job_id'],follow=False)))
            receipts=[]
            for line in log.read_text().splitlines():
                if not line.startswith('{'):continue
                try:value=json.loads(line)
                except json.JSONDecodeError:continue
                if set(value)=={'case','status','evidence'} and value['case']==name:receipts.append(value)
            if len(receipts)==1:
                evidence=receipts[0]['evidence']
                assert evidence['repo']=='coyotte508/powergrid-ai-germany-v1' and evidence['archive_path']=='archives/'+name+'.tgz'
                assert evidence['remote_archive_verified'] and re.fullmatch('[a-f0-9]{40}',evidence['revision'])
                archive=Path(hf_hub_download(evidence['repo'],evidence['archive_path'],revision=evidence['revision']))
                assert digest(archive)==evidence['archive_sha256']
                if not (folder/'artifacts').exists():extract_verified(archive,folder/'artifacts')
                assert receipts[0]['status']==read(folder/'artifacts/status.json')
            if stage!='COMPLETED' or len(receipts)!=1:
                write(folder/'failure.json',{**state,'receipts':len(receipts),'logs_preserved':True})
                raise RuntimeError('Original runtime job incomplete/ambiguous; inspect without resubmission')
            review=verify_artifacts(folder/'artifacts',source,row,evidence,folder/'independent-audit')
            result={**state,'row':row,'review':review,'evidence':evidence,'verified':True,
                'source_sha256':digest(SOURCE),'guard_sha256':digest(folder/'launch.json')}
            save(folder/'verified.json',result);results.append(result)
        report={'checked_at':now(),'complete':len(results)==6,'verified_jobs':len(results),'jobs':results,
            'unverified_states':states,'source_sha256':digest(SOURCE),'scope':'runtime-only','new_strength_games':0,
            'qualification_eligible':False,'reserved_final_seeds_used':False}
        write(OUT/'collection-state.json',report)
        if report['complete'] and not RESULT.exists():
            assert sum(row['review']['games'] for row in results)==96;save(RESULT,report)
        return {'complete':report['complete'],'verified_jobs':len(results),'scope':'runtime-only'}


if __name__=='__main__':
    parser=argparse.ArgumentParser(__doc__);parser.add_argument('operation',choices=['prepare','upload','launch','collect'])
    parser.add_argument('--execute',action='store_true');args=parser.parse_args()
    result=launch(args.execute) if args.operation=='launch' else globals()[args.operation]()
    print(json.dumps(result),flush=True)
