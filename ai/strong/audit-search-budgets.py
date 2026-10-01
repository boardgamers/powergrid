"""HF diagnostic shard: repeat searches with shared scenarios across policies."""
import concurrent.futures
import hashlib
import itertools
import json
import os
from pathlib import Path
import subprocess
from huggingface_hub import HfApi

players = int(os.environ['PLAYER_COUNT'])
assert 2 <= players <= 6
fixtures = Path('ai/strong/fixtures/teacher-reliability-v1.jsonl')
rows = [json.loads(line) for line in fixtures.read_text().splitlines()]
indices = [i for i, r in enumerate(rows) if r['cell'][0] == players]
assert len(indices) == 12
tasks = list(itertools.product(indices, ['mixed', 'economic', 'heuristic'], ['a', 'b']))


def audit(task):
    index, policy, batch = task
    process = subprocess.run(['node', 'ai/strong/audit-search-budget.cjs', str(fixtures),
                              str(index), policy, batch], capture_output=True, text=True, check=True)
    row = json.loads(process.stdout)
    assert row['cell'][0] == players and row['continuation'] == policy and row['batch'] == batch
    result = row['result']
    assert len(result['sampleOutcomes']) * 384 == result['evaluations']
    assert sum(v.count(None) for v in result['sampleOutcomes'].values()) == result['truncated']
    for k, v in result['sampleOutcomes'].items():
        assert len(v) == 384 and sum(x for x in v if x is not None) == result['values'][k]
    return row


completed = []
with concurrent.futures.ThreadPoolExecutor(max_workers=24) as pool:
    futures = [pool.submit(audit, task) for task in tasks]
    for f in concurrent.futures.as_completed(futures):
        completed.append(f.result())
        print(json.dumps({'players': players, 'completed_searches': len(completed),
                          'requested_searches': len(tasks)}), flush=True)
completed.sort(key=lambda r: (r['fixtureIndex'], r['continuation'], r['batch']))
output = Path(f'results-{players}p.jsonl')
output.write_text(''.join(json.dumps(r) + '\n' for r in completed))
manifest = {'players': players, 'positions': 12, 'searches': len(completed), 'samples': 384,
            'search_max_steps': 2400, 'fixture_sha256': hashlib.sha256(fixtures.read_bytes()).hexdigest(),
            'output_sha256': hashlib.sha256(output.read_bytes()).hexdigest(),
            'evaluations': sum(r['result']['evaluations'] for r in completed),
            'truncated': sum(r['result']['truncated'] for r in completed),
            'scope': 'Reused development positions; nested budgets and shared public scenarios; no strength claim.'}
api = HfApi()
api.upload_file(repo_id=os.environ['HF_MODEL_REPO'], path_or_fileobj=output,
                path_in_repo=f'runs/teacher-reliability-v2/{output.name}')
api.upload_file(repo_id=os.environ['HF_MODEL_REPO'], path_or_fileobj=json.dumps(manifest, indent=2).encode(),
                path_in_repo=f'runs/teacher-reliability-v2/manifest-{players}p.json')
print(json.dumps(manifest), flush=True)
