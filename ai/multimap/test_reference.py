"""Offline guard/transport tests; no HF download, model inference, or full games."""
import io
import json
from pathlib import Path
import sys
import tarfile
import tempfile
import types
import unittest
from unittest import mock

import reference_recover as recover
import reference_evaluate as evaluate


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        recover.CACHE.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix='test-reference-', dir=recover.CACHE)
        self.root = Path(self.temp.name)
        self.addCleanup(self.temp.cleanup)

    def test_remote_limits_checked_without_downloading(self):
        stub = types.SimpleNamespace(
            hf_hub_url=lambda *a, **kw: 'https://huggingface.co/test', get_token=lambda: None,
            get_hf_file_metadata=lambda *a, **kw: types.SimpleNamespace(
                commit_hash=recover.PINS['source']['revision'], size=recover.MAX_ARCHIVE + 1))
        with mock.patch.dict(sys.modules, huggingface_hub=stub):
            with self.assertRaisesRegex(ValueError, 'oversized'):
                recover.remote_metadata(recover.PINS['source'])
        stub.get_hf_file_metadata = lambda *a, **kw: types.SimpleNamespace(commit_hash='mutable-main', size=1)
        with mock.patch.dict(sys.modules, huggingface_hub=stub):
            with self.assertRaisesRegex(ValueError, 'revision'):
                recover.remote_metadata(recover.PINS['source'])

    def test_budget_refuses_before_write(self):
        (self.root / 'existing').write_bytes(b'1234')
        with mock.patch.object(recover, 'MAX_CACHE', 10):
            self.assertEqual(recover.budget(self.root, 6), 10)
            with self.assertRaisesRegex(ValueError, 'budget'):
                recover.budget(self.root, 7)

    def archive(self, members):
        archive = self.root / 'source.tgz'
        with tarfile.open(archive, 'w:gz') as tf:
            for info, contents in members:
                tf.addfile(info, io.BytesIO(contents) if contents is not None else None)
        return archive

    def test_selective_regular_extraction_and_path_rejection(self):
        chosen = tarfile.TarInfo('artifact/keep'); chosen.size = 3
        omitted = tarfile.TarInfo('artifact/data/roots'); omitted.size = 4
        archive = self.archive([(chosen, b'yes'), (omitted, b'nope')])
        out = self.root / 'out'
        recover.extract_selected(archive, out, {'artifact/keep': 'keep'}, self.root)
        self.assertEqual((out / 'keep').read_bytes(), b'yes')
        self.assertFalse((out / 'data').exists())
        for name in ('/escape', '../escape', 'ok/../../escape', r'ok\escape'):
            with self.assertRaises(ValueError):
                recover.safe_name(name)
        with self.assertRaises(ValueError):
            recover.extract_selected(archive, self.root / 'bad', {'artifact/keep': '../escape'}, self.root)

    def test_symlinks_are_never_extracted(self):
        link = tarfile.TarInfo('artifact/link'); link.type = tarfile.SYMTYPE; link.linkname = '/etc/passwd'
        archive = self.archive([(link, None)])
        with self.assertRaisesRegex(ValueError, 'Non-regular'):
            recover.extract_selected(archive, self.root / 'out', {'artifact/link': 'link'}, self.root)

    def test_memory_archive_hash_and_budget_before_extraction(self):
        import hashlib
        pin = dict(recover.PINS['source'], sha256=hashlib.sha256(b'abc').hexdigest())
        meta = dict(bytes=3, revision=pin['revision'])
        response = mock.MagicMock()
        response.iter_bytes.return_value = [b'a', b'bc']
        session = mock.Mock()
        session.stream.return_value.__enter__ = mock.Mock(return_value=response)
        session.stream.return_value.__exit__ = mock.Mock(return_value=False)
        with mock.patch('huggingface_hub.utils.get_session', return_value=session), mock.patch('huggingface_hub.utils.build_hf_headers', return_value={}):
            with recover.memory_archive(pin, meta) as stream:
                self.assertEqual(stream.read(), b'abc')
            with self.assertRaisesRegex(ValueError, 'advertised size'):
                recover.memory_archive(pin, dict(meta, bytes=2))
            with self.assertRaisesRegex(ValueError, 'hash/size'):
                recover.memory_archive(dict(pin, sha256='0'*64), meta)
        self.assertEqual(list(self.root.iterdir()), [])

    def test_runtime_filter_omits_roots_and_keeps_exact_implementation(self):
        for name in ('ai/core.cjs', 'ai/strong/public_policy_runtime_v1.py',
                     'ai/strong/current_engine_scope_v1.py', 'ai/strong/sealed-policy-beliefs.cjs',
                     'engine/dist/index.js', 'policy.onnx', 'manifest.json'):
            self.assertTrue(recover.runtime_member(name))
        for name in ('ai/strong/fixtures/giant.jsonl', 'ai/strong/data/roots.jsonl.gz', 'final-opponent-a260.onnx'):
            self.assertFalse(recover.runtime_member(name))

    @unittest.skipUnless((recover.CACHE / 'recovery.json').exists(), 'Run bounded recovery first')
    def test_recovered_pins_and_loader_completeness(self):
        receipt = json.loads((recover.CACHE / 'recovery.json').read_text())
        self.assertEqual(receipt['pins'], recover.PINS)
        self.assertEqual(receipt['verifiedArchiveManifestFiles'], 1467)
        self.assertEqual(receipt['locallyVerifiedFiles'], 1467 if receipt['exactServiceReady'] else 1450)
        self.assertLess(recover.budget(recover.CACHE), recover.MAX_CACHE)
        self.assertFalse((recover.CACHE / 'source.tgz').exists())
        self.assertEqual(recover.digest(recover.CACHE / 'ppo.pt'), recover.PINS['ppo']['sha256'])
        recover.verify_artifact(recover.CACHE / 'artifact', require_complete=False)
        if receipt['exactServiceReady']:
            recover.verify_artifact(recover.CACHE / 'artifact')
        else:
            with self.assertRaisesRegex(ValueError, 'omitted non-runtime'):
                recover.verify_artifact(recover.CACHE / 'artifact')


