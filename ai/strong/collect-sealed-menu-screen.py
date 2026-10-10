"""Independently verify one immutable action-menu screen, including all raw outcomes."""
import argparse
from pathlib import Path
import re
from huggingface_hub import hf_hub_download
from five_plant_screen import ROOT, REPO, read, write, digest, collect
from sealed_menu_screen import prepare, validate_checks

p = argparse.ArgumentParser(__doc__)
p.add_argument('key', choices=['control', 'expanded'])
p.add_argument('revision')
p.add_argument('output', type=Path)
a = p.parse_args()
assert re.fullmatch('[a-f0-9]{40}', a.revision)
protocol = read(ROOT / 'ai/strong/sealed-menu-protocol-v1.json')
source = read(ROOT / 'ai/strong/sealed-menu-source-v1.json')
out = a.output.resolve(); out.mkdir(parents=True, exist_ok=True)

def fetch(name):
    assert Path(name).name == name
    raw = Path(hf_hub_download(REPO, f'runs/sealed-menu-screen-v1-{a.key}/{name}', revision=a.revision)).read_bytes()
    (out / name).write_bytes(raw)

fetch('screen-check.json')
status = read(out / 'screen-check.json')
assert status['key'] == a.key and status['status'] == 'complete'
assert status['games'] == 7520 and status['cells'] == 13 and status['truncations'] == 0
assert status['trained'] is False and status['qualification_eligible'] is False
assert status['protocol_sha256'] == digest(ROOT / 'ai/strong/sealed-menu-protocol-v1.json')
assert status['fixture_sha256'] == protocol['fixture_sha256']
assert status['source_revision'] == source['revision'] and status['source_sha256'] == source['sha256']
for name, sha in status['artifact_sha256'].items():
    fetch(name); assert digest(out / name) == sha
manifest = read(out / 'checkpoint.json')
assert prepare(a.key, out, protocol) == manifest
validate_checks(out, manifest)
assert collect(out, protocol, manifest) == read(out / 'summary.json')
write(out / 'verified.json', {'key': a.key, 'revision': a.revision, 'verified': True,
                            'screen_report_sha256': digest(out / 'screen-check.json'),
                            'games': 7520, 'truncations': 0, 'qualification_eligible': False})
print({k: round(v['win_rate'] * 100, 3) for k, v in read(out / 'summary.json')['cells'].items()})
