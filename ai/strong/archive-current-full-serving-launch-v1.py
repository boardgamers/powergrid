"""Preserve original full-serving launch and standalone recovery package once."""
from datetime import datetime,timezone
import json
from pathlib import Path

from huggingface_hub import HfApi
from policy_iteration_evidence_archive import upload_evidence
from public_policy_development_job_v1 import read,digest

ROOT=Path(__file__).resolve().parents[2]
NAME='current-full-serving-launch-evidence-v1'
OUT=ROOT/'ai/runs'/NAME
RESULT=ROOT/'ai/strong'/(NAME+'.json')
PREP=ROOT/'ai/runs/current-full-serving-8840u-prepared-v1'


def save(p,value):
    with p.open('x') as f:json.dump(value,f,indent=2,allow_nan=False);f.write('\n')


def main():
    assert all(not p.exists() for p in (OUT,OUT.with_suffix('.tgz'),OUT.with_suffix('.intent.json'),RESULT)), 'Inspect existing archive outcome'
    ready_path=ROOT/'ai/strong/current-full-serving-readiness-v1.json';ready=read(ready_path)
    assert ready['passed'] and ready['tests']==6 and ready['compatible_original_positions']==2553
    assert all(digest(ROOT/n)==h for n,h in ready['input_hashes'].items())
    prepared=read(PREP/'prepared.json');guard=read(ROOT/'ai/strong/current-full-serving-8840u-launch-v1.json')
    snapshot=read(PREP/'last-target-status.json')
    assert guard['stage']=='launched' and snapshot['pid']==guard['pid'] and snapshot['live']
    assert snapshot['status']['stage']=='running' and '8840U' in snapshot['status']['processor']
    assert digest(PREP/'package.tgz')==prepared['package_sha256']==guard['package_sha256']
    assert digest(PREP/'package/benchmark-manifest.json')==prepared['manifest_sha256']
    sources={ROOT/n for n in ready['input_hashes']};fixture=ROOT/'ai/strong/fixtures/multiplayer-serving-v1.jsonl'
    assert digest(PREP/'package/artifact/ai/strong/fixtures/multiplayer-serving-v1.jsonl')==digest(fixture)
    sources.remove(fixture)  # It already exists in the exact standalone archive.
    sources.update((Path(__file__).resolve(),ready_path,ROOT/'ai/CURRENT-FULL-SERVING-2026-10-29.md',
        ROOT/'ai/strong/current-full-serving-8840u-launch-v1.json',
        ROOT/'ai/strong/policy_iteration_evidence_archive.py',ROOT/'ai/strong/strategic_collection.py',
        ROOT/'ai/runs/current-engine-serving-fixture-audit-v1-first.log',
        ROOT/'ai/runs/current-full-serving-8840u-prepare-v1-first.log',
        ROOT/'ai/runs/current-full-serving-8840u-launch-v1-first.log'))
    sources.update(PREP/n for n in ('prepare-intent.json','prepared.json','package.tgz',
        'package/benchmark-manifest.json','target-prelaunch-check.json','last-target-status.json'))
    repo='coyotte508/powergrid-ai-germany-v1';api=HfApi()
    assert api.model_info(repo).private and not api.file_exists(repo,'archives/'+NAME+'.tgz')
    OUT.mkdir();manifest={}
    for p in sorted(sources):
        assert p.is_file() and not p.is_symlink()
        name=str(p.relative_to(ROOT));before=digest(p);target=OUT/name;target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes(p.read_bytes());assert digest(target)==before==digest(p);manifest[name]=before
    save(OUT/'recovery.json',{'target_pid':guard['pid'],'host':guard['host'],'remote_directory':guard['directory'],
        'package_sha256':prepared['package_sha256'],'manifest_sha256':prepared['manifest_sha256'],
        'original_fixture_from_package':'artifact/ai/strong/fixtures/multiplayer-serving-v1.jsonl',
        'original_fixture_sha256':ready['original_fixture_sha256'],
        'instructions':'Inspect the exact original process; never relaunch on an observation timeout. Restore prepared/package by extracting the archived original package.tgz. If needed copy its original fixture to the research fixture path and verify the hash. Do not repeat preparation, compatibility audit or target execution. Collect/audit only after the original is terminal; preserve failures. No selection, deployment or reserved final seeds are authorized by these receipts.'})
    manifest['recovery.json']=digest(OUT/'recovery.json');save(OUT/'manifest.json',manifest)
    intent={'created_at':datetime.now(timezone.utc).isoformat(),'stage':'prepared_for_upload','manifest_sha256':digest(OUT/'manifest.json')}
    save(OUT.with_suffix('.intent.json'),intent);archive=upload_evidence(OUT)
    save(RESULT,{'passed':True,'tests':6,'compatible_original_positions':2553,'planned_requests':5106,
        'target_pid':guard['pid'],'target_started':True,'target_completed':False,
        'readiness_sha256':digest(ready_path),'package_sha256':prepared['package_sha256'],
        'candidate_selected':False,'qualified':False,'reserved_final_seeds_used':False,'archive':archive})
    OUT.with_suffix('.intent.json').write_text(json.dumps({**intent,'stage':'uploaded_download_verified',
        'archive':archive,'descriptor_sha256':digest(RESULT)},indent=2)+'\n')
    print(json.dumps(archive),flush=True)


if __name__=='__main__':main()
