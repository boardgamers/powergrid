"""Freeze fresh training capture without changing any existing engine/model code."""
import shutil
import subprocess
import sys
import tarfile
from huggingface_hub import HfApi, hf_hub_download
from strategic_collection import ROOT, PROTOCOL, SOURCE, read, write, digest

base=read(ROOT/'ai/strong/multiplayer-search-transfer-source-v1.json')
archive=hf_hub_download('coyotte508/powergrid-ai-training-v1',base['archive'],repo_type='dataset',revision=base['revision'])
assert digest(archive)==base['sha256']
out=ROOT/'ai/runs/strategic-training-collection-source-v1';out.mkdir(exist_ok=False)
with tarfile.open(archive) as f:f.extractall(out,filter='data')
before={str(p.relative_to(out)):digest(p) for p in out.rglob('*') if p.is_file()}
overlays={}
for name in ['capture-strategic-training.cjs','test-strategic-training-capture.cjs','strategic_collection.py',
             'test_strategic_collection.py','strategic-training-collection-protocol-v1.json']:
    relative='ai/strong/'+name;assert not (out/relative).exists()
    shutil.copy2(ROOT/relative,out/relative);overlays[relative]=digest(out/relative)
fixture=subprocess.check_output(['node','ai/strong/test-strategic-training-capture.cjs'],cwd=out,text=True)
import json
fixture=json.loads(fixture);assert fixture['positions']==2553 and fixture['private_data_invariant']
test=subprocess.run([sys.executable,'ai/strong/test_strategic_collection.py'],cwd=out,text=True,capture_output=True,check=True)
assert all(digest(out/p)==sha for p,sha in before.items())
target=ROOT/'ai/runs/strong-source-strategic-training-collection-20261010-v1.tgz';assert not target.exists()
with tarfile.open(target,'w:gz') as f:
    for p in sorted(out.rglob('*')):
        if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc':f.add(p,arcname=str(p.relative_to(out)),recursive=False)
uploaded=HfApi().upload_file(repo_id='coyotte508/powergrid-ai-training-v1',repo_type='dataset',path_or_fileobj=target,path_in_repo=target.name)
record={'archive':target.name,'revision':uploaded.oid,'sha256':digest(target),'overlays':overlays,
        'base':{k:base[k] for k in ['archive','revision','sha256']},'unchanged_base_file_count':len(before),
        'protocol_sha256':digest(PROTOCOL),'qualification_eligible':False}
write(SOURCE,record)
write(ROOT/'ai/strong/strategic-training-collection-preflight-v1.json',{'source_revision':record['revision'],
    'source_sha256':record['sha256'],'frozen_package_passed':True,'fixtures':fixture,'contract_tests':test.stderr.strip(),
    'local_twin_smoke':read(ROOT/'ai/runs/strategic-collection-local-preflight-v1/collection-check.json'),
    'scope':'Fixture privacy/menu parity plus local eight-game capture check. Independent HF probes still required before full launch.',
    'qualification_eligible':False})
print(record)
