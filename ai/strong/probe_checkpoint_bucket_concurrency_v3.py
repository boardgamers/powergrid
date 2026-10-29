"""64 concurrent transfers of existing evidence; no games, inference or HF jobs.

Eight clients deliberately lose their acknowledgement after successful upload.
All clients use disjoint content-addressed paths and independently verify bytes.
Do not rerun: inspect the durable intent and individual ledgers after interruption.
"""
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import json
from pathlib import Path
import threading
import time

import httpx2
from huggingface_hub import HfApi

from checkpoint_bucket_transport_v3 import BucketTransport, digest, read, save, require, diagnostic

ROOT = Path(__file__).resolve().parents[2]
STRONG = ROOT/'ai/strong'
OUT = ROOT/'ai/runs/checkpoint-bucket-concurrency-v3'
REPORT = STRONG/'checkpoint-bucket-concurrency-v3.json'
BUCKET = 'coyotte508/powergrid-ai-checkpoints'


def main():
    require(not OUT.exists() and not REPORT.exists(), 'Inspect prior concurrency probe; do not repeat')
    original = read(STRONG/'current-auction-bucket-retention-probe-v3.json')['source_evidence']
    archive = ROOT/'ai/runs/current-auction-bucket-retention-probe-v3/normal.tgz'
    require(digest(archive) == original['archive_sha256'], 'Original downloaded checkpoint changed')
    test_log = ROOT/'ai/runs/checkpoint-bucket-transport-v3-tests-second.log'
    require('Ran 19 tests' in test_log.read_text() and test_log.read_text().rstrip().endswith('OK'), 'Transport tests incomplete')
    require(HfApi().bucket_info(BUCKET).private is True, 'Private bucket required')
    OUT.mkdir()
    started = time.monotonic()
    intent = {'created_at': datetime.now(timezone.utc).isoformat(), 'clients': 64,
        'injected_acknowledgement_losses': 8, 'original_evidence': original, 'bucket': BUCKET,
        'transport_sha256': digest(STRONG/'checkpoint_bucket_transport_v3.py'),
        'probe_sha256': digest(__file__), 'tests_sha256': digest(test_log),
        'planned_remote_prefix': 'probes/checkpoint-bucket-concurrency-v3',
        'new_jobs': 0, 'new_games': 0, 'new_inference': 0, 'worker_admitted': False}
    save(OUT/'intent.json', intent)
    barrier = threading.Barrier(64)
    lock = threading.Lock()
    counters = {'active_upload_calls': 0, 'peak_upload_calls': 0, 'application_upload_calls': 0,
        'injected_acknowledgement_losses': 0, 'actual_upload_exceptions': []}

    class Client:
        def __init__(self, number):
            self.api, self.number, self.calls = HfApi(), number, 0

        def __getattr__(self, name): return getattr(self.api, name)

        def batch_bucket_files(self, *args, **kwargs):
            self.calls += 1
            if self.calls == 1: barrier.wait(timeout=120)
            with lock:
                counters['active_upload_calls'] += 1
                counters['application_upload_calls'] += 1
                counters['peak_upload_calls'] = max(counters['peak_upload_calls'], counters['active_upload_calls'])
            try:
                try: self.api.batch_bucket_files(*args, **kwargs)
                except Exception as error:
                    with lock: counters['actual_upload_exceptions'].append({'client': self.number, **diagnostic(error)})
                    raise
                if self.number % 8 == 0 and self.calls == 1:
                    with lock: counters['injected_acknowledgement_losses'] += 1
                    raise httpx2.ReadTimeout('Deliberate local acknowledgement-loss injection after successful upload')
            finally:
                with lock: counters['active_upload_calls'] -= 1

    def one(number):
        client = Client(number)
        try:
            receipt = BucketTransport(client).retain(archive, bucket=BUCKET,
                prefix=f'probes/checkpoint-bucket-concurrency-v3/client-{number:02d}',
                manifest_sha256=original['manifest_sha256'], ledger=OUT/f'client-{number:02d}')
            return {'client': number, 'passed': True, 'receipt': receipt,
                'receipt_sha256': digest(OUT/f'client-{number:02d}/receipt.json')}
        except Exception as error:
            return {'client': number, 'passed': False, 'error': diagnostic(error)}

    records = []
    with ThreadPoolExecutor(max_workers=64) as pool:
        futures = [pool.submit(one, i) for i in range(64)]
        for future in as_completed(futures):
            result = future.result()
            save(OUT/f'client-{result["client"]:02d}-result.json', result)
            records.append(result)
            if len(records) % 8 == 0:
                print(json.dumps({'finished': len(records), 'passed': sum(r['passed'] for r in records)}), flush=True)
    report = {**intent, 'finished_at': datetime.now(timezone.utc).isoformat(),
        'seconds': time.monotonic()-started, **counters,
        'passed': len(records) == 64 and all(r['passed'] for r in records)
            and counters['peak_upload_calls'] == 64 and counters['injected_acknowledgement_losses'] == 8,
        'verified_objects': sum(r['passed'] for r in records), 'records': sorted(records, key=lambda r:r['client']),
        'distinct_source_archives': 1, 'source_archive_bytes': archive.stat().st_size,
        'simulated_faults_only': not counters['actual_upload_exceptions'],
        'production_worker_integrated': False, 'qualified': False, 'reserved_final_seeds_used': False,
        'limitations': 'One client host and one repeated existing 1.7 MB archive; not distributed workers, diverse large archives, or sustained job traffic. Bucket storage is mutable, not versioned.'}
    save(REPORT, report)
    print(json.dumps({k: report[k] for k in ('passed', 'verified_objects', 'peak_upload_calls',
        'application_upload_calls', 'injected_acknowledgement_losses', 'actual_upload_exceptions', 'seconds')}), flush=True)
    require(report['passed'], 'Concurrent storage probe failed; inspect individual original intents')


if __name__ == '__main__': main()
