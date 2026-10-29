"""Recovery admission mutations; synthetic fixtures never count as strength."""
from collections import Counter
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import current_auction_final_selection_v2 as gate
import test_current_auction_final_selection_v1 as previous_tests


class UnchangedScientificGates(previous_tests.SelectionGateTests):
    def setUp(self):
        replacement = patch.object(previous_tests, 'gate', gate)
        replacement.start(); self.addCleanup(replacement.stop)
        super().setUp()

    def test_incomplete_owner_blocks_before_opening_any_outcomes(self):
        # Completion now means canonical coverage, not a stopped process flag.
        plan = {'slots': [{'name': 'missing', 'kind': 'recovery'}]}
        found = {'complete': False, 'missing': ['missing'], 'required': 1, 'available': []}
        with patch.object(gate.auth.coverage, 'actual_plan', return_value=plan), \
             patch.object(gate.auth, 'actual_routes', return_value={}), \
             patch.object(gate.auth, 'inventory', return_value=found), \
             patch.object(gate.comparison_tool, 'check_inputs') as inputs, \
             patch.object(gate, 'read') as outcomes, \
             patch.object(gate, 'check_technical') as technical:
            with self.assertRaisesRegex(ValueError, 'Incomplete recovery coverage'):
                gate.verify(gate.ROOT/'NO-SELECTION.json')
            for fn in (inputs, outcomes, technical): fn.assert_not_called()


