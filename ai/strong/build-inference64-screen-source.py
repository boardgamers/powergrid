"""Preserve each original arena runtime; overlay only explicit numerical-repair tooling."""
import argparse
from pathlib import Path
import shutil
import tarfile
from huggingface_hub import HfApi, hf_hub_download
from inference64_screen import ROOT, PROTOCOL, read, write, digest

p = argparse.ArgumentParser(__doc__)
p.add_argument('cohort', choices=['population', 'five-plant'])
a = p.parse_args()
if a.cohort == 'population':
    base = {'archive': 'strong-source-v32.tgz', 'revision': '37465b08df007221665d796448aea57e6828257e',
            'sha256': 'b95ab1d8bc8f2bae42e7428d8f7d80e727083c3e48f8c0075d64e6ae16144bfc'}
else:
    base = {k: read(ROOT / 'ai/strong/five-plant-screen-source-v1.json')[k]
            for k in ['archive', 'revision', 'sha256']}
source = hf_hub_download('coyotte508/powergrid-ai-training-v1', base['archive'],
                         repo_type='dataset', revision=base['revision'])
assert digest(source) == base['sha256']
out = ROOT / 'ai/runs' / ('inference64-screen-source-v1-' + a.cohort)
out.mkdir(exist_ok=False)
with tarfile.open(source) as file:
    file.extractall(out, filter='data')
original = {str(p.relative_to(out)): digest(p) for p in out.rglob('*') if p.is_file()}
names = ['model.py', 'audit-inference64.py', 'inference64_screen.py', 'launch-inference64-screen.py',
    'collect-inference64-screen.py', 'five_plant_screen.py', 'collect-population-screen.py',
    'prepare-population-screen.py', 'test_five_plant_screen.py', 'inference64-screen-protocol-v1.json',
    'population-training-protocol-v1.json', 'five-plant-ablation-protocol-v1.json',
    'five-plant-ablation-source-v1.json', 'population-opponents-v1.json']
overlays = {}
for name in names:
    rel = 'ai/strong/' + name
    shutil.copyfile(ROOT / rel, out / rel)
    overlays[rel] = digest(out / rel)
fixture = 'ai/strong/fixtures/multiplayer-serving-v1.jsonl'
(out / fixture).parent.mkdir(parents=True, exist_ok=True)
shutil.copyfile(ROOT / 'ai/runs/multiplayer-serving-fixtures.jsonl', out / fixture)
assert digest(out / fixture) == read(PROTOCOL)['fixture_sha256']
allowed = set(overlays) | {fixture}
unchanged = {name: sha for name, sha in original.items() if name not in allowed}
assert all(digest(out / name) == sha for name, sha in unchanged.items())
assert all(name not in overlays for name in ['ai/infer.py', 'ai/pool.py', 'ai/strong/bridge.cjs',
    'ai/strong/evaluate.py', 'ai/strong/economics.cjs', 'ai/strong/model_v4.py'])
archive = ROOT / 'ai/runs' / ('strong-source-inference64-screen-20261010-v1-' + a.cohort + '.tgz')
assert not archive.exists()
with tarfile.open(archive, 'w:gz') as file:
    for path in sorted(out.rglob('*')):
        if path.is_file():
            file.add(path, arcname=str(path.relative_to(out)), recursive=False)
result = HfApi().upload_file(repo_id='coyotte508/powergrid-ai-training-v1', repo_type='dataset',
    path_or_fileobj=archive, path_in_repo=archive.name,
    commit_message='Freeze ' + a.cohort + ' numerical-repair arena with original game runtime')
manifest = {'archive': archive.name, 'sha256': digest(archive), 'revision': result.oid,
    'bytes': archive.stat().st_size, 'base': base, 'overlays': overlays,
    'unchanged_base_files': unchanged, 'fixture_sha256': digest(out / fixture),
    'protocol_sha256': digest(PROTOCOL), 'cohort': a.cohort,
    'scope': 'Original engine, inference runner, features, candidates and opponents retained. Explicit numerical derivative only; fresh development rerun, not qualification.'}
write(ROOT / f'ai/strong/inference64-screen-source-v1-{a.cohort}.json', manifest)
print({'cohort': a.cohort, 'revision': result.oid, 'unchanged_base_files': len(unchanged)})
