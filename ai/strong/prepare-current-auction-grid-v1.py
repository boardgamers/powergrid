"""Size the frozen confirmation from complete pilots; never launch jobs.

The schedule can be tested in isolation. Source preparation requires all four
original pilots and independent raw audits, and uses their costs, not their wins.
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
import importlib.util
import json
import math
from pathlib import Path
import shutil

from public_policy_development_job_v1 import digest, read
from public_policy_final_audit_v1 import artifact_identity
from public_policy_final_contract_v1 import admit

ROOT = Path(__file__).resolve().parents[2]
PROTOCOL = ROOT / 'ai/strong/current-auction-confirmation-protocol-v1.json'
PROTOCOL_SHA = 'd0504c3f92d94fe96a1b336f26fe0e6c991502a3e03ff17fb1b2d00f53067d93'
OUT = ROOT / 'ai/runs/current-auction-grid-prepared-v1'
ARMS = ('filter', 'conservative_population')


def save(path, value):
    with Path(path).open('x') as stream:
        json.dump(value, stream, indent=2, allow_nan=False); stream.write('\n')


def protocol():
    assert digest(PROTOCOL) == PROTOCOL_SHA
    return read(PROTOCOL)


def schedule(p, sizing):
    assert set(p['arms']) == set(ARMS) and p['independent_deals_per_count'] == 32
    assert p['deal_offsets'] == list(range(32)) and p['planned_games_total'] == 26880
    assert p['seed_template'] == 'current-auction-confirmation-v1-{players}p'
    rows = []
    for arm in ARMS:
        short = 'filter' if arm == 'filter' else 'pop'
        for screen in p['screens']:
            n, opponent = screen['players'], screen['opponent']; allocation = sizing['per_arm_count'][arm][str(n)]
            deals = allocation['deals_per_job']
            assert type(deals) is int and deals in (1, 2, 4, 8, 16, 32)
            assert screen['deals'] == 32 and screen['games'] == 128*n
            for offset in range(0, 32, deals):
                name = f'pg-current-confirm-v1-{short}-{opponent}-{n}p-{offset:02d}'
                assert len(name) <= 63
                shard = {'name': name, 'group': f'{opponent}/{n}p', 'players': n, 'start': offset,
                    'deals': deals, 'seed': p['seed_template'].format(players=n), 'opponent': opponent,
                    'opponent_sha256': screen.get('sha256'), 'games': 4*n*deals}
                rows.append({'arm': arm, 'shard': shard,
                    'opponent_model': 'artifact/final-opponent-a260.onnx' if opponent == 'a260' else None})
    assert len({r['shard']['name'] for r in rows}) == len(rows)
    assert sum(r['shard']['games'] for r in rows) == 26880
    assert Counter({a: sum(r['shard']['games'] for r in rows if r['arm'] == a) for a in ARMS}) == {a: 13440 for a in ARMS}
    return rows


def resources(p, result, source, source_sha):
    assert result['complete'] is True and result['verified_jobs'] == len(result['jobs']) == 4
    assert result['source_sha256'] == source_sha and source['protocol_sha256'] == PROTOCOL_SHA
    assert source['workers'] == 4
    expected = {(r['arm'], r['players']) for r in p['runtime_pilots']}; seen = set(); measurements = []
    for job in result['jobs']:
        row, review = job['row'], job['review']; audit = review['audit']; m = review['measurement']
        key = row['arm'], row['players']; assert key in expected and key not in seen; seen.add(key)
        assert row in source['rows'] and row['flavor'] == 'cpu-upgrade'
        assert job['verified'] is True and job['stage'] == 'COMPLETED' and job['evidence']['remote_archive_verified']
        assert audit['all_receipts_verified'] and audit['expected'] == row['shard'] and audit['identity'] == row['identity']
        assert audit['counts']['rollout_caps'] == 0 and not audit['reserved_final_seeds_used']
        assert review['games'] == len(audit['terminals']) == row['shard']['games'] == 4*row['players']
        if row['arm'] == 'conservative_population':
            assert audit['counts']['rollouts'] > 0 and audit['counts']['search_decisions'] > 0
        else: assert audit['counts']['rollouts'] == 0
        assert m['memory_sampling_period_seconds'] == .2 and m['includes_startup_and_validation']
        assert all(type(m[k]) in (int, float) and math.isfinite(m[k]) and m[k] > 0
                   for k in ('seconds', 'cpu_seconds', 'sampled_peak_total_rss_bytes', 'memory_samples'))
        measurements.append({'name': row['name'], 'job_id': job['job_id'], 'arm': row['arm'],
                             'players': row['players'], 'games': review['games'], **m})
    assert seen == expected and seen == {(a,n) for a in ARMS for n in (2,6)}
    peak = max(m['sampled_peak_total_rss_bytes'] for m in measurements)
    assert 2*peak < .8*32*1024**3, 'Complete pilots exceed the planned memory envelope'
    per_game = {a: max(m['seconds']/m['games'] for m in measurements if m['arm'] == a) for a in ARMS}
    allocations = {}
    for arm in ARMS:
        allocations[arm] = {}
        for n in range(2, 7):
            projected = lambda d: 900 + 2*per_game[arm]*4*n*d
            eligible = [d for d in (1,2,4,8,16,32) if projected(d) <= 3*3600]
            deals = max(eligible) if eligible else 1
            timeout = math.ceil(projected(deals)/(.75*3600))
            assert timeout <= 24, 'A whole paired deal needs a new resource design'
            allocations[arm][str(n)] = {'deals_per_job': deals, 'projected_seconds_with_margin': projected(deals),
                'timeout_hours': timeout, 'exceeds_three_hour_target': projected(deals) > 3*3600}
    return {'flavor': 'cpu-upgrade', 'workers': 4, 'search_workers': 4, 'inference_threads': 1,
        'per_arm_count': allocations, 'measurements': measurements, 'per_game_seconds': per_game,
        'setup_allowance_seconds': 900, 'runtime_multiplier': 2, 'timeout_utilization': .75,
        'target_seconds_per_job': 3*3600, 'sampled_peak_rss_bytes': peak, 'memory_margin': 2,
        'max_active_jobs': 64,
        'rationale': 'Same tested concurrency/hardware. Per arm, use the slower endpoint per game, double it for unseen deals/counts/opponents, and pack whole deals to a three-hour target. Never use pilot outcomes. This is a planning allowance, not a statistical bound.'}


def pilot_manager():
    path = Path(__file__).with_name('manage-current-auction-runtime-v1.py')
    spec = importlib.util.spec_from_file_location('unchanged_current_pilots', path)
    value = importlib.util.module_from_spec(spec); spec.loader.exec_module(value); return value


def prepare():
    p = protocol(); manager = pilot_manager()
    assert manager.RESULT.exists(), 'Complete all four original pilots before source preparation'
    ready = read(ROOT / 'ai/strong/current-auction-grid-readiness-v1.json')
    assert ready['passed'] and all(digest(ROOT / n) == sha for n, sha in ready['input_hashes'].items())
    assert not OUT.exists(), 'Inspect existing source instead of rebuilding it'
    # Re-audit original raw files using the exact runtime collector; never submit.
    result = manager.collect(); assert result['complete'] and result['verified_jobs'] == 4
    source_info = manager.source_checked(); results = read(manager.RESULT)
    sizing = resources(p, results, source_info, digest(manager.SOURCE)); plan = schedule(p, sizing)
    source = OUT / 'source'; OUT.mkdir(); shutil.copytree(manager.LOCAL / 'source', source)
    old_pins = read(source / 'source-manifest.json')
    assert all(digest(source / name) == sha for name, sha in old_pins.items())
    artifact = source / 'artifact'; assert digest(artifact / 'manifest.json') == p['runtime_manifest_sha256']
    identities = {a: artifact_identity(artifact, f'policies/{a}.json') for a in ARMS}
    assert all(read(artifact / f'policies/{a}.json') == p['arms'][a] for a in ARMS)
    controls = source / 'confirmation-controls'; controls.mkdir(); now = datetime.now(timezone.utc).isoformat(); rows = []
    for item in plan:
        arm, shard = item['arm'], item['shard']; name = shard['name']; candidate = f'runtime-controls/{arm}.candidate.json'
        contract = {'version': 1, 'purpose': 'engineering', 'created_at': now,
            'candidate_sha256': digest(source / candidate), 'protocol_sha256': read(source / candidate)['protocol_sha256'],
            'identity': identities[arm], 'shard': shard, 'launch_authorization': None}
        assert not admit(contract, read(source / candidate), digest(source / candidate), identities[arm])['reserved']
        if item['opponent_model']: assert digest(source / item['opponent_model']) == shard['opponent_sha256']
        contract_name = f'confirmation-controls/{name}.contract.json'; save(source / contract_name, contract)
        job_name = f'confirmation-controls/{name}.job.json'
        save(source / job_name, {'version': 1, 'artifact': 'artifact', 'descriptor': f'policies/{arm}.json',
            'candidate': candidate, 'contract': contract_name, 'workers': sizing['workers'], 'opponent_model': item['opponent_model']})
        allocation = sizing['per_arm_count'][arm][str(shard['players'])]
        rows.append({'name': name, 'arm': arm, 'players': shard['players'], 'job': job_name, 'shard': shard,
            'identity': identities[arm], 'flavor': sizing['flavor'], 'timeout': str(allocation['timeout_hours'])+'h',
            'candidate_sha256': digest(source / candidate), 'contract_sha256': digest(source / contract_name),
            'job_spec_sha256': digest(source / job_name)})
    admission = {'created_at': now, 'protocol_sha256': PROTOCOL_SHA, 'runtime_results_sha256': digest(manager.RESULT),
        'runtime_source_sha256': digest(manager.SOURCE), 'sizing': sizing, 'identities': identities, 'games': 26880,
        'rows': rows, 'status': 'complete_pilots_admitted_source_prepared_not_launched', 'reserved_final_seeds_used': False}
    save(source / 'confirmation-admission.json', admission)
    assert all(digest(source / name) == sha for name, sha in old_pins.items())
    pins = {str(f.relative_to(source)): digest(f) for f in sorted(source.rglob('*'))
            if f.is_file() and f != source / 'source-manifest.json'}
    (source / 'source-manifest.json').write_text(json.dumps(pins, indent=2) + '\n')
    save(OUT / 'prepared.json', {**admission, 'source_manifest_sha256': digest(source / 'source-manifest.json'),
        'admission_sha256': digest(source / 'confirmation-admission.json'), 'source_files': len(pins),
        'unchanged_base_files': len(old_pins), 'preparer_sha256': digest(__file__), 'new_hf_jobs': 0})
    print(json.dumps({'prepared': True, 'games': 26880, 'shards': len(rows), 'sizing': sizing, 'new_hf_jobs': 0}), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__); parser.add_argument('operation', choices=['prepare'])
    globals()[parser.parse_args().operation]()
