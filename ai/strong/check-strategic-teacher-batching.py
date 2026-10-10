"""Confirm serial/batched frozen-model decisions on all saved serving requests."""
import argparse
from pathlib import Path
import json
import hashlib
from strategic_teacher import ROOT, Node, predict_batch, REVISION
from strategic_collection import get_model, read, PROTOCOL

p=argparse.ArgumentParser(__doc__);p.add_argument('--fixtures', type=Path, required=True)
p.add_argument('--output', type=Path, required=True);a=p.parse_args()
assert hashlib.sha256(a.fixtures.read_bytes()).hexdigest() == 'f1c97bf909e38e5df372a89d169d80f5a6f24c00dccefacd60b10b767f1fcfa0'
model=get_model(read(PROTOCOL));node=Node('strong/worker.cjs');rows=[];expected=[]
try:
    for line in a.fixtures.read_text().splitlines():
        fixture=json.loads(line)
        row=node.call({**fixture['request'], 'featureRevision':REVISION})
        rows.append(row);expected.append(model.predict(row['state'],row['actions'])[0])
finally:node.close()
assert len(rows)==2553
for batch in [1,17,64]:assert predict_batch(model,rows,batch)==expected
assert predict_batch(model,list(reversed(rows)))==list(reversed(expected))
result={'positions':len(rows),'feature_revision':REVISION,'model_sha256':model.sha256,
    'batch_sizes':[1,17,64],'reverse_order_passed':True,'all_actions_match_serial':True,
    'scope':'Inference batching parity only; no gradients or strength claim.'}
a.output.write_text(json.dumps(result,indent=2)+'\n');print(result)
