"""Offline adversarial tests; synthetic metadata/checkpoints only.

No live HF, downloads, model games or historical tensor/outcome inspection. Torch
fixtures are freshly constructed tiny parameters or random ExpertPolicy tensors;
they are not fitted on any data. Run with the existing candidate venv:
  ai/.venv/bin/python -B -m unittest discover -s ai/multimap \
      -p 'test_audit_expert_replicas_integrity_v1.py'
"""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import random
import subprocess
import sys
import tempfile
from types import SimpleNamespace as NS
import unittest
from unittest.mock import patch

import audit_expert_replicas_integrity_v1 as a
import audit_expert_replicas_v1 as j

HAS_TORCH = importlib.util.find_spec('torch') is not None


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, allow_nan=False) + '\n')


def manifest_fixture(root, original=False):
    for name in a.snapshot_names(original):
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b'{}\n' if name.endswith('.json') else b'synthetic-not-torch')
    manifest = {n: a.digest(root / n) for n in a.snapshot_names(original)}
    write(root / 'artifacts.json', manifest)
    return manifest


class FakeRemote:
    """Offline implementation of only the authenticated RemoteFiles contract."""
    def __init__(self, source, replica=1, original=False):
        self.source = source
        self.prefix = 'runs/' + a.run_name(replica, original) + '/'
        self.entries = [NS(path=self.prefix + p.relative_to(source).as_posix(), size=p.stat().st_size,
                           blob_id='b'*40, lfs=None) for p in source.rglob('*') if p.is_file()]
        self.api = NS(list_repo_tree=lambda *args, **kwargs: iter(self.entries))
        self.evidence = []
        self.got = []

    def describe(self, pin):
        return next(e for e in self.entries if e.path == pin['path'])

    def get(self, pin, metadata=None, cached=None):
        self.got.append(pin['path'])
        path = Path(cached) if cached else self.source / pin['path'][len(self.prefix):]
        if 'sha256' in pin:
            a.require(a.digest(path) == pin['sha256'], 'Fake remote hash')
        self.evidence.append(dict(path=pin['path'], sha256=a.digest(path)))
        return path


def transaction_boundary(stage='train', update=32, confirmations=None):
    return dict(stage=stage, update=update, confirmations={} if confirmations is None else confirmations,
                result=None, history=[], bestSha256='a'*64)


def synthetic_log(replica=1, segment=1, revision='f'*40):
    lines = ['# tests 7', '# pass 7', '# fail 0',
             json.dumps(dict(stage='expert-ppo', update=999)),  # mocked startup NOT production
             json.dumps(dict(stage='uploaded', label='runtime-ready', revision='c'*40)),
             json.dumps(dict(stage='uploaded', label='complete', revision='c'*40)),
             json.dumps(dict(stage='complete', run='group-r1', result={'qualified': False})),
             'Ran 34 tests in 0.1s', '', 'OK',
             json.dumps(dict(stage='uploaded', label='runtime-ready', revision='0'*40))]
    def upload(label, value):
        lines.append(json.dumps(dict(stage='uploaded', label=label, revision=value)))
    if segment == 1:
        upload('initial', '1'*40)
        upload('warmup', '2'*40)
        for u in range(1, 33):
            upload('update-' + str(u), a.PINS[replica]['selection'] if u == 32 else format(u + 10, '040x'))
            lines.append(json.dumps(dict(stage='expert-ppo', update=u)))
        upload('confirmation-selected', a.PINS[replica]['original'])
    else:
        upload('confirmation-teacher', '3'*40)
        upload('complete', '4'*40)
        upload('complete', revision)
        lines.append(json.dumps(dict(stage='complete', run=a.run_name(replica), result={})))
    return '\n'.join(lines)


