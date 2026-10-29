"""Run the small all-legal nomination teacher pilot in the frozen artifact."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time


def digest(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()
def read(path):return json.loads(Path(path).read_text())
def object_hash(value):return hashlib.sha256(json.dumps(value,sort_keys=True).encode()).hexdigest()
def save(path,value):
    with Path(path).open('x') as stream:json.dump(value,stream,indent=2,allow_nan=False);stream.write('\n')


def main():
    parser=argparse.ArgumentParser(__doc__)
    parser.add_argument('--artifact',type=Path,required=True)
    parser.add_argument('--bundle',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--execute',action='store_true')
    parser.add_argument('--upload',action='store_true');args=parser.parse_args()
    artifact=args.artifact.resolve();bundle=args.bundle.resolve();out=args.output.resolve()
    assert not out.exists(),'Inspect prior teacher execution; no automatic rerun'
    protocol=read(bundle/'protocol.json');roots=read(bundle/'roots.json')
    assert digest(bundle/'roots.json')==protocol['roots']['sha256'] and len(roots)==70
    assert digest(artifact/'manifest.json')==protocol['artifact_manifest_sha256']
    assert digest(artifact/protocol['teacher_policy'])==protocol['teacher_policy_sha256']
    sys.path.insert(0,str(artifact/'ai/strong'))
    import public_policy_runtime_v1 as runtime
    from opponent_auction_policy_v1 import select_action
    assert Path(runtime.__file__).resolve().is_relative_to(artifact)
    instance=runtime.load_artifact(artifact,protocol['teacher_policy'])
    out.mkdir();start=time.monotonic();summaries=[];receipts=[]
    try:
        for index,root in enumerate(roots):
            request=root['request']
            assert object_hash(request)==root['public_root_sha256']
            runtime.current_engine_scope_v1.validate_request_scope(request)
            prepared=instance.prepare(request)
            assert prepared['moves']==root['legal']
            assert {m['name'] for m in prepared['moves']} <= {'ChoosePowerPlant','Pass'}
            assert not prepared['lossFilter']['forbidden'],'All legal nomination choices must be labelled'
            options=list(range(len(prepared['moves'])))
            baseline=instance.policy.base.choose(request)['index']
            assert baseline in options and len(options)>=2
            summary={'rootId':root['rootId'],'split':root['split'],'players':root['players'],
                'kind':root['kind'],'options':len(options),'baseline':baseline,
                'public_root_sha256':root['public_root_sha256']}
            if args.execute:
                result=instance.policy.probe.run(request,options,mode=protocol['pilot']['mode'],
                    samples=protocol['pilot']['worlds'],max_steps=protocol['pilot']['max_steps'])
                assert result['usable'] and result['caps']==0,'Incomplete teacher continuation cannot be used'
                exact=select_action([result],options,baseline,request['player'],
                    modes=['neural_population'],minimum_advantage='1/8')
                assert exact['fallbackReason'] is None
                folder=out/f'pg-discount-teacher-pilot-v1-root-{index:03d}';folder.mkdir()
                save(folder/'root.json',root)
                save(folder/'result.json',{'identity':instance.identity,'protocol_sha256':digest(bundle/'protocol.json'),
                    'baseline':baseline,'continuations':result,'exact_summary':exact,'training_ready':False})
                save(folder/'manifest.json',{p.name:digest(p) for p in folder.iterdir()})
                summary.update(rollouts=len(result['rows']),seconds=result['seconds'],
                               neural_decisions=result['inference_decisions']['neural'])
                if args.upload:
                    sys.path.insert(0,str(bundle/'transport'))
                    from checkpoint_bucket_archives_v3 import upload_directory
                    from huggingface_hub import HfApi
                    receipt=upload_directory(folder,out/'transport-ledgers',HfApi())
                    receipts.append(receipt)
                    print(json.dumps({'rootId':root['rootId'],'bucket_evidence':receipt}),flush=True)
            summaries.append(summary)
            save(out/f'progress-{index:03d}.json',summary)
        assert sum(r['split']=='train' for r in summaries)==36
        report={'complete':True,'executed':args.execute,'roots':len(roots),'identity':instance.identity,
            'protocol_sha256':digest(bundle/'protocol.json'),'summaries':summaries,'receipts':receipts,
            'seconds':time.monotonic()-start,'new_gradient_updates':0,'pilot_targets_training_ready':False,
            'qualified':False,'reserved_final_seeds_used':False}
        save(out/'report.json',report)
        print(json.dumps({'complete':True,'executed':args.execute,'roots':len(roots),
            'rollouts':sum(r.get('rollouts',0) for r in summaries),'seconds':report['seconds']}),flush=True)
    finally:instance.close()


if __name__=='__main__':main()
