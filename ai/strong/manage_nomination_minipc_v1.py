"""Own one original mini-PC development shard, preserving HF reservations/audits."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile

from run_nomination_minipc_v1 import read, save, digest

ROOT = Path(__file__).resolve().parents[2]
STRONG = ROOT/'ai/strong'
PREP = ROOT/'ai/runs/nomination-discount-development-v1'
LOCAL = ROOT/'ai/runs/nomination-discount-minipc-v1'
CLAIMS = PREP/'launches'
REMOTE = '/home/coyotte508/powergrid-ai-nomination-development-minipc-v1'
PYTHON = '/home/coyotte508/powergrid-ai-baseline/.venv/bin/python'
NAME = 'pg-nom-dev-v1-parent-search-geo-2p'
RECORD = STRONG/'nomination-discount-minipc-launch-v1.json'
RECOVERY = STRONG/'nomination-discount-minipc-launch-recovery-v1.json'
DEPS = '/home/coyotte508/powergrid-ai-surrogate-opponent-8840u-v1/dependencies'


def now(): return datetime.now(timezone.utc).isoformat()
def ssh(script):
    return subprocess.run(['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10', 'minipc', 'python3 -'],
                          input=script, text=True, capture_output=True, check=True)


def unclaimed(folder, name):
    for suffix in ('.json', '.intent.json', '.minipc.intent.json'):
        assert not (folder/(name+suffix)).exists(), 'Inspect original claim; never duplicate: '+name+suffix


def pilots_checked():
    protocol = STRONG/'nomination-discount-development-protocol-v1.json'
    reports = []
    for n in (2, 6):
        folder = ROOT/f'ai/runs/nomination-discount-development-collected-v1/pg-nom-dev-v1-d1-all1-search-geo-{n}p'
        report = read(folder/'audit.json')
        assert report['independently_audited'] and report['protocol_sha256'] == digest(protocol)
        assert report['games'] == 16*n and report['caps'] == 0
        assert report['auditor_sha256'] == digest(STRONG/'audit_nomination_development_v1.py')
        assert report['raw_manifest_sha256'] == read(folder/'receipt.json')['manifest_sha256']
        reports.append({'path': str((folder/'audit.json').relative_to(ROOT)), 'sha256': digest(folder/'audit.json')})
    return reports


def prepare():
    unclaimed(CLAIMS, NAME); pilots = pilots_checked()
    assert not LOCAL.exists(), 'Inspect existing preparation instead of replacing it'
    source = read(STRONG/'nomination-discount-development-source-v1.json')
    assert source['remote_archive_verified'] and source['manifest_sha256'] == digest(PREP/'bundle/manifest.json')
    assert all(digest(PREP/'bundle'/n) == h for n, h in read(PREP/'bundle/manifest.json').items())
    LOCAL.mkdir(); package = LOCAL/'package'; package.mkdir()
    shutil.copytree(PREP/'bundle', package/'bundle')
    shutil.copyfile(STRONG/'run_nomination_minipc_v1.py', package/'worker.py')
    node = read(STRONG/'node-runtime-cache-v1.json')
    assert digest(ROOT/node['local_archive']) == node['sha256']
    shutil.copyfile(ROOT/node['local_archive'], package/'node.tar.xz')
    fixture = ROOT/'ai/runs/current-full-serving-8840u-prepared-v1/package/cases.jsonl'
    serving = read(STRONG/'nomination-discount-serving-v1.json')
    assert serving['complete'] and digest(fixture) == serving['fixture_source_sha256']
    indices = set(serving['selected_case_indices'])
    with (package/'cases.jsonl').open('x') as f:
        for line in fixture.open():
            if json.loads(line)['index'] in indices: f.write(line)
    (package/'references').mkdir()
    for arm in read(PREP/'bundle/protocol.json')['arms']:
        trace = ROOT/f'ai/runs/nomination-discount-serving-v1/{arm}.jsonl'
        assert digest(trace) == next(r for r in serving['arms'] if r['arm'] == arm)['trace_sha256']
        shutil.copyfile(trace, package/'references'/trace.name)
    adapter = {'created_at': now(), 'authorized_names': [NAME], 'host': 'minipc',
        'remote_base': '/home/coyotte508/powergrid-ai-current-full-serving-8840u-v1/artifact',
        'protocol_sha256': digest(PREP/'bundle/protocol.json'), 'source': source, 'node': node,
        'pilot_audits': pilots, 'manager_sha256': digest(__file__),
        'scope': 'Original unsubmitted development shard; unchanged games, seeds, policies and raw auditor.',
        'files': {str(p.relative_to(package)): digest(p) for p in sorted(package.rglob('*')) if p.is_file()}}
    save(package/'adapter.json', adapter)
    with tarfile.open(LOCAL/'package.tgz', 'w:gz') as archive:
        for p in sorted(package.rglob('*')):
            if p.is_file(): archive.add(p, arcname=str(p.relative_to(package)), recursive=False)
    save(LOCAL/'prepared.json', {'archive_sha256': digest(LOCAL/'package.tgz'),
        'adapter_sha256': digest(package/'adapter.json'), 'protocol_sha256': adapter['protocol_sha256']})
    ssh(f'from pathlib import Path\nassert not Path({REMOTE!r}).exists() and not Path({(REMOTE+".tgz")!r}).exists()\n')
    subprocess.run(['scp', '-q', str(LOCAL/'package.tgz'), 'minipc:'+REMOTE+'.tgz'], check=True)
    # The package contains no credentials and is verified before extraction/execution.
    script = f'''import hashlib,tarfile,subprocess
from pathlib import Path
root=Path({REMOTE!r}); archive=Path({(REMOTE+'.tgz')!r})
assert not root.exists()
assert hashlib.sha256(archive.read_bytes()).hexdigest()=={digest(LOCAL/'package.tgz')!r}
with tarfile.open(archive) as bundle:
 members=bundle.getmembers()
 assert len(members)==len(set(m.name for m in members))
 assert all(m.isfile() and not Path(m.name).is_absolute() and '..' not in Path(m.name).parts for m in members)
 root.mkdir(); bundle.extractall(root,filter='data')
with (root/'prepare.log').open('x') as log:
 subprocess.run([{PYTHON!r},'-u','-B',str(root/'worker.py'),'prepare','--root',str(root)],stdout=log,stderr=subprocess.STDOUT,check=True)
print((root/'ready.json').read_text())
'''
    ready = json.loads(ssh(script).stdout); save(LOCAL/'ready.json', ready)
    assert ready['complete'] and ready['adapter_sha256'] == digest(package/'adapter.json')
    print({'prepared': True, 'exact_saved_choices': sum(r['exact_choices'] for r in ready['reports']), 'versions': ready['versions']}, flush=True)


def launch():
    unclaimed(CLAIMS, NAME); pilots_checked()
    package = LOCAL/'package'; ready = read(LOCAL/'ready.json'); config = read(package/'adapter.json')
    assert config['manager_sha256'] == digest(__file__)
    assert digest(package/'worker.py') == digest(STRONG/'run_nomination_minipc_v1.py')
    assert ready['complete'] and ready['adapter_sha256'] == digest(package/'adapter.json')
    assert all(digest(package/n) == h for n, h in config['files'].items())
    assert not RECORD.exists()
    row = next(r for r in read(PREP/'bundle/protocol.json')['rows'] if r['name'] == NAME)
    intent = {'created_at': now(), 'name': NAME, 'host': 'minipc', 'remote': REMOTE,
        'protocol_sha256': config['protocol_sha256'], 'adapter_sha256': digest(package/'adapter.json'),
        'row': row, 'automatic_retries': False, 'qualified': False, 'reserved_final_seeds_used': False}
    save(CLAIMS/(NAME+'.minipc.intent.json'), intent)
    script = f'''import json,os,subprocess
from pathlib import Path
from datetime import datetime,timezone
root=Path({REMOTE!r}); name={NAME!r}
assert not (root/'outputs'/name).exists() and not (root/(name+'.launch.json')).exists()
ready=json.loads((root/'ready.json').read_text());assert ready['complete']
assert ready['adapter_sha256']=={digest(package/'adapter.json')!r}
with (root/(name+'.supervisor.log')).open('x') as log:
 process=subprocess.Popen([{PYTHON!r},'-u','-B',str(root/'worker.py'),'run','--root',str(root),'--name',name],
  cwd=str(root),stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True,preexec_fn=lambda:os.nice(10))
state={{'pid':process.pid,'started_at':datetime.now(timezone.utc).isoformat(),'name':name,'host':'minipc','remote':str(root)}}
with (root/(name+'.launch.json')).open('x') as f:json.dump(state,f,indent=2)
print(json.dumps(state))
'''
    outcome = json.loads(ssh(script).stdout)
    record = {**intent, **outcome, 'intent_sha256': digest(CLAIMS/(NAME+'.minipc.intent.json')),
        'expected_duration_minutes': [5, 15], 'estimate_basis': 'Matching 32-game HF shard took 5.3 minutes; first mini-PC whole-game batch, provisional.',
        'hard_timeout_seconds': 18000, 'progress_log': REMOTE+'/outputs/'+NAME+'/runner.log'}
    save(RECORD, record); print(json.dumps(record), flush=True)


def status():
    record = read(RECOVERY if RECOVERY.exists() else RECORD); assert record['name'] == NAME
    script = f'''import subprocess,json
from pathlib import Path
result=json.loads(subprocess.check_output([{PYTHON!r},'-u','-B',{(REMOTE+'/worker.py')!r},'status','--root',{REMOTE!r},'--name',{NAME!r}],text=True))
pid={record['pid']}
try:
 args=Path('/proc/'+str(pid)+'/cmdline').read_bytes().split(b'\\0')
 alive={(REMOTE+'/worker.py').encode()!r} in args and {NAME.encode()!r} in args and b'run' in args
except (FileNotFoundError,ProcessLookupError):alive=False
result.update(pid=pid,supervisor_alive=alive,started_at={record['started_at']!r})
print(json.dumps(result))
'''
    result = json.loads(ssh(script).stdout)
    (LOCAL/'last-status.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result), flush=True); return result


def recover_preexecution():
    """One explicit environment repair, only when no game output was created."""
    original = read(RECORD); pilots_checked()
    assert not RECOVERY.exists() and not (LOCAL/'recovery-intent.json').exists()
    assert original['pid'] == 118249 and original['name'] == NAME
    failed = LOCAL/'preexecution-failure-01'; failed.mkdir()
    subprocess.run(['scp', '-q', 'minipc:'+REMOTE+'/'+NAME+'.supervisor.log', str(failed/'supervisor.log')], check=True)
    assert "ModuleNotFoundError: No module named 'huggingface_hub'" in (failed/'supervisor.log').read_text()
    shutil.copyfile(RECORD, failed/'launch.json')
    # No execute command ran: the wrapper validates before creating its output.
    script = f'''import os,subprocess,sys,json
from pathlib import Path
root=Path({REMOTE!r}); name={NAME!r}
assert not Path('/proc/{original['pid']}').exists()
assert not (root/'outputs'/name).exists()
env={{**os.environ,'PYTHONPATH':{DEPS!r},'HF_HUB_OFFLINE':'1'}}
code="""import sys,json
from pathlib import Path
sys.path.insert(0,{REMOTE!r})
import worker
root=Path({REMOTE!r}); config,protocol=worker.checked(root)
row=next(r for r in protocol['rows'] if r['name']=={NAME!r})
import huggingface_hub
import subprocess
subprocess.run(worker.command(root,row,protocol,root/'outputs'/{NAME!r}),check=True,env=worker.environment(root),stdout=subprocess.DEVNULL)
print(json.dumps({{'validated_only':True,'game_output_absent':not (root/'outputs'/{NAME!r}).exists(),'huggingface_hub':huggingface_hub.__version__}}))
"""
subprocess.run([{PYTHON!r},'-B','-c',code],env=env,check=True)
'''
    check = json.loads(ssh(script).stdout)
    assert check['validated_only'] and check['game_output_absent']
    save(failed/'verified-no-execution.json', check)
    save(LOCAL/'recovery-intent.json', {'created_at': now(), 'original_launch_sha256': digest(RECORD),
        'original_failure_log_sha256': digest(failed/'supervisor.log'), 'no_game_execution_verified': check,
        'change': 'Add existing huggingface_hub dependency directory to PYTHONPATH; runtime/models/contracts unchanged.',
        'manager_sha256': digest(__file__), 'automatic_game_retries': False})
    script = f'''import os,json,subprocess
from pathlib import Path
from datetime import datetime,timezone
root=Path({REMOTE!r});name={NAME!r}
assert not Path('/proc/{original['pid']}').exists() and not (root/'outputs'/name).exists()
env={{**os.environ,'PYTHONPATH':{DEPS!r},'HF_HUB_OFFLINE':'1'}}
with (root/(name+'.recovery-1.supervisor.log')).open('x') as log:
 process=subprocess.Popen([{PYTHON!r},'-u','-B',str(root/'worker.py'),'run','--root',str(root),'--name',name],
  cwd=str(root),env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True,preexec_fn=lambda:os.nice(10))
result={{'pid':process.pid,'started_at':datetime.now(timezone.utc).isoformat(),'name':name,'host':'minipc','remote':str(root)}}
with (root/(name+'.recovery-1.launch.json')).open('x') as f:json.dump(result,f,indent=2)
print(json.dumps(result))
'''
    result = json.loads(ssh(script).stdout)
    save(RECOVERY, {**original, **result, 'original_launch_sha256': digest(RECORD),
        'recovery_intent_sha256': digest(LOCAL/'recovery-intent.json'), 'dependency_directory': DEPS,
        'original_attempt_games': 0, 'original_pid': original['pid'], 'manager_sha256': digest(__file__)})
    print(json.dumps(result), flush=True)


def collect():
    state = status(); assert not state['supervisor_alive'] and state['terminal']['complete']
    raw = LOCAL/'collected'/NAME
    raw.mkdir(parents=True, exist_ok=True)
    subprocess.run(['rsync', '-a', 'minipc:'+REMOTE+'/outputs/'+NAME+'/', str(raw)+'/'], check=True)
    manifest = read(raw/'manifest.json')
    assert set(manifest) == {str(p.relative_to(raw)) for p in raw.rglob('*') if p.is_file() and p.name != 'manifest.json'}
    assert all(digest(raw/n) == h for n, h in manifest.items())
    report = LOCAL/'audit.json'
    if not report.exists():
        subprocess.run([sys.executable, '-B', str(STRONG/'audit_nomination_development_v1.py'),
            '--artifact', str(PREP/'artifact'), '--bundle', str(PREP/'bundle'), '--raw', str(raw), '--name', NAME,
            '--output', str(report)], check=True)
    audit = read(report)
    assert audit['independently_audited'] and audit['caps'] == 0 and audit['games'] == 32
    assert audit['auditor_sha256'] == digest(STRONG/'audit_nomination_development_v1.py')
    assert audit['raw_manifest_sha256'] == digest(raw/'manifest.json')
    print({'independently_audited_games': audit['games'], 'seconds': audit['seconds'], 'qualified': False})


if __name__ == '__main__':
    p = argparse.ArgumentParser(__doc__); p.add_argument('operation', choices=['prepare', 'launch', 'status', 'collect', 'recover-preexecution'])
    globals()[p.parse_args().operation.replace('-', '_')]()
