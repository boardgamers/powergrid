"""Audit and archive all 28 opponent diagnostic shards, never partial rankings."""
import argparse
from fractions import Fraction
import importlib.util
import json
from pathlib import Path
import shutil

import numpy as np

from strategic_collection import ROOT, read, write, digest
from policy_iteration_evidence_archive import upload_evidence

STRONG = ROOT / 'ai/strong'
spec = importlib.util.spec_from_file_location('reference_manager', STRONG / 'manage-reference-opponents-v2.py')
manager = importlib.util.module_from_spec(spec)
spec.loader.exec_module(manager)
COORDINATOR = ROOT / 'ai/runs/reference-opponent-coordinator-v2'
OUT = ROOT / 'ai/runs/reference-opponent-complete-evidence-v2'
DESCRIPTOR = STRONG / 'reference-opponent-complete-evidence-v2.json'


def terminal_credits(root, rows, begin=0, count=64):
    """Recompute credits from terminal players, keyed by world and fixed action."""
    seat = root['request']['player']
    players = len(root['request']['state']['players'])
    expected = {(world, action) for world in range(begin, begin + count) for action in root['options']}
    credits = {}
    for row in rows:
        key = (row['sample'], row['actionIndex'])
        assert key in expected and key not in credits, 'Missing, duplicate or misplaced world/action'
        assert row['truncated'] is False
        assert row['searchStats']['truncated'] == row['diagnostic']['priorSearchStats']['truncated'] == 0
        terminal = row['diagnostic']['terminal']
        assert len(terminal) == players
        scores = [tuple(player[k] for k in ('powered', 'money', 'cities')) for player in terminal]
        assert all(type(value) is int and value >= 0 for score in scores for value in score)
        assert all(score[0] <= score[2] for score in scores)
        best = max(scores)
        credit = Fraction(1, scores.count(best)) if scores[seat] == best else Fraction(0)
        assert abs(row['value'] - float(credit)) < 1e-12, 'Terminal credit disagrees with players'
        credits[key] = credit
    assert set(credits) == expected, 'Incomplete fixed world/action grid'
    return credits


def close(actual, expected):
    assert np.allclose(actual, expected, rtol=0, atol=1e-12), 'Summary disagrees with terminal evidence'


def audit():
    state = read(COORDINATOR / 'state.json')
    assert state['stage'] == 'comparison_complete', 'Wait for the existing coordinator; do not compare partial results'
    assert state['jobs_submitted'] == state['jobs_verified'] == 28 and not state['failed_jobs']
    assert all(digest(ROOT / name) == sha for name, sha in state['code_hashes'].items())
    assert manager.COMPARISON.exists()
    assert manager.compare() == state['comparison']
    comparison = read(manager.COMPARISON)
    protocol, descriptor, cases = manager.contract(refresh=True)
    assert comparison['complete'] and comparison['roots'] == len(comparison['comparisons']) == 7
    assert comparison['reference_continuations'] == 896
    assert comparison['gradients'] is comparison['candidate_selected'] is False
    assert comparison['qualification_eligible'] is comparison['reserved_final_seeds_used'] is False
    assert comparison['new_strength_games'] == 0
    preflight = read(ROOT / 'ai/runs/reference-opponent-collector-v2-preflight/receipt.json')
    assert preflight['collector_sha256'] == digest(__file__)
    assert preflight['control_rows'] == 896 and preflight['pilot_rows'] == 16
    assert preflight['partial_comparison_rejected'] and len(preflight['corruptions_rejected']) == 5
    all_rows = {i: [] for i in range(7)}
    runtime = []
    for case in cases:
        folder = manager.COLLECTED / case['case']
        result = read(folder / 'artifacts/result.json')
        all_rows[case['root']].extend(result['rows'])
        runtime.append({**case, **{k: result[k] for k in ('seconds', 'cpu_seconds', 'sampled_peak_total_rss_bytes')}})
    roots = []
    for index, root in enumerate(protocol['roots']):
        item = comparison['comparisons'][index]
        baseline, selected = root['options']
        assert item['root'] == index and item['label'] == root['label']
        assert item['baseline_index'] == baseline and item['selected_index'] == selected
        assert item['fixed_options'] == root['options']
        assert item['fixed_selected_action'] == root['original_decision']['move']
        reference = terminal_credits(root, all_rows[index])
        control = read(manager.probe.OUT / f'control-{index}.json')
        mixture = terminal_credits(root, control['rows'])
        margins = [[credits[(world, selected)] - credits[(world, baseline)] for world in range(64)]
                   for credits in (mixture, reference)]
        for name, values in zip(('mixture', 'reference'), margins):
            close(item[name + '_world_margins'], [float(value) for value in values])
            close(item['original_eight_world_means'][name], float(sum(values[:8]) / 8))
        differences = [right - left for left, right in zip(*margins)]
        series = dict(zip(('mixture', 'reference', 'reference_minus_mixture'), [*margins, differences]))
        # Reconstruct each block with rational credits, then use bootstrap block
        # multiplicities instead of the comparator's indexed floating point means.
        blocks = np.array([[float(sum(values[start:start + 4]) / 4)
                            for values in series.values()] for start in range(8, 64, 4)])
        draws = np.random.default_rng(12347).integers(14, size=(10000, 14))
        weights = np.array([np.bincount(draw, minlength=14) for draw in draws])
        bootstrap = weights @ blocks / 14
        for column, (name, values) in enumerate(series.items()):
            close(item['heldout_56_world_means'][name], float(sum(values[8:]) / 56))
            close(item['paired_block_bootstrap_95'][name], np.quantile(bootstrap[:, column], [.025, .975]))
        roots.append({k: item[k] for k in ('root', 'label', 'opponent', 'baseline_index', 'selected_index',
                                           'original_eight_world_means', 'heldout_56_world_means',
                                           'paired_block_bootstrap_95', 'checks')})
    return {
        'complete': True, 'jobs': 28, 'roots': 7, 'reference_continuations': 896,
        'mixture_control_continuations': 896, 'caps': 0,
        'terminal_credits_recomputed': True, 'world_action_grid_verified': True,
        'rational_margin_audit': True, 'bootstrap_multiplicity_audit': True,
        'protocol_sha256': descriptor['protocol_sha256'],
        'comparison_sha256': digest(manager.COMPARISON), 'collector_sha256': digest(__file__),
        'pilot_evidence_revision': descriptor['revision'], 'comparison': roots, 'runtime': runtime,
        'total_reference_cpu_seconds': sum(row['cpu_seconds'] for row in runtime),
        'max_shard_wall_seconds': max(row['seconds'] for row in runtime),
        'max_sampled_process_rss_bytes': max(row['sampled_peak_total_rss_bytes'] for row in runtime),
        'timing_limitations': 'CPU Basic with four worker processes on two vCPUs; diagnostic nested search, not an AMD 8840U deployment benchmark. RSS is sampled, not a hard bound.',
        'primary': protocol['primary'], 'uncertainty': protocol['uncertainty'],
        'limitations': protocol['limitations'], 'new_strength_games': 0, 'new_hf_jobs': 0,
        'gradients': False, 'candidate_selected': False,
        'qualification_eligible': False, 'reserved_final_seeds_used': False,
    }


