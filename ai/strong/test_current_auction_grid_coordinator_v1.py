"""Fake-manager owner ordering/failure checks; no processes or jobs launched."""
import importlib.util
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

spec = importlib.util.spec_from_file_location('owner', Path(__file__).with_name('coordinate-current-auction-grid-v1.py'))
owner = importlib.util.module_from_spec(spec); spec.loader.exec_module(owner)


class OwnerTests(unittest.TestCase):
    def test_failed_collection_never_submits_more(self):
        manager = SimpleNamespace(collect=Mock(side_effect=RuntimeError('failed original')), launch=Mock())
        with patch.object(owner, 'check_pins'):
            with self.assertRaises(RuntimeError): owner.tick(manager, {})
        manager.launch.assert_not_called()

    def test_complete_collection_never_submits_more(self):
        manager = SimpleNamespace(collect=Mock(return_value={'complete': True, 'verified_jobs': 100}), launch=Mock())
        with patch.object(owner, 'check_pins'), patch.object(owner, 'write_state'):
            self.assertTrue(owner.tick(manager, {}))
        manager.launch.assert_not_called()

    def test_audits_before_bounded_launch(self):
        order = []
        with tempfile.TemporaryDirectory() as tmp:
            manager = SimpleNamespace(OUT=Path(tmp),
                collect=Mock(side_effect=lambda: (order.append('audit') or {'complete': False, 'verified_jobs': 3})),
                launch=Mock(side_effect=lambda **kw: (order.append(('launch', kw)) or {'active_jobs': 5})))
            with patch.object(owner, 'check_pins'), patch.object(owner, 'write_state'):
                self.assertFalse(owner.tick(manager, {}))
            self.assertEqual(order, ['audit', ('launch', {'execute': True, 'limit': 64})])

    def test_stop_marker_blocks_tick_before_collection(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(owner, 'OUT', Path(tmp)):
            (Path(tmp) / 'STOP').touch(); manager = SimpleNamespace(collect=Mock(), launch=Mock())
            with self.assertRaises(KeyboardInterrupt): owner.tick(manager, {'code_hashes': {}})
            manager.collect.assert_not_called(); manager.launch.assert_not_called()


if __name__ == '__main__': unittest.main()
