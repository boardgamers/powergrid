"""Finite, disjoint-world bid-target assessment; frozen policies, no gradients."""
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
    with Path(p).open('x') as f:
        json.dump(value, f, indent=2, allow_nan=False); f.write('\n')
def now(): return datetime.now(timezone.utc).isoformat()


def check_result(result, root, mode, begin, worlds):
    """Recompute exact terminal credit; reject missing, unpaired or capped rows."""
    assert begin in (4, 32)
    options = root['options']; seat = root['request']['player']
    assert result['mode'] == mode and result['options'] == options
    assert result['samples'] == 60 and result['begin'] == begin and result['count'] == 28
    assert result['usable'] and result['caps'] == result['outer_caps'] == result['nested_caps'] == 0
    assert len(result['rows']) == 28 * len(options)
    credits = {str(a): [] for a in options}; identities = {}
    for i, row in enumerate(result['rows']):
        sample = begin + i // len(options); action = options[i % len(options)]
        assert row['env'] == i and row['sample'] == sample and row['actionIndex'] == action
        assert not row['truncated']
        assert row['searchStats']['truncated'] == row['diagnostic']['priorSearchStats']['truncated'] == 0
        signature = row['diagnostic']['sampledWorldSha256']
        assert isinstance(signature, str) and len(signature) == 64 and int(signature, 16) >= 0
        assert worlds.setdefault(sample, signature) == signature
        identity = {k: row[k] for k in ('roles', 'initialBelief')}
        assert identities.setdefault(sample, identity) == identity
        assert len(row['roles']) == root['players'] and row['roles'][seat] == 'neural'
        if mode == 'reference_opponent_v1':
            assert row['roles'] == ['neural' if p == seat else 'search_geo' for p in range(root['players'])]
        else:
            assert row['searchStats'] == row['diagnostic']['priorSearchStats'] == {'decisions': 0, 'evaluations': 0, 'truncated': 0}
        assert sum(row['policyDecisions'].values()) == row['steps']
        scores = [tuple(p[k] for k in ('powered', 'money', 'cities')) for p in row['diagnostic']['terminal']]
        assert len(scores) == root['players'] and all(type(v) is int and v >= 0 for s in scores for v in s)
        best = max(scores)
        value = Fraction(1, scores.count(best)) if scores[seat] == best else Fraction(0)
        assert float(value) == row['value']
        credits[str(action)].append(value)
    base = credits[str(root['baseline'])]
    return {'rollouts': len(result['rows']), 'caps': 0, 'begin': begin, 'count': 28,
            'mean_credits': {a: str(sum(v, Fraction()) / 28) for a, v in credits.items()},
            'paired_margins': {a: str(sum((x-y for x, y in zip(v, base)), Fraction()) / 28) for a, v in credits.items()},
            'worlds': {str(s): worlds[s] for s in range(begin, begin + 28)},
            'seconds': result['seconds']}


def choose(means, baseline):
    """Fixed 1/40 margin, parent-favouring ties, then smallest legal index."""
    best = min(means, key=lambda a: (-means[a], int(a) != baseline, int(a)))
    return str(baseline) if means[best] - means[str(baseline)] <= Fraction(1, 40) else best


def compare_halves(root, audits):
    """Select on one half only, report both populations on the opposite half."""
    modes = ('neural_population', 'reference_opponent_v1'); rows = []
    base = str(root['baseline'])
    for selection, evaluation in ((4, 32), (32, 4)):
        means = {m: {a: Fraction(v) for a, v in audits[f'{m}-{selection}']['mean_credits'].items()} for m in modes}
        means['equal_mixture'] = {a: (means[modes[0]][a] + means[modes[1]][a]) / 2 for a in means[modes[0]]}
        for selector in (*modes, 'equal_mixture'):
            action = choose(means[selector], root['baseline'])
            heldout = {}
            for mode in modes:
                scores = audits[f'{mode}-{evaluation}']['mean_credits']
                heldout[mode] = str(Fraction(scores[action]) - Fraction(scores[base]))
            rows.append({'selection_begin': selection, 'evaluation_begin': evaluation, 'selector': selector,
                'action': int(action), 'parent': root['baseline'], 'overridden': action != base,
                'selection_margin': str(means[selector][action] - means[selector][base]),
                'heldout_margins': heldout})
    return rows


def load(root, runtime):
    protocol = read(root/'protocol.json')
    assert digest(runtime/'manifest.json') == protocol['runtime_manifest_sha256']
    assert all(digest(runtime/n) == h for n, h in read(runtime/'manifest.json').items())
    assert digest(root/'roots.json') == protocol['roots_sha256']
    assert digest(__file__) == protocol['worker_sha256']
    assert protocol['samples'] == 60 and protocol['begins'] == [4, 32] and protocol['count'] == 28
    assert protocol['workers_per_lane'] == 4 and protocol['lanes'] == 2 and protocol['threads'] == 1
    assert sorted(i for lane in protocol['lane_roots'] for i in lane) == list(range(10))
    assert not os.environ.get('NODE_OPTIONS')
    sys.path.insert(0, str(runtime/'ai/strong'))
    import public_policy_runtime_v1 as transport
    assert Path(transport.__file__).resolve().is_relative_to(runtime)
    instance = transport.load_artifact(runtime, 'policies/conservative_population.json')
    return protocol, read(root/'roots.json'), instance


