"""Independent atomic-resource receipts; no inference, games, jobs or selection.

The frozen whole-game checker is loaded privately with this decision checker.
Its terminal, pairing, hashes and report checks stay intact. Receipt consistency
cannot alone prove engine legality or reproduce inference; those require replay.
"""
from collections import Counter
import importlib.util
from pathlib import Path
import re

from population_policy_verification import verify_decision as verify_base_decision
from population_policy_verification import integer, finite

RESOURCES = ('coal', 'oil', 'garbage', 'uranium')
ROLES = {'neural', 'economic', 'legacy', 'rush'}
RESOURCE_ARMS = ('resource-filter', 'resource-combined')
EXECUTION = 'stateless-atomic-resource-replanning-v1'
PASS = {'name': 'Pass', 'data': True}


def vector(values, length):
    assert isinstance(values, list) and len(values) == length
    for value in values:
        integer(value)


def verify_plan(plan, config, seat, *, horizon=2400, allow_caps=False):
    n, samples = config['players'], config['samples']
    assert n in range(2, 7) and type(seat) is int and 0 <= seat < n
    assert type(samples) is int and samples in range(4, 65, 4)
    assert plan['revision'] == 'resource-turn-search-v1'
    assert plan['modelSha256'] == config['model_sha256']
    assert plan['featureRevision'] == '4.3-strategic-correction'
    assert plan['qualification_eligible'] is False
    assert plan['executionContract'] == 'Execute the complete returned resource turn. Replanning each purchase is a different policy.'
    finite(plan['elapsedMs'])
    bundles = plan['bundles']
    # A legal atomic buy can exist even when the candidate family and model
    # baseline both reduce to Pass. The current runtime still evaluates it.
    assert isinstance(bundles, list) and len(bundles) >= 1
    assert len({b['id'] for b in bundles}) == len(bundles)
    assert '0,0,0,0' in {b['id'] for b in bundles}
    baseline, selected = plan['baseline'], plan['selected']
    for index in (baseline, selected):
        integer(index)
        assert index < len(bundles)
    trace = plan['baselineDecisions']
    assert isinstance(trace, list) and trace
    for decision in trace:
        integer(decision['index'])
    assert [d['move'] for d in trace] == bundles[baseline]['actions']
    for i, bundle in enumerate(bundles):
        vector(bundle['counts'], 4)
        integer(bundle['cost'])
        assert type(bundle['baseline']) is bool and bundle['baseline'] is (i == baseline)
        assert bundle['id'] == ','.join(map(str, bundle['counts']))
        actions = bundle['actions']
        assert isinstance(actions, list) and actions and actions[-1] == PASS
        counts = [0] * 4
        for action in actions[:-1]:
            assert set(action) == {'name', 'data'} and action['name'] == 'BuyResource'
            assert set(action['data']) == {'resource'} and action['data']['resource'] in RESOURCES
            counts[RESOURCES.index(action['data']['resource'])] += 1
        assert counts == bundle['counts'] and len(actions) == sum(counts) + 1
        if not sum(counts):
            assert bundle['cost'] == 0
    assert plan['actions'] == bundles[selected]['actions']
    assert plan['firstMove'] == plan['actions'][0]

    search = plan['search']
    assert search['samples'] == samples and search['maxSteps'] == horizon
    assert re.fullmatch(r'hybrid-public-v1-[a-f0-9]{64}', search['seed'])
    assert search['valueStatus'] == 'simulated-terminal-credits-not-calibrated-win-probabilities'
    integer(search['neuralDecisions'])
    worlds = search['worlds']
    assert set(worlds) == {str(i) for i in range(samples)}
    for world in worlds.values():
        roles = world['roles']
        assert len(roles) == n and set(roles) <= ROLES and roles[seat] == 'neural'
        belief = world['initialBelief']
        assert belief['kind'] == 'resource_population_v1' and belief['committed'] == []
        assert re.fullmatch(r'[a-f0-9]{64}', belief['sampledWorldSha256'])
    for player in range(n):
        if player != seat:
            assert Counter(w['roles'][player] for w in worlds.values()) == {r: samples // 4 for r in ROLES}
            assert all(worlds[str(i)]['roles'][player] == worlds[str(i % 4)]['roles'][player]
                       for i in range(samples))

    receipts = plan['receipts']
    assert len(receipts) == search['evaluations'] == samples * len(bundles)
    scores = {b['id']: [] for b in bundles}
    initial = None
    caps = neural = 0
    for index, receipt in enumerate(receipts):
        sample, action_index = divmod(index, len(bundles))
        bundle = bundles[action_index]
        assert receipt['env'] == index and receipt['sample'] == sample
        assert receipt['actionIndex'] == action_index
        world = worlds[str(sample)]
        assert receipt['roles'] == world['roles'] and receipt['initialBelief'] == world['initialBelief']
        assert receipt['searchStats'] == {'decisions': 0, 'evaluations': 0, 'truncated': 0}
        turn = receipt['resourceTurn']
        for key in ('actions', 'counts', 'cost'):
            assert turn[key] == bundle[key]
        assert turn['bundleId'] == bundle['id']
        after = turn['afterPurchases']
        integer(after['money'])
        vector(after['stock'], 4)
        vector(after['market'], 4)
        # All candidate worlds start from the same visible inventory, cash and
        # market. This checks receipt consistency, not prices against an engine.
        before = {'money': after['money'] + bundle['cost'],
                  'stock': [v - k for v, k in zip(after['stock'], bundle['counts'])],
                  'market': [v + k for v, k in zip(after['market'], bundle['counts'])]}
        vector(before['stock'], 4)
        if initial is None:
            initial = before
        assert before == initial
        decisions = receipt['policyDecisions']
        assert set(decisions) == ROLES | {'forced'}
        for value in decisions.values():
            integer(value)
        integer(receipt['steps'])
        assert sum(decisions.values()) == receipt['steps'] <= horizon
        neural += decisions['neural']
        assert type(receipt['truncated']) is bool
        if receipt['truncated']:
            assert receipt['value'] is None and receipt['terminal'] is None
            assert receipt['steps'] == horizon
            caps += 1
        else:
            terminal = receipt['terminal']
            assert isinstance(terminal, list) and len(terminal) == n
            final_scores = []
            for player in terminal:
                for key in ('powered', 'money', 'cities', 'capacity'):
                    integer(player[key])
                assert player['powered'] <= min(player['cities'], player['capacity'])
                final_scores.append(tuple(player[k] for k in ('powered', 'money', 'cities')))
            best = max(final_scores)
            credit = 1 / final_scores.count(best) if final_scores[seat] == best else 0
            finite(receipt['value'])
            assert receipt['value'] == credit
        scores[bundle['id']].append(receipt['value'])
    assert neural == search['neuralDecisions']
    assert scores == search['sampleOutcomes']
    integer(search['truncated'])
    assert search['truncated'] == caps and search['usable'] is (caps == 0)
    if caps:
        assert allow_caps, 'Incomplete resource rollout invalidates the result'
        assert search['fallbackReason'] == 'incomplete-rollouts' and search['meanCredits'] is None
        assert selected == baseline
    else:
        assert search['fallbackReason'] is None
        means = {key: sum(values) / len(values) for key, values in scores.items()}
        assert set(search['meanCredits']) == set(means)
        assert all(abs(value - search['meanCredits'][key]) < 1e-12 for key, value in means.items())
        chosen = max(range(len(bundles)), key=lambda i: (means[bundles[i]['id']], i == baseline, -i))
        assert selected == chosen
    return {'rollouts': len(receipts), 'rollout_caps': caps, 'neural_decisions': neural}


def verify_decision(row, config, seat, *, horizon=2400, allow_caps=False):
    arm = config['arm']
    if arm not in RESOURCE_ARMS:
        assert 'resourcePlan' not in row and 'executionMode' not in row
        return verify_base_decision(row, config, seat, horizon=horizon, allow_caps=allow_caps)
    assert row['arm'] == arm and row['executionMode'] == EXECUTION
    base = {**row, 'arm': arm.removeprefix('resource-')}
    base_config = {**config, 'arm': base['arm']}
    plan = row['resourcePlan']
    if plan is None:
        assert row['phase'] != 'resources'
        return verify_base_decision(base, base_config, seat, horizon=horizon, allow_caps=allow_caps)
    assert row['phase'] == 'resources' and not row['filterApplied'] and row['filterCertificate'] is None
    assert row['search'] == plan['search'] and row['modelSha256'] == plan['modelSha256']
    assert row['featureRevision'] == plan['featureRevision']
    assert row['qualification_eligible'] is False
    integer(row['index'])
    integer(row['modelProposal'])
    finite(row['elapsedMs'])
    assert row['move'] == plan['firstMove']
    assert row['modelProposal'] == plan['baselineDecisions'][0]['index']
    assert (row['index'] == row['modelProposal']) is (row['move'] == plan['baselineDecisions'][0]['move'])
    counts = verify_plan(plan, config, seat, horizon=horizon, allow_caps=allow_caps)
    return {**counts, 'decisions': 1, 'root_filter_overrides': 0,
            'search_changes': int(row['index'] != row['modelProposal']),
            'search_decisions': 1, 'resource_search_decisions': 1}


def verify_evaluation(directory, expected):
    """Reuse complete-game integrity checks with a private decision adapter."""
    path = Path(__file__).with_name('population_policy_verification.py')
    spec = importlib.util.spec_from_file_location('resource_report_base_v1', path)
    base = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(base)
    base.verify_decision = verify_decision
    return base.verify_evaluation(directory, expected)
