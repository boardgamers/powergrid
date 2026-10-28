"""Prepare, launch once and audit a current-engine fixed-position CPU benchmark."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile

import current_auction_cpu_v1 as bench

ROOT = Path(__file__).resolve().parents[2]
PREP = ROOT / 'ai/runs/current-auction-8840u-prepared-v1'
COLLECTED = ROOT / 'ai/runs/current-auction-8840u-collected-v1'
GUARD = ROOT / 'ai/strong/current-auction-8840u-launch-v1.json'
REMOTE = '/home/coyotte508/powergrid-ai-current-auction-8840u-v1'
PYTHON = '/home/coyotte508/powergrid-ai-baseline/.venv/bin/python'
DEPS = '/home/coyotte508/powergrid-ai-surrogate-opponent-8840u-v1/dependencies'
BASE = ROOT / 'ai/runs/current-engine-auction-v2'


def save(path, value):
    with Path(path).open('x') as stream: json.dump(value, stream, indent=2, allow_nan=False); stream.write('\n')


def prepare():
    assert not any(p.exists() for p in (PREP, GUARD, COLLECTED)), 'Inspect original preparation before retry'
    assessment = bench.read(BASE / 'assessment.json')
    assert assessment['passed'] and assessment['counts']['conservative_population']['requests'] == 160
    assert bench.digest(BASE / 'decisions.jsonl') == assessment['receipts_sha256']
    assert bench.digest(BASE / 'artifact/manifest.json') == bench.RUNTIME_SHA
    test = ROOT / 'ai/runs/current-auction-cpu-tests-v1.log'
    assert 'Ran 6 tests' in test.read_text() and test.read_text().rstrip().endswith('OK')
    package = PREP / 'package'; package.mkdir(parents=True)
    save(PREP / 'prepare-intent.json', {'started_at':datetime.now(timezone.utc).isoformat(),
        'existing_assessment_sha256':bench.digest(BASE/'assessment.json'),
        'existing_receipts_sha256':assessment['receipts_sha256'], 'new_filter_requests':140,
        'reused_population_requests':160, 'reused_filter_wrapper_requests':20,
        'new_full_games':0, 'new_hf_jobs':0, 'reserved_final_seeds_used':False})
    shutil.copytree(BASE / 'artifact', package / 'artifact')
    artifact = package / 'artifact'; sys.path.insert(0,str(artifact/'ai/strong'))
    from public_policy_arena_v1 import PublicPolicyProcess
    from public_policy_final_audit_v1 import artifact_identity
    identities = {a:artifact_identity(artifact,f'policies/{a}.json') for a in bench.ARMS}
    assert identities == assessment['identities']
    cases=[]; references={a:{} for a in bench.ARMS}; wrappers={}; counts={a:Counter() for a in bench.ARMS}
    with (BASE / 'decisions.jsonl').open() as stream:
        for line in stream:
            row=json.loads(line)
            if row['arm']=='filter': wrappers[row['name']]=row; continue
            assert row['arm']=='conservative_population'
            q=row['request']; state=q['state']; name=row['name']
            group='canonical' if name.startswith('cpu-') else 'wrapper' if name.endswith(('pending-actor','wrapper-auto-pass')) else 'discount'
            stage=name.rsplit('-',1)[1] if group=='canonical' else 'bid' if group=='wrapper' else 'choose'
            case={'name':name,'group':group,'stage':stage,'players':len(state['players']),
                  'variant':state['options']['variant'],'sealed':state['options']['fastBid'],
                  'request':q,'legal':row['legal'],'player_order':row['response']['playerOrder']}
            counts['conservative_population'].update(bench.verify_response(case,'conservative_population',row['response'],identities['conservative_population']))
            references['conservative_population'][name]=bench.response_hash(row['response']); cases.append(case)
    assert len(cases)==160 and len(wrappers)==20
    calls=0
    with (package/'filter-reference.jsonl').open('x') as raw, (PREP/'filter-reference.stderr.log').open('x') as stderr:
        process=PublicPolicyProcess(artifact,'policies/filter.json',stderr)
        try:
            for case in cases:
                name=case['name']
                if name in wrappers:
                    row=wrappers[name]; assert row['request']==case['request'] and row['legal']==case['legal']
                    response=row['response']; origin='existing_current_engine_wrapper_receipt'
                else:
                    response=process.call(case['request']); calls+=1; origin='new_current_engine_filtered_model_only'
                counts['filter'].update(bench.verify_response(case,'filter',response,identities['filter']))
                references['filter'][name]=bench.response_hash(response)
                raw.write(json.dumps({'case':name,'origin':origin,'response':response},allow_nan=False)+'\n'); raw.flush()
        finally: process.close()
    assert calls==140 and counts['conservative_population']['rollouts']==2960
    assert counts['conservative_population']['neural_decisions']==512203
    bench.validate_cases(cases,references)
    save(package/'cases.json',cases); save(package/'reference.json',references)
    shutil.copyfile(bench.__file__,package/'benchmark.py')
    provenance={'assessment_sha256':bench.digest(BASE/'assessment.json'),
        'existing_receipts_sha256':assessment['receipts_sha256'], 'new_filter_requests':calls,
        'reused_population_requests':160,'reused_filter_wrapper_requests':20,
        'filter_reference_sha256':bench.digest(package/'filter-reference.jsonl')}
    manifest={'version':1,'runtime_manifest_sha256':bench.RUNTIME_SHA,'arms':list(bench.ARMS),
        'positions':160,'requests':320,'identities':identities,'runner_sha256':bench.digest(bench.__file__),
        'reference_provenance':provenance,'reference_counts':{a:dict(c) for a,c in counts.items()},
        'selection':'All 160 already audited current-engine population cases: 100 canonical, 40 discount-menu, 20 actual-wrapper cases; no outcomes used.',
        'files':{str(p.relative_to(package)):bench.digest(p) for p in sorted(package.rglob('*')) if p.is_file()},
        'qualification_eligible':False,'reserved_final_seeds_used':False}
    save(package/'benchmark-manifest.json',manifest); bench.checked_package(package)
    assert bench.digest(BASE/'decisions.jsonl')==assessment['receipts_sha256']
    with tarfile.open(PREP/'package.tgz','w:gz') as bundle:
        for p in sorted(package.rglob('*')):
            if not p.is_file():continue
            assert not p.is_symlink(); info=bundle.gettarinfo(p,arcname=str(p.relative_to(package)))
            info.uid=info.gid=info.mtime=0;info.uname=info.gname=''
            with p.open('rb') as stream:bundle.addfile(info,stream)
    prepared={'package_sha256':bench.digest(PREP/'package.tgz'),'package_bytes':(PREP/'package.tgz').stat().st_size,
        'manifest_sha256':bench.digest(package/'benchmark-manifest.json'),'runner_sha256':bench.digest(bench.__file__),
        'manager_sha256':bench.digest(__file__),'test_log_sha256':bench.digest(test),
        'cases_sha256':bench.digest(package/'cases.json'),'reference_sha256':bench.digest(package/'reference.json'),
        'runtime_manifest_sha256':bench.RUNTIME_SHA,'positions':160,'requests':320,
        'reference_provenance':provenance,'new_hf_jobs':0,'new_full_games':0,
        'qualification_eligible':False,'reserved_final_seeds_used':False}
    save(PREP/'prepared.json',prepared);print(json.dumps(prepared),flush=True)


def checked():
    p=bench.read(PREP/'prepared.json')
    assert p['runner_sha256']==bench.digest(bench.__file__) and p['manager_sha256']==bench.digest(__file__)
    assert p['manifest_sha256']==bench.digest(PREP/'package/benchmark-manifest.json')
    assert p['package_sha256']==bench.digest(PREP/'package.tgz')
    assert p['test_log_sha256']==bench.digest(ROOT/'ai/runs/current-auction-cpu-tests-v1.log')
    bench.checked_package(PREP/'package');return p


def ssh(script):
    return subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','minipc','python3 -'],
                          input=script,text=True,capture_output=True,check=True)


def launch():
    p=checked();assert not GUARD.exists(),'Inspect original target launch; never duplicate it'
    guard={'stage':'launch_intent','host':'minipc','directory':REMOTE,**p};save(GUARD,guard)
    try:
        ssh(f'from pathlib import Path; assert not Path({REMOTE!r}).exists() and not Path({(REMOTE+".tgz")!r}).exists()')
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
 child=subprocess.Popen([{PYTHON!r},'-u','-B',str(root/'benchmark.py'),'--package',str(root),'--output',str(root/'output'),'--require-cpu','8840U'],cwd='/tmp',env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
value={{'pid':child.pid,'directory':str(root)}}
(root/'target-launch.json').write_text(json.dumps(value));print(json.dumps(value))
'''
        remote=json.loads(ssh(script).stdout);guard.update(stage='launched',pid=remote['pid'])
    except BaseException as error:
        guard.update(stage='launch_unknown',failure_type=type(error).__name__);raise
    finally:bench.write(GUARD,guard)
    print(json.dumps(guard),flush=True)


def inspect():
    guard=bench.read(GUARD);assert guard['stage']=='launched'
    script=f'''from pathlib import Path
import json
root=Path({REMOTE!r});proc=Path('/proc')/{str(guard['pid'])!r}/'cmdline';status=root/'output/status.json'
print(json.dumps({{'pid':{guard['pid']},'live':proc.exists() and str(root/'benchmark.py').encode() in proc.read_bytes(),
 'status':json.loads(status.read_text()) if status.exists() else None,'log_tail':(root/'run.log').read_text()[-1600:]}}))
'''
    state=json.loads(ssh(script).stdout);bench.write(PREP/'last-target-status.json',state)
    print(json.dumps({'pid':state['pid'],'live':state['live'],'status':{k:state['status'][k] for k in ('stage','processor','completed_requests','passed') if k in (state['status'] or {})},'log_tail':state['log_tail']}),flush=True)
    return state


def collect():
    p=checked();state=inspect();s=state['status']
    assert not state['live'] and s and s['stage']=='completed' and s['passed']
    assert '8840U' in s['processor'] and s['completed_requests']==320
    assert not COLLECTED.exists(),'Preserve original collection';COLLECTED.mkdir()
    for name in ('output','run.log','target-launch.json'):
        subprocess.run(['scp','-qr','minipc:'+REMOTE+'/'+name,str(COLLECTED)],check=True)
    script='''import json,sys
from pathlib import Path
from collections import Counter
package,out=map(Path,sys.argv[1:]);sys.path.insert(0,str(package));import benchmark as b
manifest=b.checked_package(package);sys.path.insert(0,str(package/'artifact/ai/strong'))
status=b.read(out/'status.json');assert status['stage']=='completed' and status['passed'] and status['completed_requests']==320
assert status['manifest_sha256']==b.digest(package/'benchmark-manifest.json')
assert all(b.digest(out/n)==h for n,h in status['output_hashes'].items())
cases={c['name']:c for c in b.read(package/'cases.json')};reference=b.read(package/'reference.json')
rows=[json.loads(l) for l in (out/'receipts.jsonl').open()];assert len(rows)==320
assert {(r['arm'],r['case']) for r in rows}=={(a,c) for a in b.ARMS for c in cases}
counts=Counter()
for r in rows:
 c=cases[r['case']];assert r['group']==c['group'] and r['stage']==c['stage'] and r['players']==c['players']
 counts.update(b.verify_response(c,r['arm'],r['response'],manifest['identities'][r['arm']]))
 assert b.response_hash(r['response'])==reference[r['arm']][r['case']]==r['semantic_sha256']
assert dict(counts)==status['counts'] and counts['rollout_caps']==0
print(json.dumps({'target_receipts_audited':320,'exact_reference_responses':320,'counts':dict(counts)}))
'''
    with (COLLECTED/'independent-audit.log').open('x') as log:
        subprocess.run([sys.executable,'-B','-c',script,str(PREP/'package'),str(COLLECTED/'output')],cwd='/tmp',stdout=log,stderr=subprocess.STDOUT,check=True)
    rows=[json.loads(l) for l in (COLLECTED/'output/receipts.jsonl').open()]
    import numpy as np
    timings={}
    for arm in bench.ARMS:
        groups={}
        for group in ('canonical','discount','wrapper','all'):
            selected=[r['round_trip_ms'] for r in rows if r['arm']==arm and (group=='all' or r['group']==group) and not r['first_request']]
            groups[group]={'requests':len(selected),'median_ms':float(np.median(selected)),
                           'p95_ms':float(np.percentile(selected,95)),'max_ms':max(selected)}
        canonical_auction=[r['round_trip_ms'] for r in rows if r['arm']==arm and r['group']=='canonical' and r['stage'] in ('choose','bid') and not r['first_request']]
        canonical_other=[r['round_trip_ms'] for r in rows if r['arm']==arm and r['group']=='canonical' and r['stage'] not in ('choose','bid')]
        timings[arm]={'warm_groups':groups,'canonical_warm_auction_median_ms':float(np.median(canonical_auction)),
            'canonical_other_median_ms':float(np.median(canonical_other)),
            'first_request_including_startup_ms':next(r['cold_process_plus_request_ms'] for r in rows if r['arm']==arm and r['first_request'])}
    assessment={'complete':True,'processor':s['processor'],'requests':320,'exact_reference_responses':320,
        'counts':s['counts'],'timings':timings,'seconds':s['seconds'],'target_status_sha256':bench.digest(COLLECTED/'output/status.json'),
        'manifest_sha256':p['manifest_sha256'],'reference_sha256':p['reference_sha256'],
        'scope':s['scope'],'qualification_eligible':False,'reserved_final_seeds_used':False}
    save(COLLECTED/'assessment.json',assessment);print(json.dumps(assessment),flush=True)


if __name__ == '__main__':
    p=argparse.ArgumentParser(__doc__);p.add_argument('operation',choices=['prepare','launch','inspect','collect'])
    globals()[p.parse_args().operation]()
