"""Measure the same frozen workload on CPU Upgrade; do not replace queued labels."""
from datetime import datetime, timezone
import hashlib
import json
import os
import re
import subprocess
from huggingface_hub import get_token
from strategic_collection import ROOT, read, write, digest

BOOTSTRAP = '''
set -euo pipefail
apt-get update -qq
apt-get install -y --no-install-recommends libstdc++6 libgomp1 ca-certificates >/dev/null
python -m pip install --quiet --timeout 120 --retries 5 huggingface_hub==2.0.0 onnxruntime==1.30.0 numpy==2.4.6
mkdir -p /workspace
python - <<'INNER'
import urllib.request,tarfile,os,hashlib
from pathlib import Path
from huggingface_hub import hf_hub_download
urllib.request.urlretrieve('https://nodejs.org/dist/v24.14.0/node-v24.14.0-linux-x64.tar.xz','/tmp/node.tar.xz')
with tarfile.open('/tmp/node.tar.xz') as bundle: bundle.extractall('/opt')
file=hf_hub_download('coyotte508/powergrid-ai-training-v1',os.environ['SOURCE_ARCHIVE'],repo_type='dataset',revision=os.environ['SOURCE_REVISION'])
assert hashlib.sha256(Path(file).read_bytes()).hexdigest()==os.environ['SOURCE_SHA256']
with tarfile.open(file) as bundle: bundle.extractall('/workspace',filter='data')
INNER
export PATH=/opt/node-v24.14.0-linux-x64/bin:$PATH
cd /workspace
mkdir -p ai/runs
python -u ai/strong/profile-policy-iteration-inference.py ai/runs/cpu-upgrade-micro-v2.json
python -u ai/strong/profile-policy-iteration-continuations.py ai/runs/cpu-upgrade-profile-v2
python - <<'INNER'
import json,os,platform,shutil
from pathlib import Path
from huggingface_hub import HfApi
out=Path('ai/runs/cpu-upgrade-profile-v2')
shutil.copy2('ai/runs/cpu-upgrade-micro-v2.json',out/'micro.json')
environment={'requested_flavor':'cpu-upgrade','cpu_count':os.cpu_count(),'affinity_count':len(os.sched_getaffinity(0)),'platform':platform.platform()}
for file in ['/sys/fs/cgroup/cpu.max','/sys/fs/cgroup/memory.max']:
 p=Path(file)
 environment[file]=p.read_text().strip() if p.exists() else None
(out/'environment.json').write_text(json.dumps(environment,indent=2)+'\\n')
HfApi().upload_folder(repo_id='coyotte508/powergrid-ai-germany-v1',folder_path=out,path_in_repo='runs/policy-iteration-cpu-upgrade-profile-v2')
INNER
'''


def main():
    source = read(ROOT/'ai/strong/policy-iteration-inference-profile-source-v2.json')
    for file, sha in source['overlays'].items():
        assert digest(ROOT/file) == sha
    reference = read(ROOT/'ai/strong/policy-iteration-inference-hf-profile-v2.json')
    assert reference['verified'] and reference['source'] == source and reference['rollouts'] == 3072
    guard = ROOT/'ai/runs/policy-iteration-cpu-upgrade-profile-launch-v2.json'
    record = {'stage': 'launch_intent', 'created_at': datetime.now(timezone.utc).isoformat(),
              'source': source, 'flavor': 'cpu-upgrade', 'timeout_hours': 2,
              'reference_file': 'ai/strong/policy-iteration-inference-hf-profile-v2.json',
              'reference_sha256': digest(ROOT/'ai/strong/policy-iteration-inference-hf-profile-v2.json'),
              'bootstrap_sha256': hashlib.sha256(BOOTSTRAP.encode()).hexdigest(),
              'artifact_prefix': 'runs/policy-iteration-cpu-upgrade-profile-v2',
              'full_label_jobs_changed': False, 'gradients': False, 'qualification_eligible': False}
    with guard.open('x') as f:
        json.dump(record, f, indent=2)
    env = os.environ.copy()
    env['HF_TOKEN'] = get_token() or env.get('HF_TOKEN') or ''
    assert env['HF_TOKEN']
    command = ['hf', 'jobs', 'run', '--detach', '--flavor', 'cpu-upgrade', '--timeout', '2h',
               '--secrets', 'HF_TOKEN', '--label', 'project=powergrid-ai', '--label', 'stage=policy-cpu-upgrade-profile-v2']
    for key, value in {'SOURCE_ARCHIVE': source['archive'], 'SOURCE_REVISION': source['revision'],
                       'SOURCE_SHA256': source['sha256'], 'HF_HUB_DISABLE_PROGRESS_BARS': '1'}.items():
        command += ['--env', key+'='+value]
    command += ['--', 'python:3.11-slim-bookworm', 'bash', '-lc', BOOTSTRAP]
    try:
        result = subprocess.run(command, cwd=ROOT, env=env, capture_output=True, text=True, check=True)
        guard.with_suffix('.log').write_text(result.stdout + result.stderr)
        ids = set(re.findall(r'\b[a-f0-9]{24}\b', result.stdout))
        assert len(ids) == 1
        record.update(stage='launched', job_id=ids.pop())
    except BaseException as error:
        record.update(stage='launch_unknown', error=type(error).__name__ + ': ' + str(error))
        raise
    finally:
        write(guard, record)
    print({k: record[k] for k in ['stage', 'job_id', 'flavor', 'artifact_prefix']}, flush=True)


if __name__ == '__main__':
    main()
