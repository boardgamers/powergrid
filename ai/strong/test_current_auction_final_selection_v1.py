"""Synthetic confirmation gates and mutations of existing technical proofs.

No games, policy inference, actual selection, reserved seeds or HF calls.
"""
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import current_auction_final_selection_v1 as gate


class SelectionGateTests(unittest.TestCase):
    def setUp(self):
        self.t, self.b, self.e, self.a = [gate.read(gate.ROOT / p) for p in
            (gate.TECHNICAL, gate.BINDING, gate.EXPORT, gate.EXPORT_AUDIT)]
        self.hashes = {p: gate.digest(gate.ROOT / p) for p in
            (gate.TECHNICAL, gate.BINDING, gate.EXPORT, gate.EXPORT_AUDIT)}
        self.ids = deepcopy(self.t['identities'])
        p = gate.statistics.protocol(); absolute = {}; contrasts = {}; directions = {'negative': [], 'positive': [], 'zero': []}
        for screen in p['screens']:
            cell = f"{screen['opponent']}/{screen['players']}p"; absolute[cell] = {}; contrasts[cell] = {}
            for rule in ('overall', *gate.statistics.RULES):
                negative = cell == 'economic/2p' and rule == 'overall'
                delta = '-1/100' if negative else '1/10'
                absolute[cell][rule] = {'win_credit': {'exact_mean': '1', 'paired_whole_deal_95_interval': [.75, 1.]}}
                contrasts[cell][rule] = {'win_credit_difference': {'exact_mean': delta}}
                directions['negative' if negative else 'positive'].append(
                    {'cell': cell, 'rules': rule, 'difference': -.01 if negative else .1})
        self.c = {'complete': True, 'games': 26880, 'games_per_arm': 13440, 'cells_per_arm': 27,
            'independent_deals_per_count': 32, 'candidate_selected': False, 'qualification_eligible': False,
            'reserved_final_seeds_used': False, 'protocol_sha256': gate.statistics.PROTOCOL_SHA,
            'identities': deepcopy(self.ids), 'raw_receipts_reaudited': True,
            'parallel_raw_audit': {'all_reviews_exact': True, 'jobs': 944},
            'uncertainty': {'replicates': 10000, 'seed': 281028}, 'absolute': {gate.ARM: absolute},
            'contrasts': {gate.CONTRAST: contrasts}, 'all_cell_directions': {gate.CONTRAST: directions},
            'search_equal_count': {gate.CONTRAST: {'paired_whole_deal_95_interval': [.05, .15]}},
            'costs': {arm: {'counts': {'rollout_caps': 0, 'search_decisions': 10, 'rollouts': 80}} for arm in gate.statistics.ARMS},
            'created_at': '2026-10-29T01:00:00+00:00'}
        self.c['confirmation_requirements_review'] = gate.statistics.confirmation_requirements(self.c, gate.protocol())
        self.review = {'version': 1, 'created_at': '2026-10-29T02:00:00+00:00',
            'decision': 'propose_conservative_population_for_reserved_evaluation', 'comparison_sha256': 'a'*64,
            'identity': deepcopy(self.ids[gate.ARM]), 'adverse_cells': [{**directions['negative'][0], 'assessment': 'Synthetic assessment only; no actual research decision.'}],
            'rationale': 'Synthetic gate fixture only.', 'limitations': ['Held-out strength remains unproved.'],
            'qualified': False, 'reserved_final_seeds_used': False}

    def confirm(self): return gate.confirmation_gate(self.c, self.ids)

    def technical(self): return gate.technical_gate(self.t, self.b, self.e, self.a, self.hashes, self.ids)

    def review_selection(self):
        gate.reviewed_selection(self.review, self.c, 'a'*64, self.ids[gate.ARM], self.confirm())

    def test_positive_synthetic_gate_and_explicit_adverse_review(self):
        self.assertEqual(len(self.confirm()), 1); self.review_selection(); self.technical()

    def test_incomplete_or_not_independently_audited_grid_rejected(self):
        original = deepcopy(self.c)
        for key, value in (('complete', False), ('games', 26879), ('games_per_arm', 13439),
                           ('cells_per_arm', 26), ('independent_deals_per_count', 31), ('raw_receipts_reaudited', False)):
            self.c = deepcopy(original); self.c[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError): self.confirm()

    def test_recomputes_primary_instead_of_trusting_saved_pass(self):
        self.c['search_equal_count'][gate.CONTRAST]['paired_whole_deal_95_interval'][0] = 0
        with self.assertRaisesRegex(ValueError, 'checks differ'): self.confirm()
        self.c['confirmation_requirements_review'] = gate.statistics.confirmation_requirements(self.c, gate.protocol())
        with self.assertRaisesRegex(ValueError, 'requirements failed'): self.confirm()

    def test_rejects_chance_lower_bound_and_low_absolute_floor(self):
        views = self.c['absolute'][gate.ARM]['search_geo/2p']
        for metric in ({'exact_mean': '1', 'paired_whole_deal_95_interval': [.5, 1.]},
                       {'exact_mean': '0', 'paired_whole_deal_95_interval': [.75, 1.]}):
            views['overall']['win_credit'] = metric
            self.c['confirmation_requirements_review'] = gate.statistics.confirmation_requirements(self.c, gate.protocol())
            with self.assertRaisesRegex(ValueError, 'requirements failed'): self.confirm()

    def test_changed_search_recipe_rejected(self):
        self.c['identities'][gate.ARM]['settings']['samples'] = 16
        with self.assertRaisesRegex(ValueError, 'policy identity'): self.confirm()

    def test_regression_inventory_cannot_drop_negative_view(self):
        self.c['all_cell_directions'][gate.CONTRAST]['negative'] = []
        with self.assertRaisesRegex(ValueError, 'Regression inventory'): self.confirm()

    def test_adverse_review_cannot_omit_change_duplicate_or_hide_regression(self):
        original = deepcopy(self.review)
        for entries in ([], original['adverse_cells']*2,
                        [{**original['adverse_cells'][0], 'difference': 0}],
                        [{**original['adverse_cells'][0], 'assessment': ''}]):
            self.review = deepcopy(original); self.review['adverse_cells'] = entries
            with self.subTest(entries=entries), self.assertRaises(ValueError): self.review_selection()

    def test_review_must_follow_and_bind_complete_results(self):
        original = deepcopy(self.review)
        for key, value in (('created_at', '2026-10-28T01:00:00+00:00'), ('comparison_sha256', 'b'*64),
                           ('qualified', True), ('reserved_final_seeds_used', True), ('limitations', [])):
            self.review = deepcopy(original); self.review[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError): self.review_selection()

    def test_incomplete_owner_blocks_before_opening_any_outcomes(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); owner = root / gate.OWNER
            with patch.object(gate, 'read', return_value={'stage': 'waiting_for_original_confirmation_jobs'}) as reader:
                with self.assertRaisesRegex(ValueError, 'Wait for all original'): gate.verify(root/'absent-review.json', root)
            reader.assert_called_once_with(owner)

    def test_actual_technical_proof_rejects_missing_target_positions(self):
        self.t['requests'] = 320
        with self.assertRaisesRegex(ValueError, 'Incomplete full target'): self.technical()

    def test_actual_technical_proof_rejects_wrong_native_or_binding(self):
        self.b['checkpoint_sha256'] = 'b'*64
        with self.assertRaisesRegex(ValueError, 'Wrong native'): self.technical()
        self.b['checkpoint_sha256'] = self.e['checkpoint_sha256']; self.b['technical_report_sha256'] = 'c'*64
        with self.assertRaisesRegex(ValueError, 'proof hashes'): self.technical()

    def test_actual_target_requires_search_and_exact_coverage(self):
        original = deepcopy(self.t)
        self.t['counts'][gate.ARM]['rollouts'] = 0
        with self.assertRaisesRegex(ValueError, 'did not exercise'): self.technical()
        self.t = deepcopy(original); views = self.t['warm_timings_by_count_rule_phase'][gate.ARM]
        views['7p/original/open/Auction'] = views.pop('6p/original/open/Auction')
        with self.assertRaisesRegex(ValueError, 'timing coverage'): self.technical()

    def test_frozen_input_change_or_path_escape_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); p=root/'proof';p.write_text('original');pins={'proof':gate.digest(p)}
            gate.pinned_files(root,pins);p.write_text('changed')
            with self.assertRaisesRegex(ValueError, 'Changed evidence'): gate.pinned_files(root,pins)
            with self.assertRaisesRegex(ValueError, 'Changed evidence'): gate.pinned_files(root,{str(p):gate.digest(p)})


if __name__ == '__main__': unittest.main()
