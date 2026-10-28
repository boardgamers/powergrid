"""Archive the bounded collection snapshot and failure-preserving collector."""
from datetime import datetime,timezone
import json
from pathlib import Path
import shutil

from huggingface_hub import HfApi
from policy_iteration_evidence_archive import upload_evidence
from public_policy_development_job_v1 import read,digest

ROOT=Path(__file__).resolve().parents[2]
NAME='resource-runtime-collection-evidence-v2'
OUT=ROOT/'ai/runs'/NAME
RESULT=ROOT/'ai/strong'/(NAME+'.json')


def save(path,value):
    with path.open('x') as stream:
        json.dump(value,stream,indent=2,allow_nan=False);stream.write('\n')


def main():
    for path in (OUT,OUT.with_suffix('.tgz'),OUT.with_suffix('.intent.json'),RESULT):
        assert not path.exists(),'Inspect existing archive intent/outcome before retry'
    run=ROOT/'ai/runs/resource-turn-runtime-outcomes-v2';state=read(run/'state.json')
    tests=ROOT/'ai/runs/resource-runtime-collection-tests-v2.json';proof=read(tests)
    assert proof['passed'] and proof['tests']==12
    assert all(digest(ROOT/name)==sha for name,sha in proof['code_hashes'].items())
    assert state['collector_sha256']==digest(ROOT/'ai/strong/collect-resource-runtime-outcomes-v2.py')
    assert state['source_sha256']==digest(ROOT/'ai/strong/resource-turn-runtime-source-v1.json')
    assert state['verified_successful_jobs']==2 and state['verified_successful_games']==16
    assert state['failed_jobs_preserved']==1 and state['pending_jobs']==3 and state['unverified_jobs']==0
    assert state['all_originals_terminal'] is state['success_gate_passed'] is False
    sources={Path(__file__).resolve(),tests,ROOT/'ai/runs/resource-turn-runtime-outcomes-v2-first.log',
        ROOT/'ai/runs/resource-runtime-collection-tests-v2-recovered.log'}
    sources.update(ROOT/name for name in proof['code_hashes'])
    for directory in (run,ROOT/'ai/runs/resource-runtime-collection-tests-v2-initial'):
        sources.update(p for p in directory.rglob('*') if p.is_file())
    for row in state['jobs']:
        original=ROOT/'ai/runs/resource-turn-runtime-hf-v1'/row['name']
        sources.add(original/'launch.json')
        if row['outcome']=='verified_success':
            receipt=ROOT/row['verified_receipt'];assert digest(receipt)==row['verified_receipt_sha256']
            sources.add(receipt);sources.add(receipt.parent/'independent-audit/result.json')
    sources.update(ROOT/'ai/strong'/name for name in ('resource-turn-runtime-source-v1.json',
        'resource-turn-runtime-launch-evidence-v1.json','resource-turn-boundary-evidence-v2.json',
        'manage-resource-turn-runtime-v1.py','policy_iteration_evidence_archive.py','strategic_collection.py'))
    sources.update(ROOT/'ai'/name for name in ('RESOURCE-TURN-RUNTIME-2026-10-28.md','RESUME.md'))
    api=HfApi();repo='coyotte508/powergrid-ai-germany-v1'
    assert api.model_info(repo).private and not api.file_exists(repo,'archives/'+NAME+'.tgz')
    OUT.mkdir();hashes={}
    for source in sorted(sources):
        assert source.is_file() and not source.is_symlink()
        name=str(source.relative_to(ROOT));target=OUT/name;target.parent.mkdir(parents=True,exist_ok=True)
        sha=digest(source);shutil.copy2(source,target);assert digest(target)==sha;hashes[name]=sha
    save(OUT/'manifest.json',hashes)
    intent={'created_at':datetime.now(timezone.utc).isoformat(),'stage':'prepared_for_upload',
        'archive_path':'archives/'+NAME+'.tgz','manifest_sha256':digest(OUT/'manifest.json')}
    save(OUT.with_suffix('.intent.json'),intent)
    print(json.dumps({'stage':'uploading','files':len(hashes)+1}),flush=True)
    archive=upload_evidence(OUT)
    save(RESULT,{'status':'collection_path_verified_original_runtime_gate_failed_remaining_jobs_pending',
        'state_snapshot_sha256':digest(run/'state.json'),'tests_sha256':digest(tests),'tests':12,
        'verified_successful_jobs':2,'verified_successful_games':16,'failed_jobs_preserved':1,'pending_jobs':3,
        'all_originals_terminal':False,'success_gate_passed':False,'new_hf_jobs':0,'new_inference':0,
        'new_full_games':0,'qualification_eligible':False,'reserved_final_seeds_used':False,'archive':archive})
    OUT.with_suffix('.intent.json').write_text(json.dumps({**intent,'stage':'uploaded_download_verified',
        'archive':archive,'descriptor_sha256':digest(RESULT)},indent=2)+'\n')
    print(json.dumps(archive),flush=True)


if __name__=='__main__':main()
