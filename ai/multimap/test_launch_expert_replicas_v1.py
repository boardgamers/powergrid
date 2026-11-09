"""Offline launcher admission/recovery tests. All HF/storage/package calls mocked."""
import copy
from contextlib import ExitStack, redirect_stdout
import io
import json
import os
from pathlib import Path
import random
import tarfile
import tempfile
from types import SimpleNamespace as NS
import unittest
from unittest.mock import Mock, patch

import torch
import launch_expert_replicas_v1 as launch
from data import atomic_json, digest
from expert_policy import ExpertPolicy, save
from expert_replicas_v1 import BASE, STUDY

GROUP = 'multimap-expert-replicas-20261109-v1'
COMMIT = 'a' * 40
SOURCE_REVISION = 'b' * 40
RESUME_REVISION = 'c' * 40
HERE = Path(__file__).resolve().parent


class LauncherTests(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.root = Path(self.stack.enter_context(tempfile.TemporaryDirectory()))
        self.directory = self.root / 'ai/runs' / GROUP
        self.directory.parent.mkdir(parents=True)
        self.source_files = {
            launch.LAUNCHER_NAME: (HERE / 'launch_expert_replicas_v1.py').read_bytes(),
            'ai/multimap/test_launch_expert_replicas_v1.py': Path(__file__).read_bytes(),
            'ai/multimap/requirements-cpu.txt': b'# frozen requirements fixture\n',
            'ai/multimap/expert-replicas-protocol-v1.json': (HERE / 'expert-replicas-protocol-v1.json').read_bytes(),
        }
        for name, content in self.source_files.items():
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
        self.identities = {}
        for number in (1, 2):
            protocol = copy.deepcopy(BASE)
            protocol.update(seed=STUDY['replicas'][number - 1]['seed'],
                            seedNamespace=STUDY['replicas'][number - 1]['seedNamespace'], transferMaps=[])
            self.identities[str(number)] = dict(schema='multimap-expert-replica-identity-v1', replica=number,
                protocol=protocol, smoke=True, replicaStudy=copy.deepcopy(STUDY),
                sourceFiles={n: launch.sha_bytes(v) for n, v in self.source_files.items()},
                execution=dict(workers=6), referenceManifestSha256='d' * 64,
                runtimeVersions={'fixture': 'frozen-runtime'})
        self.preflight = dict(schema='multimap-expert-replicas-preflight-v1', allChecksPassed=True,
            protocolSha256=digest(self.root / 'ai/multimap/expert-replicas-protocol-v1.json'),
            smokeIdentities=self.identities, totalTerminalGames=264, exactTerminalAndCounterReplayMatches=132,
            failures=0, interruptedAfterUpdate=1, completedCommittedWorkPreserved=True,
            deliberatelyCorruptedBestRepaired=True, completedResumePerformsNoCollection=True,
            onlySmokeRoots=True, reusedReferenceArtifact=True, productionGamesExecuted=0,
            qualified=False, qualificationEligible=False, reservedFinalSeedsUsed=False,
            results={str(number): dict(exactTerminalAndCounterReplayMatches=66,
                exactModelOptimizerRngAndHistory=True) for number in (1, 2)})
        atomic_json(self.root / launch.PREFLIGHT_NAME, self.preflight)
        self.jobs, self.remote = {}, {}
        self.remote_paths = set()
        self.events = []
        self.fail_job = None
        self.omit_job = None
        self.api = Mock()
        self.api.model_info.return_value = NS(private=True)
        self.api.dataset_info.return_value = NS(private=True)
        self.api.file_exists.return_value = False
        self.api.list_repo_tree.side_effect = self.list_repo_tree
        self.api.list_jobs.side_effect = lambda **kw: list(self.jobs.values())
        self.api.inspect_job.side_effect = lambda job_id, **kw: self.jobs[job_id]
        self.api.run_job.side_effect = self.run_job
        self.api.upload_file.side_effect = self.upload
        self.mock(launch, 'ROOT', self.root)
        self.mock(launch, 'PROTOCOL_PATH', self.root / 'ai/multimap/expert-replicas-protocol-v1.json')
        self.mock(launch, 'HfApi', Mock(return_value=self.api))
        self.mock(launch, 'get_token', Mock(return_value='SECRET-ONLY-IN-API'))
        self.storage = self.mock(launch, 'check_local_storage', Mock())
        self.package = self.mock(launch, 'package', Mock(side_effect=self.make_package))
        self.mock(launch, 'hf_hub_download', Mock(side_effect=self.download))
        self.mock(launch, 'remote_size', Mock(side_effect=self.remote_size))
        self.mock(launch.subprocess, 'check_output', Mock(side_effect=self.git))
        self.replica = self.mock(launch, 'Replica', Mock(side_effect=self.replica_identity))
        self.stack.enter_context(redirect_stdout(io.StringIO()))

    def mock(self, module, name, value):
        return self.stack.enter_context(patch.object(module, name, value))

    def git(self, args, **kwargs):
        if args[1] == 'status':
            return ''
        if args[1] == 'rev-parse':
            return COMMIT + '\n'
        if args[1] == 'show':
            self.assertEqual(args[2], COMMIT + ':' + launch.LAUNCHER_NAME)
            return self.source_files[launch.LAUNCHER_NAME].decode()
        raise AssertionError(args)

    def replica_identity(self, number):
        def config(smoke, protocol, **kwargs):
            self.assertIs(smoke, True)
            self.assertEqual(kwargs['workers'], 6)
            return copy.deepcopy(self.identities[str(number)])
        return NS(protocol=self.identities[str(number)]['protocol'], config=config)

    def list_repo_tree(self, repo, path_in_repo, **kwargs):
        if path_in_repo in self.remote_paths:
            return iter([NS(path=path_in_repo + '/anything')])
        raise launch.EntryNotFoundError('not found')

    def make_package(self, directory):
        files = dict(self.source_files)
        files[launch.PREFLIGHT_NAME] = (self.root / launch.PREFLIGHT_NAME).read_bytes()
        manifest = dict(gitCommit=COMMIT, files={n: launch.sha_bytes(v) for n, v in files.items()})
        files['source-manifest.json'] = json.dumps(manifest).encode()
        path = Path(directory) / 'source.tgz'
        with tarfile.open(path, 'w:gz') as archive:
            for name, content in files.items():
                member = tarfile.TarInfo(name)
                member.size = len(content)
                archive.addfile(member, io.BytesIO(content))
        return path, COMMIT

    def upload(self, repo_id, path_in_repo, path_or_fileobj, **kwargs):
        self.assertTrue((self.directory / 'intent.json').is_file())
        self.remote[repo_id, path_in_repo, SOURCE_REVISION] = Path(path_or_fileobj)
        return NS(oid=SOURCE_REVISION)

    def run_job(self, **kwargs):
        replica = int(kwargs['labels']['replica'])
        segment = int(kwargs['labels']['segment'])
        intent = self.directory / 'intents' / f'r{replica}-s{segment}.json'
        self.assertTrue(intent.exists())
        self.assertEqual(launch.read(intent)['env'], kwargs['env'])
        self.assertTrue((self.directory.parent / kwargs['name'] / 'intent.json').exists())
        self.assertEqual(kwargs['secrets'], {'HF_TOKEN': 'SECRET-ONLY-IN-API'})
        self.assertNotIn('SECRET-ONLY-IN-API', json.dumps({k: v for k, v in kwargs.items() if k != 'secrets'}))
        number = len(self.jobs) + 1
        job = NS(id='job' + str(number), environment=kwargs['env'], docker_image=kwargs['image'],
                 command=kwargs['command'], arguments=[], flavor=kwargs['flavor'],
                 status=NS(stage='RUNNING'), labels=kwargs['labels'], volumes=None, space_id=None)
        if number != self.omit_job:
            self.jobs[job.id] = job
        if self.fail_job == number:
            raise TimeoutError('uncertain submission')
        return job

    def download(self, repo, name, revision, **kwargs):
        self.events.append(('download', name))
        # Real HF caches return snapshot paths linked to content-addressed blobs.
        cache = Path(kwargs['cache_dir'])
        kind = 'datasets' if kwargs.get('repo_type') == 'dataset' else 'models'
        repository = cache / (kind + '--' + repo.replace('/', '--'))
        content = self.remote[repo, name, revision].read_bytes()
        blob = repository / 'blobs' / launch.sha_bytes(content)
        blob.parent.mkdir(parents=True, exist_ok=True)
        blob.write_bytes(content)
        snapshot = repository / 'snapshots' / revision / name
        snapshot.parent.mkdir(parents=True, exist_ok=True)
        snapshot.symlink_to(os.path.relpath(blob, snapshot.parent))
        return str(snapshot)

    def remote_size(self, repo, name, revision, maximum=launch.LIMIT, **kwargs):
        self.events.append(('metadata', name))
        size = self.remote[repo, name, revision].stat().st_size
        if size > maximum:
            raise ValueError('fixture size guard')
        return size

    def start(self):
        return launch.launch(GROUP, self.directory)

    def receipt_path(self, replica=1):
        return self.directory.parent / (GROUP + '-r' + str(replica)) / 'launch.json'

    def snapshot(self, replica=1):
        base = self.root / ('snapshot' + str(replica))
        training = base / 'expert'
        training.mkdir(parents=True)
        identity = copy.deepcopy(self.identities[str(replica)])
        identity['smoke'] = False
        atomic_json(training / 'config.json', identity)
        model = ExpertPolicy()
        optimizer = torch.optim.AdamW(model.parameters(), lr=identity['protocol']['warmupLearningRate'],
                                      weight_decay=identity['protocol']['weightDecay'])
        save(training / 'initial.pt', model, config=identity, stage='initial', update=0)
        save(training / 'best.pt', model, config=identity, stage='initial', update=0)
        best = (training / 'best.pt').read_bytes()
        save(training / 'last.pt', model, config=identity, stage='initial', update=0,
             optimizer=optimizer.state_dict(), torchRng=torch.get_rng_state(), pythonRng=random.getstate(),
             history=[], baseline=dict(failures=0), bestArtifact=best, bestSha256=launch.sha_bytes(best),
             bestStage='initial', bestUpdate=0, bestScore=.29, confirmations={}, result=None)
        source = launch.read(self.directory / 'source.json')
        atomic_json(base / 'status.json', dict(run=GROUP + '-r' + str(replica), workers=6, smoke=False,
            protocol=identity['protocol'], sourceRepo=launch.DATASET, sourcePath=source['sourcePath'],
            sourceRevision=source['sourceRevision'], sourceSha256=source['sourceSha256']))
        atomic_json(base / 'protocol.json', identity['protocol'])
        atomic_json(base / 'environment.json', dict(requirementsSha256=identity['protocol']['referenceRequirementsSha256'],
                                                  versions=identity['runtimeVersions']))
        reference = identity['protocol']['reference']
        atomic_json(base / 'recovery.json', dict(exactServiceReady=True,
            runtimeManifestSha256=identity['referenceManifestSha256'], policySha256=reference['policySha256'],
            pins=dict(source=reference['sourcePin'], model=reference['modelPin']), omitted=[]))
        self.publish_snapshot(base, replica)
        self.jobs['job' + str(replica)].status.stage = 'ERROR'
        return base

    def publish_snapshot(self, base, replica=1):
        manifest = {p.relative_to(base).as_posix(): digest(p) for p in base.rglob('*')
                    if p.is_file() and p.name != 'artifacts.json'}
        atomic_json(base / 'artifacts.json', manifest)
        for path in base.rglob('*'):
            if path.is_file():
                name = f'runs/{GROUP}-r{replica}/' + path.relative_to(base).as_posix()
                self.remote[launch.MODEL, name, RESUME_REVISION] = path

    def resume(self, replica=1, **kwargs):
        return launch.continue_replica(self.receipt_path(replica), GROUP + '-continuation-r' + str(replica),
                                       revision=RESUME_REVISION, **kwargs)

    def test_two_jobs_same_archive_bounded_recipe_secret_only_api(self):
        records = self.start()
        self.assertEqual(len(records), 2)
        self.assertEqual(self.package.call_count, 1)
        self.assertEqual(self.api.upload_file.call_count, 1)
        self.assertEqual(records[0]['source'], records[1]['source'])
        for number, record in enumerate(records, 1):
            self.assertEqual(record['segment'], 1)
            self.assertEqual(record['env']['EXPERT_REPLICA'], str(number))
            self.assertEqual(record['env']['REPLICA_SEGMENT'], '1')
            self.assertEqual(record['env']['EXPERT_WORKERS'], '6')
            self.assertEqual(record['env']['EXPERT_SMOKE'], '0')
            self.assertEqual(record['plannedGames'], 6240)
            self.assertEqual(record['maxTotalJobHours'], 12)
            self.assertEqual(record['timeout'], '3h')
            for name in launch.THREAD_ENV:
                self.assertEqual(record['env'][name], '1')
            self.assertNotIn('SECRET-ONLY-IN-API', json.dumps(record))
            self.assertNotIn('RESUME_RUN', record['env'])
        self.assertEqual(launch.read(self.directory / 'launches.json'), records)

    def test_dirty_source_blocks_before_api(self):
        launch.subprocess.check_output.return_value = ' M source.py'
        launch.subprocess.check_output.side_effect = None
        with self.assertRaisesRegex(ValueError, 'Commit'):
            self.start()
        launch.HfApi.assert_not_called()
        self.package.assert_not_called()

    def test_preflight_missing_schema_failed_or_changed_identity_blocks(self):
        for mutation in ('schema', 'passed', 'hash', 'identity'):
            with self.subTest(mutation=mutation):
                value = copy.deepcopy(self.preflight)
                if mutation == 'schema': value['schema'] = 'wrong'
                if mutation == 'passed': value['allChecksPassed'] = 1
                if mutation == 'hash': value['protocolSha256'] = 'f' * 64
                if mutation == 'identity': value['smokeIdentities']['2']['execution']['workers'] = 5
                atomic_json(self.root / launch.PREFLIGHT_NAME, value)
                with self.assertRaises(ValueError): self.start()
        self.api.run_job.assert_not_called()

    def test_preflight_missing_or_incomplete_real_game_counts_blocks_before_api(self):
        for field, expected in (('totalTerminalGames', 264), ('exactTerminalAndCounterReplayMatches', 132),
                                ('failures', 0), ('productionGamesExecuted', 0), ('interruptedAfterUpdate', 1)):
            for value in (None, expected + 1):
                with self.subTest(field=field, value=value):
                    changed = copy.deepcopy(self.preflight)
                    if value is None:
                        changed.pop(field)
                    else:
                        changed[field] = value
                    atomic_json(self.root / launch.PREFLIGHT_NAME, changed)
                    with self.assertRaisesRegex(ValueError, 'Incomplete real-service'):
                        self.start()
        launch.HfApi.assert_not_called()
        self.package.assert_not_called()

    def test_preflight_required_safety_and_recovery_flags_cannot_be_missing_or_flipped(self):
        fields = ('completedCommittedWorkPreserved', 'deliberatelyCorruptedBestRepaired',
                  'completedResumePerformsNoCollection', 'onlySmokeRoots', 'reusedReferenceArtifact',
                  'qualified', 'qualificationEligible', 'reservedFinalSeedsUsed')
        for field in fields:
            for value in (None, not self.preflight[field]):
                with self.subTest(field=field, value=value):
                    changed = copy.deepcopy(self.preflight)
                    if value is None:
                        changed.pop(field)
                    else:
                        changed[field] = value
                    atomic_json(self.root / launch.PREFLIGHT_NAME, changed)
                    with self.assertRaisesRegex(ValueError, 'Incomplete real-service'):
                        self.start()
        launch.HfApi.assert_not_called()
        self.package.assert_not_called()

    def test_preflight_boolean_and_numeric_lookalikes_are_not_evidence(self):
        # Python equality alone accepts False == 0 and True == 1, or 264.0 == 264.
        for field, original in self.preflight.items():
            if type(original) not in (int, bool) or field == 'allChecksPassed':
                continue
            variants = (int(original),) if type(original) is bool else (float(original), bool(original))
            for value in variants:
                with self.subTest(field=field, value=value):
                    changed = dict(self.preflight, **{field: value})
                    atomic_json(self.root / launch.PREFLIGHT_NAME, changed)
                    with self.assertRaisesRegex(ValueError, 'Incomplete real-service'):
                        self.start()
        launch.HfApi.assert_not_called()
        self.package.assert_not_called()

    def test_preflight_both_replica_exact_replays_required(self):
        for number in ('1', '2'):
            for mutation in ('missing_replica', 'missing_count', 'wrong_count', 'float_count',
                             'missing_tensors', 'false_tensors', 'numeric_tensors'):
                with self.subTest(replica=number, mutation=mutation):
                    changed = copy.deepcopy(self.preflight)
                    result = changed['results'][number]
                    if mutation == 'missing_replica': changed['results'].pop(number)
                    if mutation == 'missing_count': result.pop('exactTerminalAndCounterReplayMatches')
                    if mutation == 'wrong_count': result['exactTerminalAndCounterReplayMatches'] = 65
                    if mutation == 'float_count': result['exactTerminalAndCounterReplayMatches'] = 66.0
                    if mutation == 'missing_tensors': result.pop('exactModelOptimizerRngAndHistory')
                    if mutation == 'false_tensors': result['exactModelOptimizerRngAndHistory'] = False
                    if mutation == 'numeric_tensors': result['exactModelOptimizerRngAndHistory'] = 1
                    atomic_json(self.root / launch.PREFLIGHT_NAME, changed)
                    with self.assertRaisesRegex(ValueError, 'Both replica replays'):
                        self.start()
        changed = dict(self.preflight)
        changed.pop('results')
        atomic_json(self.root / launch.PREFLIGHT_NAME, changed)
        with self.assertRaisesRegex(ValueError, 'Both replica replays'):
            self.start()
        launch.HfApi.assert_not_called()
        self.package.assert_not_called()

    def test_existing_group_intent_and_output_block(self):
        self.directory.mkdir()
        with self.assertRaisesRegex(ValueError, 'Existing group'): self.start()
        self.directory.rmdir()
        (self.directory.parent / (GROUP + '-r2')).mkdir()
        with self.assertRaisesRegex(ValueError, 'Existing intent/output'): self.start()
        self.package.assert_not_called()

    def test_paths_and_groups_are_strict(self):
        for group in ('../multimap', 'multimap-expert', GROUP + '-other'):
            with self.assertRaises(ValueError): launch.launch(group, self.directory)
        with self.assertRaisesRegex(ValueError, 'dedicated'):
            launch.launch(GROUP, self.root / GROUP)

    def test_private_existing_repos_and_credentials_required(self):
        self.api.model_info.return_value.private = False
        with self.assertRaisesRegex(ValueError, 'private'): self.start()
        self.api.model_info.return_value.private = True
        launch.get_token.return_value = None
        with self.assertRaisesRegex(ValueError, 'credentials'): self.start()
        self.api.create_repo.assert_not_called()
        self.package.assert_not_called()

    def test_remote_source_or_any_output_file_blocks(self):
        self.api.file_exists.return_value = True
        with self.assertRaisesRegex(ValueError, 'source already'): self.start()
        self.api.file_exists.return_value = False
        self.remote_paths.add('runs/' + GROUP + '-r2')
        with self.assertRaisesRegex(ValueError, 'Remote run path'): self.start()
        self.package.assert_not_called()

    def test_uncertain_source_upload_cannot_be_retried_as_new(self):
        self.api.upload_file.side_effect = TimeoutError('uncertain upload')
        with self.assertRaises(TimeoutError): self.start()
        with self.assertRaisesRegex(ValueError, 'Existing group'): self.start()
        self.assertTrue((self.directory / 'intent.json').exists())
        self.api.run_job.assert_not_called()

    def test_missing_peer_reuses_source_without_package(self):
        original_submit = launch.submit
        def stop_second(api, token, directory, intent, command):
            if intent['replica'] == 2: raise RuntimeError('local interruption before intent')
            return original_submit(api, token, directory, intent, command)
        with patch.object(launch, 'submit', side_effect=stop_second):
            with self.assertRaisesRegex(RuntimeError, 'local interruption'): self.start()
        first = launch.read(self.receipt_path())
        peer = launch.continue_replica(self.receipt_path(), GROUP + '-r2', missing_replica=2)
        self.assertEqual(peer['source'], first['source'])
        self.assertEqual(peer['segment'], 1)
        self.assertEqual(self.package.call_count, 1)
        self.assertEqual(self.api.upload_file.call_count, 1)
        self.assertNotIn('RESUME_RUN', peer['env'])
        self.assertTrue(peer['sourceArchiveReusedExactly'])

    def test_source_only_recovery_after_upload_before_jobs(self):
        with patch.object(launch, 'submit', side_effect=RuntimeError('pre-submit interruption')):
            with self.assertRaises(RuntimeError): self.start()
        receipt = launch.continue_replica(self.directory / 'source.json', GROUP + '-r1', missing_replica=1)
        self.assertEqual(receipt['segment'], 1)
        self.assertEqual(self.package.call_count, 1)
        with self.assertRaises(ValueError):
            launch.continue_replica(self.directory / 'source.json', GROUP + '-continuation-r1', revision=RESUME_REVISION)

    def test_uncertain_peer_submission_blocks_even_if_remote_not_visible(self):
        self.fail_job = 2
        self.omit_job = 2
        with self.assertRaises(TimeoutError): self.start()
        with self.assertRaisesRegex(ValueError, 'slot already attempted'):
            launch.continue_replica(self.receipt_path(), GROUP + '-r2', missing_replica=2)
        with self.assertRaises(ValueError):
            launch.continue_replica(self.receipt_path(), GROUP + '-renamed-r2', missing_replica=2)
        self.assertEqual(self.api.run_job.call_count, 2)

    def test_uncertain_visible_submission_without_receipt_fails_closed(self):
        self.fail_job = 2
        with self.assertRaises(TimeoutError): self.start()
        with self.assertRaisesRegex(ValueError, 'without durable receipt'):
            launch.continue_replica(self.receipt_path(), GROUP + '-r2', missing_replica=2)
        self.assertEqual(self.api.run_job.call_count, 2)

    def test_resume_real_hf_snapshot_blob_layout_audits_then_submits_once(self):
        records = self.start()
        self.snapshot()
        checked = []
        original = launch.downloaded_file
        def audit(path, cache, size):
            snapshot = Path(path)
            self.assertTrue(snapshot.is_symlink())
            self.assertIn('snapshots', snapshot.relative_to(cache).parts)
            blob = original(path, cache, size)
            self.assertTrue(blob.is_file())
            self.assertFalse(blob.is_symlink())
            self.assertIn('blobs', blob.relative_to(cache).parts)
            checked.append(snapshot)
            return blob
        with patch.object(launch, 'downloaded_file', side_effect=audit):
            receipt = self.resume()
        self.assertEqual(len(checked), len(receipt['resumeAudit']['allFileHashes']) + 2)
        self.assertEqual(receipt['env']['REPLICA_SEGMENT'], '2')
        self.assertEqual(receipt['env']['RESUME_RUN'], records[0]['run'])
        self.assertEqual(receipt['env']['RESUME_REVISION'], RESUME_REVISION)
        self.assertEqual(receipt['firstReceiptSha256'], digest(self.receipt_path()))
        self.assertEqual(receipt['resumeAudit']['transaction']['stage'], 'initial')
        self.assertEqual(self.package.call_count, 1)
        self.assertEqual(self.api.upload_file.call_count, 1)
        self.assertFalse(list(self.directory.glob('.resume-audit-*')))
        self.assertEqual(self.jobs['job3'].command, self.jobs['job1'].command)
        self.assertTrue(self.storage.called)

    def test_four_slots_exactly_no_more_than_twelve_hours(self):
        self.start()
        self.snapshot(1); self.snapshot(2)
        self.resume(1); self.resume(2)
        self.assertEqual(self.api.run_job.call_count, 4)
        self.assertEqual(len(list((self.directory / 'intents').glob('*.json'))), 4)
        with self.assertRaises(ValueError): self.resume(1)
        with self.assertRaises(ValueError): self.resume(2)
        self.assertEqual(self.api.run_job.call_count, 4)

    def test_second_continuation_renamed_or_altered_receipt_blocked(self):
        self.start(); self.snapshot(); second = self.resume()
        for run in (GROUP + '-again-r1', GROUP + '-continuation-r1'):
            altered = dict(second, segment=1)
            fake = self.root / 'altered.json'
            atomic_json(fake, altered)
            with self.assertRaises(ValueError):
                launch.continue_replica(fake, run, revision=RESUME_REVISION)
        self.assertEqual(self.api.run_job.call_count, 3)

    def test_uncertain_continuation_consumes_slot_with_no_remote_visibility(self):
        self.start(); self.snapshot()
        self.fail_job = 3; self.omit_job = 3
        with self.assertRaises(TimeoutError): self.resume()
        with self.assertRaisesRegex(ValueError, 'slot already attempted'): self.resume()
        with self.assertRaises(ValueError):
            launch.continue_replica(self.receipt_path(), GROUP + '-different-r1', revision=RESUME_REVISION)
        self.assertEqual(self.api.run_job.call_count, 3)

    def test_only_error_or_canceled_original_can_resume(self):
        self.start(); self.snapshot()
        for stage in ('RUNNING', 'SCHEDULING', 'PENDING', 'COMPLETED'):
            self.jobs['job1'].status.stage = stage
            with self.subTest(stage=stage), self.assertRaisesRegex(ValueError, 'ERROR/CANCELED'):
                self.resume()
        self.jobs['job1'].status.stage = 'CANCELED'
        self.resume()
        self.assertEqual(self.api.run_job.call_count, 3)

    def test_immutable_revision_and_correct_peer_required(self):
        self.start()
        for kwargs in ({}, {'revision': 'main'}, {'revision': RESUME_REVISION, 'missing_replica': 2},
                       {'missing_replica': 1}, {'missing_replica': True}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                launch.continue_replica(self.receipt_path(), GROUP + '-r2', **kwargs)
        self.assertEqual(self.api.run_job.call_count, 2)

    def test_original_job_command_arguments_image_env_and_labels_pinned(self):
        self.start(); self.snapshot()
        job = self.jobs['job1']
        for field, value in [('command', ['wrong']), ('arguments', ['extra']), ('docker_image', 'changed'),
                             ('environment', dict(job.environment, EXPERT_WORKERS='5')),
                             ('flavor', 'cpu-basic'), ('labels', dict(job.labels, segment='2'))]:
            old = getattr(job, field)
            setattr(job, field, value)
            with self.subTest(field=field), self.assertRaises(ValueError): self.resume()
            setattr(job, field, old)
        self.assertEqual(self.api.run_job.call_count, 2)

    def test_original_bootstrap_read_from_original_commit_not_current_constant(self):
        self.start(); self.snapshot()
        with patch.object(launch, 'BOOTSTRAP', 'changed current in-memory bootstrap'):
            receipt = self.resume()
        self.assertEqual(self.jobs[receipt['jobId']].command, self.jobs['job1'].command)
        self.assertTrue(any(call.args[0][1] == 'show' for call in launch.subprocess.check_output.call_args_list))

    def test_remote_duplicate_slot_and_bounded_inventory_fail_closed(self):
        self.start(); self.snapshot()
        duplicate = copy.deepcopy(self.jobs['job1']); duplicate.id = 'duplicate'
        self.jobs[duplicate.id] = duplicate
        with self.assertRaisesRegex(ValueError, 'Duplicate remote'): self.resume()
        self.jobs.pop('duplicate')
        calls = []
        def too_many(**kwargs):
            for index in range(100):
                calls.append(index)
                replica, segment = ((1, 1), (2, 1), (1, 2), (2, 2))[index % 4]
                job = copy.deepcopy(self.jobs['job1']); job.id = 'extra' + str(index)
                job.labels = launch.labels_for(GROUP, replica, segment)
                self.jobs[job.id] = job
                yield job
        self.api.list_jobs.side_effect = too_many
        with self.assertRaisesRegex(ValueError, 'four-job'): launch.inventory(self.api, GROUP)
        self.assertEqual(len(calls), 5)

    def test_download_symlink_escape_in_source_manifest_or_payload_blocks_paid_resume(self):
        self.start(); self.snapshot()
        names = (f'multimap/{GROUP}/source.tgz', f'runs/{GROUP}-r1/artifacts.json',
                 f'runs/{GROUP}-r1/expert/last.pt')
        for target in names:
            def escape(repo, name, revision, **kwargs):
                path = Path(self.download(repo, name, revision, **kwargs))
                if name == target:
                    path.unlink()
                    # Valid bytes and hashes, but the symlink points outside the cache.
                    path.symlink_to(self.remote[repo, name, revision])
                return str(path)
            with self.subTest(target=target), patch.object(launch, 'hf_hub_download', side_effect=escape):
                with self.assertRaisesRegex(ValueError, 'escapes cache'):
                    self.resume()
                self.assertEqual(self.api.run_job.call_count, 2)
                self.assertFalse(launch.slot(self.directory, 1, 2).exists())
                self.assertFalse((self.directory.parent / (GROUP + '-continuation-r1')).exists())
                self.assertFalse(list(self.directory.glob('.*-audit-*')))

    def test_download_actual_size_must_match_source_manifest_and_payload_metadata(self):
        self.start(); self.snapshot()
        names = (f'multimap/{GROUP}/source.tgz', f'runs/{GROUP}-r1/artifacts.json',
                 f'runs/{GROUP}-r1/expert/last.pt')
        for target in names:
            def changed_size(repo, name, revision, **kwargs):
                path = Path(self.download(repo, name, revision, **kwargs))
                if name == target:
                    path.write_bytes(path.read_bytes() + b'\n')
                return str(path)
            with self.subTest(target=target), patch.object(launch, 'hf_hub_download', side_effect=changed_size):
                with self.assertRaisesRegex(ValueError, 'metadata size mismatch'):
                    self.resume()
                self.assertEqual(self.api.run_job.call_count, 2)
                self.assertFalse(launch.slot(self.directory, 1, 2).exists())

    def test_local_receipt_symlinks_remain_forbidden_before_api(self):
        self.start(); self.snapshot()
        link = self.root / 'receipt-link.json'
        link.symlink_to(self.receipt_path())
        with patch.object(launch, 'HfApi') as api_factory:
            with self.assertRaisesRegex(ValueError, 'Unsafe/oversize receipt'):
                launch.continue_replica(link, GROUP + '-continuation-r1', revision=RESUME_REVISION)
            api_factory.assert_not_called()
        self.assertEqual(self.api.run_job.call_count, 2)

    def test_source_archive_corruption_blocks_recovery_before_paid_call(self):
        self.start(); self.snapshot()
        (self.directory / 'source.tgz').write_bytes(b'corrupt')
        with self.assertRaisesRegex(ValueError, 'source metadata'): self.resume()
        self.assertEqual(self.api.run_job.call_count, 2)

    def test_archive_manifest_missing_file_or_symlink_rejected(self):
        self.start()
        source = launch.read(self.directory / 'source.json')
        for kind in ('missing', 'symlink'):
            path = self.root / (kind + '.tgz')
            with tarfile.open(path, 'w:gz') as tar:
                content = json.dumps(dict(gitCommit=COMMIT, files={'missing': 'a' * 64})).encode()
                member = tarfile.TarInfo('source-manifest.json'); member.size = len(content)
                tar.addfile(member, io.BytesIO(content))
                if kind == 'symlink':
                    member = tarfile.TarInfo('bad'); member.type = tarfile.SYMTYPE; member.linkname = '/etc/passwd'
                    tar.addfile(member)
            altered = dict(source, sourceBytes=path.stat().st_size, sourceSha256=digest(path))
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                launch.verify_archive(path, altered, self.preflight, self.source_files[launch.LAUNCHER_NAME])

    def test_resume_all_metadata_before_payload_and_hashes_every_metadata_file(self):
        self.start(); base = self.snapshot()
        self.events.clear()
        self.resume()
        snapshot_events = [(kind, name) for kind, name in self.events if name.startswith('runs/')]
        payload_start = next(i for i, (kind, name) in enumerate(snapshot_events)
                             if kind == 'download' and not name.endswith('artifacts.json'))
        metadata_names = {name for kind, name in snapshot_events[:payload_start] if kind == 'metadata'}
        downloaded = {name for kind, name in snapshot_events if kind == 'download'}
        self.assertEqual(metadata_names, downloaded)
        self.assertEqual(len(downloaded), len(list(base.rglob('*.json'))) + len(list(base.rglob('*.pt'))))

    def test_resume_aggregate_budget_includes_nontraining_metadata_before_payload(self):
        self.start(); self.snapshot()
        real = self.remote_size
        def large(repo, name, revision, **kwargs):
            if name.endswith(('status.json', 'recovery.json')): return 70 * 1024**2
            return real(repo, name, revision, **kwargs)
        launch.remote_size.side_effect = large
        with self.assertRaisesRegex(ValueError, 'Aggregate'): self.resume()
        downloads = [name for kind, name in self.events if kind == 'download' and name.startswith('runs/')]
        self.assertEqual(downloads, [f'runs/{GROUP}-r1/artifacts.json'])
        self.assertEqual(self.api.run_job.call_count, 2)

    def test_hash_corruption_in_nontraining_metadata_blocks_paid_resume(self):
        self.start(); base = self.snapshot()
        (base / 'status.json').write_text('{}')
        with self.assertRaisesRegex(ValueError, 'hash/size'): self.resume()
        self.assertEqual(self.api.run_job.call_count, 2)

    def test_resume_config_replica_workers_and_source_drift_blocks(self):
        self.start(); base = self.snapshot()
        original = launch.read(base / 'expert/config.json')
        for field, value in (('replica', 2), ('execution', {'workers': 5}), ('sourceFiles', {})):
            atomic_json(base / 'expert/config.json', dict(original, **{field: value}))
            self.publish_snapshot(base)
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, 'replica/config/source/workers'):
                self.resume()
        self.assertEqual(self.api.run_job.call_count, 2)

    def test_resume_status_source_identity_drift_blocks(self):
        self.start(); base = self.snapshot()
        original = launch.read(base / 'status.json')
        for field, value in [('sourceSha256', 'e' * 64), ('sourceRevision', 'f' * 40), ('workers', 5),
                             ('protocol', self.identities['2']['protocol'])]:
            atomic_json(base / 'status.json', dict(original, **{field: value}))
            self.publish_snapshot(base)
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, 'snapshot source'):
                self.resume()
        self.assertEqual(self.api.run_job.call_count, 2)

    def test_checkpoint_embedded_config_rng_best_hash_and_completed_guard(self):
        self.start(); base = self.snapshot()
        last = base / 'expert/last.pt'
        original = torch.load(last, map_location='cpu', weights_only=True)
        variants = [dict(config=self.identities['2']), dict(bestSha256='f' * 64),
                    dict(torchRng=torch.tensor([1], dtype=torch.uint8)), dict(result={'completed': True}),
                    dict(stage='train', update=33)]
        for variant in variants:
            torch.save(dict(original, **variant), last)
            self.publish_snapshot(base)
            with self.subTest(variant=list(variant)), self.assertRaises((ValueError, RuntimeError)):
                self.resume()
        self.assertEqual(self.api.run_job.call_count, 2)

    def test_newer_uploaded_best_and_history_do_not_override_committed_transaction(self):
        self.start(); base = self.snapshot()
        identity = launch.read(base / 'expert/config.json')
        newer = ExpertPolicy()
        save(base / 'expert/best.pt', newer, config=identity, stage='warmup', update=0)
        atomic_json(base / 'expert/history.json', [{'stage': 'warmup', 'update': 0}])
        self.publish_snapshot(base)
        before = {p: digest(base / p) for p in ('expert/best.pt', 'expert/history.json', 'expert/last.pt')}
        receipt = self.resume()
        self.assertEqual(receipt['resumeAudit']['transaction']['stage'], 'initial')
        self.assertNotEqual(receipt['resumeAudit']['transaction']['bestSha256'], before['expert/best.pt'])
        self.assertEqual(before, {p: digest(base / p) for p in before})

    def test_nonfinite_optimizer_state_and_recipe_override_rejected(self):
        self.start(); base = self.snapshot()
        path = base / 'expert/last.pt'
        original = torch.load(path, map_location='cpu', weights_only=True)
        changed = copy.deepcopy(original)
        changed['optimizer']['param_groups'][0]['lr'] *= 2
        torch.save(changed, path); self.publish_snapshot(base)
        with self.assertRaisesRegex(ValueError, 'optimizer recipe'): self.resume()
        changed = copy.deepcopy(original)
        parameter = next(ExpertPolicy().parameters())
        changed['optimizer']['state'][0] = dict(step=torch.tensor(1.),
            exp_avg=torch.full_like(parameter, float('nan')), exp_avg_sq=torch.zeros_like(parameter))
        torch.save(changed, path); self.publish_snapshot(base)
        with self.assertRaisesRegex(ValueError, 'nonfinite optimizer'): self.resume()
        self.assertEqual(self.api.run_job.call_count, 2)

    def test_manifest_unsafe_path_rejected_before_payload(self):
        self.start(); base = self.snapshot()
        manifest = launch.read(base / 'artifacts.json')
        manifest['../escape'] = 'f' * 64
        atomic_json(base / 'artifacts.json', manifest)
        with self.assertRaisesRegex(ValueError, 'Unsafe/unexpected'): self.resume()
        self.assertEqual(self.api.run_job.call_count, 2)

    def test_group_lock_prevents_concurrent_reservations(self):
        self.start()
        with launch.locked(self.directory):
            with self.assertRaises(BlockingIOError):
                launch.continue_replica(self.receipt_path(), GROUP + '-r2', missing_replica=2)
        self.assertEqual(self.api.run_job.call_count, 2)


class DownloadedFileTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.cache = self.root / 'cache'
        self.cache.mkdir()
        self.blob = self.cache / 'blob'
        self.blob.write_bytes(b'{}')

    def test_regular_cached_file_is_accepted_without_symlink(self):
        self.assertEqual(launch.downloaded_file(self.blob, self.cache, 2), self.blob)

    def test_cache_containment_is_component_based_and_resolves_all_links(self):
        outside = self.root / 'cache-outside'
        outside.mkdir()
        target = outside / 'blob'
        target.write_bytes(b'{}')
        link = self.cache / 'snapshot'
        self.blob.unlink()
        self.blob.symlink_to(target)
        link.symlink_to(self.blob)
        for path in (target, link):
            with self.subTest(path=path), self.assertRaisesRegex(ValueError, 'escapes cache'):
                launch.downloaded_file(path, self.cache, 2)

    def test_missing_dangling_and_cyclic_paths_fail_strict_resolution(self):
        missing = self.cache / 'missing'
        dangling = self.cache / 'dangling'
        dangling.symlink_to(missing)
        cycle = self.cache / 'cycle'
        cycle.symlink_to(cycle)
        for path in (missing, dangling, cycle):
            with self.subTest(path=path), self.assertRaises((OSError, RuntimeError)):
                launch.downloaded_file(path, self.cache, 2)

    def test_directories_and_special_files_are_not_downloaded_payloads(self):
        directory = self.cache / 'directory'
        directory.mkdir()
        link = self.cache / 'directory-link'
        link.symlink_to(directory)
        fifo = self.cache / 'fifo'
        os.mkfifo(fifo)
        for path in (directory, link, fifo):
            with self.subTest(path=path), self.assertRaisesRegex(ValueError, 'not a regular file'):
                launch.downloaded_file(path, self.cache, path.stat().st_size)


