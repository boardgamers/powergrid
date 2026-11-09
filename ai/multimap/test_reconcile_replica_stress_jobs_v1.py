"""Offline decoder/binding/continuation conformance. No HF calls, jobs or games.

The original launch fixtures create temporary ledgers with FakeAPI metadata.
Integration tests run the REAL new decoder and unchanged old guard call graph;
only their already-offline storage/Git/HF boundaries remain fixture endpoints.
"""
import copy
from contextlib import redirect_stderr, redirect_stdout
import io
from pathlib import Path
import shutil
from types import SimpleNamespace as NS
import unittest
from unittest.mock import Mock, patch

import launch_replica_stress_v1 as old
import reconcile_replica_stress_jobs_v1 as reconcile
import replica_stress_study_v1 as study
import test_launch_replica_stress_v1 as fixtures

SECRET = 'PRIVATE-RESPONSE-MUST-NOT-BE-RETAINED'


def raw_job(job):
    return dict(id=job.id, environment=copy.deepcopy(job.environment), dockerImage=job.docker_image,
                flavor=job.flavor, command=copy.deepcopy(job.command), arguments=job.arguments,
                labels=copy.deepcopy(job.labels), volumes=job.volumes, spaceId=job.space_id,
                timeout=job.timeout_seconds, expose={'ports': []}, ssh={'enabled': False},
                status=dict(stage=job.status.stage, message=job.status.message,
                            exposeUrls=getattr(job.status, 'expose_urls', None),
                            sshUrl=getattr(job.status, 'ssh_url', None), secrets=SECRET),
                secrets={'HF_TOKEN': SECRET}, internal={'accessToken': SECRET})


