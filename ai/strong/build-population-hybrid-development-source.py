"""Prepare an unchanged-policy package, then freeze a runtime-admitted HF plan."""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile

from huggingface_hub import HfApi,hf_hub_download
from strategic_collection import ROOT,read,write,digest
from population_hybrid_development import PROTOCOL,SOURCE,PLAN,runtime_admission,make_plan

BASE=ROOT/'ai/strong/population-hybrid-source-v2.json'
PREP=ROOT/'ai/runs/population-hybrid-development-source-prepared-v1'
ARCHIVE=ROOT/'ai/runs/strong-source-population-hybrid-development-20261024-v1.tgz'
REPO='coyotte508/powergrid-ai-training-v1'
NAMES=['population_policy_verification.py','population_hybrid_development.py',
       'population-hybrid-development-job.py','manage-population-hybrid-development.py',
       'coordinate-population-hybrid-development.py','compare-population-hybrid-development.py',
       'collect-population-hybrid-runtime.py','build-population-hybrid-development-source.py',
       'test_population_policy_verification.py','test_population_hybrid_development.py']

LAYOUT_TEST="""
import sys,importlib.util,os,json
from pathlib import Path
sys.path.insert(0,str(Path('ai/strong').resolve()))
spec=importlib.util.spec_from_file_location('development_job',Path('ai/strong/population-hybrid-development-job.py'))
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
class ReachedEvaluation(Exception):pass
original_popen=module.subprocess.Popen
commands=[]
def stop(*a,**k):
    if a and 'ai/strong/evaluate-population-policy.py' in a[0]:
        commands.append(a[0]);raise ReachedEvaluation('intentional clean-package preflight stop')
    return original_popen(*a,**k)
module.subprocess.Popen=stop
module.hf_hub_download=lambda *a,**k:os.environ['PREFLIGHT_MODEL']
module.upload_evidence=lambda directory:{'preflight_only':True}
assert not Path('ai/runs').exists()
try:module.run('combined',6,'search_geo',2,4)
except ReachedEvaluation:pass
else:raise AssertionError('Did not reach evaluation subprocess')
assert len(commands)==1
command=commands[0]
for flag,value in [('--players','6'),('--start','2'),('--deals','2'),('--workers','8'),('--search-workers','1'),('--samples','8'),('--seed','population-hybrid-development-v1-6p')]:
    assert command[command.index(flag)+1]==value
path=Path('ai/runs/population-hybrid-development-v1-combined-6p-search_geo-2-4')
status=json.loads((path/'development-check.json').read_text())
assert status['stage']=='failed' and status['error'].startswith('ReachedEvaluation:')
assert (path/'manifest.json').exists()
Path('development-layout-check.json').write_text(json.dumps({'clean_package_without_runs':True,'reached_evaluation_subprocess':True,'nonzero_deal_offset_checked':True,'failure_receipt_written':True,'new_games':0,'new_jobs':0}))
"""


def prepare():
    assert not PREP.exists() and not ARCHIVE.exists() and not SOURCE.exists() and not PLAN.exists()
    base=read(BASE);protocol=read(PROTOCOL)
    assert base['protocol_sha256']==digest(PROTOCOL)
    assert digest(ROOT/'ai/strong/final-protocol-multiplayer.json')==protocol['final_protocol_sha256']
    assert all(digest(ROOT/name)==sha for name,sha in base['overlays'].items())
    PREP.mkdir();layout=PREP/'layout';layout.mkdir()
    archive=Path(hf_hub_download(REPO,base['archive'],repo_type='dataset',revision=base['revision']))
    assert digest(archive)==base['sha256']
    with tarfile.open(archive) as bundle:bundle.extractall(layout,filter='data')
    before={str(p.relative_to(layout)):digest(p) for p in layout.rglob('*') if p.is_file()}
    added={}
    for name in NAMES:
        rel='ai/strong/'+name;assert rel not in before
        shutil.copy2(ROOT/rel,layout/rel);added[rel]=digest(layout/rel)
    # Re-run the independent verifier and execution-contract tests together.
    for pattern in ['test_population_policy_verification.py','test_population_hybrid_development.py']:
        with (PREP/(pattern+'.log')).open('w') as log:
            subprocess.run([sys.executable,'-m','unittest','discover','-s','ai/strong','-p',pattern,'-v'],
                cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,check=True)
    model=ROOT/'ai/runs/policy-iteration-trained-8840u-prepared-v2/local-package-frozen-1/policy.onnx'
    env={**os.environ,'PREFLIGHT_MODEL':str(model),'PROTOCOL_SHA256':digest(PROTOCOL),
        'SOURCE_REVISION':'clean-package-preflight','SOURCE_SHA256':base['sha256']}
    with (PREP/'clean-package-test.log').open('w') as log:
        subprocess.run([sys.executable,'-c',LAYOUT_TEST],cwd=layout,env=env,
            stdout=log,stderr=subprocess.STDOUT,check=True)
    assert all(digest(layout/name)==sha for name,sha in before.items())
    assert all(digest(ROOT/name)==digest(layout/name)==sha for name,sha in added.items())
    with tarfile.open(ARCHIVE,'w:gz') as bundle:
        for name in sorted(set(before)|set(added)):bundle.add(layout/name,arcname=name,recursive=False)
    report={'prepared':True,'base_descriptor_sha256':digest(BASE),'base':base,
        'archive':ARCHIVE.name,'sha256':digest(ARCHIVE),'bytes':ARCHIVE.stat().st_size,
        'unchanged_base_files':len(before),'overlays':{**base['overlays'],**added},
        'new_files':added,'protocol_sha256':digest(PROTOCOL),
        'layout_check':read(layout/'development-layout-check.json'),
        'test_log_hashes':{str(p.relative_to(ROOT)):digest(p) for p in PREP.glob('*.log')},
        'new_jobs':0,'gradients':False,'qualification_eligible':False,'reserved_final_seeds_used':False}
    write(PREP/'prepared.json',report)
    print({k:report[k] for k in ['prepared','archive','sha256','unchanged_base_files','new_jobs']},flush=True)


