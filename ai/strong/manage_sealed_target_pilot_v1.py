"""Prepare, launch once, observe or collect the fixed ten-root mini-PC pilot."""
import argparse
import json
from pathlib import Path
import subprocess
import tarfile

from run_sealed_target_pilot_v1 import read, save, digest, now, check_result

ROOT = Path(__file__).resolve().parents[2]
LOCAL = ROOT/'ai/runs/sealed-target-pilot-v1'
REMOTE = '/home/coyotte508/powergrid-ai-sealed-target-pilot-v1'
RUNTIME = '/home/coyotte508/powergrid-ai-current-full-serving-8840u-v1/artifact'
PYTHON = '/home/coyotte508/powergrid-ai-baseline/.venv/bin/python'
DEPS = '/home/coyotte508/powergrid-ai-surrogate-opponent-8840u-v1/dependencies'
NODE = '/home/coyotte508/powergrid-ai-nomination-development-minipc-v1/node/bin/node'
RECORD = ROOT/'ai/strong/sealed-target-pilot-launch-v1.json'


def ssh(code):
    return subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','minipc','python3 -'],
        input=code,text=True,capture_output=True,check=True).stdout


def environment_code():
    return f"env={{**os.environ,'PYTHONPATH':{DEPS!r},'PATH':str(Path({NODE!r}).parent)+':'+os.environ['PATH'],'HF_HUB_OFFLINE':'1','PYTHONDONTWRITEBYTECODE':'1','OMP_NUM_THREADS':'1','OPENBLAS_NUM_THREADS':'1','MKL_NUM_THREADS':'1'}}"


def prepare():
    package=LOCAL/'package';protocol=read(package/'protocol.json')
    assert read(package/'preflight.json')['complete'] and not (LOCAL/'package.tgz').exists()
    assert digest(ROOT/'ai/strong/run_sealed_target_pilot_v1.py')==protocol['worker_sha256']
    # The local preflight is retained locally. Target-host checks execute independently.
    files=['worker.py','roots.json','protocol.json']
    with tarfile.open(LOCAL/'package.tgz','w:gz') as f:
        for name in files:f.add(package/name,arcname=name,recursive=False)
    save(LOCAL/'package-receipt.json',{'files':{n:digest(package/n) for n in files},'sha256':digest(LOCAL/'package.tgz')})
    ssh(f'from pathlib import Path\nassert not Path({REMOTE!r}).exists() and not Path({(REMOTE+".tgz")!r}).exists()\n')
    subprocess.run(['scp','-q',str(LOCAL/'package.tgz'),'minipc:'+REMOTE+'.tgz'],check=True)
    node=read(ROOT/'ai/strong/node-runtime-cache-v1.json')
    result=ssh(f'''import os,json,hashlib,tarfile,subprocess
from pathlib import Path
root=Path({REMOTE!r});archive=Path({(REMOTE+'.tgz')!r})
assert not root.exists()
assert hashlib.sha256(archive.read_bytes()).hexdigest()=={digest(LOCAL/'package.tgz')!r}
assert hashlib.sha256(Path({NODE!r}).read_bytes()).hexdigest()=={node['node_executable_sha256']!r}
with tarfile.open(archive) as bundle:
 members=bundle.getmembers()
 assert set(m.name for m in members)==set({files!r}) and all(m.isfile() for m in members)
 root.mkdir();bundle.extractall(root,filter='data')
{environment_code()}
with (root/'preflight.log').open('x') as log:
 subprocess.run([{PYTHON!r},'-u','-B',str(root/'worker.py'),'prepare','--root',str(root),'--runtime',{RUNTIME!r}],env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
print((root/'preflight.json').read_text())
''')
    ready=json.loads(result);assert ready['complete'] and ready['roots']==10 and ready['new_rollouts']==0
    assert ready['protocol_sha256']==digest(package/'protocol.json')
    save(LOCAL/'remote-preflight.json',ready);print({'target_preflight':True,'roots':10,'new_rollouts':0},flush=True)


