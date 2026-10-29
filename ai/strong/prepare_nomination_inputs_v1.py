"""Encode the fixed all-legal teacher inputs; no targets, gradients or games."""
from collections import Counter
import json
from pathlib import Path
import subprocess
import numpy as np
from prepare_auction_discount_teacher_v2 import ROOT,PROTOCOL,digest,read,save

OUT=ROOT/'ai/runs/nomination-discount-inputs-v1'


def main():
    assert not OUT.exists(),'Inspect prior input preparation'
    protocol=read(PROTOCOL);bundle=ROOT/'ai/runs/auction-discount-teacher-prepared-v2/bundle'
    artifact=ROOT/'ai/runs/current-auction-grid-prepared-v1/source/artifact'
    assert digest(artifact/'manifest.json')==protocol['artifact_manifest_sha256']
    worker=ROOT/'ai/strong/auction-discount-warmstart-inputs-v1.cjs'
    roots=[]
    for shard in protocol['shards']:
        assert digest(bundle/shard['file'])==shard['sha256'];roots+=read(bundle/shard['file'])
    assert len(roots)==5770
    OUT.mkdir();state=np.zeros((5770,1218),np.float32);actions=np.zeros((5770,7,103),np.float32);mask=np.zeros((5770,7),bool)
    meta=[]
    with (OUT/'encoder.log').open('x') as log:
        process=subprocess.Popen(['node',str(worker),str(artifact)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=log,text=True,cwd='/tmp')
        try:
            for start in range(0,len(roots),32):
                batch=roots[start:start+32];process.stdin.write(json.dumps(batch)+'\n');process.stdin.flush()
                encoded=json.loads(process.stdout.readline());assert len(encoded)==len(batch)
                for offset,(root,row) in enumerate(zip(batch,encoded)):
                    i=start+offset;n=len(root['legal']);assert 2<=n<=7
                    assert len(row['state'])==1218 and len(row['actions'])==n
                    state[i]=row['state'];actions[i,:n]=row['actions'];mask[i,:n]=True
                    assert any(actions[i,:n,0]>.5)
                    assert np.array_equal(actions[i,:n,0]>.5,[a['name']=='ChoosePowerPlant' for a in root['legal']])
                    meta.append({k:v for k,v in root.items() if k not in ('request','legal')})
        finally:
            process.stdin.close();assert process.wait()==0
    assert np.isfinite(state).all() and np.isfinite(actions).all()
    np.savez_compressed(OUT/'inputs.npz',state=state,actions=actions,mask=mask)
    save(OUT/'metadata.json',meta)
    report={'complete':True,'roots':len(meta),'splits':dict(Counter(r['split'] for r in meta)),
        'protocol_sha256':digest(PROTOCOL),'encoder_sha256':digest(worker),
        'extension_sha256':digest(ROOT/'ai/strong/features-v4_4.cjs'),
        'artifact_manifest_sha256':digest(artifact/'manifest.json'),
        'files':{f:digest(OUT/f) for f in ('inputs.npz','metadata.json')},'new_games':0,'new_gradients':0}
    save(OUT/'report.json',report);print(report,flush=True)


if __name__=='__main__':main()
