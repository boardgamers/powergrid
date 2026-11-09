"""Offline filesystem/metadata/whole-batch worker conformance. No HF or games."""
import copy
from contextlib import ExitStack
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

import job_replica_stress_v1 as worker
import replica_stress_study_v1 as study
from replica_stress_rollout_v1 import model_pins
from expert_policy import PROTOCOL as EXPERT
from data import atomic_json, digest
from test_replica_stress_rollout_v1 import outcome

COMMIT = 'a' * 40
REVISION = 'b' * 40
SNAPSHOT = 'c' * 40


def identity_fixture(panel='strong', smoke=False, source_files=None):
    expert = dict(protocol=copy.deepcopy(EXPERT), runtimeVersions={'fixture': 'frozen'},
                  referenceManifestSha256=EXPERT['reference']['runtimeManifestSha256'], sourceFiles={})
    return dict(schema='multimap-replica-stress-identity-v1', protocol=worker.PROTOCOL,
                panel=panel, smoke=smoke, workers=6, threads=1, tasks=study.plan(panel, smoke),
                sourceFiles=source_files or {}, frozenSources={},
                modelProvenance={pin['name']: dict(pin=pin, config=copy.deepcopy(expert)) for pin in model_pins()})


def source_fixture():
    return dict(group=worker.GROUP, sourceCommit=COMMIT, sourceRevision=REVISION,
                sourceRepo='coyotte508/powergrid-ai-training-v1',
                sourcePath=f'multimap/{worker.GROUP}/source.tgz', sourceSha256='d' * 64)


def write_snapshot(base, source, panel, config, committed=1):
    base = Path(base)
    atomic_json(base / 'study/plan.json', config)
    groups = study.batches(config['tasks'])
    games = []
    for index, tasks in enumerate(groups[:committed]):
        records = [outcome(s) for s in tasks]
        atomic_json(base / f'study/batch-{index:03}.json', dict(schema='multimap-replica-stress-batch-v1',
            index=index, taskSha256=study.task_hash(tasks), games=records))
        games.extend(records)
    status = dict(run=worker.GROUP + '-' + panel, workflow='replica-stress-v1', panel=panel,
                  segment=1, slot=panel, workers=6, smoke=False, protocol=worker.PROTOCOL,
                  stage='batches-16', **source)
    atomic_json(base / 'status.json', status)
    atomic_json(base / 'protocol.json', worker.PROTOCOL)
    frozen = config['modelProvenance']['expert24']['config']
    atomic_json(base / 'environment.json', dict(requirementsSha256=frozen['protocol']['referenceRequirementsSha256'],
                                              versions=frozen['runtimeVersions']))
    ref = frozen['protocol']['reference']
    atomic_json(base / 'recovery.json', dict(exactServiceReady=True, runtimeManifestSha256=frozen['referenceManifestSha256'],
        policySha256=ref['policySha256'], pins=dict(source=ref['sourcePin'], model=ref['modelPin']), omitted=[]))
    if committed == len(groups):
        atomic_json(base / 'study/summary.json', study.analyze(games, panel, False))
    worker.write_manifest(base, worker.compact_files(base))
    return base


class WorkerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = identity_fixture()

    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.root = Path(self.stack.enter_context(tempfile.TemporaryDirectory()))
        self.source = source_fixture()
        self.base = write_snapshot(self.root / 'snapshot', self.source, 'strong', self.config)
        self.events = []
        self.stack.enter_context(patch.object(worker, 'remote_size', side_effect=self.metadata))
        self.stack.enter_context(patch.object(worker, 'hf_hub_download', side_effect=self.download))

    def metadata(self, repo, name, revision, maximum, **kwargs):
        self.assertEqual(revision, SNAPSHOT)
        self.events.append(('metadata', name))
        size = (self.base / name.split('/', 2)[2]).stat().st_size
        if size > maximum:
            raise ValueError('fixture metadata budget')
        return size

    def download(self, repo, name, revision, cache_dir, **kwargs):
        self.events.append(('download', name))
        content = (self.base / name.split('/', 2)[2]).read_bytes()
        repository = Path(cache_dir) / 'models--fixture--repository'
        blob = repository / 'blobs' / __import__('hashlib').sha256(content).hexdigest()
        blob.parent.mkdir(parents=True, exist_ok=True)
        blob.write_bytes(content)
        path = repository / 'snapshots' / revision / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.symlink_to(os.path.relpath(blob, path.parent))
        return str(path)

    def fetch(self):
        return worker.fetch_snapshot('fixture', worker.GROUP + '-strong', SNAPSHOT,
                                     self.root / 'verified', self.root / 'cache')

    def validate(self, **kwargs):
        return worker.validate_snapshot(self.base, self.source, 'strong', worker.GROUP + '-strong', self.config, **kwargs)

    def rewrite_manifest(self):
        worker.write_manifest(self.base, worker.compact_files(self.base))

    def test_real_snapshot_blob_links_all_metadata_before_payload(self):
        checked = self.fetch()
        self.assertEqual(len(checked['files']), 2)
        first = next(i for i, (kind, name) in enumerate(self.events)
                     if kind == 'download' and not name.endswith('artifacts.json'))
        metadata = {n for k, n in self.events[:first] if k == 'metadata'}
        self.assertEqual(metadata, {n for k, n in self.events if k == 'download'})
        self.assertEqual(checked['allFileHashes'], worker.read(self.base / 'artifacts.json'))
        self.assertFalse(any(p.is_symlink() for p in (self.root / 'verified').rglob('*')))

    def test_contiguous_whole_three_arm_allseat_prefix_is_valid(self):
        checked = self.validate()
        self.assertEqual(checked['committedBatches'], 1)
        self.assertEqual(checked['committedGames'], 6)
        self.assertFalse(checked['complete'])

    def test_manifest_all_640_batches_fits_actual_64k_limit(self):
        value = {name: 'a' * 64 for name in worker.NAMES}
        encoded = (worker.canonical(value) + '\n').encode()
        self.assertEqual(len(value), 646)
        self.assertLessEqual(len(encoded), worker.MANIFEST_LIMIT)
        self.assertEqual(len(worker.validate_manifest(value)), 642)

    def test_manifest_path_index_hash_and_metadata_coverage(self):
        original = worker.read(self.base / 'artifacts.json')
        for name in ('../escape', 'study/batch-640.json', 'model.pt', 'study/batch-000.json.tmp'):
            with self.subTest(name=name), self.assertRaises(ValueError):
                worker.validate_manifest(dict(original, **{name: 'a' * 64}))
        for name in worker.METADATA_NAMES | {'study/plan.json'}:
            value = dict(original); value.pop(name)
            with self.subTest(missing=name), self.assertRaises(ValueError): worker.validate_manifest(value)
        with self.assertRaises(ValueError): worker.validate_manifest(dict(original, **{'status.json': 'bad'}))

    def test_metadata_aggregate_includes_status_environment_and_manifest(self):
        actual = self.metadata
        def large(repo, name, revision, **kwargs):
            if name.endswith(('status.json', 'recovery.json')):
                self.events.append(('metadata', name))
                return worker.LIMIT // 2
            return actual(repo, name, revision, **kwargs)
        with patch.object(worker, 'remote_size', side_effect=large), self.assertRaisesRegex(ValueError, 'Aggregate'):
            self.fetch()
        self.assertEqual([n for k, n in self.events if k == 'download'],
                         ['runs/' + worker.GROUP + '-strong/artifacts.json'])

    def test_remote_hash_corruption_rejected(self):
        (self.base / 'environment.json').write_text('{}')
        with self.assertRaisesRegex(ValueError, 'hash/size'): self.fetch()

    def test_cache_escape_rejected_even_when_bytes_hashes_are_right(self):
        original = self.download
        def escape(*args, **kwargs):
            path = Path(original(*args, **kwargs))
            path.unlink(); path.symlink_to(self.base / args[1].split('/', 2)[2])
            return path
        with patch.object(worker, 'hf_hub_download', side_effect=escape), self.assertRaisesRegex(ValueError, 'escapes cache'):
            self.fetch()

    def test_actual_download_size_differs_from_metadata(self):
        original = self.download
        def changed(*args, **kwargs):
            path = Path(original(*args, **kwargs)); path.write_bytes(path.read_bytes() + b' '); return path
        with patch.object(worker, 'hf_hub_download', side_effect=changed), self.assertRaisesRegex(ValueError, 'metadata size'):
            self.fetch()

    def test_no_raw_payload_and_no_nonregular_files(self):
        for forbidden in worker.FORBIDDEN:
            with self.subTest(forbidden=forbidden), self.assertRaises(ValueError):
                worker.compact_json({'nested': [{'nested': {forbidden: []}}]})
        fifo = self.base / 'fifo'; os.mkfifo(fifo)
        with self.assertRaisesRegex(ValueError, 'Nonregular'): worker.compact_files(self.base)

    def test_output_and_parent_links_forbidden(self):
        link = self.root / 'link'; link.symlink_to(self.base, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, 'symlink'): worker.read(link / 'status.json')
        (self.base / 'study/link').symlink_to(self.base / 'status.json')
        with self.assertRaisesRegex(ValueError, 'symlink'): worker.compact_files(self.base)

    def test_each_pair_of_five_paths_must_be_nonnested(self):
        paths = [self.root / n for n in ('output', 'reference', 'venv', 'resume', 'models')]
        worker.shared.separate_paths(*paths)
        for a in range(5):
            for b in range(5):
                if a == b: continue
                changed = list(paths); changed[b] = changed[a] / 'child'
                with self.subTest(a=a, b=b), self.assertRaisesRegex(ValueError, 'nonnested'):
                    worker.shared.separate_paths(*changed)

    def test_local_uncommitted_tmp_ignored_but_remote_tmp_rejected(self):
        (self.base / 'study/batch-001.json.tmp').write_text('{incomplete')
        self.assertNotIn('study/batch-001.json.tmp', worker.compact_files(self.base))
        self.assertEqual(self.validate()['committedBatches'], 1)

    def test_duplicate_and_nonfinite_json_rejected(self):
        path = self.root / 'bad.json'
        for content in ('{"a":1,"a":2}', '{"a":NaN}', '{"a":Infinity}'):
            path.write_text(content)
            with self.subTest(content=content), self.assertRaises(ValueError): worker.read(path)

    def test_corrupted_batch_spec_counters_hash_or_partial_arm_rejected(self):
        path = self.base / 'study/batch-000.json'; original = worker.read(path)
        for mutation in ('spec', 'counter', 'hash', 'arm', 'index'):
            value = copy.deepcopy(original)
            if mutation == 'spec': value['games'][0]['spec']['seed'] += '-changed'
            if mutation == 'counter': value['games'][0]['policyRequests']['replica1'] += 1
            if mutation == 'hash': value['taskSha256'] = 'f' * 64
            if mutation == 'arm': value['games'].pop()
            if mutation == 'index': value['index'] = 1
            atomic_json(path, value)
            with self.subTest(mutation=mutation), self.assertRaises(ValueError): self.validate()

    def test_noncontiguous_prefix_rejected(self):
        (self.base / 'study/batch-000.json').rename(self.base / 'study/batch-001.json')
        with self.assertRaisesRegex(ValueError, 'Noncontiguous'): self.validate()

    def test_full_task_model_source_runtime_identity_drift(self):
        path = self.base / 'study/plan.json'; original = worker.read(path)
        for name, value in (('workers', 5), ('sourceFiles', {'changed': 'e' * 64}), ('modelProvenance', {}), ('smoke', True)):
            atomic_json(path, dict(original, **{name: value}))
            with self.subTest(name=name), self.assertRaisesRegex(ValueError, 'full task/model/source/runtime'):
                self.validate()

    def test_status_protocol_environment_reference_drift(self):
        for name, field, value in (('status', 'sourceCommit', 'e' * 40), ('status', 'segment', 2),
                                   ('status', 'workers', 5), ('environment', 'versions', {}),
                                   ('recovery', 'omitted', ['missing']), ('protocol', 'workers', 5)):
            path = self.base / (name + '.json'); original = worker.read(path)
            atomic_json(path, dict(original, **{field: value}))
            with self.subTest(name=name, field=field), self.assertRaises(ValueError): self.validate()
            atomic_json(path, original)

    def test_false_complete_status_and_partial_summary_forbidden(self):
        status = worker.read(self.base / 'status.json'); status['stage'] = 'complete'
        atomic_json(self.base / 'status.json', status)
        with self.assertRaisesRegex(ValueError, 'claims incomplete'): self.validate()
        status['stage'] = 'failed'; atomic_json(self.base / 'status.json', status)
        with self.assertRaisesRegex(ValueError, 'worker/game failure'): self.validate()
        status['stage'] = 'batches-16'; atomic_json(self.base / 'status.json', status)
        atomic_json(self.base / 'study/summary.json', {})
        with self.assertRaisesRegex(ValueError, 'Summary exists'): self.validate()

    def test_restoration_verifies_before_copy_and_preserves_only_study_files(self):
        dest = self.root / 'destination'
        checked = worker.restore_resume('fixture', worker.GROUP + '-strong', SNAPSHOT, dest, self.root / 'resume',
                                         source=self.source, panel='strong', expected_identity=self.config)
        self.assertEqual(checked['transaction']['committedBatches'], 1)
        self.assertEqual({p.relative_to(dest).as_posix() for p in dest.rglob('*') if p.is_file()}, set(checked['files']))
        self.assertEqual(digest(dest / 'study/batch-000.json'), digest(self.base / 'study/batch-000.json'))

    def test_64mib_budget_boundary(self):
        used = worker.artifact_budget(self.base)
        self.assertEqual(worker.artifact_budget(self.base, worker.LIMIT - used), worker.LIMIT)
        with self.assertRaisesRegex(ValueError, 'budget'): worker.artifact_budget(self.base, worker.LIMIT - used + 1)


