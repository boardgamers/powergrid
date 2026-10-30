"""Prepare/launch once, observe and independently collect a fixed two-lane run."""
import argparse
from fractions import Fraction
import json
from pathlib import Path
import subprocess
import tarfile

from manage_sealed_target_pilot_v1 import ssh, environment_code, RUNTIME, PYTHON, NODE
from run_sealed_target_quality_v1 import read, save, digest, now, check_result, compare_halves

ROOT = Path(__file__).resolve().parents[2]
LOCAL = ROOT/'ai/runs/sealed-target-quality-v1'
REMOTE = '/home/coyotte508/powergrid-ai-sealed-target-quality-v1'
RECORD = ROOT/'ai/strong/sealed-target-quality-launch-v1.json'


def prepare():
    package = LOCAL/'package'; protocol = read(package/'protocol.json')
    assert read(package/'preflight.json')['complete'] and not (LOCAL/'package.tgz').exists()
    assert digest(ROOT/'ai/strong/run_sealed_target_quality_v1.py') == protocol['worker_sha256']
    files = ['worker.py', 'roots.json', 'protocol.json']
    with tarfile.open(LOCAL/'package.tgz', 'w:gz') as f:
        for name in files: f.add(package/name, arcname=name, recursive=False)
    save(LOCAL/'package-receipt.json', {'files': {n: digest(package/n) for n in files}, 'sha256': digest(LOCAL/'package.tgz')})
    ssh(f'from pathlib import Path\nassert not Path({REMOTE!r}).exists() and not Path({(REMOTE+".tgz")!r}).exists()\n')
    subprocess.run(['scp', '-q', str(LOCAL/'package.tgz'), 'minipc:'+REMOTE+'.tgz'], check=True)
    node = read(ROOT/'ai/strong/node-runtime-cache-v1.json')
    result = ssh(f'''import os,json,hashlib,tarfile,subprocess
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
    ready = json.loads(result)
    assert ready['complete'] and ready['roots'] == 10 and ready['new_rollouts'] == 0
    assert ready['protocol_sha256'] == digest(package/'protocol.json')
    save(LOCAL/'remote-preflight.json', ready)
    print({'target_preflight': True, 'roots': 10, 'new_rollouts': 0}, flush=True)


def launch():
    assert not RECORD.exists() and not (LOCAL/'launch-intent.json').exists()
    protocol = read(LOCAL/'package/protocol.json'); ready = read(LOCAL/'remote-preflight.json')
    assert ready['complete'] and ready['protocol_sha256'] == digest(LOCAL/'package/protocol.json')
    intent = {'created_at': now(), 'remote': REMOTE, 'runtime': RUNTIME, 'protocol_sha256': ready['protocol_sha256'],
        'planned_rollouts': protocol['planned_rollouts'], 'automatic_retries': False, 'manager_sha256': digest(__file__),
        'transport_helper_sha256': digest(ROOT/'ai/strong/manage_sealed_target_pilot_v1.py')}
    save(LOCAL/'launch-intent.json', intent)
    result = ssh(f'''import os,json,subprocess,hashlib
from pathlib import Path
from datetime import datetime,timezone
root=Path({REMOTE!r})
assert not any((root/n).exists() for n in ('launch.json','execution.json','lane-0.log','lane-1.log','state.json'))
assert hashlib.sha256((root/'protocol.json').read_bytes()).hexdigest()=={intent['protocol_sha256']!r}
assert json.loads((root/'preflight.json').read_text())['protocol_sha256']=={intent['protocol_sha256']!r}
{environment_code()}
with (root/'supervisor.log').open('x') as log:
 child=subprocess.Popen([{PYTHON!r},'-u','-B',str(root/'worker.py'),'supervise','--root',str(root),'--runtime',{RUNTIME!r}],
  env=env,cwd=str(root),stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True,preexec_fn=lambda:os.nice(10))
record={{'pid':child.pid,'started_at':datetime.now(timezone.utc).isoformat(),'host':'minipc'}}
with (root/'launch.json').open('x') as f:json.dump(record,f,indent=2)
print(json.dumps(record))
''')
    record = {**intent, **json.loads(result), 'expected_hours': protocol['estimate_hours'],
        'hard_timeout_seconds': protocol['hard_timeout_seconds'], 'lanes': 2, 'workers_per_lane': 4,
        'suggested_ping_paris': protocol['suggested_ping_paris'],
        'scope': 'Ten-root target reliability assessment, not gameplay qualification or gradient training.'}
    save(RECORD, record); print(json.dumps(record), flush=True)


def status():
    record = read(RECORD)
    observed = json.loads(ssh(f'''from pathlib import Path
import json
root=Path({REMOTE!r});pid={record['pid']}
try:args=Path('/proc/'+str(pid)+'/cmdline').read_bytes().split(b'\\0')
except (FileNotFoundError,ProcessLookupError):args=[]
rows=[]
for lane in range(2):
 p=root/f'lane-{{lane}}.log'
 if not p.exists():continue
 for line in p.read_text().splitlines():
  try:r=json.loads(line)
  except ValueError:continue
  if isinstance(r,dict) and 'rollouts' in r:rows.append({{'lane':lane,**r}})
print(json.dumps({{'pid':pid,'supervisor_alive':{(REMOTE+'/worker.py').encode()!r} in args and b'supervise' in args,
 'completed_components':len(rows),'completed_rollouts':sum(r['rollouts'] for r in rows),'progress':rows,
 'terminal':json.loads((root/'state.json').read_text()) if (root/'state.json').exists() else None}}))
'''))
    (LOCAL/'last-status.json').write_text(json.dumps(observed, indent=2)+'\n')
    print(json.dumps(observed), flush=True); return observed


def collect():
    observed = status()
    assert observed['terminal'] is not None and not observed['supervisor_alive'], 'Original run still active'
    target = LOCAL/'collected'; assert not target.exists(), 'Inspect prior collection before retry'
    subprocess.run(['scp', '-q', '-r', 'minipc:'+REMOTE, str(target)], check=True)
    assert read(target/'state.json') == observed['terminal']
    assert observed['terminal']['complete'], 'Preserve failure and partial evidence; never resubmit automatically'
    protocol = read(target/'protocol.json'); roots = read(target/'roots.json')
    assert digest(target/'protocol.json') == read(RECORD)['protocol_sha256']
    assert digest(target/'roots.json') == protocol['roots_sha256']
    assert digest(target/'worker.py') == protocol['worker_sha256']
    reports = []; total = 0
    for i, root in enumerate(roots):
        worlds = {}; audits = {}; files = {}
        for begin in protocol['begins']:
            for mode in protocol['modes']:
                path = target/f'root-{i:02d}-{mode}-{begin}.json'
                check = check_result(read(path), root, mode, begin, worlds)
                assert check == read(path.with_suffix('.audit.json'))
                audits[f'{mode}-{begin}'] = check; files[path.name] = digest(path)
                total += check['rollouts']
        assert set(worlds) == set(range(4, 60))
        reports.append({'rootId': root['rootId'], 'players': root['players'], 'variant': root['variant'],
            'raw_files': files, 'audits': audits, 'cross_fit': compare_halves(root, audits)})
    assert total == protocol['planned_rollouts'] == 6160
    for lane in range(2):
        done = read(target/f'lane-{lane}-complete.json')
        expected = sum(112 * len(roots[i]['options']) for i in protocol['lane_roots'][lane])
        assert done['complete'] and done['new_rollouts'] == expected and done['protocol_sha256'] == digest(target/'protocol.json')
    summary = {}
    for selector in (*protocol['modes'], 'equal_mixture'):
        rows = [row for r in reports for row in r['cross_fit'] if row['selector'] == selector]
        summary[selector] = {'root_directions': len(rows), 'overrides': sum(r['overridden'] for r in rows),
            'mean_selection_margin': str(sum((Fraction(r['selection_margin']) for r in rows), Fraction()) / len(rows)),
            'mean_heldout_margins': {m: str(sum((Fraction(r['heldout_margins'][m]) for r in rows), Fraction()) / len(rows)) for m in protocol['modes']}}
    save(ROOT/'ai/strong/sealed-target-quality-complete-v1.json', {'created_at': now(), 'complete': True,
        'roots': 10, 'reports': reports, 'summary': summary, 'rollouts': total, 'caps': 0,
        'protocol_sha256': digest(target/'protocol.json'), 'seconds': observed['terminal']['seconds'],
        'new_gradients': 0, 'qualified': False, 'reserved_final_seeds_used': False,
        'interpretation': 'Conditional sampled terminal-credit margins on ten training roots. Root pairs are dependent; not game win rates, a model selection gate or broadly representative training targets.'})


if __name__ == '__main__':
    p = argparse.ArgumentParser(__doc__)
    p.add_argument('operation', choices=['prepare', 'launch', 'status', 'collect'])
    globals()[p.parse_args().operation]()
