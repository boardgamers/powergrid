"""Record complete serving responses/timings on the actual 8840U, without training."""
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import tarfile
import time

import numpy as np
import onnxruntime as ort

read = lambda p: json.loads(p.read_text())
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def validate(fixture, result, pin):
    q = fixture['request']; n = len(q['state']['players'])
    assert 'error' not in result, result
    assert result['requestId'] == q['requestId'] and result['revision'] == q['revision']
    assert result['move'] in fixture['legal']
    assert result['modelSha256'] == pin['files']['inference64.onnx']
    assert result['featureRevision'] == pin['feature_revision'] and result['schema'] == 4
    assert result['playerOrder'] == [(q['player'] + j) % n for j in range(n)]
    values = result['winProbabilities']
    assert len(values) == n and all(np.isfinite(v) and 0 <= v <= 1 for v in values)
    assert abs(sum(values) - 1) < 1e-5
    assert result['valueStatus'] == 'uncalibrated-training-opponents'


def describe(xs):
    return {'positions': len(xs), 'p50_ms': float(np.percentile(xs, 50)),
            'p95_ms': float(np.percentile(xs, 95)), 'max_ms': max(xs)}


def summarize(rows):
    groups = {}
    for row in rows:
        for axis in ['players', 'phase', 'rule']:
            groups.setdefault(axis, {}).setdefault(str(row[axis]), []).append(row['roundtrip_ms'])
    searching = [r for r in rows if (r['response'].get('search') or {}).get('evaluations', 0)]
    return {'positions': len(rows), 'cold_start_ms': rows[0]['roundtrip_ms'],
            'warm': describe([r['roundtrip_ms'] for r in rows[1:]]),
            'groups': {axis: {key: describe(xs) for key, xs in values.items()} for axis, values in groups.items()},
            'search_decisions': len(searching),
            'search_timing': describe([r['roundtrip_ms'] for r in searching]) if searching else None,
            'search_evaluations': sum((r['response'].get('search') or {}).get('evaluations', 0) for r in rows),
            'search_truncations': sum((r['response'].get('search') or {}).get('truncated', 0) for r in rows),
            'all_moves_legal': True}


def run(root):
    manifest = read(root/'manifest.json')
    assert sha(Path(__file__)) == manifest['harness_sha256']
    cpu = next(x.split(':', 1)[1].strip() for x in Path('/proc/cpuinfo').read_text().splitlines() if x.startswith('model name'))
    assert '8840U' in cpu, cpu
    identity = {'hostname': platform.node(), 'processor': cpu, 'python': sys.version,
                'numpy': np.__version__, 'onnxruntime': ort.__version__,
                'node': subprocess.check_output(['node', '--version'], text=True).strip(), 'load_before': os.getloadavg()}
    (root/'machine.json').write_text(json.dumps(identity, indent=2)+'\n')
    assert sha(root/'source.tgz') == manifest['source']['sha256']
    work = root/'runtime'; work.mkdir(exist_ok=False)
    with tarfile.open(root/'source.tgz') as f: f.extractall(work, filter='data')
    fixtures_path = work/'ai/strong/fixtures/multiplayer-serving-v1.jsonl'
    assert sha(fixtures_path) == manifest['fixtures_sha256']
    fixtures = [json.loads(line) for line in fixtures_path.open()]
    assert len(fixtures) == 2553
    results = {}
    for key, pin in manifest['models'].items():
        model = root/(key+'.onnx'); assert sha(model) == pin['files']['inference64.onnx']
        raw_moves = {}
        results[key] = {}
        for condition, samples, indices in [('raw', 0, list(range(len(fixtures)))),
                                             ('search48', 48, manifest['search_indices'])]:
            command = [sys.executable, str(work/'ai/strong/infer.py'), str(model), '--search-samples', str(samples), '--search-scope', 'all']
            if samples: command.append('--geographic-search')
            rows = []; prefix = f'{key}-{condition}'
            with (root/(prefix+'.stderr')).open('w') as error, (root/(prefix+'.jsonl')).open('x') as output:
                worker = subprocess.Popen(command, cwd=work, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                          stderr=error, text=True, bufsize=1)
                try:
                    for index in indices:
                        fixture = fixtures[index]; q = fixture['request']; g = q['state']
                        start = time.perf_counter()
                        worker.stdin.write(json.dumps(q)+'\n'); worker.stdin.flush()
                        result = json.loads(worker.stdout.readline()); elapsed = (time.perf_counter()-start)*1000
                        validate(fixture, result, pin)
                        if condition == 'raw':
                            assert result['search'] is None
                            raw_moves[index] = result['move']
                        elif all(m['name'] == 'DiscardPowerPlant' for m in fixture['legal']):
                            assert result['move'] == raw_moves[index]
                            assert result['search']['evaluations'] == 0
                        row = {'fixture_index': index, 'players': len(g['players']), 'phase': g['phase'],
                               'rule': g['options']['variant']+('/sealed' if g['options'].get('fastBid') else '/open'),
                               'roundtrip_ms': elapsed, 'response': result}
                        rows.append(row); output.write(json.dumps(row)+'\n'); output.flush()
                finally:
                    worker.stdin.close(); worker.wait(timeout=10); worker.stdout.close()
                assert worker.returncode == 0
            summary = summarize(rows); results[key][condition] = summary
            (root/(prefix+'.json')).write_text(json.dumps(summary, indent=2)+'\n')
            print(key, condition, json.dumps(summary), flush=True)
    result = {'machine': identity, 'models': results, 'qualification_eligible': False,
              'scope': manifest['scope'], 'load_after': os.getloadavg()}
    (root/'results.json').write_text(json.dumps(result, indent=2)+'\n')
    print('COMPLETE', flush=True)


if __name__ == '__main__':
    run(Path(__file__).resolve().parent)
