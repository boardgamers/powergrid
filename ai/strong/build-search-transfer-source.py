"""Freeze the search wrapper without changing the engine, policies or opponents."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
from huggingface_hub import HfApi,hf_hub_download

ROOT=Path(__file__).resolve().parents[2]
read=lambda p:json.loads(Path(p).read_text())
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
base=read(ROOT/'ai/strong/discard-opponents-source-v1.json')
archive=hf_hub_download('coyotte508/powergrid-ai-training-v1',base['archive'],repo_type='dataset',revision=base['revision'])
assert sha(archive)==base['sha256']
out=ROOT/'ai/runs/search-transfer-source-v1';out.mkdir(exist_ok=False)
with tarfile.open(archive) as f:f.extractall(out,filter='data')
before={str(p.relative_to(out)):sha(p) for p in out.rglob('*') if p.is_file()}
overlays={}
for name in ['search_transfer.py','search-transfer-protocol-v1.json','check-search-transfer.cjs','compare-population-screens.py']:
    relative='ai/strong/'+name;assert not (out/relative).exists()
    shutil.copy2(ROOT/relative,out/relative);overlays[relative]=sha(out/relative)
routing=json.loads(subprocess.check_output(['node','ai/strong/check-search-transfer.cjs'],cwd=out,text=True))
assert routing['positions']==2553 and routing['routes']==5106 and routing['eligibleDiscards']==9
baseline_code='''
import json,sys
from pathlib import Path
sys.path.insert(0,'ai/strong')
from search_transfer import read,verify,digest
protocol=read('ai/strong/search-transfer-protocol-v1.json')
primary=Path(sys.argv[1]);games=0
for case in protocol['cases']:
 for key in protocol['models']:
  path=primary/f'ai/runs/discard-opponents-verified-v1/{key}-2p/{case["opponent"]}.json' if case['players']==2 else primary/f'ai/runs/discard-correction-screen-verified-v1/{key}/a260-3p.json'
  assert digest(path)==case['baselines'][key]['sha256']
  games+=verify(read(path),protocol,key,case,False)['games']
assert games==1152
print(json.dumps({'baseline_games':games,'all_baseline_contracts_passed':True}))
'''
baseline=json.loads(subprocess.check_output([sys.executable,'-c',baseline_code,str(ROOT)],cwd=out,text=True))
assert all(sha(out/k)==v for k,v in before.items())
target=ROOT/'ai/runs/strong-source-search-transfer-20261010-v1.tgz';assert not target.exists()
with tarfile.open(target,'w:gz') as f:
    for p in sorted(out.rglob('*')):
        if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc':f.add(p,arcname=str(p.relative_to(out)),recursive=False)
r=HfApi().upload_file(repo_id='coyotte508/powergrid-ai-training-v1',repo_type='dataset',path_or_fileobj=target,path_in_repo=target.name)
record={'archive':target.name,'revision':r.oid,'sha256':sha(target),'overlays':overlays,
    'base':{k:base[k] for k in ['archive','revision','sha256']},'unchanged_base_file_count':len(before),
    'protocol_sha256':sha(out/'ai/strong/search-transfer-protocol-v1.json'),'qualification_eligible':False}
(ROOT/'ai/strong/search-transfer-source-v1.json').write_text(json.dumps(record,indent=2)+'\n')
preflight={'source_revision':r.oid,'source_sha256':record['sha256'],'protocol_sha256':record['protocol_sha256'],
    'routing':routing,'baseline':baseline,'frozen_package_passed':True,
    'full_game_search48_smoke_verified':False,'scope':'Frozen-package routing and baseline admission only. Complete HF games and runtime still required.','qualification_eligible':False}
(ROOT/'ai/strong/search-transfer-local-preflight-v1.json').write_text(json.dumps(preflight,indent=2)+'\n')
print({k:v for k,v in record.items() if k not in ['overlays','base']})