class DecoderTests(unittest.TestCase):
    def setUp(self):
        source = dict(group=old.GROUP, sourceCommit=reconcile.SOURCE_GIT,
                      sourceRevision=reconcile.SOURCE_REVISION, sourceSha256=reconcile.SOURCE_SHA256,
                      sourcePath=f'multimap/{old.GROUP}/source.tgz', preflightSha256='a' * 64)
        self.receipt = dict(old.intent_for(source, 'strong', 1, old.GROUP + '-strong'), jobId='job1')
        self.command = old.command_for(old.BOOTSTRAP)
        self.raw = dict(id='job1', environment=self.receipt['env'], dockerImage=old.IMAGE,
                        flavor='cpu-upgrade', command=self.command, arguments=[],
                        labels=dict(old.labels_for(old.GROUP, 'strong', 1, 'strong'), name=self.receipt['run']),
                        volumes=None, spaceId=None, timeout=21600, expose={'ports': []}, ssh={'enabled': False},
                        status=dict(stage='RUNNING', message=None, secrets={'token': SECRET}),
                        secrets={'HF_TOKEN': SECRET}, internal={'accessToken': SECRET})

    def valid(self, raw):
        actual = reconcile.decode_actual(raw)
        old.validate_job(actual, self.receipt, self.command)
        return actual

    def test_current_response_integer_timeout_disabled_objects_is_valid(self):
        actual = self.valid(self.raw)
        self.assertEqual(actual.timeout_seconds, 21600)
        self.assertIs(actual.expose, False)
        self.assertIs(actual.ssh, False)
        self.assertEqual(actual.status.stage, 'RUNNING')
        self.assertIsNone(actual.status.expose_urls)
        self.assertIsNone(actual.status.ssh_url)

    def test_old_alias_and_all_supported_disabled_shapes(self):
        self.raw['timeoutSeconds'] = self.raw.pop('timeout')
        for expose in (None, False, [], {'ports': []}):
            for ssh in (None, False, {'enabled': False}):
                with self.subTest(expose=expose, ssh=ssh):
                    self.valid(dict(self.raw, expose=expose, ssh=ssh))
        self.raw.pop('expose'); self.raw.pop('ssh')
        self.valid(self.raw)

    def test_equal_aliases_allowed_conflicts_rejected(self):
        self.valid(dict(self.raw, timeoutSeconds=21600))
        for value in (10800, 21601):
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, 'aliases conflict'):
                reconcile.decode_actual(dict(self.raw, timeoutSeconds=value))

    def test_every_alias_must_be_positive_exact_integer_no_fallback(self):
        for alias in ('timeout', 'timeoutSeconds'):
            other = 'timeout' if alias == 'timeoutSeconds' else 'timeoutSeconds'
            for value in (True, False, None, 0, -1, 21600.0, '21600', '6h', [], {}):
                for include_other in (False, True):
                    raw = {k: v for k, v in self.raw.items() if k != 'timeout'}
                    raw[alias] = value
                    if include_other: raw[other] = 21600
                    with self.subTest(alias=alias, value=value, include_other=include_other), \
                         self.assertRaisesRegex(ValueError, 'timeout missing or invalid'):
                        reconcile.decode_actual(raw)
        self.raw.pop('timeout')
        # The receipt still has 6h. No receipt value can supply missing metadata.
        self.assertEqual(self.receipt['timeout'], '6h')
        with self.assertRaisesRegex(ValueError, 'timeout missing'):
            reconcile.decode_actual(self.raw)

    def test_valid_but_wrong_actual_timeout_rejected_by_old_validator(self):
        with self.assertRaisesRegex(ValueError, 'Actual HF job config'):
            self.valid(dict(self.raw, timeout=10800))

    def test_unknown_or_active_expose_rejected_not_coerced_by_truthiness(self):
        values = (True, 0, 0.0, '', 'false', (), {}, [8000], {'ports': [8000]}, {'ports': None},
                  {'ports': False}, {'ports': ()}, {'ports': [] , 'enabled': False}, {'enabled': False})
        for value in values:
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, 'expose configuration'):
                reconcile.decode_actual(dict(self.raw, expose=value))

    def test_unknown_or_active_ssh_rejected_with_strict_boolean(self):
        values = (True, 0, 0.0, '', 'false', [], {}, {'enabled': True}, {'enabled': 0}, {'enabled': None},
                  {'enabled': 'false'}, {'enabled': False, 'port': None}, {'ports': []})
        for value in values:
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, 'SSH configuration'):
                reconcile.decode_actual(dict(self.raw, ssh=value))

    def test_status_active_endpoints_preserved_and_rejected_even_when_config_disabled(self):
        for field, value in (('exposeUrls', ['https://offline.invalid']), ('exposeUrls', {'8000': 'active'}),
                             ('sshUrl', 'ssh://offline.invalid')):
            raw = dict(self.raw, status=dict(self.raw['status'], **{field: value}))
            actual = reconcile.decode_actual(raw)
            self.assertEqual(getattr(actual.status, 'expose_urls' if field == 'exposeUrls' else 'ssh_url'), value)
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, 'Actual HF job config'):
                old.validate_job(actual, self.receipt, self.command)

    def test_malformed_raw_and_status_fail_closed(self):
        for raw in (None, [], 'body', dict(self.raw, status=None), dict(self.raw, status=[])):
            with self.subTest(raw_type=type(raw).__name__), self.assertRaises(ValueError):
                reconcile.decode_actual(raw)

    def test_only_old_allowlist_and_no_secrets_or_raw_body_retained(self):
        before = copy.deepcopy(self.raw)
        output = io.StringIO()
        with redirect_stdout(output), redirect_stderr(output):
            actual = self.valid(self.raw)
        self.assertEqual(self.raw, before)
        self.assertEqual(set(vars(actual)), {'id', 'environment', 'docker_image', 'flavor', 'command', 'arguments',
                         'labels', 'volumes', 'space_id', 'timeout_seconds', 'status', 'expose', 'ssh'})
        self.assertEqual(set(vars(actual.status)), {'stage', 'message', 'expose_urls', 'ssh_url'})
        self.assertNotIn(SECRET, repr(actual))
        self.assertEqual(output.getvalue(), '')

    def test_inspector_one_authenticated_get_without_jobinfo_or_extra_api_calls(self):
        api = Mock(endpoint='https://offline.invalid')
        api._build_hf_headers.return_value = {'authorization': 'Bearer fixture'}
        response = Mock(); response.json.return_value = self.raw
        session = Mock(); session.get.return_value = response
        with patch.object(reconcile, 'get_session', return_value=session), \
             patch.object(reconcile, 'hf_raise_for_status') as raise_status:
            actual = reconcile.inspect_actual(api, 'job1')
        old.validate_job(actual, self.receipt, self.command)
        session.get.assert_called_once_with(f'https://offline.invalid/api/jobs/{old.NAMESPACE}/job1',
                                            headers={'authorization': 'Bearer fixture'}, timeout=30)
        response.json.assert_called_once_with()
        raise_status.assert_called_once_with(response)
        self.assertEqual([call[0] for call in api.mock_calls], ['_build_hf_headers'])
        self.assertNotIn(SECRET, repr(actual))

    def test_request_failure_sanitized_and_not_retried(self):
        api = NS(endpoint='https://offline.invalid', _build_hf_headers=lambda: {})
        for fail_at in ('get', 'status', 'json'):
            session = Mock(); response = session.get.return_value
            raise_status = Mock()
            target = {'get': session.get, 'status': raise_status, 'json': response.json}[fail_at]
            target.side_effect = RuntimeError(SECRET)
            output = io.StringIO()
            with self.subTest(fail_at=fail_at), patch.object(reconcile, 'get_session', return_value=session), \
                 patch.object(reconcile, 'hf_raise_for_status', raise_status), redirect_stdout(output), \
                 redirect_stderr(output), self.assertRaisesRegex(ValueError, 'metadata request failed') as caught:
                reconcile.inspect_actual(api, 'job1')
            session.get.assert_called_once()
            self.assertNotIn(SECRET, str(caught.exception))
            self.assertEqual(output.getvalue(), '')

    def test_unsafe_job_id_rejected_before_session(self):
        for value in (None, 123, '', '../job', 'job?token=private', 'job/other'):
            with self.subTest(value=value), patch.object(reconcile, 'get_session') as session, \
                 self.assertRaisesRegex(ValueError, 'Unsafe job ID'):
                reconcile.inspect_actual(None, value)
            session.assert_not_called()


