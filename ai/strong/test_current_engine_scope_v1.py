"""Unsupported game variants must be rejected before model/search construction."""
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import unittest

from current_engine_scope_v1 import validate_request_scope

ROOT = Path(__file__).resolve().parents[2]


class ScopeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases = json.loads((ROOT / 'ai/runs/conservative-auction-8840u-prepared-v2/package/cases.json').read_text())

    def test_all_existing_count_rule_stage_cases_supported(self):
        for case in self.cases:
            with self.subTest(case=case['name']): validate_request_scope(case['fixture']['request'])

    def invalid_cases(self):
        original = self.cases[0]['fixture']['request']
        for field in ('alternatePowerPlants', 'endPlantDiscountAtStep3', 'chooseRegions', 'chooseColors', 'randomizeMap'):
            q = deepcopy(original); q['state']['options'][field] = True; yield q
        for field, value in [('variant', 'unknown'), ('showMoney', False), ('fastBid', 'yes'), ('futureRule', True)]:
            q = deepcopy(original); q['state']['options'][field] = value; yield q
        q = deepcopy(original); q['state']['options'].update(variant='recharged', useNewRechargedSetup=False); yield q
        q = deepcopy(original); q['state']['map']['name'] = 'France'; yield q
        q = deepcopy(original); q['state']['players'][0]['money'] = -1; yield q

    def test_unvalidated_options_and_hidden_balances_rejected(self):
        for i, request in enumerate(self.invalid_cases()):
            with self.subTest(case=i), self.assertRaises(ValueError): validate_request_scope(request)

    def test_public_zero_balance_remains_supported(self):
        request = deepcopy(self.cases[0]['fixture']['request'])
        request['state']['players'][0]['money'] = 0
        validate_request_scope(request)

    def test_actual_transport_rejects_before_factory(self):
        code = '''import sys,json
sys.path.insert(0,sys.argv[1])
from public_policy_runtime_v1 import PublicPolicyService
calls=[]
def factory():
    calls.append(1)
    raise RuntimeError('factory reached')
service=PublicPolicyService(factory)
requests=json.load(sys.stdin)
for q in requests['bad']:
    response=service.handle_line(json.dumps(q))
    assert response['error'].startswith('ValueError:'),response
    assert response['requestId']==q['requestId'] and response['revision']==q['revision']
assert not calls
response=service.handle_line(json.dumps(requests['valid']))
assert response['error']=='RuntimeError: factory reached' and len(calls)==1
print(json.dumps({'unsupported_requests_rejected_before_factory':len(requests['bad'])}))
'''
        result = subprocess.run([sys.executable, '-B', '-c', code,
            str(ROOT / 'ai/runs/current-engine-auction-v1/artifact/ai/strong')],
            input=json.dumps({'bad': list(self.invalid_cases()), 'valid': self.cases[0]['fixture']['request']}),
            text=True, capture_output=True, check=True)
        self.assertEqual(json.loads(result.stdout)['unsupported_requests_rejected_before_factory'], 12)


if __name__ == '__main__': unittest.main()
