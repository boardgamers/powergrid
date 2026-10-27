"""Ensure regression comparison cannot normalize away a playing-policy change."""
from copy import deepcopy
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('regression', Path(__file__).with_name('compare-conservative-auction-runtime-regression-v2.py'))
regression = importlib.util.module_from_spec(spec)
spec.loader.exec_module(regression)


class RegressionTests(unittest.TestCase):
    def setUp(self):
        self.old_identity = {'runtimeManifestSha256': 'old-runtime', 'policySha256': 'old-policy', 'modelSha256': 'same-model'}
        self.new_identity = {'runtimeManifestSha256': 'new-runtime', 'policySha256': 'new-policy', 'modelSha256': 'same-model'}
        core = {'move': {'name': 'Pass'}, 'index': 1, 'elapsedMs': 1,
                'search': {'components': [{'worker_sha256': 'old-worker', 'elapsedMs': 2, 'credits': [0, 1]}]}}
        self.old = {**deepcopy(core), 'publicRequest': {'state': {'money': 10}},
                    'publicResponse': {**self.old_identity, 'requestId': '1:2', 'decision': deepcopy(core), 'elapsedMs': 3}}
        self.new = deepcopy(self.old)
        self.new['publicResponse'].update(self.new_identity)
        for row in (self.new, self.new['publicResponse']['decision']):
            row['elapsedMs'] = 9
            row['search']['components'][0].update(worker_sha256=regression.NEW_WORKER, elapsedMs=10)
        self.new['publicResponse']['elapsedMs'] = 11

    def compare(self, row):
        regression.compare_receipt(self.old, row, self.old_identity, self.new_identity, 'old-worker')

    def test_only_declared_metadata_changes_are_allowed(self):
        old = deepcopy(self.old); new = deepcopy(self.new)
        self.compare(self.new)
        self.assertEqual(self.old, old)
        self.assertEqual(self.new, new)

    def test_changed_actions_world_outcomes_or_public_inputs_fail(self):
        mutations = [lambda r: r['move'].update(name='Build'),
                     lambda r: r.update(index=0),
                     lambda r: r['search']['components'][0]['credits'].__setitem__(0, 1),
                     lambda r: r['publicRequest']['state'].update(money=11),
                     lambda r: r['publicResponse']['decision']['move'].update(name='Build')]
        for mutation in mutations:
            row = deepcopy(self.new); mutation(row)
            with self.subTest(mutation=mutation), self.assertRaises(AssertionError): self.compare(row)

    def test_unpinned_identities_and_workers_fail(self):
        for container, key in [('response', 'modelSha256'), ('response', 'policySha256'), ('worker', 'worker_sha256')]:
            row = deepcopy(self.new)
            target = row['publicResponse'] if container == 'response' else row['search']['components'][0]
            target[key] = 'unexpected'
            with self.subTest(key=key), self.assertRaises(AssertionError): self.compare(row)


if __name__ == '__main__': unittest.main()
