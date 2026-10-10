"""Submit the frozen coordinator once and reserve its four future screen keys."""
import json
import os
from pathlib import Path
import re
import subprocess
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[2]
source = json.loads((ROOT / 'ai/strong/five-plant-coordinator-source-v1.json').read_text())
config = json.loads((ROOT / 'ai/strong/five-plant-coordinator-config-v1.json').read_text())
record_file = ROOT / 'ai/runs/five-plant-coordinator-launch-v1.json'
record = {'stage': 'launch_intent', 'created_at': datetime.now(timezone.utc).isoformat(),
          'source_revision': source['revision'], 'source_sha256': source['sha256'],
          'training_jobs': config['training_jobs'], 'parent_job': config['parent_job']}
guards = ROOT / 'ai/runs/five-plant-screen-launches-v1'
guards.mkdir(exist_ok=True)
assert all(not (guards / (k + '.json')).exists() for k in config['training_jobs']), 'An existing screen intent needs reconciliation'
with record_file.open('x') as file:
    json.dump(record, file, indent=2)
for key in config['training_jobs']:
    with (guards / (key + '.json')).open('x') as file:
        json.dump({'key': key, 'stage': 'coordinator_owned', 'coordinator_intent': str(record_file)}, file, indent=2)
env = {**os.environ, 'SOURCE_ARCHIVE': source['archive'], 'SOURCE_REVISION': source['revision'],
       'SOURCE_SHA256': source['sha256']}
try:
    result = subprocess.run(['bash', 'ai/strong/launch-five-plant-coordinator-v1.sh'],
                            cwd=ROOT, env=env, capture_output=True, text=True, check=True)
    (ROOT / 'ai/runs/five-plant-coordinator-launch-v1.log').write_text(result.stdout + result.stderr)
    ids = set(re.findall(r'\b[0-9a-f]{24}\b', result.stdout))
    if len(ids) != 1:
        raise ValueError('Ambiguous coordinator launch response; reconcile intent before retry')
    record.update(stage='launched', job_id=ids.pop())
except BaseException as error:
    record.update(stage='launch_unknown', error=type(error).__name__ + ': ' + str(error))
    raise
finally:
    record_file.write_text(json.dumps(record, indent=2) + '\n')
    (ROOT / 'ai/strong/five-plant-coordinator-status-v1.json').write_text(json.dumps(record, indent=2) + '\n')
if 'job_id' in record:
    for key in config['training_jobs']:
        path = guards / (key + '.json')
        value = json.loads(path.read_text())
        value['coordinator_job_id'] = record['job_id']
        path.write_text(json.dumps(value, indent=2) + '\n')
print(json.dumps(record))
