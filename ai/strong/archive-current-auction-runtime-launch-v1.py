"""Archive four original runtime handles and recovery code; never submit a job."""
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path

from huggingface_hub import HfApi
from public_policy_development_job_v1 import digest, read
from policy_iteration_evidence_archive import upload_evidence

ROOT = Path(__file__).resolve().parents[2]
NAME = 'current-auction-runtime-launch-evidence-v1'
OUT = ROOT / 'ai/runs' / NAME
RESULT = ROOT / 'ai/strong' / (NAME + '.json')


def save(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2, allow_nan=False); stream.write('\n')


def main():
    for path in (OUT, OUT.with_suffix('.tgz'), OUT.with_suffix('.intent.json'), RESULT):
        assert not path.exists(), 'Inspect existing archive/upload outcome before retry'
    module_path = Path(__file__).with_name('manage-current-auction-runtime-v1.py')
    spec = importlib.util.spec_from_file_location('manager', module_path)
    manager = importlib.util.module_from_spec(spec); spec.loader.exec_module(manager)
    source = manager.source_checked(); api = HfApi(); statuses = []
    sources = {Path(__file__), module_path, manager.SOURCE, manager.PROTOCOL,
        manager.LOCAL / 'prepared.json', manager.LOCAL / 'validated.json', manager.OUT / 'prepared.json',
        manager.OUT / 'upload-intent.json', manager.OUT / 'upload-receipt.json'}
    for row in source['rows']:
        path = manager.OUT / row['name'] / 'launch.json'; guard = read(path)
        assert guard['stage'] == 'launched' and guard['source'] == source and guard['row'] == row
        job = api.inspect_job(job_id=guard['job_id'])
        assert job.command == ['bash', '-lc', manager.BOOTSTRAP] and job.flavor == row['flavor']
        assert job.docker_image == 'python:3.11-slim-bookworm'
        assert job.environment['SOURCE_SHA256'] == source['sha256'] and job.environment['PILOT_JOB'] == row['job']
        assert job.environment['SOURCE_REVISION'] == source['revision']
        statuses.append({'name': row['name'], 'job_id': job.id, 'stage': job.status.stage,
            'created_at': str(job.created_at), 'started_at': str(job.started_at), 'finished_at': str(job.finished_at),
            'guard_sha256': digest(path), 'games': row['shard']['games'], 'timeout': row['timeout'], 'flavor': row['flavor']})
        sources.add(path)
        sources.add(manager.LOCAL / (row['name'] + '.validation.log'))
    assert len(statuses) == 4 and sum(r['games'] for r in statuses) == 64
    sources.update(ROOT / name for name in source['code_hashes'])
    sources.update(ROOT / p for p in (
        'ai/CURRENT-ENGINE-AUCTION-2026-10-28.md', 'ai/RESUME.md',
        'ai/strong/prepare-current-auction-confirmation-v1.py',
        'ai/strong/current-engine-auction-evidence-v2.json',
        'ai/strong/public_policy_development_job_v1.py', 'ai/strong/public_policy_measured_job_v1.py',
        'ai/strong/policy_iteration_evidence_archive.py', 'ai/strong/strategic_collection.py',
        'ai/runs/current-auction-runtime-tests-v1.log', 'ai/runs/current-auction-runtime-preparation-v1-first.log',
        'ai/runs/current-auction-runtime-hf-preparation-v1-first.log', 'ai/runs/current-auction-runtime-launch-v1-first.log'))
    repo = 'coyotte508/powergrid-ai-germany-v1'
    assert api.model_info(repo).private and not api.file_exists(repo, 'archives/' + NAME + '.tgz')
    OUT.mkdir(); hashes = {}
    for path in sorted(sources):
        assert path.is_file() and not path.is_symlink()
        name = str(path.relative_to(ROOT)); target = OUT / name; target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(path.read_bytes()); hashes[name] = digest(target)
    snapshot = {'checked_at': datetime.now(timezone.utc).isoformat(), 'jobs': statuses,
        'runtime_games': 64, 'source_sha256': digest(manager.SOURCE), 'protocol_sha256': digest(manager.PROTOCOL),
        'confirmation_games': 26880, 'confirmation_grid_admitted': False,
        'recovery': 'Use only manage-current-auction-runtime-v1.py collect on the four original handles. Preserve failures/partial evidence; no automatic retry. Complete all pilots and cost review before preparing the larger grid.',
        'goal_status': 'active', 'candidate_qualified': False, 'reserved_final_seeds_used': False}
    save(OUT / 'launch-snapshot.json', snapshot); hashes['launch-snapshot.json'] = digest(OUT / 'launch-snapshot.json')
    save(OUT / 'manifest.json', hashes)
    intent = {'created_at': snapshot['checked_at'], 'stage': 'prepared_for_upload', 'manifest_sha256': digest(OUT / 'manifest.json')}
    save(OUT.with_suffix('.intent.json'), intent)
    archive = upload_evidence(OUT)
    save(RESULT, {**snapshot, 'archive': archive})
    OUT.with_suffix('.intent.json').write_text(json.dumps({**intent, 'stage': 'uploaded_download_verified',
        'archive': archive, 'descriptor_sha256': digest(RESULT)}, indent=2) + '\n')
    print(json.dumps({'jobs': statuses, 'archive': archive}), flush=True)


if __name__ == '__main__': main()
