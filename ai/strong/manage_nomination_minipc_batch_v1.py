"""Finite queue of the three remaining 2p/search arms, with no game retries."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
STRONG = ROOT/'ai/strong'
LOCAL = ROOT/'ai/runs/nomination-discount-minipc-batch-v1'
REMOTE = '/home/coyotte508/powergrid-ai-nomination-development-minipc-batch-v1'
PREVIOUS = '/home/coyotte508/powergrid-ai-nomination-development-minipc-v1'
PYTHON = '/home/coyotte508/powergrid-ai-baseline/.venv/bin/python'
DEPS = '/home/coyotte508/powergrid-ai-surrogate-opponent-8840u-v1/dependencies'
NAMES = [f'pg-nom-dev-v1-{arm}-search-geo-2p' for arm in ('d0-all0', 'd0-all1', 'd1-all0')]
RECORD = STRONG/'nomination-discount-minipc-batch-launch-v1.json'


def read(p): return json.loads(Path(p).read_text())
def digest(p):
    with Path(p).open('rb') as f: return hashlib.file_digest(f, 'sha256').hexdigest()
def save(p, value):
    with Path(p).open('x') as f: json.dump(value, f, indent=2, allow_nan=False); f.write('\n')
def now(): return datetime.now(timezone.utc).isoformat()
def ssh(script):
    return subprocess.run(['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10', 'minipc', 'python3 -'],
                          input=script, text=True, capture_output=True, check=True)
def env(): return {**os.environ, 'PYTHONPATH': DEPS, 'HF_HUB_OFFLINE': '1'}


def remote_prepare(root):
    previous = Path(PREVIOUS); config = read(root/'adapter.json'); original = read(previous/'adapter.json')
    assert digest(previous/'adapter.json') == config['previous_adapter_sha256']
    assert config['authorized_names'] == NAMES and config['files']['batch.py'] == digest(__file__)
    # Copy verified bytes, never hard-link or edit the first run's artifact.
    for name, sha in original['files'].items():
        assert digest(previous/name) == sha
        target = root/name; target.parent.mkdir(parents=True, exist_ok=True)
        assert not target.exists(); shutil.copyfile(previous/name, target)
    for name in ('artifact', 'node'): shutil.copytree(previous/name, root/name)
    sys.path.insert(0, str(root)); import worker
    _, protocol = worker.checked(root)
    ready = read(previous/'ready.json'); assert ready['complete']
    assert ready['adapter_sha256'] == digest(previous/'adapter.json')
    # Existing exact-choice proof applies to the identical artifact/interpreter.
    for name in NAMES:
        row = next(r for r in protocol['rows'] if r['name'] == name)
        subprocess.run(worker.command(root, row, protocol, root/'outputs'/name),
                       env=worker.environment(root), check=True, stdout=subprocess.DEVNULL)
    save(root/'ready.json', {**ready, 'adapter_sha256': digest(root/'adapter.json'),
        'derived_from_ready_sha256': digest(previous/'ready.json'), 'contract_validations': NAMES,
        'source_preflight_unchanged_artifact': True, 'created_at': now()})


def remote_run(root):
    sys.path.insert(0, str(root)); import worker
    config, _ = worker.checked(root); assert config['authorized_names'] == NAMES
    assert read(root/'ready.json')['contract_validations'] == NAMES
    state = {'stage': 'running', 'pid': os.getpid(), 'started_at': now(), 'completed_shards': [],
             'names': NAMES, 'expected_games': 96, 'qualified': False, 'reserved_final_seeds_used': False}
    def update():
        temp = root/'state.tmp'; temp.write_text(json.dumps(state, indent=2)+'\n'); temp.replace(root/'state.json')
    assert not (root/'state.json').exists(); update(); start = time.monotonic()
    try:
        for name in NAMES:
            state['current_name'] = name; update()
            worker.run(root, name)
            state['completed_shards'].append(name); update()
        state['stage'] = 'completed'
    except BaseException as error:
        state.update(stage='failed', failure=type(error).__name__+': '+str(error)); raise
    finally:
        state.update(finished_at=now(), seconds=time.monotonic()-start); update()


def launch():
    from manage_nomination_minipc_v1 import unclaimed, pilots_checked, CLAIMS
    pilots_checked()
    first = ROOT/'ai/runs/nomination-discount-minipc-v1'
    audit = read(first/'audit.json'); assert audit['independently_audited'] and audit['games'] == 32 and audit['caps'] == 0
    assert audit['auditor_sha256'] == digest(STRONG/'audit_nomination_development_v1.py')
    assert not LOCAL.exists() and not RECORD.exists()
    for name in NAMES: unclaimed(CLAIMS, name)
    LOCAL.mkdir(); old = read(first/'package/adapter.json')
    config = {**old, 'created_at': now(), 'authorized_names': NAMES,
        'previous_adapter_sha256': digest(first/'package/adapter.json'), 'manager_sha256': digest(__file__),
        'files': {**old['files'], 'batch.py': digest(__file__)}}
    save(LOCAL/'adapter.json', config)
    ssh(f'from pathlib import Path\np=Path({REMOTE!r});assert not p.exists();p.mkdir()\n')
    subprocess.run(['scp', '-q', str(LOCAL/'adapter.json'), 'minipc:'+REMOTE+'/adapter.json'], check=True)
    subprocess.run(['scp', '-q', __file__, 'minipc:'+REMOTE+'/batch.py'], check=True)
    script = f'''import os,subprocess
from pathlib import Path
root=Path({REMOTE!r})
env={{**os.environ,'PYTHONPATH':{DEPS!r},'HF_HUB_OFFLINE':'1'}}
with (root/'prepare.log').open('x') as log:
 subprocess.run([{PYTHON!r},'-u','-B',str(root/'batch.py'),'remote-prepare','--remote-root',str(root)],env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
print((root/'ready.json').read_text())
'''
    ready = json.loads(ssh(script).stdout); save(LOCAL/'ready.json', ready)
    assert ready['adapter_sha256'] == digest(LOCAL/'adapter.json') and ready['contract_validations'] == NAMES
    for name in NAMES:
        unclaimed(CLAIMS, name)
        save(CLAIMS/(name+'.minipc.intent.json'), {'created_at': now(), 'name': name, 'host': 'minipc',
            'remote': REMOTE, 'protocol_sha256': config['protocol_sha256'], 'adapter_sha256': digest(LOCAL/'adapter.json'),
            'automatic_retries': False, 'qualified': False, 'reserved_final_seeds_used': False})
    save(LOCAL/'launch-intent.json', {'created_at': now(), 'names': NAMES, 'games': 96,
        'protocol_sha256': config['protocol_sha256'], 'manager_sha256': digest(__file__),
        'adapter_sha256': digest(LOCAL/'adapter.json'), 'parent_audit_sha256': digest(first/'audit.json')})
    script = f'''import os,subprocess,json
from pathlib import Path
from datetime import datetime,timezone
root=Path({REMOTE!r});assert not (root/'state.json').exists() and not (root/'launch.json').exists()
env={{**os.environ,'PYTHONPATH':{DEPS!r},'HF_HUB_OFFLINE':'1'}}
with (root/'run.log').open('x') as log:
 p=subprocess.Popen([{PYTHON!r},'-u','-B',str(root/'batch.py'),'remote-run','--remote-root',str(root)],
  env=env,cwd=str(root),stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True,preexec_fn=lambda:os.nice(10))
record={{'pid':p.pid,'started_at':datetime.now(timezone.utc).isoformat(),'host':'minipc','remote':str(root)}}
with (root/'launch.json').open('x') as f:json.dump(record,f,indent=2)
print(json.dumps(record))
'''
    result = json.loads(ssh(script).stdout)
    save(RECORD, {**result, 'names': NAMES, 'games': 96, 'workers': 4, 'shards_run_sequentially': True,
        'launch_intent_sha256': digest(LOCAL/'launch-intent.json'), 'protocol_sha256': config['protocol_sha256'],
        'expected_minutes': [10, 20], 'estimate_basis': 'Parent 32-game shard measured 172.37 seconds on this mini PC; allow overhead/trajectory differences.',
        'automatic_retries': False, 'qualified': False, 'reserved_final_seeds_used': False})
    print(json.dumps(result), flush=True)


def status():
    record = read(RECORD)
    script = f'''import sys,json
from pathlib import Path
root=Path({REMOTE!r});sys.path.insert(0,str(root));import worker
state=json.loads((root/'state.json').read_text());pid={record['pid']}
try:
 args=Path('/proc/'+str(pid)+'/cmdline').read_bytes().split(b'\\0')
 state['supervisor_alive']={(REMOTE+'/batch.py').encode()!r} in args and b'remote-run' in args
except (FileNotFoundError,ProcessLookupError):state['supervisor_alive']=False
state['shards']=[worker.status(root,name) for name in {NAMES!r}]
print(json.dumps(state))
'''
    state = json.loads(ssh(script).stdout)
    (LOCAL/'last-status.json').write_text(json.dumps(state, indent=2)+'\n')
    print(json.dumps(state), flush=True); return state


def collect():
    state = status(); reports = []
    for shard in state['shards']:
        if not shard.get('terminal', {}).get('complete'): continue
        name = shard['name']; raw = LOCAL/'collected'/name; raw.mkdir(parents=True, exist_ok=True)
        subprocess.run(['rsync', '-a', 'minipc:'+REMOTE+'/outputs/'+name+'/', str(raw)+'/'], check=True)
        pins = read(raw/'manifest.json')
        assert set(pins) == {str(p.relative_to(raw)) for p in raw.rglob('*') if p.is_file() and p.name != 'manifest.json'}
        assert all(digest(raw/n) == h for n, h in pins.items())
        report = LOCAL/(name+'.audit.json')
        if not report.exists():
            subprocess.run([sys.executable, '-B', str(STRONG/'audit_nomination_development_v1.py'),
                '--artifact', str(ROOT/'ai/runs/nomination-discount-development-v1/artifact'),
                '--bundle', str(ROOT/'ai/runs/nomination-discount-development-v1/bundle'),
                '--raw', str(raw), '--name', name, '--output', str(report)], check=True)
        audit = read(report)
        assert audit['independently_audited'] and audit['games'] == 32 and audit['caps'] == 0
        assert audit['auditor_sha256'] == digest(STRONG/'audit_nomination_development_v1.py')
        assert audit['raw_manifest_sha256'] == digest(raw/'manifest.json')
        reports.append({'name': name, 'games': 32, 'audit_sha256': digest(report)})
    (LOCAL/'collection.json').write_text(json.dumps({'audits': reports, 'games': sum(r['games'] for r in reports)}, indent=2)+'\n')


if __name__ == '__main__':
    p = argparse.ArgumentParser(__doc__); p.add_argument('operation', choices=['launch', 'status', 'collect', 'remote-prepare', 'remote-run'])
    p.add_argument('--remote-root', type=Path); a = p.parse_args()
    if a.operation.startswith('remote-'): globals()[a.operation.replace('-', '_')](a.remote_root)
    else: globals()[a.operation]()
