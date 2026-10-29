"""Validate every prepared teacher root against the current frozen runtime."""
from collections import Counter
import json
import sys
import time
from prepare_auction_discount_teacher_v2 import ROOT, OUT, PROTOCOL, digest, read, save, object_hash
from current_auction_resource_job_v2 import tree


def main():
    output=ROOT/'ai/strong/auction-discount-teacher-preflight-v2.json'
    assert not output.exists(), 'Inspect prior preflight'
    p=read(PROTOCOL);bundle=OUT/'bundle';pins=tree(bundle,'manifest.json',digest(bundle/'manifest.json'))
    assert digest(PROTOCOL)==pins['protocol.json']
    artifact=ROOT/'ai/runs/current-auction-grid-prepared-v1/source/artifact'
    assert digest(artifact/'manifest.json')==p['artifact_manifest_sha256']
    sys.path.insert(0,str(artifact/'ai/strong'))
    import public_policy_runtime_v1 as runtime
    instance=runtime.load_artifact(artifact,p['teacher_policy']);start=time.monotonic()
    roots={};splits=Counter();shards=[];rollouts=0
    try:
        for entry in p['shards']:
            rows=read(bundle/entry['file']);assert digest(bundle/entry['file'])==entry['sha256']
            assert len(rows)==entry['roots']
            for root in rows:
                assert root['rootId'] not in roots;roots[root['rootId']]=root['public_root_sha256']
                assert object_hash(root['request'])==root['public_root_sha256']
                runtime.current_engine_scope_v1.validate_request_scope(root['request'])
                prepared=instance.prepare(root['request'])
                assert prepared['moves']==root['legal'] and not prepared['lossFilter']['forbidden']
                assert {m['name'] for m in prepared['moves']} <= {'ChoosePowerPlant','Pass'}
                assert set(prepared['options']) <= set(range(len(root['legal'])))
                baseline=instance.policy.base.choose(root['request'])['index']
                assert 0<=baseline<len(root['legal']) and len(root['legal'])>=2
                assert root['split']==('validation' if root['deal'] in (0,4,8,12) else 'train')
                splits[root['split']]+=1;rollouts+=len(root['legal'])*64
            shards.append({'shard':entry['shard'],'roots':len(rows),'sha256':entry['sha256']})
            print(json.dumps(shards[-1]),flush=True)
        assert len(roots)==len(set(roots.values()))==p['roots'] and dict(splits)==p['splits']
        assert rollouts==p['planned_rollouts']
        save(output,{'complete':True,'roots':len(roots),'splits':dict(splits),'shards':shards,
            'protocol_sha256':digest(PROTOCOL),'manifest_sha256':digest(bundle/'manifest.json'),
            'worker_sha256':digest(bundle/'run_auction_discount_teacher_v2.py'),
            'identity':instance.identity,'seconds':time.monotonic()-start,
            'policy_forwards':len(roots),'new_rollouts':0,'new_gradient_updates':0,
            'qualified':False,'reserved_final_seeds_used':False})
    finally:instance.close()


if __name__=='__main__':main()
