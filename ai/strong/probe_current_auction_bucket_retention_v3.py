"""Two private bucket transfers of an already archived checkpoint; no game/job.

This demonstrates transport and acknowledgement-loss reconciliation only. It
does not admit a new supervisor, concurrency level, retries or replacement runs.
"""
import json
from pathlib import Path
import re
import time

from huggingface_hub import HfApi, hf_hub_download
import manage_current_auction_remaining_v2 as m

BUCKET='coyotte508/powergrid-ai-checkpoints'
OUT=m.ROOT/'ai/runs/current-auction-bucket-retention-probe-v3'
REPORT=m.STRONG/'current-auction-bucket-retention-probe-v3.json'


class SimulatedAcknowledgementLoss(Exception): pass


def main():
    m.require(not OUT.exists() and not REPORT.exists(),'Inspect previous bucket probe intent/outcome')
    m.require(m.digest(m.first.RESULT)==m.FIRST_RESULT_SHA,'Completed original recovery changed')
    original=m.read(m.first.RESULT)['checkpoint_archives'][0]['evidence']
    archive=Path(hf_hub_download(original['repo'],original['archive_path'],revision=original['revision']))
    m.require(m.digest(archive)==original['archive_sha256'],'Original immutable checkpoint differs')
    api=HfApi();existing={b.id:b for b in api.list_buckets(namespace='coyotte508',search='powergrid')}
    OUT.mkdir();started=time.monotonic()
    m.durable(OUT/'intent.json',{'bucket':BUCKET,'private':True,'source_evidence':original,
        'planned_uploads':2,'automatic_retries':False,'new_jobs':0,'new_games':0,'probe_only':True})
    if BUCKET not in existing:
        m.durable(OUT/'bucket-create-intent.json',{'bucket':BUCKET,'private':True,'automatic_retries':False})
        created=api.create_bucket(BUCKET,private=True,exist_ok=False)
        m.require(created.bucket_id==BUCKET,'Bucket creation returned another identity')
        m.durable(OUT/'bucket-create-receipt.json',{'bucket':created.bucket_id,'private':True})
    info=api.bucket_info(BUCKET);m.require(info.private is True,'Checkpoint bucket must be private')
    results=[]
    for mode in ('normal','simulated-acknowledgement-loss'):
        remote=f'probes/current-auction-retention-v3/{mode}/{original["archive_sha256"]}.tgz'
        m.require(not list(api.get_bucket_paths_info(BUCKET,[remote])),'Inspect existing probe object; do not overwrite')
        m.durable(OUT/(mode+'.upload-intent.json'),{'bucket':BUCKET,'path':remote,
            'archive_sha256':original['archive_sha256'],'bytes':archive.stat().st_size,'automatic_retries':False})
        upload_start=time.monotonic();ack_loss=False
        try:
            api.batch_bucket_files(BUCKET,add=[(archive,remote)])
            if mode=='simulated-acknowledgement-loss':raise SimulatedAcknowledgementLoss()
        except SimulatedAcknowledgementLoss:
            # Deliberate local fault after the real upload returned. Inspect the
            # original path and verify bytes; never make another upload call.
            ack_loss=True
        metadata=list(api.get_bucket_paths_info(BUCKET,[remote]))
        m.require(len(metadata)==1 and metadata[0].path==remote and metadata[0].size==archive.stat().st_size,
            'Original bucket object missing/changed')
        obj=metadata[0];m.require(re.fullmatch('[a-f0-9]{64}',obj.xet_hash),'Missing content identity')
        downloaded=OUT/(mode+'.tgz')
        api.download_bucket_files(BUCKET,[(obj,downloaded)],raise_on_missing_files=True)
        m.require(m.digest(downloaded)==original['archive_sha256'],'Bucket download differs from immutable original archive')
        after=list(api.get_bucket_paths_info(BUCKET,[remote]))
        m.require(len(after)==1 and after[0].xet_hash==obj.xet_hash and after[0].size==obj.size,'Object changed during verification')
        receipt={'bucket':BUCKET,'path':remote,'xet_hash':obj.xet_hash,'archive_sha256':original['archive_sha256'],
            'manifest_sha256':original['manifest_sha256'],'bytes':obj.size,'download_verified':True,
            'private':True,'seconds':time.monotonic()-upload_start,'simulated_acknowledgement_loss':ack_loss,
            'upload_calls':1,'reuploads':0,'server_versioning':False,'content_addressed_path':True}
        m.durable(OUT/(mode+'.receipt.json'),receipt);results.append(receipt)
        print(json.dumps({'mode':mode,'bytes':obj.size,'download_verified':True,'reuploads':0}),flush=True)
    m.require(api.bucket_info(BUCKET).private is True,'Bucket visibility changed')
    report={'passed':True,'created_at':m.now(),'bucket':BUCKET,'private':True,'source_evidence':original,
        'source_first_recovery_sha256':m.FIRST_RESULT_SHA,'script_sha256':m.digest(__file__),
        'transfers':results,'seconds':time.monotonic()-started,'new_jobs':0,'new_games':0,'new_inference':0,
        'simulated_acknowledgement_losses':1,'actual_network_failures_exercised':0,'concurrency_tested':1,
        'new_supervisor_admitted':False,'replacement_runs_admitted':False,'qualified':False,'reserved_final_seeds_used':False,
        'limitation':'Buckets are mutable and non-versioned; future use requires pinned object hashes, independent download verification, explicit missing/corrupt rejection, and durable final versioned archives.'}
    m.save(REPORT,report);print(json.dumps({'passed':True,'bucket':BUCKET,'transfers':2,'new_jobs':0,'new_games':0}),flush=True)


if __name__=='__main__':main()
