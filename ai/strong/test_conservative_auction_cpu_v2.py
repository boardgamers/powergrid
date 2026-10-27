"""Saved-position selection and one-shot target admission; no game generation."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import conservative_auction_cpu_v2 as cpu

spec = importlib.util.spec_from_file_location('cpu_manager', Path(__file__).with_name('benchmark-conservative-auction-8840u-v2.py'))
manager = importlib.util.module_from_spec(spec); spec.loader.exec_module(manager)


def fixture_pool():
    return [{'request': {'player': 0, 'requestId': str(i), 'revision': 1,
        'state': {'seed': 'secret', 'powerPlantsDeck': [], 'players': [{'bid': 0, 'money': 50} for _ in range(n)],
            'options': {'variant': variant, 'fastBid': sealed, 'showMoney': True}}},
        'legal': [{'name': move}, {'name': 'Pass'}]}
        for i, (n, variant, sealed, move) in enumerate((n, v, s, m) for n in range(2, 7)
            for v in ('original', 'recharged') for s in (False, True) for m in cpu.STAGES.values())]


class CPUBenchmarkTests(unittest.TestCase):
    def select(self, rows):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)/'fixtures.jsonl'; p.write_text(''.join(json.dumps(r)+'\n' for r in rows))
            with patch.object(cpu, 'FIXTURES_SHA', cpu.digest(p)):
                return cpu.select_fixtures(p)

    def test_all_counts_rules_stages_and_first_nonforced_choice(self):
        rows = fixture_pool(); forced = deepcopy(rows[0]); forced['legal'] = forced['legal'][:1]
        selected = self.select([forced, *rows, deepcopy(rows[0])])
        self.assertEqual(len(selected), 100)
        self.assertEqual(len({r['name'] for r in selected}), 100)
        self.assertEqual({n: sum(r['players'] == n for r in selected) for n in range(2, 7)}, {n: 20 for n in range(2, 7)})
        self.assertEqual(min(r['source_ordinal'] for r in selected), 1)
        self.assertEqual(max(r['source_ordinal'] for r in selected), 100)
        self.assertTrue(all(r['fixture']['request']['state']['players'][0]['money'] == 50 for r in selected))
        self.assertEqual(selected, self.select([forced, *rows, deepcopy(rows[0])]))

    def test_missing_rule_or_stage_rejected(self):
        with self.assertRaisesRegex(AssertionError, 'Incomplete'): self.select(fixture_pool()[:-1])

    def test_hidden_bid_or_deck_rejected(self):
        for kind in ('bid', 'deck'):
            rows = fixture_pool()
            if kind == 'bid':
                row = next(r for r in rows if r['request']['state']['options']['fastBid'])
                row['request']['state']['players'][1]['bid'] = 4
            else: rows[0]['request']['state']['powerPlantsDeck'] = [10]
            state = row['request']['state'] if kind == 'bid' else rows[0]['request']['state']
            with self.subTest(kind=kind), self.assertRaises(AssertionError): cpu.assert_public_state(state)

    def test_changed_fixture_pool_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)/'fixtures.jsonl'; p.write_text('{}\n')
            with self.assertRaisesRegex(AssertionError, 'pool changed'): cpu.select_fixtures(p)

    def test_target_cannot_start_before_complete_local_reference(self):
        with patch.object(manager, 'checked', return_value={}), patch.object(manager, 'read', return_value={'stage': 'running'}), patch.object(manager.subprocess, 'run') as run:
            with self.assertRaises(AssertionError): manager.launch()
            run.assert_not_called()

    def test_existing_target_guard_prevents_duplicate_execution(self):
        with tempfile.TemporaryDirectory() as tmp:
            guard = Path(tmp)/'guard.json'; guard.write_text('{"stage":"launch_unknown"}')
            reference = {'stage': 'completed', 'passed': True, 'completed_requests': 300,
                         'manifest_sha256': 'a'*64, 'output_hashes': {}}
            with patch.object(manager, 'GUARD', guard), patch.object(manager, 'checked', return_value={'manifest_sha256': 'a'*64}), patch.object(manager, 'read', return_value=reference), patch.object(manager.subprocess, 'run') as run:
                with self.assertRaisesRegex(AssertionError, 'never duplicate'): manager.launch()
                run.assert_not_called()
            self.assertEqual(json.loads(guard.read_text())['stage'], 'launch_unknown')


if __name__ == '__main__': unittest.main()
