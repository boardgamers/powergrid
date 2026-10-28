"""Archive the original runtime launch and recovery evidence; never submit jobs."""
from datetime import datetime,timezone
import importlib.util
import json
from pathlib import Path
import shutil

from huggingface_hub import HfApi
from policy_iteration_evidence_archive import upload_evidence
from public_policy_development_job_v1 import read,digest

ROOT=Path(__file__).resolve().parents[2]
NAME='resource-turn-runtime-launch-evidence-v1'
OUT=ROOT/'ai/runs'/NAME
RESULT=ROOT/'ai/strong'/(NAME+'.json')
HANDLES={
    'pg-resource-turn-runtime-v1-corrected-2p':'6ae20c1241e90535df775236',
    'pg-resource-turn-runtime-v1-corrected-6p':'6ae20c123fb22a235dd4146d',
    'pg-resource-turn-runtime-v1-anchored-2p':'6ae20c133fb22a235dd4146f',
    'pg-resource-turn-runtime-v1-anchored-6p':'6ae20c1341e90535df775238',
    'pg-resource-turn-runtime-v1-whole-2p':'6ae20c133fb22a235dd41471',
    'pg-resource-turn-runtime-v1-whole-6p':'6ae20c1341e90535df77523a',
}


def save(path,value):
    with path.open('x') as stream:json.dump(value,stream,indent=2,allow_nan=False);stream.write('\n')


