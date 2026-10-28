"""Independent seed-binding audit from chronological public requests.

Does not call the history-rewind helper. Retains the actual first request's seed
and compares subsequent receipts against it, then uses the frozen arithmetic
auditor for the unchanged candidate/continuation protocol.
"""
from copy import deepcopy

from hybrid_search import public_seed
from resource_policy_verification_v1 import verify_decision as verify_original
from resource_policy_verification_v1 import verify_plan as verify_original_plan

REVISION = 'resource-turn-search-anchored-v1'
MODE = 'turn-start-public-history-v1'


def original_plan(plan, expected):
    assert plan['revision'] == REVISION
    assert plan['search']['sampling'] == expected['sampling'], 'Sampling receipt differs from public history'
    assert plan['search']['seed'] == expected['seed'], 'Search did not use the actual first-decision seed'
    result = deepcopy(plan)
    result['revision'] = 'resource-turn-search-v1'
    del result['search']['sampling']
    return result


def verify_plan(plan, config, seat, expected):
    return verify_original_plan(original_plan(plan, expected), config, seat)


class SamplingAudit:
    def __init__(self, prepare_call):
        self.prepare_call = prepare_call
        self.origin = None
        self.buys = 0

    def expected(self, request):
        state, seat = request['state'], request['player']
        assert state['phase'] == 'Resources' and state['map']['name'] == 'Germany'
        assert state['options']['showMoney'] and state['currentPlayers'] == [seat]
        root = self.prepare_call({'op': 'prepare', 'state': state, 'player': seat,
                                  'featureRevision': '4.3-strategic-correction'})
        current = public_seed(root)
        if self.origin is None:
            assert state['newTurn'] is True, 'Audit requires the actual start of the resource turn'
            self.origin = {'seed': current, 'round': state['round'], 'step': state['step'],
                'player': seat, 'money': state['players'][seat]['money'], 'logLength': len(state['log'])}
            self.buys = 0
        start = self.origin
        assert (start['round'], start['step'], start['player']) == (state['round'], state['step'], seat)
        assert state['newTurn'] is (self.buys == 0)
        assert len(state['log']) == start['logLength'] + self.buys
        assert all(entry['type'] == 'move' and entry['player'] == seat and entry['move']['name'] == 'BuyResource'
                   for entry in state['log'][start['logLength']:])
        return {'seed': start['seed'], 'sampling': {'mode': MODE, 'currentSeed': current,
            'anchor': {'revision': 'resource-turn-public-history-anchor-v1',
                'round': state['round'], 'step': state['step'], 'player': seat,
                'purchasesRewound': self.buys, 'costRewound': start['money'] - state['players'][seat]['money'],
                'boundaryLogLength': start['logLength'], 'historyRequired': 'complete-canonical-public-log',
                'qualification_eligible': False}}}, root

    def verify(self, request, decision, config):
        seat = request['player']
        if request['state']['phase'] != 'Resources':
            assert self.origin is None, 'Resource turn ended without a recorded Pass'
            return verify_original(decision, config, seat)
        expected, root = self.expected(request)
        assert root['moves'][decision['index']] == decision['move']
        plan = decision['resourcePlan']
        if plan is None:
            assert len(root['moves']) == 1, 'Search missing on a non-forced resource decision'
            result = verify_original(decision, config, seat)
        else:
            assert decision['search'] == plan['search']
            converted = deepcopy(decision)
            converted['resourcePlan'] = original_plan(plan, expected)
            converted['search'] = converted['resourcePlan']['search']
            result = verify_original(converted, config, seat)
        if decision['move'] == {'name': 'Pass', 'data': True}:
            self.origin = None
            self.buys = 0
        else:
            assert decision['move']['name'] == 'BuyResource'
            self.buys += 1
        return result
