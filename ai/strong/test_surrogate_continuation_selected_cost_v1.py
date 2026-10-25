"""Selected-surrogate timing envelope and preparation gates; no real submissions."""
from copy import deepcopy
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

from strategic_collection import ROOT, read, write, digest
from surrogate_continuation_study_v1 import policy_digest
import surrogate_continuation_selected_cost_v1 as cost
import test_surrogate_continuation_job_v1 as fixtures

spec = importlib.util.spec_from_file_location('study_packaging_test', ROOT/'ai/strong/build-surrogate-continuation-study-source-v1.py')
builder = importlib.util.module_from_spec(spec); spec.loader.exec_module(builder)


class SelectedCostTests(unittest.TestCase):
    def setUp(self):
        # Reuse saved-record scaffolding, not another execution or training model.
        fixtures.JobTests.setUpClass()
        self.fixture = fixtures.JobTests(); self.fixture.setUp(); self.addCleanup(self.fixture.doCleanups)
        self.fixture.raw = deepcopy(self.fixture.raw)
        self.root = self.fixture.root; self.out = self.fixture.out
        self.roots = {'2p-0-plant': self.root}
        p = patch.object(cost, 'run_chunk', side_effect=self.fixture.saved_chunk)
        p.start(); self.addCleanup(p.stop)

    def execute(self, roots=None, scope='local_engineering_fixture'):
        return cost.execute(roots or self.roots, self.fixture.focal, self.fixture.surrogate, self.out,
                            scope=scope, provenance={'fixture': True})

    def test_complete_saved_record_envelope_and_independent_recheck(self):
        state = self.execute()
        self.assertEqual(state['stage'], 'complete'); self.assertEqual(state['continuations'], 16)
        self.assertEqual(self.fixture.calls, [cost.MODE])
        result = cost.verify(self.out, self.roots, policy_digest(self.fixture.policy))
        self.assertTrue(result['complete']); self.assertFalse(result['full_study_admitted'])
        self.assertTrue(all(digest(self.out/name) == sha for name, sha in read(self.out/'manifest.json').items()))

    def test_cap_does_not_drop_other_runtime_roots(self):
        raw = self.fixture.raw[cost.MODE]; row = raw['rows'][0]
        row.update(truncated=True, value=None, steps=2400); row['diagnostic']['terminal'] = None
        row['policyDecisions'] = {key: 0 for key in row['policyDecisions']}; row['policyDecisions']['neural'] = 2400
        raw.update(caps=1, outer_caps=1, nested_caps=0, usable=False)
        raw['inference_decisions'] = {role: sum(r['policyDecisions'].get(role, 0) for r in raw['rows']) for role in ('neural', 'surrogate')}
        state = self.execute({'fixture-a': self.root, 'fixture-b': self.root})
        self.assertEqual(state['stage'], 'capped'); self.assertEqual(state['continuations'], 32); self.assertEqual(state['caps'], 2)
        self.assertEqual(len(state['measurements']), 2); self.assertEqual(len(self.fixture.calls), 2)
        self.assertFalse(read(self.out/'audit.json')['complete'])

    def test_failed_output_is_preserved_and_never_repeated(self):
        def fail(root, mode, begin, count, focal, surrogate, output, **kwargs):
            output.mkdir(); write(output/'partial.json', {'original': True})
            raise RuntimeError('Original fixture failure')
        with patch.object(cost, 'run_chunk', side_effect=fail):
            with self.assertRaises(RuntimeError): self.execute()
        self.assertEqual(read(self.out/'job.json')['stage'], 'failed'); before = digest(self.out/'job.json')
        with self.assertRaises(FileExistsError): self.execute()
        self.assertEqual(before, digest(self.out/'job.json'))
        self.assertTrue((self.out/'2p-0-plant/partial.json').exists())

    def test_nonfinite_timing_and_wrong_policy_pin_are_rejected(self):
        self.execute(); state = read(self.out/'job.json')
        with self.assertRaises(AssertionError): cost.verify(self.out, self.roots, 'f'*64)
        state['measurements']['2p-0-plant']['seconds'] = float('nan'); write(self.out/'job.json', state)
        with self.assertRaises(AssertionError): cost.verify(self.out, self.roots, policy_digest(self.fixture.policy))

    def test_full_calibration_requires_all_24_runtime_roots(self):
        with self.assertRaises(AssertionError): self.execute(scope='selected_runtime_calibration')
        self.assertFalse(self.out.exists()); self.assertEqual(self.fixture.calls, [])

    def test_fresh_scientific_root_cannot_be_used_for_runtime_selection(self):
        root = deepcopy(self.root); root['identity']['mode'] = 'root'
        with self.assertRaises(AssertionError): self.execute({'wrong': root})
        self.assertFalse(self.out.exists())

    def test_source_prepare_requires_actual_frozen_training_before_output(self):
        missing = Path(self.fixture.temp.name)/'unfrozen'; prep = Path(self.fixture.temp.name)/'source'
        with patch.object(builder, 'FROZEN', missing), patch.object(builder, 'PREP', prep), patch.object(builder, 'HfApi') as api:
            with self.assertRaisesRegex(AssertionError, 'actual audited training'): builder.prepare()
            api.assert_not_called()
        self.assertFalse(prep.exists())


if __name__ == '__main__': unittest.main()
