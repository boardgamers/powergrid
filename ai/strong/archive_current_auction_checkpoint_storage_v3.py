"""Archive transport diagnosis/proof and exact original job recovery metadata.

One versioned evidence archive only; no jobs, games, inference or job retries.
Inspect this helper's existing intent and remote path before any retry.
"""
import json
from pathlib import Path
import shutil

from huggingface_hub import HfApi
import manage_current_auction_remaining_v2 as m
import collect_current_auction_retained_after_transport_failure_v2 as collection

OUT = m.ROOT/'ai/runs/current-auction-checkpoint-storage-evidence-v3'
DESCRIPTOR = m.STRONG/'current-auction-checkpoint-storage-evidence-v3.json'
SNAPSHOT = m.STRONG/'current-auction-checkpoint-storage-status-v3.json'


def main():
    m.require(not OUT.exists() and not OUT.with_suffix('.tgz').exists() and not DESCRIPTOR.exists(),
        'Inspect previous archive intent/outcome; do not repeat')
    with m.exclusive(m.OUT, 'cycle'):
        source, rows, records = collection.original_bindings()
        status = m.read(SNAPSHOT)
        state = collection.OUT/'collection-state.json'
        m.require(status['collection_state_sha256'] == m.digest(state)
            and status['stop_sha256'] == m.digest(m.OUT/'STOP.json'), 'Snapshot changed before archive')
        repo = m.worker.base.retention.REPO
        api = HfApi()
        m.require(api.model_info(repo).private is True, 'Evidence repo must stay private')
        m.require(not api.file_exists(repo, 'archives/'+OUT.name+'.tgz'), 'Inspect existing remote archive')
        names = ('checkpoint_bucket_transport_v3.py', 'test_checkpoint_bucket_transport_v3.py',
            'probe_checkpoint_bucket_concurrency_v3.py', 'checkpoint-bucket-concurrency-v3.json',
            'probe_current_auction_bucket_retention_v3.py', 'current-auction-bucket-retention-probe-v3.json',
            'collect_current_auction_retained_after_transport_failure_v2.py')
        paths = {Path(__file__), SNAPSHOT, m.SOURCE,
            m.STRONG/'current-auction-resource-recovery-decision-v2.json', collection.REGISTRY,
            m.OUT/'STOP.json', state, m.first.RESULT,
            m.ROOT/'ai/CURRENT-AUCTION-CHECKPOINT-STORAGE-2026-10-29.md', m.ROOT/'ai/RESUME.md'}
        paths.update(m.STRONG/name for name in names)
        for directory in (collection.OUT, m.ROOT/'ai/runs/current-auction-bucket-retention-probe-v3',
                m.ROOT/'ai/runs/checkpoint-bucket-concurrency-v3'):
            paths.update(directory.rglob('*.json'))
        for pattern in ('checkpoint-bucket-*-v3-*.log', 'current-auction-bucket-retention-probe-v3-*.log',
                'current-auction-retained-post-failure-collection-v2-*.log',
                'current-auction-remaining-failure-inspection-v2-*.log'):
            paths.update(m.ROOT.joinpath('ai/runs').glob(pattern))
        for item in records:
            folder = m.OUT/'jobs'/item['attempt_id']
            for name in ('launch-intent.json', 'launch.json', 'terminal.json', 'review.json', 'original.log'):
                if (folder/name).is_file(): paths.add(folder/name)
            checks = sorted((folder/'checks').glob('*.json'))
            if checks: paths.add(checks[-1])
            for name in ('run-status.json', 'attempt.json', 'checkpoint-transports.json'):
                if (folder/'artifacts'/name).is_file(): paths.add(folder/'artifacts'/name)
            supervisor = folder/'artifacts/supervisor'
            if supervisor.is_dir(): paths.update(supervisor.glob('*.json'))
        OUT.mkdir()
        for path in sorted(paths):
            m.require(path.is_file() and not path.is_symlink(), 'Invalid metadata source')
            target = OUT/path.relative_to(m.ROOT)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, target)
            m.require(m.digest(path) == m.digest(target), 'Metadata changed while copying')
        m.save(OUT/'manifest.json', {str(p.relative_to(OUT)): m.digest(p)
            for p in sorted(OUT.rglob('*')) if p.is_file()})
        m.durable(OUT.with_suffix('.intent.json'), {'created_at': m.now(),
            'manifest_sha256': m.digest(OUT/'manifest.json'), 'automatic_retries': False,
            'references_existing_raw_archives': True, 'new_jobs': 0})
        evidence = m.first.upload_evidence(OUT)
        m.save(DESCRIPTOR, {'archive': evidence, 'snapshot_sha256': m.digest(SNAPSHOT),
            'transport_sha256': m.digest(m.STRONG/'checkpoint_bucket_transport_v3.py'),
            'concurrency_report_sha256': m.digest(m.STRONG/'checkpoint-bucket-concurrency-v3.json'),
            'stop_preserved_sha256': m.digest(m.OUT/'STOP.json'),
            'new_jobs': 0, 'new_games': 0, 'qualified': False, 'reserved_final_seeds_used': False})
        print(json.dumps({'archive': evidence, 'new_jobs': 0}), flush=True)


if __name__ == '__main__': main()
