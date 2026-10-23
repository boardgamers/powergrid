"""Read authoritative HF state for existing guarded jobs; never launch or retry."""
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from huggingface_hub import HfApi
from strategic_collection import ROOT, read, write


def main():
    api = HfApi()
    jobs = {job.id: job for job in api.list_jobs(labels={'project': 'powergrid-ai'})}
    revision = api.model_info('coyotte508/powergrid-ai-germany-v1').sha
    groups = [
        ('strategic-teacher-training-launches-v1', 'strategic-teacher-training-status-v1.json'),
        ('strategic-correction-screen-launches-v1', 'strategic-correction-screen-status-v1.json'),
        ('strategic-correction-launch-v1', 'strategic-correction-job-status-v1.json'),
    ]
    for directory, destination in groups:
        guards = sorted((ROOT/'ai/runs'/directory).glob('*.json'))
        if not guards:
            continue
        rows = []
        for guard in guards:
            row = read(guard)
            # Preserve ambiguous intents. Never interpret a missing ID as permission to retry.
            if not row.get('job_id'):
                rows.append({**row, 'guard': str(guard.relative_to(ROOT)),
                    'authoritative_status': 'RECONCILIATION_REQUIRED'})
                continue
            job = jobs.get(row['job_id']) or api.inspect_job(job_id=row['job_id'])
            rows.append({**row, 'guard': str(guard.relative_to(ROOT)),
                'authoritative_status': job.status.stage, 'message': job.status.message,
                'started_at': str(job.started_at) if job.started_at else None,
                'finished_at': str(job.finished_at) if job.finished_at else None})
        if directory == 'strategic-teacher-training-launches-v1':
            identity = lambda r: tuple(r.get(k) for k in ['players', 'source_mode', 'mode',
                'deal_start', 'deal_end', 'source_revision', 'source_sha256', 'protocol_sha256'])
            for row in rows:
                if row['authoritative_status'] == 'ERROR':
                    row['completed_replacement_job_ids'] = [r['job_id'] for r in rows
                        if r['authoritative_status'] == 'COMPLETED' and identity(r) == identity(row)]
        report = {'checked_at': datetime.now(timezone.utc).isoformat(),
            'artifact_revision': revision, 'submitted_shards': sum(bool(r.get('job_id')) for r in rows),
            'status_counts': dict(Counter(r['authoritative_status'] for r in rows)),
            'historical_errors_with_completed_replacements': sum(bool(r.get('completed_replacement_job_ids')) for r in rows),
            'jobs': rows, 'qualification_eligible': False}
        write(ROOT/'ai/strong'/destination, report)
        print({'file': destination, 'checked_at': report['checked_at'],
            'status_counts': report['status_counts'],
            'historical_errors_with_completed_replacements': report['historical_errors_with_completed_replacements'],
            'artifact_revision': revision}, flush=True)


if __name__ == '__main__':
    main()
