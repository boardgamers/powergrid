"""One-attempt launch of the corrected resource runtime pilots.

There is deliberately no admission-creation operation. A separate reviewed
budget must bind the terminal original outcomes before preparation or launch.
This script never retries jobs, runs simulations locally, or selects policies.
"""
import argparse
import base64
from datetime import datetime, timezone
import fcntl
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import tarfile

from huggingface_hub import HfApi, get_token, hf_hub_download
from public_policy_development_job_v1 import digest, read, write

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'ai/runs/resource-turn-runtime-hf-v2'
SOURCE=ROOT/'ai/strong/resource-turn-runtime-source-v2.json'
ADMISSION=ROOT/'ai/strong/resource-turn-runtime-admission-v2.json'
ARCHIVE=ROOT/'ai/runs/strong-source-resource-turn-runtime-v2.tgz'
TEST=ROOT/'ai/runs/resource-turn-runtime-launcher-tests-v2/assessment.json'
EVIDENCE=ROOT/'ai/strong/resource-runtime-preflight-evidence-v2.json'
REPO='coyotte508/powergrid-ai-training-v1'


def module(name, filename):
    spec=importlib.util.spec_from_file_location(name, Path(__file__).with_name(filename))
    value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value


preflight=module('corrected_resource_preflight', 'prepare-resource-turn-runtime-v2.py')
collector=module('original_resource_outcomes', 'collect-resource-runtime-outcomes-v2.py')
original=collector.load_manager()
CACHE=original.CACHE
save=original.save
BOOTSTRAP=original.BOOTSTRAP.split('python -u -B /workspace/source/resource_turn_runtime_job_v1.py')[0]+r'''
python - <<'ADMISSION'
import base64,hashlib,os
from pathlib import Path
raw=base64.b64decode(os.environ['RUNTIME_ADMISSION_BASE64'],validate=True)
assert hashlib.sha256(raw).hexdigest()==os.environ['RUNTIME_ADMISSION_SHA256']
with Path('/workspace/runtime-admission.json').open('xb') as stream:stream.write(raw)
ADMISSION
python -u -B /workspace/source/resource_turn_runtime_job_v2.py \
  --source /workspace/source --manifest-sha256 "$SOURCE_MANIFEST_SHA256" \
  --job "$PILOT_JOB" --output "/workspace/output/$PILOT_NAME" \
  --admission /workspace/runtime-admission.json --admission-sha256 "$RUNTIME_ADMISSION_SHA256" \
  --source-revision "$SOURCE_REVISION" --source-archive-sha256 "$SOURCE_SHA256" --execute --upload
'''


def now():return datetime.now(timezone.utc).isoformat()


def terminal_summary_checked(report):
    """Do not confuse a well-shaped wrapper admission with actual outcomes."""
    assert report['all_originals_terminal'] is True, 'Wait for all six original outcomes'
    records=report['jobs']
    assert len(records)==6
    expected={'pg-resource-turn-runtime-v1-'+name:handle for name,handle in collector.HANDLES.items()}
    assert {row['name']:row['job_id'] for row in records}==expected
    assert all(row['stage'] in collector.FAILED|{'COMPLETED'} for row in records)
    assert all(row['outcome'] in ('verified_success','failed_preserved') for row in records), 'Unpreserved original evidence'
    assert all((row['outcome']=='verified_success')==row['verified'] for row in records)
    assert all(row['stage']=='COMPLETED' for row in records if row['verified'])
    for key,value in collector.summarize(records).items():
        if key!='checked_at':assert report[key]==value, 'Original summary mismatch: '+key
    assert report['pending_jobs']==report['unverified_jobs']==0
    return records


