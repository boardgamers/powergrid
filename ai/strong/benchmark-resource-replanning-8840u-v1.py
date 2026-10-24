"""Prepare, run and collect the unchanged atomic resource policy on the actual 8840U."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile

from strategic_collection import ROOT,read,write,digest

PREP=ROOT/'ai/runs/resource-replanning-8840u-prepared-v1'
LOCAL=ROOT/'ai/runs/resource-replanning-profile-local-v1'
COLLECTED=ROOT/'ai/runs/resource-replanning-8840u-collected-v1'
GUARD=ROOT/'ai/strong/resource-replanning-8840u-launch-v1.json'
REMOTE='/home/coyotte508/powergrid-ai-resource-replanning-8840u-v1'
PYTHON='/home/coyotte508/powergrid-ai-baseline/.venv/bin/python'


def prepare():
    assert not PREP.exists() and not LOCAL.exists() and not GUARD.exists()
    base=ROOT/'ai/runs/resource-replanning-v1';runtime=base/'runtime';provenance=read(base/'preparation.json')
    assert read(base/'replays/assessment.json')['passed'] and read(base/'games/assessment.json')['passed']
    all_files={**provenance['runtime_hashes'],**provenance['new_files']}
    for name,sha in all_files.items():assert digest(runtime/name)==sha
    for name,sha in read(ROOT/'ai/strong/population-hybrid-development-plan-v1.json')['dependency_hashes'].items():assert digest(ROOT/name)==sha
    PREP.mkdir();package=PREP/'package';package.mkdir()
    python_names=['ai/core.cjs','ai/infer.py','ai/pool.py']+['ai/strong/'+name for name in
        ['hybrid_search.py','feature_contract.py','population_hybrid_policy.py',
         'resource_turn_search_v1.py','resource_replanning_policy_v1.py']]
    names=[name for name in all_files if name.startswith('engine/') or
        (name.startswith('ai/strong/') and name.endswith('.cjs')) or name in python_names]
    assert set(python_names)<=set(names)
    for name in names:
        dest=package/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(runtime/name,dest)
    model=ROOT/'ai/runs/policy-iteration-trained-8840u-prepared-v2/local-package-frozen-1/policy.onnx'
    assert digest(model)=='55331f43379e8fe89025d93b1a7a48c88e0ea39b4ebd3a7ef8240d4b62753530'
    shutil.copy2(model,package/'policy.onnx')
    roots={p.name.removesuffix('-slow-root.json'):read(p) for p in sorted((base/'replays').glob('*-slow-root.json'))}
    assert len(roots)==4;write(package/'slow-roots.json',roots)
    shutil.copy2(ROOT/'ai/strong/profile-resource-replanning-runtime-v1.py',package/'benchmark.py')
    hashes={str(p.relative_to(package)):digest(p) for p in package.rglob('*') if p.is_file()}
    manifest={'files':hashes,'model_sha256':digest(model),'exact_runtime_files':len(names),
        'source_provenance_sha256':digest(base/'preparation.json'),
        'source_evidence':read(ROOT/'ai/strong/resource-replanning-evidence-v1.json'),
        'execution_settings':[[1,1],[1,4],[4,4]],'samples':4,'max_steps':2400,
        'new_strength_games':0,'gradients':False,'qualification_eligible':False,'reserved_final_seeds_used':False}
    write(package/'manifest.json',manifest)
    with tarfile.open(PREP/'package.tgz','w:gz') as tar:
        for p in sorted(package.rglob('*')):
            if p.is_file():tar.add(p,arcname=str(p.relative_to(package)))
    record={'package_sha256':digest(PREP/'package.tgz'),'manifest_sha256':digest(package/'manifest.json'),
        'runner_sha256':digest(package/'benchmark.py'),'model_sha256':digest(model),
        'exact_runtime_files':len(names),'qualification_eligible':False}
    write(PREP/'prepared.json',record);print(record,flush=True)


def local():
    assert not LOCAL.exists()
    with (PREP/'local.log').open('x') as log:
        subprocess.run([sys.executable,'-u',str(PREP/'package/benchmark.py'),
            '--package',str(PREP/'package'),'--output',str(LOCAL)],cwd='/tmp',stdout=log,stderr=subprocess.STDOUT,check=True)
    result=read(LOCAL/'status.json');assert result['passed'];print(result,flush=True)


def launch():
    reference=read(LOCAL/'status.json');prepared=read(PREP/'prepared.json')
    assert reference['passed'] and not GUARD.exists()
    assert digest(PREP/'package.tgz')==prepared['package_sha256']
    assert reference['manifest_sha256']==prepared['manifest_sha256']==digest(PREP/'package/manifest.json')
    assert all(digest(LOCAL/name)==sha for name,sha in reference['output_hashes'].items())
    record={'stage':'launch_intent','host':'minipc','directory':REMOTE,**prepared,
        'new_hf_jobs':0,'gradients':False,'qualification_eligible':False}
    with GUARD.open('x') as stream:json.dump(record,stream,indent=2)
    try:
        subprocess.run(['scp','-q',str(PREP/'package.tgz'),'minipc:'+REMOTE+'.tgz'],check=True)
        script=f'''import pathlib,hashlib,tarfile,subprocess,json
root=pathlib.Path({REMOTE!r});archive=pathlib.Path({(REMOTE+'.tgz')!r})
assert not root.exists()
assert hashlib.sha256(archive.read_bytes()).hexdigest()=={prepared['package_sha256']!r}
root.mkdir()
with tarfile.open(archive) as tar:tar.extractall(root,filter='data')
with (root/'run.log').open('x') as log:
 child=subprocess.Popen([{PYTHON!r},'-u',str(root/'benchmark.py'),'--package',str(root),'--output',str(root/'output'),'--require-cpu','8840U'],cwd='/tmp',stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
result={{'pid':child.pid,'directory':str(root)}}
(root/'target-launch.json').write_text(json.dumps(result))
print(json.dumps(result))
'''
        response=subprocess.run(['ssh','-o','BatchMode=yes','minipc','python3 -'],input=script,capture_output=True,text=True,check=True)
        value=json.loads(response.stdout);record.update(stage='launched',pid=value['pid'])
    except BaseException as error:
        record.update(stage='launch_unknown',error=type(error).__name__+': '+str(error));raise
    finally:write(GUARD,record)
    print(record,flush=True)


def inspect():
    guard=read(GUARD);assert guard['stage']=='launched'
    script=f'''import pathlib,json
root=pathlib.Path({REMOTE!r});path=root/'output/status.json';proc=pathlib.Path('/proc')/{str(guard['pid'])!r}/'cmdline'
value={{'pid':{guard['pid']},'process_present':proc.exists(),'status':json.loads(path.read_text()) if path.exists() else None}}
if proc.exists():value['command_matches']=str(root/'benchmark.py').encode() in proc.read_bytes()
value['progress']=(root/'run.log').read_text().splitlines()[-2:]
print(json.dumps(value))
'''
    response=subprocess.run(['ssh','-o','BatchMode=yes','minipc','python3 -'],input=script,capture_output=True,text=True,check=True)
    result=json.loads(response.stdout);write(PREP/'last-target-status.json',result);print(result,flush=True);return result


def collect():
    current=inspect();assert current['status']['stage']=='completed' and current['status']['passed']
    assert not COLLECTED.exists();COLLECTED.mkdir()
    subprocess.run(['scp','-qr','minipc:'+REMOTE+'/output',str(COLLECTED)],check=True)
    target=COLLECTED/'output';local=read(LOCAL/'status.json');remote=read(target/'status.json')
    assert local['passed'] and remote['passed'] and '8840U' in remote['processor'] and remote['required_cpu']=='8840U'
    assert local['searches']==remote['searches']==12 and local['rollouts']==remote['rollouts']
    assert local['manifest_sha256']==remote['manifest_sha256']==digest(PREP/'package/manifest.json')
    for folder,report in [(LOCAL,local),(target,remote)]:
        assert all(digest(folder/name)==sha for name,sha in report['output_hashes'].items())
    def rows(p):return [json.loads(line) for line in p.read_text().splitlines()]
    def semantic(d):
        if isinstance(d,dict):return {str(k):semantic(v) for k,v in d.items() if k!='elapsedMs'}
        if isinstance(d,list):return [semantic(v) for v in d]
        return d
    a,b=rows(LOCAL/'results.jsonl'),rows(target/'results.jsonl')
    for left,right in zip(a,b):
        assert [left[k] for k in ['case','threads','workers']]==[right[k] for k in ['case','threads','workers']]
        assert semantic(left['result'])==semantic(right['result'])
    timings=[{k:row[k] for k in ['case','threads','workers','model_load_ms','profile']} for row in b]
    assessment={'passed':True,'target':remote,'local_status_sha256':digest(LOCAL/'status.json'),
        'target_status_sha256':digest(target/'status.json'),'exact_searches':12,'target_timings':timings,
        'new_strength_games':0,'qualification_eligible':False,'reserved_final_seeds_used':False}
    write(COLLECTED/'assessment.json',assessment);print({'passed':True,'exact_searches':12,'target_timings':timings},flush=True)


def archive():
    from policy_iteration_evidence_archive import upload_evidence
    assessment=read(COLLECTED/'assessment.json');assert assessment['passed']
    out=ROOT/'ai/runs/resource-replanning-8840u-evidence-v1';assert not out.exists();out.mkdir()
    sources=[Path(__file__),ROOT/'ai/strong/profile-resource-replanning-runtime-v1.py',GUARD,
        PREP/'package.tgz',PREP/'prepared.json',PREP/'package/manifest.json',PREP/'local.log',PREP/'last-target-status.json']
    for folder in [LOCAL,COLLECTED]:sources += [p for p in folder.rglob('*') if p.is_file()]
    for source in sources:
        dest=out/source.relative_to(ROOT);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,dest)
    write(out/'assessment.json',assessment)
    write(out/'manifest.json',{str(p.relative_to(out)):digest(p) for p in out.rglob('*') if p.is_file()})
    receipt=upload_evidence(out)
    descriptor={**receipt,'status':'verified_actual8840u_resource_stress_benchmark',
        'processor':assessment['target']['processor'],'exact_searches':12,'rollouts':assessment['target']['rollouts'],
        'timings':assessment['target_timings'],'scope':assessment['target']['scope'],
        'model_sha256':read(PREP/'prepared.json')['model_sha256'],
        'new_hf_jobs':0,'gradients':False,'qualification_eligible':False,'reserved_final_seeds_used':False}
    write(ROOT/'ai/strong/resource-replanning-8840u-evidence-v1.json',descriptor);print(receipt,flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(__doc__);parser.add_argument('operation',choices=['prepare','local','launch','inspect','collect','archive'])
    globals()[parser.parse_args().operation]()
