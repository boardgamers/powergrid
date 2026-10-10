"""Freeze the multiplayer wrapper while keeping the tested engine/search unchanged."""
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile

from huggingface_hub import HfApi, hf_hub_download
from multiplayer_search_transfer import ROOT, PROTOCOL, read, write, digest

base = read(ROOT/'ai/strong/search-transfer-source-v1.json')
archive = hf_hub_download('coyotte508/powergrid-ai-training-v1', base['archive'],
                          repo_type='dataset', revision=base['revision'])
assert digest(archive) == base['sha256']
out = ROOT/'ai/runs/multiplayer-search-transfer-source-v1'; out.mkdir(exist_ok=False)
with tarfile.open(archive) as f: f.extractall(out, filter='data')
before = {str(p.relative_to(out)): digest(p) for p in out.rglob('*') if p.is_file()}
overlays = {}
for name in ['multiplayer_search_transfer.py', 'multiplayer-search-transfer-protocol-v1.json']:
    relative = 'ai/strong/'+name; assert not (out/relative).exists()
    shutil.copy2(ROOT/relative, out/relative); overlays[relative] = digest(out/relative)
code = '''
import copy,json,sys
from pathlib import Path
sys.path.insert(0,'ai/strong')
from multiplayer_search_transfer import read,verify
protocol=read('ai/strong/multiplayer-search-transfer-protocol-v1.json');primary=Path(sys.argv[1])
games=0;negative_checks=0
for n in [3,4]:
 for key in protocol['models']:
  raw=read(primary/f'ai/runs/discard-opponents-verified-v1/{key}-{n}p/search_geo.json')
  games+=verify(raw,protocol,key,n,guided=False)['games']
  for fault in ['raw-as-guided','budget','model','missing','cap','reference','seed','search-cap']:
   bad=copy.deepcopy(raw)
   if fault=='budget':bad['candidate_search_samples']=16
   elif fault=='model':bad['model_sha256']='wrong'
   elif fault=='missing':bad['results'].pop()
   elif fault=='cap':bad['results'][0]['truncated']=True
   elif fault=='reference':bad['opponent']='rush'
   elif fault=='seed':bad['results'][0]['gameSeed']='unprescribed'
   elif fault=='search-cap':bad['results'][0]['searchStats']['search_geo']['truncated']=1
   try:verify(bad,protocol,key,n,guided=fault=='raw-as-guided')
   except (ValueError,AssertionError):negative_checks+=1
   else:raise AssertionError('Fault accepted:'+fault)
assert games==672 and negative_checks==48
print(json.dumps({'baseline_games':games,'negative_checks':negative_checks,'verified_players':[3,4]}))
'''
import json
checks = json.loads(subprocess.check_output([sys.executable, '-c', code, str(ROOT)], cwd=out, text=True))
assert all(digest(out/p) == sha for p, sha in before.items())
target = ROOT/'ai/runs/strong-source-multiplayer-search-transfer-20261010-v1.tgz'; assert not target.exists()
with tarfile.open(target, 'w:gz') as f:
    for p in sorted(out.rglob('*')):
        if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc':
            f.add(p, arcname=str(p.relative_to(out)), recursive=False)
uploaded = HfApi().upload_file(repo_id='coyotte508/powergrid-ai-training-v1', repo_type='dataset',
    path_or_fileobj=target, path_in_repo=target.name)
record = {'archive': target.name, 'revision': uploaded.oid, 'sha256': digest(target),
          'overlays': overlays, 'base': {k: base[k] for k in ['archive', 'revision', 'sha256']},
          'unchanged_base_file_count': len(before), 'protocol_sha256': digest(PROTOCOL), 'qualification_eligible': False}
write(ROOT/'ai/strong/multiplayer-search-transfer-source-v1.json', record)
preflight = {'source_revision': uploaded.oid, 'source_sha256': record['sha256'],
             'protocol_sha256': record['protocol_sha256'], 'frozen_package_passed': True, **checks,
             'scope': 'Unchanged tested engine, models and search;672 real raw-baseline games verify and48 altered contracts fail. New3-6p guided HF probe results remain required.',
             'qualification_eligible': False}
write(ROOT/'ai/strong/multiplayer-search-transfer-preflight-v1.json', preflight)
print(preflight)