def main(archive):
    review = audit()
    if not archive:
        print(json.dumps(review, indent=2))
        return
    assert not OUT.exists() and not OUT.with_suffix('.tgz').exists() and not DESCRIPTOR.exists(), \
        'Inspect any previous archive attempt before repeating an upload'
    files = [Path(__file__), manager.COMPARISON, Path(manager.__file__), Path(manager.probe.__file__),
             STRONG / 'coordinate-reference-opponents-v2.py', STRONG / 'launch-reference-opponents-v2.py',
             STRONG / 'reference-opponent-job-v2.py', manager.probe.WORKER, manager.probe.TEST,
             STRONG / 'reference-opponent-pilot-evidence-v2.json',
             STRONG / 'population-hybrid-development-source-v1.json',
             STRONG / 'auction-world-generalization-evidence-v1.json',
             STRONG / 'policy_iteration_evidence_archive.py', STRONG / 'strategic_collection.py',
             STRONG / 'population_policy_verification.py']
    protocol = read(manager.probe.OUT / 'protocol.json')
    files += [ROOT / name for name in protocol['repair_dependencies']]
    files += list(manager.probe.OUT.glob('*.json')) + list(manager.probe.OLD.glob('*.json'))
    files += list(manager.GUARDS.glob('*.json'))
    files += [file for file in manager.COLLECTED.rglob('*') if file.is_file()]
    files += [COORDINATOR / 'state.json', COORDINATOR / 'coordinator.log', COORDINATOR / 'latest-status.json']
    files += [ROOT / 'ai/runs/reference-opponent-collector-v2-preflight/receipt.json']
    OUT.mkdir()
    for source in sorted(set(files)):
        assert source.is_file() and not source.is_symlink()
        destination = OUT / source.relative_to(ROOT)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        assert digest(source) == digest(destination)
    write(OUT / 'review.json', review)
    write(OUT / 'manifest.json', {str(file.relative_to(OUT)): digest(file)
                                 for file in sorted(OUT.rglob('*')) if file.is_file()})
    descriptor = {**review, **upload_evidence(OUT)}
    write(DESCRIPTOR, descriptor)
    print(json.dumps({k: v for k, v in descriptor.items() if k not in ('comparison', 'runtime')}, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--archive', action='store_true', help='Upload once only after the complete audit passes')
    main(parser.parse_args().archive)
