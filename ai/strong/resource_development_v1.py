"""Preregister the isolated resource ablation; this module cannot launch jobs."""
import argparse
import copy
from datetime import datetime, timezone

from strategic_collection import ROOT, read, write, digest

PROTOCOL = ROOT / 'ai/strong/resource-replanning-development-protocol-v1.json'
CURRENT_PROTOCOL = ROOT / 'ai/strong/population-hybrid-development-protocol-v1.json'
CURRENT_PLAN = ROOT / 'ai/strong/population-hybrid-development-plan-v1.json'
ARMS = ('filter', 'resource-filter')
SEED = 'resource-replanning-development-v1-{players}p'
SMOKE_SEED = 'resource-replanning-runtime-v1-{players}p'


def validate(protocol):
    assert protocol['status'] == 'preregistered_not_runtime_admitted_or_launched'
    assert tuple(protocol['arms']) == ARMS
    assert protocol['seed_template'] == SEED and protocol['smoke_seed_template'] == SMOKE_SEED
    assert protocol['deal_offsets'] == [0, 1, 2, 3]
    assert protocol['search']['samples'] == 8 and protocol['search']['horizon'] == 2400
    assert protocol['search']['nested_search'] is False
    assert protocol['execution_mode'] == 'stateless-atomic-resource-replanning-v1'
    assert protocol['game_max_steps'] == 1600
    assert protocol['hf_jobs_submitted'] == 0
    assert protocol['gradients'] is False
    assert protocol['bootstrap_replicates'] == 10000 and protocol['bootstrap_seed'] == 12317
    assert protocol['qualification_eligible'] is protocol['reserved_final_seeds_used'] is False
    expected = {(n, opponent) for n in range(2, 7)
                for opponent in ['legacy', 'heuristic', 'economic', 'rush', 'search_geo']}
    expected |= {(2, 'economic_capacity_v1'), (3, 'a260')}
    screens = protocol['screens']
    assert len(screens) == 27 and {(s['players'], s['opponent']) for s in screens} == expected
    for screen in screens:
        assert screen['deals'] == 4 and screen['games'] == 16 * screen['players']
    assert sum(s['games'] for s in screens) == protocol['planned_games_per_arm'] == 1680
    assert protocol['planned_games_total'] == 3360
    assert protocol['prerequisites']['current_comparison_required'] is True
    assert protocol['prerequisites']['new_resource_runtime_pilots_required'] is True
    assert protocol['prerequisites']['automatic_launch'] is False
    assert protocol['model_pin']['files']['inference64.onnx'] == '55331f43379e8fe89025d93b1a7a48c88e0ea39b4ebd3a7ef8240d4b62753530'


def case_rows(protocol, deals_per_shard):
    """Potential partitions; choosing one still requires measured admission."""
    validate(protocol)
    assert type(deals_per_shard) is int and deals_per_shard in [1, 2, 4]
    rows = []
    for arm in ARMS:
        for screen in protocol['screens']:
            n, opponent = screen['players'], screen['opponent']
            for start in range(0, 4, deals_per_shard):
                end = start + deals_per_shard
                rows.append({'case': f'resource-replanning-development-v1-{arm}-{n}p-{opponent}-{start}-{end}',
                             'arm': arm, 'players': n, 'opponent': opponent,
                             'start': start, 'end': end, 'games': 4 * n * deals_per_shard})
    assert sum(row['games'] for row in rows) == 3360
    assert len({row['case'] for row in rows}) == len(rows)
    return rows


def verify_pins(protocol):
    validate(protocol)
    assert digest(CURRENT_PLAN) == protocol['current_hybrid_plan_sha256']
    assert digest(CURRENT_PROTOCOL) == protocol['current_hybrid_protocol_sha256']
    assert protocol['model_pin'] == read(CURRENT_PROTOCOL)['model_pin']
    assert protocol['screens'] == read(CURRENT_PROTOCOL)['screens']
    assert digest(ROOT / 'ai/strong/final-protocol-multiplayer.json') == protocol['final_protocol_sha256']
    for path, sha in {**protocol['source_overlays'], **protocol['evidence_hashes']}.items():
        assert digest(ROOT / path) == sha, path
    for path, sha in read(CURRENT_PLAN)['dependency_hashes'].items():
        assert digest(ROOT / path) == sha, path


