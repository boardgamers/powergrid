"""Check the parity boundary using recorded decisions; never play or submit a game."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from strategic_collection import ROOT, read, write, digest

spec = importlib.util.spec_from_file_location('resource_hf_runtime_collection',
    Path(__file__).with_name('collect-resource-replanning-hf-runtime-v1.py'))
collector = importlib.util.module_from_spec(spec)
spec.loader.exec_module(collector)


class ResourceParityTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        base = ROOT / 'ai/runs/resource-replanning-runtime-source-prepared-v1/layout/ai/runs/resource-replanning-runtime-v1/2p-resource-filter/evaluation'
        report = read(base / 'evaluation.json')
        assert digest(base / 'evaluation.json') == 'ee37e2882a03d96828cdf46d1cb1145cdcfe5cf3522e1c0f9526c1c41ad26372'
        cls.config = report['config']
        with (base / 'decisions-0.jsonl').open() as stream:
            cls.row = next(json.loads(line) for line in stream if json.loads(line).get('resourcePlan') is not None)
        cls.temp = tempfile.TemporaryDirectory()
        cls.base = Path(cls.temp.name)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def evaluation(self, folder, row, *, config_change=None, terminal_change=False):
        folder.mkdir(exist_ok=True)
        receipt = folder / 'decisions-0.jsonl'
        receipt.write_text(json.dumps(row) + '\n')
        config = copy.deepcopy(self.config)
        config.update(config_change or {})
        report = {'config': config, 'seconds': row['elapsedMs'] / 1000 + 10,
                  'results': [{'episode': 0, 'decisions': 1, 'seconds': 100,
                               'terminal': {'fixture_only': True, 'changed': terminal_change},
                               'decision_receipt_sha256': digest(receipt)}]}
        write(folder / 'evaluation.json', report)
        return folder

    def test_only_documented_paths_and_timings_are_ignored(self):
        row = copy.deepcopy(self.row)
        row['elapsedMs'] += 100
        row['resourcePlan']['elapsedMs'] += 100
        left = self.evaluation(self.base / 'left', self.row)
        right = self.evaluation(self.base / 'right', row, config_change={
            'model': '/other/model.onnx', 'runtime': '/workspace', 'output': '/other/output'})
        result = collector.paired_parity(left, right)
        self.assertTrue(result['exact'])
        self.assertEqual(result['learner_decisions'], 1)
        self.assertEqual(result['resource_decisions'], 1)
        self.assertEqual(result['resource_rollouts'], self.row['search']['evaluations'])

    def test_policy_and_simulation_changes_are_not_hidden(self):
        left = self.evaluation(self.base / 'left', self.row)
        edits = {
            'move': lambda row: row.update(move={'name': 'Pass', 'data': True}),
            'model_proposal': lambda row: row.update(modelProposal=999),
            'world': lambda row: row['resourcePlan']['search']['worlds']['0']['initialBelief'].update(sampledWorldSha256='0' * 64),
            'resource_cost': lambda row: row['resourcePlan']['receipts'][0]['resourceTurn'].update(cost=999),
            'rollout_terminal': lambda row: row['resourcePlan']['receipts'][0]['terminal'][0].update(money=999),
            'new_timing_field': lambda row: row['search'].update(elapsedMs=123),
        }
        for name, edit in edits.items():
            with self.subTest(name=name):
                row = copy.deepcopy(self.row)
                edit(row)
                right = self.evaluation(self.base / 'right', row)
                with self.assertRaisesRegex(AssertionError, 'decision 1 differs'):
                    collector.paired_parity(left, right)

    def test_changed_seed_terminal_and_unlisted_path_are_rejected(self):
        left = self.evaluation(self.base / 'left', self.row)
        for changes in ({'config_change': {'seed': 'unexpected'}}, {'terminal_change': True},
                        {'config_change': {'new_path': '/not-an-excluded-field'}}):
            with self.subTest(changes=changes):
                right = self.evaluation(self.base / 'right', self.row, **changes)
                with self.assertRaises(AssertionError):
                    collector.paired_parity(left, right)

    def test_receipt_mutation_without_hash_update_is_rejected(self):
        left = self.evaluation(self.base / 'left', self.row)
        right = self.evaluation(self.base / 'right', self.row)
        (right / 'decisions-0.jsonl').write_text('{}\n')
        with self.assertRaises(AssertionError):
            collector.paired_parity(left, right)

    def test_collection_before_full_pilot_never_calls_hf(self):
        with patch.object(collector.launcher, 'PILOT', self.base / 'missing-pilot.json'), \
                patch.object(collector, 'HfApi') as api:
            with self.assertRaisesRegex(AssertionError, 'complete local 64-game / 16-replay'):
                collector.collect(2)
            api.assert_not_called()


if __name__ == '__main__':
    unittest.main()
