"""Reconstruct verified real games from deal slices; no new training games."""
import gzip
import importlib.util
import json
from pathlib import Path
from strategic_collection import ROOT, read, write, digest

spec=importlib.util.spec_from_file_location('merge_slices',ROOT/'ai/strong/merge-strategic-collection-slices.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
source=ROOT/'ai/runs/strategic-training-collection-verified-v1/2p-economic'
v=read(source/'verified.json')
assert v['verified'] and v['summary']['games']==128
for name,sha in v['artifacts'].items():assert digest(source/name)==sha
out=ROOT/'ai/runs/strategic-collection-merge-preflight-v1';out.mkdir(exist_ok=False)
games=read(source/'games.json')
with gzip.open(source/'roots.jsonl.gz','rt') as f:roots=list(map(json.loads,f))
pieces=[]
for start in range(0,16,4):
    folder=out/f'{start}-{start+4}';folder.mkdir()
    write(folder/'games.json',[r for r in games if start<=r['episode']//8<start+4])
    selected=[r for r in roots if start<=r['deal']<start+4]
    with gzip.open(folder/'roots.jsonl.gz','wt') as f:
        for i,r in enumerate(selected):f.write(json.dumps({**r,'rootIndex':i})+'\n')
    pieces.append({'start':start,'end':start+4,'folder':folder,'roots':len(selected)})
summary=module.assemble(pieces,2,'economic',out/'merged')
assert summary['games']==128 and summary['roots']==len(roots)
for faulty in [pieces[:-1],pieces+[pieces[0]],[{**pieces[0],'end':3},*pieces[1:]],
               [{**pieces[0],'start':-1},*pieces[1:]]]:
    try:module.check_ranges(faulty,16)
    except AssertionError:pass
    else:raise AssertionError('Invalid deal partition accepted')
# Existing artifact directories must never be overwritten by another merge.
try:module.assemble(pieces,2,'economic',out/'merged')
except FileExistsError:pass
else:raise AssertionError('Existing merged data overwritten')
report={'passed':True,'original_verified_sha256':digest(source/'verified.json'),
    'summary':summary,'gaps_overlaps_bad_ranges_rejected':True,'existing_output_preserved':True,
    'scope':'Repartition/reconstruction of existing verified128 games only; not new training data.',
    'qualification_eligible':False}
write(ROOT/'ai/strong/strategic-collection-merge-preflight-v1.json',report)
print(report)
