"""Execute one pinned development shard on HF and retain its original raw output."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time


def digest(path):
    with Path(path).open('rb') as f: return hashlib.file_digest(f, 'sha256').hexdigest()
def read(path): return json.loads(Path(path).read_text())
def save(path, data):
    with Path(path).open('x') as f: json.dump(data, f, indent=2, allow_nan=False); f.write('\n')


def main():
    p = argparse.ArgumentParser(__doc__)
    for name in ('bundle', 'artifact', 'output'): p.add_argument('--'+name, type=Path, required=True)
    p.add_argument('--name', required=True); p.add_argument('--execute', action='store_true'); p.add_argument('--upload', action='store_true')
    a = p.parse_args(); bundle = a.bundle.resolve(); artifact = a.artifact.resolve(); out = a.output.resolve()
    assert not out.exists() and (not a.upload or a.execute)
    protocol = read(bundle/'protocol.json'); row = next(r for r in protocol['rows'] if r['name'] == a.name)
    assert digest(artifact/'manifest.json') == protocol['runtime_manifest_sha256']
    assert digest(bundle/row['candidate']) == read(bundle/row['contract'])['candidate_sha256']
    assert row['shard']['seed'] == f"nomination-discount-development-v1-{row['shard']['players']}p"
    command = [sys.executable, '-u', '-B', str(artifact/'ai/strong/public_policy_final_runner_v1.py'),
        '--artifact', str(artifact), '--descriptor', row['descriptor'], '--candidate', str(bundle/row['candidate']),
        '--contract', str(bundle/row['contract']), '--workers', str(protocol['workers']), '--output', str(out/'evaluation')]
    if row['opponent_model']: command += ['--opponent-model', str(artifact/row['opponent_model'])]
    subprocess.run(command, check=True, stdout=subprocess.DEVNULL)
    if not a.execute: print({'validated': a.name, 'executed': False}); return
    assert os.environ.get('POWERGRID_HF_DEVELOPMENT') == '1', 'Full games run on HF Jobs'
    out.mkdir(); save(out/'origin.json', {'name': a.name, 'protocol_sha256': digest(bundle/'protocol.json'), 'row': row,
                                       'qualified': False, 'reserved_final_seeds_used': False})
    started = time.monotonic(); code = None
    try:
        with (out/'runner.log').open('x') as log:
            code = subprocess.run([*command, '--execute'], stdout=log, stderr=subprocess.STDOUT).returncode
    finally:
        save(out/'status.json', {'returncode': code, 'seconds': time.monotonic()-started, 'complete': code == 0,
                                'qualified': False, 'raw_independently_audited': False})
        save(out/'manifest.json', {str(p.relative_to(out)): digest(p) for p in sorted(out.rglob('*')) if p.is_file()})
        if a.upload:
            sys.path.insert(0, str(bundle/'transport'))
            from checkpoint_bucket_archives_v3 import upload_directory
            from huggingface_hub import HfApi
            receipt = upload_directory(out, out.parent/'transport-ledgers', HfApi())
            print(json.dumps({'development_evidence': receipt, 'name': a.name, 'returncode': code}), flush=True)
    assert code == 0, 'Preserved failed original; inspect raw logs, no automatic retry'


if __name__ == '__main__': main()