class MixedProvenanceTests(unittest.TestCase):
    def setUp(self):
        self.plan = {'canonical_shards': 944, 'canonical_games': 26880,
            'game_keys_sha256': 'a'*64, 'shards_by_disposition': {'synthetic': 944},
            'original_failure_preserved': {'job_id': 'original-timeout', 'stage': 'ERROR'}, 'slots': []}
        self.cases = []; self.saved = {}; audits = {}; provenance = {}
        backends = ('original', 'timeout_v2', 'retained_v2', 'bucket_first_v3',
                    'bucket_remaining_v3', 'bucket_failed_v3')
        counts = {arm: Counter() for arm in gate.statistics.ARMS}
        for i in range(944):
            name = f'synthetic-{i:04d}'; backend = backends[i % len(backends)]
            arm = gate.statistics.ARMS[i % 2]; games = 29 if i < 448 else 28
            count = {'decisions': games, 'rollout_caps': 0}
            case = {'name': name, 'backend': backend, 'job_id': f'{i:024x}',
                'stage': 'ERROR' if backend == 'original' else 'COMPLETED', 'games': games,
                'receipt_file': f'ai/runs/synthetic/{name}.json', 'receipt_sha256': 'b'*64,
                'raw_review_sha256': 'c'*64, 'counts': count}
            history = [{'job_id': f'{i+1000:024x}', 'stage': 'ERROR'}] if backend == 'bucket_failed_v3' else []
            self.cases.append(case)
            self.saved[name] = {'review': {'audit': {'counts': count}}, 'prior_failed_attempts': history}
            self.plan['slots'].append({'name': name, 'arm': arm}); counts[arm].update(count)
            trees, evaluation = self.evidence(case, self.saved[name])
            audits[name] = {k: case[k] for k in ('name', 'backend', 'job_id', 'games', 'receipt_sha256', 'counts')}
            audits[name].update(original_hf_stage=case['stage'], review_sha256=case['raw_review_sha256'],
                raw_trees=trees, evaluation_file=evaluation, evaluation_sha256='e'*64)
            provenance[name] = {k: case[k] for k in ('backend', 'job_id', 'stage', 'receipt_file', 'receipt_sha256')}
            provenance[name]['prior_failed_attempts'] = history
        self.comparison = {'canonical_coverage': {'jobs': 944, 'games': 26880,
                'game_keys_sha256': self.plan['game_keys_sha256'],
                'shards_by_disposition': self.plan['shards_by_disposition']},
            'original_failure_preserved': deepcopy(self.plan['original_failure_preserved']),
            'parallel_raw_audit': {'workers': 4, 'all_reviews_exact': True,
                'readiness_sha256': gate.digest(gate.comparison_tool.READINESS), 'jobs': audits},
            'attempt_provenance': deepcopy(provenance),
            'costs': {arm: {'counts': dict(total)} for arm, total in counts.items()}}

    @staticmethod
    def evidence(case, saved):
        root = 'ai/runs/synthetic/'+case['name']
        return [{'directory': root, 'manifest_sha256': 'd'*64}], root+'/evaluation.json'

    def verify(self):
        with patch.object(gate, 'expected_evidence', side_effect=self.evidence):
            return gate.complete_provenance(self.comparison, self.plan, self.cases, self.saved)

    def test_all_six_backends_bound_before_normalizing_count(self):
        normalized = self.verify()
        self.assertEqual(normalized['parallel_raw_audit']['jobs'], 944)
        self.assertIsInstance(self.comparison['parallel_raw_audit']['jobs'], dict)
        self.assertIs(gate.confirmation_gate, gate.original.confirmation_gate)
        self.assertIs(gate.reviewed_selection, gate.original.reviewed_selection)
        self.assertIs(gate.technical_gate, gate.original.technical_gate)

    def test_missing_duplicate_or_mislabelled_raw_audit_rejected(self):
        original = deepcopy(self.comparison)
        for mutation in ('missing', 'duplicate', 'mislabelled'):
            self.comparison = deepcopy(original); jobs = self.comparison['parallel_raw_audit']['jobs']
            first, second = list(jobs)[:2]
            if mutation == 'missing': del jobs[first]
            elif mutation == 'duplicate': jobs[second] = deepcopy(jobs[first])
            else: jobs[first], jobs[second] = jobs[second], jobs[first]
            with self.subTest(mutation=mutation), self.assertRaises(ValueError): self.verify()

    def test_changed_job_backend_receipt_or_raw_review_rejected(self):
        original = deepcopy(self.comparison)
        for field, value in (('job_id', 'f'*24), ('backend', 'wrong'), ('receipt_sha256', 'f'*64),
                             ('review_sha256', 'f'*64), ('original_hf_stage', 'RUNNING')):
            self.comparison = deepcopy(original)
            self.comparison['parallel_raw_audit']['jobs'][self.cases[0]['name']][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError): self.verify()

    def test_failed_attempt_history_cannot_be_erased(self):
        name = next(c['name'] for c in self.cases if c['backend'] == 'bucket_failed_v3')
        self.comparison['attempt_provenance'][name]['prior_failed_attempts'] = []
        with self.assertRaisesRegex(ValueError, 'execution provenance'): self.verify()

    def test_original_timeout_cannot_be_erased(self):
        self.comparison['original_failure_preserved'] = {}
        with self.assertRaisesRegex(ValueError, 'Original timeout'): self.verify()

    def test_raw_evidence_substitution_rejected(self):
        original = deepcopy(self.comparison)
        for field, value in (('raw_trees', []), ('evaluation_file', 'ai/runs/other/evaluation.json')):
            self.comparison = deepcopy(original)
            self.comparison['parallel_raw_audit']['jobs'][self.cases[0]['name']][field] = value
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, 'different raw evidence'):
                self.verify()

    def test_cost_totals_must_match_original_reviews(self):
        self.comparison['costs'][gate.ARM]['counts']['decisions'] += 1
        with self.assertRaisesRegex(ValueError, 'search totals'): self.verify()

    def test_coverage_cannot_substitute_game_keys(self):
        self.comparison['canonical_coverage']['game_keys_sha256'] = 'f'*64
        with self.assertRaisesRegex(ValueError, 'Canonical coverage'): self.verify()

    def test_receipt_change_rejected_before_reading_raw_files(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); receipt = root/'receipt.json'; receipt.write_text('{}')
            case = {'name': 'one', 'receipt_file': 'receipt.json', 'receipt_sha256': gate.digest(receipt)}
            receipt.write_text('{"changed":true}')
            with patch.object(gate, 'ROOT', root), patch.object(gate.comparison_tool, 'tree_pin') as tree:
                with self.assertRaisesRegex(ValueError, 'receipt changed'):
                    gate.check_audited_files([case], {})
                tree.assert_not_called()


if __name__ == '__main__': unittest.main()