class StandardLibraryTests(unittest.TestCase):
    def test_import_is_lazy_and_offline(self):
        code = ("import sys;sys.path.insert(0," + repr(str(a.HERE)) + ");"
                "import audit_expert_replicas_integrity_v1;"
                "assert 'torch' not in sys.modules;assert 'huggingface_hub' not in sys.modules;"
                "assert 'expert_replicas_v1' not in sys.modules")
        subprocess.run([sys.executable, '-B', '-c', code], check=True)

    def test_source_expansion_budget_is_private_and_matches_frozen_launcher(self):
        helpers = a.authenticate_helpers()
        old = helpers['audit_neural']
        before = dict(old.verify_source.__globals__)
        bound = a.source_verifier(helpers, {'sourceFiles': {'example.py': 'a'*64}})
        self.assertIs(bound.__code__, old.verify_source.__code__)
        self.assertEqual(bound.__globals__['LIMIT'], 256 * 1024**2 - 1)
        self.assertEqual(old.LIMIT, 128 * 1024**2)
        self.assertEqual(old.verify_source.__globals__, before)
        for size in (128 * 1024**2, 134987579, 256 * 1024**2 - 1):
            self.assertLessEqual(size, bound.__globals__['LIMIT'])
        self.assertGreater(256 * 1024**2, bound.__globals__['LIMIT'])
        remote = old.RemoteFiles(NS())
        with self.assertRaisesRegex(ValueError, '128 MiB'):
            remote.get(dict(repo='private', revision='f'*40, path='file'),
                       metadata=NS(size=128 * 1024**2 + 1), cached='/not-read')

    def test_environment_is_bound_to_actual_expert_preflight_schema(self):
        config = dict(smoke=False, runtimeVersions={'reference': {'numpy': 'pinned'}})
        preflight = dict(smokeIdentities={'1': dict(config, smoke=True)})
        protocol = dict(referenceRequirementsSha256='a'*64, referenceVenvMaxBytes=100)
        environment = dict(versions=config['runtimeVersions'], requirementsSha256='a'*64, referenceVenvBytes=100)
        with patch.object(a, 'git_bytes', return_value=json.dumps(preflight).encode()):
            result = a.verify_recorded_environment(1, protocol, environment, config)
            self.assertTrue(result['frozenPreflightVerified'])
            self.assertEqual(result['replayVersions'], config['runtimeVersions'])
            for changed in (dict(config, smoke=True), dict(config, runtimeVersions={'reference': {'numpy': 'other'}})):
                with self.assertRaises(ValueError):
                    a.verify_recorded_environment(1, protocol, environment, changed)

    def test_environment_rejects_version_requirements_and_budget_drift(self):
        config = dict(smoke=False, runtimeVersions={'reference': {'numpy': 'pinned'}})
        preflight = dict(smokeIdentities={'1': dict(config, smoke=True)})
        protocol = dict(referenceRequirementsSha256='a'*64, referenceVenvMaxBytes=100)
        good = dict(versions=config['runtimeVersions'], requirementsSha256='a'*64, referenceVenvBytes=50)
        changes = [dict(good, versions={}), dict(good, requirementsSha256='b'*64)]
        changes += [dict(good, referenceVenvBytes=size) for size in (0, -1, 101, True, 50.)]
        with patch.object(a, 'git_bytes', return_value=json.dumps(preflight).encode()):
            for changed in changes:
                with self.subTest(changed=changed), self.assertRaises(ValueError):
                    a.verify_recorded_environment(1, protocol, changed, config)

    def test_replica_scope_is_literal(self):
        for invalid in (True, False, 0, 3, '1', 1.):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                a.replica_id(invalid)
        self.assertEqual(a.run_name(1), a.GROUP + '-continuation-r1')
        self.assertEqual(a.run_name(2, True), a.GROUP + '-r2')

    def test_immutable_pin(self):
        for invalid in ('main', 'A'*40, 'a'*39, '../bad', None):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                a.immutable(invalid)
        self.assertEqual(a.immutable('a'*40), 'a'*40)

    def test_full_whitelist_independent_matches_json_auditor(self):
        self.assertEqual(a.complete_names(), j.expected_names())
        self.assertEqual(len(a.snapshot_names()), 88)
        self.assertEqual(len(a.snapshot_names(True)), 86)

    def test_safe_names(self):
        for name in ('../x', '/x', 'a/../b', 'a//b', 'a/./b', 'a\\b', '.', '', 'a/'):
            with self.subTest(name=name), self.assertRaises(ValueError):
                a.safe_name(name)
        a.safe_name('expert/last.pt')

    def test_json_duplicate_nonfinite_and_overflow(self):
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory) / 'x.json'
            for raw in ('{"x":1,"x":2}', '{"x":NaN}', '{"x":1e400}', '{"x":Infinity}'):
                p.write_text(raw)
                with self.subTest(raw=raw), self.assertRaises(ValueError):
                    a.read(p)
            p.write_text('{}')
            with self.assertRaises(ValueError):
                a.read(p, 1)

    def test_evidence_never_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory) / 'out/evidence.json'
            h = a.write_new(p, {'a': 1})
            self.assertEqual(h, a.write_new(p, {'a': 1}))
            with self.assertRaisesRegex(ValueError, 'Existing different'):
                a.write_new(p, {'a': 2})

    def test_restore_rejects_symlink_ancestors_and_descendants(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'outside').mkdir()
            (root / 'linked').symlink_to(root / 'outside', target_is_directory=True)
            with self.assertRaises(ValueError):
                a.restore_safety(root / 'linked/new', set())
            base = root / 'base'; base.mkdir()
            (base / 'expert').symlink_to(root / 'outside', target_is_directory=True)
            with self.assertRaises(ValueError):
                a.restore_safety(base, {'expert/config.json'})

    def test_restore_rejects_unexpected_descendants(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); (root / 'unexpected').write_text('x')
            with self.assertRaises(ValueError):
                a.restore_safety(root, {'artifacts.json'})

    def test_snapshot_metadata_rejects_each_attack(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); manifest = manifest_fixture(root); remote = FakeRemote(root)
            good = remote.entries
            self.assertEqual(len(a.snapshot_metadata(manifest, good, remote.prefix)), 89)
            cases = [good[:-1], good + [good[0]], [NS(**dict(vars(e), size=True)) for e in good],
                     [NS(**dict(vars(e), size=a.FILE_LIMIT + 1)) for e in good],
                     [NS(**dict(vars(e), size=a.FILE_LIMIT)) for e in good],
                     [NS(**dict(vars(e), path=e.path.replace(remote.prefix, '../'))) for e in good]]
            for bad in cases:
                with self.subTest(size=len(bad)), self.assertRaises(ValueError):
                    a.snapshot_metadata(manifest, bad, remote.prefix)
            with self.assertRaises(ValueError):
                a.snapshot_metadata(dict(manifest, evil='a'*64), good, remote.prefix)
            with self.assertRaises(ValueError):
                a.snapshot_metadata(dict(manifest, **{'expert/last.pt': 'x'*64}), good, remote.prefix)

    def test_lfs_pointer_content_and_size_authenticated_before_payloads(self):
        from audit_neural import git_blob
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); manifest = manifest_fixture(root); remote = FakeRemote(root)
            entry = next(e for e in remote.entries if e.path.endswith('last.pt'))
            entry.lfs = NS(size=entry.size, sha256=manifest['expert/last.pt'])
            pointer = (f'version https://git-lfs.github.com/spec/v1\noid sha256:{entry.lfs.sha256}'
                       f'\nsize {entry.size}\n').encode()
            entry.blob_id = git_blob(pointer)
            a.snapshot_metadata(manifest, remote.entries, remote.prefix)
            for key, value in (('blob_id', 'd'*40), ('lfs', NS(size=entry.size + 1, sha256=entry.lfs.sha256)),
                               ('lfs', NS(size=entry.size, sha256='c'*64))):
                original = getattr(entry, key); setattr(entry, key, value)
                with self.subTest(key=key), self.assertRaises(ValueError):
                    a.snapshot_metadata(manifest, remote.entries, remote.prefix)
                setattr(entry, key, original)

    def test_metadata_budget_before_any_payload(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); manifest_fixture(root); remote = FakeRemote(root)
            for e in remote.entries:
                if e.path.endswith('last.pt'):
                    e.size = a.FILE_LIMIT + 1
            with self.assertRaises(ValueError):
                a.authenticate_snapshot(1, 'f'*40, root, remote)
            self.assertEqual(remote.got, [remote.prefix + 'artifacts.json'])

    def test_local_snapshot_authentication_without_download(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); manifest_fixture(root); remote = FakeRemote(root)
            report = a.authenticate_snapshot(1, 'f'*40, root, remote)
            self.assertEqual(report['files'], 89)
            self.assertEqual(report['manifestSha256'], a.digest(root / 'artifacts.json'))

    def test_fetch_restore_is_not_symlink_copy(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); source = root / 'source'; source.mkdir()
            manifest_fixture(source); remote = FakeRemote(source)
            destination = root / 'out/restored'
            a.authenticate_snapshot(1, 'f'*40, destination, remote, download=True)
            self.assertEqual(len(list(p for p in destination.rglob('*') if p.is_file())), 89)
            self.assertFalse(any(p.is_symlink() for p in destination.rglob('*')))

    def test_snapshot_existing_corrupt_file_is_not_replaced(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); source = root / 'source'; source.mkdir()
            manifest_fixture(source); remote = FakeRemote(source)
            destination = root / 'dest'; manifest_fixture(destination)
            path = destination / 'expert/last.pt'; path.write_bytes(b'wrong')
            with self.assertRaises(ValueError):
                a.authenticate_snapshot(1, 'f'*40, destination, remote, download=True)
            self.assertEqual(path.read_bytes(), b'wrong')

    def test_local_snapshot_missing_requires_explicit_fetch(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); source = root / 'source'; source.mkdir()
            manifest_fixture(source); remote = FakeRemote(source)
            with self.assertRaises(ValueError):
                a.authenticate_snapshot(1, 'f'*40, root / 'missing', remote)
            self.assertEqual(remote.got, [])

    def test_committed_boundary_not_uploaded_manifest(self):
        initial = a.committed_names(transaction_boundary('initial', 0))
        self.assertNotIn('expert/warmup.pt', initial)
        self.assertNotIn('expert/confirmation-plan.json', initial)
        warmup = a.committed_names(transaction_boundary('warmup', 0))
        self.assertIn('expert/warmup.pt', warmup)
        self.assertNotIn('expert/train-1.json', warmup)
        train = a.committed_names(transaction_boundary('train', 9))
        self.assertIn('expert/selection-8.json', train)
        self.assertNotIn('expert/selection-16.json', train)
        self.assertNotIn('expert/train-10.json', train)
        complete_train = a.committed_names(transaction_boundary())
        self.assertNotIn('expert/confirmation-selected.json', complete_train)
        selected = a.committed_names(transaction_boundary(confirmations={'selected': {}}))
        self.assertIn('expert/confirmation-selected.json', selected)
        self.assertNotIn('expert/confirmation-teacher.json', selected)
        self.assertNotIn('expert/history.json', selected)
        self.assertNotIn('expert/best.pt', selected)

    def test_boundary_rejects_premature_confirmation_or_result(self):
        for saved in (transaction_boundary('train', 31, {'selected': {}}),
                      transaction_boundary(confirmations={'teacher': {}}),
                      dict(transaction_boundary(), result={}), transaction_boundary('initial', 1)):
            with self.subTest(saved=saved), self.assertRaises(ValueError):
                a.committed_names(saved)

    def test_inherited_uncommitted_file_can_change_committed_cannot(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); old = root / 'old'; final = root / 'final'
            saved = transaction_boundary('train', 1)
            saved['history'] = []
            names = a.committed_names(saved) | {'expert/history.json', 'expert/best.pt', 'expert/train-2.json'}
            old_manifest, final_manifest = {}, {}
            for name in names:
                for folder, manifest in ((old, old_manifest), (final, final_manifest)):
                    write(folder / name, [] if name.endswith('history.json') else {})
                    manifest[name] = a.digest(folder / name)
            write(final / 'expert/train-2.json', {'uncommittedReplay': True})
            final_manifest['expert/train-2.json'] = a.digest(final / 'expert/train-2.json')
            report = a.verify_inherited(old, final, saved, old_manifest, final_manifest)
            self.assertIn('expert/train-2.json', report['excludedUploadedFiles'])
            write(final / 'expert/train-1.json', {'changed': True})
            final_manifest['expert/train-1.json'] = a.digest(final / 'expert/train-1.json')
            with self.assertRaises(ValueError):
                a.verify_inherited(old, final, saved, old_manifest, final_manifest)

    def test_projection_comes_from_actual_metadata_and_bytes(self):
        saved = {k: None for k in a.PROJECTION_KEYS}
        saved['update'] = 17
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory) / 'last.pt'; p.write_bytes(b'unique synthetic bytes')
            projected = a.checkpoint_projection(saved, p)
            self.assertEqual(projected['update'], 17)
            self.assertEqual(projected['lastSha256'], hashlib.sha256(p.read_bytes()).hexdigest())
            saved['update'] = 32
            self.assertEqual(projected['update'], 17)

    def test_environment_is_fixed_not_caller_supplied(self):
        for replica in (1, 2):
            first = a.expected_environment(replica, 1)
            second = a.expected_environment(replica, 2)
            self.assertNotIn('RESUME_RUN', first)
            self.assertEqual(second['RESUME_REVISION'], a.PINS[replica]['original'])
            self.assertEqual(first['SOURCE_SHA256'], second['SOURCE_SHA256'])
            self.assertEqual(second['REPLICA_SEGMENT'], '2')
            self.assertNotIn('HF_TOKEN', second)

    def test_job_config_rejects_command_labels_env_mounts_without_dumping_secrets(self):
        receipt = dict(replica=1, segment=2, jobId='id')
        good = NS(id='id', environment=a.expected_environment(1, 2), docker_image=a.IMAGE,
                  flavor='cpu-upgrade', command=['fake-original'], arguments=[], volumes=[], space_id=None,
                  labels=a.expected_labels(1, 2))
        a.verify_job_config(good, receipt, good.command)
        for key, value in (('environment', {'HF_TOKEN': 'secret-that-must-not-leak'}), ('command', ['changed']),
                           ('labels', dict(good.labels, replica='2')), ('volumes', ['x']), ('space_id', 's'),
                           ('arguments', ['--smoke']), ('flavor', 'other')):
            bad = copy.deepcopy(good); setattr(bad, key, value)
            with self.subTest(key=key), self.assertRaises(ValueError) as exc:
                a.verify_job_config(bad, receipt, good.command)
            self.assertNotIn('secret-that-must-not-leak', str(exc.exception))

    def test_bounded_log_stream_stops_before_unbounded_read(self):
        with self.assertRaises(ValueError):
            a.bounded_log(['x' * a.LOG_LIMIT, 'never'])
        self.assertEqual(a.bounded_log(['a', 'b']), 'a\nb')

    def test_log_original_and_confirmation_only_resume(self):
        for replica in (1, 2):
            first = a.verify_log(synthetic_log(replica), replica, 1)
            final = a.verify_log(synthetic_log(replica, 2), replica, 2, 'f'*40)
            self.assertEqual(first['optimizationUpdates'], list(range(1, 33)))
            self.assertEqual(final['optimizationUpdates'], [])
            self.assertEqual(first['runtimeReady'], dict(stage='runtime-ready', revision='0'*40))
            self.assertEqual(final['runtimeReady'], first['runtimeReady'])

    def test_log_rejects_duplicate_or_unbound_production_boundary(self):
        good = synthetic_log(segment=2)
        ready = json.dumps(dict(stage='uploaded', label='runtime-ready', revision='0'*40))
        for bad in (good.replace(ready, ready + '\n' + ready),
                    good.replace(ready, ready.replace('0'*40, 'not-an-immutable-revision')),
                    good.replace(ready, '{"stage": "expert-ppo", "update": 999}\n' + ready),
                    good.replace(ready, '')):
            with self.subTest(log=bad[-100:]), self.assertRaises(ValueError):
                a.verify_log(bad, 1, 2, 'f'*40)

    def test_log_requires_node_success_before_python_startup_boundary(self):
        good = synthetic_log()
        for bad in (good.replace('# pass 7\n', '') + '\n# pass 7',
                    good + '\nRan 34 tests in 0.1s\n\nOK'):
            with self.assertRaises(ValueError):
                a.verify_log(bad, 1, 1)

    def test_all_upload_receipts_include_actual_runtime_ready(self):
        for segment in (1, 2):
            job = a.verify_log(synthetic_log(segment=segment), 1, segment, 'f'*40)
            status = dict(receipts=[job['runtimeReady'], *job['uploads'][:-1]])
            a.verify_upload_receipts(status, job)
            changed = copy.deepcopy(status)
            changed['receipts'][0]['revision'] = 'c'*40
            with self.assertRaisesRegex(ValueError, 'runtime-ready'):
                a.verify_upload_receipts(changed, job)
            with self.assertRaises(ValueError):
                a.verify_upload_receipts(dict(receipts=status['receipts'][1:]), job)

    def test_log_rejects_reoptimization_or_reselection(self):
        good = synthetic_log(segment=2)
        bad = good.replace('{"stage": "complete", "run":', '{"stage": "expert-ppo", "update": 1}\n{"stage": "complete", "run":')
        with self.assertRaises(ValueError):
            a.verify_log(bad, 1, 2, 'f'*40)
        bad = good.replace('confirmation-teacher', 'confirmation-selected')
        with self.assertRaises(ValueError):
            a.verify_log(bad, 1, 2, 'f'*40)

    def test_log_rejects_wrong_pin_missing_tests_and_wrong_boundary(self):
        for log in (synthetic_log().replace(a.PINS[1]['selection'], '9'*40),
                    synthetic_log().replace('Ran 34 tests', 'Ran 33 tests'),
                    synthetic_log().replace('runtime-ready', 'missing'),
                    synthetic_log().replace('# fail 0', '# fail 1')):
            with self.subTest(log=log[:20]), self.assertRaises(ValueError):
                a.verify_log(log, 1, 1)

    def test_log_cross_event_chronology_not_just_separate_label_lists(self):
        log = synthetic_log()
        lines = log.splitlines()
        index = next(i for i, line in enumerate(lines) if '"label": "update-32"' in line)
        lines[index], lines[index + 1] = lines[index + 1], lines[index]
        with self.assertRaisesRegex(ValueError, 'strictly before'):
            a.verify_log('\n'.join(lines), 1, 1)

    def jobs_fixture(self):
        receipts, jobs = {}, {}
        for replica in (1, 2):
            for segment in (1, 2):
                jid = a.PINS[replica]['originalJob' if segment == 1 else 'job']
                receipts[replica, segment] = dict(replica=replica, segment=segment, jobId=jid)
                jobs[jid] = NS(id=jid, environment=a.expected_environment(replica, segment), docker_image=a.IMAGE,
                    flavor='cpu-upgrade', command=['frozen'], arguments=[], volumes=[], space_id=None,
                    labels=a.expected_labels(replica, segment),
                    started_at='2026-01-01T00:00:00+00:00' if segment == 1 else '2026-01-01T04:00:00+00:00',
                    finished_at='2026-01-01T03:00:00+00:00' if segment == 1 else '2026-01-01T05:00:00+00:00',
                    status=NS(stage='ERROR' if segment == 1 else 'COMPLETED', message='Job timeout' if segment == 1 else ''))
        api = NS(list_jobs=lambda **kwargs: list(jobs.values()),
                 inspect_job=lambda job_id, **kwargs: jobs[job_id],
                 fetch_job_logs=lambda job_id, **kwargs: synthetic_log(
                     int(jobs[job_id].labels['replica']), int(jobs[job_id].labels['segment'])).splitlines())
        return receipts, jobs, api

    def test_four_actual_job_configs_and_nonoverlapping_chronology(self):
        receipts, jobs, api = self.jobs_fixture()
        with patch.object(a, 'frozen_command', return_value=['frozen']):
            report = a.verify_jobs(api, receipts, 1, 'f'*40)
        self.assertEqual(len(report['groupJobIds']), 4)
        self.assertEqual(len(report['targetJobs']), 2)
        self.assertNotIn('environment', report['targetJobs'][0])
        jobs[a.PINS[2]['job']].started_at = '2026-01-01T02:00:00+00:00'
        with patch.object(a, 'frozen_command', return_value=['frozen']), self.assertRaisesRegex(ValueError, 'overlap'):
            a.verify_jobs(api, receipts, 1, 'f'*40)

    def test_inventory_cannot_hide_fifth_job_duplicate_slot_or_missing_peer(self):
        for change in ('extra', 'missing', 'duplicate'):
            receipts, jobs, api = self.jobs_fixture()
            inventory = list(jobs.values())
            if change == 'extra':
                inventory.append(NS(id='replacement'))
            elif change == 'missing':
                inventory.pop()
            else:
                inventory[-1] = inventory[0]
            api.list_jobs = lambda **kwargs: inventory
            with patch.object(a, 'frozen_command', return_value=['frozen']), self.subTest(change=change), self.assertRaises(ValueError):
                a.verify_jobs(api, receipts, 1, 'f'*40)

    def test_original_success_cannot_authorize_replacement(self):
        receipts, jobs, api = self.jobs_fixture()
        jobs[a.PINS[2]['originalJob']].status.stage = 'COMPLETED'
        with patch.object(a, 'frozen_command', return_value=['frozen']), self.assertRaisesRegex(ValueError, 'replacement'):
            a.verify_jobs(api, receipts, 1, 'f'*40)

    def test_source_changes_only_named_nonserving_files(self):
        self.assertIsNone(a.local_source_difference('ai/multimap/expert_ppo.py', 'a', 'a'))
        self.assertIsNotNone(a.local_source_difference('ai/multimap/README.md', 'a', 'b'))
        for name in ('ai/multimap/expert_ppo.py', 'ai/multimap/expert_replicas_v1.py',
                     'ai/multimap/audit_expert.py', 'engine/dist/index.js', 'runtime/node'):
            with self.subTest(name=name), self.assertRaises(ValueError):
                a.local_source_difference(name, 'a', 'b')

    def test_no_game_without_explicit_opt_in(self):
        with self.assertRaisesRegex(ValueError, 'Explicit'):
            a.replay(1, Path('/nonexistent'), Path('/nonexistent'))

    def test_replay_exact_preregistered_scope_only_all_coverage(self):
        keys = ('map', 'players', 'variant', 'fastBid', 'deal', 'focalSeat')
        for replica in (1, 2):
            batches = a.replay_tasks(replica)
            self.assertEqual(len(batches), 16)
            for label in ('confirmation-selected', 'confirmation-teacher'):
                tasks = [batch[0] for stage, batch in batches if stage == label]
                self.assertEqual([tuple(s[k] for k in keys) for s in tasks], list(a.REPLAY_SCOPES))
                self.assertEqual({s['players'] for s in tasks}, set(range(2, 7)))
                self.assertEqual({s['map'] for s in tasks}, set(j.TRAIN_MAPS))
                self.assertEqual({(s['variant'], s['fastBid']) for s in tasks},
                                 {('original', False), ('original', True), ('recharged', False), ('recharged', True)})
                self.assertTrue(all(s['split'] == 'confirmation' and s['smoke'] is False for s in tasks))
                self.assertTrue(all(s.get('focalTeacher', False) == (label == 'confirmation-teacher') for s in tasks))

    def test_helper_git_and_hash_binding(self):
        with patch.object(a, 'git_bytes', return_value=b'tampered'):
            with self.assertRaisesRegex(ValueError, 'Frozen helper'):
                a.authenticate_helpers()

    def test_frozen_bootstrap_parsed_from_git_without_execution(self):
        source = b"BOOTSTRAP = 'literal; not executed'\nraise RuntimeError('must not execute')\n"
        with patch.object(a, 'git_bytes', return_value=source):
            result = a.frozen_command()
        self.assertEqual(result[:2], ['bash', '-lc'])
        self.assertIn('huggingface_hub==1.29.0', result[2])
        self.assertIn('literal; not executed', result[2])

    def test_cached_pin_never_downloads_when_absent(self):
        fake_hub = NS(try_to_load_from_cache=lambda *args, **kwargs: None)
        remote = NS(get=lambda *args, **kwargs: self.fail('get called with cache absent'))
        with patch.dict(sys.modules, huggingface_hub=fake_hub):
            with self.assertRaisesRegex(ValueError, 'not cached'):
                a.cached_pin(remote, dict(repo='x', path='y', revision='f'*40))


