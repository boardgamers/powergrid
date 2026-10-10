"""Recheck all raw paired outcomes and artifact provenance from a completed HF screen."""
import argparse
from pathlib import Path
import re
from huggingface_hub import hf_hub_download
from five_plant_screen import ROOT, REPO, COUNTS, digest, read, write, prepare, collect

p = argparse.ArgumentParser(__doc__)
p.add_argument('key')
p.add_argument('revision')
p.add_argument('output', type=Path)
a = p.parse_args()
assert re.fullmatch('[a-f0-9]{40}', a.revision)
protocol = read(ROOT / 'ai/strong/five-plant-ablation-protocol-v1.json')
source = read(ROOT / 'ai/strong/five-plant-screen-source-v1.json')
assert a.key in ['parent', *protocol['runs']]
out = a.output.resolve()
out.mkdir(parents=True, exist_ok=True)
prefix = 'runs/five-plant-screen-v1-' + a.key

def fetch(name):
    assert Path(name).name == name
    raw = Path(hf_hub_download(REPO, prefix + '/' + name, revision=a.revision)).read_bytes()
    (out / name).write_bytes(raw)

fetch('screen-check.json')
status = read(out / 'screen-check.json')
assert status['key'] == a.key and status['status'] == 'complete'
assert status['games'] == 4000 and status['cells'] == 7 and status['truncations'] == 0
assert status['protocol_sha256'] == digest(ROOT / 'ai/strong/five-plant-ablation-protocol-v1.json')
assert status['source_revision'] == source['revision'] and status['source_sha256'] == source['sha256']
for name, sha in status['artifact_sha256'].items():
    fetch(name)
    assert digest(out / name) == sha, name
manifest = read(out / 'checkpoint.json')
assert manifest == prepare(a.key, status['model_revision'], out, protocol)
parity, serving = read(out / 'parity.json'), read(out / 'serving.json')
assert parity['positions'] == serving['positions'] == 2553
assert parity['by_player_count'] == COUNTS
assert {k: v['positions'] for k, v in serving['by_player_count'].items()} == COUNTS
assert parity['feature_revision'] == manifest['feature_revision']
assert parity['all_actions_match'] and parity['inactive_values_zero'] and serving['all_moves_legal']
assert parity['model_sha256'] == serving['model_sha256'] == manifest['hashes']['latest.onnx']
assert collect(out, protocol, manifest) == read(out / 'summary.json')
write(out / 'verified.json', {'key': a.key, 'revision': a.revision, 'verified': True,
                            'screen_report_sha256': digest(out / 'screen-check.json'),
                            'games': 4000, 'truncations': 0, 'qualification_eligible': False})
print({k: round(v['win_rate'] * 100, 3) for k, v in read(out / 'summary.json')['cells'].items()})
