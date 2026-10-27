"""Prepare the frozen 10,080-game comparison after complete runtime evidence.

This module cannot launch jobs. Schedule inspection is available before runtime
completion; actual source preparation requires all four original audited pilots.
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
import importlib.util
import json
import math
from pathlib import Path
import shutil

from public_policy_final_audit_v1 import artifact_identity, digest, read
from public_policy_final_contract_v1 import admit

ROOT = Path(__file__).resolve().parents[2]
PROTOCOL = ROOT/'ai/strong/conservative-auction-development-protocol-v2.json'
PROTOCOL_SHA = '51b845f4a57c3131475e24267fbbb08eb624c391aa6a8e6a4f5d5c6b8ac718ee'
OUT = ROOT/'ai/runs/conservative-auction-development-prepared-v2'
SHORT = {'filter': 'filter', 'conservative_population': 'pop', 'conservative_dual': 'dual'}


def write(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False)+'\n')


def protocol():
    assert digest(PROTOCOL) == PROTOCOL_SHA
    return read(PROTOCOL)


def schedule(p, deals):
    assert type(deals) is int and deals in (1, 2, 4, 8)
    result = []
    for arm in p['arms']:
        for screen in p['screens']:
            n, opponent = screen['players'], screen['opponent']
            assert screen['deals'] == 8 and screen['games'] == 32*n
            for start in range(0, 8, deals):
                name = f'pg-conservative-dev-v2-{SHORT[arm]}-{opponent}-{n}p-{start:02d}'
                assert len(name) <= 63
                result.append({'arm': arm, 'shard': {'name': name, 'group': f'{opponent}/{n}p',
                    'players': n, 'start': start, 'deals': deals,
                    'seed': p['seed_template'].format(players=n), 'opponent': opponent,
                    'opponent_sha256': screen.get('sha256'), 'games': 4*n*deals},
                    'opponent_model': 'artifact/final-opponent-a260.onnx' if opponent == 'a260' else None})
    assert len({r['shard']['name'] for r in result}) == len(result)
    assert sum(r['shard']['games'] for r in result) == p['planned_games_total'] == 10080
    for arm in p['arms']:
        assert sum(r['shard']['games'] for r in result if r['arm'] == arm) == p['planned_games_per_arm'] == 3360
    return result


def resources(p, result, source, source_sha):
    """Choose batch length using cost only; no wins/outcomes enter this choice."""
    assert result['complete'] is True and result['verified_jobs'] == len(result['jobs']) == 4
    assert result['source_sha256'] == source_sha and source['protocol_sha256'] == PROTOCOL_SHA
    assert source['flavor'] == 'cpu-upgrade' and source['workers'] == 4
    expected = {(r['arm'], r['players']) for r in p['runtime_pilots']}; seen = set()
    measurements = []
    for job in result['jobs']:
        row, review = job['row'], job['review']; audit = review['audit']; m = review['measurement']
        key = row['arm'], row['players']; assert key in expected and key not in seen; seen.add(key)
        assert job['verified'] is True and job['stage'] == 'COMPLETED' and row in source['rows']
        assert job['evidence']['remote_archive_verified'] and audit['all_receipts_verified']
        assert audit['expected'] == row['shard'] and audit['identity'] == row['identity']
        assert not audit['reserved_final_seeds_used'] and audit['counts']['rollout_caps'] == 0
        assert audit['counts']['rollouts'] > 0 and audit['counts']['search_decisions'] > 0
        assert review['games'] == len(audit['terminals']) == row['shard']['games'] == 4*row['players']
        assert m['memory_sampling_period_seconds'] == .2 and m['includes_startup_and_validation']
        assert all(math.isfinite(m[k]) and m[k] > 0 for k in ('seconds', 'cpu_seconds', 'sampled_peak_total_rss_bytes', 'memory_samples'))
        measurements.append({'name': row['name'], 'job_id': job['job_id'], 'arm': row['arm'],
            'players': row['players'], 'games': review['games'], **m})
    assert seen == expected
    # Use the slower endpoint per game, then double it for unseen deals/counts/
    # opponents. The factor is an allowance, not a statistical runtime bound.
    per_game = {arm: max(m['seconds']/m['games'] for m in measurements if m['arm'] == arm)
                for arm in ('conservative_population', 'conservative_dual')}
    per_game['filter'] = max(per_game.values())
    peak = max(m['sampled_peak_total_rss_bytes'] for m in measurements)
    assert 2*peak < .8*32*1024**3, 'Measured memory requires a new hardware admission; preserve originals'
    worst = max(per_game.values())
    projected = lambda deals, n, arm: 900 + 2*per_game[arm]*4*n*deals
    eligible = [d for d in (1, 2, 4, 8) if 900 + 2*worst*24*d <= 3*3600]
    deals = max(eligible) if eligible else 1
    per_count = {arm: {str(n): {'projected_seconds_with_margin': projected(deals, n, arm),
                    'timeout_hours': math.ceil(projected(deals, n, arm)/(.75*3600))}
                    for n in range(2, 7)} for arm in p['arms']}
    assert max(c['timeout_hours'] for rows in per_count.values() for c in rows.values()) <= 24
    return {'flavor': 'cpu-upgrade', 'workers': 4, 'search_workers': 4, 'inference_threads': 1,
        'deals_per_job': deals, 'measurements': measurements, 'per_game_seconds': per_game,
        'setup_allowance_seconds': 900, 'runtime_multiplier': 2, 'timeout_utilization': .75,
        'target_seconds_per_job': 3*3600, 'sampled_peak_rss_bytes': peak,
        'memory_margin': 2, 'per_arm_count': per_count,
        'rationale': 'Whole paired deals; largest power-of-two batch targeting three hours under a doubled measured per-game envelope. Filter conservatively uses the slower search envelope. Pilot outcomes are excluded.'}


def pilot_manager():
    path = Path(__file__).with_name('manage-conservative-auction-runtime-v2.py')
    spec = importlib.util.spec_from_file_location('original_pilot_manager', path)
    manager = importlib.util.module_from_spec(spec); spec.loader.exec_module(manager)
    return manager


def prepare():
    p = protocol(); manager = pilot_manager()
    assert manager.RESULT.exists(), 'Wait for complete original pilot receipts; do not rerun or use partial timing'
    checked = manager.collect(); assert checked['complete'] and checked['verified_jobs'] == 4
    source_info = manager.source_checked(); result = read(manager.RESULT)
    sizing = resources(p, result, source_info, digest(manager.SOURCE))
    plan = schedule(p, sizing['deals_per_job'])
    assert not OUT.exists(), 'Inspect existing preparation; never overwrite frozen controls'
    source = OUT/'source'; OUT.mkdir(); shutil.copytree(manager.LOCAL/'source', source)
    old_pins = read(source/'source-manifest.json')
    assert all(digest(source/name) == sha for name, sha in old_pins.items())
    artifact = source/'artifact'; runtime = read(artifact/'manifest.json')
    assert digest(artifact/'manifest.json') == p['base_runtime_manifest_sha256']
    assert digest(Path(__file__).with_name('public_policy_final_contract_v1.py')) == runtime['ai/strong/public_policy_final_contract_v1.py']
    controls = source/'development-controls'; controls.mkdir(); identities = {}
    for arm in p['arms']:
        assert read(artifact/f'policies/{arm}.json') == p['arms'][arm]
        identities[arm] = artifact_identity(artifact, f'policies/{arm}.json')
    now = datetime.now(timezone.utc).isoformat(); rows = []
    for item in plan:
        arm, shard = item['arm'], item['shard']; name = shard['name']
        candidate = f'runtime-controls/{arm}.candidate.json'; value = read(source/candidate)
        contract = {'version': 1, 'purpose': 'engineering', 'created_at': now,
            'candidate_sha256': digest(source/candidate), 'protocol_sha256': value['protocol_sha256'],
            'identity': identities[arm], 'shard': shard, 'launch_authorization': None}
        binding = admit(contract, value, digest(source/candidate), identities[arm]); assert not binding['reserved']
        if item['opponent_model']: assert digest(source/item['opponent_model']) == shard['opponent_sha256']
        contract_name = f'development-controls/{name}.contract.json'; write(source/contract_name, contract)
        job_name = f'development-controls/{name}.job.json'
        write(source/job_name, {'version': 1, 'artifact': 'artifact', 'descriptor': f'policies/{arm}.json',
            'candidate': candidate, 'contract': contract_name, 'workers': sizing['workers'],
            'opponent_model': item['opponent_model']})
        allocation = sizing['per_arm_count'][arm][str(shard['players'])]
        rows.append({'name': name, 'arm': arm, 'players': shard['players'], 'job': job_name,
            'shard': shard, 'identity': identities[arm], 'flavor': sizing['flavor'],
            'timeout': str(allocation['timeout_hours'])+'h',
            'candidate_sha256': digest(source/candidate), 'contract_sha256': digest(source/contract_name),
            'job_spec_sha256': digest(source/job_name)})
    admission = {'created_at': now, 'protocol_sha256': PROTOCOL_SHA,
        'runtime_results_sha256': digest(manager.RESULT), 'runtime_source_sha256': digest(manager.SOURCE),
        'sizing': sizing, 'identities': identities, 'games': 10080, 'rows': rows,
        'status': 'runtime_admitted_source_prepared_not_launched', 'reserved_final_seeds_used': False}
    write(source/'development-admission.json', admission)
    assert all(digest(source/name) == sha for name, sha in old_pins.items())
    pins = {str(path.relative_to(source)): digest(path) for path in sorted(source.rglob('*'))
            if path.is_file() and path != source/'source-manifest.json'}
    write(source/'source-manifest.json', pins)
    prepared = {**admission, 'source_manifest_sha256': digest(source/'source-manifest.json'),
        'admission_sha256': digest(source/'development-admission.json'), 'source_files': len(pins),
        'unchanged_base_files': len(old_pins), 'preparer_sha256': digest(__file__),
        'runtime_source': source_info, 'new_hf_jobs': 0}
    write(OUT/'prepared.json', prepared)
    print(json.dumps({'prepared': True, 'games': 10080, 'shards': len(rows),
        'deals_per_job': sizing['deals_per_job'], 'source_files': len(pins), 'new_hf_jobs': 0}), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__); parser.add_argument('operation', choices=['schedule', 'prepare'])
    parser.add_argument('--deals-per-job', type=int, default=4); args = parser.parse_args()
    if args.operation == 'prepare': prepare()
    else:
        plan = schedule(protocol(), args.deals_per_job)
        print(json.dumps({'preview_only': True, 'shards': len(plan), 'games': sum(r['shard']['games'] for r in plan),
            'by_arm': dict(Counter({arm: sum(r['shard']['games'] for r in plan if r['arm'] == arm) for arm in SHORT})),
            'runtime_admitted': False, 'new_hf_jobs': 0}), flush=True)
