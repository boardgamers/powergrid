"""Final receipt compatibility and rejection of mixed or unfinished evidence."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from strategic_collection import ROOT

SPEC = importlib.util.spec_from_file_location('final_evidence', ROOT/'ai/strong/prepare-policy-iteration-final-evidence.py')
adapter = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(adapter)


class FinalEvidenceContracts(unittest.TestCase):
    def inputs(self):
        # Deliberately synthetic unit-test records; never saved as training,
        # target or final evidence. The production entry point admits real files.
        counts = {'2': 349, '3': 427, '4': 527, '5': 609, '6': 641}
        pin = {'training_verified': True, 'qualification_eligible': False,
               'feature_revision': '4.3-strategic-correction', 'revision': 'a'*40,
               'files': {'inference64.onnx': 'b'*64, 'inference64.pt': 'c'*64},
               'strict_parity_positions': 2553, 'cached_positions_checked': 17280}
        native = {'model_sha256': 'b'*64, 'checkpoint_sha256': 'c'*64,
            'complete': True, 'all_native_onnx_actions_equal': True, 'all_moves_legal': True,
            'parent_values_preserved': True, 'cached_parent_proposals_equal': True,
            'positions': 2553, 'cached_positions_checked': 17280, 'by_player_count': counts,
            'max_logit_error': 0., 'max_value_error': 0.}
        target = {'model_pin': deepcopy(pin), 'all_frozen_runtime_moves_identical': True,
            'maximum_value_difference': 0., 'package_sha256': 'd'*64,
            'summary': {'positions': 2553, 'all_moves_legal': True, 'search_decisions': 0,
                        'search_evaluations': 0, 'search_truncations': 0,
                        'groups': {'players': {n: {'positions': c} for n, c in counts.items()}},
                        'cold_start_ms': 200., 'warm': {'p50_ms': 5., 'p95_ms': 10.}}}
        machine = {'processor': 'AMD Ryzen 7 8840U w/ Radeon 780M Graphics'}
        package = {'model_sha256': 'b'*64, 'all_hashes_match': True, 'all_moves_legal': True,
                   'files_verified': 1200, 'positions_verified': 80, 'player_counts': [2,3,4,5,6]}
        return [pin, native, target, machine, package, counts]

    def test_mixed_models_partial_coverage_wrong_cpu_and_search_rejected(self):
        for index, field, value in [
            (0, 'synthetic_untrained', True), (0, 'training_verified', False),
            (1, 'model_sha256', '0'*64), (1, 'checkpoint_sha256', '0'*64),
            (1, 'all_native_onnx_actions_equal', False), (1, 'positions', 427),
            (1, 'cached_positions_checked', 17000), (1, 'by_player_count', {'2': 2553}),
            (1, 'max_value_error', float('nan')), (1, 'max_logit_error', -1.),
            (1, 'parent_values_preserved', False),
            (2, 'model_pin', {}), (2, 'all_frozen_runtime_moves_identical', False),
            (2, 'maximum_value_difference', .01), (3, 'processor', 'AMD Ryzen AI HX370'),
            (4, 'model_sha256', '0'*64), (4, 'positions_verified', 79),
            (4, 'player_counts', [2,3,4,5]), (4, 'all_hashes_match', False),
        ]:
            args = self.inputs(); args[index][field] = value
            with self.subTest(index=index, field=field), self.assertRaises(AssertionError):
                adapter.convert(*args)
        for field in ['search_decisions', 'search_evaluations', 'search_truncations']:
            args = self.inputs(); args[2]['summary'][field] = 1
            with self.subTest(field=field), self.assertRaises(AssertionError):
                adapter.convert(*args)

    def test_real_final_verifier_accepts_receipt_schema_but_not_missing_games(self):
        args = self.inputs(); reports = adapter.convert(*args)
        with TemporaryDirectory() as tmp:
            base = Path(tmp)
            for name, report in reports.items():
                self.assertFalse(report['qualification_eligible'])
                self.assertFalse(report['candidate_selected'])
                (base/(name+'.json')).write_text(json.dumps(report))
            candidate = {'status': 'selected', 'model_sha256': args[0]['files']['inference64.onnx'],
                         'search_samples': 0, 'geographic_search': False, 'search_scope': 'all'}
            (base/'candidate.json').write_text(json.dumps(candidate))
            (base/'absent-games.json').write_text(json.dumps({'player_count': 2, 'opponent': 'unit-test-placeholder'}))
            result = subprocess.run([sys.executable, str(ROOT/'ai/strong/verify-final.py'),
                str(base/'candidate.json'), str(base/'absent-games.json'), '--protocol',
                str(ROOT/'ai/strong/final-protocol-multiplayer.json'), '--parity', str(base/'parity.json'),
                '--cpu', str(base/'cpu.json'), '--package', str(base/'package.json'),
                '--output', str(base/'result.json')], capture_output=True, text=True)
            self.assertEqual(result.returncode, 1, result.stderr)
            report = json.loads((base/'result.json').read_text())
            self.assertFalse(report['passed'])
            self.assertEqual(len(report['errors']), 2, report['errors'])
            self.assertTrue(report['errors'][0].startswith('Unknown opponent report:'))
            self.assertEqual(report['errors'][1], 'Missing required opponent evaluations')

    def test_pending_training_cannot_create_receipts_or_download(self):
        with TemporaryDirectory() as tmp:
            base = Path(tmp); state = base/'upstream.json'
            state.write_text(json.dumps({'stage': 'waiting_for_training_submission'}))
            with patch.object(adapter.benchmark, 'UPSTREAM', state), \
                 patch.object(adapter, 'OUTPUT', base/'out'), \
                 patch.object(adapter, 'hf_hub_download') as download, \
                 patch.object(adapter.benchmark, 'hf_hub_download') as benchmark_download:
                with self.assertRaisesRegex(AssertionError, 'not ready'):
                    adapter.prepare()
                self.assertFalse((base/'out').exists())
                download.assert_not_called(); benchmark_download.assert_not_called()


if __name__ == '__main__':
    unittest.main()
