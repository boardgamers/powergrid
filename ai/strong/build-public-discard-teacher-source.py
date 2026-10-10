"""Freeze the discard audit onto the already verified collection runtime."""
import hashlib
import json
from pathlib import Path
import shutil
import tarfile
from huggingface_hub import HfApi, hf_hub_download

ROOT = Path(__file__).resolve().parents[2]
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
base = json.loads((ROOT / 'ai/strong/public-discard-source-v1.json').read_text())
archive = Path(hf_hub_download('coyotte508/powergrid-ai-training-v1', base['archive'],
    repo_type='dataset', revision=base['revision']))
assert sha(archive) == base['sha256']
out = ROOT / 'ai/runs/public-discard-teacher-source-v1'
out.mkdir(exist_ok=False)
with tarfile.open(archive) as t:
    t.extractall(out, filter='data')
before = {str(p.relative_to(out)): sha(p) for p in out.rglob('*') if p.is_file()}
files = ['audit-public-discard-teacher.py', 'public-discard-teacher-protocol-v1.json',
         'audit-neural-continuations.py', 'continuation-rollouts.cjs', 'test-continuation-rollouts.cjs']
overlays = {}
for name in files:
    relative = 'ai/strong/' + name
    shutil.copy2(ROOT / relative, out / relative)
    overlays[relative] = sha(out / relative)
unchanged = {k: v for k, v in before.items() if k not in overlays}
assert all(sha(out / k) == v for k, v in unchanged.items())
name = 'strong-source-public-discard-teacher-20261010-v1.tgz'
target = ROOT / 'ai/runs' / name
with tarfile.open(target, 'w:gz') as t:
    for p in sorted(out.rglob('*')):
        if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc':
            t.add(p, arcname=str(p.relative_to(out)))
result = HfApi().upload_file(path_or_fileobj=target, path_in_repo=name,
    repo_id='coyotte508/powergrid-ai-training-v1', repo_type='dataset')
record = {'archive': name, 'revision': result.oid, 'sha256': sha(target),
    'base': {k: base[k] for k in ['archive', 'revision', 'sha256']},
    'overlays': overlays, 'unchanged_base_file_count': len(unchanged),
    'protocol_sha256': sha(out / 'ai/strong/public-discard-teacher-protocol-v1.json'),
    'qualification_eligible': False}
(ROOT / 'ai/strong/public-discard-teacher-source-v1.json').write_text(json.dumps(record, indent=2) + '\n')
print(json.dumps(record))
