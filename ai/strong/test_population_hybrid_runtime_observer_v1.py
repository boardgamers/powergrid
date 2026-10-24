import importlib.util
import json
from pathlib import Path
import unittest

from strategic_collection import ROOT, read

spec = importlib.util.spec_from_file_location('runtime_observer_test', Path(__file__).with_name('inspect-population-hybrid-runtime-v1.py'))
observer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(observer)


class RuntimeObserverTests(unittest.TestCase):
    def setUp(self):
        self.failure = ROOT / 'ai/runs/population-hybrid-auction5p-failure-v1'
        self.row = read(self.failure / 'original-guard.json')['row']

    def test_actual_failure_log_preserves_79_completions_and_storage_error(self):
        progress, errors = observer.parse_game_events((self.failure / 'job.log').read_text().splitlines(), self.row)
        self.assertEqual(len(progress), 79)
        self.assertEqual(max(p['completed'] for p in progress), 79)
        self.assertEqual({p['episode'] for p in progress}, set(range(80)) - {36})
        self.assertEqual(errors, [{'episode': 36, 'error': 'OSError: [Errno 28] No space left on device'}])

    def test_error_is_visible_before_job_completion(self):
        error = {'episode': 36, 'error': 'OSError: [Errno 28] No space left on device'}
        progress, errors = observer.parse_game_events([json.dumps(error)], self.row)
        self.assertEqual(progress, [])
        self.assertEqual(errors, [error])
        self.assertNotIn('authoritative_status', errors[0])

    def test_non_events_ignored_and_missing_error_is_not_inferred(self):
        progress, errors = observer.parse_game_events(['No logs available', '[]', 'null', 'bad JSON',
            json.dumps({'error': 'setup message without game provenance'}),
            json.dumps({'episode': 0, 'something': 'unrelated'})], self.row)
        self.assertEqual((progress, errors), ([], []))

    def test_wrong_episode_range_or_error_shape_rejected(self):
        for episode in [-1, 80, '36', True]:
            with self.subTest(episode=episode), self.assertRaises(AssertionError):
                observer.parse_game_events([json.dumps({'episode': episode, 'error': 'failure'})], self.row)
        for value in ['', None, 12]:
            with self.subTest(error=value), self.assertRaises(AssertionError):
                observer.parse_game_events([json.dumps({'episode': 36, 'error': value})], self.row)
        shifted = {**self.row, 'start': 1, 'end': 2, 'games': 20}
        with self.assertRaises(AssertionError):
            observer.parse_game_events([json.dumps({'episode': 0, 'error': 'failure'})], shifted)
        self.assertEqual(observer.parse_game_events([json.dumps({'episode': 36, 'error': 'failure'})], shifted)[1],
                         [{'episode': 36, 'error': 'failure'}])


if __name__ == '__main__':
    unittest.main()
