"""Snapshot original handles and cached audits without collecting or submitting jobs.

The coordinator remains the sole study owner. This helper writes only to a new
snapshot directory and calls inspect_job on exact already-launched handles.
"""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import datetime
import hashlib
import json
from pathlib import Path
import re
import time

from huggingface_hub import HfApi

ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/'ai/strong/conservative-auction-development-source-v2.json'
OWNER=ROOT/'ai/runs/conservative-auction-development-coordinator-recovery-v2/state.json'
JOBS=ROOT/'ai/runs/conservative-auction-development-hf-v2'


def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def sha(raw):return hashlib.sha256(raw).hexdigest()
def object_hash(value):
    return sha(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode())


def stable_json(path):
    # State/launch files can be updated while the sole owner runs. A short read
    # race is not a job failure, permission to restart, or an uncertain launch.
    for attempt in range(5):
        raw=path.read_bytes()
        try:value=json.loads(raw)
        except json.JSONDecodeError:
            if attempt==4:raise
            time.sleep(.05);continue
        if path.read_bytes()==raw:return raw,value
        time.sleep(.05)
    raise RuntimeError('Snapshot could not obtain a stable read: '+str(path.relative_to(ROOT)))


def owner_checked():
    raw,state=stable_json(OWNER)
    proc=Path('/proc')/str(state['pid'])
    cmd=(proc/'cmdline').read_bytes()
    assert b'recover-conservative-auction-development-v2.py' in cmd and b'--start' in cmd
    start_ticks=(proc/'stat').read_text().rsplit(')',1)[1].split()[19]
    assert len(state['code_hashes'])==24
    for name,digest in state['code_hashes'].items():assert sha((ROOT/name).read_bytes())==digest,name
    return raw,state,{'pid':state['pid'],'start_ticks':start_ticks,'cmdline_sha256':sha(cmd)}