def original_outcomes_checked():
    report=read(collector.RESULT);records=terminal_summary_checked(report)
    source=original.source_checked()
    assert report['source_sha256']==digest(original.SOURCE)
    assert report['collector_sha256']==digest(collector.__file__)
    by_name={row['job']['name']:row for row in source['rows']}
    for record in records:
        name=record['name'];row=by_name[name];folder=original.OUT/name
        guard=read(folder/'launch.json')
        assert guard['stage']=='launched' and guard['job_id']==record['job_id']
        assert guard['source']==source and guard['row']==row
        paths=(collector.OUT/name,folder)
        raw=next(p/'artifacts' for p in paths if (p/'artifacts').exists())
        evidence=record['evidence'];status=collector.raw_checked(raw,source,row,evidence)
        assert evidence['remote_archive_verified'] is True
        assert evidence['repo']=='coyotte508/powergrid-ai-germany-v1'
        assert evidence['archive_path']=='archives/'+name+'.tgz'
        assert re.fullmatch('[a-f0-9]{40}',evidence['revision'])
        log=next(p/'job.log' for p in (folder,collector.OUT/name) if (p/'job.log').exists())
        receipts=[]
        for line in log.read_text().splitlines():
            if not line.startswith('{'):continue
            try:value=json.loads(line)
            except json.JSONDecodeError:continue
            if set(value)=={'case','status','evidence'} and value['case']==name:receipts.append(value)
        assert len(receipts)==1 and receipts[0]['status']==status and receipts[0]['evidence']==evidence
        if record['verified']:
            receipt=ROOT/record['verified_receipt']
            assert receipt in tuple(p/'verified.json' for p in paths)
            assert digest(receipt)==record['verified_receipt_sha256']
            proof=collector.cached_checked(receipt,folder,guard,source,row,original)
            assert proof['review']==record['review'] and proof['evidence']==evidence
            assert status['stage']=='complete' and status['measurement']==record['review']['measurement']
        else:
            assert record['raw_artifacts_verified'] is True and record['partial_games_independently_audited'] is False
            assert record['original_success_gate_passed'] is False
            assert status['stage']==record['wrapper_stage'] and status.get('measurement')==record['measurement']
            partial=read(raw/'evaluation/evaluation.json') if (raw/'evaluation/evaluation.json').exists() else None
            assert record['partial_complete_games_reported']==(partial['completed_games'] if partial else None)
    return report,source


def inspect_original_terminals(api, report, source):
    """Fresh authoritative observations immediately before any submissions."""
    terminal_summary_checked(report)
    rows={row['job']['name']:row for row in source['rows']}
    for record in report['jobs']:
        info=api.inspect_job(job_id=record['job_id'])
        assert info.status.stage==record['stage'], 'Original status changed; collect and review first'
        assert info.command==['bash','-lc',original.BOOTSTRAP]
        assert info.docker_image=='python:3.11-slim-bookworm' and info.flavor==source['flavor']
        assert all(info.environment.get(k)==v for k,v in original.environment(source,rows[record['name']]).items())


def admission_checked(admission, prep, protocol, outcomes_sha):
    assert admission['revision']=='resource-turn-runtime-admission-v2'
    assert admission['source_manifest_sha256']==prep['source_manifest_sha256']
    assert admission['protocol_sha256']==prep['protocol_sha256']
    assert admission['all_originals_terminal'] is True and admission['original_outcomes_sha256']==outcomes_sha
    assert re.fullmatch('[a-f0-9]{64}',outcomes_sha)
    assert admission['source_evidence_preserved'] is True and admission['scope']=='runtime-only'
    assert admission['automatic_retries'] is False and not admission.get('synthetic_fixtures_only',False)
    assert admission['qualification_eligible'] is False and admission['reserved_final_seeds_used'] is False
    expected={name:digest(preflight.OUT/'source'/name) for name,job in protocol['jobs'].items() if not job['control']}
    assert len(expected)==2 and admission['job_specs']==expected
    assert admission['flavor']=='cpu-upgrade' and admission['max_concurrent_jobs']==2
    seconds=admission['timeout_seconds']
    assert type(seconds) is int and 7200<=seconds<=43200
    review=admission['budget_review']
    assert review['original_outcomes_sha256']==outcomes_sha
    assert review['max_total_job_hours']==2*seconds/3600
    assert isinstance(review['reason'],str) and len(review['reason'].strip())>=30
    assert datetime.fromisoformat(review['reviewed_at']).tzinfo is not None
    return admission


def prerequisites():
    prep=preflight.pinned();proof=read(preflight.OUT/'verified.json')
    assert proof['passed'] and proof['jobs_dry_validated']==3 and proof['recorded_games_replayed']==8
    assert proof['exact_decisions']==1360 and proof['unadmitted_executions_rejected']==2
    assert proof['source_manifest_sha256']==prep['source_manifest_sha256']
    assert proof['prepared_sha256']==digest(preflight.OUT/'prepared.json')
    assert proof['control_manifest_sha256']==digest(preflight.OUT/'local-control/manifest.json')
    assert proof['control_status_sha256']==digest(preflight.OUT/'local-control/status.json')
    evidence=read(EVIDENCE)
    assert evidence['verification_sha256']==digest(preflight.OUT/'verified.json')
    assert evidence['source_manifest_sha256']==prep['source_manifest_sha256']
    assert evidence['archive']['remote_archive_verified'] is True
    protocol=read(preflight.PROTOCOL)
    assert protocol['hf_jobs']==2 and protocol['hf_games']==32
    report,old_source=original_outcomes_checked()
    admission=admission_checked(read(ADMISSION),prep,protocol,digest(collector.RESULT))
    return prep,protocol,admission,report,old_source


