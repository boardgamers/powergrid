"""Add the new teacher runtime to the unchanged, pinned collection source."""
import shutil
import subprocess
import tarfile
from huggingface_hub import HfApi, hf_hub_download
from strategic_collection import ROOT, read, write, digest

base=read(ROOT/'ai/strong/strategic-training-collection-source-v1.json')
roots=read(ROOT/'ai/strong/strategic-teacher-probe-roots-v1.json')
collection=read(ROOT/'ai/strong/strategic-training-collection-protocol-v1.json')
batching=read(ROOT/'ai/runs/strategic-teacher-batching-check-v1.json')
assert batching['positions']==2553 and batching['all_actions_match_serial'] and batching['reverse_order_passed']
protocol_path=ROOT/'ai/strong/strategic-teacher-probe-protocol-v1.json';assert not protocol_path.exists()
write(protocol_path,{'purpose':'Runtime feasibility only, before full paired-continuation training labels.',
    'repo':collection['repo'],'model':collection['model'],'ort_threads':1,'workers':24,
    'players':[2,3,4,5,6],'modes':['neural','neural_economic','neural_search','mixed_control'],
    'samples':2,'batches':['a','b'],'max_steps':2400,'nested_search_samples':16,'nested_search_candidates':6,
    'nested_search_max_steps':2400,'roots_sha256':roots['sha256'],
    'root_positions':10,'positions_per_job':2,'expected_jobs':20,
    'options':'Unchanged geography/economics shortlist plus exact frozen-model proposal.',
    'seed':'Independent public-world seeds from rootId and batch, shared across modes and root actions; never the true game seed.',
    'outputs':'Individual terminal credits, paired advantages over the model proposal, all outer/nested caps and timings. No hard labels.',
    'scope':'Validation-only roots chosen by hash; two samples cannot establish target reliability or playing strength.',
    'trained':False,'qualification_eligible':False})
archive=hf_hub_download('coyotte508/powergrid-ai-training-v1',base['archive'],repo_type='dataset',revision=base['revision'])
assert digest(archive)==base['sha256']
out=ROOT/'ai/runs/strategic-teacher-probe-source-v1';out.mkdir(exist_ok=False)
with tarfile.open(archive) as f:f.extractall(out,filter='data')
before={str(p.relative_to(out)):digest(p) for p in out.rglob('*') if p.is_file()}
overlays={}
for name in ['strategic-continuations.cjs','test-strategic-continuations.cjs','strategic_teacher.py',
             'check-strategic-teacher-batching.py','run-strategic-teacher-probe.py',
             'strategic-teacher-probe-protocol-v1.json','strategic-teacher-probe-roots-v1.json',
             'fixtures/strategic-teacher-probe-v1.jsonl']:
    relative='ai/strong/'+name;assert not (out/relative).exists()
    shutil.copy2(ROOT/relative,out/relative);overlays[relative]=digest(out/relative)
tests=subprocess.run(['node','--test','ai/strong/test-strategic-continuations.cjs'],cwd=out,text=True,capture_output=True,check=True)
assert all(digest(out/p)==sha for p,sha in before.items())
target=ROOT/'ai/runs/strong-source-strategic-teacher-probe-20261010-v1.tgz';assert not target.exists()
with tarfile.open(target,'w:gz') as f:
    for p in sorted(out.rglob('*')):
        if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc':f.add(p,arcname=str(p.relative_to(out)),recursive=False)
uploaded=HfApi().upload_file(repo_id='coyotte508/powergrid-ai-training-v1',repo_type='dataset',path_or_fileobj=target,path_in_repo=target.name)
record={'archive':target.name,'revision':uploaded.oid,'sha256':digest(target),'overlays':overlays,
    'base':{k:base[k] for k in ['archive','revision','sha256']},'unchanged_base_file_count':len(before),
    'protocol_sha256':digest(protocol_path),'qualification_eligible':False}
write(ROOT/'ai/strong/strategic-teacher-probe-source-v1.json',record)
write(ROOT/'ai/strong/strategic-teacher-probe-preflight-v1.json',{'source_revision':record['revision'],
    'source_sha256':record['sha256'],'frozen_package_passed':True,'batching':batching,'contract_tests':tests.stdout,
    'scope':'Control trajectory equality, public-information boundary, opponent routing, cap accounting, and batched inference parity. No training or strength claim.',
    'qualification_eligible':False})
print(record)
