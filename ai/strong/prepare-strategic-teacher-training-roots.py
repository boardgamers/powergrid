"""Freeze balanced public nomination/bid/build roots without outcome-based selection."""
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path
from strategic_collection import ROOT, read, write, digest, request_hash

def decision(r):
    names={m['name'] for m in r['legal']}
    return 'nomination' if 'ChoosePowerPlant' in names else 'bid' if 'Bid' in names else 'building'

out=ROOT/'ai/runs/strategic-teacher-training-roots-v1.jsonl.gz';assert not out.exists()
probe=read(ROOT/'ai/strong/strategic-teacher-probe-roots-v1.json')
exclude={r['rootId'] for r in probe['roots']};chosen=[];pins={};candidate_cells={}
for n in range(2,7):
    for mode in ['economic','snapshot0']:
        key=f'{n}p-{mode}';folder=ROOT/f'ai/runs/strategic-training-collection-verified-v1/{key}'
        v=read(folder/'verified.json');assert v['verified'] and not v['smoke'] and v['players']==n and v['mode']==mode
        for name,sha in v['artifacts'].items():assert Path(name).name==name and digest(folder/name)==sha
        pins[key]={k:v[k] for k in ['revision','prefix','source_revision','source_sha256','protocol_sha256','artifacts']}
        best={}
        with gzip.open(folder/'roots.jsonl.gz','rt') as f:
            for line in f:
                r=json.loads(line)
                if r['rootId'] in exclude:continue
                kind=decision(r);cell=(r['deal'],r['variant'],r['sealed'],kind)
                rank=hashlib.sha256(('strategic-teacher-training-root-selection-v1-'+r['rootId']).encode()).hexdigest()
                candidates=best.setdefault(cell,[])
                item=(rank,r['public_root_sha256'],line)
                same=next((i for i,x in enumerate(candidates) if x[1]==item[1]),None)
                if same is not None:
                    if candidates[same][0]<=rank:continue
                    candidates.pop(same)
                candidates.append(item);candidates.sort(key=lambda x:x[0]);del candidates[12:]
        expected={(d,v,s,k) for d in range(16) for v in ['original','recharged'] for s in [False,True]
            for k in ['nomination','bid','building']}
        assert set(best)==expected, (key,expected-set(best))
        for cell in sorted(best):candidate_cells[(n,mode,*cell)]=best[cell]
        print({'source':key,'candidate_cells':len(best)},flush=True)
# Validation positions are fixed first. Training chooses the next hash-ranked
# distinct state when its first candidate is identical to a validation input.
validation_hashes=set();skipped=0
for validation in [True,False]:
    for cell,candidates in sorted(candidate_cells.items()):
        if (cell[2] in [0,4,8,12])!=validation:continue
        eligible=[x for x in candidates if validation or x[1] not in validation_hashes]
        assert eligible, ('Need a larger predeclared candidate pool for public-state separation',cell)
        rank,public_hash,line=eligible[0];skipped+=next(i for i,x in enumerate(candidates) if x[0]==rank)
        r=json.loads(line);assert request_hash(r['request'])==r['public_root_sha256']
        chosen.append({**r,'decision':cell[-1],'selection_sha256':rank})
        if validation:validation_hashes.add(public_hash)
chosen.sort(key=lambda r:(r['players'],r['mode'],r['deal'],r['variant'],r['sealed'],r['decision']))
assert len(chosen)==1920 and len({r['rootId'] for r in chosen})==1920
splits=Counter(r['split'] for r in chosen);assert dict(splits)=={'validation':480,'train':1440}
deal_splits={};public_splits={}
for r in chosen:
    key=(r['players'],r['mode'],r['deal']);assert deal_splits.setdefault(key,r['split'])==r['split']
    public_splits.setdefault(r['public_root_sha256'],set()).add(r['split'])
assert all(len(s)==1 for s in public_splits.values()),'Identical public state crosses splits; revise selection before freezing'
with gzip.open(out,'wt') as f:
    for i,r in enumerate(chosen):r['teacherRootIndex']=i;f.write(json.dumps(r)+'\n')
record={'positions':len(chosen),'root_splits':dict(splits),'file':'ai/strong/fixtures/strategic-teacher-training-roots-v1.jsonl.gz',
    'local_file':str(out.relative_to(ROOT)),'sha256':digest(out),'collection_pins':pins,
    'selection':'Lowest fixed rootId hash within count/source/deal/rule/decision among12 distinct-state candidates; validation fixed first; training skips identical validation public states. No outcomes used; runtime-probe roots excluded.',
    'cross_split_collision_candidates_skipped':skipped,
    'decision_counts':dict(Counter(r['decision'] for r in chosen)),
    'scope':'Economic and frozen-self-play pilot roots; search-opponent collection remains separately active. Every count, rule and decision covered.',
    'no_whole_deal_split_leakage':True,'no_identical_public_root_crosses_splits':True,
    'qualification_eligible':False,'labels_generated':False,'trained':False}
write(ROOT/'ai/strong/strategic-teacher-training-roots-v1.json',record)
print({k:v for k,v in record.items() if k!='collection_pins'})
