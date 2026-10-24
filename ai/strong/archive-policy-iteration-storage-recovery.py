"""Save repository compaction proofs, exact failed-job retries and collector state."""
import os
from pathlib import Path
import shutil

from huggingface_hub import HfApi
from strategic_collection import ROOT, read, write, digest
from policy_iteration_label_attempts import FAILURE_RETRIES, effective_guard
from policy_iteration_evidence_archive import upload_evidence


def main():
    strong = ROOT/'ai/strong'
    records = sorted((ROOT/'ai/runs/policy-iteration-storage-compaction-v2').glob('*.json'))
    compacted = [read(p) for p in records]
    assert len(compacted) == 13 and all(r['stage'] == 'verified' for r in compacted)
    assert all(r['remote_archive_verified'] and r['historical_revision_read_verified'] for r in compacted)
    assert all(r['original_revisions_preserved'] and not r['raw_job_outputs_removed'] for r in compacted)
    retries = sorted(FAILURE_RETRIES.glob('*.json'))
    assert len(retries) == 2 and all(read(p)['stage'] == 'launched' for p in retries)
    api = HfApi()
    jobs = []
    for path in retries:
        guard = effective_guard(ROOT/'ai/runs/policy-iteration-labels-launches-v2'/path.name)
        job = api.inspect_job(job_id=guard['job_id'])
        assert job.status.stage in ['SCHEDULING', 'RUNNING', 'COMPLETED']
        jobs.append({'shard': guard['shard']['id'], 'job_id': guard['job_id'],
                     'failed_job_id': guard['failed_job_id'], 'status': job.status.stage})
    run = ROOT/'ai/runs/policy-iteration-harvest-recovered-v2'
    collector = read(run/'state.json')
    assert collector['stage'] in ['running', 'waiting']
    os.kill(collector['pid'], 0)
    command = (Path('/proc')/str(collector['pid'])/'cmdline').read_bytes()
    assert b'harvest-policy-iteration-jobs.py' in command and b'policy-iteration-harvest-recovered-v2' in command
    out = ROOT/'ai/runs/policy-iteration-storage-recovery-evidence-v2'
    out.mkdir(exist_ok=False)
    names = ['compact-policy-iteration-evidence.py', 'harvest-policy-iteration-jobs.py',
             'policy_iteration_evidence_archive.py', 'retry-policy-iteration-upload-errors.py',
             'policy_iteration_label_attempts.py', 'policy-iteration-upload-retry-controls-v2.json',
             'policy-iteration-harvest-controls-v2.json', 'archive-policy-iteration-storage-recovery.py',
             'archive-policy-iteration-labels-progress.py', 'archive-policy-iteration-parent-grid.py',
             'policy-iteration-parent-reference-progress-92-v2.json',
             'policy-iteration-parent-reference-92-evidence-v2.json',
             'policy-iteration-labels-333-progress-evidence-v2.json',
             'policy-iteration-labels-source-v2.json', 'policy-iteration-cpu-upgrade-profile-results-v2.json']
    for name in names:
        shutil.copy2(strong/name, out/name)
    for path in records:
        target = out/'compactions'/path.name
        target.parent.mkdir(exist_ok=True)
        shutil.copy2(path, target)
    shutil.copytree(FAILURE_RETRIES, out/'failure-retries', ignore=shutil.ignore_patterns('.*'))
    write(out/'collector-state.json', collector)
    shutil.copy2(ROOT/'ai/runs/policy-iteration-harvest-v2/state.json', out/'previous-collector-error.json')
    write(out/'label-status.json', read(strong/'policy-iteration-labels-status-v2.json'))
    write(out/'manifest.json', {str(p.relative_to(out)): digest(p) for p in out.rglob('*') if p.is_file()})
    result = {**upload_evidence(out), 'head_compactions': len(compacted),
              'net_head_files_freed': sum(r['net_head_file_reduction'] for r in compacted),
              'files_at_retry_admission': read(retries[0])['repo_files_after_compaction'],
              'compacted_revisions': {r['name']: r['revision'] for r in compacted},
              'original_pins_preserved': True, 'raw_job_outputs_removed': False,
              'failure_retries': jobs, 'collector_pid': collector['pid'],
              'collector_process_checked_alive': True, 'collector_directory': str(run.relative_to(ROOT)),
              'collector_started_at': collector['started_at'], 'collector_session_id': 82318,
              'gradients': False, 'qualification_eligible': False, 'reserved_final_seeds_used': False}
    write(strong/'policy-iteration-storage-recovery-evidence-v2.json', result)
    print(result, flush=True)


if __name__ == '__main__':
    main()