def main():
    for path in (OUT,OUT.with_suffix('.tgz'),OUT.with_suffix('.intent.json'),RESULT):
        assert not path.exists(),'Inspect previous archive intent/outcome before retrying'
    path=Path(__file__).with_name('manage-resource-turn-runtime-v1.py')
    spec=importlib.util.spec_from_file_location('runtime_launch_archive_manager',path)
    manager=importlib.util.module_from_spec(spec);spec.loader.exec_module(manager)
    source=manager.source_checked();tests=read(manager.TEST)
    assert tests['passed'] and tests['tests']==8
    assert all(digest(ROOT/name)==sha for name,sha in tests['code_hashes'].items())
    assert source['games']==96 and source['max_concurrent_jobs']==6 and source['timeout']=='4h'
    assert {row['job']['name'] for row in source['rows']}==set(HANDLES)
    sources={Path(__file__).resolve(),manager.SOURCE,manager.TEST,path.resolve(),manager.CACHE,
        manager.OUT/'prepared.json',manager.OUT/'upload-intent.json',manager.OUT/'upload-receipt.json',
        manager.OUT/'collection-state.json'}
    records=[]
    for row in source['rows']:
        name=row['job']['name'];folder=manager.OUT/name;guard=read(folder/'launch.json')
        status=read(folder/'status.json')
        assert guard['stage']=='launched' and guard['job_id']==HANDLES[name]
        assert guard['source']==source and guard['row']==row
        assert status['job_id']==guard['job_id'] and status['name']==name
        sources.update((folder/'launch.json',folder/'status.json'))
        records.append({'name':name,'job_id':guard['job_id'],'games':row['job']['games'],
            'mode':row['job']['mode'],'players':row['job']['players'],'observed_status':status,
            'guard_sha256':digest(folder/'launch.json')})
    prep=manager.preflight.OUT
    sources.update(p for p in prep.iterdir() if p.is_file())
    sources.update(p for p in (prep/'local-control').rglob('*') if p.is_file())
    sources.add(prep/'source/source-manifest.json')
    sources.update(ROOT/name for name in tests['code_hashes'])
    sources.update(ROOT/row['path'] for row in source['resource_estimate']['calibration'])
    sources.update(ROOT/'ai/strong'/name for name in (
        'resource-turn-runtime-protocol-v1.json','resource-turn-anchored-policy-evidence-v1.json',
        'resource-turn-anchored-policy-results-v1.json','resource-turn-full-integration-evidence-v2.json',
        'resource-replanning-development-complete-evidence-v1.json','resource-replanning-job-source-v1.json',
        'policy_iteration_evidence_archive.py','strategic_collection.py',
        'public_policy_development_job_v1.py','manage-public-policy-development-hf-v1.py',
        'population_policy_verification.py','conservative-auction-bootstrap-recovery-evidence-v1.json'))
    sources.update(ROOT/'ai'/name for name in ('RESOURCE-TURN-RUNTIME-2026-10-28.md',
        'RESOURCE-TURN-ANCHORED-POLICY-2026-10-28.md','RESUME.md'))
    api=HfApi();repo='coyotte508/powergrid-ai-germany-v1'
    assert api.model_info(repo).private
    assert not api.file_exists(repo,'archives/'+NAME+'.tgz'),'Inspect existing remote archive'
    OUT.mkdir();hashes={}
    for path in sorted(sources):
        assert path.is_file() and not path.is_symlink()
        name=str(path.relative_to(ROOT));target=OUT/name;target.parent.mkdir(parents=True,exist_ok=True)
        before=digest(path);shutil.copy2(path,target);assert digest(target)==before;hashes[name]=before
    coordinator=ROOT/'ai/runs/conservative-auction-development-attempts-coordinator-v1/state.json'
    state=read(coordinator);pid=state['pid'];proc=Path('/proc')/str(pid)
    command=(proc/'cmdline').read_bytes().replace(b'\0',b' ').decode().strip()
    assert command.endswith('ai/strong/coordinate-conservative-auction-attempts-v1.py --start')
    assert all(digest(ROOT/name)==sha for name,sha in state['code_hashes'].items())
    owner={'checked_at':datetime.now(timezone.utc).isoformat(),'pid':pid,'command':command,
        'proc_stat':(proc/'stat').read_text(),'state':state,'all_owner_pins_match':True,
        'observation_only':True}
    owner_path=OUT/'auction-owner-snapshot.json';save(owner_path,owner);hashes[owner_path.name]=digest(owner_path)
    snapshot={'created_at':datetime.now(timezone.utc).isoformat(),'scope':'runtime-only',
        'source_descriptor_sha256':digest(manager.SOURCE),'source_revision':source['revision'],
        'source_archive_sha256':source['sha256'],'source_manifest_sha256':source['source_manifest_sha256'],
        'protocol_sha256':source['protocol_sha256'],'original_jobs':records,
        'submitted_jobs':6,'planned_games':96,'verified_jobs_at_snapshot':0,
        'local_recorded_control_games':8,'local_recorded_control_decisions':1360,
        'submission_guard_tests':8,'automatic_retries':False,'resource_coordinator_created':False,
        'new_gradients':0,'new_strength_games':0,'qualification_eligible':False,
        'reserved_final_seeds_used':False,'auction_source_changed':False}
    assert read(manager.OUT/'collection-state.json')['verified_jobs']==0
    snapshot_path=OUT/'launch-snapshot.json';save(snapshot_path,snapshot);hashes[snapshot_path.name]=digest(snapshot_path)
    note=OUT/'README.md'
    note.write_text('''# Resource runtime launch recovery evidence

Six original HF handles and their guards, pinned source descriptor, admission
protocol, exact wrapper and launcher, fake-API tests, and eight recorded-game
control receipts. Full job source is already available at the immutable dataset
revision in the source descriptor. Do not repeat preparation, validation or job
submission. Resume by inspecting the exact original handles and using collect.

The jobs were running when observed. These are runtime-only engineering games,
not independent strength or qualification data. No new gradients, selected
candidate, reserved final seeds or deployment. Auction-owner status is a
read-only snapshot; verify the actual process before interacting with that study.
''');hashes[note.name]=digest(note);save(OUT/'manifest.json',hashes)
    intent={'created_at':snapshot['created_at'],'stage':'prepared_for_upload',
        'archive_path':'archives/'+NAME+'.tgz','manifest_sha256':digest(OUT/'manifest.json')}
    save(OUT.with_suffix('.intent.json'),intent)
    print(json.dumps({'stage':'uploading','files':len(hashes)+1}),flush=True)
    archive=upload_evidence(OUT)
    save(RESULT,{**snapshot,'status':'original_runtime_jobs_launched_results_pending','archive':archive})
    OUT.with_suffix('.intent.json').write_text(json.dumps({**intent,'stage':'uploaded_download_verified',
        'archive':archive,'descriptor_sha256':digest(RESULT)},indent=2)+'\n')
    print(json.dumps(archive),flush=True)


if __name__=='__main__':main()
