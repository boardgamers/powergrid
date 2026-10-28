"""Freeze a fresh confirmation and prepare four current-engine runtime pilots.

No simulation, training, source upload or job submission. All strength deals are
fresh, paired across the two unchanged recipes, and separate from final seeds.
Whole-game runtime pilots must finish before the confirmation grid is admitted.
"""
from copy import deepcopy
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import shutil
import subprocess
import sys

from public_policy_development_job_v1 import digest, read
from public_policy_final_audit_v1 import artifact_identity, PROTOCOL_SHA
from public_policy_final_contract_v1 import admit

ROOT = Path(__file__).resolve().parents[2]
RUNTIME = ROOT / 'ai/runs/current-engine-auction-v2'
OUT = ROOT / 'ai/runs/current-auction-runtime-prepared-v1'
PROTOCOL = ROOT / 'ai/strong/current-auction-confirmation-protocol-v1.json'
EVIDENCE = ROOT / 'ai/strong/current-engine-auction-evidence-v2.json'
ARMS = ('filter', 'conservative_population')


def save(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2, allow_nan=False); stream.write('\n')


def main():
    assert not OUT.exists() and not PROTOCOL.exists(), 'Inspect existing preparation; never overwrite it'
    evidence = read(EVIDENCE); check = read(RUNTIME / 'assessment.json')
    assert evidence['archive']['remote_archive_verified'] and check['passed']
    assert evidence['reports']['2']['sha256'] == digest(RUNTIME / 'assessment.json')
    assert check['counts']['conservative_population']['exact_canonical_decisions'] == 140
    assert check['counts']['conservative_population']['wrapper_requests'] == 20
    assert check['counts']['conservative_population']['rollout_caps'] == 0
    prep = read(RUNTIME / 'prepared.json'); artifact = RUNTIME / 'artifact'
    assert digest(artifact / 'manifest.json') == prep['runtime_manifest_sha256'] == evidence['runtime_manifest_sha256']
    assert all(digest(artifact / p) == sha for p, sha in read(artifact / 'manifest.json').items())
    old_path = ROOT / 'ai/strong/conservative-auction-development-protocol-v2.json'; old = read(old_path)
    assert digest(old_path) == '51b845f4a57c3131475e24267fbbb08eb624c391aa6a8e6a4f5d5c6b8ac718ee'
    previous = ROOT / 'ai/strong/conservative-auction-comparison-evidence-v2.json'
    assert read(previous)['games'] == 10080 and read(previous)['archive']['remote_archive_verified']
    now = datetime.now(timezone.utc).isoformat()
    arms = {}
    for arm in ARMS:
        arms[arm] = read(artifact / f'policies/{arm}.json')
        expected = deepcopy(old['arms'][arm]); expected['runtime_manifest']['sha256'] = prep['runtime_manifest_sha256']
        assert arms[arm] == expected, 'Weights/features/search settings must remain unchanged'
    screens = [{**row, 'deals': 32, 'games': 128 * row['players']} for row in old['screens']]
    assert len(screens) == 27 and sum(s['games'] for s in screens) == 13440
    pilots = [{'arm': a, 'players': n, 'opponent': 'search_geo', 'deals': 1, 'games': 4*n}
              for a in ARMS for n in (2, 6)]
    protocol = {'version': 1, 'created_at': now,
        'purpose': 'Fresh confirmation of unchanged conservative population auction search versus the same filtered model on the current engine. Not reserved final qualification.',
        'previous_comparison_evidence_sha256': digest(previous), 'current_engine_evidence_sha256': digest(EVIDENCE),
        'current_engine_commit': prep['current_engine_commit'], 'runtime_manifest_sha256': prep['runtime_manifest_sha256'],
        'scope': {'map': 'Germany', 'players': [2, 3, 4, 5, 6], 'variants': ['original', 'recharged'],
            'auctions': ['open', 'sealed'], 'money': 'public', 'setup': 'automatic',
            'deck': 'standard', 'recharged_setup': 'current', 'endPlantDiscountAtStep3': False},
        'arms': arms, 'screens': screens, 'independent_deals_per_count': 32,
        'seed_template': 'current-auction-confirmation-v1-{players}p',
        'runtime_seed_template': 'current-auction-runtime-v1-{players}p', 'deal_offsets': list(range(32)),
        'planned_games_per_arm': 13440, 'planned_games_total': 26880,
        'pairing': 'Every independent deal repeats all seats and all four rules, shared across both arms and opponents. Preserve complete deal blocks.',
        'primary': 'Population minus filter: equal-weight mean terminal win-credit difference across the five search_geo player counts.',
        'secondary': 'All 27 count/opponent cells and every count/rule view, strict wins, tied-win credits, every adverse paired difference, actual search overrides and runtime costs.',
        'uncertainty': {'method': 'Paired whole-deal bootstrap of 32 independent deals per count; keep both arms, all seats/rules/opponents together.',
            'replicates': 10000, 'seed': 281028, 'confidence': .95,
            'interpretation': 'One prespecified primary contrast. Secondary intervals are marginal descriptive intervals, not simultaneous family-wide guarantees.'},
        'confirmation_success': [
            'Every planned game and decision audit completes, with no illegal moves or capped outcomes.',
            'Primary paired population-minus-filter interval lower endpoint is strictly greater than zero.',
            'Population search satisfies the unchanged final protocol point floors and per-count/per-rule above-chance interval requirements on these confirmation deals.',
            'Report all regressions and review them before final selection; no retrospective count/rule routing, threshold tuning, or automatic promotion.'],
        'game_max_steps': old['game_max_steps'], 'reference_search': old['reference_search'],
        'search_semantics': old['search_semantics'], 'model_pin': old['model_pin'],
        'runtime_pilots': pilots, 'runtime_pilot_games': 64,
        'admission': 'Finish four current-engine HF runtime pilots, then freeze job sizes/timeouts/concurrency from their complete measured costs. Pilot wins are excluded from strength.',
        'failure_policy': 'Preserve every original handle, failed game and partial receipt. No automatic retries, survivor-only comparisons or grid launch after a failed pilot. Diagnose before a separately recorded recovery decision.',
        'forbidden_changes': ['weights', 'feature revision', 'candidate shortlist', 'minimum advantage', 'sample budget', 'opponent population', 'auction-only scope'],
        'final_protocol_sha256': PROTOCOL_SHA, 'grid_admitted': False,
        'qualification_eligible': False, 'reserved_final_seeds_used': False, 'new_hf_jobs': 0}
    assert protocol['seed_template'] != old['seed_template'] and 'reserved' not in protocol['seed_template']
    assert digest(ROOT / 'ai/strong/final-protocol-multiplayer.json') == PROTOCOL_SHA
    save(PROTOCOL, protocol)
    source = OUT / 'source'; source.mkdir(parents=True)
    shutil.copytree(artifact, source / 'artifact')
    old_source = ROOT / 'ai/runs/conservative-auction-development-prepared-v2/source'
    for name in ('public_policy_development_job_v1.py', 'public_policy_measured_job_v1.py'):
        assert digest(old_source / name) == read(old_source / 'source-manifest.json')[name]
        shutil.copyfile(old_source / name, source / name)
    shutil.copyfile(PROTOCOL, source / 'experiment-protocol.json'); (source / 'runtime-controls').mkdir()
    identities = {a: artifact_identity(source / 'artifact', f'policies/{a}.json') for a in ARMS}
    for arm in ARMS:
        save(source / f'runtime-controls/{arm}.candidate.json', {'status': 'engineering', 'frozen_at': now,
             'identity': identities[arm], 'protocol_sha256': PROTOCOL_SHA, 'selection_evidence': None})
    historical_path = ROOT / 'ai/strong/conservative-auction-runtime-results-v2.json'
    historical = read(historical_path); assert historical['complete']
    calibration = [{'job_id': j['job_id'], 'players': j['row']['players'], 'games': j['review']['games'],
                    **j['review']['measurement']} for j in historical['jobs'] if j['row']['arm'] == 'conservative_population']
    assert len(calibration) == 2 and {r['players'] for r in calibration} == {2, 6}
    assert 2 * max(r['sampled_peak_total_rss_bytes'] for r in calibration) < .8 * 32 * 1024**3
    rows = []
    for pilot in pilots:
        arm, n = pilot['arm'], pilot['players']; short = 'filter' if arm == 'filter' else 'pop'
        name = f'pg-current-auction-runtime-v1-{short}-{n}p'
        shard = {'name': name, 'group': f'search_geo/{n}p', 'players': n, 'start': 0, 'deals': 1,
                 'seed': protocol['runtime_seed_template'].format(players=n), 'opponent': 'search_geo',
                 'opponent_sha256': None, 'games': 4*n}
        candidate = f'runtime-controls/{arm}.candidate.json'; contract = f'runtime-controls/{name}.contract.json'
        value = {'version': 1, 'purpose': 'engineering', 'created_at': now, 'candidate_sha256': digest(source / candidate),
                 'protocol_sha256': PROTOCOL_SHA, 'identity': identities[arm], 'shard': shard, 'launch_authorization': None}
        assert not admit(value, read(source / candidate), digest(source / candidate), identities[arm])['reserved']
        save(source / contract, value)
        job = f'runtime-controls/{name}.job.json'
        save(source / job, {'version': 1, 'artifact': 'artifact', 'descriptor': f'policies/{arm}.json',
            'candidate': candidate, 'contract': contract, 'workers': 4, 'opponent_model': None})
        seconds = next(r['seconds'] for r in calibration if r['players'] == n)
        timeout = math.ceil((900 + 2*seconds) / (.75*3600))
        rows.append({'name': name, 'arm': arm, 'players': n, 'job': job, 'shard': shard, 'identity': identities[arm],
            'candidate_sha256': digest(source / candidate), 'contract_sha256': digest(source / contract),
            'job_spec_sha256': digest(source / job), 'flavor': 'cpu-upgrade', 'timeout': f'{timeout}h'})
    assert sum(r['shard']['games'] for r in rows) == 64
    pins = {str(p.relative_to(source)): digest(p) for p in sorted(source.rglob('*')) if p.is_file()}
    save(source / 'source-manifest.json', pins)
    prepared = {'created_at': now, 'stage': 'prepared_not_launched', 'protocol_sha256': digest(PROTOCOL),
        'runtime_evidence_sha256': digest(EVIDENCE), 'runtime_manifest_sha256': prep['runtime_manifest_sha256'],
        'source_manifest_sha256': digest(source / 'source-manifest.json'), 'preparer_sha256': digest(__file__),
        'source_files': len(pins), 'rows': rows, 'games': 64, 'workers': 4,
        'calibration': calibration, 'calibration_sha256': digest(historical_path),
        'allocation': 'Four concurrent games, four search workers, one inference thread. Timeout uses 900 seconds setup plus twice historical same-count population pilot wall time within 75% of limit; filter conservatively uses the same bound.',
        'new_hf_jobs': 0, 'new_full_games': 0, 'new_gradients': 0, 'grid_admitted': False, 'reserved_final_seeds_used': False}
    save(OUT / 'prepared.json', prepared)
    for row in rows:
        with (OUT / (row['name'] + '.validation.log')).open('x') as log:
            subprocess.run([sys.executable, '-u', '-B', str(source / 'public_policy_development_job_v1.py'),
                '--source', str(source), '--manifest-sha256', prepared['source_manifest_sha256'],
                '--job', row['job'], '--output', str(OUT / 'validation-output' / row['name'])],
                cwd='/tmp', stdout=log, stderr=subprocess.STDOUT, check=True)
        assert not (OUT / 'validation-output' / row['name']).exists()
    assert all(digest(source / name) == sha for name, sha in pins.items())
    save(OUT / 'validated.json', {'passed': True, 'prepared_sha256': digest(OUT / 'prepared.json'),
        'jobs_validated': 4, 'games_executed': 0, 'new_hf_jobs': 0})
    print(json.dumps({'prepared': True, 'runtime_jobs': 4, 'runtime_games': 64,
        'confirmation_games': 26880, 'new_hf_jobs': 0}), flush=True)


if __name__ == '__main__': main()
