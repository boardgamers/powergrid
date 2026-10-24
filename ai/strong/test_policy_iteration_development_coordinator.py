"""Dispatch boundary checks only;no simulation, gradients or HF submissions."""
from copy import deepcopy
import importlib.util
import unittest
from strategic_collection import ROOT, read
from policy_iteration_development import PROTOCOL, contract

SPEC = importlib.util.spec_from_file_location('tested_development_coordinator',
                                           ROOT/'ai/strong/coordinate-policy-iteration-development.py')
coordinator = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(coordinator)


class DevelopmentCoordinatorContracts(unittest.TestCase):
    def handoffs(self):
        labels = {'stage': 'complete', 'qualification_eligible': False, 'labels_complete': True,
                  'label_shards_verified': 948, 'parent_reference_complete': True,
                  'parent_shards_verified': 108, 'parent_games_verified': 6720}
        training = {'stage': 'both_heads_verified_and_archived', 'qualification_eligible': False,
                    'remote_submissions_allowed': False, 'local_gradients': False,
                    'training_jobs': {'frozen': '1'*24, 'public': '2'*24}, 'heads_verified': {}}
        for head, job in training['training_jobs'].items():
            training['heads_verified'][head] = {'head_type': head, 'job_id': job,
                'remote_archive_verified': True, 'qualification_eligible': False,
                'candidate_pins': {head+'-0': {}, head+'-1': {}}}
        return labels, training

    def test_waits_for_both_complete_upstreams_without_partial_admission(self):
        labels, training = self.handoffs()
        self.assertTrue(coordinator.upstreams_ready(labels, training))
        for stage in coordinator.LABEL_WAIT:
            self.assertFalse(coordinator.upstreams_ready({**labels, 'stage': stage}, training))
        for stage in coordinator.TRAINING_WAIT:
            self.assertFalse(coordinator.upstreams_ready(labels, {**training, 'stage': stage}))
        for field, value in [('stage', 'stopped_with_error'), ('stage', 'window_ended'),
                             ('labels_complete', False), ('label_shards_verified', 947),
                             ('parent_reference_complete', False), ('parent_shards_verified', 107),
                             ('parent_games_verified', 6719), ('qualification_eligible', True)]:
            with self.subTest(field=field, value=value), self.assertRaises(AssertionError):
                coordinator.upstreams_ready({**labels, field: value}, training)
        for field, value in [('stage', 'stopped_with_error'), ('stage', 'wait_window_ended'),
                             ('heads_verified', {}), ('training_jobs', {'frozen': '1'*24, 'public': '1'*24}),
                             ('remote_submissions_allowed', True), ('local_gradients', True)]:
            with self.subTest(field=field), self.assertRaises(AssertionError):
                coordinator.upstreams_ready(labels, {**training, field: value})

    def test_all_four_exact_archived_candidates_required(self):
        labels, training = self.handoffs()
        for field, value in [('job_id', '3'*24), ('head_type', 'public'),
                             ('remote_archive_verified', False), ('qualification_eligible', True),
                             ('candidate_pins', {'frozen-0': {}})]:
            bad = deepcopy(training)
            bad['heads_verified']['frozen'][field] = value
            with self.subTest(field=field), self.assertRaises(AssertionError):
                coordinator.upstreams_ready(labels, bad)

    def test_probes_cover_both_endpoints_all_ensembles_and_separate_seeds(self):
        protocol = read(PROTOCOL)
        rows = coordinator.probe_rows()
        self.assertEqual(len(rows), 8)
        self.assertEqual(len({r['case'] for r in rows}), 8)
        self.assertEqual({(r['key'], r['players']) for r in rows},
                         {(key, n) for key in coordinator.KEYS for n in [2, 6]})
        games = 0
        for row in rows:
            screen, probe = contract(protocol, row['players'], row['opponent'], row['start'], row['end'], row['mode'])
            self.assertEqual(probe['seed_template'], protocol['smoke_seed_template'])
            self.assertNotEqual(probe['seed_template'], protocol['seed_template'])
            self.assertNotIn('reserved', probe['seed_template'])
            self.assertEqual(probe['deal_offsets'], [0])
            games += screen['games']
        self.assertEqual(games, 128)


if __name__ == '__main__':
    unittest.main()
