"""Actual offset/twin parity with already verified unsliced training games."""
from collections import Counter
import gzip
import json
from pathlib import Path
from strategic_collection_slices import ROOT, run, verify_games, read, write, PROTOCOL

out=ROOT/'ai/runs/strategic-collection-slices-preflight-v1';out.mkdir(exist_ok=False)
run(2,'economic',out/'slice',8,9)
full=ROOT/'ai/runs/strategic-training-collection-verified-v1/2p-economic'
expected=[r for r in read(full/'games.json') if 8*8<=r['episode']<9*8]
actual=read(out/'slice/games.json');assert len(expected)==len(actual)==8
def comparable(r):return {k:v for k,v in r.items() if k!='env'}
assert {r['episode']:comparable(r) for r in actual}=={r['episode']:comparable(r) for r in expected}
def roots(path,selected=False):
    result={}
    with gzip.open(path,'rt') as f:
        for line in f:
            r=json.loads(line)
            if selected and r['deal']!=8:continue
            r.pop('rootIndex');result[r['rootId']]=r
    return result
a=roots(out/'slice/roots.jsonl.gz');b=roots(full/'roots.jsonl.gz',True)
assert len(a)>0 and a==b
p=read(PROTOCOL)
for faulty,start,end in [(actual[:-1],8,9),(actual+[actual[0]],8,9),(actual,7,8),(actual,8,10)]:
    try:verify_games(faulty,p,2,'economic',False,start,end)
    except (AssertionError,ValueError):pass
    else:raise AssertionError('Invalid slice accepted')
report={'games':len(actual),'roots':len(a),'deal_start':8,'deal_end':9,
    'exact_game_rows_match_unsliced':True,'exact_public_roots_and_proposals_match_unsliced':True,
    'ignored_fields':['terminal worker-local env index','root file order index'],
    'twin_controls_match':read(out/'slice/collection-check.json')['all_twin_controls_match'],
    'bad_ranges_and_missing_duplicate_games_rejected':True,'qualification_eligible':False,
    'scope':'Local scheduling parity only; not new training data or playing strength.'}
write(out/'check.json',report);print(report)
