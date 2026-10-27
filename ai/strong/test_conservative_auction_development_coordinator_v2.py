"""Admission failure must stop new compute; completion must not launch again."""
import importlib.util
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

spec = importlib.util.spec_from_file_location('development_coordinator', Path(__file__).with_name('coordinate-conservative-auction-development-v2.py'))
owner = importlib.util.module_from_spec(spec); spec.loader.exec_module(owner)


class CoordinatorTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.manager = SimpleNamespace(OUT=Path(self.tmp.name), collect=Mock(), launch=Mock())
        self.pins = patch.object(owner, 'check_pins'); self.pins.start(); self.addCleanup(self.pins.stop)
        self.write = patch.object(owner, 'write_state'); self.write.start(); self.addCleanup(self.write.stop)

    def test_invalid_original_receipt_prevents_next_launch(self):
        self.manager.collect.side_effect = ValueError('Invalid original evidence')
        with self.assertRaisesRegex(ValueError, 'original evidence'):
            owner.development_tick(self.manager, {})
        self.manager.launch.assert_not_called()

    def test_completed_comparison_does_not_launch_again(self):
        self.manager.collect.return_value = {'complete': True, 'verified_jobs': 648}
        self.assertTrue(owner.development_tick(self.manager, {}))
        self.manager.launch.assert_not_called()

    def test_pending_comparison_is_audited_before_bounded_launch(self):
        events = []
        self.manager.collect.side_effect = lambda: events.append('audit') or {'complete': False, 'verified_jobs': 3}
        self.manager.launch.side_effect = lambda **kw: events.append('launch') or {'active_jobs': 64}
        self.assertFalse(owner.development_tick(self.manager, {}))
        self.assertEqual(events, ['audit', 'launch'])
        self.manager.launch.assert_called_once_with(execute=True, limit=64)


if __name__ == '__main__': unittest.main()