@unittest.skipUnless(HAS_TORCH, 'Candidate venv required for synthetic tensor fixtures')
class TensorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import torch
        cls.torch = torch
        cls.old_threads = torch.get_num_threads()
        torch.set_num_threads(1)

    @classmethod
    def tearDownClass(cls):
        cls.torch.set_num_threads(cls.old_threads)

    def optimizer_fixture(self, stage='train'):
        torch = self.torch
        model = torch.nn.Linear(2, 1)
        protocol = dict(learningRate=.0001, warmupLearningRate=.0003, weightDecay=.001)
        optimizer = torch.optim.AdamW(model.parameters(), lr=protocol['learningRate' if stage == 'train' else 'warmupLearningRate'], weight_decay=.001)
        if stage != 'initial':
            # Analytic synthetic moments, not optimization or a game/model forward.
            state = optimizer.state_dict()
            for i, parameter in zip(state['param_groups'][0]['params'], model.parameters()):
                state['state'][i] = dict(step=torch.tensor(1.), exp_avg=torch.zeros_like(parameter), exp_avg_sq=torch.ones_like(parameter))
        else:
            state = optimizer.state_dict()
        history = [] if stage == 'initial' else [dict(stage='warmup', update=0, optimization=dict(optimizerSteps=1))]
        if stage == 'train':
            history.append(dict(stage='train', update=1, optimization=dict(optimizerSteps=1)))
        saved = dict(stage=stage, update=1 if stage == 'train' else 0, history=history,
                     optimizer=state, torchRng=torch.get_rng_state(), pythonRng=random.Random(123).getstate())
        return saved, model, protocol

    def test_complete_optimizer_valid_all_stages(self):
        for stage in ('initial', 'warmup', 'train'):
            saved, model, protocol = self.optimizer_fixture(stage)
            a.verify_optimizer(saved, model, protocol)

    def test_optimizer_rejects_missing_extra_parameters(self):
        for extra in (False, True):
            saved, model, protocol = self.optimizer_fixture()
            if extra:
                saved['optimizer']['state'][99] = copy.deepcopy(saved['optimizer']['state'][0])
            else:
                saved['optimizer']['state'].pop(0)
            with self.subTest(extra=extra), self.assertRaises(ValueError):
                a.verify_optimizer(saved, model, protocol)

    def test_optimizer_rejects_group_recipe_type_and_order_changes(self):
        for key, value in (('lr', .1), ('weight_decay', 0.), ('amsgrad', True), ('params', [1, 0]), ('foreach', False)):
            saved, model, protocol = self.optimizer_fixture()
            saved['optimizer']['param_groups'][0][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                a.verify_optimizer(saved, model, protocol)

    def test_optimizer_rejects_nonfinite_negative_wrong_shape_dtype_and_step(self):
        torch = self.torch
        mutations = [('exp_avg', torch.full((1, 2), float('nan'))),
                     ('exp_avg_sq', -torch.ones(1, 2)), ('exp_avg', torch.zeros(2)),
                     ('exp_avg', torch.zeros(1, 2, dtype=torch.float64)), ('step', torch.tensor(2.)),
                     ('step', torch.tensor(float('inf'))), ('step', torch.tensor([1.])), ('step', torch.tensor(1))]
        for key, value in mutations:
            saved, model, protocol = self.optimizer_fixture()
            saved['optimizer']['state'][0][key] = value
            with self.subTest(key=key, shape=value.shape), self.assertRaises(ValueError):
                a.verify_optimizer(saved, model, protocol)

    def test_optimizer_rejects_invalid_rng_and_history(self):
        for key, value in (('torchRng', self.torch.tensor([1], dtype=self.torch.int64)),
                           ('pythonRng', ()), ('history', [])):
            saved, model, protocol = self.optimizer_fixture()
            saved[key] = value
            with self.subTest(key=key), self.assertRaises((ValueError, TypeError, IndexError)):
                a.verify_optimizer(saved, model, protocol)

    def test_finite_model_requires_all_exact_keys_shapes_types(self):
        torch = self.torch
        expected = dict(a=torch.zeros(2))
        a.finite_state(expected, expected)
        for state in ({}, dict(a=torch.ones(3)), dict(a=torch.ones(2, dtype=torch.float64)),
                      dict(a=torch.tensor([0., float('nan')])), dict(a=torch.zeros(2), b=torch.zeros(2))):
            with self.subTest(state=state), self.assertRaises(ValueError):
                a.finite_state(state, expected)

    def model_file(self, path):
        from expert_policy import ExpertPolicy, save
        model = ExpertPolicy(64, 16)
        config = {'protocol': dict(learningRate=.0001, warmupLearningRate=.0003, weightDecay=.001)}
        save(path, model, stage='initial', update=0, config=config)
        return config

    def test_actual_checkpoint_projection_loads_finite_tensors_and_preserves_rng(self):
        torch = self.torch
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory) / 'initial.pt'; config = self.model_file(p)
            before = torch.get_rng_state().clone()
            saved = a.load_checkpoint(p, config)
            self.assertEqual(saved['width'], 64)
            self.assertTrue(torch.equal(before, torch.get_rng_state()))

    def test_checkpoint_rejects_nonfinite_unknown_field_wrong_architecture_and_config(self):
        torch = self.torch
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory) / 'initial.pt'; config = self.model_file(p)
            original = torch.load(p, weights_only=True)
            cases = [dict(original, width=32), dict(original, priorAsActionFeature=1), dict(original, unknown=True),
                     dict(original, config={'wrong': True}), dict(original, stage='bad'), dict(original, update=True)]
            bad = copy.deepcopy(original); next(iter(bad['state_dict'].values())).flatten()[0] = float('nan'); cases.append(bad)
            for saved in cases:
                torch.save(saved, p)
                with self.subTest(keys=list(saved)), self.assertRaises(ValueError):
                    a.load_checkpoint(p, config)

    def test_exact_one_constructor_rng_chain_and_preserves_callers_rng(self):
        torch = self.torch
        from expert_policy import load
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory) / 'best.pt'; self.model_file(p)
            before = dict(confirmations={}, result=None, torchRng=torch.get_rng_state().clone(),
                          model=dict(a=torch.zeros(2)), optimizer=dict(a=torch.ones(2)), pythonRng=random.Random(1).getstate())
            after = copy.deepcopy(before)
            with torch.random.fork_rng(devices=[]):
                torch.set_rng_state(before['torchRng']); load(p)
                after['torchRng'] = torch.get_rng_state()
            after['confirmations'] = {'selected': {'sha256': 'a'*64}}
            current = torch.get_rng_state().clone()
            a.unchanged_transaction(before, after, p)
            self.assertTrue(torch.equal(current, torch.get_rng_state()))
            for mutate in ('zero-advance', 'two-advances', 'optimizer', 'pythonRng'):
                bad = copy.deepcopy(after)
                if mutate == 'zero-advance':
                    bad['torchRng'] = before['torchRng']
                elif mutate == 'two-advances':
                    with torch.random.fork_rng(devices=[]):
                        torch.set_rng_state(after['torchRng']); load(p); bad['torchRng'] = torch.get_rng_state()
                elif mutate == 'optimizer':
                    bad['optimizer']['a'][0] = 2
                else:
                    bad['pythonRng'] = random.Random(2).getstate()
                with self.subTest(mutate=mutate), self.assertRaises(ValueError):
                    a.unchanged_transaction(before, bad, p)

    def test_replay_tasks_pass_unmodified_replica_guard(self):
        from expert_replicas_v1 import Replica
        for replica in (1, 2):
            runner = Replica(replica)
            for _, tasks in a.replay_tasks(replica):
                runner.validate_tasks(tasks, 'evaluation', False, runner.protocol)

    def chain_fixture(self, directory, replica=1):
        """Entire synthetic nine-checkpoint chain; no stored study tensors.

        Only this NEW auditor's literal PINS are privately patched by the test.
        Frozen expert functions get private FunctionType bindings, not globals.
        """
        torch = self.torch
        import audit_expert
        from model import GraphPolicy, SCHEMA
        from expert_policy import warm_start, save, load
        root = Path(directory); final = root / 'final'; old = root / 'old'
        warm_path = root / 'representation.pt'
        torch.save(dict(schema=SCHEMA, width=64, state_dict=GraphPolicy(64).state_dict()), warm_path)
        protocol = j.protocol_for(replica)
        protocol['warmStart']['sha256'] = a.digest(warm_path)
        config = dict(protocol=protocol, syntheticFixture=True)
        model = audit_expert.reuse(warm_start, PROTOCOL=protocol)(warm_path)
        for base in (old, final):
            for name in a.snapshot_names(base == old):
                if name.endswith('.json'):
                    write(base / name, {})
            write(base / 'expert/config.json', config)
        save(final / 'expert/initial.pt', model, stage='initial', update=0, config=config)
        save(final / 'expert/warmup.pt', model, stage='warmup', update=0, config=config)
        best_update = 24 if replica == 1 else 32
        save(final / 'expert/best.pt', model, stage='train', update=best_update, config=config)
        for name in ('initial', 'warmup', 'best'):
            (old / f'expert/{name}.pt').write_bytes((final / f'expert/{name}.pt').read_bytes())
        history = [dict(stage='warmup', update=0, optimization=dict(optimizerSteps=1))]
        history += [dict(stage='train', update=u, optimization=dict(optimizerSteps=1)) for u in range(1, 33)]
        for base in (old, final):
            write(base / 'expert/history.json', history)
        optimizer = torch.optim.AdamW(model.parameters(), lr=protocol['learningRate'], weight_decay=protocol['weightDecay']).state_dict()
        for index, parameter in zip(optimizer['param_groups'][0]['params'], model.parameters()):
            optimizer['state'][index] = dict(step=torch.tensor(32.), exp_avg=torch.zeros_like(parameter), exp_avg_sq=torch.ones_like(parameter))
        outcomes = [dict(spec=dict(cell='Germany|2|original|0'), credit=.5)]
        scores = j.summary(outcomes)
        for base in (old, final):
            write(base / 'expert/confirmation-selected.json', dict(games=outcomes, summary=scores))
        write(final / 'expert/confirmation-teacher.json', dict(games=outcomes, summary=scores))
        best_bytes = (final / 'expert/best.pt').read_bytes()
        extra = dict(stage='train', update=32, config=config, optimizer=optimizer, torchRng=torch.get_rng_state(),
                     pythonRng=random.Random(123).getstate(), history=history, bestUpdate=best_update, bestStage='train',
                     bestScore=.5, baseline=scores, bestArtifact=best_bytes, bestSha256=a.sha(best_bytes), confirmations={}, result=None)
        selection = root / 'selection.pt'
        save(selection, model, **extra)
        with torch.random.fork_rng(devices=[]):
            torch.set_rng_state(extra['torchRng']); load(final / 'expert/best.pt'); extra['torchRng'] = torch.get_rng_state()
        extra['confirmations'] = dict(selected=dict(summary=scores, sha256=a.digest(old / 'expert/confirmation-selected.json')))
        save(old / 'expert/last.pt', model, **extra)
        with torch.random.fork_rng(devices=[]):
            torch.set_rng_state(extra['torchRng']); load(final / 'expert/best.pt'); extra['torchRng'] = torch.get_rng_state()
        extra['confirmations']['teacher'] = dict(summary=scores, sha256=a.digest(final / 'expert/confirmation-teacher.json'))
        extra['result'] = dict(syntheticFixture=True)
        write(final / 'expert/result.json', extra['result'])
        save(final / 'expert/last.pt', model, **extra)
        for base in (old, final):
            write(base / 'artifacts.json', {p.relative_to(base).as_posix(): a.digest(p) for p in base.rglob('*')
                                          if p.is_file() and p.name != 'artifacts.json'})
        pins = copy.deepcopy(a.PINS)
        pins[replica]['bestSha256'] = a.sha(best_bytes)
        helpers = {'audit_expert': audit_expert, 'audit_expert_replicas_v1': j}
        return (replica, final, old, selection, warm_path, helpers), pins

    def test_full_synthetic_chain_two_replicas_actual_projections_and_json_gate(self):
        for replica in (1, 2):
            with self.subTest(replica=replica), tempfile.TemporaryDirectory() as directory:
                args, pins = self.chain_fixture(directory, replica)
                with patch.object(a, 'PINS', pins):
                    report = a.verify_checkpoint_chain(*args)
                self.assertEqual(report['finiteModelCheckpoints'], 9)
                self.assertEqual(report['constructorAdvances'], {'selectionToOriginal': 1, 'originalToContinuation': 1})
                self.assertEqual(report['finalCheckpoint']['lastSha256'], a.digest(args[1] / 'expert/last.pt'))
                self.assertEqual(report['selectionCommit']['projection']['confirmations'], {})
                self.assertNotIn('expert/confirmation-teacher.json', report['inherited']['files'])
                # EXPLICIT synthetic contract test, not a production attestation.
                receipt = dict(schema='multimap-expert-replica-external-integrity-v1', replica=replica,
                    manifestSha256='a'*64, evidenceSha256='b'*64, checks=dict.fromkeys(j.EXTERNAL_CHECKS, True),
                    finalCheckpoint=report['finalCheckpoint'], selectionCommit=report['selectionCommit'])
                j._external_gate(receipt, replica, 'a'*64, report['finalCheckpoint'], pins[replica]['selection'])
                bad = copy.deepcopy(receipt); bad['selectionCommit']['projection']['lastSha256'] = 'c'*64
                with self.assertRaises(ValueError):
                    j._external_gate(bad, replica, 'a'*64, report['finalCheckpoint'])

    def test_full_chain_rejects_embedded_best_metadata_and_postselection_model_changes(self):
        for changed in ('bestArtifact', 'state_dict', 'optimizer', 'history', 'confirmations'):
            with self.subTest(changed=changed), tempfile.TemporaryDirectory() as directory:
                args, pins = self.chain_fixture(directory)
                path = args[1] / 'expert/last.pt'
                saved = self.torch.load(path, weights_only=True)
                if changed == 'bestArtifact':
                    saved[changed] = saved[changed] + b'changed'
                elif changed == 'state_dict':
                    next(iter(saved[changed].values())).flatten()[0] += .01
                elif changed == 'optimizer':
                    saved[changed]['state'][0]['exp_avg'].flatten()[0] = .25
                elif changed == 'history':
                    saved[changed][0]['optimization']['optimizerSteps'] = 2
                else:
                    saved[changed]['selected']['sha256'] = 'c'*64
                self.torch.save(saved, path)
                with patch.object(a, 'PINS', pins), self.assertRaises(ValueError):
                    a.verify_checkpoint_chain(*args)

    def test_private_binding_does_not_mutate_old_helpers(self):
        from audit_expert import reuse
        import audit_neural
        old = audit_neural.SOURCE
        bound = reuse(audit_neural.git_bytes, SOURCE='f'*40)
        self.assertEqual(bound.__globals__['SOURCE'], 'f'*40)
        self.assertEqual(audit_neural.SOURCE, old)


if __name__ == '__main__':
    unittest.main()
