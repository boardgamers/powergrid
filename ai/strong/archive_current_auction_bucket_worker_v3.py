"""One immutable metadata archive for bucket worker integration; no execution."""
import json
from pathlib import Path
import shutil

from huggingface_hub import HfApi
import collect_current_auction_retained_after_transport_failure_v2 as c
m=c.m
OUT=m.ROOT/'ai/runs/current-auction-bucket-worker-evidence-v3'
DESCRIPTOR=m.STRONG/'current-auction-bucket-worker-evidence-v3.json'
SNAPSHOT=m.STRONG/'current-auction-bucket-worker-status-v3.json'


def main():
    m.require(not OUT.exists() and not OUT.with_suffix('.tgz').exists() and not DESCRIPTOR.exists(),
        'Inspect previous archive intent/outcome; no blind retry')
    with m.exclusive(m.OUT,'cycle'):
        source,rows,records=c.original_bindings();status=m.read(SNAPSHOT)
        m.require(status['collection_state_sha256']==m.digest(c.OUT/'collection-state.json')
            and status['stop_sha256']==m.digest(m.OUT/'STOP.json'),'Snapshot changed')
        repo='coyotte508/powergrid-ai-germany-v1';api=HfApi()
        m.require(api.model_info(repo).private is True,'Evidence repo must remain private')
        m.require(not api.file_exists(repo,'archives/'+OUT.name+'.tgz'),'Inspect existing remote archive')
        names=('checkpoint_bucket_archives_v3.py','current_auction_bucket_checkpoints_v3.py',
            'current_auction_bucket_collection_v3.py','current_auction_bucket_worker_v3.py',
            'promote_bucket_evidence_v3.py','test_checkpoint_bucket_archives_v3.py',
            'test_current_auction_bucket_checkpoints_v3.py','test_current_auction_bucket_collection_v3.py',
            'test_current_auction_bucket_worker_v3.py','test_current_auction_bucket_worker_flow_v3.py',
            'probe_current_auction_bucket_integration_v3.py','preflight_current_auction_bucket_worker_v3.py',
            'current-auction-bucket-integration-probe-v3.json','current-auction-bucket-worker-preflight-v3.json',
            'checkpoint_bucket_transport_v3.py','current-auction-checkpoint-storage-evidence-v3.json')
        paths={Path(__file__),SNAPSHOT,m.SOURCE,c.REGISTRY,c.OUT/'collection-state.json',m.OUT/'STOP.json',
            m.ROOT/'ai/CURRENT-AUCTION-BUCKET-WORKER-2026-10-29.md',m.ROOT/'ai/RESUME.md'}
        paths.update(m.STRONG/name for name in names)
        pre=m.ROOT/'ai/runs/current-auction-bucket-worker-preflight-v3'
        paths.update(p for p in pre.rglob('*') if p.is_file())
        probe=m.ROOT/'ai/runs/current-auction-bucket-integration-probe-v3'
        paths.update((probe/'intent.json',probe/'promotion/intent.json',probe/'promotion/receipt.json'))
        for case in sorted(probe.glob('case-*')):
            paths.add(case/'result.json');paths.update((case/'supervisor').glob('*.json'))
            paths.update((case/'transport-ledgers').rglob('*.json'))
        for pattern in ('current-auction-bucket-*-v3-*.log','checkpoint-bucket-archives-v3-*.log',
                'current-auction-retained-post-failure-collection-v2-fourth.log',
                'current-auction-retained-post-failure-collection-v2-fifth.log'):
            paths.update(m.ROOT.joinpath('ai/runs').glob(pattern))
        for item in records:
            folder=m.OUT/'jobs'/item['attempt_id']
            for name in ('launch-intent.json','launch.json','terminal.json','review.json'):
                if (folder/name).is_file():paths.add(folder/name)
            checks=sorted((folder/'checks').glob('*.json'))
            if checks:paths.add(checks[-1])
        OUT.mkdir()
        for path in sorted(paths):
            m.require(path.is_file() and not path.is_symlink(),'Unsafe metadata source')
            target=OUT/path.relative_to(m.ROOT);target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(path,target);m.require(m.digest(path)==m.digest(target),'Metadata changed during archive')
        m.save(OUT/'manifest.json',{str(p.relative_to(OUT)):m.digest(p) for p in sorted(OUT.rglob('*')) if p.is_file()})
        m.durable(OUT.with_suffix('.intent.json'),{'created_at':m.now(),'manifest_sha256':m.digest(OUT/'manifest.json'),
            'automatic_retries':False,'references_existing_raw_archives':True,'new_jobs':0})
        evidence=m.first.upload_evidence(OUT)
        m.save(DESCRIPTOR,{'archive':evidence,'snapshot_sha256':m.digest(SNAPSHOT),
            'worker_sha256':m.digest(m.STRONG/'current_auction_bucket_worker_v3.py'),
            'collector_sha256':m.digest(m.STRONG/'current_auction_bucket_collection_v3.py'),
            'preflight_sha256':m.digest(m.STRONG/'current-auction-bucket-worker-preflight-v3.json'),
            'integration_probe_sha256':m.digest(m.STRONG/'current-auction-bucket-integration-probe-v3.json'),
            'stop_sha256':m.digest(m.OUT/'STOP.json'),'new_jobs':0,'new_games':0,'new_inference':0,
            'production_execution_admitted':False,'qualified':False,'reserved_final_seeds_used':False})
        print(json.dumps({'archive':evidence,'new_jobs':0}),flush=True)


if __name__=='__main__':main()