class CompletedSnapshotTests(unittest.TestCase):
    def test_complete_real_640_batch_snapshot_requires_audit_never_recovery(self):
        with tempfile.TemporaryDirectory() as directory:
            config = identity_fixture()
            source = source_fixture()
            base = write_snapshot(Path(directory) / 'complete', source, 'strong', config, 640)
            with self.assertRaisesRegex(ValueError, 'requires audit'):
                worker.validate_snapshot(base, source, 'strong', worker.GROUP + '-strong', config)
            checked = worker.validate_snapshot(base, source, 'strong', worker.GROUP + '-strong', config,
                                               require_incomplete=False)
            self.assertEqual(checked['committedBatches'], 640)
            self.assertEqual(checked['committedGames'], 7680)
            self.assertTrue(checked['complete'])
            (base / 'study/summary.json').unlink()
            # A completed batch set without its final summary also needs audit;
            # do not pay for another job merely to write a summary.
            with self.assertRaisesRegex(ValueError, 'requires audit'):
                worker.validate_snapshot(base, source, 'strong', worker.GROUP + '-strong', config)


class WorkerRunTests(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack(); self.addCleanup(self.stack.close)
        self.root = Path(self.stack.enter_context(tempfile.TemporaryDirectory()))
        self.base = self.root / 'output'
        self.source = source_fixture()
        self.config = identity_fixture()
        preflight = dict(smokeIdentities={'strong': dict(self.config, smoke=True, tasks=study.plan('strong', True))})
        atomic_json(self.root / 'source-manifest.json', dict(gitCommit=COMMIT))
        atomic_json(self.root / 'ai/multimap/replica-stress-preflight-v1.json', preflight)
        self.stack.enter_context(patch.object(worker, 'ROOT', self.root))
        environment = dict(RUN_ID=worker.GROUP + '-strong', MODEL_REPO=worker.PROTOCOL['modelRepo'],
            DATASET_REPO=self.source['sourceRepo'], SOURCE_PATH=self.source['sourcePath'],
            SOURCE_REVISION=REVISION, SOURCE_COMMIT=COMMIT, SOURCE_SHA256=self.source['sourceSha256'],
            REPLICA_STRESS_PANEL='strong', REPLICA_STRESS_GROUP=worker.GROUP, REPLICA_STRESS_SEGMENT='1',
            REPLICA_STRESS_SLOT='strong', REPLICA_STRESS_WORKERS='6', REPLICA_STRESS_SMOKE='0',
            RUN_DIR=str(self.base), REFERENCE_CACHE=str(self.root / 'reference'),
            REFERENCE_VENV=str(self.root / 'venv'), RESUME_CACHE=str(self.root / 'resume'),
            REPLICA_STRESS_MODEL_CACHE=str(self.root / 'models'))
        self.stack.enter_context(patch.dict(os.environ, environment, clear=True))
        self.api = Mock(); self.api.model_info.return_value.private = True
        self.api.dataset_info.return_value.private = True
        self.api.upload_folder.return_value.oid = SNAPSHOT
        self.stack.enter_context(patch('huggingface_hub.HfApi', return_value=self.api))
        frozen = self.config['modelProvenance']['expert24']['config']; ref = frozen['protocol']['reference']
        self.stack.enter_context(patch.object(worker.shared, 'ensure_reference_environment', return_value=(
            self.root / 'venv/bin/python', dict(requirementsSha256=frozen['protocol']['referenceRequirementsSha256'],
                                               versions=frozen['runtimeVersions']))))
        self.stack.enter_context(patch.object(worker, 'recover_reference', return_value=dict(exactServiceReady=True,
            runtimeManifestSha256=frozen['referenceManifestSha256'], policySha256=ref['policySha256'],
            pins=dict(source=ref['sourcePin'], model=ref['modelPin']), omitted=[])))
        self.stack.enter_context(patch.object(worker, 'identity', return_value=self.config))
        self.evaluate = self.stack.enter_context(patch.object(worker, 'evaluate', return_value=dict(games=7680)))
        from contextlib import redirect_stdout, redirect_stderr
        import io
        self.stdout = io.StringIO(); self.stderr = io.StringIO()
        self.stack.enter_context(redirect_stdout(self.stdout)); self.stack.enter_context(redirect_stderr(self.stderr))

    def test_worker_fixed_scope_separate_caches_runtime_identity_and_compact_upload(self):
        worker.run()
        self.evaluate.assert_called_once()
        self.assertEqual(self.evaluate.call_args.kwargs['workers'], 6)
        self.assertFalse(self.evaluate.call_args.kwargs['smoke'])
        self.assertEqual(self.api.upload_folder.call_count, 2)
        names = self.api.upload_folder.call_args.kwargs['allow_patterns']
        self.assertNotIn('models', names)
        self.assertTrue(all(n in worker.NAMES | {'artifacts.json'} for n in names))
        status = worker.read(self.base / 'status.json')
        self.assertEqual(status['workflow'], 'replica-stress-v1')
        self.assertEqual(status['sourceCommit'], COMMIT)

    def test_worker_game_error_no_retry_no_fake_zero_and_sanitized_status(self):
        secret = 'SECRET-RAW-PAYLOAD-DO-NOT-PRINT'
        self.evaluate.side_effect = RuntimeError(secret)
        with self.assertRaisesRegex(RuntimeError, 'Replica stress stopped') as caught:
            worker.run()
        self.assertEqual(self.evaluate.call_count, 1)
        status = worker.read(self.base / 'status.json')
        self.assertEqual(status['error'], {'code': 'replica-stress-job-stopped'})
        self.assertNotIn('result', status)
        self.assertNotIn(secret, json.dumps(status) + self.stdout.getvalue() + self.stderr.getvalue() + str(caught.exception))

    def test_preflight_runtime_model_drift_aborts_before_collection(self):
        changed = dict(self.config, workers=5)
        with patch.object(worker, 'identity', return_value=changed), self.assertRaises(RuntimeError): worker.run()
        self.evaluate.assert_not_called()

    def test_no_initial_with_resume_or_wrong_workers_or_slot(self):
        for changed in ({'REPLICA_STRESS_WORKERS': '5'}, {'REPLICA_STRESS_SLOT': 'recovery'},
                        {'RESUME_RUN': worker.GROUP + '-strong', 'RESUME_REVISION': SNAPSHOT}):
            with patch.dict(os.environ, changed), self.subTest(changed=changed), self.assertRaises(ValueError): worker.run()
        self.evaluate.assert_not_called()
        self.api.upload_folder.assert_not_called()


class DownloadedFileTests(unittest.TestCase):
    def test_real_hf_file_types_and_strict_resolution(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); cache = root / 'cache'; cache.mkdir()
            blob = cache / 'blob'; blob.write_text('{}')
            self.assertEqual(worker.downloaded_file(blob, cache, 2), blob)
            link = cache / 'snapshot'; link.symlink_to(blob)
            self.assertEqual(worker.downloaded_file(link, cache, 2), blob)
            fifo = cache / 'fifo'; os.mkfifo(fifo)
            for path in (cache, fifo):
                with self.assertRaisesRegex(ValueError, 'not a regular'): worker.downloaded_file(path, cache, 2)
            outside = root / 'cache-outside'; outside.write_text('{}')
            blob.unlink(); blob.symlink_to(outside)
            with self.assertRaisesRegex(ValueError, 'escapes cache'): worker.downloaded_file(link, cache, 2)
            dangling = cache / 'dangling'; dangling.symlink_to(cache / 'missing')
            cycle = cache / 'cycle'; cycle.symlink_to(cycle)
            for path in (dangling, cycle, cache / 'missing'):
                with self.assertRaises((OSError, RuntimeError)): worker.downloaded_file(path, cache, 2)


if __name__ == '__main__':
    unittest.main()
