"""Archive the exact unlaunched v4 job package and its replay/admission checks."""
from datetime import datetime,timezone
import json
from pathlib import Path
import shutil

from huggingface_hub import HfApi
from policy_iteration_evidence_archive import upload_evidence
from public_policy_development_job_v1 import read,digest

ROOT=Path(__file__).resolve().parents[2]
NAME='resource-runtime-preflight-evidence-v2'
OUT=ROOT/'ai/runs'/NAME
RESULT=ROOT/'ai/strong'/(NAME+'.json')


def save(path,value):
    with path.open('x') as stream:
        json.dump(value,stream,indent=2,allow_nan=False);stream.write('\n')


def main():
    for p in (OUT,OUT.with_suffix('.tgz'),OUT.with_suffix('.intent.json'),RESULT):
        assert not p.exists(),'Inspect existing archive intent/outcome before retry'
    prep=ROOT/'ai/runs/resource-turn-runtime-prepared-v2';source=prep/'source'
    prepared=read(prep/'prepared.json');proof=read(prep/'verified.json')
    checks=ROOT/'ai/runs/resource-runtime-admission-checks-v2';audit=read(checks/'assessment.json')
    assert proof['passed'] and proof['jobs_dry_validated']==3 and proof['recorded_games_replayed']==8
    assert proof['exact_decisions']==1360 and proof['unadmitted_executions_rejected']==2
    assert proof['hf_admission_created'] is False and audit['actual_hf_admission_created'] is False
    assert audit['passed'] and audit['checks']==12 and audit['synthetic_fixtures_only']
    assert proof['prepared_sha256']==digest(prep/'prepared.json')
    assert proof['source_manifest_sha256']==prepared['source_manifest_sha256']==audit['source_manifest_sha256']==digest(source/'source-manifest.json')
    pins=read(source/'source-manifest.json')
    assert all(digest(source/n)==v for n,v in pins.items())
    assert set(pins)|{'source-manifest.json'}=={str(p.relative_to(source)) for p in source.rglob('*') if p.is_file()}
    assert len(pins)==1510
    assert proof['control_manifest_sha256']==digest(prep/'local-control/manifest.json')
    control=read(prep/'local-control/manifest.json')
    assert all(digest(prep/'local-control'/n)==v for n,v in control.items())
    assert all(digest(checks/n)==v for n,v in audit['output_hashes'].items())
    assert prepared['preparer_sha256']==digest(ROOT/'ai/strong/prepare-resource-turn-runtime-v2.py')
    assert prepared['entry_sha256']==digest(ROOT/'ai/strong/resource_turn_runtime_job_v2.py')
    assert audit['checker_sha256']==digest(ROOT/'ai/strong/check-resource-runtime-admission-v2.py')
    sources={Path(__file__).resolve()}
    for directory in (prep,checks,ROOT/'ai/runs/resource-turn-runtime-prepared-v2-initial'):
        sources.update(p for p in directory.rglob('*') if p.is_file())
    for name in ('resource-turn-runtime-prepared-v2-prepare-recovered.log',
                 'resource-turn-runtime-prepared-v2-verify.log','resource-runtime-admission-checks-v2.log'):
        sources.add(ROOT/'ai/runs'/name)
    sources.update(ROOT/'ai/strong'/n for n in ('prepare-resource-turn-runtime-v2.py','resource_turn_runtime_job_v2.py',
        'check-resource-runtime-admission-v2.py','resource-turn-runtime-protocol-v2.json',
        'resource-turn-boundary-policy-evidence-v2.json','resource-turn-runtime-source-v1.json',
        'policy_iteration_evidence_archive.py','strategic_collection.py'))
    sources.update(ROOT/'ai'/n for n in ('RESOURCE-RUNTIME-PREFLIGHT-2026-10-28.md','RESUME.md'))
    api=HfApi();repo='coyotte508/powergrid-ai-germany-v1'
    assert api.model_info(repo).private and not api.file_exists(repo,'archives/'+NAME+'.tgz')
    OUT.mkdir();hashes={}
    for path in sorted(sources):
        assert path.is_file() and not path.is_symlink()
        name=str(path.relative_to(ROOT));target=OUT/name;target.parent.mkdir(parents=True,exist_ok=True)
        sha=digest(path);shutil.copy2(path,target);assert digest(target)==sha;hashes[name]=sha
    save(OUT/'manifest.json',hashes)
    intent={'created_at':datetime.now(timezone.utc).isoformat(),'stage':'prepared_for_upload',
        'archive_path':'archives/'+NAME+'.tgz','manifest_sha256':digest(OUT/'manifest.json')}
    save(OUT.with_suffix('.intent.json'),intent)
    print(json.dumps({'stage':'uploading','files':len(hashes)+1}),flush=True)
    archive=upload_evidence(OUT)
    save(RESULT,{'status':'v4_runtime_package_replay_verified_not_admitted_or_launched',
        'source_manifest_sha256':prepared['source_manifest_sha256'],'prepared_sha256':digest(prep/'prepared.json'),
        'verification_sha256':digest(prep/'verified.json'),'admission_checks_sha256':digest(checks/'assessment.json'),
        'recorded_games':8,'exact_decisions':1360,'admission_checks':12,'unadmitted_executions_rejected':2,
        'planned_hf_jobs':2,'planned_runtime_games':32,'actual_hf_admission_created':False,
        'new_hf_jobs':0,'new_full_game_trajectories':0,'new_gradients':0,
        'qualification_eligible':False,'reserved_final_seeds_used':False,'archive':archive})
    OUT.with_suffix('.intent.json').write_text(json.dumps({**intent,'stage':'uploaded_download_verified',
        'archive':archive,'descriptor_sha256':digest(RESULT)},indent=2)+'\n')
    print(json.dumps(archive),flush=True)


if __name__=='__main__':main()