def execute(root, runtime, lane=None):
    protocol, roots, instance = load(root, runtime)
    assert len(roots) == 10
    prepare = lane is None
    output = root/('preflight.json' if prepare else f'lane-{lane}-complete.json')
    assert not output.exists()
    if not prepare:
        assert read(root/'preflight.json')['complete']
        assert read(root/'preflight.json')['protocol_sha256'] == digest(root/'protocol.json')
    start = time.monotonic(); rollouts = 0
    try:
        for index in (range(10) if prepare else protocol['lane_roots'][lane]):
            r = roots[index]
            assert r['split'] == 'train' and r['deal'] not in (0, 4, 8, 12)
            prepared = instance.prepare(r['request']); baseline = instance.policy.base.choose(r['request'])['index']
            assert prepared['moves'] == r['moves'] and prepared['options'] == r['shortlist'] and baseline == r['baseline']
            assert r['options'] == list(dict.fromkeys(r['shortlist'] + [baseline]))
            assert not prepared['lossFilter']['forbidden']
            assert [p['actor'] for p in prepared['prior']] == r['prior_actors']
            if prepare: continue
            worlds = {}
            for begin in protocol['begins']:
                for mode in protocol['modes']:
                    path = root/f'root-{index:02d}-{mode}-{begin}.json'
                    assert not path.exists()
                    save(path.with_suffix('.intent.json'), {'started_at': now(), 'root': r['rootId'], 'mode': mode,
                        'begin': begin, 'count': 28, 'automatic_retries': False})
                    result = instance.policy.probe.run(r['request'], r['options'], mode=mode, samples=60,
                        begin=begin, count=28, max_steps=2400)
                    save(path, result)
                    audit = check_result(result, r, mode, begin, worlds)
                    save(path.with_suffix('.audit.json'), audit); rollouts += audit['rollouts']
                    print(json.dumps({'root': index, 'players': r['players'], 'variant': r['variant'],
                        'mode': mode, 'begin': begin, 'rollouts': audit['rollouts'], 'seconds': result['seconds'], 'caps': 0}), flush=True)
        save(output, {'created_at': now(), 'complete': True, 'preflight_only': prepare, 'lane': lane,
            'roots': 10 if prepare else len(protocol['lane_roots'][lane]), 'seconds': time.monotonic()-start,
            'protocol_sha256': digest(root/'protocol.json'), 'new_rollouts': rollouts,
            'new_gradients': 0, 'qualified': False, 'reserved_final_seeds_used': False})
    finally: instance.close()


def supervise(root, runtime):
    assert not (root/'state.json').exists() and not (root/'execution.json').exists()
    protocol = read(root/'protocol.json'); start = time.monotonic(); children = []; logs = []
    failure = None; timed_out = False
    try:
        for lane in range(protocol['lanes']):
            log = (root/f'lane-{lane}.log').open('x'); logs.append(log)
            children.append(subprocess.Popen([sys.executable, '-u', '-B', __file__, 'run', '--root', str(root),
                '--runtime', str(runtime), '--lane', str(lane)], stdin=subprocess.DEVNULL, stdout=log,
                stderr=subprocess.STDOUT, start_new_session=True))
        save(root/'execution.json', {'started_at': now(), 'pids': [c.pid for c in children],
            'supervisor_pid': os.getpid(), 'timeout_seconds': protocol['hard_timeout_seconds']})
        while True:
            codes = [c.poll() for c in children]
            if any(code not in (None, 0) for code in codes): failure = 'lane_failed'; break
            if all(code == 0 for code in codes): break
            if time.monotonic()-start >= protocol['hard_timeout_seconds']:
                failure = 'timeout'; timed_out = True; break
            time.sleep(2)
    except BaseException as error:
        failure = type(error).__name__
        raise
    finally:
        if failure:
            for child in children:
                try: os.killpg(child.pid, signal.SIGTERM)
                except ProcessLookupError: pass
            for child in children:
                try: child.wait(timeout=10)
                except subprocess.TimeoutExpired: pass
                try: os.killpg(child.pid, signal.SIGKILL)
                except ProcessLookupError: pass
                child.wait()
        for log in logs: log.close()
        save(root/'state.json', {'finished_at': now(), 'complete': failure is None,
            'returncodes': [c.poll() for c in children], 'failure': failure, 'timed_out': timed_out,
            'seconds': time.monotonic()-start, 'automatic_retries': False})


if __name__ == '__main__':
    p = argparse.ArgumentParser(__doc__); p.add_argument('operation', choices=['prepare', 'run', 'supervise'])
    p.add_argument('--root', type=Path, required=True); p.add_argument('--runtime', type=Path, required=True)
    p.add_argument('--lane', type=int, choices=(0, 1)); a = p.parse_args()
    root = a.root.resolve(); runtime = a.runtime.resolve()
    if a.operation == 'supervise': supervise(root, runtime)
    elif a.operation == 'prepare': execute(root, runtime)
    else:
        assert a.lane is not None
        execute(root, runtime, a.lane)
