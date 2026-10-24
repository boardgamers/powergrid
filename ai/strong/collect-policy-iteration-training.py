"""Recover completed HF jobs, verify their exact exports, and pin all ensembles."""
import argparse
from datetime import datetime, timezone
import fcntl
import json
from pathlib import Path
import subprocess
import sys
import tarfile

from huggingface_hub import HfApi, hf_hub_download
from strategic_collection import ROOT, read, write, digest
from policy_iteration_job import admission
from policy_iteration_development import validate_pin, PROTOCOL

VERIFIER = ROOT/'ai/strong/policy_iteration_training_verification.py'


def immutable_write(path, value):
    if path.exists():
        assert read(path) == value, f'Existing verified artifact differs: {path}'
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('x') as stream:
            json.dump(value, stream, indent=2)
            stream.write('\n')


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--head-type', choices=['frozen', 'public'], required=True)
    args = parser.parse_args()
    design, data_pin, source = admission()
    guard_path = ROOT/'ai/runs/policy-iteration-training-launches-v2'/(args.head_type+'.json')
    guard = read(guard_path)
    assert guard['stage'] == 'launched' and guard['source'] == source and guard['data_pin'] == data_pin
    assert guard['head_type'] == args.head_type and guard['seeds'] == design['seeds']
    assert guard['flavor'] == 'l4x1'
    api = HfApi()
    job = api.inspect_job(job_id=guard['job_id'])
    print({'job_id': guard['job_id'], 'head_type': args.head_type, 'stage': job.status.stage}, flush=True)
    if job.status.stage != 'COMPLETED':
        return
    base = ROOT/'ai/runs/policy-iteration-training-verified-v2'
    base.mkdir(exist_ok=True)
    with (base/'.collection.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        out = base/args.head_type
        prefix = 'runs/policy-iteration-training-v2-'+args.head_type
        intent_path = out/'collection-intent.json'
        if intent_path.exists():
            intent = read(intent_path)
            assert intent['job_id'] == guard['job_id'] and intent['source'] == source and intent['data_pin'] == data_pin
            assert intent['prefix'] == prefix and intent['guard_sha256'] == digest(guard_path)
            assert intent['verifier_sha256'] == digest(VERIFIER)
        else:
            intent = {'job_id': guard['job_id'], 'source': source, 'data_pin': data_pin,
                      'repo': design['parent']['repo'], 'revision': api.model_info(design['parent']['repo']).sha,
                      'prefix': prefix, 'guard_sha256': digest(guard_path), 'verifier_sha256': digest(VERIFIER)}
            immutable_write(intent_path, intent)
        def fetch(file):
            assert not Path(file).is_absolute() and '..' not in Path(file).parts
            data = Path(hf_hub_download(intent['repo'], prefix+'/'+file, revision=intent['revision'])).read_bytes()
            target = out/file
            if target.exists():
                assert target.read_bytes() == data
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
        fetch('training-check.json')
        status = read(out/'training-check.json')
        assert status['status'] == 'complete'
        for file, sha in status['artifacts'].items():
            fetch(file)
            assert digest(out/file) == sha
        runtime = base/'frozen-source'
        archive = Path(hf_hub_download('coyotte508/powergrid-ai-training-v1', source['archive'],
                                      repo_type='dataset', revision=source['revision']))
        assert digest(archive) == source['sha256']
        with tarfile.open(archive) as bundle:
            if not runtime.exists():
                runtime.mkdir()
                bundle.extractall(runtime, filter='data')
            import hashlib
            for member in bundle.getmembers():
                if member.isfile():
                    assert digest(runtime/member.name) == hashlib.sha256(bundle.extractfile(member).read()).hexdigest()
        script = '''
import json,sys
from pathlib import Path
sys.path.insert(0,sys.argv[1])
sys.path.insert(1,sys.argv[2])
from policy_iteration_job import recover_data
from policy_iteration_training_verification import verify
from strategic_collection import ROOT,write
a=json.loads(sys.argv[3]); data_dir=ROOT/'ai/runs/policy-iteration-training-data-v2'
recover_data(data_dir)
result=verify(Path(a['out']),a['head_type'],a['source'],a['data_pin'],data_dir)
write(Path(a['result']),result)
'''
        result_path = base/(args.head_type+'-verification-result.json')
        parameters = {'out': str(out), 'head_type': args.head_type, 'source': source,
                      'data_pin': data_pin, 'result': str(result_path)}
        with (base/(args.head_type+'-verification.log')).open('w') as log:
            subprocess.run([sys.executable, '-c', script, str(runtime/'ai/strong'), str(VERIFIER.parent),
                            json.dumps(parameters)], cwd=runtime, stdout=log, stderr=subprocess.STDOUT, check=True)
        verified = {**read(result_path), **intent,
                    'artifacts': {file: digest(out/file) for file in ['training-check.json', 'collection-intent.json', *status['artifacts']]}}
        immutable_write(out/'verified.json', verified)
        protocol = read(PROTOCOL)
        for key, spec in protocol['candidate_heads'].items():
            if spec['head_type'] != args.head_type:
                continue
            ensemble = 'ensemble-'+str(int(spec['penalty']))
            info = verified['ensembles'][ensemble]
            pin = {'key': key, 'repo': intent['repo'], 'revision': intent['revision'],
                   'prefix': prefix+'/'+ensemble+'/derivative', 'files': info['files'],
                   'feature_revision': design['feature_revision'], 'model_args': info['model_args'],
                   'training_verified': True, 'parent_frozen': True, 'seeds': design['seeds'],
                   'design_sha256': verified['design_sha256'], 'data_check_sha256': verified['data_check_sha256'],
                   'training_verified_sha256': digest(out/'verified.json'),
                   'strict_parity_positions': info['parity']['positions'],
                   'cached_positions_checked': info['parity']['cached_positions_checked'],
                   'qualification_eligible': False}
            validate_pin(pin, key, protocol)
            immutable_write(ROOT/'ai/strong/policy-iteration-development-pins-v2'/(key+'.json'), pin)
        print({'verified': True, 'head_type': args.head_type, 'seeds': design['seeds'],
               'ensemble_pins': 2, 'qualification_eligible': False}, flush=True)


if __name__ == '__main__':
    main()
