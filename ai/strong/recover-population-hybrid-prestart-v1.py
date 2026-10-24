"""One reviewed exact replacement of the terminal prestart failure.

Does not resume the coordinator or retry a replacement. Original failure/guard
are archived before mutation; every experiment/execution field stays identical.
"""
import argparse
from contextlib import ExitStack
from datetime import datetime, timezone
import fcntl
import importlib.util
from pathlib import Path

from huggingface_hub import HfApi
from strategic_collection import ROOT, read, write, digest

FAILED = ROOT / 'ai/runs/population-hybrid-prestart-failure-v1'
ADMISSION = ROOT / 'ai/strong/population-hybrid-prestart-recovery-admission-v1.json'
RUN = ROOT / 'ai/runs/population-hybrid-prestart-recovery-v1'
COORDINATOR = ROOT / 'ai/runs/population-hybrid-development-coordinator-v1'
spec = importlib.util.spec_from_file_location('original_hybrid_prestart_manager', ROOT / 'ai/strong/manage-population-hybrid-development.py')
manager = importlib.util.module_from_spec(spec)
spec.loader.exec_module(manager)


def replacement_allowed(original, canonical, status, remote, *, coordinator_present, coordinator_stage):
    assert status['job_id'] == original['job_id']
    assert status['stage'] == 'ERROR', 'Only the confirmed terminal failed job may be replaced'
    assert status['started_at'] is None, 'This admission only covers the reviewed no-start failure'
    assert canonical == original and original['stage'] == 'launched'
    assert 'replaces_job_id' not in original and 'recovery_admission_sha256' not in original
    assert original['qualification_eligible'] is original['reserved_final_seeds_used'] is False
    assert not coordinator_present and coordinator_stage == 'stopped_with_error'
    assert remote['repo'] == 'coyotte508/powergrid-ai-germany-v1'
    assert remote['path'] == 'archives/' + original['case'] + '.tgz'
    assert remote['exists'] is False, 'Review existing artifacts before replacing their producer'


def admit():
    admission = read(ADMISSION)
    assert admission['maximum_replacements'] == 1 and admission['maximum_replacement_retries'] == 0
    assert admission['qualification_eligible'] is admission['reserved_final_seeds_used'] is False
    for name, sha in admission['failure_file_hashes'].items():
        assert digest(FAILED / name) == sha
    assert digest(ROOT / 'ai/strong/population-hybrid-prestart-failure-evidence-v1.json') == admission['failure_evidence_descriptor_sha256']
    assert admission['failure_evidence']['remote_archive_verified'] is True
    original = read(FAILED / 'original-guard.json')
    assert original['case'] == admission['case'] and original['job_id'] == admission['original_job_id']
    assert original['source'] == admission['source'] and original['plan_sha256'] == admission['plan_sha256']
    state = read(COORDINATOR / 'state.json')
    assert digest(COORDINATOR / 'state.json') == admission['original_coordinator_sha256']
    present = Path('/proc', str(state['pid']), 'cmdline').exists()
    plan, source, row = manager.admission(original['case'])
    assert original['source'] == source and original['row'] == row
    canonical = manager.GUARDS / (original['case'] + '.json')
    assert digest(canonical) == admission['original_guard_sha256']
    assert not (manager.COLLECTED / original['case'] / 'verified.json').exists()
    assert not (manager.COLLECTED / original['case'] / 'artifacts').exists()
    api = HfApi()
    job = api.inspect_job(job_id=original['job_id'])
    status = {'job_id': job.id, 'stage': job.status.stage, 'message': job.status.message,
              'started_at': str(job.started_at) if job.started_at else None,
              'finished_at': str(job.finished_at) if job.finished_at else None,
              'checked_at': datetime.now(timezone.utc).isoformat()}
    repo = 'coyotte508/powergrid-ai-germany-v1'
    revision = api.model_info(repo).sha
    remote = {'repo': repo, 'revision': revision, 'path': 'archives/' + original['case'] + '.tgz'}
    remote['exists'] = api.file_exists(repo, remote['path'], revision=revision)
    replacement_allowed(original, read(canonical), status, remote,
                        coordinator_present=present, coordinator_stage=state['stage'])
    previous_hashes = read(FAILED / 'original-guard-hashes.json')
    assert {p.stem: digest(p) for p in manager.GUARDS.glob('*.json')} == previous_hashes
    return admission, original, status, remote, previous_hashes


def main(execute):
    with ExitStack() as locks:
        for path in [COORDINATOR / 'coordinator.lock', ROOT / 'ai/runs/.population-hybrid-prestart-recovery.lock']:
            stream = locks.enter_context(path.open('a'))
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        admission, original, status, remote, before = admit()
        if not execute:
            print({'case': original['case'], 'terminal_status': status['stage'],
                   'remote_artifact_exists': remote['exists'], 'execute': False})
            return
        RUN.mkdir(exist_ok=False)
        attempts = RUN / 'replacement-guards'
        attempts.mkdir()
        state = {'stage': 'launching_exact_replacement', 'case': original['case'],
                 'original_job_id': original['job_id'], 'admission_sha256': digest(ADMISSION),
                 'script_sha256': digest(Path(__file__)), 'fresh_original_status': status,
                 'fresh_artifact_check': remote, 'automatic_retries': False,
                 'coordinator_resumed': False, 'qualification_eligible': False,
                 'reserved_final_seeds_used': False}
        write(RUN / 'state.json', state)
        canonical_guards = manager.GUARDS
        try:
            try:
                manager.GUARDS = attempts
                manager.launch(original['case'], execute=True)
            finally:
                manager.GUARDS = canonical_guards
            attempt_path = attempts / (original['case'] + '.json')
            new = read(attempt_path)
            assert new['stage'] == 'launched' and new['job_id'] != original['job_id']
            assert set(new) == set(original)
            for key in original:
                if key not in admission['unchanged_fields_except']:
                    assert new[key] == original[key], key
            new.update(replaces_job_id=original['job_id'],
                       original_guard_sha256=admission['original_guard_sha256'],
                       recovery_admission_sha256=digest(ADMISSION),
                       original_failure_evidence=admission['failure_evidence'])
            write(attempt_path, new)
            new_job = HfApi().inspect_job(job_id=new['job_id'])
            state.update(replacement_job_id=new['job_id'], replacement_status=new_job.status.stage)
            write(RUN / 'state.json', state)
            assert new_job.status.stage in ['SCHEDULING', 'RUNNING', 'COMPLETED'], 'Replacement failed; preserve it and do not retry automatically'
            canonical = canonical_guards / (original['case'] + '.json')
            assert digest(canonical) == admission['original_guard_sha256']
            temporary = canonical.with_suffix('.recovery.tmp')
            with temporary.open('x') as stream:
                import json
                stream.write(json.dumps(new, indent=2) + '\n')
            temporary.replace(canonical)
            for case, sha in before.items():
                if case != original['case']:
                    assert digest(canonical_guards / (case + '.json')) == sha
            assert len(list(canonical_guards.glob('*.json'))) == len(before)
            state.update(stage='replacement_installed_coordinator_not_resumed',
                         installed_guard_sha256=digest(canonical), other_guards_unchanged=len(before)-1)
            write(RUN / 'state.json', state)
            print({k: state[k] for k in ['stage', 'case', 'original_job_id', 'replacement_job_id', 'replacement_status', 'other_guards_unchanged']}, flush=True)
        except BaseException as error:
            state.update(stage='stopped_with_error', error=type(error).__name__ + ': ' + str(error))
            write(RUN / 'state.json', state)
            raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--execute', action='store_true')
    main(parser.parse_args().execute)
