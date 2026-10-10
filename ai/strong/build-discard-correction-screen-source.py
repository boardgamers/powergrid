"""Pin verified learned models and preserve the training/engine runtime for arenas."""
import hashlib
import json
from pathlib import Path
import shutil
import tarfile
from huggingface_hub import HfApi, hf_hub_download

ROOT=Path(__file__).resolve().parents[2]
read=lambda p:json.loads(Path(p).read_text())
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,d):Path(p).write_text(json.dumps(d,indent=2)+'\n')
verified=read(ROOT/'ai/runs/discard-correction-verified-v1-recheck/verified.json')
parent=read(ROOT/'ai/strong/inference64-screen-protocol-v1.json')['cohorts']['five-plant']['models']['parent']
old=parent['derivative']
models={'parent':{'revision':old['revision'],'prefix':old['prefix'],
    'files':{k:old['files'][k] for k in ['inference64.onnx','inference64.pt']},'feature_revision':parent['feature_revision']}}
for seed,result in verified['seeds'].items():
    path=ROOT/'ai/runs/discard-correction-verified-v1-recheck'/seed/'derivative'
    assert result['parent_tensors_identical'] and result['scope']['labels_strict_parity']==3361
    assert result['parity']['positions']==result['serving']['positions']==2553
    models[seed]={'revision':verified['revision'],'prefix':verified['prefix']+'/'+seed+'/derivative',
        'files':{name:sha(path/name) for name in ['inference64.onnx','inference64.pt']},
        'feature_revision':result['parity']['feature_revision'],'selected_epoch':result['selected_epoch']}
    assert models[seed]['files']['inference64.onnx']==result['model_sha256']
write(ROOT/'ai/strong/discard-correction-results-v1.json',verified)
write(ROOT/'ai/strong/discard-correction-screen-models-v1.json',models)
base=read(ROOT/'ai/strong/discard-correction-source-v1.json')
archive=hf_hub_download('coyotte508/powergrid-ai-training-v1',base['archive'],repo_type='dataset',revision=base['revision'])
assert sha(archive)==base['sha256']
out=ROOT/'ai/runs/discard-correction-screen-source-v1';out.mkdir(exist_ok=False)
with tarfile.open(archive) as f:f.extractall(out,filter='data')
before={str(p.relative_to(out)):sha(p) for p in out.rglob('*') if p.is_file()}
overlays={}
for name in ['discard_correction_screen.py','discard-correction-screen-protocol-v1.json',
    'discard-correction-screen-models-v1.json','discard-correction-results-v1.json']:
    relative='ai/strong/'+name;shutil.copy2(ROOT/relative,out/relative);overlays[relative]=sha(out/relative)
assert all(sha(out/name)==value for name,value in before.items() if name not in overlays)
target=ROOT/'ai/runs/strong-source-discard-correction-screen-20261010-v1.tgz';assert not target.exists()
with tarfile.open(target,'w:gz') as f:
    for p in sorted(out.rglob('*')):
        if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc':f.add(p,arcname=str(p.relative_to(out)),recursive=False)
r=HfApi().upload_file(repo_id='coyotte508/powergrid-ai-training-v1',repo_type='dataset',path_or_fileobj=target,path_in_repo=target.name)
manifest={'archive':target.name,'revision':r.oid,'sha256':sha(target),'overlays':overlays,
    'base':{k:base[k] for k in ['archive','revision','sha256']},'unchanged_base_file_count':sum(k not in overlays for k in before),
    'protocol_sha256':sha(out/'ai/strong/discard-correction-screen-protocol-v1.json'),
    'models_sha256':sha(out/'ai/strong/discard-correction-screen-models-v1.json'),'qualification_eligible':False}
write(ROOT/'ai/strong/discard-correction-screen-source-v1.json',manifest)
print({k:v for k,v in manifest.items() if k not in ['overlays','base']})