def snapshot(out):
    assert not out.exists(),'Snapshots must not overwrite prior evidence'
    before_raw,before,process=owner_checked()
    source_raw,source=stable_json(SOURCE)
    assert sha(source_raw)==before['development_source_sha256']
    assert source['remote_archive_verified'] and source['games']==10080 and len(source['rows'])==648
    fingerprint=object_hash(source);rows={r['name']:r for r in source['rows']}
    assert len(rows)==648
    captured={str(SOURCE.relative_to(ROOT)):source_raw}
    records=[];intents=[];verified_games=0
    started=now()
    paths=sorted(JOBS.glob('*/launch.json'))
    for guard_path in paths:
        raw,guard=stable_json(guard_path);name=guard_path.parent.name
        assert name in rows and guard['row']==rows[name]
        assert guard['source_fingerprint']==fingerprint
        relative=str(guard_path.relative_to(ROOT));captured[relative]=raw
        if guard['stage']!='launched':
            assert guard['stage'] in ('launch_intent','launch_unknown')
            intents.append({'name':name,'stage':guard['stage'],'launch_sha256':sha(raw)})
            continue
        job_id=guard['job_id'];assert re.fullmatch('[a-f0-9]{24}',job_id)
        row=rows[name]
        record={'name':name,'job_id':job_id,'arm':row['arm'],'players':row['players'],
                'planned_games':row['shard']['games'],'launch_sha256':sha(raw),
                'cached_audit_present':False}
        verified_path=guard_path.parent/'verified.json'
        if verified_path.exists():
            verified_raw,verified=stable_json(verified_path)
            assert verified['job_id']==job_id and verified['name']==name and verified['row']==row
            assert verified['verified'] is True and verified['stage']=='COMPLETED'
            assert verified['guard_sha256']==sha(raw) and verified['source_sha256']==sha(source_raw)
            assert verified['review']['games']==row['shard']['games']
            assert verified['review']['audit']['identity']==row['identity']
            assert verified['review']['audit']['expected']==row['shard']
            assert verified['review']['audit']['all_receipts_verified'] is True
            assert verified['review']['audit']['counts']['rollout_caps']==0
            evidence=verified['evidence']
            assert evidence['repo']=='coyotte508/powergrid-ai-germany-v1'
            assert evidence['archive_path']=='archives/'+name+'.tgz'
            assert re.fullmatch('[a-f0-9]{40}',evidence['revision']) and evidence['remote_archive_verified']
            manifest_path=guard_path.parent/'artifacts/manifest.json'
            manifest_raw,_=stable_json(manifest_path)
            assert sha(manifest_raw)==evidence['manifest_sha256']
            captured[str(verified_path.relative_to(ROOT))]=verified_raw
            captured[str(manifest_path.relative_to(ROOT))]=manifest_raw
            record.update(cached_audit_present=True,verified_sha256=sha(verified_raw),
                status='COMPLETED',status_basis='previously_completed_cached_raw_audit',evidence=evidence)
            verified_games+=row['shard']['games']
        records.append(record)
    assert len({r['job_id'] for r in records})==len(records)
    api=HfApi()
    def inspect(record):
        try:
            stage=api.inspect_job(job_id=record['job_id']).status.stage
            return record['name'],{'status':stage,'status_basis':'direct_original_handle_inspection','checked_at':now()}
        except Exception as error:
            # Preserve a transient observation error without calling it terminal.
            return record['name'],{'status':None,'status_basis':'observation_error',
                'error_type':type(error).__name__,'checked_at':now()}
    pending=[r for r in records if not r['cached_audit_present']]
    with ThreadPoolExecutor(max_workers=8) as pool:observed=dict(pool.map(inspect,pending))
    for record in records:
        if record['name'] in observed:record.update(observed[record['name']])
    after_raw,after,after_process=owner_checked()
    assert process==after_process
    assert before['code_hashes']==after['code_hashes']
    assert sha(SOURCE.read_bytes())==sha(source_raw)
    statuses=Counter(r['status'] or 'OBSERVATION_ERROR' for r in records)
    result={'snapshot_started_at':started,'snapshot_finished_at':now(),
        'scope':'Recovery metadata and direct status of unaudited originals only; no collection, new raw audit, resubmission, inference, outcome analysis or policy selection.',
        'owner_process':process,'owner_live_before_and_after':True,'all_24_pins_match':True,
        'owner_before':{k:before[k] for k in ('stage','development_verified','development_submitted','updated_at')},
        'owner_after':{k:after[k] for k in ('stage','development_verified','development_submitted','updated_at')},
        'source_sha256':sha(source_raw),'source_fingerprint':fingerprint,
        'expected_jobs':648,'expected_games':10080,'launched_handles_captured':len(records),
        'planned_games_in_captured_handles':sum(r['planned_games'] for r in records),
        'cached_audits_captured':sum(r['cached_audit_present'] for r in records),
        'games_in_captured_cached_audits':verified_games,'directly_inspected_handles':len(pending),
        'statuses':dict(statuses),'launches_in_progress_or_unknown':intents,'jobs':records,
        'new_guard_names_seen_after_capture':sorted({p.parent.name for p in JOBS.glob('*/launch.json')}-{p.parent.name for p in paths}),
        'complete':False,'new_hf_jobs':0,'reserved_final_seeds_used':False,'qualification_eligible':False,
        'snapshotter_sha256':sha(Path(__file__).read_bytes())}
    out.mkdir()
    captured['owner-before.json']=before_raw;captured['owner-after.json']=after_raw
    for name,raw in captured.items():
        target=out/name;target.parent.mkdir(parents=True,exist_ok=True)
        with target.open('xb') as stream:stream.write(raw)
        assert sha(target.read_bytes())==sha(raw)
    with (out/'captured-files.json').open('x') as stream:
        json.dump({name:sha(raw) for name,raw in captured.items()},stream,indent=2);stream.write('\n')
    with (out/'snapshot.json').open('x') as stream:json.dump(result,stream,indent=2);stream.write('\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ('jobs',)}),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(__doc__);parser.add_argument('output',type=Path)
    args=parser.parse_args();snapshot(args.output.resolve())
