"""Complete fresh-root shard checks, including every count/deal/seat/rule contract."""
import math
from pathlib import Path

from strategic_collection import read, digest
from hybrid_search import Model
from population_hybrid_policy import PopulationPolicy
from surrogate_continuation_roots_v1 import contract, verify_game


def verify_artifacts(folder, evidence, source, protocol, runtime, model_path, players, start, end, mode):
    folder, runtime = Path(folder), Path(runtime)
    assert mode in ('root', 'runtime') and type(players) is int and players in protocol['player_counts']
    assert type(start) is type(end) is int and 0 <= start < end <= protocol['deals_per_count']
    if mode == 'runtime': assert players in (2, 6) and (start, end) == (0, 1)
    manifest = read(folder/'manifest.json')
    assert {str(p.relative_to(folder)) for p in folder.rglob('*') if p.is_file()} == set(manifest) | {'manifest.json'}
    assert digest(folder/'manifest.json') == evidence['manifest_sha256'] and len(manifest)+1 == evidence['archived_files']
    assert all(digest(folder/name) == sha for name, sha in manifest.items())
    job, state, intent = (read(folder/name) for name in ('job.json', 'games/status.json', 'games/intent.json'))
    assert job['stage'] == state['stage'] == 'complete' and intent['stage'] == 'running'
    assert not state['errors'] and intent['errors'] == [] and intent['cases'] == {}
    assert job['case'] == f'surrogate-continuation-{mode}-v1-{players}p-{start}-{end}'
    assert (job['players'], job['start'], job['end'], job['mode']) == (players, start, end, mode)
    assert job['source_revision'] == source['revision'] and job['source_sha256'] == source['sha256']
    assert job['source_manifest_sha256'] == source['manifest_sha256']
    assert job['job_runner_sha256'] == source['new_files']['ai/strong/surrogate-continuation-roots-job-v1.py']
    assert state['runner_sha256'] == intent['runner_sha256'] == source['new_files']['ai/strong/surrogate_continuation_roots_v1.py']
    for row in (job, state, intent):
        assert row['protocol_sha256'] == source['protocol_sha256']
        assert all(row[key] is False for key in ('gradients', 'qualification_eligible', 'reserved_final_seeds_used'))
    assert job['automatic_retries'] is False and job['caps'] == 0
    expected = {str(4*(deal*players+seat)+rule): contract(players, deal, seat, rule, mode)
                for deal in range(start, end) for seat in range(players) for rule in range(4)}
    assert state['tasks'] == intent['tasks'] and len(state['tasks']) == len(expected)
    assert set(state['cases']) == set(expected)
    assert {(task['deal'], task['seat'], task['rule']) for task in state['tasks']} == {
        (deal, seat, rule) for deal in range(start, end) for seat in range(players) for rule in range(4)}
    assert all(task['players'] == players and task['mode'] == mode and task['twin'] is (mode == 'runtime') for task in state['tasks'])
    assert digest(runtime/'surrogate-continuation-roots-source-manifest.json') == source['manifest_sha256']
    assert all(digest(runtime/name) == sha for name, sha in read(runtime/'surrogate-continuation-roots-source-manifest.json').items())
    model = Model(model_path, threads=1); assert model.sha256 == protocol['focal_model_sha256']
    policy = PopulationPolicy(model, runtime/'ai/strong/population-hybrid-policy.cjs', arm='filter')
    checks = {}; counts = {'eligible_decisions': 0, 'selected_roots': 0}; phase_counts = {}
    try:
        for episode, q in expected.items():
            game = folder/'games'/f'game-{episode}'; result = read(game/'verified.json')
            assert result == state['cases'][episode] and read(game/'contract.json') == q and result['twin_exact'] is (mode == 'runtime')
            assert {p.name for p in game.iterdir()} == {'contract.json', 'decisions.jsonl', 'roots.json', 'terminal.json', 'verified.json'}
            checks[episode] = verify_game(game, policy)
            for key in counts: counts[key] += checks[episode][key]
            for phase in read(game/'roots.json')['roots']:
                key = f'{players}/{q["rule"]}/{phase}'; phase_counts[key] = phase_counts.get(key, 0)+1
    finally: policy.close()
    assert read(folder/'root-audit.json') == checks
    assert job['games'] == len(expected) and job['twin_games'] == (len(expected) if mode == 'runtime' else 0)
    assert job['selected_roots'] == state['selected_roots'] == counts['selected_roots']
    assert job['eligible_decisions'] == counts['eligible_decisions']
    for key in ('seconds', 'cpu_seconds', 'sampled_peak_total_rss_bytes', 'memory_samples'):
        value = job['runtime'][key]; assert type(value) in (int, float) and math.isfinite(value) and value > 0
    return {'complete': True, 'players': players, 'start': start, 'end': end, 'mode': mode,
            'games': len(expected), 'twin_games': job['twin_games'], **counts, 'caps': 0, 'phase_counts': phase_counts,
            'missing_phases': {episode: check['missing_phases'] for episode, check in checks.items() if check['missing_phases']},
            'runtime': job['runtime'], 'raw_evidence_bytes': sum(p.stat().st_size for p in folder.rglob('*') if p.is_file()),
            'local_root_checks': checks, 'training_eligible': False, 'qualification_eligible': False}
