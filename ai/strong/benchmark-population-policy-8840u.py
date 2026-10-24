"""Prepare, run and compare the exact experimental hybrid on the actual 8840U."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile

from strategic_collection import ROOT,read,write,digest

PREP=ROOT/'ai/runs/population-policy-8840u-prepared-v2'
LOCAL=ROOT/'ai/runs/population-policy-local-reference-v2'
COLLECTED=ROOT/'ai/runs/population-policy-8840u-collected-v2'
GUARD=ROOT/'ai/strong/population-policy-8840u-launch-v2.json'
REMOTE='/home/coyotte508/powergrid-ai-population-policy-8840u-v2'
PYTHON='/home/coyotte508/powergrid-ai-baseline/.venv/bin/python'


def prepare():
    assert not PREP.exists() and not LOCAL.exists() and not GUARD.exists()
    source=read(ROOT/'ai/strong/population-hybrid-source-v2.json')
    protocol=read(ROOT/'ai/strong/population-hybrid-development-protocol-v1.json')
    prepared=ROOT/'ai/runs/population-hybrid-development-source-prepared-v1'
    report=read(prepared/'prepared.json');runtime=prepared/'layout'
    assert report['base']==source and all(digest(ROOT/name)==sha for name,sha in report['overlays'].items())
    PREP.mkdir();package=PREP/'package';package.mkdir()
    shutil.copytree(runtime/'engine',package/'engine')
    names=['ai/core.cjs','ai/infer.py','ai/pool.py']
    names += ['ai/strong/'+name for name in ['hybrid_search.py','feature_contract.py',
        'population_hybrid_policy.py','population_policy_verification.py','arena_statistics.py']]
    names += [str(p.relative_to(runtime)) for p in (runtime/'ai/strong').glob('*.cjs')]
    for name in names:
        target=package/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(runtime/name,target)
    old=ROOT/'ai/runs/policy-iteration-trained-8840u-prepared-v2'
    shutil.copy2(old/'fixtures.jsonl',package/'fixtures.jsonl')
    shutil.copy2(old/'local-package-frozen-1/policy.onnx',package/'policy.onnx')
    assert digest(package/'policy.onnx')==protocol['model_pin']['files']['inference64.onnx']
    shutil.copy2(ROOT/'ai/runs/trained-hybrid-probe-v2/selected-fixtures.json',package/'selected-fixtures.json')
    shutil.copy2(ROOT/'ai/strong/run-population-policy-benchmark.py',package/'benchmark.py')
    hashes={str(p.relative_to(package)):digest(p) for p in package.rglob('*') if p.is_file()}
    runtime_names=[name for name in hashes if name.startswith('engine/') or name.startswith('ai/')]
    assert all(hashes[name]==digest(runtime/name) for name in runtime_names)
    manifest={'source':source,'model_pin':protocol['model_pin'],'protocol_sha256':digest(ROOT/'ai/strong/population-hybrid-development-protocol-v1.json'),
        'files':hashes,'exact_runtime_files':len(runtime_names),'samples':8,'horizon':2400,
        'search_arm':'combined','execution_settings':[[1,1],[4,4]],'new_strength_games':0,
        'gradients':False,'qualification_eligible':False,'reserved_final_seeds_used':False}
    write(package/'manifest.json',manifest)
    with tarfile.open(PREP/'package.tgz','w:gz') as bundle:
        for p in sorted(package.rglob('*')):
            if p.is_file():bundle.add(p,arcname=str(p.relative_to(package)))
    write(PREP/'prepared.json',{'package_sha256':digest(PREP/'package.tgz'),
        'manifest_sha256':digest(package/'manifest.json'),'model_sha256':digest(package/'policy.onnx'),
        'runner_sha256':digest(package/'benchmark.py'),'exact_runtime_files':len(runtime_names),
        'qualification_eligible':False,'reserved_final_seeds_used':False})
    print(read(PREP/'prepared.json'),flush=True)


def local():
    package=PREP/'package';assert not LOCAL.exists()
    with (PREP/'local.log').open('x') as log:
        subprocess.run([sys.executable,str(package/'benchmark.py'),'--package',str(package),'--output',str(LOCAL)],
            cwd='/tmp',stdout=log,stderr=subprocess.STDOUT,check=True)
    result=read(LOCAL/'status.json');assert result['passed']
    print({'stage':'local_complete','counts':result['counts'],'seconds':result['seconds']},flush=True)


def launch():
    reference=read(LOCAL/'status.json');assert reference['passed'] and not GUARD.exists()
    prepared=read(PREP/'prepared.json');assert digest(PREP/'package.tgz')==prepared['package_sha256']
    assert digest(PREP/'package/manifest.json')==prepared['manifest_sha256']
    assert reference['manifest_sha256']==prepared['manifest_sha256']
    assert all(digest(LOCAL/name)==sha for name,sha in reference['output_hashes'].items())
    record={'stage':'launch_intent','host':'minipc','directory':REMOTE,**prepared,
        'gradients':False,'new_hf_jobs':0,'qualification_eligible':False}
    with GUARD.open('x') as stream:json.dump(record,stream,indent=2)
    try:
        subprocess.run(['scp','-q',str(PREP/'package.tgz'),'minipc:'+REMOTE+'.tgz'],check=True)
        script=f'''import subprocess,tarfile,json,hashlib
from pathlib import Path
root=Path({REMOTE!r});archive=Path({(REMOTE+'.tgz')!r})
assert not root.exists()
assert hashlib.sha256(archive.read_bytes()).hexdigest()=={prepared['package_sha256']!r}
root.mkdir()
with tarfile.open(archive) as bundle:bundle.extractall(root,filter='data')
with (root/'run.log').open('x') as log:
    child=subprocess.Popen([{PYTHON!r},'-u',str(root/'benchmark.py'),'--package',str(root),'--output',str(root/'output'),'--require-cpu','8840U'],cwd='/tmp',stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
value={{'pid':child.pid,'directory':str(root)}}
(root/'target-launch.json').write_text(json.dumps(value))
print(json.dumps(value))
'''
        result=subprocess.run(['ssh','-o','BatchMode=yes','minipc','python3 -'],input=script,capture_output=True,text=True,check=True)
        value=json.loads(result.stdout);record.update(stage='launched',pid=value['pid'])
    except BaseException as error:
        record.update(stage='launch_unknown',error=type(error).__name__+': '+str(error));raise
    finally:write(GUARD,record)
    print(record,flush=True)


def inspect():
    guard=read(GUARD);assert guard['stage']=='launched'
    script=f'''import json
from pathlib import Path
root=Path({REMOTE!r});state=root/'output/status.json';proc=Path('/proc')/{str(guard['pid'])!r}/'cmdline'
value={{'pid':{guard['pid']},'process_present':proc.exists(),'status':json.loads(state.read_text()) if state.exists() else None}}
if proc.exists():value['command_matches']=str(root/'benchmark.py').encode() in proc.read_bytes()
print(json.dumps(value))
'''
    result=subprocess.run(['ssh','-o','BatchMode=yes','minipc','python3 -'],input=script,capture_output=True,text=True,check=True)
    state=json.loads(result.stdout);write(PREP/'last-target-status.json',state);print(state,flush=True);return state


def collect():
    state=inspect();assert state['status']['stage']=='completed' and state['status']['passed']
    assert not COLLECTED.exists();COLLECTED.mkdir()
    subprocess.run(['scp','-qr','minipc:'+REMOTE+'/output',str(COLLECTED)],check=True)
    target=COLLECTED/'output';status=read(target/'status.json');reference=read(LOCAL/'status.json')
    assert status['manifest_sha256']==reference['manifest_sha256']==digest(PREP/'package/manifest.json')
    assert '8840U' in status['processor'] and status['required_cpu']=='8840U'
    assert status['counts']==reference['counts'] and status['passed'] and reference['passed']
    for directory,record in [(target,status),(LOCAL,reference)]:
        assert all(digest(directory/name)==sha for name,sha in record['output_hashes'].items())
    def rows(path):return [json.loads(line) for line in path.read_text().splitlines()]
    def semantic(value):
        if isinstance(value,dict):return {k:semantic(v) for k,v in value.items() if k!='elapsedMs'}
        if isinstance(value,list):return [semantic(v) for v in value]
        return value
    for name in ['model-filter.jsonl','search.jsonl']:
        assert semantic(rows(target/name))==semantic(rows(LOCAL/name)),name+' target parity mismatch'
    search=rows(target/'search.jsonl')
    timings=[{'fixture':r['fixture'],'threads':r['threads'],'workers':r['workers'],
        'seconds':r['result']['elapsedMs']/1000} for r in search]
    assessment={'passed':True,'target':status,'local_reference_sha256':digest(LOCAL/'status.json'),
        'target_status_sha256':digest(target/'status.json'),'search_timings':timings,
        'model_filter_decisions_exact':5106,'search_outcomes_worlds_choices_exact':8,
        'scope':status['scope'],'qualification_eligible':False,'reserved_final_seeds_used':False}
    write(COLLECTED/'assessment.json',assessment);print(assessment,flush=True)


def archive():
    from policy_iteration_evidence_archive import upload_evidence
    assessment=read(COLLECTED/'assessment.json');assert assessment['passed']
    out=ROOT/'ai/runs/population-policy-8840u-evidence-v2';assert not out.exists();out.mkdir()
    files=[Path(__file__),ROOT/'ai/strong/run-population-policy-benchmark.py',GUARD,
        PREP/'package.tgz',PREP/'prepared.json',PREP/'package/manifest.json',PREP/'local.log',
        PREP/'last-target-status.json',ROOT/'ai/runs/population-policy-8840u-prepared-v1/package.tgz']
    for directory in [COLLECTED,LOCAL,ROOT/'ai/runs/population-policy-local-reference-v1',
                      ROOT/'ai/runs/population-policy-benchmark-failure-v1']:
        files.extend(p for p in directory.rglob('*') if p.is_file())
    for path in files:
        dest=out/path.relative_to(ROOT);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,dest)
    write(out/'assessment.json',assessment)
    write(out/'manifest.json',{str(p.relative_to(out)):digest(p) for p in sorted(out.rglob('*')) if p.is_file()})
    evidence=upload_evidence(out)
    record={**evidence,'assessment_sha256':digest(out/'assessment.json'),
        'counts':assessment['target']['counts'],'search_timings':assessment['search_timings'],
        'processor':assessment['target']['processor'],'model_sha256':read(PREP/'prepared.json')['model_sha256'],
        'model_filter_decisions_exact':5106,'search_outcomes_worlds_choices_exact':8,
        'scope':assessment['scope'],'new_hf_jobs':0,'gradients':False,
        'qualification_eligible':False,'reserved_final_seeds_used':False}
    write(ROOT/'ai/strong/population-policy-8840u-evidence-v2.json',record)
    print(evidence,flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(__doc__);parser.add_argument('operation',choices=['prepare','local','launch','inspect','collect','archive'])
    globals()[parser.parse_args().operation]()
