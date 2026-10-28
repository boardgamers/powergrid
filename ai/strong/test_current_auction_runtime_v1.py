"""Submission boundaries: no duplicate/unknown retry or reserved-seed launch."""
from copy import deepcopy
import fcntl
import importlib.util
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest

spec = importlib.util.spec_from_file_location('current_runtime', Path(__file__).with_name('manage-current-auction-runtime-v1.py'))
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)


class FakeAPI:
    def __init__(self, fail=False): self.calls = []; self.fail = fail
    def run_job(self, **kwargs):
        self.calls.append(kwargs)
        if self.fail: raise TimeoutError('unknown submission outcome')
        return SimpleNamespace(id='a'*24)


class LaunchBoundaries(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name) / 'job'
        self.row = {'name': 'pg-current-auction-runtime-v1-pop-6p', 'arm': 'conservative_population',
            'players': 6, 'job': 'runtime-controls/test.job.json', 'flavor': 'cpu-upgrade', 'timeout': '5h',
            'shard': {'seed': 'current-auction-runtime-v1-6p', 'start': 0, 'deals': 1, 'games': 24}}
        self.source = {'rows': [self.row], 'archive': 'test.tgz', 'revision': 'b'*40, 'sha256': 'c'*64,
            'source_manifest_sha256': 'd'*64, 'protocol_sha256': 'e'*64}

    def test_same_guard_never_submits_twice(self):
        api = FakeAPI()
        first = m.launch_once(api, self.folder, self.source, self.row, 'fake-secret')
        second = m.launch_once(api, self.folder, self.source, self.row, 'fake-secret')
        self.assertEqual(first, second); self.assertEqual(len(api.calls), 1)
        self.assertNotIn('fake-secret', (self.folder / 'launch.json').read_text())
        self.assertEqual(api.calls[0]['env']['PILOT_NAME'], self.row['name'])
        self.assertEqual(api.calls[0]['timeout'], '5h')

    def test_unknown_outcome_is_preserved_and_not_retried(self):
        api = FakeAPI(fail=True)
        with self.assertRaises(TimeoutError): m.launch_once(api, self.folder, self.source, self.row, 'fake-secret')
        original = (self.folder / 'launch.json').read_bytes()
        self.assertEqual(json.loads(original)['stage'], 'launch_unknown')
        with self.assertRaises(AssertionError): m.launch_once(api, self.folder, self.source, self.row, 'fake-secret')
        self.assertEqual(len(api.calls), 1); self.assertEqual((self.folder / 'launch.json').read_bytes(), original)

    def test_reserved_or_development_seed_is_rejected(self):
        for seed in ('strong-multiplayer-final-reserved-v1-6p', 'current-auction-confirmation-v1-6p'):
            row = deepcopy(self.row); row['shard']['seed'] = seed
            source = {**self.source, 'rows': [row]}; api = FakeAPI()
            with self.assertRaises(AssertionError): m.launch_once(api, self.folder, source, row, 'fake-secret')
            self.assertFalse(api.calls); self.assertFalse(self.folder.exists())

    def test_changed_or_expanded_shard_is_rejected(self):
        for change in ({'games': 48}, {'deals': 2}, {'start': 1}):
            row = deepcopy(self.row); row['shard'].update(change); api = FakeAPI()
            with self.assertRaises(AssertionError): m.launch_once(api, self.folder, self.source, row, 'fake-secret')
            with self.assertRaises(AssertionError): m.launch_once(api, self.folder, {**self.source, 'rows': [row]}, row, 'fake-secret')
            self.assertFalse(api.calls)

    def test_exclusive_launch_lock(self):
        self.folder.mkdir()
        with (self.folder / '.launch.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB); api = FakeAPI()
            with self.assertRaises(BlockingIOError): m.launch_once(api, self.folder, self.source, self.row, 'fake-secret')
            self.assertFalse(api.calls); self.assertFalse((self.folder / 'launch.json').exists())


if __name__ == '__main__': unittest.main()
