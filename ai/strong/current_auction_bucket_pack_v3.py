"""Select one explicitly prepared row from a shared immutable worker archive.

The original evaluator and audited bucket worker are unchanged. No HF job API.
"""
import argparse
import json
from pathlib import Path
import shutil

import current_auction_bucket_worker_v3 as worker

read, digest, require = worker.read, worker.digest, worker.require
COMMON = {worker.ENTRY, *worker.CODE, 'original-source.json', 'decision.json'}
ROW_FILES = {'control.json', 'admission.json', 'manifest.json'}


def materialize(pack, pack_sha, name, destination):
    pack, destination = Path(pack).resolve(), Path(destination).resolve()
    pins = worker.base.tree(pack, 'manifest.json', pack_sha)
    index = read(pack/'index.json')
    require(index['version'] == 3 and index['scope'] == 'untouched_fixed_confirmation_rows'
        and index['automatic_job_retries'] is False, 'Wrong pack purpose')
    require(name in index['rows'], 'Row is outside prepared pack')
    entry = index['rows'][name]
    attempt = name.replace('pg-current-confirm-v1-', 'pg-current-bucket-v3-', 1).replace('_','-')
    require(name.startswith('pg-current-confirm-v1-') and entry['attempt_id'] == attempt,
        'Row/attempt mismatch')
    prefix = 'rows/'+attempt+'/'
    require(all(prefix+filename in pins for filename in ROW_FILES), 'Incomplete prepared row')
    require(pins[prefix+'manifest.json'] == entry['bundle_manifest_sha256'], 'Row manifest pin differs')
    require(not destination.exists() and not destination.is_relative_to(pack)
        and not pack.is_relative_to(destination), 'Destination exists or overlaps pack')
    flat = read(pack/prefix/'manifest.json')
    require(set(flat) == COMMON|{'control.json','admission.json'}, 'Unexpected flat worker files')
    require(all(flat[name] == pins[name] for name in COMMON)
        and all(flat[name] == pins[prefix+name] for name in ('control.json','admission.json')),
        'Row and shared files differ')
    control = read(pack/prefix/'control.json')
    require(control['original_name'] == name and control['attempt_id'] == attempt
        and control['reason'] == 'never_submitted' and not control['prior_failed_attempts'],
        'Pack cannot retry failed jobs')
    destination.mkdir(parents=True)
    for filename in COMMON: shutil.copyfile(pack/filename, destination/filename)
    for filename in ROW_FILES: shutil.copyfile(pack/prefix/filename, destination/filename)
    worker.base.tree(destination, 'manifest.json', entry['bundle_manifest_sha256'])
    return entry['bundle_manifest_sha256']


def run(pack, pack_sha, name, destination, source, output, execute=False):
    sha = materialize(pack,pack_sha,name,destination)
    return worker.run(destination,sha,source,output,execute=execute)


if __name__ == '__main__':
    p=argparse.ArgumentParser(__doc__)
    for field in ('pack','destination','source','output'):p.add_argument('--'+field,type=Path,required=True)
    p.add_argument('--pack-manifest-sha256',required=True);p.add_argument('--name',required=True)
    p.add_argument('--execute',action='store_true');a=p.parse_args()
    print(json.dumps(run(a.pack,a.pack_manifest_sha256,a.name,a.destination,a.source,a.output,a.execute)),flush=True)
