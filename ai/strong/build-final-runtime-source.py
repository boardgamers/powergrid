"""Freeze only the provenance-aware job wrapper; do not run reserved tests."""
from pathlib import Path
import shutil
import tarfile

from huggingface_hub import HfApi, hf_hub_download
from five_plant_screen import ROOT, read, write, digest

base = read(ROOT/'ai/strong/multiplayer-search-transfer-source-v1.json')
archive = hf_hub_download('coyotte508/powergrid-ai-training-v1', base['archive'],
                          repo_type='dataset', revision=base['revision'])
assert digest(archive) == base['sha256']
out = ROOT/'ai/runs/final-runtime-source-v1'; out.mkdir(exist_ok=False)
with tarfile.open(archive) as f: f.extractall(out, filter='data')
before = {str(p.relative_to(out)): digest(p) for p in out.rglob('*') if p.is_file()}
relative = 'ai/strong/arena-job.py'; assert relative in before
shutil.copy2(ROOT/relative, out/relative)
assert all(digest(out/p) == sha for p, sha in before.items() if p != relative)
target = ROOT/'ai/runs/strong-source-final-runtime-20261010-v1.tgz'; assert not target.exists()
with tarfile.open(target, 'w:gz') as f:
    for p in sorted(out.rglob('*')):
        if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc':
            f.add(p, arcname=str(p.relative_to(out)), recursive=False)
upload = HfApi().upload_file(repo_id='coyotte508/powergrid-ai-training-v1', repo_type='dataset',
                            path_or_fileobj=target, path_in_repo=target.name)
record = {'archive': target.name, 'revision': upload.oid, 'sha256': digest(target),
          'base': {k: base[k] for k in ['archive', 'revision', 'sha256']},
          'overlays': {relative: digest(out/relative)}, 'old_runner_sha256': before[relative],
          'arena_runner_sha256': digest(out/relative), 'unchanged_base_file_count': len(before)-1,
          'scope': 'Arena wrapper checks supplied model hashes and records pinned runtime/model provenance; all engine, model inference, search, features and arena evaluation bytes unchanged. No reserved games or model selection.',
          'qualification_eligible': False}
write(ROOT/'ai/strong/final-runtime-source-v1.json', record)
print(record)
