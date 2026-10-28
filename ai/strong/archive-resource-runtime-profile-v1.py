"""Archive exact-parity profiling evidence; no experiments or job submission."""
from datetime import datetime,timezone
import json
from pathlib import Path
import shutil

from huggingface_hub import HfApi
from policy_iteration_evidence_archive import upload_evidence
from public_policy_development_job_v1 import read,digest

ROOT=Path(__file__).resolve().parents[2]
NAME='resource-runtime-profile-evidence-v1'
OUT=ROOT/'ai/runs'/NAME
RESULT=ROOT/'ai/strong'/(NAME+'.json')


def save(path,value):
    with path.open('x') as stream:json.dump(value,stream,indent=2,allow_nan=False);stream.write('\n')


def main():
    for path in (OUT,OUT.with_suffix('.tgz'),OUT.with_suffix('.intent.json'),RESULT):
        assert not path.exists(),'Inspect prior archive intent/outcome before retry'
    run=ROOT/'ai/runs/resource-runtime-profile-v2';failed=ROOT/'ai/runs/resource-runtime-profile-v1'
    report=ROOT/'ai/strong/resource-runtime-profile-results-v1.json';data=read(report);plan=read(run/'plan.json')
    assert data['passed'] and data['exact_original_receipts']==4 and data['rollout_caps']==0
    assert data['assessment_sha256']==digest(run/'assessment.json') and data['plan_sha256']==digest(run/'plan.json')
    assert all(digest(run/name)==sha for name,sha in data['output_hashes'].items())
    assert all(digest(ROOT/name)==sha for name,sha in plan['input_hashes'].items())
    assert digest(ROOT/'ai/strong/profile-resource-runtime-v1.py')==plan['source_sha256']
    assert digest(failed/'failure-summary.json')==plan['preserved_failed_profile']['summary_sha256']
    assert digest(failed/'original-profiler.py')==plan['preserved_failed_profile']['original_profiler_sha256']
    pilot=ROOT/'ai/runs/resource-turn-runtime-hf-v1/pg-resource-turn-runtime-v1-whole-2p'
    assert digest(pilot/'verified.json')==plan['verified_pilot_sha256']
    sources={Path(__file__).resolve(),report,run.with_suffix('.log'),failed.with_suffix('.log'),
        ROOT/'ai/strong/profile-resource-runtime-v1.py',pilot/'verified.json',pilot/'independent-audit/result.json'}
    for directory in (run,failed):sources.update(p for p in directory.rglob('*') if p.is_file())
    sources.update(ROOT/'ai/strong'/name for name in ('resource-turn-runtime-source-v1.json',
        'resource-turn-runtime-launch-evidence-v1.json','resource-turn-snapshot-adapter-evidence-v1.json',
        'policy_iteration_evidence_archive.py','strategic_collection.py'))
    sources.update(ROOT/'ai'/name for name in ('RESOURCE-RUNTIME-PROFILE-2026-10-28.md','RESUME.md'))
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
    save(OUT.with_suffix('.intent.json'),intent);print(json.dumps({'stage':'uploading','files':len(hashes)+1}),flush=True)
    archive=upload_evidence(OUT)
    prior=read(failed/'failure-summary.json')
    failed_response=read(failed/'response-0.json')['diagnostics']['searchResult']['search']
    save(RESULT,{'status':'runtime_profile_verified_not_strength_evidence','assessment_sha256':data['assessment_sha256'],
        'exact_original_receipts':4,'successful_replay_rollouts':data['rollouts_replayed'],
        'total_rollouts_including_failed_harness':data['rollouts_replayed']+prior['replayed_rollouts'],
        'total_neural_decisions_including_failed_harness':data['neural_decisions_replayed']+failed_response['neuralDecisions'],
        'local_component_fractions':data['local_component_fractions'],'preserved_failed_profile':plan['preserved_failed_profile'],
        'new_hf_jobs':0,'new_full_game_trajectories':0,'new_strength_games':0,'new_gradients':0,
        'qualification_eligible':False,'reserved_final_seeds_used':False,'archive':archive})
    OUT.with_suffix('.intent.json').write_text(json.dumps({**intent,'stage':'uploaded_download_verified',
        'archive':archive,'descriptor_sha256':digest(RESULT)},indent=2)+'\n')
    print(json.dumps(archive),flush=True)


if __name__=='__main__':main()
