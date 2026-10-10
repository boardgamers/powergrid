"""Preserve all verified model/runtime files; append the broader arena only."""
import hashlib
import json
from pathlib import Path
import shutil
import tarfile
from huggingface_hub import HfApi,hf_hub_download

ROOT=Path(__file__).resolve().parents[2]
read=lambda p:json.loads(Path(p).read_text())
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
base=read(ROOT/'ai/strong/discard-correction-screen-source-v1.json')
archive=hf_hub_download('coyotte508/powergrid-ai-training-v1',base['archive'],repo_type='dataset',revision=base['revision'])
assert sha(archive)==base['sha256']
out=ROOT/'ai/runs/discard-opponents-source-v1';out.mkdir(exist_ok=False)
with tarfile.open(archive) as f:f.extractall(out,filter='data')
before={str(p.relative_to(out)):sha(p) for p in out.rglob('*') if p.is_file()}
overlays={}
for name in ['discard_opponents_screen.py','discard-opponents-protocol-v1.json']:
    relative='ai/strong/'+name;shutil.copy2(ROOT/relative,out/relative);overlays[relative]=sha(out/relative)
assert all(sha(out/k)==v for k,v in before.items())
target=ROOT/'ai/runs/strong-source-discard-opponents-20261010-v1.tgz';assert not target.exists()
with tarfile.open(target,'w:gz') as f:
    for p in sorted(out.rglob('*')):
        if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc':f.add(p,arcname=str(p.relative_to(out)),recursive=False)
r=HfApi().upload_file(repo_id='coyotte508/powergrid-ai-training-v1',repo_type='dataset',path_or_fileobj=target,path_in_repo=target.name)
record={'archive':target.name,'revision':r.oid,'sha256':sha(target),'overlays':overlays,
    'base':{k:base[k] for k in ['archive','revision','sha256']},'unchanged_base_file_count':len(before),
    'protocol_sha256':sha(out/'ai/strong/discard-opponents-protocol-v1.json'),
    'models_sha256':sha(out/'ai/strong/discard-correction-screen-models-v1.json'),'qualification_eligible':False}
(ROOT/'ai/strong/discard-opponents-source-v1.json').write_text(json.dumps(record,indent=2)+'\n')
print({k:v for k,v in record.items() if k not in ['overlays','base']})
