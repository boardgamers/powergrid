"""Independently bind saved export outputs and eventual target model proposals.

Export audit recomputes features only. Serving binding reads completed collected
receipts only; neither operation runs networks, searches, jobs or game moves.
"""
import argparse
from collections import Counter
import json
import hashlib
from pathlib import Path
import subprocess

import numpy as np
import current_engine_export_parity_v1 as p

AUDIT=p.ROOT/'ai/strong/current-engine-export-audit-v1.json'
BINDING=p.ROOT/'ai/strong/current-full-serving-export-binding-v1.json'
COLLECTED=p.ROOT/'ai/runs/current-full-serving-8840u-collected-v1'


def checked_report():
    r=p.read(p.RESULT)
    assert r['complete'] and r['positions']==2553 and r['by_player_count']==p.COUNTS
    assert r['model_sha256']==p.MODEL_SHA and r['checkpoint_sha256']==p.CHECKPOINT_SHA
    assert r['runtime_manifest_sha256']==p.RUNTIME_SHA
    assert all(p.digest(p.ROOT/n)==h for n,h in r['input_hashes'].items())
    assert p.digest(p.OUT/'receipts.jsonl')==r['receipts_sha256']
    assert p.digest(p.ARTIFACT/'manifest.json')==p.RUNTIME_SHA
    assert all(p.digest(p.ARTIFACT/n)==h for n,h in p.read(p.ARTIFACT/'manifest.json').items())
    return r


def audit_export():
    assert not AUDIT.exists(),'Inspect existing independent audit'
    r=checked_report();counts=Counter();maximum=[0.,0.]
    with (p.OUT/'independent-audit.stderr.log').open('x') as errors:
        worker=subprocess.Popen(['node',str(p.ARTIFACT/'ai/strong/population-hybrid-policy.cjs')],
            stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=errors,text=True,bufsize=1,cwd='/tmp')
        try:
            with (p.PACKAGE/'cases.jsonl').open() as cases,(p.OUT/'receipts.jsonl').open() as receipts:
                for index,line in enumerate(cases):
                    c=json.loads(line);s=json.loads(next(receipts));q=c['request']
                    assert c['index']==s['index']==index and s['players']==c['players']
                    assert s['requestId']==q['requestId'] and s['revision']==q['revision']
                    assert s['request_sha256']==p.object_hash(q) and s['legal_sha256']==p.object_hash(c['legal'])
                    assert s['model_sha256']==p.MODEL_SHA and s['checkpoint_sha256']==p.CHECKPOINT_SHA
                    worker.stdin.write(p.wire({'op':'prepare','state':q['state'],'player':q['player'],'featureRevision':'4.3-strategic-correction'})+'\n');worker.stdin.flush()
                    answer=worker.stdout.readline();assert answer
                    root=json.loads(answer);row=root['observation'];assert root['moves']==c['legal'] and row['playerOrder']==c['player_order']
                    batch={'state':np.asarray([row['state']],np.float32),'actions':np.asarray([row['actions']],np.float32)}
                    batch['mask']=np.ones(batch['actions'].shape[:2],bool)
                    tensors={k:{'shape':list(v.shape),'dtype':str(v.dtype),'sha256':hashlib.sha256(v.tobytes()).hexdigest()} for k,v in batch.items()}
                    assert tensors==s['input_tensors'],'Saved inference inputs differ from frozen runtime'
                    selected,errors=p.compare_outputs(s['native_outputs'],s['onnx_outputs'],c['players'],len(c['legal']))
                    assert selected==s['selected_index'] and s['selected_move']==c['legal'][selected] and errors==s['max_errors']
                    counts[str(c['players'])]+=1;maximum=[max(a,b) for a,b in zip(maximum,errors)]
                assert receipts.read()==''
        finally:
            worker.stdin.close();code=worker.wait(timeout=30);worker.stdout.close();assert code==0
    assert dict(counts)==p.COUNTS and maximum==[r['max_logit_error'],r['max_value_error']]
    checked_report()
    result={'complete':True,'positions':2553,'all_input_tensor_hashes_match':True,'all_native_onnx_actions_equal':True,
        'finite_values':True,'inactive_values_zero':True,'values_normalized':True,'by_player_count':dict(counts),
        'report_sha256':p.digest(p.RESULT),'receipts_sha256':r['receipts_sha256'],
        'auditor_sha256':p.digest(__file__),'runtime_manifest_sha256':p.RUNTIME_SHA,'model_sha256':p.MODEL_SHA,
        'checkpoint_sha256':p.CHECKPOINT_SHA,'new_forward_passes':0,'new_search_rollouts':0,'new_full_games':0,
        'candidate_selected':False,'qualified':False,'reserved_final_seeds_used':False}
    p.save(AUDIT,result);print(json.dumps(result),flush=True)


