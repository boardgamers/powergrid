"""Synthetic failure gates and exact frozen-grid coverage; no jobs or games."""
import copy
import unittest

from strategic_collection import ROOT, read, digest
from hybrid_timeout_partition_v1 import PLAN, PROTOCOL, partition, specification


class TimeoutPartitionTests(unittest.TestCase):
    def setUp(self):
        self.plan, self.protocol = read(PLAN), read(PROTOCOL)
        self.case = 'population-hybrid-development-v1-combined-6p-search_geo-0-4'
        path = ROOT / 'ai/runs/population-hybrid-development-launches-v1' / (self.case + '.json')
        self.original = read(path)
        # This is a fabricated timeout solely for negative/positive contract
        # tests. It is not a status observation or a real recovery admission.
        self.current = {'job_id': self.original['job_id'], 'authoritative_status': 'ERROR',
                        'message': 'Job timeout', 'guard_sha256': digest(path), 'plan_sha256': digest(PLAN)}
        self.review = {'coordinator': {'stage': 'stopped_with_error'}, 'coordinator_present': False,
                       'artifacts': [], 'failure_review': {
                           'reviewed': True, 'original_job_id': self.original['job_id'],
                           'original_guard_sha256': digest(path), 'terminal_status': 'ERROR',
                           'reason': 'timeout', 'failure_logs_preserved': True,
                           'remote_artifact_check': {'completed': True, 'files': []},
                           'selection_from_partial_results': False}}

    def call(self, current=None, review=None, original=None, canonical=None):
        return specification(self.plan, self.protocol, original or self.original,
                             canonical or self.original, current or self.current, **(review or self.review))

    def test_every_original_shard_retains_every_game_and_rule(self):
        original_episodes = set()
        child_episodes = set()
        count = 0
        for row in self.plan['shards']:
            key = (row['arm'], row['players'], row['opponent'])
            n = row['players']
            original_episodes.update((key, i) for i in range(row['start'] * 4 * n, row['end'] * 4 * n))
            children = partition(row, self.protocol)
            self.assertEqual(sum(c['row']['games'] for c in children), row['games'])
            for child in children:
                self.assertEqual(child['expected_config']['workers'], 8)
                self.assertEqual(child['expected_config']['search_workers'], 1)
                self.assertEqual(child['expected_config']['samples'], 8)
                for episode in child['episodes']:
                    self.assertNotIn((key, episode), child_episodes)
                    child_episodes.add((key, episode))
                count += 1
        self.assertEqual(original_episodes, child_episodes)
        self.assertEqual((len(child_episodes), count), (8400, 540))

    def test_synthetic_reviewed_failure_changes_only_partitioning(self):
        spec = self.call()
        self.assertEqual(spec['games'], 96)
        self.assertEqual(len(spec['children']), 4)
        self.assertEqual(spec['source'], self.original['source'])
        self.assertEqual(spec['bootstrap_sha256'], self.original['bootstrap_sha256'])
        self.assertEqual(spec['timeout_hours'], self.original['timeout_hours'])
        self.assertFalse(spec['launch_implemented'])

    def test_live_unknown_completed_and_unrelated_errors_rejected(self):
        for stage in ['RUNNING', 'SCHEDULING', 'COMPLETED', 'CANCELED', 'UNKNOWN', None]:
            with self.subTest(stage=stage), self.assertRaises(AssertionError):
                self.call(current={**self.current, 'authoritative_status': stage})
        for message in ['network failure', 'CPU utilization low', 'slow progress', '']:
            with self.subTest(message=message), self.assertRaises(AssertionError):
                self.call(current={**self.current, 'message': message})

    def test_coordinator_artifacts_and_missing_review_block_specification(self):
        for key, value in [('coordinator_present', True), ('coordinator', {'stage': 'waiting_for_jobs'}),
                           ('artifacts', ['manifest.json']), ('failure_review', None)]:
            with self.subTest(key=key), self.assertRaises(AssertionError):
                self.call(review={**self.review, key: value})
        for key, value in [('reviewed', False), ('failure_logs_preserved', False),
                           ('selection_from_partial_results', True),
                           ('remote_artifact_check', {'completed': False, 'files': []}),
                           ('remote_artifact_check', {'completed': True, 'files': ['complete.tgz']})]:
            changed = copy.deepcopy(self.review)
            changed['failure_review'][key] = value
            with self.subTest(key=key), self.assertRaises(AssertionError):
                self.call(review=changed)

    def test_changed_guard_source_and_repeat_replacement_rejected(self):
        changed = {**self.original, 'job_id': 'another-job'}
        with self.assertRaises(AssertionError):
            self.call(canonical=changed)
        changed = {**self.original, 'source': {'sha256': 'different'}}
        with self.assertRaises(AssertionError):
            self.call(original=changed, canonical=changed)
        changed = {**self.original, 'replaces_job_id': 'earlier-job'}
        with self.assertRaises(AssertionError):
            self.call(original=changed, canonical=changed)

    def test_changed_protocol_or_plan_rejected(self):
        changed = copy.deepcopy(self.protocol)
        changed['search']['samples'] = 4
        with self.assertRaises(AssertionError):
            specification(self.plan, changed, self.original, self.original, self.current, **self.review)
        changed = copy.deepcopy(self.plan)
        changed['admission']['workers'] = 4
        with self.assertRaises(AssertionError):
            specification(changed, self.protocol, self.original, self.original, self.current, **self.review)


if __name__ == '__main__':
    unittest.main()
