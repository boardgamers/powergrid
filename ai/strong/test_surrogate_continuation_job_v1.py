"""Actual saved records exercise the complete HF root-job envelope; no submissions."""
from copy import deepcopy
from fractions import Fraction
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from strategic_collection import ROOT, read, write, digest
from surrogate_continuation_study_v1 import code_hashes, policy_digest, PROTOCOL, MODES
import surrogate_continuation_job_v1 as job

BASE = ROOT/'ai/runs/surrogate-continuation-study-preflight-v1'


class JobTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = read(BASE/'plant-reference_opponent_v1-0-8/root.json')
        cls.policy = read(BASE/'plant-surrogate_opponent_v1-0-8/policy.json')
        cls.raw = {}; cls.intents = {}
        for mode in MODES:
            folders = sorted(BASE.glob(f'plant-{mode}-*'))
            parts = [read(p/'result.json') for p in folders]
            value = deepcopy(parts[0]); value.update(begin=0, count=8)
            value['rows'] = [row for part in parts for row in part['rows']]
            for i, row in enumerate(value['rows']): row['env'] = i
            value['seconds'] = sum(p['seconds'] for p in parts)
            value['inference_decisions'] = {role: sum(p['inference_decisions'][role] for p in parts) for role in ('neural', 'surrogate')}
            cls.raw[mode] = value
            cls.intents[mode] = {**read(folders[0]/'intent.json'), 'begin': 0, 'count': 8, 'workers': 8}

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.out = Path(self.temp.name)/'root-job'; self.calls = []; self.cap = False; self.fail = False
        self.focal = SimpleNamespace(sha256=read(PROTOCOL)['focal_model_sha256'])
        self.surrogate = SimpleNamespace(policy=self.policy)
        self.cpu = 0
        def times():
            self.cpu += 1
            return (float(self.cpu), 0., 0., 0., 0.)
        self.patches = [patch.object(job, 'run_chunk', side_effect=self.saved_chunk),
            patch.object(job.os, 'times', side_effect=times),
            patch.object(job.resources, 'MemorySampler', side_effect=lambda: SimpleNamespace(
                peak=100000000, samples=1, stop=SimpleNamespace(set=lambda: None),
                thread=SimpleNamespace(start=lambda: None, join=lambda: None)))]
        for p in self.patches: p.start(); self.addCleanup(p.stop)

    def saved_chunk(self, root, mode, begin, count, focal, surrogate, output, **kwargs):
        self.calls.append(mode); output.mkdir()
        intent = deepcopy(self.intents[mode]); intent['code_hashes'] = code_hashes()
        write(output/'intent.json', intent); write(output/'root.json', root)
        if self.fail and mode == 'reference_opponent_v1': raise RuntimeError('Preserve original failed execution')
        result = deepcopy(self.raw[mode])
        if self.cap and mode == 'reference_opponent_v1':
            row = result['rows'][0]
            row.update(truncated=True, value=None, steps=2400)
            row['diagnostic']['terminal'] = None
            row['policyDecisions'] = {key: 0 for key in row['policyDecisions']}; row['policyDecisions']['neural'] = 2400
            result.update(caps=1, outer_caps=1, nested_caps=0, usable=False)
            result['inference_decisions'] = {role: sum(r['policyDecisions'].get(role, 0) for r in result['rows']) for role in ('neural', 'surrogate')}
        if surrogate is not None: write(output/'policy.json', surrogate.policy)
        write(output/'result.json', result)
        status = {**intent, 'stage': 'complete' if result['usable'] else 'capped', 'caps': result['caps'],
                  'rows': 16, 'result_sha256': digest(output/'result.json')}
        write(output/'status.json', status); return status

    def execute(self):
        return job.execute_root(self.root, self.focal, self.surrogate, self.out,
                                scope='local_engineering_fixture', provenance={'fixture': True})

    def test_all_modes_complete_and_every_saved_record_reverified(self):
        result = self.execute()
        self.assertEqual(self.calls, list(MODES)); self.assertEqual(result['continuations'], 48)
        self.assertEqual(result['stage'], 'complete'); self.assertEqual(result['caps'], 0)
        audit = job.verify_root_job(self.out, self.root, policy_digest(self.policy)); self.assertTrue(audit['complete'])
        manifest = read(self.out/'manifest.json')
        self.assertNotIn('manifest.json', manifest)
        self.assertTrue(all(digest(self.out/name) == sha for name, sha in manifest.items()))

    def test_capped_mode_keeps_all_48_records_without_margin(self):
        self.cap = True; result = self.execute()
        self.assertEqual(self.calls, list(MODES)); self.assertEqual(result['stage'], 'capped')
        paired = read(self.out/'paired.json')
        self.assertEqual(paired['caps'], 1); self.assertIsNone(paired['margins'])
        self.assertEqual(sum(len(rows)*2 for rows in paired['mode_credits'].values()), 48)
        self.assertFalse(read(self.out/'audit.json')['complete'])

    def test_failed_execution_retained_and_existing_output_never_repeated(self):
        self.fail = True
        with self.assertRaises(RuntimeError): self.execute()
        self.assertEqual(read(self.out/'job.json')['stage'], 'failed')
        self.assertTrue((self.out/'manifest.json').exists())
        before = digest(self.out/'job.json')
        with self.assertRaises(FileExistsError): self.execute()
        self.assertEqual(digest(self.out/'job.json'), before); self.assertEqual(len(self.calls), 2)

    def test_resealed_bad_terminal_and_resource_accounting_rejected(self):
        self.execute(); mode = 'reference_opponent_v1'; folder = self.out/mode
        raw = read(folder/'result.json'); raw['rows'][0]['value'] = .123
        write(folder/'result.json', raw); status = read(folder/'status.json')
        status['result_sha256'] = digest(folder/'result.json'); write(folder/'status.json', status)
        state = read(self.out/'job.json'); state['modes'][mode]['status_sha256'] = digest(folder/'status.json')
        write(self.out/'job.json', state)
        with self.assertRaises(AssertionError): job.verify_root_job(self.out, self.root, policy_digest(self.policy))

    def test_shared_prior_work_matches_all_collected_reference_receipts(self):
        checked = prior = 0
        for path in (ROOT/'ai/runs/surrogate-continuation-cost-collected-v1').glob('*/artifacts/reference_opponent_v1/result.json'):
            raw = read(path); work = job.search_work(raw, 8); checked += 1
            row_count = sum(r['searchStats']['evaluations']+r['diagnostic']['priorSearchStats']['evaluations'] for r in raw['rows'])
            self.assertEqual(work['row_attributed_total']['evaluations'], row_count)
            self.assertEqual(work['physical_total']['evaluations'], row_count-work['prior_once_per_worker_world']['evaluations'])
            prior += work['prior_once_per_worker_world']['evaluations']
        self.assertGreaterEqual(checked, 22); self.assertGreater(prior, 0)

    def test_scope_and_focal_model_mismatch_refuse_before_execution(self):
        for kind in ('scope', 'model'):
            focal = self.focal if kind == 'scope' else SimpleNamespace(sha256='f'*64)
            with self.assertRaises(AssertionError):
                job.execute_root(self.root, focal, self.surrogate, self.out,
                                 scope='fresh_fidelity' if kind == 'scope' else 'local_engineering_fixture', provenance={})
        self.assertFalse(self.out.exists()); self.assertEqual(self.calls, [])

    def test_incomplete_input_bundle_refuses_before_hf_execution(self):
        with self.assertRaises(FileNotFoundError): job.validate_inputs(Path(self.temp.name)/'missing')
        self.assertEqual(self.calls, [])


if __name__ == '__main__': unittest.main()
