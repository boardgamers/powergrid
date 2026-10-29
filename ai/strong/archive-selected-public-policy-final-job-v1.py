"""Archive final-transport validation, referencing the unchanged runtime source."""
from datetime import datetime,timezone
import json
from pathlib import Path

from huggingface_hub import HfApi
from policy_iteration_evidence_archive import upload_evidence
from public_policy_development_job_v1 import read,digest

ROOT=Path(__file__).resolve().parents[2]
NAME='selected-public-policy-final-job-evidence-v1'
OUT=ROOT/'ai/runs'/NAME
RESULT=ROOT/'ai/strong'/(NAME+'.json')


def save(path,value):
    with path.open('x') as f:json.dump(value,f,indent=2,allow_nan=False);f.write('\n')


def main():
    assert all(not p.exists() for p in (OUT,OUT.with_suffix('.tgz'),OUT.with_suffix('.intent.json'),RESULT)), 'Inspect previous archive outcome'
    report_path=ROOT/'ai/strong/selected-public-policy-final-job-preflight-v2.json';report=read(report_path)
    assert report['passed'] and report['tests']==12 and len(report['real_artifact_validation_cases'])==5
    assert report['new_games']==report['new_policy_calls']==report['new_hf_jobs']==0
    assert not report['candidate_selected'] and not report['reserved_final_seeds_used']
    assert all(digest(ROOT/n)==h for n,h in report['input_hashes'].items())
    sources={ROOT/n for n in report['input_hashes']}
    sources.update((Path(__file__).resolve(),report_path,
        ROOT/'ai/SELECTED-PUBLIC-POLICY-FINAL-JOB-2026-10-29.md',
        ROOT/'ai/strong/policy_iteration_evidence_archive.py',ROOT/'ai/strong/strategic_collection.py'))
    for version in (1,2):
        run=ROOT/f'ai/runs/selected-public-policy-final-job-preflight-v{version}'
        sources.add(ROOT/f'ai/runs/selected-public-policy-final-job-preflight-v{version}-first.log')
        for p in run.rglob('*'):
            if p.is_file() and 'artifact' not in p.relative_to(run).parts:sources.add(p)
    for case in report['real_artifact_validation_cases']:
        folder=ROOT/case['original_case_directory'] if case.get('reused_original_validation') else ROOT/'ai/runs/selected-public-policy-final-job-preflight-v2'/case['case']
        assert digest(folder/'validation.log')==case['validation_log_sha256']
        assert digest(folder/'source/source-manifest.json')==case['source_manifest_sha256']
        assert all(digest(folder/'source'/n)==h for n,h in read(folder/'source/source-manifest.json').items())
        assert not (folder/'must-not-exist').exists()
    repo='coyotte508/powergrid-ai-germany-v1';api=HfApi()
    assert api.model_info(repo).private and not api.file_exists(repo,'archives/'+NAME+'.tgz')
    OUT.mkdir();manifest={}
    for path in sorted(sources):
        assert path.is_file() and not path.is_symlink()
        name=str(path.relative_to(ROOT));before=digest(path);target=OUT/name
        target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(path.read_bytes())
        assert digest(target)==before==digest(path);manifest[name]=before
    recovery={'source':report['reference_source'],'repo_type':'dataset','artifact_subdirectory':'artifact',
        'runtime_manifest_sha256':report['identity']['runtimeManifestSha256'],
        'instructions':'Restore the immutable confirmation source by revision and hash. For each validation source, copy its unchanged artifact directory and the archived external wrapper/controls; verify source-manifest.json. The selected/launch documents here are synthetic validation fixtures, never real admission. Do not execute reserved games or repeat preflights on restore.'}
    save(OUT/'runtime-reference.json',recovery);manifest['runtime-reference.json']=digest(OUT/'runtime-reference.json')
    save(OUT/'manifest.json',manifest)
    intent={'created_at':datetime.now(timezone.utc).isoformat(),'stage':'prepared_for_upload','manifest_sha256':digest(OUT/'manifest.json')}
    save(OUT.with_suffix('.intent.json'),intent)
    archive=upload_evidence(OUT)
    save(RESULT,{'passed':True,'tests':12,'real_artifact_validation_cases':5,
        'preflight_report':str(report_path.relative_to(ROOT)),'preflight_sha256':digest(report_path),
        'identity':report['identity'],'preserved_first_harness_failure':True,
        'new_games':0,'new_hf_jobs':0,'new_policy_calls':0,'candidate_selected':False,
        'qualified':False,'reserved_final_seeds_used':False,'archive':archive})
    OUT.with_suffix('.intent.json').write_text(json.dumps({**intent,'stage':'uploaded_download_verified',
        'archive':archive,'descriptor_sha256':digest(RESULT)},indent=2)+'\n')
    print(json.dumps(archive),flush=True)


if __name__=='__main__':main()
