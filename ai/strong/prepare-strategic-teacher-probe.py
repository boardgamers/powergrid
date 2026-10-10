"""Freeze ten validation-only public roots for continuation runtime probes."""
import gzip
import hashlib
import json
from pathlib import Path
from strategic_collection import ROOT, read, write, digest, request_hash

out=ROOT/'ai/strong/fixtures/strategic-teacher-probe-v1.jsonl'
assert not out.exists(), 'Frozen selection exists; do not silently replace it'
selected=[];pins={}
for n in range(2,7):
    folder=ROOT/f'ai/runs/strategic-training-collection-verified-v1/{n}p-economic'
    verified=read(folder/'verified.json')
    assert verified['verified'] and not verified['smoke'] and verified['players']==n
    for name,sha in verified['artifacts'].items():assert digest(folder/name)==sha
    pins[str(n)]={k:verified[k] for k in ['revision','prefix','source_revision','source_sha256','protocol_sha256','artifacts']}
    best={}
    with gzip.open(folder/'roots.jsonl.gz','rt') as f:
        for line in f:
            r=json.loads(line)
            if r['split']!='validation':continue
            phase=r['phase'];key=hashlib.sha256(('strategic-teacher-runtime-selection-v1-'+r['rootId']).encode()).hexdigest()
            if phase not in best or key<best[phase][0]:best[phase]=(key,r)
    assert set(best)=={'auction','building'}
    for phase in ['auction','building']:
        key,r=best[phase];assert request_hash(r['request'])==r['public_root_sha256']
        selected.append({**r,'probe_selection_sha256':key})
out.parent.mkdir(exist_ok=True)
out.write_text(''.join(json.dumps(r)+'\n' for r in selected))
record={'positions':len(selected),'file':str(out.relative_to(ROOT)),'sha256':digest(out),
    'selection':'Lowest fixed hash of rootId per count/phase among verified economic validation roots; no outcomes used.',
    'scope':'Ten runtime probes only; not representative reliability, training or playing-strength evidence.',
    'roots':[{k:r[k] for k in ['rootId','players','phase','variant','sealed','round','split','public_root_sha256']} for r in selected],
    'collection_pins':pins,'qualification_eligible':False}
write(ROOT/'ai/strong/strategic-teacher-probe-roots-v1.json',record);print(record['roots'])
