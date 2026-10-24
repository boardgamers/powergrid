"""Recover exactly two confirmed failed uploads after the HF file limit is fixed."""
import argparse
from datetime import datetime, timezone
import fcntl
import hashlib
import importlib.util
import math
import os
import re
import subprocess

from huggingface_hub import HfApi, get_token
from huggingface_hub.errors import EntryNotFoundError
from strategic_collection import ROOT, read, write, digest
from policy_iteration_label_attempts import FAILURE_RETRIES, effective_guard

FAILED = {'2p-11101-snapshot0-neural-0504': '6adc221c1e112550ce7dc2c5',
          '5p-parent-economic-neural-0095': '6adc1f98046eb82b1ecd9b84'}


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    spec = importlib.util.spec_from_file_location('upload_retry_manager', ROOT/'ai/strong/manage-policy-iteration-labels.py')
    manager = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(manager)
    source = read(manager.SOURCE)
    for file, sha in source['overlays'].items():
        assert digest(ROOT/file) == sha
    profile_path = ROOT/'ai/strong/policy-iteration-cpu-upgrade-profile-results-v2.json'
    profile = read(profile_path)
    assert profile['verified'] and profile['rollouts'] == 3072
    assert profile['full_trajectories_and_choice_transcripts_match_reference']
    assert profile['all_microbenchmark_raw_outputs_identical']
    multiplier = max(1., profile['worst_case_upgrade_slowdown'])*1.25
    api = HfApi()
    repo = read(manager.PROTOCOL)['repo']
    revision = api.model_info(repo).sha
    files = [r for r in api.list_repo_tree(repo, recursive=True, revision=revision) if hasattr(r, 'blob_id')]
    assert len(files) <= 13000, 'Restore repository headroom before retrying'
    FAILURE_RETRIES.mkdir(exist_ok=True)
    with (FAILURE_RETRIES/'.launch.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        assert not list(FAILURE_RETRIES.glob('*.json')), 'Reconcile existing retries; never resubmit blindly'
        ready = []
        for shard, failed_id in FAILED.items():
            guard_path = manager.GUARDS/(shard+'.json')
            guard = effective_guard(guard_path)
            assert guard['job_id'] == failed_id and guard['source'] == source
            job = api.inspect_job(job_id=failed_id)
            assert job.status.stage == 'ERROR' and job.finished_at is not None
            logs = '\n'.join(api.fetch_job_logs(job_id=failed_id))
            assert 'over the limit of 20000 files' in logs and 'in upload_folder' in logs
            assert 'AssertionError' not in logs and 'During handling of the above exception' not in logs
            log_path = FAILURE_RETRIES/(shard+'.failed.log')
            if args.execute:
                log_path.write_text(logs)
            prefix = manager.PREFIX+shard
            try:
                present = list(api.list_repo_tree(repo, path_in_repo=prefix, recursive=True, revision=revision))
            except EntryNotFoundError:
                present = []
            assert not present, 'Inspect existing outputs before choosing a retry'
            seconds = math.ceil(guard['shard']['admission']['conservative_seconds']*multiplier)
            assert seconds <= .75*12*3600
            ready.append((shard, guard, log_path, seconds, job))
        print({'execute': args.execute, 'confirmed_upload_failures': len(ready), 'repo_files': len(files),
               'flavor': 'cpu-upgrade', 'timeout_hours': 12, 'frozen_source_unchanged': True}, flush=True)
        if not args.execute:
            return
        env = os.environ.copy()
        env['HF_TOKEN'] = get_token() or env.get('HF_TOKEN') or ''
        assert env['HF_TOKEN']
        for shard, previous, log_path, seconds, failed in ready:
            assert api.inspect_job(job_id=failed.id).status.stage == 'ERROR'
            record = {'stage': 'launch_intent', 'previous_guard': previous,
                      'failure': {'job_id': previous['job_id'], 'stage': 'ERROR',
                                  'started_at': str(failed.started_at), 'finished_at': str(failed.finished_at)},
                      'failure_reason': 'artifact_repository_file_limit', 'failure_log_sha256': digest(log_path),
                      'remote_artifact_prefix_absent': True, 'artifact_revision_checked': revision,
                      'repo_files_after_compaction': len(files), 'flavor': 'cpu-upgrade', 'timeout_hours': 12,
                      'profile_sha256': digest(profile_path), 'admission_multiplier': multiplier,
                      'conservative_seconds': seconds, 'created_at': datetime.now(timezone.utc).isoformat(),
                      'bootstrap_sha256': hashlib.sha256(manager.BOOTSTRAP.encode()).hexdigest(),
                      'source_unchanged': True, 'qualification_eligible': False}
            path = FAILURE_RETRIES/(shard+'.json')
            write(path, record)
            command = ['hf', 'jobs', 'run', '--detach', '--flavor', 'cpu-upgrade', '--timeout', '12h',
                       '--secrets', 'HF_TOKEN', '--label', 'project=powergrid-ai',
                       '--label', 'stage=policy-labels-upload-retry-v2', '--label', 'shard='+shard]
            for key, value in {'SOURCE_ARCHIVE': source['archive'], 'SOURCE_REVISION': source['revision'],
                               'SOURCE_SHA256': source['sha256'], 'LABEL_SHARD': shard,
                               'HF_HUB_DISABLE_PROGRESS_BARS': '1'}.items():
                command += ['--env', key+'='+value]
            command += ['--', 'python:3.11-slim-bookworm', 'bash', '-lc', manager.BOOTSTRAP]
            try:
                result = subprocess.run(command, cwd=ROOT, env=env, capture_output=True, text=True, check=True)
                path.with_suffix('.launch.log').write_text(result.stdout+result.stderr)
                ids = set(re.findall(r'\b[a-f0-9]{24}\b', result.stdout))
                assert len(ids) == 1, 'Ambiguous submission; reconcile before another action'
                record.update(stage='launched', job_id=ids.pop())
            except BaseException as error:
                record.update(stage='launch_unknown', error=type(error).__name__+': '+str(error))
                raise
            finally:
                write(path, record)
            print({'shard': shard, 'failed_job_id': previous['job_id'], 'retry_job_id': record['job_id']}, flush=True)


if __name__ == '__main__':
    main()
