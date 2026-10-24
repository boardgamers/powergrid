"""Submit exactly one four-seed representation job after full source admission."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
import re
import subprocess

from huggingface_hub import get_token
from strategic_collection import ROOT, write, digest
from policy_iteration_job import admission, BOOTSTRAP, DATA_PIN


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--head-type', choices=['frozen', 'public'], required=True)
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    design, data_pin, source = admission()
    record = {'stage': 'launch_intent', 'created_at': datetime.now(timezone.utc).isoformat(),
              'source': source, 'data_pin': data_pin, 'head_type': args.head_type,
              'seeds': design['seeds'], 'flavor': 'l4x1', 'timeout_hours': 3,
              'bootstrap_sha256': hashlib.sha256(BOOTSTRAP.encode()).hexdigest(), 'qualification_eligible': False}
    if not args.execute:
        print({'admitted': True, 'head_type': args.head_type, 'seeds': design['seeds'], 'executed': False})
        return
    env = os.environ.copy()
    env['HF_TOKEN'] = get_token() or env.get('HF_TOKEN') or ''
    assert env['HF_TOKEN']
    directory = ROOT/'ai/runs/policy-iteration-training-launches-v2'
    directory.mkdir(exist_ok=True)
    guard = directory/(args.head_type+'.json')
    with guard.open('x') as stream:
        json.dump(record, stream, indent=2)
    command = ['hf', 'jobs', 'run', '--detach', '--flavor', 'l4x1', '--timeout', '3h', '--secrets', 'HF_TOKEN',
               '--label', 'project=powergrid-ai', '--label', 'stage=policy-iteration-training-v2',
               '--label', 'representation='+args.head_type]
    for key, value in {'SOURCE_ARCHIVE': source['archive'], 'SOURCE_REVISION': source['revision'],
                       'SOURCE_SHA256': source['sha256'], 'DESIGN_SHA256': source['design_sha256'],
                       'DATA_PIN_SHA256': digest(DATA_PIN), 'DATA_CHECK_SHA256': source['data_check_sha256'],
                       'POWERGRID_HF_TRAINING': '1', 'HEAD_TYPE': args.head_type, 'HF_HUB_DISABLE_PROGRESS_BARS': '1'}.items():
        command += ['--env', key+'='+value]
    command += ['--', 'pytorch/pytorch:2.6.0-cuda12.4-cudnn9-runtime', 'bash', '-lc', BOOTSTRAP]
    try:
        result = subprocess.run(command, cwd=ROOT, env=env, capture_output=True, text=True, check=True)
        guard.with_suffix('.log').write_text(result.stdout+result.stderr)
        ids = set(re.findall(r'\b[a-f0-9]{24}\b', result.stdout))
        assert len(ids) == 1, 'Ambiguous launch: inspect HF before any retry'
        record.update(stage='launched', job_id=ids.pop())
    except BaseException as error:
        record.update(stage='launch_unknown', error=type(error).__name__+': '+str(error))
        raise
    finally:
        write(guard, record)
    print({k: record[k] for k in ['stage', 'job_id', 'head_type', 'seeds']}, flush=True)


if __name__ == '__main__':
    main()
