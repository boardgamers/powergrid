"""One guarded HF CPU measurement; no gradients or training-data mutation."""
import argparse
import importlib.util
import json
import os
import re
import subprocess
from datetime import datetime, timezone

from huggingface_hub import get_token
from strategic_collection import ROOT, read, write, digest


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    s = read(ROOT/'ai/strong/policy-iteration-inference-profile-source-v2.json')
    check = read(ROOT/'ai/strong/policy-iteration-inference-profile-preflight-v2.json')
    assert check['passed'] and check['source'] == s and check['control']['rollouts'] == 64
    for file, sha in s['overlays'].items():
        assert digest(ROOT/file) == sha
    guard = ROOT/'ai/runs/policy-iteration-inference-profile-launch-v2.json'
    if guard.exists():
        record = read(guard)
        assert record['stage'] == 'launched' and record['source'] == s
        print({'already_launched': record['job_id']})
        return
    print({'execute': args.execute, 'jobs': 1, 'flavor': 'cpu-performance', 'timeout_hours': 2}, flush=True)
    if not args.execute:
        return
    spec = importlib.util.spec_from_file_location('label_manager', ROOT/'ai/strong/manage-policy-iteration-labels.py')
    manager = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(manager)
    bootstrap = manager.BOOTSTRAP.replace(
        'python -u ai/strong/policy_iteration_labels.py "$LABEL_SHARD" ai/runs/full-labels --upload',
        '''python -u ai/strong/profile-policy-iteration-continuations.py ai/runs/inference-profile
python -u ai/strong/profile-policy-iteration-inference.py ai/runs/inference-profile/microbenchmark.json
python - <<'UPLOAD'
from huggingface_hub import HfApi
HfApi().upload_folder(repo_id='coyotte508/powergrid-ai-germany-v1',folder_path='ai/runs/inference-profile',path_in_repo='runs/policy-iteration-inference-hf-profile-v2')
UPLOAD''')
    assert 'LABEL_SHARD' not in bootstrap
    command = ['hf', 'jobs', 'run', '--detach', '--flavor', 'cpu-performance', '--timeout', '2h',
               '--secrets', 'HF_TOKEN', '--label', 'project=powergrid-ai', '--label', 'stage=policy-inference-profile-v2']
    for key, value in {'SOURCE_ARCHIVE': s['archive'], 'SOURCE_REVISION': s['revision'], 'SOURCE_SHA256': s['sha256'],
                       'HF_HUB_DISABLE_PROGRESS_BARS': '1'}.items():
        command += ['--env', key + '=' + value]
    command += ['--', 'python:3.11-slim-bookworm', 'bash', '-lc', bootstrap]
    env = os.environ.copy()
    env['HF_TOKEN'] = get_token() or env.get('HF_TOKEN') or ''
    assert env['HF_TOKEN']
    record = {'stage': 'launch_intent', 'source': s, 'created_at': datetime.now(timezone.utc).isoformat(),
              'flavor': 'cpu-performance', 'timeout_hours': 2, 'gradients': False, 'qualification_eligible': False}
    with guard.open('x') as f:
        json.dump(record, f, indent=2)
    try:
        result = subprocess.run(command, cwd=ROOT, env=env, text=True, capture_output=True, check=True)
        guard.with_suffix('.log').write_text(result.stdout + result.stderr)
        ids = set(re.findall(r'\b[a-f0-9]{24}\b', result.stdout))
        assert len(ids) == 1
        record.update(stage='launched', job_id=ids.pop())
    except BaseException as error:
        record.update(stage='launch_unknown', error=type(error).__name__ + ': ' + str(error))
        raise
    finally:
        write(guard, record)
    print({'job_id': record['job_id']}, flush=True)


if __name__ == '__main__':
    main()