class HarnessTests(unittest.TestCase):
    def test_plans_are_bounded_new_namespace_and_not_seed_selection(self):
        plans = evaluate.plans()
        self.assertEqual(len(plans), 20)
        self.assertEqual(len({p['cell'] for p in plans}), 20)
        self.assertTrue(all(p['seed'].startswith(evaluate.NAMESPACE + ':') for p in plans))
        for mode in ('selected', 'teacher', 'reference'):
            self.assertEqual(evaluate.plans(1, mode)[0]['focalPolicy'], mode)
        self.assertEqual([p['seed'] for p in evaluate.plans(20, 'teacher')], [p['seed'] for p in plans])
        for count in (0, 21, True):
            with self.assertRaises(ValueError): evaluate.plans(count)
        with self.assertRaises(ValueError): evaluate.plans(1, 'best-confirmation-seed')

    def test_json_transport_preserves_order(self):
        process = evaluate.LineProcess([sys.executable, '-u', '-c',
            'import sys,json\nfor line in sys.stdin: print(json.dumps({"keys":list(json.loads(line))}),flush=True)'])
        try:
            self.assertEqual(process.call({'z': 1, 'a': 2})['keys'], ['z', 'a'])
            self.assertEqual(process.call({'b': 1, 'z': 2})['keys'], ['b', 'z'])
        finally:
            process.close()
        self.assertIsNotNone(process.process.poll())

    def test_subprocess_timeout_is_bounded(self):
        process = evaluate.LineProcess([sys.executable, '-u', '-c', 'import time; time.sleep(30)'], timeout=.1)
        try:
            with self.assertRaises(TimeoutError): process.call({'request': True})
        finally:
            process.close()

    def test_invalid_supplied_model_provenance_and_game_cap_fail_before_start(self):
        with self.assertRaises(ValueError): evaluate.evaluate([])
        with self.assertRaises(ValueError): evaluate.evaluate(evaluate.plans() + evaluate.plans(1))
        with self.assertRaisesRegex(ValueError, 'provenance'): evaluate.evaluate(evaluate.plans(1), model=object())
        with self.assertRaisesRegex(ValueError, 'OR checkpoint'):
            evaluate.evaluate(evaluate.plans(1), model=object(), checkpoint='x', model_label='test')

    def test_unredacted_requests_rejected_before_service(self):
        process = evaluate.ReferenceProcess.__new__(evaluate.ReferenceProcess)
        process.call = mock.Mock(side_effect=AssertionError('Must reject before sending'))
        for state in ({'seed': 'secret', 'powerPlantsDeck': [7], 'hiddenLog': []},
                      {'seed': 'private', 'powerPlantsDeck': [], 'hiddenLog': []}):
            with self.assertRaisesRegex(ValueError, 'Unredacted'):
                process.decide(dict(requestId='test', revision=0, player=0, state=state))
        process.call.assert_not_called()


if __name__ == '__main__':
    unittest.main()
