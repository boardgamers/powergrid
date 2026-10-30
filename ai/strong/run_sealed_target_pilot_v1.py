"""Bounded training-position diagnostic using unchanged current-engine policies."""
import argparse
from datetime import datetime, timezone
from fractions import Fraction
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time


def read(p): return json.loads(Path(p).read_text())
def digest(p):
    with Path(p).open('rb') as f: return hashlib.file_digest(f, 'sha256').hexdigest()
def save(p, value):
    with Path(p).open('x') as f: json.dump(value, f, indent=2, allow_nan=False); f.write('\n')
def now(): return datetime.now(timezone.utc).isoformat()


def check_result(result, root, worlds=None):
    options = root['options']; seat = root['request']['player']; worlds = {} if worlds is None else worlds
    assert result['options'] == options and result['samples'] == result['count'] == 4 and result['begin'] == 0
    assert result['usable'] and result['caps'] == result['outer_caps'] == result['nested_caps'] == 0
    assert len(result['rows']) == 4*len(options)
    credits = {str(a): [] for a in options}
    for i,row in enumerate(result['rows']):
        sample, ordinal = divmod(i,len(options)); action = options[ordinal]
        assert row['env'] == i and row['sample'] == sample and row['actionIndex'] == action and not row['truncated']
        assert row['searchStats']['truncated'] == row['diagnostic']['priorSearchStats']['truncated'] == 0
        signature = row['diagnostic']['sampledWorldSha256']
        assert worlds.setdefault(sample,signature) == signature
        scores = [tuple(p[k] for k in ('powered','money','cities')) for p in row['diagnostic']['terminal']]
        assert len(scores) == root['players'] and all(type(v) is int and v >= 0 for s in scores for v in s)
        best = max(scores); value = Fraction(1,scores.count(best)) if scores[seat] == best else Fraction(0)
        assert float(value) == row['value']
        credits[str(action)].append(value)
    baseline = credits[str(root['baseline'])]
    return {'rollouts':len(result['rows']), 'caps':0,
        'mean_credits':{a:str(sum(v,Fraction(0))/4) for a,v in credits.items()},
        'paired_margins':{a:str(sum((x-y for x,y in zip(v,baseline)),Fraction(0))/4) for a,v in credits.items()},
        'worlds':worlds, 'seconds':result['seconds']}


def load(root, runtime):
    protocol = read(root/'protocol.json')
    assert digest(runtime/'manifest.json') == protocol['runtime_manifest_sha256']
    assert all(digest(runtime/n) == h for n,h in read(runtime/'manifest.json').items())
    assert digest(root/'roots.json') == protocol['roots_sha256']
    assert digest(__file__) == protocol['worker_sha256']
    assert not os.environ.get('NODE_OPTIONS')
    sys.path.insert(0,str(runtime/'ai/strong'))
    import public_policy_runtime_v1 as transport
    assert Path(transport.__file__).resolve().is_relative_to(runtime)
    instance = transport.load_artifact(runtime,'policies/conservative_population.json')
    return protocol,read(root/'roots.json'),instance


def execute(root,runtime,prepare):
    protocol,roots,instance = load(root,runtime)
    assert len(roots)==10 and protocol['worlds']==4 and protocol['workers']==4
    output=root/('preflight.json' if prepare else 'results.json')
    assert not output.exists()
    if not prepare: assert read(root/'preflight.json')['complete']
    started=time.monotonic(); reports=[]
    try:
        for index,r in enumerate(roots):
            prepared=instance.prepare(r['request']);baseline=instance.policy.base.choose(r['request'])['index']
            assert prepared['moves']==r['moves'] and prepared['options']==r['shortlist'] and baseline==r['baseline']
            assert not prepared['lossFilter']['forbidden']
            assert [x['actor'] for x in prepared['prior']]==r['prior_actors']
            if prepare: continue
            checks={}; worlds={}
            for mode in protocol['modes']:
                path=root/f'root-{index:02d}-{mode}.json';assert not path.exists()
                save(path.with_suffix('.intent.json'),{'started_at':now(),'root':r['rootId'],'mode':mode,'automatic_retries':False})
                result=instance.policy.probe.run(r['request'],r['options'],mode=mode,samples=4,max_steps=2400)
                save(path,result)  # Preserve raw evidence before rejecting caps or inconsistent scores.
                checks[mode]=check_result(result,r,worlds)
                save(path.with_suffix('.audit.json'),checks[mode])
                print(json.dumps({'root':index,'players':r['players'],'variant':r['variant'],'mode':mode,
                    'rollouts':checks[mode]['rollouts'],'seconds':result['seconds'],'caps':checks[mode]['caps']}),flush=True)
            reports.append({'rootId':r['rootId'],'checks':checks})
        save(output,{'created_at':now(),'complete':True,'preflight_only':prepare,'roots':len(roots),
            'reports':reports,'seconds':time.monotonic()-started,'protocol_sha256':digest(root/'protocol.json'),
            'new_rollouts':0 if prepare else sum(c['rollouts'] for r in reports for c in r['checks'].values()),
            'new_gradients':0,'qualified':False,'reserved_final_seeds_used':False})
    finally: instance.close()


def supervise(root,runtime):
    assert not (root/'state.json').exists() and not (root/'worker.log').exists()
    start=time.monotonic();code=None;timed_out=False
    with (root/'worker.log').open('x') as log:
        child=subprocess.Popen([sys.executable,'-u','-B',__file__,'run','--root',str(root),'--runtime',str(runtime)],
            stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        save(root/'execution.json',{'started_at':now(),'pid':child.pid,'supervisor_pid':os.getpid(),'timeout_seconds':10800})
        try: code=child.wait(timeout=10800)
        except subprocess.TimeoutExpired:
            timed_out=True;os.killpg(child.pid,signal.SIGTERM)
            try: child.wait(timeout=10)
            except subprocess.TimeoutExpired: pass
            try: os.killpg(child.pid,signal.SIGKILL)
            except ProcessLookupError: pass
            code=child.wait()
    save(root/'state.json',{'finished_at':now(),'complete':code==0 and not timed_out,
        'returncode':code,'timed_out':timed_out,'seconds':time.monotonic()-start,'automatic_retries':False})


if __name__=='__main__':
    p=argparse.ArgumentParser(__doc__);p.add_argument('operation',choices=['prepare','run','supervise'])
    p.add_argument('--root',type=Path,required=True);p.add_argument('--runtime',type=Path,required=True);a=p.parse_args()
    root=a.root.resolve();runtime=a.runtime.resolve()
    if a.operation=='supervise':supervise(root,runtime)
    else:execute(root,runtime,a.operation=='prepare')
