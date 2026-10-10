"""Revalidate per-request device evidence against the pinned public fixtures."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
read = lambda p: json.loads(p.read_text())
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
spec = importlib.util.spec_from_file_location('device_probe', Path(__file__).with_name('probe-search-transfer-8840u.py'))
probe = importlib.util.module_from_spec(spec); spec.loader.exec_module(probe)
spec = importlib.util.spec_from_file_location('summary_check', Path(__file__).with_name('collect-discard-correction-screen.py'))
checks = importlib.util.module_from_spec(spec); spec.loader.exec_module(checks)


def verify(directory):
    expected_path = ROOT/'ai/runs/search-transfer-8840u-probe-v1/manifest.json'
    assert sha(directory/'manifest.json') == sha(expected_path)
    manifest = read(expected_path)
    assert manifest['harness_sha256'] == sha(Path(probe.__file__))
    assert manifest['source'] == read(ROOT/'ai/strong/search-transfer-source-v1.json')
    assert manifest['models'] == read(ROOT/'ai/strong/discard-correction-screen-models-v1.json')
    path = ROOT/'ai/runs/multiplayer-serving-fixtures.jsonl'
    assert sha(path) == manifest['fixtures_sha256']
    fixtures = [json.loads(line) for line in path.open()]
    machine = read(directory/'machine.json')
    assert '8840U' in machine['processor']
    saved = read(directory/'results.json'); assert saved['machine'] == machine
    assert not saved['qualification_eligible']
    assert saved['scope'] == manifest['scope']
    models = {}; request_count = 0; discarded = 0
    for key, pin in manifest['models'].items():
        models[key] = {}; raw_moves = {}
        for condition, indices in [('raw', list(range(2553))), ('search48', manifest['search_indices'])]:
            prefix = f'{key}-{condition}'
            rows = [json.loads(line) for line in (directory/(prefix+'.jsonl')).open()]
            assert [r['fixture_index'] for r in rows] == indices
            for row in rows:
                index = row['fixture_index']; fixture = fixtures[index]; g = fixture['request']['state']
                result = row['response']; probe.validate(fixture, result, pin)
                assert row['players'] == len(g['players']) and row['phase'] == g['phase']
                assert row['rule'] == g['options']['variant']+('/sealed' if g['options'].get('fastBid') else '/open')
                assert np.isfinite(row['roundtrip_ms']) and row['roundtrip_ms'] > 0
                assert np.isfinite(result['elapsedMs']) and 0 <= result['elapsedMs'] <= row['roundtrip_ms']
                if condition == 'raw':
                    assert result['search'] is None
                    raw_moves[index] = result['move']
                else:
                    search = result['search']; assert search is not None
                    assert isinstance(search['evaluations'], int) and search['evaluations'] >= 0
                    assert search.get('truncated', 0) == 0
                    if index in manifest['discard_indices']:
                        assert all(m['name'] == 'DiscardPowerPlant' for m in fixture['legal'])
                        assert result['move'] == raw_moves[index] and search['evaluations'] == 0
                        discarded += 1
                request_count += 1
            summary = probe.summarize(rows)
            checks.same_summary(summary, read(directory/(prefix+'.json')))
            checks.same_summary(summary, saved['models'][key][condition])
            models[key][condition] = summary
    assert request_count == manifest['planned_requests'] == 8013
    assert discarded == 174
    return {'machine': machine, 'models': models, 'requests': request_count,
            'discard_actions_preserved': discarded, 'source': manifest['source'],
            'manifest_sha256': sha(expected_path), 'verified': True,
            'search_truncations': 0, 'all_moves_legal': True, 'qualification_eligible': False,
            'scope': manifest['scope'],
            'artifacts': {p.name: sha(p) for p in sorted(directory.iterdir()) if p.is_file() and p.name != 'verified.json'}}


if __name__ == '__main__':
    p = argparse.ArgumentParser(__doc__); p.add_argument('directory', type=Path); a = p.parse_args()
    result = verify(a.directory.resolve())
    (a.directory/'verified.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({'requests': result['requests'], 'discard_actions_preserved': result['discard_actions_preserved'],
                     'timings': {k: {c: {'warm': r['warm'], 'search': r['search_timing']} for c, r in modes.items()}
                                 for k, modes in result['models'].items()}}))