class StorageHeadroomTests(unittest.TestCase):
    """Exercise the real wrapper, independently of LauncherTests' storage mock."""
    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.root = Path(self.stack.enter_context(tempfile.TemporaryDirectory()))
        self.runs = self.root / 'ai/runs'
        self.runs.mkdir(parents=True)
        self.paths = [self.runs / 'multimap-existing', self.runs / GROUP]
        for path in self.paths + [self.runs / 'unrelated-study']:
            path.mkdir()
        self.reserved = 8 * launch.LIMIT
        self.minimum_free = STUDY['budget']['minimumFreeBytes']
        self.stack.enter_context(patch.object(launch, 'ROOT', self.root))
        self.inherited = self.stack.enter_context(patch.object(launch, 'inherited_storage_check'))
        self.tree = self.stack.enter_context(patch.object(launch, 'tree_bytes', return_value=0))
        self.disk = self.stack.enter_context(patch.object(launch.shutil, 'disk_usage',
            return_value=NS(free=self.minimum_free + self.reserved)))

    def test_exact_decimal_ceiling_and_free_reservation_boundaries_pass(self):
        self.assertEqual(self.reserved, 1024**3)
        self.assertEqual(self.minimum_free, 2 * 1024**3)
        sizes = {self.paths[0]: 1, self.paths[1]: 8_000_000_000 - self.reserved - 1}
        self.tree.side_effect = sizes.__getitem__
        launch.check_local_storage(self.paths[1])
        self.inherited.assert_called_once_with(self.paths[1])
        self.assertEqual({call.args[0] for call in self.tree.call_args_list}, set(self.paths))
        self.disk.assert_called_once_with(self.root)

    def test_one_byte_over_combined_eight_decimal_gb_fails(self):
        sizes = {self.paths[0]: 1, self.paths[1]: 8_000_000_000 - self.reserved}
        self.tree.side_effect = sizes.__getitem__
        with self.assertRaisesRegex(ValueError, 'staging/recovery headroom'):
            launch.check_local_storage(self.paths[1])
        self.inherited.assert_called_once_with(self.paths[1])

    def test_binary_eight_gib_is_not_a_relaxation_of_old_ceiling(self):
        sizes = {self.paths[0]: 0, self.paths[1]: 8 * 1024**3 - self.reserved}
        self.tree.side_effect = sizes.__getitem__
        with self.assertRaisesRegex(ValueError, 'staging/recovery headroom'):
            launch.check_local_storage(self.paths[1])

    def test_free_space_includes_entire_one_gib_reservation(self):
        for free in (self.minimum_free, self.minimum_free + self.reserved - 1):
            self.disk.return_value.free = free
            with self.subTest(free=free), self.assertRaisesRegex(ValueError, 'staging/recovery headroom'):
                launch.check_local_storage(self.paths[1])

    def test_inherited_storage_rejection_is_preserved_before_extra_checks(self):
        self.inherited.side_effect = RuntimeError('old storage guard')
        with self.assertRaisesRegex(RuntimeError, 'old storage guard'):
            launch.check_local_storage(self.paths[1])
        self.inherited.assert_called_once_with(self.paths[1])
        self.tree.assert_not_called()
        self.disk.assert_not_called()


if __name__ == '__main__':
    unittest.main()
