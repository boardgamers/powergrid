"""Offline bounded-launch conformance; all HF/package/storage endpoints are fixtures."""
import copy
from contextlib import ExitStack, redirect_stdout
import io
import json
import os
from pathlib import Path
import shutil
import tarfile
import tempfile
from types import SimpleNamespace as NS
import unittest
from unittest.mock import Mock, patch

import launch_replica_stress_v1 as launch
import job_replica_stress_v1 as worker
import replica_stress_study_v1 as study
from data import atomic_json, digest
from test_job_replica_stress_v1 import identity_fixture, write_snapshot, COMMIT, REVISION, SNAPSHOT
from test_replica_stress_rollout_v1 import outcome

GROUP = launch.GROUP
HERE = Path(__file__).resolve().parent


class LauncherTests(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.root = Path(self.stack.enter_context(tempfile.TemporaryDirectory()))
        self.directory = self.root / 'ai/runs' / GROUP
        self.directory.parent.mkdir(parents=True)
        self.source_files = {'ai/multimap/' + n: (HERE / n).read_bytes() if (HERE / n).exists() else b'# fixture\n'
                             for n in launch.SOURCE_NAMES}
        for name, content in self.source_files.items():
            path = self.root / name; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(content)
        source_hashes = {Path(n).name: launch.sha_bytes(v) for n, v in self.source_files.items()}
        self.identities = {p: identity_fixture(p, True, source_hashes) for p in launch.PANELS}
        self.preflight = dict(schema='multimap-replica-stress-real-preflight-v1', allChecksPassed=True,
            protocolSha256=digest(self.root / 'ai/multimap/replica-stress-protocol-v1.json'),
            totalTerminalGames=396, exactTerminalAndCounterReplayMatches=198, failures=0,
            interruptedAfterBatches=1, completedBatchesPreserved=True, interruptedTemporaryBatchIgnored=True,
            completedResumePerformsNoCollection=True, bothPanels=True, reusedReferenceArtifact=True,
            allThreeFocalArms=True, allSixPinnedModels=True, modelLoads=6,
            allFourMaps=True, allFivePlayerCounts=True, allFourRules=True,
            modelTensorAndInferenceFlagsUnchanged=True, metadataBeforeAllTransfers=True,
            legacyServingGitHashesVerified=True, reusedPythonEnvironments=True, onlySmokeRoots=True,
            fitting=False, selection=False,
            productionGamesExecuted=0, qualified=False, qualificationEligible=False, reservedFinalSeedsUsed=False,
            smokeIdentities=self.identities,
            privateEvidence=dict(repo=launch.MODEL, revision='e' * 40,
                                 prefix='diagnostics/replica-stress-v1-preflight', files={}, bytes=0))
        self.save_preflight()
        self.jobs, self.remote = {}, {}
        self.remote_paths = set()
        self.events = []
        self.fail_job = self.omit_job = None
        self.api = Mock()
        self.api.model_info.return_value = NS(private=True, sha=SNAPSHOT)
        self.api.dataset_info.return_value = NS(private=True, sha='d' * 40)
        self.api.file_exists.side_effect = lambda repo, path, revision, **kwargs: (repo, path, revision) in self.remote
        self.before_commit = None
        self.api.list_repo_tree.side_effect = self.list_repo_tree
        self.api.list_jobs.side_effect = lambda **kwargs: list(self.jobs.values())
        self.api.run_job.side_effect = self.run_job
        self.api.create_commit.side_effect = self.commit
        self.mock(launch, 'ROOT', self.root)
        self.mock(launch, 'PROTOCOL_PATH', self.root / 'ai/multimap/replica-stress-protocol-v1.json')
        self.mock(launch, 'HfApi', Mock(return_value=self.api))
        self.mock(launch, 'get_token', Mock(return_value='SECRET-ONLY-IN-API'))
        self.mock(launch, 'inspect_actual', Mock(side_effect=lambda api, job_id: self.jobs[job_id]))
        self.storage = self.mock(launch, 'check_local_storage', Mock())
        self.package = self.mock(launch, 'package', Mock(side_effect=self.make_package))
        self.archive_check = self.mock(launch, 'verify_preflight_archive', Mock())
        for module in (launch, worker):
            self.mock(module, 'hf_hub_download', Mock(side_effect=self.download))
            self.mock(module, 'remote_size', Mock(side_effect=self.metadata))
        self.mock(launch.subprocess, 'check_output', Mock(side_effect=self.git))
        self.mock(launch, 'identity', Mock(side_effect=lambda panel, *args: copy.deepcopy(self.identities[panel])))
        self.stack.enter_context(redirect_stdout(io.StringIO()))

    def mock(self, module, name, value):
        return self.stack.enter_context(patch.object(module, name, value))

    def save_preflight(self):
        atomic_json(self.root / launch.PREFLIGHT_NAME, self.preflight)

    def git(self, args, **kwargs):
        if args[1] == 'status': return ''
        if args[1] == 'rev-parse': return COMMIT + '\n'
        if args[1] == 'show':
            commit, name = args[2].split(':', 1)
            self.assertEqual(commit, COMMIT)
            content = (self.root / name).read_bytes() if name == launch.PREFLIGHT_NAME else self.source_files[name]
            return content.decode() if kwargs.get('text') else content
        raise AssertionError(args)

    def list_repo_tree(self, repo, path_in_repo, **kwargs):
        if path_in_repo in self.remote_paths: return iter([NS(path=path_in_repo + '/anything')])
        raise launch.EntryNotFoundError('fixture absent')

    def make_package(self, directory):
        files = dict(self.source_files, **{launch.PREFLIGHT_NAME: (self.root / launch.PREFLIGHT_NAME).read_bytes()})
        files['source-manifest.json'] = json.dumps(dict(gitCommit=COMMIT,
            files={n: launch.sha_bytes(v) for n, v in files.items()})).encode()
        path = Path(directory) / 'source.tgz'
        with tarfile.open(path, 'w:gz') as tar:
            for name, content in files.items():
                item = tarfile.TarInfo(name); item.size = len(content); tar.addfile(item, io.BytesIO(content))
        return path, COMMIT

    def commit(self, repo_id, repo_type, operations, parent_commit, **kwargs):
        directory = launch.ROOT / 'ai/runs' / GROUP
        self.assertTrue((directory / 'intent.json').exists())
        self.assertTrue((directory / 'reservation.json').exists())
        self.assertEqual(repo_type, 'dataset')
        self.assertEqual({op.path_in_repo for op in operations},
                         {f'multimap/{GROUP}/source.tgz', f'multimap/{GROUP}/reservation.json'})
        if self.before_commit is not None:
            callback, self.before_commit = self.before_commit, None
            callback()
        if parent_commit != self.api.dataset_info.return_value.sha:
            raise ValueError('fixture remote CAS parent conflict')
        for operation in operations:
            value = operation.path_or_fileobj
            if isinstance(value, bytes):
                path = self.root / 'remote-owner.json'; path.write_bytes(value)
            else:
                path = Path(value)
            self.remote[repo_id, operation.path_in_repo, REVISION] = path
        self.api.dataset_info.return_value.sha = REVISION
        return NS(oid=REVISION)

    def run_job(self, **kwargs):
        name = kwargs['labels']['slot']
        directory = launch.ROOT / 'ai/runs' / GROUP
        intent = launch.slot(directory, name)
        self.assertTrue(intent.exists())
        self.assertEqual(launch.read(intent)['env'], kwargs['env'])
        self.assertTrue((directory.parent / kwargs['name'] / 'intent.json').exists())
        self.assertEqual(kwargs['secrets'], {'HF_TOKEN': 'SECRET-ONLY-IN-API'})
        self.assertNotIn('SECRET-ONLY-IN-API', json.dumps({k: v for k, v in kwargs.items() if k != 'secrets'}))
        number = self.api.run_job.call_count
        job = NS(id='job' + str(number), environment=copy.deepcopy(kwargs['env']), docker_image=kwargs['image'],
                 command=kwargs['command'], arguments=[], flavor=kwargs['flavor'],
                 status=NS(stage='RUNNING', message=None), labels=dict(kwargs['labels'], name=kwargs['name']),
                 timeout_seconds=int(kwargs['timeout'][:-1]) * 3600, volumes=None, space_id=None, expose=None, ssh=None)
        if self.omit_job != number: self.jobs[job.id] = job
        if self.fail_job == number: raise TimeoutError('fixture uncertain')
        return job

    def download(self, repo, name, revision, cache_dir, **kwargs):
        self.events.append(('download', name))
        content = self.remote[repo, name, revision].read_bytes()
        prefix = 'datasets' if kwargs.get('repo_type') == 'dataset' else 'models'
        repository = Path(cache_dir) / (prefix + '--' + repo.replace('/', '--'))
        blob = repository / 'blobs' / launch.sha_bytes(content)
        blob.parent.mkdir(parents=True, exist_ok=True); blob.write_bytes(content)
        snapshot = repository / 'snapshots' / revision / name
        snapshot.parent.mkdir(parents=True, exist_ok=True)
        snapshot.symlink_to(os.path.relpath(blob, snapshot.parent))
        return str(snapshot)

    def metadata(self, repo, name, revision, maximum=launch.LIMIT, **kwargs):
        self.events.append(('metadata', name))
        size = self.remote[repo, name, revision].stat().st_size
        if size > maximum: raise ValueError('fixture remote metadata budget')
        return size

    def start(self):
        return launch.launch(GROUP, self.directory)

    def receipt(self, panel='strong'):
        return self.directory.parent / (GROUP + '-' + panel) / 'launch.json'

    def snapshot(self, panel='strong', committed=1):
        source = launch.read(self.directory / 'source.json')
        config = worker.production_identity(self.preflight, panel)
        base = write_snapshot(self.root / ('snapshot-' + panel), source, panel, config, committed)
        self.publish_snapshot(base, panel)
        self.jobs['job1' if panel == 'strong' else 'job2'].status = NS(stage='ERROR', message='Job timeout')
        return base

    def publish_snapshot(self, base, panel='strong', revision=SNAPSHOT):
        worker.write_manifest(base, worker.compact_files(base))
        for path in base.rglob('*.json'):
            self.remote[launch.MODEL, f'runs/{GROUP}-{panel}/' + path.relative_to(base).as_posix(), revision] = path

    def copy_revision(self, repo, before, after):
        for (stored_repo, name, revision), path in list(self.remote.items()):
            if stored_repo == repo and revision == before:
                destination = self.root / ('immutable-' + after) / name
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(path.read_bytes())
                self.remote[repo, name, after] = destination

    def both(self):
        self.start(); self.snapshot('strong'); self.snapshot('mixed')

    def resume(self, panel='strong'):
        return launch.continue_panel(self.receipt(panel), GROUP + '-recovery-' + panel,
                                     revision=SNAPSHOT, peer_revision=SNAPSHOT)

    def partial(self, stop='mixed'):
        original = launch.submit
        def submit(api, token, directory, intent, command):
            if intent['panel'] == stop: raise RuntimeError('fixture local interruption')
            return original(api, token, directory, intent, command)
        with patch.object(launch, 'submit', side_effect=submit), self.assertRaises(RuntimeError): self.start()

    def test_two_initial_jobs_exact_six_plus_three_same_source_secrets_only(self):
        records = self.start()
        self.assertEqual([r['requestedHours'] for r in records], [6, 3])
        self.assertEqual([r['timeout'] for r in records], ['6h', '3h'])
        self.assertEqual(self.package.call_count, 1)
        self.assertEqual(self.api.create_commit.call_count, 1)
        self.assertEqual(records[0]['source'], records[1]['source'])
        for panel, record in zip(launch.PANELS, records):
            self.assertEqual(record['env']['REPLICA_STRESS_PANEL'], panel)
            self.assertEqual(record['env']['REPLICA_STRESS_WORKERS'], '6')
            self.assertEqual(record['env']['SOURCE_COMMIT'], COMMIT)
            self.assertNotIn('RESUME_RUN', record['env'])
            self.assertNotIn('SECRET-ONLY-IN-API', json.dumps(record))
            self.assertEqual(record['plannedGames'], 7680)
            self.assertEqual(record['plannedDealRoots'], 640)
        self.assertEqual(launch.read(self.directory / 'launches.json'), records)

    def test_exact_twelve_hours_three_attempts_shared_recovery_strong_priority(self):
        self.both(); record = self.resume()
        self.assertEqual(record['requestedHours'], 3)
        self.assertEqual(record['slot'], 'recovery')
        self.assertEqual(record['otherIncompletePanels'], ['mixed'])
        self.assertFalse(record['furtherJobsAuthorized'])
        self.assertEqual(record['resumeAudit']['transaction']['committedBatches'], 1)
        self.assertEqual(record['env']['RESUME_RUN'], GROUP + '-strong')
        self.assertEqual(self.jobs['job3'].command, self.jobs['job1'].command)
        self.assertEqual(sum(launch.read(p)['requestedHours'] for p in (self.directory / 'intents').glob('*.json')), 12)
        for panel in launch.PANELS:
            with self.assertRaises(ValueError): self.resume(panel)
        self.assertEqual(self.api.run_job.call_count, 3)
        self.assertEqual(self.package.call_count, 1)

    def test_mixed_cannot_steal_shared_slot_when_both_incomplete(self):
        self.both()
        with self.assertRaisesRegex(ValueError, 'strong-priority'): self.resume('mixed')
        self.assertFalse(launch.slot(self.directory, 'recovery').exists())
        self.assertEqual(self.api.run_job.call_count, 2)

    def test_mixed_recovery_when_strong_complete_and_complete_errored_not_replayed(self):
        self.both()
        real = launch.verify_resume
        def audited(source, receipt, *args, **kwargs):
            value = real(source, receipt, *args, **kwargs)
            if receipt['panel'] == 'strong': value['transaction']['complete'] = True
            return value
        with patch.object(launch, 'verify_resume', side_effect=audited):
            record = self.resume('mixed')
        self.assertEqual(record['panel'], 'mixed')
        self.assertEqual(record['otherIncompletePanels'], [])

    def test_both_complete_audit_no_new_job(self):
        self.both()
        original = launch.verify_resume
        def complete(*args, **kwargs):
            result = original(*args, **kwargs)
            result['transaction']['complete'] = True
            return result
        with patch.object(launch, 'verify_resume', side_effect=complete), \
             self.assertRaisesRegex(ValueError, 'audit instead'): self.resume()
        self.assertEqual(self.api.run_job.call_count, 2)

    def test_both_initials_must_be_terminal_not_running_scheduling_or_pending(self):
        self.both()
        for panel in launch.PANELS:
            job = self.jobs['job1' if panel == 'strong' else 'job2']
            for state in ('RUNNING', 'SCHEDULING', 'PENDING', None):
                job.status.stage = state
                with self.subTest(panel=panel, state=state), self.assertRaisesRegex(ValueError, 'terminal'): self.resume()
            job.status.stage = 'ERROR'
        self.assertEqual(self.api.run_job.call_count, 2)

    def test_only_actual_timeout_not_canceled_other_error_or_claimed_complete(self):
        self.both()
        for stage, message in [('CANCELED', 'Job timeout'), ('ERROR', 'OOM'), ('ERROR', None),
                               ('ERROR', 'job timeout'), ('COMPLETED', 'Job timeout')]:
            self.jobs['job1'].status = NS(stage=stage, message=message)
            with self.subTest(stage=stage, message=message), self.assertRaisesRegex(ValueError, 'actual ERROR'): self.resume()
        self.assertEqual(self.api.run_job.call_count, 2)

    def test_missing_initial_peer_original_source_explicit_mode(self):
        self.partial()
        peer = launch.continue_panel(self.receipt(), GROUP + '-mixed', missing_panel='mixed')
        self.assertEqual(peer['requestedHours'], 3)
        self.assertEqual(peer['segment'], 1)
        self.assertTrue(peer['sourceArchiveReusedExactly'])
        self.assertNotIn('RESUME_RUN', peer['env'])
        self.assertEqual(self.package.call_count, 1)
        self.assertEqual(self.api.create_commit.call_count, 1)

    def test_source_receipt_after_upload_before_first_submission(self):
        self.partial('strong')
        record = launch.continue_panel(self.directory / 'source.json', GROUP + '-strong', missing_panel='strong')
        self.assertEqual(record['requestedHours'], 6)
        self.assertEqual(self.package.call_count, 1)

    def test_no_recovery_until_missing_peer_explicitly_submitted_and_terminal(self):
        self.partial(); self.snapshot()
        with self.assertRaisesRegex(ValueError, 'Both original initial'): self.resume()
        self.assertEqual(self.api.run_job.call_count, 1)

    def test_uncertain_submission_visible_or_invisible_blocks_all_further_attempts(self):
        self.fail_job = 2; self.omit_job = 2
        with self.assertRaises(TimeoutError): self.start()
        self.assertTrue(launch.slot(self.directory, 'mixed').exists())
        with self.assertRaisesRegex(ValueError, 'Uncertain intent'):
            launch.continue_panel(self.receipt(), GROUP + '-mixed', missing_panel='mixed')
        self.assertEqual(self.api.run_job.call_count, 2)

    def test_uncertain_visible_submission_without_receipt_fails_closed(self):
        self.fail_job = 2
        with self.assertRaises(TimeoutError): self.start()
        self.assertEqual(len(self.jobs), 2)
        with self.assertRaisesRegex(ValueError, 'Uncertain intent'):
            launch.continue_panel(self.receipt(), GROUP + '-mixed', missing_panel='mixed')
        self.assertEqual(self.api.run_job.call_count, 2)

    def test_uncertain_recovery_permanently_consumes_shared_three_hour_slot(self):
        self.both(); self.fail_job = 3; self.omit_job = 3
        with self.assertRaises(TimeoutError): self.resume()
        for panel in launch.PANELS:
            with self.assertRaisesRegex(ValueError, 'Uncertain intent'): self.resume(panel)
        self.assertEqual(self.api.run_job.call_count, 3)
        self.assertEqual(sum(launch.read(p)['requestedHours'] for p in (self.directory / 'intents').glob('*.json')), 12)

    def test_uncertain_upload_cannot_be_retried_or_repackaged(self):
        self.api.create_commit.side_effect = TimeoutError('fixture unknown')
        with self.assertRaises(TimeoutError): self.start()
        with self.assertRaisesRegex(ValueError, 'Existing group'): self.start()
        self.assertEqual(self.package.call_count, 1)
        self.api.run_job.assert_not_called()

    def test_dirty_source_failed_preflight_blocks_before_api(self):
        self.mock(launch.subprocess, 'check_output', Mock(return_value=' M source.py'))
        with self.assertRaisesRegex(ValueError, 'Commit all'): self.start()
        launch.HfApi.assert_not_called()
        self.package.assert_not_called()

    def test_all_real_preflight_counts_flags_identity_and_archive_required(self):
        original = copy.deepcopy(self.preflight)
        for field in ('totalTerminalGames', 'exactTerminalAndCounterReplayMatches', 'interruptedAfterBatches',
                      'completedBatchesPreserved', 'completedResumePerformsNoCollection', 'bothPanels',
                      'productionGamesExecuted', 'privateEvidence', 'schema'):
            self.preflight = copy.deepcopy(original); self.preflight.pop(field); self.save_preflight()
            with self.subTest(field=field), self.assertRaises(ValueError): self.start()
        self.api.run_job.assert_not_called()

    def test_boolean_float_lookalikes_are_not_preflight_evidence(self):
        original = copy.deepcopy(self.preflight)
        for field, value in [('totalTerminalGames', 396.), ('interruptedAfterBatches', True),
                             ('allChecksPassed', 1), ('qualified', 0), ('productionGamesExecuted', False)]:
            self.preflight = copy.deepcopy(original); self.preflight[field] = value; self.save_preflight()
            with self.subTest(field=field), self.assertRaises(ValueError): self.start()
        self.api.run_job.assert_not_called()

    def test_preflight_model_source_drift_blocks(self):
        self.preflight['smokeIdentities']['strong']['workers'] = 5
        launch.identity.side_effect = lambda panel, *args: dict(self.identities[panel], workers=6)
        self.save_preflight()
        with self.assertRaisesRegex(ValueError, 'identity changed'): self.start()
        self.api.run_job.assert_not_called()

    def test_source_files_must_match_committed_git_even_if_clean_flag_wrong(self):
        path = self.root / 'ai/multimap/job_replica_stress_v1.py'; path.write_text('# altered source')
        with self.assertRaisesRegex(ValueError, 'committed Git'): self.start()
        self.api.run_job.assert_not_called()

    def test_private_repositories_and_credentials_required(self):
        self.api.model_info.return_value.private = False
        with self.assertRaisesRegex(ValueError, 'private'): self.start()
        self.api.model_info.return_value.private = True
        launch.get_token.return_value = None
        with self.assertRaisesRegex(ValueError, 'credentials'): self.start()
        self.api.create_repo.assert_not_called()

    def test_actual_job_every_config_field_and_timeout_seconds_checked(self):
        self.both(); job = self.jobs['job1']
        for field, changed in [('command', ['wrong']), ('arguments', ['extra']), ('docker_image', 'changed'),
                ('environment', dict(job.environment, SOURCE_COMMIT='f' * 40)), ('flavor', 'cpu-basic'),
                ('labels', dict(job.labels, stage='stress-v1')), ('timeout_seconds', None),
                ('timeout_seconds', 10800), ('timeout_seconds', 21600.), ('volumes', ['mount']),
                ('space_id', 'owner/space'), ('expose', {'ports': [8000]}), ('ssh', {'enabled': True})]:
            old = getattr(job, field); setattr(job, field, changed)
            with self.subTest(field=field), self.assertRaises(ValueError): self.resume()
            setattr(job, field, old)
        self.assertEqual(self.api.run_job.call_count, 2)

    def test_original_git_bootstrap_used_not_current_in_memory_constant(self):
        self.both()
        with patch.object(launch, 'BOOTSTRAP', 'different runtime constant'):
            record = self.resume()
        self.assertEqual(self.jobs[record['jobId']].command, self.jobs['job1'].command)

    def test_remote_duplicate_or_unreceipted_or_hidden_original_failclosed(self):
        self.both()
        duplicate = copy.deepcopy(self.jobs['job1']); duplicate.id = 'duplicate'; self.jobs['duplicate'] = duplicate
        with self.assertRaisesRegex(ValueError, 'Duplicate remote'): self.resume()
        self.jobs.pop('duplicate')
        first = self.jobs.pop('job1')
        with self.assertRaisesRegex(ValueError, 'absent from authoritative'): self.resume()
        self.jobs['job1'] = first
        remote = copy.deepcopy(first); remote.id = 'extra'
        remote.labels = dict(launch.labels_for(GROUP, 'strong', 2, 'recovery'), name=GROUP + '-recovery-strong')
        self.jobs['extra'] = remote
        with self.assertRaisesRegex(ValueError, 'without durable receipt'): self.resume()

    def test_group_inventory_bounded_at_fourth_summary(self):
        self.start(); seen = []
        originals = list(self.jobs.values())
        third = copy.deepcopy(originals[0]); third.id = 'third'
        third.labels = dict(launch.labels_for(GROUP, 'strong', 2, 'recovery'), name=GROUP + '-recovery-strong')
        self.jobs['third'] = third
        def infinite(**kwargs):
            for i in range(10000):
                seen.append(i); yield (originals + [third])[i % 3]
        self.api.list_jobs.side_effect = infinite
        with self.assertRaisesRegex(ValueError, 'three-job'): launch.inventory(self.api, GROUP)
        self.assertEqual(len(seen), 4)

    def test_lock_blocks_concurrent_reservation(self):
        self.start()
        with launch.locked(self.directory), self.assertRaises(BlockingIOError):
            launch.continue_panel(self.receipt(), GROUP + '-mixed', missing_panel='mixed')
        self.assertEqual(self.api.run_job.call_count, 2)

    def test_copied_coordinator_and_symlinked_receipt_rejected(self):
        self.start()
        original = self.directory.with_name('original-ledger')
        self.directory.rename(original); shutil.copytree(original, self.directory)
        with self.assertRaisesRegex(ValueError, 'Copied/changed'): self.resume()
        link = self.root / 'link.json'; link.symlink_to(self.receipt())
        with self.assertRaisesRegex(ValueError, 'symlink'):
            launch.continue_panel(link, GROUP + '-mixed', missing_panel='mixed')

    def test_renamed_groups_runs_later_receipts_and_mutable_revisions_forbidden(self):
        with self.assertRaises(ValueError): launch.launch(GROUP + '-new', self.directory)
        self.both(); record = self.resume()
        with self.assertRaises(ValueError):
            launch.continue_panel(self.directory.parent / record['run'] / 'launch.json', record['run'],
                                  revision=SNAPSHOT, peer_revision=SNAPSHOT)
        with self.assertRaises(ValueError):
            launch.continue_panel(self.receipt(), GROUP + '-again', revision='main', peer_revision=SNAPSHOT)
        self.assertEqual(self.api.run_job.call_count, 3)

    def test_resume_corrupt_metadata_plan_batch_source_stops_before_paid_call(self):
        self.both(); base = self.root / 'snapshot-strong'
        for name in ('environment.json', 'study/plan.json', 'study/batch-000.json', 'status.json'):
            path = base / name; old = path.read_bytes(); path.write_text('{}')
            with self.subTest(name=name), self.assertRaises(ValueError): self.resume()
            path.write_bytes(old)
        archive = self.directory / 'source.tgz'; archive.write_bytes(b'corrupt')
        with self.assertRaisesRegex(ValueError, 'source metadata'): self.resume()
        self.assertEqual(self.api.run_job.call_count, 2)
        self.assertFalse(launch.slot(self.directory, 'recovery').exists())

    def test_noncontiguous_validhash_snapshot_stops_before_paid_call(self):
        self.both(); base = self.root / 'snapshot-strong'
        (base / 'study/batch-000.json').rename(base / 'study/batch-001.json')
        self.publish_snapshot(base)
        with self.assertRaisesRegex(ValueError, 'Noncontiguous'): self.resume()
        self.assertEqual(self.api.run_job.call_count, 2)

    def test_manifest_allmetadata_before_payload_in_both_panel_audits(self):
        self.both(); self.events.clear(); self.resume()
        for panel in launch.PANELS:
            events = [(kind, name) for kind, name in self.events if name.startswith(f'runs/{GROUP}-{panel}/')]
            first = next(i for i, (k, n) in enumerate(events) if k == 'download' and not n.endswith('artifacts.json'))
            self.assertEqual({n for k, n in events[:first] if k == 'metadata'}, {n for k, n in events if k == 'download'})

    def test_remote_conditional_owner_reservation_one_winner_across_independent_coordinators(self):
        other_root = self.root / 'other-worktree'
        shutil.copytree(self.root / 'ai/multimap', other_root / 'ai/multimap')
        other_directory = other_root / 'ai/runs' / GROUP
        other_records = []
        def interleave():
            # A has passed inventory/absence, packaged and reached its CAS.
            # B independently passes those same checks against the same parent,
            # wins the reservation and submits before A's CAS resumes.
            with patch.object(launch, 'ROOT', other_root), \
                 patch.object(launch, 'PROTOCOL_PATH', other_root / 'ai/multimap/replica-stress-protocol-v1.json'):
                other_records.extend(launch.launch(GROUP, other_directory))
        self.before_commit = interleave
        with self.assertRaisesRegex(ValueError, 'CAS parent conflict'): self.start()
        self.assertEqual(len(other_records), 2)
        self.assertEqual(self.api.create_commit.call_count, 2)
        self.assertEqual(self.api.run_job.call_count, 2)
        self.assertEqual(sum(r['requestedHours'] for r in other_records), 9)
        self.assertFalse((self.directory / 'source.json').exists())
        self.assertTrue((self.directory / 'reservation.json').exists())
        loser = launch.read(self.directory / 'intent.json')['reservationOwner']
        winner = launch.read(other_directory / 'source.json')['reservationOwner']
        self.assertNotEqual(loser, winner)
        marker = launch.read(self.remote[launch.DATASET, f'multimap/{GROUP}/reservation.json', REVISION])
        self.assertEqual(marker['owner'], winner)
        self.assertTrue(all(c.kwargs['parent_commit'] == 'd' * 40 for c in self.api.create_commit.call_args_list))
        self.assertTrue(all(c.kwargs['revision'] == 'd' * 40 for c in self.api.file_exists.call_args_list))
        with self.assertRaisesRegex(ValueError, 'Existing group'): self.start()
        self.assertEqual(self.api.run_job.call_count, 2)
        self.api.upload_file.assert_not_called()

    def test_unknown_remote_reservation_success_blocks_fresh_coordinator_without_retry(self):
        original = self.commit
        def unknown(**kwargs):
            original(**kwargs)
            raise TimeoutError('fixture CAS succeeded, response lost')
        self.api.create_commit.side_effect = unknown
        with self.assertRaises(TimeoutError): self.start()
        other_root = self.root / 'other-worktree'
        shutil.copytree(self.root / 'ai/multimap', other_root / 'ai/multimap')
        with patch.object(launch, 'ROOT', other_root), \
             patch.object(launch, 'PROTOCOL_PATH', other_root / 'ai/multimap/replica-stress-protocol-v1.json'), \
             self.assertRaisesRegex(ValueError, 'already reserved'):
            launch.launch(GROUP, other_root / 'ai/runs' / GROUP)
        self.assertEqual(self.api.create_commit.call_count, 1)
        self.api.run_job.assert_not_called()

    def test_remote_owner_current_head_must_still_match_for_missing_peer(self):
        self.partial()
        latest = 'f' * 40
        self.copy_revision(launch.DATASET, REVISION, latest)
        path = self.remote[launch.DATASET, f'multimap/{GROUP}/reservation.json', latest]
        changed = launch.read(path); changed['owner'] = 'f' * 32; atomic_json(path, changed)
        self.api.dataset_info.return_value.sha = latest
        with self.assertRaisesRegex(ValueError, 'Remote group reservation changed'):
            launch.continue_panel(self.receipt(), GROUP + '-mixed', missing_panel='mixed')
        self.assertEqual(self.api.run_job.call_count, 1)
        self.assertFalse(launch.slot(self.directory, 'mixed').exists())

    def test_remote_owner_original_and_latest_markers_bound_for_recovery(self):
        self.both()
        path = self.remote[launch.DATASET, f'multimap/{GROUP}/reservation.json', REVISION]
        changed = launch.read(path); changed['sourceSha256'] = 'f' * 64; atomic_json(path, changed)
        with self.assertRaisesRegex(ValueError, 'Remote group reservation changed'): self.resume()
        self.assertEqual(self.api.run_job.call_count, 2)
        self.assertFalse(launch.slot(self.directory, 'recovery').exists())

    def test_stale_incomplete_cannot_hide_new_complete_or_steal_mixed_priority(self):
        self.both()
        latest = 'f' * 40
        self.copy_revision(launch.MODEL, SNAPSHOT, latest)
        source = launch.read(self.directory / 'source.json')
        completed = write_snapshot(self.root / 'latest-complete', source, 'strong',
                                   worker.production_identity(self.preflight, 'strong'), 640)
        self.publish_snapshot(completed, 'strong', revision=latest)
        self.api.model_info.return_value.sha = latest
        for panel in launch.PANELS:
            with self.subTest(panel=panel), self.assertRaisesRegex(ValueError, 'Stale original snapshot'):
                self.resume(panel)
        self.assertEqual(self.api.run_job.call_count, 2)
        self.assertFalse(launch.slot(self.directory, 'recovery').exists())
        # Current evidence permits only mixed, even though both original jobs
        # timed out; the completed strong output is marked for separate audit.
        record = launch.continue_panel(self.receipt('mixed'), GROUP + '-recovery-mixed',
                                       revision=latest, peer_revision=latest)
        self.assertEqual(record['panel'], 'mixed')
        self.assertEqual(record['resumeRevision'], latest)
        self.assertEqual(record['completeAfterErrorRequiresAudit'], ['strong'])
        self.assertEqual(record['originalSnapshotAuthority']['revision'], latest)
        self.assertEqual(record['lastSnapshotAuthority']['revision'], latest)
        self.assertEqual(self.api.run_job.call_count, 3)

    def test_stale_incomplete_cannot_hide_new_failed_snapshot(self):
        self.both()
        latest = 'f' * 40
        self.copy_revision(launch.MODEL, SNAPSHOT, latest)
        base = self.root / ('immutable-' + latest) / 'runs' / (GROUP + '-strong')
        status = worker.read(base / 'status.json')
        status.update(stage='failed', error={'code': 'replica-stress-job-stopped'})
        atomic_json(base / 'status.json', status)
        self.publish_snapshot(base, 'strong', revision=latest)
        self.api.model_info.return_value.sha = latest
        with self.assertRaisesRegex(ValueError, 'Stale original snapshot'): self.resume()
        with self.assertRaisesRegex(ValueError, 'worker/game failure'):
            launch.continue_panel(self.receipt(), GROUP + '-recovery-strong', revision=latest, peer_revision=latest)
        self.assertEqual(self.api.run_job.call_count, 2)
        self.assertFalse(launch.slot(self.directory, 'recovery').exists())

    def test_latest_authority_rechecked_after_audits_before_recovery_slot(self):
        self.both()
        latest = 'f' * 40
        self.copy_revision(launch.MODEL, SNAPSHOT, latest)
        base = self.root / ('immutable-' + latest) / 'runs' / (GROUP + '-strong')
        status = worker.read(base / 'status.json'); status['stage'] = 'failed'
        atomic_json(base / 'status.json', status)
        self.publish_snapshot(base, 'strong', revision=latest)
        # Initially HEAD still names the good snapshot. Move it only after the
        # full current payload audits and priority choice have already passed.
        def move_head(*args): self.api.model_info.return_value.sha = latest
        self.archive_check.side_effect = move_head
        with self.assertRaisesRegex(ValueError, 'changed during recovery audit'): self.resume()
        self.assertEqual(self.api.run_job.call_count, 2)
        self.assertFalse(launch.slot(self.directory, 'recovery').exists())

    def test_unrelated_new_repository_commit_same_manifests_uses_authoritative_head(self):
        self.both()
        latest = 'f' * 40
        self.copy_revision(launch.MODEL, SNAPSHOT, latest)
        self.api.model_info.return_value.sha = latest
        record = self.resume()
        self.assertEqual(record['requestedSnapshotRevisions'], {'strong': SNAPSHOT, 'mixed': SNAPSHOT})
        self.assertEqual(record['resumeRevision'], latest)
        self.assertEqual(record['env']['RESUME_REVISION'], latest)
        self.assertEqual(record['resumeAudit']['revision'], latest)

    def test_raw_sdk_status_exposure_and_ssh_are_rejected(self):
        self.both()
        receipt = launch.read(self.receipt()); job = self.jobs['job1']
        raw = dict(id=job.id, environment=job.environment, dockerImage=job.docker_image, flavor=job.flavor,
                   command=job.command, arguments=[], labels=job.labels, timeoutSeconds=21600,
                   status=dict(stage='ERROR', message='Job timeout'))
        original_inspect = INSPECT_ACTUAL
        self.api.endpoint = 'https://offline.invalid'
        response = Mock(); response.json.side_effect = lambda: copy.deepcopy(raw)
        session = Mock(); session.get.return_value = response
        for field, value in (('exposeUrls', ['https://fixture.hf.jobs']), ('sshUrl', 'ssh://fixture.hf.jobs')):
            raw['status'][field] = value
            with self.subTest(field=field), patch.object(launch, 'get_session', return_value=session), \
                 patch.object(launch, 'hf_raise_for_status'):
                inspected = original_inspect(self.api, 'job1')
                with self.assertRaisesRegex(ValueError, 'Actual HF job config'):
                    launch.validate_job(inspected, receipt, job.command)
            raw['status'].pop(field)
        self.assertEqual(self.api.run_job.call_count, 2)

    def test_archive_distinguishes_pinned_historical_ppo0_from_current_serving(self):
        historical = copy.deepcopy(launch.PROTOCOL['ppo0HistoricalTraining'])
        current = {}
        for name in historical['sourceFiles']:
            content = (HERE / name).read_bytes()
            self.source_files['ai/multimap/' + name] = content
            path = self.root / 'ai/multimap' / name; path.write_bytes(content)
            current[name] = launch.sha_bytes(content)
        for identity in self.identities.values():
            provenance = identity['modelProvenance']['ppo0']
            provenance['config']['sourceFiles'] = current
            provenance['checkpointConfig'] = dict(provenance['config'], sourceFiles=historical['sourceFiles'])
            provenance['historicalTrainingSource'] = historical
        self.save_preflight()
        records = self.start()
        self.assertEqual(len(records), 2)
        self.assertNotEqual(current, historical['sourceFiles'])
        source = launch.read(self.directory / 'source.json')
        changed = copy.deepcopy(self.preflight)
        for identity in changed['smokeIdentities'].values():
            identity['modelProvenance']['ppo0']['config']['sourceFiles']['ppo.py'] = 'e' * 64
        # The archived preflight itself is also bound; a caller cannot replace
        # a serving hash with the historical hash to admit a different bundle.
        with self.assertRaises(ValueError):
            launch.verify_archive(self.directory / 'source.tgz', source, changed, self.source_files[launch.LAUNCHER_NAME])

    def test_all_source_tar_members_types_paths_duplicates_coverage_and_commit(self):
        self.start(); original_source = launch.read(self.directory / 'source.json')
        for kind in ('symlink', 'hardlink', 'traversal', 'absolute', 'duplicate', 'commit', 'coverage'):
            path = self.root / (kind + '.tgz')
            with tarfile.open(path, 'w:gz') as tar:
                content = json.dumps(dict(gitCommit=('f' * 40 if kind == 'commit' else COMMIT),
                                          files={'missing': 'f' * 64})).encode()
                member = tarfile.TarInfo('source-manifest.json'); member.size = len(content)
                tar.addfile(member, io.BytesIO(content))
                if kind == 'duplicate': tar.addfile(member, io.BytesIO(content))
                if kind in ('symlink', 'hardlink', 'traversal', 'absolute'):
                    extra = tarfile.TarInfo('../bad' if kind == 'traversal' else '/bad' if kind == 'absolute' else 'bad')
                    if kind in ('symlink', 'hardlink'):
                        extra.type = tarfile.SYMTYPE if kind == 'symlink' else tarfile.LNKTYPE
                        extra.linkname = '/etc/passwd'
                    tar.addfile(extra)
            source = dict(original_source, sourceBytes=path.stat().st_size, sourceSha256=digest(path))
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                launch.verify_archive(path, source, self.preflight, self.source_files[launch.LAUNCHER_NAME])


# Keep an unmocked reference to exercise actual archived-evidence verification.
VERIFY_PREFLIGHT = launch.verify_preflight_archive
INSPECT_ACTUAL = launch.inspect_actual


class ArchivedEvidenceTests(LauncherTests):
    # Avoid inheriting the launcher test methods a second time in discovery.
    def make_evidence(self):
        base = self.root / 'preflight-evidence'
        report = {k: v for k, v in self.preflight.items() if k != 'privateEvidence'}
        atomic_json(base / 'report.json', report)
        for name in launch.SOURCE_NAMES:
            path = base / 'source' / name; path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(self.source_files['ai/multimap/' + name])
        for panel in launch.PANELS:
            config = self.identities[panel]
            groups = study.batches(config['tasks'])
            games = [outcome(spec) for spec in config['tasks']]
            for mode in ('uninterrupted', 'resumed'):
                folder = base / (panel + '-' + mode)
                atomic_json(folder / 'plan.json', config)
                atomic_json(folder / 'summary.json', study.analyze(games, panel, True))
                for index, tasks in enumerate(groups):
                    atomic_json(folder / f'batch-{index:03}.json', dict(schema='multimap-replica-stress-batch-v1',
                        index=index, taskSha256=study.task_hash(tasks), games=[outcome(spec) for spec in tasks]))
        evidence = self.preflight['privateEvidence']
        evidence['files'] = {p.relative_to(base).as_posix(): digest(p) for p in base.rglob('*') if p.is_file()}
        evidence['bytes'] = sum(p.stat().st_size for p in base.rglob('*') if p.is_file())
        for name in evidence['files']:
            self.remote[launch.MODEL, evidence['prefix'] + '/' + name, evidence['revision']] = base / name
        return base

    def test_actual_remote_archive_checks_all_source_smoke_batches_replays(self):
        self.make_evidence()
        result = VERIFY_PREFLIGHT(self.api, self.preflight, self.directory.parent)
        self.assertEqual(result['exactReplayMatches'], 198)
        first_download = next(i for i, (kind, _) in enumerate(self.events) if kind == 'download')
        self.assertEqual(first_download, len(self.preflight['privateEvidence']['files']))

    def test_remote_verified_boolean_never_substitutes_hash_evidence(self):
        base = self.make_evidence()
        self.preflight['privateEvidence']['remoteVerified'] = True
        report = base / 'report.json'
        report.write_bytes(b'!' + report.read_bytes()[1:])
        with self.assertRaisesRegex(ValueError, 'hash mismatch'):
            VERIFY_PREFLIGHT(self.api, self.preflight, self.directory.parent)

    def test_remote_report_missing_count_rejected_even_with_updated_hash(self):
        base = self.make_evidence(); report = worker.read(base / 'report.json'); report.pop('totalTerminalGames')
        atomic_json(base / 'report.json', report)
        evidence = self.preflight['privateEvidence']; evidence['files']['report.json'] = digest(base / 'report.json')
        evidence['bytes'] = sum((base / n).stat().st_size for n in evidence['files'])
        with self.assertRaisesRegex(ValueError, 'Incomplete archived'):
            VERIFY_PREFLIGHT(self.api, self.preflight, self.directory.parent)

    def test_remote_metadata_budget_fails_before_any_download(self):
        self.make_evidence()
        launch.remote_size.side_effect = lambda *args, **kwargs: 64 * 1024**2
        with self.assertRaisesRegex(ValueError, 'aggregate metadata'):
            VERIFY_PREFLIGHT(self.api, self.preflight, self.directory.parent)
        launch.hf_hub_download.assert_not_called()


# Only the four archive-specific methods are inherited into discovery; fixture
# helpers remain available without running all launcher cases twice.
for _name in list(LauncherTests.__dict__):
    if _name.startswith('test_') and _name not in ArchivedEvidenceTests.__dict__:
        setattr(ArchivedEvidenceTests, _name, None)


class APIContractTests(unittest.TestCase):
    def test_hub129_raw_timeout_required_and_secrets_never_returned(self):
        raw = dict(id='job1', dockerImage=launch.IMAGE, timeoutSeconds=21600,
                   environment={'SOURCE_COMMIT': COMMIT}, labels={}, status=dict(stage='ERROR', message='Job timeout'),
                   secrets={'HF_TOKEN': 'MUST-NOT-LEAK'})
        api = NS(endpoint='https://offline.invalid', _build_hf_headers=lambda: {'authorization': 'fixture'})
        response = Mock(); response.json.return_value = raw
        session = Mock(); session.get.return_value = response
        with patch.object(launch, 'get_session', return_value=session), patch.object(launch, 'hf_raise_for_status'):
            actual = launch.inspect_actual(api, 'job1')
        self.assertEqual(actual.timeout_seconds, 21600)
        self.assertEqual(actual.status.message, 'Job timeout')
        self.assertNotIn('secrets', vars(actual))
        self.assertNotIn('MUST-NOT-LEAK', repr(actual))
        self.assertEqual(session.get.call_args.kwargs['timeout'], 30)


class BootstrapTests(unittest.TestCase):
    def archive(self, path, kind):
        files = {'ai/multimap/worker.py': b'# fixture only\n'}
        manifest = dict(gitCommit=('f' * 40 if kind == 'commit' else COMMIT),
                        files={n: launch.sha_bytes(v) for n, v in files.items()})
        if kind == 'coverage': manifest['files']['missing'] = 'f' * 64
        files['source-manifest.json'] = json.dumps(manifest).encode()
        with tarfile.open(path, 'w:gz') as tar:
            for name, content in files.items():
                item = tarfile.TarInfo(name); item.size = len(content); tar.addfile(item, io.BytesIO(content))
                if kind == 'duplicate': tar.addfile(item, io.BytesIO(content))
            if kind in ('symlink', 'hardlink', 'traversal', 'absolute', 'fifo'):
                item = tarfile.TarInfo('../bad' if kind == 'traversal' else '/bad' if kind == 'absolute' else 'bad')
                if kind in ('symlink', 'hardlink'):
                    item.type = tarfile.SYMTYPE if kind == 'symlink' else tarfile.LNKTYPE; item.linkname = '/etc/passwd'
                if kind == 'fifo': item.type = tarfile.FIFOTYPE
                tar.addfile(item)

    def test_actual_bootstrap_metadata_first_full_manifest_safe_members(self):
        import sys
        for kind in ('valid', 'metadata', 'hash', 'commit', 'coverage', 'duplicate', 'symlink', 'hardlink', 'traversal', 'absolute', 'fifo'):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as directory, ExitStack() as stack:
                root = Path(directory); archive = root / 'source.tgz'; self.archive(archive, kind)
                source = root / 'unpacked'
                hub = NS(get_hf_file_metadata=Mock(return_value=NS(commit_hash=REVISION,
                         size=launch.LIMIT if kind == 'metadata' else archive.stat().st_size)),
                         hf_hub_url=Mock(return_value='offline://fixture'), get_token=Mock(return_value='fixture'),
                         hf_hub_download=Mock(return_value=str(archive)))
                stack.enter_context(patch.dict(sys.modules, huggingface_hub=hub))
                stack.enter_context(patch.dict(os.environ, dict(SOURCE_REVISION=REVISION, SOURCE_PATH='source.tgz',
                    DATASET_REPO=launch.DATASET, SOURCE_COMMIT=COMMIT,
                    SOURCE_SHA256='f' * 64 if kind == 'hash' else digest(archive), PATH='/usr/bin'), clear=True))
                pip = stack.enter_context(patch.object(launch.subprocess, 'run', side_effect=RuntimeError('fixture reached install boundary')))
                stack.enter_context(patch.object(os, 'chdir'))
                execute = stack.enter_context(patch.object(os, 'execvp', side_effect=AssertionError('must never exec in fixture')))
                script = launch.BOOTSTRAP.replace("Path('/tmp/multimap-source')", 'Path(' + repr(str(source)) + ')')
                with self.assertRaisesRegex(RuntimeError, 'install boundary') if kind == 'valid' else self.assertRaises((AssertionError, KeyError)):
                    exec(compile(script, '<bounded-bootstrap-fixture>', 'exec'), {})
                if kind == 'valid': pip.assert_called_once()
                else: pip.assert_not_called()
                if kind == 'metadata': hub.hf_hub_download.assert_not_called()
                execute.assert_not_called()


class StorageTests(unittest.TestCase):
    def test_decimal_eight_gb_and_two_gib_free_plus_one_gib_reserve(self):
        with tempfile.TemporaryDirectory() as directory, ExitStack() as stack:
            root = Path(directory); runs = root / 'ai/runs'; runs.mkdir(parents=True)
            (runs / 'multimap-existing').mkdir()
            stack.enter_context(patch.object(launch, 'ROOT', root))
            inherited = stack.enter_context(patch.object(launch, 'inherited_storage_check'))
            tree = stack.enter_context(patch.object(launch, 'tree_bytes', return_value=8_000_000_000 - 1024**3))
            disk = stack.enter_context(patch.object(launch.shutil, 'disk_usage', return_value=NS(free=3 * 1024**3)))
            launch.check_local_storage(runs / GROUP)
            inherited.assert_called_once()
            tree.return_value += 1
            with self.assertRaisesRegex(ValueError, 'headroom'): launch.check_local_storage(runs / GROUP)
            tree.return_value = 0
            disk.return_value.free -= 1
            with self.assertRaisesRegex(ValueError, 'headroom'): launch.check_local_storage(runs / GROUP)
            inherited.side_effect = RuntimeError('inherited guard')
            with self.assertRaisesRegex(RuntimeError, 'inherited guard'): launch.check_local_storage(runs / GROUP)


if __name__ == '__main__':
    unittest.main()
