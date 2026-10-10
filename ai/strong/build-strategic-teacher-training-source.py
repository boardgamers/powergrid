"""Freeze the first balanced teacher pilot; keep all prior runtime source unchanged."""
import gzip
import shutil
import subprocess
import sys
import tarfile
from huggingface_hub import HfApi,hf_hub_download
from strategic_collection import ROOT,read,write,digest

base=read(ROOT/'ai/strong/strategic-teacher-probe-source-v1.json')
roots=read(ROOT/'ai/strong/strategic-teacher-training-roots-v1.json')
collection=read(ROOT/'ai/strong/strategic-training-collection-protocol-v1.json')
assert roots['positions']==1920 and roots['root_splits']=={'train':1440,'validation':480}
assert roots['no_whole_deal_split_leakage'] and roots['no_identical_public_root_crosses_splits']
protocol=ROOT/'ai/strong/strategic-teacher-training-protocol-v1.json';assert not protocol.exists()
write(protocol,{'purpose':'Paired counterfactual labels for a frozen-parent strategic correction pilot; no hard winner labels.',
    'repo':collection['repo'],'model':collection['model'],'ort_threads':1,'workers':24,'players':[2,3,4,5,6],
    'source_modes':['economic','snapshot0'],'modes':['neural','neural_economic'],'samples':48,'batches':['a','b'],
    'max_steps':2400,'roots_sha256':roots['sha256'],'positions':1920,'root_splits':roots['root_splits'],
    'deals':16,'deals_per_initial_shard':2,'roots_per_initial_shard':24,'first_shard':[0,2],
    'expected_complete_shards':160,'expected_first_wave_shards':20,
    'options':'Unchanged6-proposal geographic/economic shortlist plus exact frozen-model proposal.',
    'selection':'Every count/source/deal/rule/nomination-bid-building stratum, independently hash-selected before labels.',
    'split':'Entire count/source/deal units; all rule cells, decisions and continuation modes stay together.',
    'training_targets':'Preserve every sample outcome and advantage paired against the parent proposal, separately by continuation and batch. Do not convert noisy winning moves into hard labels.',
    'future_loss':'Equal continuation mixture, count/rule/decision/deal-balanced weights and paired-sample uncertainty. Freeze actual loss before gradients.',
    'runtime_admission':'First wave only uses verified matching two-sample probes, worst root time, linear48/2 scaling and2x time margin. Remaining shards require verified first-wave runtime. Never shorten horizons to fit.',
    'scope':'Initial economic/self-play teacher pilot. Search-opponent continuations remain an independent expensive diagnostic; no results here qualify a model.',
    'trained':False,'qualification_eligible':False})
archive=hf_hub_download('coyotte508/powergrid-ai-training-v1',base['archive'],repo_type='dataset',revision=base['revision'])
assert digest(archive)==base['sha256'];out=ROOT/'ai/runs/strategic-teacher-training-source-v1';out.mkdir(exist_ok=False)
with tarfile.open(archive) as f:f.extractall(out,filter='data')
before={str(p.relative_to(out)):digest(p) for p in out.rglob('*') if p.is_file()};overlays={}
for name in ['strategic_training_labels.py','check-strategic-teacher-training.py','strategic-teacher-training-protocol-v1.json','strategic-teacher-training-roots-v1.json']:
    rel='ai/strong/'+name;assert not (out/rel).exists();shutil.copy2(ROOT/rel,out/rel);overlays[rel]=digest(out/rel)
rel=roots['file'];assert not (out/rel).exists();shutil.copy2(ROOT/roots['local_file'],out/rel);overlays[rel]=digest(out/rel)
assert overlays[rel]==roots['sha256']
checked=subprocess.run([sys.executable,'ai/strong/check-strategic-teacher-training.py'],cwd=out,text=True,capture_output=True,check=True)
assert all(digest(out/p)==sha for p,sha in before.items())
target=ROOT/'ai/runs/strong-source-strategic-teacher-training-20261010-v1.tgz';assert not target.exists()
with tarfile.open(target,'w:gz') as f:
    for p in sorted(out.rglob('*')):
        if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc':f.add(p,arcname=str(p.relative_to(out)),recursive=False)
c=HfApi().upload_file(repo_id='coyotte508/powergrid-ai-training-v1',repo_type='dataset',path_or_fileobj=target,path_in_repo=target.name)
source={'archive':target.name,'revision':c.oid,'sha256':digest(target),'overlays':overlays,
    'base':{k:base[k] for k in ['archive','revision','sha256']},'unchanged_base_file_count':len(before),
    'protocol_sha256':digest(protocol),'qualification_eligible':False}
write(ROOT/'ai/strong/strategic-teacher-training-source-v1.json',source)
write(ROOT/'ai/strong/strategic-teacher-training-preflight-v1.json',{'passed':True,'source_revision':source['revision'],
    'source_sha256':source['sha256'],'root_contract_check':checked.stdout.strip(),
    'positions':1920,'train_roots':1440,'validation_roots':480,
    'whole_deal_splits_and_public_state_separation_verified':True,
    'scope':'First/last chunk rules and decision grids, exact proposals and immutable data provenance. No gradients or strength claim.',
    'qualification_eligible':False});print(source)