def launch():
    assert not RECORD.exists() and not (LOCAL/'launch-intent.json').exists()
    protocol=read(LOCAL/'package/protocol.json');ready=read(LOCAL/'remote-preflight.json')
    assert ready['complete'] and ready['protocol_sha256']==digest(LOCAL/'package/protocol.json')
    intent={'created_at':now(),'remote':REMOTE,'runtime':RUNTIME,'protocol_sha256':ready['protocol_sha256'],
        'planned_rollouts':protocol['planned_rollouts'],'automatic_retries':False,'manager_sha256':digest(__file__)}
    save(LOCAL/'launch-intent.json',intent)
    result=ssh(f'''import os,json,subprocess
from pathlib import Path
from datetime import datetime,timezone
root=Path({REMOTE!r})
assert not any((root/n).exists() for n in ('launch.json','execution.json','worker.log','state.json','results.json'))
assert json.loads((root/'preflight.json').read_text())['protocol_sha256']=={intent['protocol_sha256']!r}
{environment_code()}
with (root/'supervisor.log').open('x') as log:
 child=subprocess.Popen([{PYTHON!r},'-u','-B',str(root/'worker.py'),'supervise','--root',str(root),'--runtime',{RUNTIME!r}],
   env=env,cwd=str(root),stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True,preexec_fn=lambda:os.nice(10))
record={{'pid':child.pid,'started_at':datetime.now(timezone.utc).isoformat(),'host':'minipc'}}
with (root/'launch.json').open('x') as f:json.dump(record,f,indent=2)
print(json.dumps(record))
''')
    record={**intent,**json.loads(result),'expected_minutes':protocol['estimate_minutes'],
        'hard_timeout_seconds':10800,'scope':'Runtime/correctness pilot only; no training or action-quality conclusion.'}
    save(RECORD,record);print(json.dumps(record),flush=True)


def status():
    record=read(RECORD)
    observed=json.loads(ssh(f'''from pathlib import Path
import json
root=Path({REMOTE!r});pid={record['pid']}
try:args=Path('/proc/'+str(pid)+'/cmdline').read_bytes().split(b'\\0')
except (FileNotFoundError,ProcessLookupError):args=[]
rows=[]
if (root/'worker.log').exists():
 for line in (root/'worker.log').read_text().splitlines():
  try:r=json.loads(line)
  except ValueError:continue
  if isinstance(r,dict) and 'rollouts' in r:rows.append(r)
print(json.dumps({{'pid':pid,'supervisor_alive':{(REMOTE+'/worker.py').encode()!r} in args and b'supervise' in args,
 'completed_components':len(rows),'completed_rollouts':sum(r['rollouts'] for r in rows),'progress':rows,
 'terminal':json.loads((root/'state.json').read_text()) if (root/'state.json').exists() else None}}))
'''))
    (LOCAL/'last-status.json').write_text(json.dumps(observed,indent=2)+'\n')
    print(json.dumps(observed),flush=True);return observed


def collect():
    observed=status();assert observed['terminal'] is not None and not observed['supervisor_alive'], 'Leave the original run intact'
    target=LOCAL/'collected';assert not target.exists(), 'Inspect prior collection'
    subprocess.run(['scp','-q','-r','minipc:'+REMOTE,str(target)],check=True)
    assert read(target/'state.json')==observed['terminal']
    assert read(target/'state.json')['complete'], 'Preserve failed/partial evidence; do not resubmit'
    roots=read(target/'roots.json');result=read(target/'results.json');assert result['complete'] and result['roots']==10
    assert digest(target/'protocol.json')==read(RECORD)['protocol_sha256']
    audits=[]
    for i,r in enumerate(roots):
        worlds={};checks={}
        for mode in read(target/'protocol.json')['modes']:
            p=target/f'root-{i:02d}-{mode}.json';check=check_result(read(p),r,worlds)
            expected=read(p.with_suffix('.audit.json'));expected['worlds']={int(k):v for k,v in expected['worlds'].items()}
            assert check==expected
            checks[mode]={'raw_sha256':digest(p),'audit':check}
        audits.append({'rootId':r['rootId'],'components':checks})
    save(ROOT/'ai/strong/sealed-target-pilot-complete-v1.json',{'created_at':now(),'complete':True,
        'roots':10,'audits':audits,'protocol_sha256':digest(target/'protocol.json'),
        'rollouts':result['new_rollouts'],'seconds':result['seconds'],'new_gradients':0,'qualified':False})


if __name__=='__main__':
    parser=argparse.ArgumentParser(__doc__);parser.add_argument('operation',choices=['prepare','launch','status','collect'])
    globals()[parser.parse_args().operation]()
