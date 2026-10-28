"""Archive the failed runtime diagnosis and separately versioned boundary fix."""
from datetime import datetime,timezone
import json
from pathlib import Path
import shutil

from huggingface_hub import HfApi,hf_hub_download
from policy_iteration_evidence_archive import upload_evidence
from public_policy_development_job_v1 import read,digest

ROOT=Path(__file__).resolve().parents[2]
NAME='resource-turn-boundary-evidence-v2'
OUT=ROOT/'ai/runs'/NAME
RESULT=ROOT/'ai/strong'/(NAME+'.json')


def save(path,value):
    with path.open('x') as stream:
        json.dump(value,stream,indent=2,allow_nan=False);stream.write('\n')


def main():
    for path in (OUT,OUT.with_suffix('.tgz'),OUT.with_suffix('.intent.json'),RESULT):
        assert not path.exists(),'Inspect prior archive intent/outcome before retry'
    run=ROOT/'ai/runs/resource-turn-boundary-v2-recovered-v1'
    failed=ROOT/'ai/runs/resource-turn-boundary-v2'
    repro=ROOT/'ai/runs/resource-turn-boundary-failure-v1'
    report=ROOT/'ai/strong/resource-turn-boundary-results-v2.json'
    data=read(report);reproduction=read(repro/'assessment.json')
    assert data['passed'] and data['assessment_sha256']==digest(run/'assessment.json')
    assert data['coverage']['families']['historical-model']==334
    assert data['counts']['old_boundary_rejections']>=1
    assert reproduction['failure_reproduced'] and reproduction['recorded_prefix_actions_exact']==137
    assert data['new_hf_jobs']==data['search_rollouts']==data['new_full_games']==0
    assert reproduction['new_learner_inference']==reproduction['new_hf_jobs']==reproduction['new_full_games']==0
    for key in ('code_hashes','input_hashes'):
        assert all(digest(ROOT/name)==sha for name,sha in data[key].items())
    for directory,assessment in ((run,data),(repro,reproduction)):
        assert all(digest(directory/name)==sha for name,sha in assessment['output_hashes'].items())
    original=ROOT/'ai/runs/resource-turn-runtime-hf-v1/pg-resource-turn-runtime-v1-anchored-2p'
    receipts=[]
    for line in (original/'job.log').read_text().splitlines():
        if not line.startswith('{'):continue
        try:row=json.loads(line)
        except json.JSONDecodeError:continue
        if set(row)=={'case','status','evidence'}:receipts.append(row)
    assert len(receipts)==1
    raw=receipts[0]['evidence']
    assert raw['revision']=='cc490998a1d3cf4a1d65994dd7669df2dc375c6b'
    assert raw['archive_sha256']=='0dafef7c84d923ceabcb38f52c1874f7265289dc329b11fe60b2adb42a9e0415'
    archive=Path(hf_hub_download(raw['repo'],raw['archive_path'],revision=raw['revision']))
    assert digest(archive)==raw['archive_sha256']
    sources={Path(__file__).resolve(),report}
    for directory in (run,failed,repro):
        sources.add(directory.with_suffix('.log'))
        sources.update(p for p in directory.rglob('*') if p.is_file())
    sources.update(ROOT/name for name in data['code_hashes'])
    sources.add(ROOT/'ai/strong/reproduce-resource-turn-boundary-failure-v1.py')
    for name in ('launch.json','failure.json','status.json','artifacts/manifest.json',
                 'artifacts/status.json','artifacts/job-spec.json','artifacts/source-manifest.json',
                 'artifacts/evaluation/failure-7.json','artifacts/evaluation/policy-7.stderr.log'):
        sources.add(original/name)
    sources.update(ROOT/'ai/strong'/name for name in ('resource-turn-runtime-source-v1.json',
        'resource-turn-runtime-launch-evidence-v1.json','resource-turn-anchor-evidence-v1.json',
        'resource-turn-anchored-policy-evidence-v1.json','policy_iteration_evidence_archive.py','strategic_collection.py'))
    sources.update(ROOT/'ai'/name for name in ('RESOURCE-TURN-BOUNDARY-2026-10-28.md','RESUME.md'))
    api=HfApi();repo='coyotte508/powergrid-ai-germany-v1'
    assert api.model_info(repo).private and not api.file_exists(repo,'archives/'+NAME+'.tgz')
    OUT.mkdir();hashes={}
    for source in sorted(sources):
        assert source.is_file() and not source.is_symlink()
        name=str(source.relative_to(ROOT));target=OUT/name;target.parent.mkdir(parents=True,exist_ok=True)
        sha=digest(source);shutil.copy2(source,target);assert digest(target)==sha;hashes[name]=sha
    save(OUT/'original-runtime-archive.json',raw)
    hashes['original-runtime-archive.json']=digest(OUT/'original-runtime-archive.json')
    save(OUT/'manifest.json',hashes)
    intent={'created_at':datetime.now(timezone.utc).isoformat(),'stage':'prepared_for_upload',
        'archive_path':'archives/'+NAME+'.tgz','manifest_sha256':digest(OUT/'manifest.json')}
    save(OUT.with_suffix('.intent.json'),intent)
    print(json.dumps({'stage':'uploading','files':len(hashes)+1}),flush=True)
    uploaded=upload_evidence(OUT)
    save(RESULT,{'status':'boundary_defect_reproduced_and_separate_helper_validated_not_integrated',
        'assessment_sha256':data['assessment_sha256'],'reproduction_sha256':digest(repro/'assessment.json'),
        'original_job_id':'6ae20c133fb22a235dd4146f','original_job_status':'ERROR','original_archive':raw,
        'counts':data['counts'],'new_hf_jobs':0,'new_learner_inference':0,'new_full_games':0,
        'opponent_prefix_reexecuted':True,'new_search_policy_integrated':False,
        'qualification_eligible':False,'reserved_final_seeds_used':False,'archive':uploaded})
    OUT.with_suffix('.intent.json').write_text(json.dumps({**intent,'stage':'uploaded_download_verified',
        'archive':uploaded,'descriptor_sha256':digest(RESULT)},indent=2)+'\n')
    print(json.dumps(uploaded),flush=True)


if __name__=='__main__':main()
