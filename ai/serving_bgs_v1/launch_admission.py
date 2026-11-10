"""One new credential-free CPU sandbox-admission job, at most ten requested minutes.

Separate from all frozen study launchers/budgets. An unknown submission consumes
this local intent; this command never retries or deletes a receipt/intent.
"""
import argparse
from dataclasses import asdict
from datetime import datetime
import hashlib
import json
from pathlib import Path
import os

ROOT = Path(__file__).resolve().parents[2]
LEDGER = ROOT / 'ai/runs/bgs-serving-v1/admission'
IMAGE = 'docker.io/library/node:24.22.1-bookworm-slim@sha256:2dd9a4f758e173b65fee15388f7706af6fb01ef50cf7a2c0538711d67a6981ae'


def exclusive(path, value):
    def encode(value):
        if isinstance(value, datetime):
            return value.isoformat()
        raise TypeError('Unsupported receipt value')
    raw = (json.dumps(value, sort_keys=True, indent=2, default=encode) + '\n').encode()
    with path.open('xb') as f:
        f.write(raw)
        f.flush()
        os.fsync(f.fileno())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--submit', action='store_true')
    args = parser.parse_args()
    code = (ROOT / 'ai/serving_bgs_v1/admission.cjs').read_bytes()
    sha = hashlib.sha256(code).hexdigest()
    spec = dict(image=IMAGE, command=['node', '-e', code.decode()], flavor='cpu-basic', timeout=600,
                name='pg-bgs-container-admission-v1', labels={'scope': 'pg-bgs-admission-v1', 'training': 'false'},
                expose=None, ssh=False)
    if not args.submit:
        print(json.dumps(dict(image=IMAGE, flavor='cpu-basic', timeoutSeconds=600, sourceSha256=sha,
                             noModels=True, noSecrets=True, noPorts=True, requestedJobHours=1/6)))
        return
    LEDGER.mkdir(parents=True, exist_ok=True)
    exclusive(LEDGER / 'intent.json', dict(schema='pg-bgs-admission-intent-v1', spec=spec, sourceSha256=sha,
                                         launcherSha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                                         maximumSubmissions=1, maximumRequestedSeconds=600))
    from huggingface_hub import HfApi
    api = HfApi()
    job = api.run_job(**spec)
    # Persist the observed ID before any admission assertions, never submit again on ambiguity.
    exclusive(LEDGER / 'submitted-id.json', dict(jobId=job.id, namespace=job.owner.name))
    data = asdict(job)
    exclusive(LEDGER / 'receipt.json', data)
    print(json.dumps(dict(jobId=job.id, namespace=job.owner.name, receipt=str((LEDGER/'receipt.json').relative_to(ROOT)))))


if __name__ == '__main__':
    main()
