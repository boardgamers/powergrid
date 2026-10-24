"""Verify untrained architecture timings and every target move against frozen runtime."""
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
read = lambda p: json.loads(p.read_text())
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    prepared = ROOT/'ai/runs/policy-iteration-8840u-prepared-v2'
    output = ROOT/'ai/runs/policy-iteration-8840u-results-v2'
    assert sha(prepared/'manifest.json') == sha(output/'manifest.json')
    manifest = read(prepared/'manifest.json')
    assert manifest['synthetic_untrained'] and manifest['gradients'] is False
    assert set(manifest['models']) == {'frozen-0','frozen-1','public-0','public-1'}
    preflight = read(ROOT/'ai/strong/policy-iteration-development-preflight-v2.json')
    assert manifest['source'] == preflight['source']
    assert sha(prepared/'fixtures.jsonl') == sha(output/'fixtures.jsonl') == manifest['fixtures_sha256']
    spec = importlib.util.spec_from_file_location('probe_helpers', ROOT/'ai/strong/probe-search-transfer-8840u.py')
    helpers = importlib.util.module_from_spec(spec); spec.loader.exec_module(helpers)
    assert sha(Path(helpers.__file__)) == manifest['helper_sha256']
    assert sha(ROOT/'ai/strong/probe-strategic-packages-8840u.py') == manifest['harness_sha256']
    fixtures = [json.loads(line) for line in (prepared/'fixtures.jsonl').open()]
    machine = read(output/'machine.json'); saved = read(output/'results.json')
    assert '8840U' in machine['processor'] and saved['machine'] == machine
    assert not saved['qualification_eligible'] and saved['scope'] == manifest['scope']
    models = {}
    frozen = prepared/'frozen-source'
    for key, item in manifest['models'].items():
        pin = item['pin']
        original = preflight['cases'][key+'-2p']['model_pin']
        assert pin['files'] == original['files'] and pin['model_args'] == original['model_args']
        assert pin['synthetic_untrained'] and pin['training_verified'] is False
        rows = [json.loads(line) for line in (output/(key+'.jsonl')).open()]
        assert len(rows) == len(fixtures) == 2553
        assert [row['fixture_index'] for row in rows] == list(range(2553))
        model = prepared/('local-package-'+key)/'policy.onnx'
        assert sha(model) == pin['files']['inference64.onnx']
        worker = subprocess.Popen([sys.executable, str(frozen/'ai/strong/infer.py'), str(model)],
            cwd='/', stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, bufsize=1)
        maximum_value_difference = 0
        try:
            for row, fixture in zip(rows, fixtures):
                game = fixture['request']['state']; result = row['response']
                helpers.validate(fixture, result, pin)
                assert result['search'] is None
                assert row['players'] == len(game['players']) and row['phase'] == game['phase']
                assert row['rule'] == game['options']['variant']+('/sealed' if game['options'].get('fastBid') else '/open')
                assert np.isfinite(row['roundtrip_ms']) and row['roundtrip_ms'] > 0
                assert np.isfinite(result['elapsedMs']) and 0 <= result['elapsedMs'] <= row['roundtrip_ms']
                worker.stdin.write(json.dumps(fixture['request'])+'\n'); worker.stdin.flush()
                reference = json.loads(worker.stdout.readline())
                helpers.validate(fixture, reference, pin)
                assert result['move'] == reference['move'], (key, row['fixture_index'])
                difference = max(abs(x-y) for x,y in zip(result['winProbabilities'],reference['winProbabilities']))
                assert difference < 1e-6
                maximum_value_difference = max(maximum_value_difference, difference)
        finally:
            worker.stdin.close(); worker.wait(timeout=10); worker.stdout.close()
        assert worker.returncode == 0
        summary = helpers.summarize(rows)
        assert summary == saved['models'][key]
        models[key] = {'summary':summary, 'model_pin':pin, 'all_frozen_runtime_moves_identical':True,
            'maximum_value_difference':maximum_value_difference, 'package_sha256':item['package_sha256']}
        print({'model':key, 'positions':len(rows), 'warm':summary['warm'], 'identical_moves':True}, flush=True)
    result = {'verified':True, 'machine':machine, 'models':models, 'requests':10212,
        'source':manifest['source'], 'manifest_sha256':sha(prepared/'manifest.json'),
        'qualification_eligible':False, 'candidate_selected':False, 'synthetic_untrained':True, 'gradients':False, 'scope':manifest['scope'],
        'interpretation':'Sequential engineering timing of untrained architectures on actual AMD8840U. No trained-model latency, statistical ranking, browser performance or strength claim. All moves match frozen runtime; the actual trained candidate must be benchmarked again.',
        'artifacts':{p.name:sha(p) for p in sorted(output.iterdir()) if p.is_file() and p.name != 'verified.json'}}
    (output/'verified.json').write_text(json.dumps(result,indent=2)+'\n')
    (ROOT/'ai/strong/policy-iteration-8840u-results-v2.json').write_text(json.dumps(result,indent=2)+'\n')


if __name__ == '__main__':
    main()
