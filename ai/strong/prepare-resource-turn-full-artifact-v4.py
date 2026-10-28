"""Create an isolated local research artifact; never upload, launch or select."""
import argparse
import json
from pathlib import Path
import shutil

from resource_turn_public_policy_v2 import checked_path, digest

ROOT = Path(__file__).resolve().parents[2]
RUNTIME = ROOT/'ai/runs/resource-replanning-job-source-prepared-v1/layout'
MANIFEST = 'resource-job-manifest.json'
MANIFEST_SHA = 'cebda6cb0ed6a1eff28cad8cd02cb17e37bb62f59595b2237b989337b40a9415'
MODEL = ROOT/'ai/runs/policy-iteration-trained-8840u-prepared-v2/local-package-frozen-1/policy.onnx'
MODEL_SHA = '55331f43379e8fe89025d93b1a7a48c88e0ea39b4ebd3a7ef8240d4b62753530'
FILES = ('resource_turn_full_policy_v4.py', 'resource_turn_full_arena_v4.py',
         'resource_turn_full_audit_v4.py', 'resource_turn_public_policy_v2.py',
         'resource-turn-exchange-worker-v1.cjs', 'resource-turn-exchange-v1.cjs',
         'resource-turn-transaction-v1.cjs', 'resource-turn-arena-bridge-v1.cjs',
         'prepare-resource-turn-full-artifact-v4.py', 'resource-model-turn-v2.cjs',
         'resource-turn-search-worker-v2.cjs', 'resource-turn-search-worker-v4.cjs',
         'resource-turn-anchor-v2.cjs', 'resource_turn_anchored_search_v2.py',
         'resource_turn_anchor_verification_v2.py')


def write(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2, allow_nan=False); stream.write('\n')


def prepare(out):
    if out.exists():
        raise ValueError('Inspect the existing package before creating another')
    assert digest(RUNTIME/MANIFEST) == MANIFEST_SHA and digest(MODEL) == MODEL_SHA
    prior = json.loads((RUNTIME/MANIFEST).read_text())
    for name, sha in prior.items():
        assert digest(checked_path(RUNTIME, name)) == sha, name
    sources = {**{'runtime/'+name:checked_path(RUNTIME, name) for name in prior},
        'runtime/'+MANIFEST:RUNTIME/MANIFEST, 'model.onnx':MODEL,
        **{'policy/'+name:ROOT/'ai/strong'/name for name in FILES}}
    hashes = {name:digest(path) for name,path in sources.items()}
    out.mkdir()
    for name, source in sources.items():
        dest = out/name; dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, dest)
        assert digest(dest) == hashes[name], name
    write(out/'manifest.json', hashes)
    descriptor = {'revision':'resource-turn-full-artifact-v4',
        'manifest':{'path':'manifest.json', 'sha256':digest(out/'manifest.json')},
        'runtime':{'directory':'runtime', 'manifest':MANIFEST,
                   'path':'runtime/'+MANIFEST, 'sha256':MANIFEST_SHA},
        'model':{'path':'model.onnx', 'sha256':MODEL_SHA},
        'settings':{'samples':8, 'workers':1, 'threads':1, 'max_steps':2400},
        'frozen_modes':['filter', 'model-turn', 'search-turn', 'atomic-search', 'atomic-search-corrected', 'atomic-search-anchored'],
        'purpose':'Correct undo-commit versus buying-phase boundary in stable sampling. Historical artifacts remain unchanged; no new strategy study admitted',
        'qualification_eligible':False, 'reserved_final_seeds_used':False}
    write(out/'resource-full-descriptor.json', descriptor)
    print(json.dumps({'artifact':str(out), 'files':len(hashes),
        'descriptor_sha256':digest(out/'resource-full-descriptor.json'),
        'new_hf_jobs':0, 'qualified':False}), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('output', type=Path)
    prepare(parser.parse_args().output.resolve())