def prepare():
    prep,protocol,admission,_,_=prerequisites()
    assert not OUT.exists() and not ARCHIVE.exists() and not SOURCE.exists(), 'Inspect previous preparation first'
    OUT.mkdir();root=preflight.OUT/'source';pins=read(root/'source-manifest.json')
    with tarfile.open(ARCHIVE,'w:gz') as bundle:
        for name in sorted(set(pins)|{'source-manifest.json'}):
            path=root/name;assert path.is_file() and not path.is_symlink()
            info=bundle.gettarinfo(path,arcname=name);info.uid=info.gid=info.mtime=0;info.uname=info.gname=''
            with path.open('rb') as stream:bundle.addfile(info,stream)
    rows=[{'file':name,'job':job,'job_spec_sha256':digest(root/name)}
        for name,job in protocol['jobs'].items() if not job['control']]
    assert len(rows)==2 and sum(row['job']['games'] for row in rows)==32
    p={key:prep[key] for key in ('source_manifest_sha256','source_files','protocol_sha256','entry_sha256',
        'artifact_descriptor_sha256','artifact_manifest_sha256')}
    p.update(created_at=now(),archive=ARCHIVE.name,sha256=digest(ARCHIVE),bytes=ARCHIVE.stat().st_size,
        preparation_sha256=digest(preflight.OUT/'prepared.json'),preflight_sha256=digest(preflight.OUT/'verified.json'),
        preflight_evidence_sha256=digest(EVIDENCE),launcher_sha256=digest(__file__),
        bootstrap_sha256=hashlib.sha256(BOOTSTRAP.encode()).hexdigest(),node_cache_descriptor_sha256=digest(CACHE),
        admission_sha256=digest(ADMISSION),admission_base64=base64.b64encode(ADMISSION.read_bytes()).decode(),
        original_outcomes_sha256=digest(collector.RESULT),rows=rows,flavor=admission['flavor'],
        timeout=f"{admission['timeout_seconds']}s",timeout_seconds=admission['timeout_seconds'],
        max_concurrent_jobs=2,games=32,scope='runtime-only',automatic_retries=False,
        new_strength_games=0,qualification_eligible=False,reserved_final_seeds_used=False)
    save(OUT/'prepared.json',p)
    return {'prepared':True,'jobs':2,'games':32,'timeout_seconds':p['timeout_seconds'],'archive_sha256':p['sha256']}


def prepared():
    prep,protocol,admission,report,old_source=prerequisites();p=read(OUT/'prepared.json')
    assert digest(ARCHIVE)==p['sha256'] and digest(__file__)==p['launcher_sha256']
    assert digest(ADMISSION)==p['admission_sha256'] and digest(collector.RESULT)==p['original_outcomes_sha256']
    assert base64.b64decode(p['admission_base64'],validate=True)==ADMISSION.read_bytes()
    assert digest(preflight.OUT/'verified.json')==p['preflight_sha256'] and digest(EVIDENCE)==p['preflight_evidence_sha256']
    assert digest(CACHE)==p['node_cache_descriptor_sha256']
    assert hashlib.sha256(BOOTSTRAP.encode()).hexdigest()==p['bootstrap_sha256']
    assert all(p[key]==prep[key] for key in ('source_manifest_sha256','source_files','protocol_sha256',
        'entry_sha256','artifact_descriptor_sha256','artifact_manifest_sha256'))
    rows=[{'file':n,'job':j,'job_spec_sha256':digest(preflight.OUT/'source'/n)}
        for n,j in protocol['jobs'].items() if not j['control']]
    assert p['rows']==rows and p['timeout_seconds']==admission['timeout_seconds']
    assert p['timeout']==f"{admission['timeout_seconds']}s" and p['flavor']==admission['flavor']
    assert p['max_concurrent_jobs']==2 and p['games']==32
    return p,report,old_source