class BindingTests(unittest.TestCase):
    def test_private_call_graph_and_original_global_identities_unchanged(self):
        before = dict(vars(old))
        bound = reconcile._bound_functions()
        self.assertEqual(set(before), set(vars(old)))
        self.assertTrue(all(vars(old)[name] is value for name, value in before.items()))
        replacements = {
            'inventory': {'inspect_actual': reconcile.inspect_actual},
            'submit': {'inspect_actual': reconcile.inspect_actual},
            'continue_panel': {'inventory': bound.inventory, 'submit': bound.submit,
                               'preflight_gate': reconcile._preflight_gate},
        }
        for name, changes in replacements.items():
            original, private = getattr(old, name), getattr(bound, name)
            self.assertIs(private.__code__, original.__code__)
            self.assertIsNot(private.__globals__, original.__globals__)
            self.assertEqual(private.__defaults__, original.__defaults__)
            self.assertEqual(private.__kwdefaults__, original.__kwdefaults__)
            for key, value in original.__globals__.items():
                self.assertIs(private.__globals__[key], changes.get(key, value))
        for guard in ('validate_inventory', 'validate_job', 'verify_source_remote', 'verify_remote_reservation',
                      'verify_preflight_archive', 'snapshot_authority', 'verify_resume', 'choose_recovery',
                      'terminal_initials', 'original_command', 'locked', 'intent_for'):
            self.assertIs(bound.continue_panel.__globals__[guard], getattr(old, guard))
        self.assertIs(bound.submit.__globals__['_HELD_LOCKS'], old._HELD_LOCKS)
        self.assertFalse(hasattr(reconcile, 'launch'))

    def test_fixed_source_membership_and_real_committed_current_bytes(self):
        source = dict(sourceCommit=reconcile.SOURCE_GIT, sourceRevision=reconcile.SOURCE_REVISION,
                      sourceSha256=reconcile.SOURCE_SHA256)
        self.assertEqual(len(reconcile.FROZEN_SOURCE_NAMES), 13)
        self.assertEqual(reconcile.FROZEN_SOURCE_NAMES, old.SOURCE_NAMES)
        self.assertEqual(reconcile.FROZEN_SOURCE_NAMES, study.SOURCES)
        self.assertNotIn(Path(reconcile.__file__).name, study.SOURCES)
        self.assertNotIn(Path(__file__).name, study.SOURCES)
        reconcile.verify_frozen_source(source)  # Real local Git/files only, no preflight execution or HF.
        reconcile.verify_frozen_source(dict(source, sourceGit=reconcile.SOURCE_GIT))
        for field in ('sourceCommit', 'sourceGit', 'sourceRevision', 'sourceSha256'):
            with self.subTest(field=field), patch.object(reconcile.subprocess, 'check_output') as git, \
                 self.assertRaisesRegex(ValueError, 'frozen original source archive'):
                reconcile.verify_frozen_source(dict(source, **{field: 'f' * 40}))
            git.assert_not_called()

    def test_cli_has_no_initial_or_ambiguous_mode(self):
        base = ['--continue-launch', 'receipt.json', '--run-id', old.GROUP + '-mixed']
        invalid = ([], ['--group', old.GROUP], base, base + ['--missing-panel', 'strong'],
                   base + ['--resume-revision', 'a' * 40],
                   base + ['--missing-panel', 'mixed', '--peer-revision', 'b' * 40],
                   base + ['--missing-panel', 'mixed', '--resume-revision', 'a' * 40],
                   base + ['--output', 'somewhere', '--missing-panel', 'mixed'])
        for args in invalid:
            with self.subTest(args=args), patch.object(reconcile, 'continue_panel') as continuation, \
                 redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as caught:
                reconcile.main(args)
            self.assertEqual(caught.exception.code, 2)
            continuation.assert_not_called()
        with patch.object(reconcile, 'continue_panel') as continuation:
            reconcile.main(base + ['--missing-panel', 'mixed'])
            continuation.assert_called_once_with('receipt.json', old.GROUP + '-mixed', revision=None,
                                                 missing_panel='mixed', peer_revision=None)
        with patch.object(reconcile, 'continue_panel') as continuation:
            reconcile.main(base + ['--resume-revision', 'a' * 40, '--peer-revision', 'b' * 40])
            continuation.assert_called_once_with('receipt.json', old.GROUP + '-mixed', revision='a' * 40,
                                                 missing_panel=None, peer_revision='b' * 40)


