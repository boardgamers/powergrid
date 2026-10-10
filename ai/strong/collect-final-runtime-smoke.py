"""Check the development-only end-to-end arena plumbing; never qualifies a model."""
import argparse
from pathlib import Path
import re

from huggingface_hub import HfApi, hf_hub_download
from search_transfer import ROOT, read, write, digest, module, verify


def main(revision):
    assert re.fullmatch('[a-f0-9]{40}', revision)
    record = read(ROOT/'ai/strong/final-runtime-smoke-v1.json')
    assert record['seed'] == 'final-runtime-smoke-development-v1-2p'
    assert record['run_name'] == 'final-runtime-smoke-development-v1'
    assert record['games'] == 8 and record['players'] == 2 and record['samples'] == 48 and record['geography']
    assert record['qualification_eligible'] is False
    assert HfApi().inspect_job(job_id=record['job_id']).status.stage == 'COMPLETED'
    protocol = read(ROOT/'ai/strong/search-transfer-protocol-v1.json')
    assert record['model'] == protocol['models']['10102']
    path = hf_hub_download(protocol['repo'], 'runs/'+record['run_name']+'/evaluation.json', revision=revision)
    report = read(Path(path))
    source = record['source']
    assert report['source'] == {k: source[k] for k in ['archive', 'revision', 'sha256']}
    assert report['arena_runner_sha256'] == source['arena_runner_sha256']
    assert report['model_repository_revision'] == record['model']['revision']
    assert report['opponent_repository_revision'] is None
    assert report['run_name'] == record['run_name']
    case = {'id': 'runtime-smoke', 'players': 2, 'deals': 1, 'opponent': 'heuristic', 'seed': record['seed']}
    summary = verify(report, protocol, '10102', case)
    merger = module('final_runtime_smoke_merger', 'merge-arena-reports.py')
    aggregate = merger.merge([path])
    assert aggregate['games'] == 8 and aggregate['independent_seeds'] == 1
    out = ROOT/'ai/runs/final-runtime-smoke-verified-v1'; out.mkdir(exist_ok=False)
    (out/'evaluation.json').write_bytes(Path(path).read_bytes())
    result = {'revision': revision, 'job_id': record['job_id'], 'source': source,
              'model': record['model'], 'games': 8, 'search_stats': summary['search_stats'],
              'seconds': summary['seconds'], 'verified': True, 'qualification_eligible': False,
              'scope': 'One fresh development deal with all seats/rules; execution and provenance only, not strength.',
              'artifacts': {'evaluation.json': digest(out/'evaluation.json')}}
    write(out/'verified.json', result)
    print({k: result[k] for k in ['job_id', 'games', 'search_stats', 'seconds', 'verified']})


if __name__ == '__main__':
    p = argparse.ArgumentParser(__doc__); p.add_argument('revision'); main(p.parse_args().revision)