def upload():
    p,_,_=prepared()
    with (OUT/'.upload.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        if SOURCE.exists():return {'existing_source_revision':source_checked()[0]['revision']}
        assert not (OUT/'upload-intent.json').exists(), 'Inspect prior unknown upload; never repeat it'
        api=HfApi();assert api.repo_info(REPO,repo_type='dataset').private
        assert not api.file_exists(REPO,p['archive'],repo_type='dataset'), 'Inspect existing remote source'
        save(OUT/'upload-intent.json',{'created_at':now(),'archive':p['archive'],'sha256':p['sha256']})
        commit=api.upload_file(repo_id=REPO,repo_type='dataset',path_or_fileobj=ARCHIVE,path_in_repo=p['archive'])
        receipt={'repo':REPO,'revision':commit.oid,'archive':p['archive'],'sha256':p['sha256']}
        save(OUT/'upload-receipt.json',receipt)
        assert digest(hf_hub_download(REPO,p['archive'],repo_type='dataset',revision=commit.oid))==p['sha256']
        save(SOURCE,{**p,**receipt,'hf_preparation_sha256':digest(OUT/'prepared.json'),'remote_archive_verified':True})
        return receipt


def source_checked():
    p,report,old_source=prepared();source=read(SOURCE)
    assert source['remote_archive_verified'] is True and source['hf_preparation_sha256']==digest(OUT/'prepared.json')
    assert source['repo']==REPO and re.fullmatch('[a-f0-9]{40}',source['revision'])
    assert all(source[key]==value for key,value in p.items())
    return source,report,old_source


def environment(source,row):
    return {**original.environment(source,row),'RUNTIME_ADMISSION_BASE64':source['admission_base64'],
        'RUNTIME_ADMISSION_SHA256':source['admission_sha256']}


def launch_once(api,directory,source,row,token):
    assert len(source['rows'])==2 and row in source['rows'] and not row['job']['control']
    assert source['games']==32 and source['max_concurrent_jobs']==2 and source['automatic_retries'] is False
    directory=Path(directory)
    with (directory/'.launch.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);path=directory/'launch.json'
        if path.exists():
            guard=read(path)
            assert guard['stage']=='launched' and guard['source']==source and guard['row']==row, 'Inspect original uncertain or changed launch'
            assert re.fullmatch('[a-f0-9]{24}',guard['job_id']);return guard
        guard={'stage':'launch_intent','created_at':now(),'source':source,'row':row};save(path,guard)
        try:
            remote=api.run_job(image='python:3.11-slim-bookworm',command=['bash','-lc',BOOTSTRAP],
                flavor=source['flavor'],timeout=source['timeout'],name=row['job']['name'],
                env=environment(source,row),secrets={'HF_TOKEN':token},
                labels={'project':'powergrid-ai','stage':'resource-turn-runtime-v2'})
            assert re.fullmatch('[a-f0-9]{24}',remote.id), 'Invalid returned handle'
            guard.update(stage='launched',job_id=remote.id)
        except BaseException as error:
            guard.update(stage='launch_unknown',failure_type=type(error).__name__);raise
        finally:write(path,guard)
        return guard


def launch(execute=False):
    source,report,old_source=source_checked();proof=read(TEST)
    assert proof['passed'] and proof['network_calls']==proof['new_hf_jobs']==0
    assert all(digest(ROOT/name)==sha for name,sha in proof['code_hashes'].items())
    if not execute:return {'execute':False,'jobs':2,'games':32,'scope':'runtime-only'}
    with (OUT/'.launch-all.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        api=HfApi();inspect_original_terminals(api,report,old_source)
        token=get_token();assert token;submitted=[]
        for row in source['rows']:
            folder=OUT/row['job']['name'];folder.mkdir(exist_ok=True)
            guard=launch_once(api,folder,source,row,token)
            item={'name':row['job']['name'],'job_id':guard['job_id'],'stage':guard['stage']}
            submitted.append(item);print(json.dumps(item),flush=True)
    return {'original_jobs':submitted,'new_strength_games':0,'automatic_retries':False}


if __name__=='__main__':
    parser=argparse.ArgumentParser(__doc__);parser.add_argument('operation',choices=['prepare','upload','launch'])
    parser.add_argument('--execute',action='store_true');args=parser.parse_args()
    result=launch(args.execute) if args.operation=='launch' else globals()[args.operation]()
    print(json.dumps(result),flush=True)
