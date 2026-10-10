"""Freeze isolated phase instrumentation; preserve every existing runtime file."""
import json
import shutil
import subprocess
import sys
import tarfile

from huggingface_hub import HfApi, hf_hub_download
from phase_search_ablation import ROOT, PROTOCOL, read, write, digest

base = read(ROOT/'ai/strong/multiplayer-search-transfer-source-v1.json')
archive = hf_hub_download('coyotte508/powergrid-ai-training-v1', base['archive'], repo_type='dataset', revision=base['revision'])
assert digest(archive) == base['sha256']
out = ROOT/'ai/runs/phase-search-ablation-source-v1'; out.mkdir(exist_ok=False)
with tarfile.open(archive) as f: f.extractall(out, filter='data')
before = {str(p.relative_to(out)): digest(p) for p in out.rglob('*') if p.is_file()}
overlays = {}
for name in ['capture-search-phase.cjs', 'test-capture-search-phase.cjs', 'phase_search_ablation.py',
             'test_phase_search_ablation.py', 'phase-search-ablation-protocol-v1.json']:
    relative = 'ai/strong/'+name; assert not (out/relative).exists()
    shutil.copy2(ROOT/relative, out/relative); overlays[relative] = digest(out/relative)
fixture = json.loads(subprocess.check_output(['node', 'ai/strong/test-capture-search-phase.cjs'], cwd=out, text=True))
assert fixture['positions'] == 2553 and fixture['checks'] == 5533
test = subprocess.run([sys.executable, 'ai/strong/test_phase_search_ablation.py'], cwd=out, text=True, capture_output=True, check=True)
assert all(digest(out/p) == sha for p, sha in before.items())
target = ROOT/'ai/runs/strong-source-phase-search-ablation-20261010-v1.tgz'; assert not target.exists()
with tarfile.open(target, 'w:gz') as f:
    for p in sorted(out.rglob('*')):
        if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc':
            f.add(p, arcname=str(p.relative_to(out)), recursive=False)
upload = HfApi().upload_file(repo_id='coyotte508/powergrid-ai-training-v1', repo_type='dataset',
                            path_or_fileobj=target, path_in_repo=target.name)
record = {'archive': target.name, 'revision': upload.oid, 'sha256': digest(target), 'overlays': overlays,
          'base': {k: base[k] for k in ['archive', 'revision', 'sha256']},
          'unchanged_base_file_count': len(before), 'protocol_sha256': digest(PROTOCOL), 'qualification_eligible': False}
write(ROOT/'ai/strong/phase-search-ablation-source-v1.json', record)
preflight = {'source_revision': record['revision'], 'source_sha256': record['sha256'],
             'protocol_sha256': record['protocol_sha256'], 'frozen_package_passed': True,
             'fixture_checks': fixture, 'routing_tests': test.stderr.strip(),
             'complete_game_control_parity': 'pending HF probes', 'qualification_eligible': False}
write(ROOT/'ai/strong/phase-search-ablation-preflight-v1.json', preflight)
print(record)
