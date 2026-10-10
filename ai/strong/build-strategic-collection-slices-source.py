"""Freeze deal-range scheduling while preserving the original data protocol."""
import shutil
import tarfile
from huggingface_hub import HfApi, hf_hub_download
from strategic_collection import ROOT, PROTOCOL, read, write, digest

base=read(ROOT/'ai/strong/strategic-training-collection-source-v1.json')
check=read(ROOT/'ai/runs/strategic-collection-slices-preflight-v1/check.json')
assert check['exact_game_rows_match_unsliced'] and check['exact_public_roots_and_proposals_match_unsliced'] and check['twin_controls_match']
archive=hf_hub_download('coyotte508/powergrid-ai-training-v1',base['archive'],repo_type='dataset',revision=base['revision'])
assert digest(archive)==base['sha256']
out=ROOT/'ai/runs/strategic-training-collection-slices-source-v1';out.mkdir(exist_ok=False)
with tarfile.open(archive) as f:f.extractall(out,filter='data')
before={str(p.relative_to(out)):digest(p) for p in out.rglob('*') if p.is_file()};overlays={}
for name in ['strategic_collection_slices.py','check-strategic-collection-slices.py']:
    relative='ai/strong/'+name;assert not (out/relative).exists()
    shutil.copy2(ROOT/relative,out/relative);overlays[relative]=digest(out/relative)
assert all(digest(out/p)==sha for p,sha in before.items())
target=ROOT/'ai/runs/strong-source-strategic-training-collection-slices-20261010-v1.tgz';assert not target.exists()
with tarfile.open(target,'w:gz') as f:
    for p in sorted(out.rglob('*')):
        if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc':f.add(p,arcname=str(p.relative_to(out)),recursive=False)
upload=HfApi().upload_file(repo_id='coyotte508/powergrid-ai-training-v1',repo_type='dataset',path_or_fileobj=target,path_in_repo=target.name)
source={'archive':target.name,'revision':upload.oid,'sha256':digest(target),'overlays':overlays,
    'base':{k:base[k] for k in ['archive','revision','sha256']},'unchanged_base_file_count':len(before),
    'protocol_sha256':digest(PROTOCOL),'scope':'Only deal-range scheduling changes; identical game seeds, model, horizon and root-selection/split protocol.',
    'qualification_eligible':False}
write(ROOT/'ai/strong/strategic-training-collection-slices-source-v1.json',source)
write(ROOT/'ai/strong/strategic-training-collection-slices-preflight-v1.json',{
    'source_revision':source['revision'],'source_sha256':source['sha256'],'passed':True,'parity':check,
    'scope':'Actual nonzero-offset scheduling parity with verified unsliced games; unchanged base engine and inference code.',
    'qualification_eligible':False});print(source)
