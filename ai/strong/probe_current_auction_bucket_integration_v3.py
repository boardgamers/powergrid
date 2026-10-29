"""Exercise real retention/download/promotion on four already-audited raw jobs.

No evaluator execution, new games, inference, HF jobs or production admission.
Each source is chosen by canonical filename, without reading game outcomes.
"""
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
from pathlib import Path
import time

from huggingface_hub import HfApi
import current_auction_bucket_checkpoints_v3 as retention
import checkpoint_bucket_archives_v3 as archives
import promote_bucket_evidence_v3 as promotion
import manage_current_auction_remaining_v2 as m

OUT = m.ROOT/'ai/runs/current-auction-bucket-integration-probe-v3'
REPORT = m.STRONG/'current-auction-bucket-integration-probe-v3.json'


def main():
    m.require(not OUT.exists() and not REPORT.exists(), 'Inspect original integration probe; never rerun')
    original, rows = m.plan(); by_name = {r['name']:r for r in rows}
    source = m.source_checked()
    reviewed = []
    for folder in sorted((m.OUT/'jobs').iterdir()):
        if (folder/'review.json').exists():
            guard=m.read(folder/'launch.json');name=guard['original_name']
            report=m.result_checked(folder,source,by_name[name]);reviewed.append((folder,by_name[name],report))
    m.require(len(reviewed)>=4,'Need four independently audited existing originals')
    chosen = reviewed[:4]
    OUT.mkdir();start=time.monotonic()
    plan={'created_at':m.now(),'selection':'first four canonical attempt directories with existing independent reviews; no outcomes read',
        'source_descriptor_sha256':m.digest(m.SOURCE),'new_games':0,'new_jobs':0,'new_inference':0,
        'source_reports':[{'name':row['name'],'job_id':report['job_id'],'games':report['games'],
            'review_sha256':m.digest(folder/'review.json'),'envelope_evidence':report['envelope_evidence']}
            for folder,row,report in chosen],
        'code_sha256':{Path(module.__file__).name:m.digest(module.__file__) for module in (retention,archives,promotion)},
        'probe_sha256':m.digest(__file__),'production_execution_admitted':False}
    m.save(OUT/'intent.json',plan)
    def one(index,item):
        folder,row,report=item;target=OUT/f'case-{index:02d}';target.mkdir()
        context={'attempt_id':f'pg-bucket-integration-proof-v3-{index:02d}',
            'decision_sha256':m.digest(OUT/'intent.json'),'source_descriptor_sha256':m.worker.base.SOURCE_SHA,
            'original_row_sha256':m.worker.base.object_hash(row),'original_row':row}
        api=HfApi()
        keeper=retention.Checkpoints(target/'supervisor',context,
            lambda directory:archives.upload_directory(directory,target/'transport-ledgers',api))
        evaluation=folder/'artifacts/raw/job/evaluation'
        receipt=keeper.capture(evaluation,full_recheck=True)
        m.require(receipt is not None and len(receipt['episodes'])==report['games'],'Original complete pair coverage differs')
        m.require(keeper.capture(evaluation,full_recheck=True) is None,'Previously retained original was unexpectedly uploaded again')
        name=next((target/'supervisor').glob('*.receipt.json')).name.removesuffix('.receipt.json')
        downloaded=archives.download_archive(receipt['evidence'],name,target/'downloaded'/name,api)
        metadata=m.read(downloaded/'checkpoint.json')
        m.require(metadata['context']==context and metadata['episodes']==receipt['episodes'],'Collected context/coverage differs')
        for hashes in metadata['pair_hashes'].values():
            for filename,sha in hashes.items():
                m.require(m.digest(downloaded/filename)==sha==m.digest(evaluation/filename),'Collected game bytes differ')
        result={'name':row['name'],'source_job_id':report['job_id'],'source_review_sha256':m.digest(folder/'review.json'),
            'existing_games':len(receipt['episodes']),'bucket_evidence':receipt['evidence'],
            'downloaded_directory':str(downloaded.relative_to(m.ROOT)), 'source_unchanged':True,
            'new_games':0,'new_jobs':0,'raw_audit_repeated':False,'game_strength_evidence_added':False}
        m.save(target/'result.json',result)
        return result
    results=[]
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures=[pool.submit(one,i,item) for i,item in enumerate(chosen)]
        for future in as_completed(futures):
            result=future.result();results.append(result)
            print(json.dumps({'verified_existing_job':result['name'],'existing_games':result['existing_games'],
                'archive_bytes':result['bucket_evidence']['bytes']}),flush=True)
    results.sort(key=lambda r:r['downloaded_directory'])
    selected=results[0]
    # This is a storage proof, not a fabricated completed v3 execution. The
    # archived checkpoint retains its explicit probe context and original hashes.
    promoted=promotion.promote(m.ROOT/selected['downloaded_directory'],selected['bucket_evidence'],OUT/'promotion',HfApi())
    report={**plan,'passed':True,'finished_at':m.now(),'seconds':time.monotonic()-start,'results':results,
        'distinct_originals':len(results),'existing_games_replayed_as_files':sum(r['existing_games'] for r in results),
        'archive_sizes_bytes':[r['bucket_evidence']['bytes'] for r in results],'promotion':promoted,
        'raw_audit_repeated':False,'game_strength_evidence_added':False,'live_game_child_tested':False,
        'collector_envelope_audit_tested':'separate synthetic fault-injection suite; this probe checks retained raw-pair transport',
        'worker_admitted':False,'qualified':False,'reserved_final_seeds_used':False}
    m.save(REPORT,report)
    print(json.dumps({k:report[k] for k in ('passed','distinct_originals','existing_games_replayed_as_files',
        'archive_sizes_bytes','seconds','new_jobs','new_games')}),flush=True)


if __name__=='__main__':main()