class BoundContinuationTests(fixtures.LauncherTests):
    """Reuse original offline boundaries, not mocks of the new decoder/guards."""
    def setUp(self):
        commit_patch = patch.object(fixtures, 'COMMIT', reconcile.SOURCE_GIT)
        commit_patch.start(); self.addCleanup(commit_patch.stop)
        super().setUp()
        # Fixture archive is temporary and deterministic only within this test.
        # Substitute its exact revision/hash pins, NOT a bypass of either gate.
        self.mock(reconcile, 'SOURCE_REVISION', fixtures.REVISION)
        self.api.endpoint = 'https://offline.invalid'
        self.api._build_hf_headers.return_value = {'authorization': 'fixture'}
        self.session = Mock()
        self.session.get.side_effect = self.actual_response
        self.mock(reconcile, 'get_session', Mock(return_value=self.session))
        self.mock(reconcile, 'hf_raise_for_status', Mock())
        self.raw_changes = {}

    def actual_response(self, url, **kwargs):
        self.assertTrue(url.startswith(f'https://offline.invalid/api/jobs/{old.NAMESPACE}/'))
        self.assertEqual(kwargs, dict(headers={'authorization': 'fixture'}, timeout=30))
        job_id = url.rsplit('/', 1)[-1]
        raw = raw_job(self.jobs[job_id])
        raw.update(self.raw_changes.get(job_id, {}))
        response = Mock(); response.json.return_value = raw
        return response

    def start(self):
        try:
            return super().start()
        finally:
            if (self.directory / 'source.json').exists():
                source = old.read(self.directory / 'source.json')
                self.mock(reconcile, 'SOURCE_SHA256', source['sourceSha256'])

    def resume(self, panel='strong'):
        return reconcile.continue_panel(self.receipt(panel), old.GROUP + '-recovery-' + panel,
                                         revision=fixtures.SNAPSHOT, peer_revision=fixtures.SNAPSHOT)

    def missing(self):
        return reconcile.continue_panel(self.receipt(), old.GROUP + '-mixed', missing_panel='mixed')

    def test_failed_original_admission_consumed_strong_then_only_mixed_no_rewrite(self):
        # Reproduce the exact failure: original decoder drops timeout and passes
        # truthy disabled objects; strong's slot/receipt are already durable.
        self.mock(old, 'inspect_actual', fixtures.INSPECT_ACTUAL)
        self.mock(old, 'get_session', Mock(return_value=self.session))
        self.mock(old, 'hf_raise_for_status', Mock())
        with self.assertRaisesRegex(ValueError, 'Actual HF job config'):
            self.start()
        self.assertEqual(self.api.run_job.call_count, 1)
        strong = old.read(old.slot(self.directory, 'strong', 'receipts'))
        self.assertEqual((strong['requestedHours'], strong['timeout']), (6, '6h'))
        protected = [self.directory / name for name in ('source.json', 'intent.json', 'reservation.json')]
        protected += [old.slot(self.directory, 'strong', kind) for kind in ('intents', 'receipts')]
        protected += [self.receipt(), self.receipt().with_name('intent.json')]
        unchanged = {path: path.read_bytes() for path in protected}
        identities = dict(vars(old))
        record = self.missing()
        self.assertTrue(all(vars(old)[name] is value for name, value in identities.items()))
        self.assertEqual(unchanged, {path: path.read_bytes() for path in protected})
        self.assertEqual(record['source'], strong['source'])
        self.assertEqual(record['env']['SOURCE_COMMIT'], reconcile.SOURCE_GIT)
        self.assertEqual((record['slot'], record['requestedHours'], record['timeout']), ('mixed', 3, '3h'))
        self.assertTrue(record['sourceArchiveReusedExactly'])
        self.assertEqual(self.jobs['job2'].command, self.jobs['job1'].command)
        self.assertEqual(self.api.run_job.call_count, 2)
        self.assertEqual(self.api.create_commit.call_count, 1)
        self.assertEqual(self.package.call_count, 1)
        self.assertEqual(sum(old.read(p)['requestedHours'] for p in (self.directory / 'intents').glob('*.json')), 9)
        self.assertEqual(self.session.get.call_count, 4)  # Failed old admission + two inventories + mixed admission.
        for path in self.directory.rglob('*.json'):
            self.assertNotIn(SECRET, path.read_text())
        with self.assertRaisesRegex(ValueError, 'Budget slot already attempted'):
            self.missing()
        with self.assertRaisesRegex(ValueError, 'Only the missing mixed'):
            reconcile.continue_panel(self.receipt('mixed'), old.GROUP + '-strong', missing_panel='strong')
        self.assertEqual(self.api.run_job.call_count, 2)

    def test_source_only_anchor_is_not_initial_launch(self):
        self.partial('strong')
        with self.assertRaisesRegex(ValueError, 'no source-only initial launch'):
            reconcile.continue_panel(self.directory / 'source.json', old.GROUP + '-mixed', missing_panel='mixed')
        self.api.run_job.assert_not_called()

    def test_actual_bad_metadata_blocks_missing_peer_no_slot_consumed(self):
        self.partial()
        for change in ({'timeout': None}, {'timeoutSeconds': 10800}, {'expose': {'ports': [8000]}},
                       {'ssh': {'enabled': True}}, {'status': {'stage': 'RUNNING', 'sshUrl': 'ssh://active'}}):
            self.raw_changes['job1'] = change
            with self.subTest(change=change), self.assertRaises(ValueError): self.missing()
            self.assertEqual(self.api.run_job.call_count, 1)
            self.assertFalse(old.slot(self.directory, 'mixed').exists())

    def test_bound_submit_bad_admission_retains_mixed_attempt_without_retry(self):
        self.partial(); self.raw_changes['job2'] = {'timeout': None}
        with self.assertRaisesRegex(ValueError, 'timeout missing'): self.missing()
        self.assertTrue(old.slot(self.directory, 'mixed').exists())
        self.assertTrue(old.slot(self.directory, 'mixed', 'receipts').exists())
        with self.assertRaises(ValueError): self.missing()
        self.assertEqual(self.api.run_job.call_count, 2)

    def test_newer_head_allowed_but_frozen_source_stays_original(self):
        self.partial()
        previous_git = self.git
        newer = 'f' * 40
        def git(args, **kwargs):
            if args[1] == 'rev-parse': return newer + '\n'
            if args[1] == 'show' and args[2].startswith(newer + ':'):
                args = [*args[:2], reconcile.SOURCE_GIT + ':' + args[2].split(':', 1)[1]]
            return previous_git(args, **kwargs)
        old.subprocess.check_output.side_effect = git
        self.assertEqual(self.missing()['sourceCommit'], reconcile.SOURCE_GIT)
        self.assertEqual(self.package.call_count, 1)

    def test_changed_frozen_guard_rejected_even_if_head_and_disk_match(self):
        self.partial()
        path = self.root / old.LAUNCHER_NAME
        frozen = self.source_files[old.LAUNCHER_NAME]
        path.write_bytes(frozen + b'\n# changed guard\n')
        previous_git = self.git
        newer = 'f' * 40
        def git(args, **kwargs):
            if args[1] == 'rev-parse': return newer + '\n'
            if args[1] == 'show' and args[2].startswith(newer + ':'):
                content = (self.root / args[2].split(':', 1)[1]).read_bytes()
                return content.decode() if kwargs.get('text') else content
            return previous_git(args, **kwargs)
        old.subprocess.check_output.side_effect = git
        # Current HEAD/current-files alone are insufficient for a guard that is
        # not executed by the serving identity fixture. The fixed Git pin adds
        # a distinct check and rejects even this apparently clean newer HEAD.
        self.assertEqual(old.preflight_gate(), self.preflight)
        with self.assertRaisesRegex(ValueError, 'differs from SOURCE_GIT'): self.missing()
        self.assertEqual(self.api.run_job.call_count, 1)
        self.assertFalse(old.slot(self.directory, 'mixed').exists())

    def test_original_preflight_still_rejects_dirty_head_after_fixed_pin(self):
        self.partial()
        previous_git = self.git
        def git(args, **kwargs):
            return ' M changed.py' if args[1] == 'status' else previous_git(args, **kwargs)
        old.subprocess.check_output.side_effect = git
        with self.assertRaisesRegex(ValueError, 'Commit all'): self.missing()
        self.assertEqual(self.api.run_job.call_count, 1)

    def test_source_archive_pin_changed_blocks_before_inventory(self):
        self.partial()
        source = old.read(self.directory / 'source.json')
        source['sourceCommit'] = 'f' * 40
        old.atomic_json(self.directory / 'source.json', source)
        self.api.list_jobs.reset_mock()
        with self.assertRaisesRegex(ValueError, 'frozen original source archive'): self.missing()
        self.api.list_jobs.assert_not_called()
        self.assertEqual(self.api.run_job.call_count, 1)

    def test_private_evidence_guard_still_checks_real_archive_hashes(self):
        base = fixtures.ArchivedEvidenceTests.make_evidence(self)
        self.save_preflight()
        self.mock(old, 'verify_preflight_archive', fixtures.VERIFY_PREFLIGHT)
        self.partial()
        path = base / 'report.json'; path.write_bytes(b'!' + path.read_bytes()[1:])
        with self.assertRaisesRegex(ValueError, 'Archived preflight hash mismatch'): self.missing()
        self.assertFalse(old.slot(self.directory, 'mixed').exists())
        self.assertEqual(self.api.run_job.call_count, 1)

    def test_owner_change_blocks_bound_missing_peer(self):
        self.partial()
        path = self.remote[old.DATASET, f'multimap/{old.GROUP}/reservation.json', fixtures.REVISION]
        owner = old.read(path); owner['owner'] = 'f' * 32; old.atomic_json(path, owner)
        with self.assertRaisesRegex(ValueError, 'Remote group reservation changed'): self.missing()
        self.assertEqual(self.api.run_job.call_count, 1)

    def test_copied_ledger_rejected_by_bound_continuation(self):
        self.partial()
        saved = self.directory.with_name('old-ledger')
        self.directory.rename(saved); shutil.copytree(saved, self.directory)
        with self.assertRaisesRegex(ValueError, 'Copied/changed'): self.missing()
        self.assertEqual(self.api.run_job.call_count, 1)

    def test_bound_inventory_three_job_limit_with_real_decoder(self):
        self.start()
        third = copy.deepcopy(self.jobs['job1']); third.id = 'third'
        third.labels = dict(old.labels_for(old.GROUP, 'strong', 2, 'recovery'), name=old.GROUP + '-recovery-strong')
        self.jobs['third'] = third
        self.api.list_jobs.side_effect = lambda **kwargs: [*self.jobs.values(), third]
        with self.assertRaisesRegex(ValueError, 'three-job'):
            reconcile._bound_functions().inventory(self.api, old.GROUP)
        self.assertEqual(self.session.get.call_count, 3)

    # These existing assertions all route via the overridden resume() through
    # the privately bound real decoder, preserving all original guard logic.
    def test_bound_recovery_three_attempts_twelve_hours_priority(self):
        super().test_exact_twelve_hours_three_attempts_shared_recovery_strong_priority()

    def test_bound_recovery_requires_terminal_initials(self):
        super().test_both_initials_must_be_terminal_not_running_scheduling_or_pending()

    def test_bound_recovery_only_actual_timeout(self):
        super().test_only_actual_timeout_not_canceled_other_error_or_claimed_complete()

    def test_bound_recovery_uncertain_attempt_still_consumed(self):
        super().test_uncertain_recovery_permanently_consumes_shared_three_hour_slot()

    def test_bound_recovery_latest_authority_rechecked_before_slot(self):
        super().test_latest_authority_rechecked_after_audits_before_recovery_slot()

    def test_bound_recovery_original_archive_corruption_rejected(self):
        super().test_resume_corrupt_metadata_plan_batch_source_stops_before_paid_call()

    def test_bound_recovery_metadata_before_transfers(self):
        super().test_manifest_allmetadata_before_payload_in_both_panel_audits()

    def test_bound_recovery_mixed_cannot_steal_priority(self):
        super().test_mixed_cannot_steal_shared_slot_when_both_incomplete()


# Keep fixture helpers, without rediscovering the old suite under this subclass.
for _name in fixtures.LauncherTests.__dict__:
    if _name.startswith('test_') and _name not in BoundContinuationTests.__dict__:
        setattr(BoundContinuationTests, _name, None)


if __name__ == '__main__':
    unittest.main()
