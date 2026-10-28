"""Archive the isolated engine diagnostic; never rebuild or rerun it."""
from datetime import datetime,timezone
import json
from pathlib import Path

from huggingface_hub import HfApi
from policy_iteration_evidence_archive import upload_evidence
from public_policy_development_job_v1 import digest,read

ROOT=Path(__file__).resolve().parents[2]
NAME='current-engine-compatibility-evidence-v1'
OUT=ROOT/'ai/runs'/NAME
RESULT=ROOT/'ai/strong'/(NAME+'.json')
RUN=ROOT/'ai/runs/current-engine-compatibility-v1'


def save(path,value):
    with path.open('x') as stream:json.dump(value,stream,indent=2,allow_nan=False);stream.write('\n')


def main():
    for p in (OUT,OUT.with_suffix('.tgz'),OUT.with_suffix('.intent.json'),RESULT):
        assert not p.exists(),'Inspect prior archive intent/outcome before retrying'
    report_path=ROOT/'ai/strong/current-engine-compatibility-results-v1.json';report=read(report_path)
    design=read(RUN/'design.json');build=read(RUN/'build.json')
    assert report['recorded_games']==33 and report['requests']==3443
    assert report['old_menu_mismatches']==report['changed_menus']==report['changed_recorded_actions']==0
    assert report['synthetic_discount_checks']==10 and report['synthetic_auto_pass_checks']==20
    assert report['setup_checks']==20 and report['setup_differences']==0
    assert report['new_hf_jobs']==report['new_inference']==report['new_full_games']==0
    assert report['qualification_eligible'] is report['reserved_final_seeds_used'] is False
    assert report['design_sha256']==build['design_sha256']==digest(RUN/'design.json')
    assert report['build_sha256']==digest(RUN/'build.json')
    assert report['details_sha256']==digest(RUN/'differences.jsonl')
    assert all(digest(ROOT/n)==sha for n,sha in design['recorded_inputs'].items())
    assert all(digest(RUN/'source'/n)==sha for n,sha in design['source_files'].items())
    assert all(digest(RUN/'source/engine'/n)==sha for n,sha in build['compiled_files'].items())
    assert digest(RUN/'typescript-4.3.5.tgz')==design['typescript_sha256']
    assert digest(RUN/'engine-source.tar')==design['source_archive_sha256']
    assert digest(ROOT/'ai/strong/check-current-engine-compatibility-v1.py')==design['python_checker_sha256']
    assert digest(ROOT/'ai/strong/check-current-engine-compatibility-v1.cjs')==design['node_checker_sha256']
    artifact=ROOT/'ai/runs/resource-turn-full-artifact-v4'
    assert digest(artifact/'manifest.json')==design['frozen_artifact_manifest_sha256']
    assert all(digest(artifact/n)==sha for n,sha in read(artifact/'manifest.json').items())
    sources={Path(__file__).resolve(),report_path}
    for directory in (RUN,ROOT/'ai/runs/current-engine-compatibility-v1-initial'):
        sources.update(p for p in directory.rglob('*') if p.is_file()
            and 'compiler' not in p.relative_to(directory).parts and 'node_modules' not in p.relative_to(directory).parts)
    sources.update(ROOT/n for n in ('ai/strong/check-current-engine-compatibility-v1.py',
        'ai/strong/check-current-engine-compatibility-v1.cjs','ai/strong/resource-turn-full-integration-evidence-v2.json',
        'ai/strong/resource-runtime-preflight-evidence-v2.json','ai/strong/resource-turn-runtime-source-v1.json',
        'ai/strong/policy_iteration_evidence_archive.py','ai/strong/strategic_collection.py',
        'ai/runs/current-engine-compatibility-v1-prepare.log','ai/runs/current-engine-compatibility-v1-check.log',
        'ai/CURRENT-ENGINE-COMPATIBILITY-2026-10-28.md','ai/RESUME.md',
        'ai/runs/conservative-auction-development-attempts-coordinator-v1/state.json'))
    api=HfApi();repo='coyotte508/powergrid-ai-germany-v1'
    assert api.model_info(repo).private and not api.file_exists(repo,'archives/'+NAME+'.tgz')
    OUT.mkdir();hashes={}
    for p in sorted(sources):
        assert p.is_file() and not p.is_symlink()
        name=str(p.relative_to(ROOT));target=OUT/name;target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes(p.read_bytes());hashes[name]=digest(target)
    save(OUT/'manifest.json',hashes)
    intent={'created_at':datetime.now(timezone.utc).isoformat(),'stage':'prepared_for_upload',
        'archive_path':'archives/'+NAME+'.tgz','manifest_sha256':digest(OUT/'manifest.json')}
    save(OUT.with_suffix('.intent.json'),intent)
    print(json.dumps({'stage':'uploading','files':len(hashes)+1}),flush=True)
    archive=upload_evidence(OUT)
    save(RESULT,{'status':'saved_state_menus_match_current_engine_with_confirmed_discount_edge_difference',
        'report_sha256':digest(report_path),'design_sha256':report['design_sha256'],'build_sha256':report['build_sha256'],
        'current_engine_commit':design['current_engine_commit'],'current_engine_version':design['current_engine_version'],
        'recorded_games':33,'recorded_requests':3443,'changed_recorded_menus':0,
        'synthetic_discount_checks':10,'synthetic_auto_pass_checks':20,'setup_checks':20,
        'full_transition_parity_verified':False,'typecheck':False,'new_hf_jobs':0,'new_inference':0,
        'new_full_games':0,'new_gradients':0,'qualification_eligible':False,'reserved_final_seeds_used':False,
        'recorded_input_archive':design['recorded_evidence'],'archive':archive})
    OUT.with_suffix('.intent.json').write_text(json.dumps({**intent,'stage':'uploaded_download_verified',
        'archive':archive,'descriptor_sha256':digest(RESULT)},indent=2)+'\n')
    print(json.dumps(archive),flush=True)


if __name__=='__main__':main()
