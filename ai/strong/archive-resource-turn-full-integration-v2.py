"""One-shot archive of corrected full-game and intermediate-input evidence."""
from datetime import datetime,timezone
import json
from pathlib import Path
import shutil

from huggingface_hub import HfApi
from policy_iteration_evidence_archive import upload_evidence
from public_policy_development_job_v1 import read,digest

ROOT=Path(__file__).resolve().parents[2]
NAME='resource-turn-full-integration-evidence-v2'
OUT=ROOT/'ai/runs'/NAME
RESULT=ROOT/'ai/strong'/(NAME+'.json')


def save(path,value):
    with path.open('x') as stream:json.dump(value,stream,indent=2,allow_nan=False);stream.write('\n')


def main():
    for p in (OUT,OUT.with_suffix('.tgz'),OUT.with_suffix('.intent.json'),RESULT):
        assert not p.exists(),'Inspect prior archive intent/outcome before retrying'
    run=ROOT/'ai/runs/resource-turn-full-integration-v2';assessment=read(run/'assessment.json')
    report=ROOT/'ai/strong/resource-turn-full-integration-results-v2.json'
    assert assessment['passed'] and read(report)['assessment_sha256']==digest(run/'assessment.json')
    assert assessment['actual_inference_replays']==33 and assessment['groups_audited']==7
    assert assessment['public_input_turns']==334 and assessment['private_feature_checks']==12888
    assert assessment['search_counts']['rollouts']==96 and assessment['search_counts']['rollout_caps']==0
    for k in ('code_hashes','input_hashes'):
        assert all(digest(ROOT/p)==sha for p,sha in assessment[k].items())
    assert all(digest(run/p)==sha for p,sha in assessment['output_hashes'].items())
    artifact=Path(assessment['artifact']);manifest=read(artifact/'manifest.json')
    assert digest(artifact/'manifest.json')==assessment['manifest_sha256']
    assert digest(artifact/'resource-full-descriptor.json')==assessment['descriptor_sha256']
    assert all(digest(artifact/p)==sha for p,sha in manifest.items())
    sources={Path(__file__).resolve(),report,run.with_suffix('.log'),artifact/'manifest.json',artifact/'resource-full-descriptor.json'}
    sources.update(p for p in run.rglob('*') if p.is_file())
    sources.update(p for p in (artifact/'policy').iterdir() if p.is_file())
    sources.update(ROOT/p for p in assessment['code_hashes'])
    sources.update(ROOT/'ai/strong'/p.name for p in (artifact/'policy').iterdir() if p.is_file())
    sources.update(ROOT/'ai/strong'/n for n in ('resource-public-state-checks-evidence-v1.json',
        'resource-turn-full-integration-evidence-v1.json','resource-replanning-job-source-v1.json',
        'resource-replanning-development-complete-evidence-v1.json','policy-iteration-development-pins-v2/frozen-1.json',
        'policy_iteration_evidence_archive.py','strategic_collection.py'))
    sources.update(ROOT/'ai'/n for n in ('RESOURCE-TURN-CORRECTED-INTEGRATION-2026-10-28.md',
        'RESOURCE-SAMPLING-AND-PUBLIC-STATE-2026-10-28.md','RESOURCE-TURN-FULL-EVALUATOR-2026-10-28.md',
        'RESOURCE-TURN-PUBLIC-POLICY-2026-10-28.md','RESUME.md'))
    assert HfApi().model_info('coyotte508/powergrid-ai-germany-v1').private
    OUT.mkdir();hashes={}
    for source in sorted(sources):
        assert source.is_file() and not source.is_symlink()
        name=str(source.relative_to(ROOT));target=OUT/name;target.parent.mkdir(parents=True,exist_ok=True)
        before=digest(source);shutil.copy2(source,target);assert digest(target)==before;hashes[name]=before
    note=OUT/'README.md'
    note.write_text('''# Corrected public resource turns: full-game artifact v2

Contains adapter sources and package manifests, actual inference replays of 33
recorded games, seven independent receipt audits, 12,888 full-state feature/menu
checks over 334 resource turns, and four corrected search-mode checks (96 uncapped
continuations). Original source, model and game archives are referenced by included
immutable descriptors. Rebuild only from those exact inputs and manifests.

The v1 artifact and historical receipts remain unchanged. V2 separates corrected
atomic search from corrected whole-turn commitment; the historical atomic baseline
is an explicit control. Stable within-turn sampling is not implemented. No fresh
strength games, HF jobs, gradients, final seeds, qualification or deployment.
''');hashes[note.name]=digest(note);save(OUT/'manifest.json',hashes)
    intent={'created_at':datetime.now(timezone.utc).isoformat(),'stage':'prepared_for_upload',
        'archive_path':'archives/'+NAME+'.tgz','manifest_sha256':digest(OUT/'manifest.json')}
    save(OUT.with_suffix('.intent.json'),intent)
    print(json.dumps({'stage':'uploading','files':len(hashes)+1}),flush=True)
    archive=upload_evidence(OUT)
    save(RESULT,{'status':'corrected_full_game_resource_integration_verified_not_strength_tested',
        'assessment_sha256':digest(run/'assessment.json'),'descriptor_sha256':assessment['descriptor_sha256'],
        'artifact_manifest_sha256':assessment['manifest_sha256'],'actual_inference_replays':33,
        'resource_turns':334,'intermediate_model_decisions':1611,'private_feature_checks':12888,
        'search_mode_checks':4,'search_rollouts':96,'rollout_caps':0,
        'new_hf_jobs':0,'new_full_game_trajectories':0,'gradients':False,
        'qualification_eligible':False,'reserved_final_seeds_used':False,'archive':archive})
    OUT.with_suffix('.intent.json').write_text(json.dumps({**intent,'stage':'uploaded_download_verified',
        'archive':archive,'descriptor_sha256':digest(RESULT)},indent=2)+'\n')
    print(json.dumps(archive),flush=True)


if __name__=='__main__':main()