def prepare():
    assert not PROTOCOL.exists()
    current, plan = read(CURRENT_PROTOCOL), read(CURRENT_PLAN)
    atomic = read(ROOT / 'ai/strong/resource-replanning-evidence-v1.json')
    target = read(ROOT / 'ai/strong/resource-replanning-8840u-evidence-v1.json')
    assert atomic['status'] == 'verified_stateless_resource_replanning_research_only'
    assert target['status'] == 'verified_actual8840u_resource_stress_benchmark'
    assert atomic['normal_caps'] == 0 and target['exact_searches'] == 12
    base = ROOT / 'ai/runs/resource-replanning-v1'
    provenance = read(base / 'preparation.json')
    source_files = {**provenance['runtime_hashes'], **provenance['new_files']}
    for path, sha in source_files.items():
        assert digest(base / 'runtime' / path) == sha
    overlays = ['resource-turn-plans-v1.cjs', 'resource-turn-search-v1.cjs',
                'resource_turn_search_v1.py', 'resource_replanning_policy_v1.py',
                'evaluate-resource-replanning-v1.py', 'resource_policy_verification_v1.py']
    for name in overlays[:-1]:
        assert digest(ROOT / 'ai/strong' / name) == source_files['ai/strong/' + name]
    evidence = ['resource-replanning-evidence-v1.json', 'resource-replanning-8840u-evidence-v1.json',
                'resource-turn-search-evidence-v1.json']
    protocol = {
        'status': 'preregistered_not_runtime_admitted_or_launched',
        'created_at': datetime.now(timezone.utc).isoformat(),
        'purpose': 'Isolate the strength/cost effect of stateless resource replanning over the same trained model and strict endgame filter. Fresh development screen, not qualification.',
        'current_hybrid_plan_sha256': digest(CURRENT_PLAN),
        'current_hybrid_protocol_sha256': digest(CURRENT_PROTOCOL),
        'base_source': plan['source'],
        'model_pin': copy.deepcopy(current['model_pin']),
        'source_overlays': {'ai/strong/' + name: digest(ROOT / 'ai/strong' / name) for name in overlays},
        'evidence_hashes': {'ai/strong/' + name: digest(ROOT / 'ai/strong' / name) for name in evidence},
        'arms': {'filter': 'Frozen-1 model with strict losing-endgame Build filter.',
                 'resource-filter': 'Identical filter policy outside Resources; evaluate whole resource bundles but execute only the first atomic action, then replan from the next public request.'},
        'execution_mode': 'stateless-atomic-resource-replanning-v1',
        'seed_template': SEED, 'smoke_seed_template': SMOKE_SEED,
        'deal_offsets': [0, 1, 2, 3], 'screens': copy.deepcopy(current['screens']),
        'planned_games_per_arm': 1680, 'planned_games_total': 3360,
        'search': {
            'samples': 8, 'horizon': 2400, 'nested_search': False,
            'candidates': 'All generated one/two-identical-cycle fuel bundles plus Pass and the exact model resource turn; retain unusual partial model stockpiles. No construction annotation prunes a bundle.',
            'focal_continuation': 'Complete the hypothetical bundle, then trained model plus strict endgame loss filter. Future replanning is approximated, not recursively searched.',
            'opponent_continuation': 'Each opponent uses neural/economic/legacy/rush twice across eight worlds. Public sampled deck and equal uncalibrated policy mixture.',
            'selection': 'Mean completed terminal credit; ties retain model bundle then original bundle order. Any cap returns model first action and invalidates strength/runtime admission.',
            'root_execution': 'One action per request, no retained plan. Independently verify actual atomic games, not committed-macro scores as playing strength.'},
        'game_max_steps': 1600,
        'reference_search': current['reference_search'],
        'bootstrap_replicates': 10000, 'bootstrap_seed': 12317,
        'analysis': {
            'contrast': 'resource-filter minus filter, paired by identical deal, seat, count, rules and opponent.',
            'all_cells': 'Report all 27 count/opponent cells and all four rules, full terminal outcomes, caps, decision/search counts and latency. Never use a partial grid or discard adverse cells.',
            'primary_summary': 'Equal-weight average of the five search_geo player-count win-share differences, each averaging all seats and four rules. Bootstrap whole deals independently within each player count; do not overweight six-player counts.',
            'secondary': 'Equal-weight economic summary and all per-count/per-rule/per-opponent contrasts. Descriptive fuel/city deficits are exploratory, not additional selection gates.',
            'limits': 'Four independent deals per cell gives coarse exploratory intervals. No automatic promotion; a favorable completed screen only motivates larger fresh confirmation with all regressions retained. No rule/count-specific routing.'},
        'prerequisites': {
            'current_comparison_required': True,
            'current_comparison': 'ai/strong/population-hybrid-development-comparison-v1.json',
            'current_completion': 'All 135 shards verified, complete 8400-game comparison, no caps/failures; review before proceeding. Do not launch pilots or jobs while it is incomplete.',
            'new_resource_runtime_pilots_required': True,
            'pilots': 'After the current comparison: full paired endpoint deals at 2p and 6p, all seats/rules, eight resource worlds, search_geo opponents, fresh runtime-only seeds; exclude outcomes from strength. Verify raw decisions and independently replay representative games.',
            'admission': 'Pin/upload a separate source and job/verifier package, then measure CPU/RAM and complete-game runtime before setting hardware, concurrency and timeout. Split whole deals rather than shortening rollout/game horizons. No assumed reuse of old auction/building runtime admission.',
            'automatic_launch': False},
        'sealed_scope': 'Canonical arena bidder order using unchanged frozen module. The separately verified asynchronous-order repair is not silently included; a serving candidate must pin/test it separately.',
        'final_protocol_sha256': current['final_protocol_sha256'],
        'hf_jobs_submitted': 0, 'gradients': False,
        'qualification_eligible': False, 'reserved_final_seeds_used': False}
    verify_pins(protocol)
    write(PROTOCOL, protocol)
    print({'protocol': str(PROTOCOL), 'planned_games': 3360, 'launched': False})


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('operation', choices=['prepare', 'validate'])
    args = parser.parse_args()
    if args.operation == 'prepare':
        prepare()
    else:
        verify_pins(read(PROTOCOL))
        print({'valid': True, 'launched': False})
