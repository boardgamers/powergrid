"""Verify every predeclared capacity-reference duel and model cell, including losses."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
from arena_statistics import validate_pairs, win_summary, search_summary

root = Path(__file__).resolve().parents[2]
p = argparse.ArgumentParser(__doc__)
p.add_argument('directory', type=Path)
p.add_argument('output', type=Path)
args = p.parse_args()
protocol_path = root / 'ai/strong/capacity-reference-protocol-v1.json'
protocol = json.loads(protocol_path.read_text())
for name, digest in protocol['runtime_sha256'].items():
    assert hashlib.sha256((root / name).read_bytes()).hexdigest() == digest, name
spec = importlib.util.spec_from_file_location('comparisons', Path(__file__).with_name('compare-population-screens.py'))
comparisons = importlib.util.module_from_spec(spec)
spec.loader.exec_module(comparisons)
reports, hashes = {}, {}

def load(name):
    data = (args.directory / (name + '.json')).read_bytes()
    hashes[name] = hashlib.sha256(data).hexdigest()
    report = json.loads(data)
    assert report['seed'] == protocol['seed'] and report['games'] == 320 and report['truncated'] == 0
    rows = report['results']
    assert len(rows) == 320
    validate_pairs(rows, 2)
    assert {r['gameSeed'] for r in rows} == {protocol['seed'] + '-' + str(d) for d in protocol['deal_offsets']}
    assert not any(r['truncated'] for r in rows)
    stats = search_summary(rows)
    assert stats == {'search_rollouts_reported': True, 'search_stats': {}}
    return report

duel = load('duel')
assert duel['candidate'] == 'economic_capacity_v1' and duel['opponent'] == 'economic'
assert duel['protocol_sha256'] == hashlib.sha256(protocol_path.read_bytes()).hexdigest()
for cell in protocol['model_cells']:
    key = cell['candidate'] + '-' + cell['opponent']
    report = load(key)
    assert report['opponent'] == cell['opponent']
    assert report['model_sha256'] == protocol['models'][cell['candidate']]['hashes']['latest.onnx']
    assert report['model_feature_revision'] == report['encoder_feature_revision'] == '4.0-multiplayer'
    assert report['candidate_search_samples'] == 0 and report['paired_seats']
    assert report['deal_offset'] == 0 and report['player_count'] == 2 and report['opponent_sha256'] is None
    assert report['search_max_steps'] == 2400
    assert abs(report['win_rate'] - win_summary(report['results'])['win_rate']) < 1e-12
    assert all(set(r['roles']) == {'learner', cell['opponent']} for r in report['results'])
    reports[key] = report

def summarize(rows):
    return {**win_summary(rows), 'by_rules': {
        f'{v}/{"sealed" if s else "open"}': win_summary([r for r in rows if r['variant'] == v and r['sealed'] == s])
        for v in ['original', 'recharged'] for s in [False, True]}}

def paired(left, right):
    return {'overall': comparisons.paired_difference(left, right), 'by_rules': {
        f'{v}/{"sealed" if s else "open"}': comparisons.paired_difference(
            [r for r in left if r['variant'] == v and r['sealed'] == s],
            [r for r in right if r['variant'] == v and r['sealed'] == s])
        for v in ['original', 'recharged'] for s in [False, True]}}

contrasts = {}
for name in protocol['models']:
    contrasts[name + ':corrected-minus-old-opponent'] = paired(
        reports[name + '-economic_capacity_v1']['results'], reports[name + '-economic']['results'])
for opponent in ['economic', 'economic_capacity_v1']:
    contrasts[opponent + ':heterogeneous-minus-parent'] = paired(
        reports['heterogeneous-u9-' + opponent]['results'], reports['parent-' + opponent]['results'])
result = {'verified': True, 'qualification_eligible': False, 'protocol_sha256': hashlib.sha256(protocol_path.read_bytes()).hexdigest(),
          'total_games': 1600, 'truncations': 0, 'duel': summarize(duel['results']),
          'different_deterministic_choices_in_duel': duel['differingChoices'],
          'model_cells': {key: summarize(r['results']) for key, r in reports.items()},
          'paired_contrasts': contrasts, 'artifact_sha256': hashes,
          'interpretation': protocol['interpretation']}
args.output.write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps({'duel': result['duel']['win_rate'], 'model_win_rates': {key: x['win_rate'] for key, x in result['model_cells'].items()},
                  'paired_contrasts': {key: x['overall'] for key, x in contrasts.items()}}))
