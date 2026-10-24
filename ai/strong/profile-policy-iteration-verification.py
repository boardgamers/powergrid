"""Measure the existing immutable verifier before changing collection concurrency."""
import argparse
import hashlib
import importlib
import json
from pathlib import Path
import resource
import sys
import tarfile
import time

from huggingface_hub import hf_hub_download


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('runtime', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('shards', nargs='+')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    runtime = args.runtime.resolve()
    source = json.loads((root/'ai/strong/policy-iteration-labels-source-v2.json').read_text())
    archive = hf_hub_download('coyotte508/powergrid-ai-training-v1', source['archive'], repo_type='dataset', revision=source['revision'])
    assert digest(archive) == source['sha256']
    with tarfile.open(archive) as bundle:
        for member in bundle.getmembers():
            if member.isfile():
                assert digest(runtime/member.name) == hashlib.sha256(bundle.extractfile(member).read()).hexdigest()
    sys.path.insert(0, str(runtime/'ai/strong'))
    module = importlib.import_module('policy_iteration_labels')
    assert module.ROOT == runtime
    p = module.read(module.PROTOCOL)
    assert digest(module.PROTOCOL) == source['protocol_sha256']
    reports = []
    for key in args.shards:
        shard = module.find_shard(p, key)
        directory = root/'ai/runs/policy-iteration-labels-verified-v2'/key
        verified = module.read(directory/'verified.json')
        assert verified['verified'] and verified['source'] == source and verified['shard'] == shard
        for file, sha in verified['artifacts'].items():
            assert digest(directory/file) == sha
        started = time.monotonic()
        roots = module.load_roots(p, shard)
        loaded = time.monotonic()
        model = module.get_model(p)
        initialized = time.monotonic()
        summary = module.check(directory, p, shard, 'full', model, roots)
        checked = time.monotonic()
        assert summary == verified['summary']
        record = {'shard': key, 'roots': len(roots), 'rollouts': summary['rollouts'],
                  'load_roots_seconds': loaded-started, 'model_init_seconds': initialized-loaded,
                  'check_seconds': checked-initialized, 'total_seconds': checked-started,
                  'max_rss_kib': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                  'summary_identical': True}
        reports.append(record)
        print(record, flush=True)
    report = {'complete': True, 'source': source, 'cases': reports, 'gradients': False,
              'new_continuations': 0, 'qualification_eligible': False,
              'script_sha256': digest(__file__), 'scope': 'Serial verification timing on this local host, not training throughput or model strength.'}
    assert not args.output.exists()
    args.output.write_text(json.dumps(report, indent=2)+'\n')


if __name__ == '__main__':
    main()
