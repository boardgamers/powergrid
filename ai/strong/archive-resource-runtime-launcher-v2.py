"""Archive corrected-runtime launch controls and offline evidence, not a launch."""
from datetime import datetime,timezone
import json
from pathlib import Path
import shutil

from huggingface_hub import HfApi
from policy_iteration_evidence_archive import upload_evidence
from public_policy_development_job_v1 import digest,read

ROOT=Path(__file__).resolve().parents[2]
NAME='resource-runtime-launcher-evidence-v2'
OUT=ROOT/'ai/runs'/NAME
RESULT=ROOT/'ai/strong'/(NAME+'.json')


def save(path,value):
    with path.open('x') as stream:json.dump(value,stream,indent=2,allow_nan=False);stream.write('\n')


def main():
    for path in (OUT,OUT.with_suffix('.tgz'),OUT.with_suffix('.intent.json'),RESULT):
        assert not path.exists(), 'Inspect existing archive intent/outcome before any retry'
    test=ROOT/'ai/runs/resource-turn-runtime-launcher-tests-v2';proof=read(test/'assessment.json')
    assert proof['passed'] and proof['tests']==26
    assert proof['network_calls']==proof['new_hf_jobs']==proof['new_inference']==proof['new_full_game_trajectories']==0
    assert proof['actual_admission_created'] is False
    assert all(digest(ROOT/n)==v for n,v in proof['code_hashes'].items())
    assert all(digest(test/Path(n).name)==v for n,v in proof['code_hashes'].items())
    for name in ('resource-turn-runtime-admission-v2.json','resource-turn-runtime-source-v2.json'):
        assert not (ROOT/'ai/strong'/name).exists(), 'Archive must describe actual unlaunched state'
    assert not (ROOT/'ai/runs/resource-turn-runtime-hf-v2').exists()
    prepared=read(ROOT/'ai/runs/resource-turn-runtime-prepared-v2/prepared.json')
    preflight=read(ROOT/'ai/strong/resource-runtime-preflight-evidence-v2.json')
    assert preflight['source_manifest_sha256']==prepared['source_manifest_sha256']
    assert preflight['archive']['remote_archive_verified']
    sources={Path(__file__).resolve(),*(ROOT/n for n in proof['code_hashes'])}
    sources.update(p for p in test.rglob('*') if p.is_file())
    sources.update(ROOT/name for name in (
        'ai/runs/resource-turn-runtime-launcher-tests-v2.log',
        'ai/runs/resource-turn-runtime-outcomes-v2/state.json',
        'ai/runs/resource-turn-runtime-outcomes-v2-fifth.log',
        'ai/runs/conservative-auction-development-attempts-coordinator-v1/state.json',
        'ai/runs/resource-turn-runtime-prepared-v2/prepared.json',
        'ai/runs/resource-turn-runtime-prepared-v2/verified.json',
        'ai/strong/resource-turn-runtime-source-v1.json',
        'ai/strong/resource-turn-runtime-protocol-v2.json',
        'ai/strong/resource-runtime-preflight-evidence-v2.json',
        'ai/strong/resource-turn-boundary-policy-evidence-v2.json',
        'ai/strong/policy_iteration_evidence_archive.py','ai/strong/strategic_collection.py',
        'ai/RESOURCE-RUNTIME-LAUNCHER-2026-10-28.md','ai/RESUME.md'))
    api=HfApi();repo='coyotte508/powergrid-ai-germany-v1'
    assert api.model_info(repo).private and not api.file_exists(repo,'archives/'+NAME+'.tgz')
    OUT.mkdir();hashes={}
    for path in sorted(sources):
        assert path.is_file() and not path.is_symlink()
        name=str(path.relative_to(ROOT));target=OUT/name;target.parent.mkdir(parents=True,exist_ok=True)
        # Read once: the auction owner can atomically update its status while
        # this evidence snapshot is being built. Preserve the exact observed bytes.
        raw=path.read_bytes();target.write_bytes(raw);hashes[name]=digest(target)
    save(OUT/'manifest.json',hashes)
    intent={'created_at':datetime.now(timezone.utc).isoformat(),'stage':'prepared_for_upload',
        'archive_path':'archives/'+NAME+'.tgz','manifest_sha256':digest(OUT/'manifest.json')}
    save(OUT.with_suffix('.intent.json'),intent)
    print(json.dumps({'stage':'uploading','files':len(hashes)+1}),flush=True)
    archive=upload_evidence(OUT)
    save(RESULT,{'status':'corrected_runtime_launcher_verified_not_admitted_or_launched',
        'launcher_sha256':digest(ROOT/'ai/strong/launch-resource-turn-runtime-v2.py'),
        'test_assessment_sha256':digest(test/'assessment.json'),'tests':26,
        'source_manifest_sha256':prepared['source_manifest_sha256'],'prepared_package_archive':preflight['archive'],
        'actual_admission_created':False,'execution_source_uploaded':False,'new_hf_jobs':0,
        'new_full_game_trajectories':0,'new_gradients':0,'qualification_eligible':False,
        'reserved_final_seeds_used':False,'archive':archive})
    OUT.with_suffix('.intent.json').write_text(json.dumps({**intent,'stage':'uploaded_download_verified',
        'archive':archive,'descriptor_sha256':digest(RESULT)},indent=2)+'\n')
    print(json.dumps(archive),flush=True)


if __name__=='__main__':main()
