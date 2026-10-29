"""One immutable shard of all-legal nomination continuations. No gradients."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time


def digest(path):
    with Path(path).open('rb') as stream: return hashlib.file_digest(stream,'sha256').hexdigest()
def read(path): return json.loads(Path(path).read_text())
def save(path,value):
    with Path(path).open('x') as stream: json.dump(value,stream,indent=2,allow_nan=False);stream.write('\n')
def object_hash(value): return hashlib.sha256(json.dumps(value,sort_keys=True).encode()).hexdigest()


def main():
    parser=argparse.ArgumentParser(__doc__)
    for name in ('artifact','bundle','output'): parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--shard',type=int,required=True)
    parser.add_argument('--execute',action='store_true');parser.add_argument('--upload',action='store_true')
    args=parser.parse_args();artifact=args.artifact.resolve();bundle=args.bundle.resolve();out=args.output.resolve()
    assert not out.exists(), 'Inspect prior shard; no automatic replay'
    assert not args.upload or args.execute
    protocol=read(bundle/'protocol.json');entry=protocol['shards'][args.shard]
    assert entry['shard']==args.shard and digest(bundle/entry['file'])==entry['sha256']
    roots=read(bundle/entry['file']);assert len(roots)==entry['roots']
    assert digest(artifact/'manifest.json')==protocol['artifact_manifest_sha256']
    assert digest(artifact/protocol['teacher_policy'])==protocol['teacher_policy_sha256']
    assert protocol['worlds']==64 and protocol['workers']==4 and protocol['threads']==1
    sys.path.insert(0,str(artifact/'ai/strong'))
    import public_policy_runtime_v1 as runtime
    from opponent_auction_policy_v1 import select_action
    assert Path(runtime.__file__).resolve().is_relative_to(artifact)
    instance=runtime.load_artifact(artifact,protocol['teacher_policy']);out.mkdir();start=time.monotonic()
    summaries=[]
    try:
        for index,root in enumerate(roots):
            request=root['request'];assert object_hash(request)==root['public_root_sha256']
            runtime.current_engine_scope_v1.validate_request_scope(request)
            prepared=instance.prepare(request)
            assert prepared['moves']==root['legal'] and not prepared['lossFilter']['forbidden']
            assert {m['name'] for m in prepared['moves']} <= {'ChoosePowerPlant','Pass'}
            baseline=instance.policy.base.choose(request)['index'];options=list(range(len(prepared['moves'])))
            assert baseline in options and len(options)>=2
            summary={'rootId':root['rootId'],'split':root['split'],'players':root['players'],
                     'options':len(options),'baseline':baseline,'public_root_sha256':root['public_root_sha256']}
            if args.execute:
                result=instance.policy.probe.run(request,options,mode=protocol['mode'],
                    samples=protocol['worlds'],max_steps=protocol['max_steps'])
                folder=out/f"{entry['name']}-root-{index:03d}";folder.mkdir()
                save(folder/'root.json',root)
                record={'identity':instance.identity,'protocol_sha256':digest(bundle/'protocol.json'),
                    'shard':args.shard,'baseline':baseline,'current_shortlist':prepared['options'],
                    'continuations':result,'training_ready':False}
                # Preserve capped or inconsistent raw outcomes before propagating failure.
                error=None
                try:
                    assert result['usable'] and result['caps']==0, 'Incomplete continuation'
                    record['exact_summary']=select_action([result],options,baseline,request['player'],
                        modes=['neural_population'],minimum_advantage='1/8')
                    assert record['exact_summary']['fallbackReason'] is None
                except Exception as exc:
                    error=exc;record['verification_error']=type(exc).__name__+': '+str(exc)
                save(folder/'result.json',record)
                save(folder/'manifest.json',{p.name:digest(p) for p in folder.iterdir()})
                summary.update(rollouts=len(result['rows']),seconds=result['seconds'],caps=result['caps'])
                if args.upload:
                    sys.path.insert(0,str(bundle/'transport'))
                    from checkpoint_bucket_archives_v3 import upload_directory
                    from huggingface_hub import HfApi
                    receipt=upload_directory(folder,out/'transport-ledgers',HfApi())
                    print(json.dumps({'rootId':root['rootId'],'bucket_evidence':receipt}),flush=True)
                if error is not None: raise error
            summaries.append(summary);save(out/f'progress-{index:03d}.json',summary)
        report={'complete':True,'executed':args.execute,'shard':args.shard,'roots':len(roots),
                'identity':instance.identity,'protocol_sha256':digest(bundle/'protocol.json'),
                'summaries':summaries,'seconds':time.monotonic()-start,'new_gradient_updates':0,
                'targets_independently_audited':False,'qualified':False,'reserved_final_seeds_used':False}
        save(out/'report.json',report)
        print(json.dumps({'complete':True,'executed':args.execute,'shard':args.shard,'roots':len(roots),
            'rollouts':sum(r.get('rollouts',0) for r in summaries),'seconds':report['seconds']}),flush=True)
    finally: instance.close()


if __name__ == '__main__': main()