def freeze():
    assert not PLAN.exists(),'Plan already frozen; use its existing guards'
    prepared=read(PREP/'prepared.json');assert prepared['prepared']
    assert prepared['base_descriptor_sha256']==digest(BASE) and prepared['protocol_sha256']==digest(PROTOCOL)
    assert digest(ARCHIVE)==prepared['sha256']
    assert all(digest(ROOT/name)==sha for field in ['overlays','test_log_hashes'] for name,sha in prepared[field].items())
    admission=runtime_admission()  # Both endpoint jobs must be independently verified.
    write(PREP/'runtime-admission.json',admission)
    if SOURCE.exists():
        source=read(SOURCE)
        assert source['sha256']==prepared['sha256'] and source['preparation_sha256']==digest(PREP/'prepared.json')
    else:
        with (PREP/'upload-intent.json').open('x') as stream:
            stream.write('{"purpose":"one immutable source upload; reconcile uncertain outcomes before retrying"}\n')
        commit=HfApi().upload_file(repo_id=REPO,repo_type='dataset',path_or_fileobj=ARCHIVE,path_in_repo=ARCHIVE.name)
        write(PREP/'upload-receipt.json',{'repo':REPO,'revision':commit.oid,'archive':ARCHIVE.name,'sha256':digest(ARCHIVE)})
        assert digest(hf_hub_download(REPO,ARCHIVE.name,repo_type='dataset',revision=commit.oid))==prepared['sha256']
        source={k:prepared[k] for k in ['archive','sha256','bytes','overlays','protocol_sha256','unchanged_base_files','layout_check']}
        source.update(revision=commit.oid,base={k:prepared['base'][k] for k in ['archive','revision','sha256']},
            base_descriptor_sha256=digest(BASE),preparation_sha256=digest(PREP/'prepared.json'),
            gradients=False,qualification_eligible=False,reserved_final_seeds_used=False)
        write(SOURCE,source)
    plan=make_plan(read(PROTOCOL),source,admission)
    dependencies=set(prepared['overlays'])|{
        'ai/strong/population-hybrid-source-v2.json','ai/strong/population-hybrid-development-source-v1.json',
        'ai/strong/strategic_collection.py','ai/strong/arena_statistics.py',
        'ai/strong/policy_iteration_development.py','ai/strong/compare-population-screens.py',
        'ai/strong/collect-population-screen.py','ai/strong/final-protocol-multiplayer.json'}
    plan['dependency_hashes']={name:digest(ROOT/name) for name in sorted(dependencies)}
    plan['preparation_sha256']=digest(PREP/'prepared.json')
    write(PLAN,plan)
    print({'plan':str(PLAN),'shards':len(plan['shards']),'games':plan['planned_games'],
        'timeout_hours':admission['timeout_hours'],'max_in_flight':admission['max_in_flight'],
        'source_revision':source['revision'],'new_jobs':0},flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(__doc__);parser.add_argument('operation',choices=['prepare','freeze'])
    globals()[parser.parse_args().operation]()
