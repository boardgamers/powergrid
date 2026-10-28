"""Archive sampling probes, preserved failures and corrected model-input checks."""
from datetime import datetime,timezone
import json
from pathlib import Path
import shutil

from huggingface_hub import HfApi
from policy_iteration_evidence_archive import upload_evidence
from public_policy_development_job_v1 import read,digest

ROOT=Path(__file__).resolve().parents[2]
NAME='resource-public-state-checks-evidence-v1'
OUT=ROOT/'ai/runs'/NAME
RESULT=ROOT/'ai/strong'/(NAME+'.json')


def save(path,value):
    with path.open('x') as stream:json.dump(value,stream,indent=2,allow_nan=False);stream.write('\n')


def main():
    for path in (OUT,OUT.with_suffix('.tgz'),OUT.with_suffix('.intent.json'),RESULT):
        assert not path.exists(),'Inspect existing archive intent/outcome before retry'
    sources={Path(__file__).resolve()};assessments={}
    for name,report_name in (('resource-sampling-anchor-v1-validated','resource-sampling-anchor-results-v1'),
                             ('resource-model-turn-v2','resource-model-turn-results-v2')):
        folder=ROOT/'ai/runs'/name;assessment=read(folder/'assessment.json');report=ROOT/'ai/strong'/(report_name+'.json')
        assert assessment['passed'] and read(report)['assessment_sha256']==digest(folder/'assessment.json')
        assert assessment['new_hf_jobs']==assessment['rollouts']==assessment['new_full_game_trajectories']==0
        for mapping in ('input_hashes','code_hashes'):
            assert all(digest(ROOT/p)==sha for p,sha in assessment[mapping].items())
        assert all(digest(folder/p)==sha for p,sha in assessment['output_hashes'].items())
        sources.update(ROOT/p for p in assessment['code_hashes']);sources.add(report)
        sources.update(p for p in folder.rglob('*') if p.is_file());sources.add(folder.with_suffix('.log'))
        assessments[name]={'assessment_sha256':digest(folder/'assessment.json'),'counts':assessment['counts']}
    for name in ('resource-sampling-anchor-v1','resource-sampling-anchor-v1-checked'):
        folder=ROOT/'ai/runs'/name;design=read(folder/'design.json')
        assert read(folder/'failure.json')['completed_turn_checks']==0
        assert all(digest(folder/'failed-probe-source'/Path(p).name)==sha for p,sha in design['code_hashes'].items())
        sources.update(p for p in folder.rglob('*') if p.is_file());sources.add(folder.with_suffix('.log'))
    sources.update(ROOT/'ai/strong'/n for n in ('resource-turn-full-integration-evidence-v1.json',
        'resource-turn-full-integration-results-v1.json','resource-replanning-job-source-v1.json',
        'resource-replanning-development-complete-evidence-v1.json','policy-iteration-development-pins-v2/frozen-1.json',
        'policy_iteration_evidence_archive.py','strategic_collection.py'))
    sources.update(ROOT/'ai'/n for n in ('RESOURCE-SAMPLING-AND-PUBLIC-STATE-2026-10-28.md',
        'RESOURCE-TURN-FULL-EVALUATOR-2026-10-28.md','RESOURCE-TURN-PUBLIC-POLICY-2026-10-28.md','RESUME.md'))
    assert HfApi().model_info('coyotte508/powergrid-ai-germany-v1').private
    OUT.mkdir();manifest={}
    for source in sorted(sources):
        assert source.is_file() and not source.is_symlink()
        name=str(source.relative_to(ROOT));target=OUT/name;target.parent.mkdir(parents=True,exist_ok=True)
        before=digest(source);shutil.copy2(source,target);assert digest(target)==before;manifest[name]=before
    note=OUT/'README.md'
    note.write_text('''# Resource sampling and public-state checks

Contains sampling-only probes, both initial failed probe sources/logs, the
separate corrected model-turn primitive, actual frozen-model traces and
independent public-input checks against complete sampled states. Original
runtime/model/recorded roots are referenced by included immutable descriptors
and input hashes instead of copied or rerun. All 20 selected roots are round 1,
step 1, economic opponents, seat zero across counts 2–6 and all four rules.

Stable latent sampling is feasible on these turns. The historical public model
turn lost cardsLeft/nextCardWeak after purchases; the corrected primitive
preserves these facts. Its 20 model plans were unchanged. These engineering
checks are not new full games, causal strength evidence or qualification.
The corrected primitive still needs full-game artifact integration, later-round
validation and a separate persistent stable-sampling control before a new study.
''');manifest[note.name]=digest(note)
    save(OUT/'manifest.json',manifest)
    intent={'created_at':datetime.now(timezone.utc).isoformat(),'stage':'prepared_for_upload',
        'archive_path':'archives/'+NAME+'.tgz','manifest_sha256':digest(OUT/'manifest.json')}
    save(OUT.with_suffix('.intent.json'),intent)
    print(json.dumps({'stage':'uploading','files':len(manifest)+1}),flush=True)
    archive=upload_evidence(OUT)
    save(RESULT,{'status':'sampling_and_corrected_public_inputs_verified_on_20_recorded_turns_not_strength_tested',
        'assessments':assessments,'archive':archive,'new_hf_jobs':0,'new_full_game_trajectories':0,
        'rollouts':0,'gradients':False,'qualification_eligible':False,'reserved_final_seeds_used':False})
    OUT.with_suffix('.intent.json').write_text(json.dumps({**intent,'stage':'uploaded_download_verified',
        'archive':archive,'descriptor_sha256':digest(RESULT)},indent=2)+'\n')
    print(json.dumps(archive),flush=True)


if __name__=='__main__':main()
