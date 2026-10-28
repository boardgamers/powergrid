"""Archive the integrated stable-sampling policy and actual search receipts once."""
from datetime import datetime,timezone
import json
from pathlib import Path
import shutil

from huggingface_hub import HfApi
from policy_iteration_evidence_archive import upload_evidence
from public_policy_development_job_v1 import read,digest

ROOT=Path(__file__).resolve().parents[2]
NAME='resource-turn-anchored-policy-evidence-v1'
OUT=ROOT/'ai/runs'/NAME
RESULT=ROOT/'ai/strong'/(NAME+'.json')


def save(path,value):
    with path.open('x') as stream:json.dump(value,stream,indent=2,allow_nan=False);stream.write('\n')


def main():
    for p in (OUT,OUT.with_suffix('.tgz'),OUT.with_suffix('.intent.json'),RESULT):
        assert not p.exists(),'Inspect prior archive intent/outcome before retrying'
    run=ROOT/'ai/runs/resource-turn-anchored-policy-v1';assessment=read(run/'assessment.json')
    report=ROOT/'ai/strong/resource-turn-anchored-policy-results-v1.json'
    assert assessment['passed'] and read(report)['assessment_sha256']==digest(run/'assessment.json')
    counts=assessment['counts']
    assert assessment['resource_turns']==counts['first_searches_matching_history']==20
    assert counts['lifecycle_replays']==6 and counts['invalid_history_errors']==2
    assert counts['tampered_receipts_rejected']==80 and counts['rollout_caps']==0
    assert assessment['new_hf_jobs']==assessment['new_full_game_trajectories']==0
    for key in ('code_hashes','input_hashes'):
        assert all(digest(ROOT/name)==sha for name,sha in assessment[key].items())
    assert all(digest(run/name)==sha for name,sha in assessment['output_hashes'].items())
    artifact=Path(assessment['artifact']);manifest=read(artifact/'manifest.json')
    assert digest(artifact/'manifest.json')==assessment['manifest_sha256']
    assert digest(artifact/'resource-full-descriptor.json')==assessment['descriptor_sha256']
    assert all(digest(artifact/name)==sha for name,sha in manifest.items())
    sources={Path(__file__).resolve(),report,run.with_suffix('.log'),artifact/'manifest.json',artifact/'resource-full-descriptor.json'}
    sources.update(p for p in run.rglob('*') if p.is_file())
    sources.update(p for p in (artifact/'policy').iterdir() if p.is_file())
    sources.update(ROOT/name for name in assessment['code_hashes'])
    for p in (artifact/'policy').iterdir():
        if p.is_file():
            source=ROOT/'ai/strong'/p.name;assert digest(source)==digest(p);sources.add(source)
    sources.update(ROOT/'ai/strong'/name for name in (
        'resource-turn-anchor-evidence-v1.json','resource-turn-anchor-results-v1.json',
        'resource-turn-full-integration-evidence-v2.json','resource-turn-full-integration-results-v2.json',
        'resource-turn-full-integration-evidence-v1.json','resource-replanning-development-complete-evidence-v1.json',
        'resource-replanning-job-source-v1.json','policy_iteration_evidence_archive.py','strategic_collection.py'))
    sources.update(ROOT/'ai'/name for name in ('RESOURCE-TURN-ANCHORED-POLICY-2026-10-28.md',
        'RESOURCE-TURN-ANCHOR-2026-10-28.md','RESOURCE-TURN-CORRECTED-INTEGRATION-2026-10-28.md','RESUME.md'))
    assert HfApi().model_info('coyotte508/powergrid-ai-germany-v1').private
    OUT.mkdir();hashes={}
    for source in sorted(sources):
        assert source.is_file() and not source.is_symlink()
        name=str(source.relative_to(ROOT));target=OUT/name;target.parent.mkdir(parents=True,exist_ok=True)
        before=digest(source);shutil.copy2(source,target);assert digest(target)==before;hashes[name]=before
    note=OUT/'README.md'
    note.write_text('''# Integrated stable resource sampling policy

Separately pinned v3 artifact with corrected per-purchase, anchored per-purchase
and whole-turn controls. Contains exact adapters, manifests, first-search parity
and actual resource-turn/lifecycle search receipts. Original model/runtime/game
archives are referenced through immutable descriptors instead of repeated.

These are engineering continuations from 20 previously selected roots, not fresh
independent strength data. No new complete games, HF jobs, gradients, final seeds,
qualification or deployment. Full-game runtime admission remains necessary.
''');hashes[note.name]=digest(note);save(OUT/'manifest.json',hashes)
    intent={'created_at':datetime.now(timezone.utc).isoformat(),'stage':'prepared_for_upload',
        'archive_path':'archives/'+NAME+'.tgz','manifest_sha256':digest(OUT/'manifest.json')}
    save(OUT.with_suffix('.intent.json'),intent)
    print(json.dumps({'stage':'uploading','files':len(hashes)+1}),flush=True)
    archive=upload_evidence(OUT)
    save(RESULT,{'status':'anchored_resource_policy_integration_verified_not_strength_tested',
        'assessment_sha256':digest(run/'assessment.json'),'descriptor_sha256':assessment['descriptor_sha256'],
        'artifact_manifest_sha256':assessment['manifest_sha256'],'resource_turns':20,'counts':counts,
        'new_hf_jobs':0,'new_full_game_trajectories':0,'gradients':False,
        'qualification_eligible':False,'reserved_final_seeds_used':False,'archive':archive})
    OUT.with_suffix('.intent.json').write_text(json.dumps({**intent,'stage':'uploaded_download_verified',
        'archive':archive,'descriptor_sha256':digest(RESULT)},indent=2)+'\n')
    print(json.dumps(archive),flush=True)


if __name__=='__main__':main()
