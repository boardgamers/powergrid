"""Independently recheck pinned repaired-export results and all original provenance."""
import argparse
from pathlib import Path
import re
from huggingface_hub import hf_hub_download
from inference64_screen import ROOT, REPO, PROTOCOL, config, prepare, check_validation, read, write, digest, collect

p = argparse.ArgumentParser(__doc__)
p.add_argument('cohort', choices=['five-plant', 'population'])
p.add_argument('key')
p.add_argument('revision')
p.add_argument('output', type=Path)
a = p.parse_args()
assert re.fullmatch('[a-f0-9]{40}', a.revision)
protocol, cfg, _ = config(a.cohort, a.key)
source = read(ROOT / f'ai/strong/inference64-screen-source-v1-{a.cohort}.json')
out = a.output.resolve()
out.mkdir(parents=True, exist_ok=True)
prefix = f'runs/inference64-screen-v1-{a.cohort}-{a.key}'


def fetch(name):
    rel = Path(name)
    assert not rel.is_absolute() and '..' not in rel.parts
    raw = Path(hf_hub_download(REPO, prefix + '/' + name, revision=a.revision)).read_bytes()
    (out / rel).parent.mkdir(parents=True, exist_ok=True)
    (out / rel).write_bytes(raw)


fetch('screen-check.json')
status = read(out / 'screen-check.json')
assert status['status'] == 'complete' and status['key'] == a.key and status['cohort'] == a.cohort
assert status['games'] == cfg['evaluation']['games_per_candidate']
assert status['cells'] == len(cfg['evaluation']['screens']) and status['truncations'] == 0
assert status['protocol_sha256'] == digest(PROTOCOL)
assert status['source_revision'] == source['revision'] and status['source_sha256'] == source['sha256']
for name, sha in status['artifact_sha256'].items():
    fetch(name)
    assert digest(out / name) == sha, name
manifest = read(out / 'evaluated-model.json')
assert manifest == prepare(a.cohort, a.key, out)
check_validation(out, manifest, protocol)
assert collect(out, cfg, manifest) == read(out / 'summary.json')
for name, sha in status['artifact_sha256'].items():
    assert digest(out / name) == sha, 'Revalidation changed evidence: ' + name
write(out / 'verified.json', {'cohort': a.cohort, 'key': a.key, 'revision': a.revision,
    'screen_report_sha256': digest(out / 'screen-check.json'), 'verified': True,
    'games': status['games'], 'truncations': 0, 'qualification_eligible': False})
print({k: round(v['win_rate'] * 100, 3) for k, v in read(out / 'summary.json')['cells'].items()})
