"""Prepare and own one complete serving replay, without selecting a policy."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile

import current_auction_full_serving_v1 as bench

ROOT=Path(__file__).resolve().parents[2]
PREP=ROOT/'ai/runs/current-full-serving-8840u-prepared-v1'
COLLECTED=ROOT/'ai/runs/current-full-serving-8840u-collected-v1'
GUARD=ROOT/'ai/strong/current-full-serving-8840u-launch-v1.json'
REMOTE='/home/coyotte508/powergrid-ai-current-full-serving-8840u-v1'
PYTHON='/home/coyotte508/powergrid-ai-baseline/.venv/bin/python'
DEPS='/home/coyotte508/powergrid-ai-surrogate-opponent-8840u-v1/dependencies'
SOURCE=ROOT/'ai/runs/current-auction-grid-prepared-v1/source/artifact'


def save(p,x):
    with p.open('x') as f:json.dump(x,f,indent=2,allow_nan=False);f.write('\n')


def prepare():
    assert not any(p.exists() for p in (PREP,GUARD,COLLECTED)), 'Inspect original outcome before retry'
    ready_path=ROOT/'ai/strong/current-full-serving-readiness-v1.json';ready=bench.read(ready_path)
    assert ready['passed'] and all(bench.digest(ROOT/n)==h for n,h in ready['input_hashes'].items())
    compatible=bench.read(ROOT/'ai/strong/current-engine-serving-fixture-audit-v1.json')
    assert compatible['passed'] and compatible['positions']==2553 and not compatible['issues']
    assert bench.digest(SOURCE/'manifest.json')==bench.RUNTIME_SHA
    assert all(bench.digest(SOURCE/n)==h for n,h in bench.read(SOURCE/'manifest.json').items())
    PREP.mkdir();save(PREP/'prepare-intent.json',{'started_at':datetime.now(timezone.utc).isoformat(),
        'positions':2553,'requests':5106,'readiness_sha256':bench.digest(ready_path),
        'runtime_manifest_sha256':bench.RUNTIME_SHA,'candidate_selected':False,'reserved_final_seeds_used':False})
    package=PREP/'package';package.mkdir();shutil.copytree(SOURCE,package/'artifact')
    subprocess.run(['node',str(ROOT/'ai/strong/prepare-current-full-serving-cases-v1.cjs'),str(package/'cases.jsonl')],check=True)
    shutil.copyfile(bench.__file__,package/'benchmark.py')
    shutil.copyfile(ROOT/'ai/strong/current_auction_cpu_v1.py',package/'current_auction_cpu_v1.py')
    sys.path.insert(0,str(package/'artifact/ai/strong'))
    from public_policy_final_audit_v1 import artifact_identity
    identities={a:artifact_identity(package/'artifact',f'policies/{a}.json') for a in bench.ARMS}
    m={'version':1,'runtime_manifest_sha256':bench.RUNTIME_SHA,'original_fixture_sha256':bench.FIXTURE_SHA,
        'compatibility_report_sha256':bench.digest(ROOT/'ai/strong/current-engine-serving-fixture-audit-v1.json'),
        'arms':list(bench.ARMS),'positions':2553,'requests':5106,'identities':identities,
        'runner_sha256':bench.digest(bench.__file__),'readiness_sha256':bench.digest(ready_path),
        'selection':'Both already-frozen confirmation policies; every original fixture in original order, no selection from outcomes.',
        'candidate_selected':False,'qualified':False,'reserved_final_seeds_used':False,
        'files':{str(p.relative_to(package)):bench.digest(p) for p in sorted(package.rglob('*')) if p.is_file()}}
    save(package/'benchmark-manifest.json',m);bench.checked_package(package)
    with tarfile.open(PREP/'package.tgz','w:gz') as bundle:
        for p in sorted(package.rglob('*')):
            if not p.is_file():continue
            assert not p.is_symlink();info=bundle.gettarinfo(p,arcname=str(p.relative_to(package)))
            info.uid=info.gid=info.mtime=0;info.uname=info.gname=''
            with p.open('rb') as f:bundle.addfile(info,f)
    prepared={'package_sha256':bench.digest(PREP/'package.tgz'),'package_bytes':(PREP/'package.tgz').stat().st_size,
        'manifest_sha256':bench.digest(package/'benchmark-manifest.json'),'runner_sha256':bench.digest(bench.__file__),
        'manager_sha256':bench.digest(__file__),'readiness_sha256':bench.digest(ready_path),
        'cases_sha256':bench.digest(package/'cases.jsonl'),'positions':2553,'requests':5106,
        'candidate_selected':False,'qualified':False,'reserved_final_seeds_used':False}
    save(PREP/'prepared.json',prepared);print(json.dumps(prepared),flush=True)


def checked():
    p=bench.read(PREP/'prepared.json')
    assert p['runner_sha256']==bench.digest(bench.__file__) and p['manager_sha256']==bench.digest(__file__)
    assert p['manifest_sha256']==bench.digest(PREP/'package/benchmark-manifest.json')
    assert p['package_sha256']==bench.digest(PREP/'package.tgz')
    ready=ROOT/'ai/strong/current-full-serving-readiness-v1.json';assert p['readiness_sha256']==bench.digest(ready)
    assert all(bench.digest(ROOT/n)==h for n,h in bench.read(ready)['input_hashes'].items())
    bench.checked_package(PREP/'package');return p


def ssh(script):
    return subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','minipc','python3 -'],
        input=script,text=True,capture_output=True,check=True)


def launch():
    p=checked();assert not GUARD.exists(),'Inspect original launch guard; never duplicate it'
    guard={'stage':'launch_intent','host':'minipc','directory':REMOTE,**p};save(GUARD,guard)
    try:
        check=f'''from pathlib import Path
import json
assert not Path({REMOTE!r}).exists() and not Path({(REMOTE+'.tgz')!r}).exists()
running=[]
for proc in Path('/proc').glob('[0-9]*'):
 try:
  cmd=(proc/'cmdline').read_bytes()
  if b'powergrid-ai-' in cmd and b'benchmark.py' in cmd:running.append(int(proc.name))
 except (FileNotFoundError,PermissionError):pass
assert not running, 'An existing benchmark is live: '+str(running)
print(json.dumps({{'existing_benchmarks':running}}))
'''
        result=ssh(check);save(PREP/'target-prelaunch-check.json',json.loads(result.stdout))
        subprocess.run(['scp','-q',str(PREP/'package.tgz'),'minipc:'+REMOTE+'.tgz'],check=True)
        script=f'''import subprocess,tarfile,json,hashlib,os
from pathlib import Path
root=Path({REMOTE!r});archive=Path({(REMOTE+'.tgz')!r});assert not root.exists()
assert hashlib.sha256(archive.read_bytes()).hexdigest()=={p['package_sha256']!r}
root.mkdir()
with tarfile.open(archive) as bundle:bundle.extractall(root,filter='data')
env={{**os.environ,'PYTHONPATH':{DEPS!r},'HF_HUB_OFFLINE':'1','PYTHONDONTWRITEBYTECODE':'1'}}
subprocess.run([{PYTHON!r},'-B','-c','import huggingface_hub; assert huggingface_hub.__version__ == "2.0.0"'],env=env,check=True)
with (root/'run.log').open('x') as log:
 child=subprocess.Popen([{PYTHON!r},'-u','-B',str(root/'benchmark.py'),'run','--package',str(root),'--output',str(root/'output')],cwd='/tmp',env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
value={{'pid':child.pid,'directory':str(root)}}
(root/'target-launch.json').write_text(json.dumps(value));print(json.dumps(value))
'''
        remote=json.loads(ssh(script).stdout);guard.update(stage='launched',pid=remote['pid'])
    except BaseException as error:
        guard.update(stage='launch_unknown',failure_type=type(error).__name__);raise
    finally:bench.write(GUARD,guard)
    print(json.dumps({'stage':guard['stage'],'pid':guard.get('pid'),'host':'minipc','requests':5106}),flush=True)


def inspect():
    guard=bench.read(GUARD);assert guard['stage']=='launched'
    script=f'''from pathlib import Path
import json
root=Path({REMOTE!r});p=Path('/proc')/{str(guard['pid'])!r};status=root/'output/status.json'
live=p.exists() and str(root/'benchmark.py').encode() in (p/'cmdline').read_bytes() and ') Z' not in (p/'stat').read_text()
print(json.dumps({{'pid':{guard['pid']},'live':live,'status':json.loads(status.read_text()) if status.exists() else None,
 'log_tail':(root/'run.log').read_text()[-1500:]}}))
'''
    state=json.loads(ssh(script).stdout);bench.write(PREP/'last-target-status.json',state)
    print(json.dumps({'pid':state['pid'],'live':state['live'],'status':{k:state['status'][k] for k in ('stage','processor','completed_requests','current_arm','passed','failure') if k in (state['status'] or {})},'log_tail':state['log_tail']}),flush=True)
    return state


def collect():
    p=checked();state=inspect();s=state['status']
    assert not state['live'] and s and s['stage']=='completed' and s['passed'] and s['completed_requests']==5106
    COLLECTED.mkdir(exist_ok=False)
    for name in ('output','run.log','target-launch.json'):
        subprocess.run(['scp','-qr','minipc:'+REMOTE+'/'+name,str(COLLECTED)],check=True)
    command=[sys.executable,'-u','-B',str(PREP/'package/benchmark.py'),'audit','--package',str(PREP/'package'),'--output',str(COLLECTED/'output')]
    with (COLLECTED/'audit.json').open('x') as f, (COLLECTED/'audit.stderr.log').open('x') as stderr:
        subprocess.run(command,stdout=f,stderr=stderr,check=True,cwd='/tmp')
    review=bench.read(COLLECTED/'audit.json');assert review['complete'] and review['requests']==5106
    save(ROOT/'ai/strong/current-full-serving-8840u-results-v1.json',review)
    print(json.dumps({'complete':True,'requests':5106,'audit_sha256':bench.digest(COLLECTED/'audit.json')}),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(__doc__);p.add_argument('operation',choices=['prepare','launch','inspect','collect'])
    globals()[p.parse_args().operation]()
