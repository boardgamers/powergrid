"""Synthetic schedule/cost/admission checks; no games or HF jobs are generated."""
from copy import deepcopy
import importlib.util
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('plan', Path(__file__).with_name('prepare-current-auction-grid-v1.py'))
plan = importlib.util.module_from_spec(spec); spec.loader.exec_module(plan)


def fixtures(p):
    rows = []; jobs = []
    for pilot in p['runtime_pilots']:
        arm, n = pilot['arm'], pilot['players']; name = f'{arm}-{n}'
        row = {'name': name, 'arm': arm, 'players': n, 'flavor': 'cpu-upgrade', 'identity': {'synthetic': arm},
               'shard': {'games': 4*n}}
        wall = (80 if n == 2 else 600) if arm == 'filter' else (1200 if n == 2 else 6000)
        audit = {'all_receipts_verified': True, 'expected': row['shard'], 'identity': row['identity'],
            'counts': {'rollout_caps': 0, 'rollouts': 0 if arm == 'filter' else 100, 'search_decisions': 0 if arm == 'filter' else 10},
            'terminals': [{'synthetic': True} for _ in range(4*n)], 'reserved_final_seeds_used': False}
        measurement = {'seconds': wall, 'cpu_seconds': 4*wall, 'sampled_peak_total_rss_bytes': 7*10**9,
            'memory_samples': 100, 'memory_sampling_period_seconds': .2, 'includes_startup_and_validation': True}
        rows.append(row); jobs.append({'job_id': format(len(jobs)+1, '024x'), 'row': row,
            'verified': True, 'stage': 'COMPLETED', 'evidence': {'remote_archive_verified': True},
            'review': {'games': 4*n, 'audit': audit, 'measurement': measurement}})
    source = {'rows': rows, 'protocol_sha256': plan.PROTOCOL_SHA, 'workers': 4}
    result = {'complete': True, 'verified_jobs': 4, 'jobs': jobs, 'source_sha256': 'synthetic-source'}
    return source, result


class PlanTests(unittest.TestCase):
    def setUp(self):
        self.p = plan.protocol(); self.source, self.result = fixtures(self.p)

    def sizing(self, result=None):
        return plan.resources(self.p, result or self.result, self.source, 'synthetic-source')

    def test_complete_paired_schedule_with_different_batch_sizes(self):
        sizing = self.sizing(); rows = plan.schedule(self.p, sizing)
        self.assertEqual(sum(r['shard']['games'] for r in rows), 26880)
        for arm in plan.ARMS:
            for s in self.p['screens']:
                n, o = s['players'], s['opponent']; deals = []
                for r in rows:
                    if r['arm'] != arm or r['shard']['group'] != f'{o}/{n}p': continue
                    x = r['shard']; deals.extend(range(x['start'], x['start']+x['deals']))
                    self.assertEqual(x['seed'], f'current-auction-confirmation-v1-{n}p')
                    self.assertNotIn('reserved', x['seed'])
                self.assertEqual(sorted(deals), list(range(32)))
        self.assertEqual(sizing['per_arm_count']['filter']['2']['deals_per_job'], 16)
        self.assertEqual(sizing['per_arm_count']['conservative_population']['2']['deals_per_job'], 2)
        self.assertEqual(sizing['per_arm_count']['conservative_population']['6']['timeout_hours'], 5)

    def test_missing_failed_capped_or_wrong_bound_pilot_refused(self):
        edits = [lambda r: r.update(complete=False), lambda r: r['jobs'].pop(),
            lambda r: r['jobs'][0].update(stage='ERROR'), lambda r: r['jobs'][0].update(verified=False),
            lambda r: r.update(source_sha256='wrong'), lambda r: r['jobs'][0]['review'].update(games=7),
            lambda r: r['jobs'][0]['review']['audit']['counts'].update(rollout_caps=1),
            lambda r: r['jobs'][2]['review']['audit']['counts'].update(rollouts=0),
            lambda r: r['jobs'][0]['review']['audit'].update(reserved_final_seeds_used=True)]
        for edit in edits:
            r = deepcopy(self.result); edit(r)
            with self.subTest(edit=edit), self.assertRaises(AssertionError): self.sizing(r)

    def test_nonfinite_cost_or_insufficient_memory_refused(self):
        for key, value in [('seconds', float('nan')), ('cpu_seconds', -1),
                           ('memory_samples', 0), ('sampled_peak_total_rss_bytes', 16*1024**3)]:
            r = deepcopy(self.result); r['jobs'][0]['review']['measurement'][key] = value
            with self.subTest(key=key), self.assertRaises(AssertionError): self.sizing(r)

    def test_cost_sizing_does_not_read_wins(self):
        r = deepcopy(self.result)
        for j in r['jobs']:
            for t in j['review']['audit']['terminals']: t['win'] = 'arbitrary-unread-synthetic-outcome'
        self.assertEqual(self.sizing(r), self.sizing())

    def test_invalid_chunk_sizes_refused(self):
        for value in (True, 0, 3, 64):
            sizing = self.sizing(); sizing['per_arm_count']['filter']['2']['deals_per_job'] = value
            with self.subTest(value=value), self.assertRaises(AssertionError): plan.schedule(self.p, sizing)

    def test_source_preparation_refuses_incomplete_pilots_without_writes(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / 'not-created'; manager = SimpleNamespace(RESULT=Path(tmp) / 'missing.json')
            with patch.object(plan, 'OUT', out), patch.object(plan, 'pilot_manager', return_value=manager):
                with self.assertRaisesRegex(AssertionError, 'Complete all four'): plan.prepare()
            self.assertFalse(out.exists())


if __name__ == '__main__': unittest.main()
