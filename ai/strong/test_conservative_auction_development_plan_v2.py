"""Check paired coverage and reject incomplete/capped runtime admission."""
from copy import deepcopy
import importlib.util
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('development_plan', Path(__file__).with_name('prepare-conservative-auction-development-v2.py'))
plan = importlib.util.module_from_spec(spec); spec.loader.exec_module(plan)


class DevelopmentPlanTests(unittest.TestCase):
    def setUp(self):
        self.p = plan.protocol()
        self.source = plan.read(Path(__file__).with_name('conservative-auction-runtime-source-v2.json'))
        jobs = []
        # Synthetic measurements exercise admission only; never saved as evidence.
        for row in self.source['rows']:
            games = row['shard']['games']
            jobs.append({'row': row, 'verified': True, 'stage': 'COMPLETED', 'job_id': row['name'],
                'evidence': {'remote_archive_verified': True}, 'review': {'games': games,
                'audit': {'all_receipts_verified': True, 'expected': row['shard'], 'identity': row['identity'],
                    'reserved_final_seeds_used': False, 'counts': {'rollout_caps': 0, 'rollouts': 8, 'search_decisions': 1},
                    'terminals': [{'synthetic': True} for _ in range(games)]},
                'measurement': {'seconds': games*40., 'cpu_seconds': games*240.,
                    'sampled_peak_total_rss_bytes': 3*1024**3, 'memory_samples': 100,
                    'memory_sampling_period_seconds': .2, 'includes_startup_and_validation': True}}})
        self.result = {'complete': True, 'verified_jobs': 4, 'jobs': jobs, 'source_sha256': 'a'*64}

    def size(self, result=None):
        return plan.resources(self.p, result or self.result, self.source, 'a'*64)

    def test_every_batch_size_covers_exact_same_10080_paired_games(self):
        expected = {(arm, s['opponent'], s['players'], deal, rule, seat)
                    for arm in self.p['arms'] for s in self.p['screens'] for deal in range(8)
                    for rule in range(4) for seat in range(s['players'])}
        self.assertEqual(len(expected), 10080)
        for batch in (1, 2, 4, 8):
            with self.subTest(batch=batch):
                seen = set()
                for row in plan.schedule(self.p, batch):
                    s = row['shard']; self.assertEqual(s['seed'], f"conservative-auction-development-v1-{s['players']}p")
                    self.assertEqual(row['opponent_model'] is not None, s['opponent'] == 'a260')
                    for deal in range(s['start'], s['start']+s['deals']):
                        for rule in range(4):
                            for seat in range(s['players']):
                                key = row['arm'], s['opponent'], s['players'], deal, rule, seat
                                self.assertNotIn(key, seen); seen.add(key)
                self.assertEqual(seen, expected)

    def test_partial_capped_duplicate_or_wrong_source_results_rejected(self):
        variants = []
        r = deepcopy(self.result); r['complete'] = False; variants.append(r)
        r = deepcopy(self.result); r['jobs'].pop(); variants.append(r)
        r = deepcopy(self.result); r['source_sha256'] = 'b'*64; variants.append(r)
        r = deepcopy(self.result); r['jobs'][0]['review']['audit']['counts']['rollout_caps'] = 1; variants.append(r)
        r = deepcopy(self.result); r['jobs'][0]['stage'] = 'RUNNING'; variants.append(r)
        r = deepcopy(self.result); r['jobs'][1] = deepcopy(r['jobs'][0]); variants.append(r)
        for r in variants:
            with self.subTest(result=r['complete']), self.assertRaises(AssertionError): self.size(r)

    def test_outcomes_do_not_affect_resource_selection(self):
        first = self.size(); r = deepcopy(self.result)
        for job in r['jobs']:
            for terminal in job['review']['audit']['terminals']:
                terminal.update(win_credit=1, synthetic_opponent_score=999999)
        self.assertEqual(self.size(r), first)
        self.assertEqual(first['workers'], 4)

    def test_slow_runtime_shrinks_batches_and_insufficient_memory_is_rejected(self):
        original = self.size(); r = deepcopy(self.result)
        for job in r['jobs']: job['review']['measurement']['seconds'] *= 4
        slower = self.size(r)
        self.assertLess(slower['deals_per_job'], original['deals_per_job'])
        r['jobs'][0]['review']['measurement']['sampled_peak_total_rss_bytes'] = 15*1024**3
        with self.assertRaisesRegex(AssertionError, 'hardware admission'): self.size(r)

    def test_source_preparation_cannot_start_with_missing_pilot_results(self):
        with tempfile.TemporaryDirectory() as tmp:
            manager = SimpleNamespace(RESULT=Path(tmp)/'missing.json')
            with patch.object(plan, 'pilot_manager', return_value=manager), patch.object(plan.shutil, 'copytree') as copy:
                with self.assertRaisesRegex(AssertionError, 'complete original pilot'): plan.prepare()
                copy.assert_not_called()


if __name__ == '__main__': unittest.main()
