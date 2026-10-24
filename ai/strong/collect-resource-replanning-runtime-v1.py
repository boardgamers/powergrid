"""Audit the complete local endpoint pilot and archive its evidence exactly once."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil

import numpy as np

from strategic_collection import ROOT, read, write, digest
from resource_development_v1 import PROTOCOL, verify_pins
from resource_policy_verification_v1 import verify_evaluation
from policy_iteration_evidence_archive import upload_evidence

STRONG = ROOT / 'ai/strong'
PREP = ROOT / 'ai/runs/resource-replanning-runtime-source-prepared-v1'
LAYOUT = PREP / 'layout'
PILOT = LAYOUT / 'ai/runs/resource-replanning-runtime-v1'
SOURCE = STRONG / 'resource-replanning-runtime-source-v1.json'
PLAN = STRONG / 'resource-replanning-runtime-plan-v1.json'
OUT = ROOT / 'ai/runs/resource-replanning-runtime-evidence-v1'
DESCRIPTOR = STRONG / 'resource-replanning-runtime-evidence-v1.json'
FAILURE = ROOT / 'ai/runs/resource-replanning-runtime-source-preparation-failed-v1'


def distribution(values):
    assert values
    return {'count': len(values), 'min': min(values), 'p50': float(np.percentile(values, 50)),
            'p95': float(np.percentile(values, 95)), 'max': max(values)}


def verify_replays(folder, cell, report):
    expected = set(cell['replay_episodes'])
    assert expected == set(range(4 * (cell['players'] - 1), 4 * cell['players']))
    assert {int(path.stem.split('-')[-1]) for path in folder.glob('replay-*.json')} == expected
    result = []
    for episode in sorted(expected):
        replay = read(folder / f'replay-{episode}.json')
        game = next(row for row in report['results'] if row['episode'] == episode)
        receipt = folder / f'evaluation/decisions-{episode}.jsonl'
        assert replay['episode'] == episode
        assert replay['exact_terminal_replay'] and replay['all_model_proposals_exact']
        assert replay['all_legal_moves_exact'] and replay['all_public_inputs_checked']
        assert replay['reference_receipt_sha256'] == digest(receipt) == game['decision_receipt_sha256']
        assert replay['learner_decisions'] == game['decisions']
        with receipt.open() as stream:
            resources = sum(json.loads(line).get('resourcePlan') is not None for line in stream)
        assert replay['resource_decisions'] == resources
        assert replay['qualification_eligible'] is False
        assert resources > 0 if cell['arm'] == 'resource-filter' else resources == 0
        result.append({**replay, 'receipt_sha256': digest(folder / f'replay-{episode}.json')})
    return result


def audit():
    status = read(PILOT / 'status.json')
    assert status['stage'] == 'complete', 'Wait for the existing pilot; partial endpoint results cannot supply admission'
    assert status['games'] == 64 and status['replays'] == 16
    assert status['new_strength_games'] == status['new_hf_jobs'] == 0
    assert status['gradients'] is status['qualification_eligible'] is status['reserved_final_seeds_used'] is False
    protocol, plan, source = read(PROTOCOL), read(PLAN), read(SOURCE)
    verify_pins(protocol)
    assert source['remote_archive_verified'] and source == status['source']
    assert digest(SOURCE) == status['source_descriptor_sha256']
    assert digest(PROTOCOL) == source['protocol_sha256'] == status['protocol_sha256']
    assert digest(PLAN) == source['runtime_plan_sha256'] == status['runtime_plan_sha256']
    assert digest(ROOT / 'ai/runs' / source['archive']) == source['sha256']
    assert digest(LAYOUT / 'resource-runtime-manifest.json') == source['manifest_sha256']
    manifest = read(LAYOUT / 'resource-runtime-manifest.json')
    assert len(manifest) == source['unchanged_base_files'] + len(source['new_files']) == 1481
    assert all(digest(LAYOUT / name) == sha for name, sha in manifest.items())
    assert all(digest(ROOT / name) == sha for name, sha in source['new_files'].items())
    assert digest(STRONG / 'resource_policy_verification_v1.py') == protocol['source_overlays']['ai/strong/resource_policy_verification_v1.py']
    preflight = read(PREP / 'replay-preflight.json')
    assert preflight['runtime_runner_sha256'] == manifest['ai/strong/resource-replanning-runtime-pilot-v1.py']
    assert preflight['result']['exact_terminal_replay'] and preflight['result']['learner_decisions'] == 159
    assert preflight['new_games'] == preflight['new_jobs'] == 0
    assert len(plan['cells']) == 4
    expected_cells = {f"{cell['players']}p-{cell['arm']}" for cell in plan['cells']}
    assert set(status['cells']) == expected_cells
    cells, reports, replay_decisions, replay_resources = {}, {}, 0, 0
    for cell in plan['cells']:
        key = f"{cell['players']}p-{cell['arm']}"
        folder = PILOT / key
        config = {'arm': cell['arm'], 'players': cell['players'], 'opponent': 'search_geo',
                  'seed': protocol['smoke_seed_template'].format(players=cell['players']),
                  'start': 0, 'deals': 1, 'samples': 8, 'workers': 8, 'search_workers': 1,
                  'model_sha256': protocol['model_pin']['files']['inference64.onnx'],
                  'opponent_model': None, 'opponent_sha256': None, 'runtime': str(LAYOUT),
                  'output': str(folder / 'evaluation')}
        summary = verify_evaluation(folder / 'evaluation', config)
        assert summary == read(folder / 'verified.json') == status['cells'][key]['summary']
        assert summary['games'] == cell['games'] == 4 * cell['players']
        assert status['cells'][key]['complete'] is True
        runtime = read(folder / 'runtime.json')
        assert runtime == status['cells'][key]['runtime']
        assert runtime['seconds'] >= summary['wall_seconds'] > 0
        assert runtime['cpu_seconds'] > 0 and runtime['sampled_peak_total_rss_bytes'] > 0
        assert runtime['memory_samples'] > 0 and runtime['memory_sampling_period_seconds'] == .1
        report = read(folder / 'evaluation/evaluation.json')
        reports[key] = report
        replays = verify_replays(folder, cell, report)
        replay_decisions += sum(row['learner_decisions'] for row in replays)
        replay_resources += sum(row['resource_decisions'] for row in replays)
        latency, candidates, simulations = [], [], []
        for path in (folder / 'evaluation').glob('decisions-*.jsonl'):
            with path.open() as stream:
                for line in stream:
                    row = json.loads(line)
                    if row.get('resourcePlan') is not None:
                        latency.append(row['elapsedMs'])
                        candidates.append(len(row['resourcePlan']['bundles']))
                        simulations.append(row['search']['evaluations'])
        if cell['arm'] == 'resource-filter':
            assert len(latency) == summary['counts']['resource_search_decisions']
            assert sum(simulations) == summary['counts']['rollouts']
        else:
            assert latency == candidates == simulations == []
        cells[key] = {
            'summary': summary, 'runtime': runtime, 'replays': replays,
            'resource_search_latency_ms': distribution(latency) if latency else None,
            'resource_candidate_bundles': distribution(candidates) if candidates else None,
            'resource_simulations_per_search': distribution(simulations) if simulations else None,
            'raw_evaluation_bytes': sum(path.stat().st_size for path in (folder / 'evaluation').rglob('*') if path.is_file()),
            'report_sha256': digest(folder / 'evaluation/evaluation.json'),
        }
    for n in (2, 6):
        left = reports[f'{n}p-filter']['results']
        right = reports[f'{n}p-resource-filter']['results']
        assert len(left) == len(right) == 4 * n
        for a, b in zip(left, right):
            assert a['episode'] == b['episode']
            assert all(a['terminal'][key] == b['terminal'][key]
                       for key in ('episode', 'gameSeed', 'playerCount', 'seat', 'variant', 'sealed', 'roles'))
    assert replay_decisions == status['replayed_learner_decisions']
    assert replay_resources == status['replayed_resource_decisions']
    return {
        'checked_at': datetime.now(timezone.utc).isoformat(), 'complete': True,
        'games': 64, 'independent_replays': 16, 'all_pairs_complete': True, 'caps': 0,
        'source': source, 'protocol_sha256': digest(PROTOCOL), 'runtime_plan_sha256': digest(PLAN),
        'pilot_status_sha256': digest(PILOT / 'status.json'), 'collector_sha256': digest(__file__),
        'processor': status['processor'], 'host': status['host'], 'cells': cells,
        'replayed_learner_decisions': replay_decisions, 'replayed_resource_decisions': replay_resources,
        'frozen_runtime_files_verified': len(manifest), 'new_hf_jobs': 0, 'new_strength_games': 0,
        'gradients': False, 'candidate_selected': False,
        'qualification_eligible': False, 'reserved_final_seeds_used': False,
        'limitations': [
            'One runtime-only deal per endpoint/arm, not a strength sample or final qualification.',
            'Timing is parallel HX370 execution, not AMD8840U serving latency or measured HF job performance.',
            'Process-tree RSS is sampled and can double-count shared pages; not a hard upper bound.',
            'Sixteen actual games were replayed, not every simulated continuation.',
        ],
    }


def main(archive):
    review = audit()
    if not archive:
        print(json.dumps(review, indent=2))
        return
    assert not OUT.exists() and not OUT.with_suffix('.tgz').exists() and not DESCRIPTOR.exists(), \
        'Inspect any existing archive attempt before another upload'
    files = [file for file in PILOT.rglob('*') if file.is_file()]
    files += [SOURCE, PLAN, PROTOCOL, Path(__file__), LAYOUT / 'resource-runtime-manifest.json']
    files += [ROOT / name for name in review['source']['new_files']]
    files += [PREP / name for name in ('prepared.json', 'layout-source.json', 'layout-check.log',
                                      'upload-intent.json', 'upload-receipt.json', 'replay-preflight.json')]
    files += [file for file in (PREP / 'replay-preflight').rglob('*') if file.is_file()]
    files += [FAILURE / 'failure.json', FAILURE / 'failed-plan.json']
    files += list((FAILURE / 'failed-sources').glob('*.py'))
    files += [STRONG / name for name in ('resource_policy_verification_v1.py', 'population_policy_verification.py',
                                        'policy_iteration_evidence_archive.py', 'strategic_collection.py')]
    OUT.mkdir()
    for source in sorted(set(files)):
        assert source.is_file() and not source.is_symlink()
        target = OUT / source.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        assert digest(source) == digest(target)
    write(OUT / 'review.json', review)
    write(OUT / 'manifest.json', {str(file.relative_to(OUT)): digest(file)
                                 for file in sorted(OUT.rglob('*')) if file.is_file()})
    descriptor = {**review, **upload_evidence(OUT)}
    write(DESCRIPTOR, descriptor)
    print(json.dumps({key: value for key, value in descriptor.items() if key not in ('cells', 'source')}, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--archive', action='store_true')
    main(parser.parse_args().archive)
