"""Check actual learned export on every label, and parent retention on real states."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import numpy as np
import torch
from huggingface_hub import hf_hub_download
from model import policy_from_checkpoint
from discard_correction_data import arrays, load_rows

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'ai'))
from infer import Node, Model

p=argparse.ArgumentParser(__doc__)
p.add_argument('checkpoint');p.add_argument('model');p.add_argument('fixtures');p.add_argument('--data');p.add_argument('--output',required=True)
a=p.parse_args();torch.set_num_threads(1)
protocol=json.loads((ROOT/'ai/strong/discard-correction-protocol-v1.json').read_text())
assert hashlib.sha256(Path(a.fixtures).read_bytes()).hexdigest()==protocol['fixture_sha256']
cp=torch.load(a.checkpoint,map_location='cpu',weights_only=True)
net=policy_from_checkpoint(cp).eval()
new=Model(a.model);pin=json.loads((ROOT/'ai/strong/discard-training-labels-protocol-v1.json').read_text())['model']
parent=Model(hf_hub_download(protocol['repo'],pin['path'],revision=pin['revision']))
assert parent.sha256==pin['sha256']
worker=Node('strong/worker.cjs');positions=eligible=changed=0;outside_error=0.
try:
    with open(a.fixtures) as f:
        for line in f:
            fixture=json.loads(line)
            row=worker.call({**fixture['request'],'featureRevision':protocol['feature_revision']})
            assert 'error' not in row and row['moves']==fixture['legal']
            state=np.array([row['state']],np.float32);actions=np.array([row['actions']],np.float32)
            mask=np.ones(actions.shape[:2],bool)
            actual=new.session.run(None,{'state':state,'actions':actions,'mask':mask})
            original=parent.session.run(None,{'state':state[:,:1149],'actions':actions[:,:,:98],'mask':mask})
            np.testing.assert_allclose(actual[1],original[1],rtol=1e-4,atol=1e-5)
            if row['state'][-1]:
                eligible+=1;changed+=int(actual[0].argmax()!=original[0].argmax())
            else:
                np.testing.assert_allclose(actual[0],original[0],rtol=1e-4,atol=1e-5)
                assert actual[0].argmax()==original[0].argmax()
                outside_error=max(outside_error,float(np.abs(actual[0]-original[0]).max()))
            positions+=1
finally:worker.close()
assert positions==2553 and eligible==9
labels=0;label_error=0.
if a.data:
    rows=load_rows(a.data,protocol)
    for split in ['train','validation']:
        subset=[r for r in rows if r['split']==split];data=arrays(subset)
        for i in range(0,len(subset),64):
            batch={k:data[k][i:i+64] for k in ['state','actions','mask']}
            actual=new.session.run(None,batch)
            with torch.inference_mode():expected=[x.numpy() for x in net(*(torch.from_numpy(batch[k]) for k in ['state','actions','mask']))]
            for x,y in zip(actual,expected):np.testing.assert_allclose(x,y,rtol=1e-4,atol=1e-5)
            np.testing.assert_array_equal(actual[0].argmax(1),expected[0].argmax(1))
            label_error=max(label_error,float(np.abs(actual[0]-expected[0]).max()));labels+=len(batch['state'])
    assert labels==3361
report={'positions':positions,'eligible':eligible,'changed_eligible':changed,'unchanged_other_actions':positions-eligible,
    'outside_max_logit_error':outside_error,'labels_strict_parity':labels,'label_max_logit_error':label_error,
    'model_sha256':new.sha256,'checkpoint_sha256':hashlib.sha256(Path(a.checkpoint).read_bytes()).hexdigest(),
    'rtol':1e-4,'atol':1e-5,'qualification_eligible':False}
Path(a.output).write_text(json.dumps(report,indent=2)+'\n');print(report)