def bind_proposal(c,parity,served,identity):
    q=c['request'];response=served['response'];decision=response['decision']
    assert parity['index']==served['index']==c['index'] and served['players']==c['players']
    assert parity['request_sha256']==served['request_sha256']==p.object_hash(q)
    assert parity['model_sha256']==response['modelSha256']==identity['modelSha256']==p.MODEL_SHA
    assert response['requestId']==q['requestId'] and response['revision']==q['revision']
    assert response['playerOrder']==c['player_order']
    assert all(response[k]==v for k,v in identity.items())
    assert type(decision['modelProposal']) is int and decision['modelProposal']==parity['selected_index']
    assert parity['selected_move']==c['legal'][parity['selected_index']]
    # The frozen filter/search may deliberately override the native model.
    assert response['move'] in c['legal']


def bind_serving():
    assert not BINDING.exists(),'Inspect existing serving binding'
    report=checked_report();audit=p.read(AUDIT)
    assert audit['complete'] and audit['report_sha256']==p.digest(p.RESULT) and audit['receipts_sha256']==report['receipts_sha256']
    technical=p.read(p.ROOT/'ai/strong/current-full-serving-8840u-results-v1.json')
    assert technical['complete'] and technical['requests']==5106 and technical['positions_per_policy']==2553
    status=p.read(COLLECTED/'output/status.json')
    assert technical['status_sha256']==p.digest(COLLECTED/'output/status.json')
    assert status['stage']=='completed' and status['passed'] and '8840U' in status['processor']
    assert all(p.digest(COLLECTED/'output'/n)==h for n,h in status['output_hashes'].items())
    assert technical==p.read(COLLECTED/'audit.json')
    manifest=p.read(p.PACKAGE/'benchmark-manifest.json');assert technical['identities']==manifest['identities']
    assert technical['manifest_sha256']==p.digest(p.PACKAGE/'benchmark-manifest.json')
    counts=Counter()
    with (COLLECTED/'output/receipts.jsonl').open() as served:
        for arm in manifest['arms']:
            with (p.PACKAGE/'cases.jsonl').open() as cases,(p.OUT/'receipts.jsonl').open() as original:
                for line in cases:
                    c=json.loads(line);base=json.loads(next(original));target=json.loads(next(served))
                    assert target['arm']==arm
                    bind_proposal(c,base,target,manifest['identities'][arm]);counts[arm]+=1
                assert original.read()==''
        assert served.read()==''
    assert dict(counts)=={'filter':2553,'conservative_population':2553}
    result={'complete':True,'requests':5106,'per_policy':dict(counts),'all_target_model_proposals_match_native_checkpoint':True,
        'model_sha256':p.MODEL_SHA,'checkpoint_sha256':p.CHECKPOINT_SHA,'runtime_manifest_sha256':p.RUNTIME_SHA,
        'export_report_sha256':p.digest(p.RESULT),'export_audit_sha256':p.digest(AUDIT),
        'technical_report_sha256':p.digest(p.ROOT/'ai/strong/current-full-serving-8840u-results-v1.json'),
        'target_receipts_sha256':p.digest(COLLECTED/'output/receipts.jsonl'),'auditor_sha256':p.digest(__file__),
        'new_forward_passes':0,'new_search_rollouts':0,'new_full_games':0,
        'candidate_selected':False,'qualified':False,'reserved_final_seeds_used':False}
    p.save(BINDING,result);print(json.dumps(result),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(__doc__);parser.add_argument('operation',choices=['audit_export','bind_serving'])
    globals()[parser.parse_args().operation]()
