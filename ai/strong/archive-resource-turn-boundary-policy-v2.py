"""Archive the integrated stable-sampling policy and actual search receipts once."""
from datetime import datetime,timezone
import json
from pathlib import Path
import shutil

from huggingface_hub import HfApi
from policy_iteration_evidence_archive import upload_evidence
from public_policy_development_job_v1 import read,digest

ROOT=Path(__file__).resolve().parents[2]
NAME='resource-turn-boundary-policy-evidence-v2'
OUT=ROOT/'ai/runs'/NAME
RESULT=ROOT/'ai/strong'/(NAME+'.json')


def save(path,value):
    with path.open('x') as stream:json.dump(value,stream,indent=2,allow_nan=False);stream.write('\n')


def main():
    for p in (OUT,OUT.with_suffix('.tgz'),OUT.with_suffix('.intent.json'),RESULT):
        assert not p.exists(),'Inspect prior archive intent/outcome before retrying'
    run=ROOT/'ai/runs/resource-turn-boundary-policy-v2';assessment=read(run/'assessment.json')
    report=ROOT/'ai/strong/resource-turn-boundary-policy-results-v2.json'
    assert assessment['passed'] and read(report)['assessment_sha256']==digest(run/'assessment.json')
    counts=assessment['counts']
    assert assessment['exceptional_resource_turns']==4 and counts['normal_first_searches_exact']==20
    assert counts['exceptional_first_searches_exact']==3
    assert counts['lifecycle_replays']==3 and counts['invalid_history_errors']==1
    assert counts['tampered_receipts_rejected']==20 and counts['rollout_caps']==0
    assert assessment['new_hf_jobs']==assessment['new_full_game_trajectories']==0
    for key in ('code_hashes','input_hashes'):
        assert all(digest(ROOT/name)==sha for name,sha in assessment[key].items())
    assert all(digest(run/name)==sha for name,sha in assessment['output_hashes'].items())
    artifact=Path(assessment['artifact']);manifest=read(artifact/'manifest.json')
    assert digest(artifact/'manifest.json')==assessment['manifest_sha256']
    assert digest(artifact/'resource-full-descriptor.json')==assessment['descriptor_sha256']
    assert all(digest(artifact/name)==sha for name,sha in manifest.items())
    sources={Path(__file__).resolve(),report,run.with_suffix('.log'),artifact.with_suffix('.log'),artifact/'manifest.json',artifact/'resource-full-descriptor.json'}
    pilot=ROOT/'ai/runs/resource-turn-runtime-outcomes-v2/pg-resource-turn-runtime-v1-whole-6p'
    pilot_result=read(pilot/'verified.json')
    assert pilot_result['verified'] and pilot_result['job_id']=='6ae20c1341e90535df77523a'
    assert pilot_result['review']['games']==24 and pilot_result['review']['audit']['counts']['rollout_caps']==0
    assert digest(pilot/'independent-audit/result.json')==pilot_result['review']['independent_audit_sha256']
    sources.update((pilot/'verified.json',pilot/'independent-audit/result.json',
        pilot.parent/'state.json',ROOT/'ai/runs/resource-turn-runtime-outcomes-v2-second.log'))
    sources.update(p for p in run.rglob('*') if p.is_file())
    sources.update(p for p in (artifact/'policy').iterdir() if p.is_file())
    sources.update(ROOT/name for name in assessment['code_hashes'])
    for p in (artifact/'policy').iterdir():
        if p.is_file():
            source=ROOT/'ai/strong'/p.name;assert digest(source)==digest(p);sources.add(source)
    sources.update(ROOT/'ai/strong'/name for name in (
        'resource-turn-boundary-evidence-v2.json','resource-turn-boundary-results-v2.json',
        'resource-turn-runtime-source-v1.json','resource-runtime-collection-evidence-v2.json',
        'resource-turn-full-integration-evidence-v2.json','resource-turn-full-integration-results-v2.json',
        'resource-turn-full-integration-evidence-v1.json','resource-replanning-development-complete-evidence-v1.json',
        'resource-replanning-job-source-v1.json','policy_iteration_evidence_archive.py','strategic_collection.py'))
    sources.update(ROOT/'ai'/name for name in ('RESOURCE-TURN-BOUNDARY-POLICY-2026-10-28.md',
        'RESOURCE-TURN-BOUNDARY-2026-10-28.md','RESOURCE-TURN-CORRECTED-INTEGRATION-2026-10-28.md','RESUME.md'))
    api=HfApi();repo='coyotte508/powergrid-ai-germany-v1'
    assert api.model_info(repo).private and not api.file_exists(repo,'archives/'+NAME+'.tgz')
    OUT.mkdir();hashes={}
    for source in sorted(sources):
        assert source.is_file() and not source.is_symlink()
        name=str(source.relative_to(ROOT));target=OUT/name;target.parent.mkdir(parents=True,exist_ok=True)
        before=digest(source);shutil.copy2(source,target);assert digest(target)==before;hashes[name]=before
    note=OUT/'README.md'
    note.write_text('''# Corrected resource phase-boundary policy

Separately pinned v4 artifact with v2 boundary-aware sampling receipts. Contains
exact policy sources, manifests, historical first-search parity, four actual
false-commit focal resource turns and lifecycle search receipts. Original model,
runtime and raw game archives are referenced through immutable descriptors.

These are engineering checks, not independent strength data. No new complete
games, HF jobs, gradients, final seeds, qualification or deployment. Full-game
runtime admission remains necessary. Original failed pilots remain failed.
''');hashes[note.name]=digest(note);save(OUT/'manifest.json',hashes)
    intent={'created_at':datetime.now(timezone.utc).isoformat(),'stage':'prepared_for_upload',
        'archive_path':'archives/'+NAME+'.tgz','manifest_sha256':digest(OUT/'manifest.json')}
    save(OUT.with_suffix('.intent.json'),intent)
    print(json.dumps({'stage':'uploading','files':len(hashes)+1}),flush=True)
    archive=upload_evidence(OUT)
    save(RESULT,{'status':'boundary_corrected_policy_integration_verified_not_runtime_or_strength_qualified',
        'assessment_sha256':digest(run/'assessment.json'),'descriptor_sha256':assessment['descriptor_sha256'],
        'artifact_manifest_sha256':assessment['manifest_sha256'],'exceptional_resource_turns':4,'counts':counts,
        'newly_collected_original_pilot':{'job_id':pilot_result['job_id'],'games':24,
            'review':pilot_result['review'],'raw_archive':pilot_result['evidence'],
            'verified_receipt_sha256':digest(pilot/'verified.json')},
        'new_hf_jobs':0,'new_full_game_trajectories':0,'gradients':False,
        'qualification_eligible':False,'reserved_final_seeds_used':False,'archive':archive})
    OUT.with_suffix('.intent.json').write_text(json.dumps({**intent,'stage':'uploaded_download_verified',
        'archive':archive,'descriptor_sha256':digest(RESULT)},indent=2)+'\n')
    print(json.dumps(archive),flush=True)


if __name__=='__main__':main()
