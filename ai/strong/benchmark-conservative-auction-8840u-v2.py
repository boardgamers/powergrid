"""Prepare and observe one exact-policy saved-position benchmark per host."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile

from conservative_auction_cpu_v2 import ARMS, FIXTURES_SHA, RUNTIME_SHA, select_fixtures, project_cases, read, digest, write
from public_policy_final_audit_v1 import artifact_identity

ROOT = Path(__file__).resolve().parents[2]
PREP = ROOT/'ai/runs/conservative-auction-8840u-prepared-v2'
LOCAL = ROOT/'ai/runs/conservative-auction-8840u-local-v2'
COLLECTED = ROOT/'ai/runs/conservative-auction-8840u-collected-v2'
GUARD = ROOT/'ai/strong/conservative-auction-8840u-launch-v2.json'
REMOTE = '/home/coyotte508/powergrid-ai-conservative-auction-8840u-v2'
PYTHON = '/home/coyotte508/powergrid-ai-baseline/.venv/bin/python'
DEPENDENCIES = '/home/coyotte508/powergrid-ai-surrogate-opponent-8840u-v1/dependencies'
RUNNER = Path(__file__).with_name('conservative_auction_cpu_v2.py')


def new_json(path, value):
    with Path(path).open('x') as stream: json.dump(value, stream, indent=2, allow_nan=False); stream.write('\n')


def prepare():
    assert not any(p.exists() for p in (PREP, LOCAL, GUARD)), 'Inspect existing benchmark preparation'
    old = ROOT/'ai/runs/conservative-auction-runtime-prepared-v2'
    source = read(ROOT/'ai/strong/conservative-auction-runtime-source-v2.json')
    assert digest(old/'source/source-manifest.json') == source['source_manifest_sha256']
    assert all(digest(old/'source'/n) == h for n, h in read(old/'source/source-manifest.json').items())
    pool = ROOT/'ai/runs/policy-iteration-trained-8840u-prepared-v2/fixtures.jsonl'
    cases = project_cases(select_fixtures(pool), old/'source/artifact')
    package = PREP/'package'; package.mkdir(parents=True)
    shutil.copytree(old/'source/artifact', package/'artifact')
    assert digest(package/'artifact/manifest.json') == RUNTIME_SHA
    ids = {a: artifact_identity(package/'artifact', f'policies/{a}.json') for a in ARMS}
    new_json(package/'cases.json', cases); shutil.copyfile(RUNNER, package/'benchmark.py')
    manifest = {'version': 2, 'fixture_pool_sha256': FIXTURES_SHA, 'runtime_manifest_sha256': RUNTIME_SHA,
        'source': source, 'positions': 100, 'requests': 300, 'arms': list(ARMS), 'identities': ids,
        'runner_sha256': digest(RUNNER), 'selection': 'First non-forced saved menu per count/rule/stage, projected with the exact frozen publicState; legal menu unchanged; no outcomes used.',
        'public_projection_sha256': digest(package/'artifact/ai/strong/sealed-policy-beliefs.cjs'),
        'files': {str(p.relative_to(package)): digest(p) for p in sorted(package.rglob('*')) if p.is_file()},
        'new_strength_games': 0, 'qualification_eligible': False, 'reserved_final_seeds_used': False}
    new_json(package/'benchmark-manifest.json', manifest)
    with tarfile.open(PREP/'package.tgz', 'w:gz') as bundle:
        for p in sorted(package.rglob('*')):
            if p.is_file():
                assert not p.is_symlink()
                info = bundle.gettarinfo(p, arcname=str(p.relative_to(package)))
                info.uid = info.gid = info.mtime = 0; info.uname = info.gname = ''
                with p.open('rb') as stream: bundle.addfile(info, stream)
    prepared = {'package_sha256': digest(PREP/'package.tgz'), 'manifest_sha256': digest(package/'benchmark-manifest.json'),
        'runner_sha256': digest(RUNNER), 'manager_sha256': digest(__file__), 'positions': 100, 'requests_per_host': 300,
        'cases_sha256': digest(package/'cases.json'), 'runtime_manifest_sha256': RUNTIME_SHA,
        'new_hf_jobs': 0, 'qualification_eligible': False, 'reserved_final_seeds_used': False}
    new_json(PREP/'prepared.json', prepared); print(json.dumps(prepared), flush=True)


def checked():
    p = read(PREP/'prepared.json')
    assert p['runner_sha256'] == digest(RUNNER) and p['manager_sha256'] == digest(__file__)
    assert p['manifest_sha256'] == digest(PREP/'package/benchmark-manifest.json')
    assert p['package_sha256'] == digest(PREP/'package.tgz')
    return p


def local():
    p = checked(); assert not LOCAL.exists()
    new_json(PREP/'local-intent.json', {'prepared_sha256': digest(PREP/'prepared.json'), 'pid': __import__('os').getpid()})
    with (PREP/'local.log').open('x') as log:
        subprocess.run([sys.executable, '-u', '-B', str(PREP/'package/benchmark.py'), '--package', str(PREP/'package'),
            '--output', str(LOCAL)], cwd='/tmp', stdout=log, stderr=subprocess.STDOUT, check=True)
    s = read(LOCAL/'status.json'); assert s['passed'] and s['completed_requests'] == 300
    print(json.dumps({'local_complete': True, 'requests': 300, 'seconds': s['seconds']}), flush=True)


def launch():
    p = checked(); reference = read(LOCAL/'status.json')
    assert reference['stage'] == 'completed' and reference['passed'] and reference['completed_requests'] == 300
    assert reference['manifest_sha256'] == p['manifest_sha256']
    assert all(digest(LOCAL/n) == h for n, h in reference['output_hashes'].items())
    assert not GUARD.exists(), 'Inspect original target launch; never duplicate it'
    record = {'stage': 'launch_intent', 'host': 'minipc', 'directory': REMOTE, **p,
              'local_status_sha256': digest(LOCAL/'status.json'), 'new_hf_jobs': 0}
    new_json(GUARD, record)
    try:
        # The destination is unique to this benchmark; existing target runs remain untouched.
        check = f"from pathlib import Path; assert not Path({REMOTE!r}).exists() and not Path({(REMOTE+'.tgz')!r}).exists()"
        subprocess.run(['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10', 'minipc', 'python3 -'], input=check, text=True, check=True)
        subprocess.run(['scp', '-q', str(PREP/'package.tgz'), 'minipc:'+REMOTE+'.tgz'], check=True)
        script = f'''import subprocess,tarfile,json,hashlib,os
from pathlib import Path
root=Path({REMOTE!r}); archive=Path({(REMOTE+'.tgz')!r}); assert not root.exists()
assert hashlib.sha256(archive.read_bytes()).hexdigest()=={p['package_sha256']!r}
root.mkdir()
with tarfile.open(archive) as bundle: bundle.extractall(root,filter='data')
env={{**os.environ,'PYTHONPATH':{DEPENDENCIES!r},'HF_HUB_OFFLINE':'1','PYTHONDONTWRITEBYTECODE':'1'}}
subprocess.run([{PYTHON!r},'-B','-c','import huggingface_hub; assert huggingface_hub.__version__ == "2.0.0"'],env=env,check=True)
with (root/'run.log').open('x') as log:
 child=subprocess.Popen([{PYTHON!r},'-u','-B',str(root/'benchmark.py'),'--package',str(root),'--output',str(root/'output'),'--require-cpu','8840U'],cwd='/tmp',env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
value={{'pid':child.pid,'directory':str(root)}}
(root/'target-launch.json').write_text(json.dumps(value)); print(json.dumps(value))
'''
        response = subprocess.run(['ssh', '-o', 'BatchMode=yes', 'minipc', 'python3 -'], input=script,
                                  text=True, capture_output=True, check=True)
        target = json.loads(response.stdout); record.update(stage='launched', pid=target['pid'])
    except BaseException as error:
        record.update(stage='launch_unknown', failure_type=type(error).__name__); raise
    finally: write(GUARD, record)
    print(json.dumps(record), flush=True)


def inspect():
    guard = read(GUARD); assert guard['stage'] == 'launched'
    script = f'''import json
from pathlib import Path
root=Path({REMOTE!r}); proc=Path('/proc')/{str(guard['pid'])!r}/'cmdline'; path=root/'output/status.json'
print(json.dumps({{'pid':{guard['pid']},'command_matches':proc.exists() and str(root/'benchmark.py').encode() in proc.read_bytes(),
 'status':json.loads(path.read_text()) if path.exists() else None,'log_tail':(root/'run.log').read_text()[-2000:]}}))
'''
    result = subprocess.run(['ssh', '-o', 'BatchMode=yes', 'minipc', 'python3 -'], input=script,
                            text=True, capture_output=True, check=True)
    state = json.loads(result.stdout); write(PREP/'last-target-status.json', state)
    print(json.dumps({'pid': state['pid'], 'live': state['command_matches'],
        'status': {k: state['status'][k] for k in ('stage', 'processor', 'completed_requests', 'passed') if k in (state['status'] or {})},
        'log_tail': state['log_tail']}), flush=True)
    return state


def collect():
    state = inspect(); s = state['status']
    assert not state['command_matches'] and s and s['stage'] == 'completed' and s['passed']
    assert '8840U' in s['processor'] and s['completed_requests'] == 300
    assert not COLLECTED.exists(), 'Preserve existing collection'
    COLLECTED.mkdir()
    for name in ('output', 'run.log', 'target-launch.json'):
        subprocess.run(['scp', '-qr', 'minipc:'+REMOTE+'/'+name, str(COLLECTED)], check=True)
    # Audit both hosts in a fresh interpreter, ensuring imports come only from the package.
    script = '''import sys,json
from pathlib import Path
package,local,target=map(Path,sys.argv[1:]);sys.path.insert(0,str(package));import benchmark as b
sys.path.insert(0,str(package/'artifact/ai/strong'));from public_policy_arena_v1 import semantic
manifest=b.checked_package(package); cases={c['name']:c for c in b.read(package/'cases.json')}
all_rows=[]
for directory in (local,target):
 status=b.read(directory/'status.json');assert status['stage']=='completed' and status['passed'] and status['completed_requests']==300
 assert status['manifest_sha256']==b.digest(package/'benchmark-manifest.json')
 assert all(b.digest(directory/n)==h for n,h in status['output_hashes'].items())
 rows=[json.loads(l) for l in (directory/'receipts.jsonl').read_text().splitlines()]
 assert len(rows)==300 and {(r['arm'],r['case']) for r in rows}=={(a,c) for a in b.ARMS for c in cases}
 for r in rows: b.verify_response(cases[r['case']],r['arm'],r['response'],manifest['identities'][r['arm']])
 all_rows.append({(r['arm'],r['case']):r for r in rows})
for key in all_rows[0]: assert semantic(all_rows[0][key]['response'])==semantic(all_rows[1][key]['response']),key
print(json.dumps({'independent_receipts_audited':600,'exact_cross_host_responses':300,'caps':0}))
'''
    with (COLLECTED/'independent-audit.log').open('x') as log:
        subprocess.run([sys.executable, '-B', '-c', script, str(PREP/'package'), str(LOCAL), str(COLLECTED/'output')],
                       cwd='/tmp', stdout=log, stderr=subprocess.STDOUT, check=True)
    rows = [json.loads(l) for l in (COLLECTED/'output/receipts.jsonl').read_text().splitlines()]
    import numpy as np
    timings = {}
    for arm in ARMS:
        groups = {}
        for stage in ('all', 'choose', 'bid', 'resources', 'building', 'bureaucracy'):
            selected = [r for r in rows if r['arm'] == arm and (stage == 'all' or r['case'].endswith('-'+stage)) and not r['first_request']]
            values = [r['round_trip_ms'] for r in selected]
            groups[stage] = {'requests': len(values), 'median_ms': float(np.median(values)),
                             'p95_ms': float(np.percentile(values, 95)), 'max_ms': max(values)}
        timings[arm] = {'warm': groups, 'cold_process_plus_request_ms': next(r['cold_process_plus_request_ms'] for r in rows if r['arm'] == arm and r['first_request'])}
    assessment = {'complete': True, 'processor': s['processor'], 'requests_per_host': 300, 'caps': 0,
        'exact_cross_host_responses': 300, 'timings': timings, 'target_status_sha256': digest(COLLECTED/'output/status.json'),
        'local_status_sha256': digest(LOCAL/'status.json'), 'manifest_sha256': s['manifest_sha256'],
        'scope': s['scope'], 'qualification_eligible': False, 'reserved_final_seeds_used': False}
    new_json(COLLECTED/'assessment.json', assessment); print(json.dumps(assessment), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__); parser.add_argument('operation', choices=['prepare', 'local', 'launch', 'inspect', 'collect'])
    globals()[parser.parse_args().operation]()
