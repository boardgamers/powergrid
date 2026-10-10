"""Freeze the verified engine/label runtime plus the explicit learned-head files."""
import hashlib
import json
from pathlib import Path
import shutil
import tarfile
from huggingface_hub import HfApi, hf_hub_download

ROOT=Path(__file__).resolve().parents[2]
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
base=json.loads((ROOT/'ai/strong/discard-training-labels-source-v1.json').read_text())
archive=hf_hub_download('coyotte508/powergrid-ai-training-v1',base['archive'],repo_type='dataset',revision=base['revision'])
assert sha(archive)==base['sha256']
out=ROOT/'ai/runs/discard-correction-source-v1';out.mkdir(exist_ok=False)
with tarfile.open(archive) as f:f.extractall(out,filter='data')
before={str(p.relative_to(out)):sha(p) for p in out.rglob('*') if p.is_file()}
names=['model.py','model_discard.py','features-v4_2.cjs','encoders.cjs','evaluate.py','export-inference64.py',
       'package-serving.py','test_model_discard.py','test-discard-correction-features.cjs',
       'discard_correction_data.py','train-discard-correction.py','check-discard-correction.py',
       'discard-correction-protocol-v1.json','verify-discard-training-labels.py','collect-public-discard-teacher.py',
       'discard-training-labels-source-v1.json','discard-training-labels-results-v1.json']
overlays={}
for name in names:
    relative='ai/strong/'+name;shutil.copy2(ROOT/relative,out/relative);overlays[relative]=sha(out/relative)
unchanged={k:v for k,v in before.items() if k not in overlays}
assert all(sha(out/k)==v for k,v in unchanged.items())
assert all(k in unchanged for k in ['ai/strong/features-v4.cjs','ai/strong/features-v4_1.cjs','ai/strong/model_v4.py',
    'ai/strong/bridge.cjs','ai/strong/economics.cjs','ai/strong/continuation-rollouts.cjs'])
target=ROOT/'ai/runs/strong-source-discard-correction-20261010-v1.tgz';assert not target.exists()
with tarfile.open(target,'w:gz') as f:
    for p in sorted(out.rglob('*')):
        if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc':f.add(p,arcname=str(p.relative_to(out)),recursive=False)
r=HfApi().upload_file(repo_id='coyotte508/powergrid-ai-training-v1',repo_type='dataset',path_or_fileobj=target,path_in_repo=target.name)
record={'archive':target.name,'revision':r.oid,'sha256':sha(target),'bytes':target.stat().st_size,
    'base':{k:base[k] for k in ['archive','revision','sha256']},'overlays':overlays,
    'unchanged_base_file_count':len(unchanged),'protocol_sha256':sha(out/'ai/strong/discard-correction-protocol-v1.json'),
    'qualification_eligible':False}
(ROOT/'ai/strong/discard-correction-source-v1.json').write_text(json.dumps(record,indent=2)+'\n')
print({k:v for k,v in record.items() if k not in ['overlays','base']})
