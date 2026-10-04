"""HF-only diagnostic collection of independent teacher-search repetitions."""
import concurrent.futures
import hashlib
import json
import os
from pathlib import Path
import subprocess
from huggingface_hub import HfApi

fixtures = Path('ai/strong/fixtures/teacher-reliability-v1.jsonl')
rows = fixtures.read_text().splitlines()
assert len(rows) == 60


def audit(index):
    result = subprocess.run(['node', 'ai/strong/audit-search-target.cjs', str(fixtures), str(index)],
                            text=True, capture_output=True, check=True)
    row = json.loads(result.stdout)
    for batch in row['batches']:
        samples = batch['sampleOutcomes']
        assert all(len(v) == 48 for v in samples.values())
        assert sum(len(v) for v in samples.values()) == batch['evaluations']
        assert sum(v.count(None) for v in samples.values()) == batch['truncated']
        assert all(sum(x for x in v if x is not None) == batch['values'][k]
                   for k, v in samples.items())
    return row


output = Path('teacher-reliability-v1.jsonl')
completed = []
with concurrent.futures.ThreadPoolExecutor(max_workers=24) as pool:
    futures = [pool.submit(audit, i) for i in range(len(rows))]
    for f in concurrent.futures.as_completed(futures):
        completed.append(f.result())
        print(json.dumps({'completed_positions': len(completed), 'requested_positions': len(rows)}), flush=True)
completed.sort(key=lambda r: r['fixtureIndex'])
output.write_text(''.join(json.dumps(r) + '\n' for r in completed))
manifest = {'positions': len(completed), 'samples_per_batch': 48, 'batches_per_position': 2,
            'search_max_steps': 2400, 'fixture_sha256': hashlib.sha256(fixtures.read_bytes()).hexdigest(),
            'output_sha256': hashlib.sha256(output.read_bytes()).hexdigest(),
            'truncated': sum(b['truncated'] for r in completed for b in r['batches']),
            'evaluations': sum(b['evaluations'] for r in completed for b in r['batches']),
            'scope': 'Reused development fixtures; diagnostic only, no strength or calibration claim.'}
api = HfApi()
api.upload_file(repo_id=os.environ['HF_MODEL_REPO'], path_or_fileobj=output,
                path_in_repo='runs/teacher-reliability-v1/results.jsonl')
api.upload_file(repo_id=os.environ['HF_MODEL_REPO'], path_or_fileobj=json.dumps(manifest, indent=2).encode(),
                path_in_repo='runs/teacher-reliability-v1/manifest.json')
print(json.dumps(manifest), flush=True)
