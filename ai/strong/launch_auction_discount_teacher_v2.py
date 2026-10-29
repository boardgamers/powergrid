"""Publish checked source or launch a bounded part of the fixed 60-shard plan."""
import argparse
from datetime import datetime,timezone
import json
from huggingface_hub import HfApi,get_token,hf_hub_download
from huggingface_hub.utils import get_session,hf_raise_for_status
from checkpoint_bucket_archives_v3 import archive_directory
from prepare_auction_discount_teacher_v2 import ROOT, OUT, PROTOCOL, digest, read, save
from launch_auction_discount_teacher_v1 import bootstrap as pilot_bootstrap

SOURCE=ROOT/'ai/strong/auction-discount-teacher-source-v2.json'
LAUNCH=ROOT/'ai/strong/auction-discount-teacher-launch-v2.json'
REPO='coyotte508/powergrid-ai-training-v1'


def bootstrap():
    prefix=pilot_bootstrap().split('python -u -B /workspace/discount-teacher/')[0]
    return prefix+'python -u -B /workspace/discount-teacher/run_auction_discount_teacher_v2.py --artifact /workspace/source/artifact --bundle /workspace/discount-teacher --output /workspace/teacher-output --shard "$TEACHER_SHARD" --execute --upload\n'


def checked_inputs():
    p=read(PROTOCOL);preflight=read(ROOT/'ai/strong/auction-discount-teacher-preflight-v2.json')
    assert preflight['complete'] and preflight['roots']==5770 and preflight['new_rollouts']==0
    assert digest(PROTOCOL)==preflight['protocol_sha256']==digest(OUT/'bundle/protocol.json')
    assert digest(OUT/'bundle/manifest.json')==preflight['manifest_sha256']
    assert digest(OUT/'bundle/run_auction_discount_teacher_v2.py')==preflight['worker_sha256']==digest(ROOT/'ai/strong/run_auction_discount_teacher_v2.py')
    return p,preflight


def publish():
    assert not SOURCE.exists() and not (OUT/'upload-intent.json').exists(), 'Inspect previous source upload'
    p,preflight=checked_inputs();api=HfApi();assert api.dataset_info(REPO).private
    remote='strong-source-auction-discount-teacher-v2.tgz'
    assert not api.file_exists(REPO,remote,repo_type='dataset'), 'Inspect previous remote source'
    archive=archive_directory(OUT/'bundle')
    save(OUT/'upload-intent.json',{'archive':remote,'sha256':digest(archive)})
    commit=api.upload_file(repo_id=REPO,repo_type='dataset',path_or_fileobj=archive,path_in_repo=remote)
    save(OUT/'upload-commit.json',{'revision':commit.oid,'archive':remote})
    assert digest(hf_hub_download(REPO,remote,repo_type='dataset',revision=commit.oid))==digest(archive)
    save(SOURCE,{'repo':REPO,'revision':commit.oid,'archive':remote,'sha256':digest(archive),
        'manifest_sha256':digest(OUT/'bundle/manifest.json'),'protocol_sha256':digest(PROTOCOL),
        'preflight_sha256':digest(ROOT/'ai/strong/auction-discount-teacher-preflight-v2.json'),
        'remote_archive_verified':True})
    print(json.dumps({'published':True,'revision':commit.oid,'bytes':archive.stat().st_size}),flush=True)


def launch(limit):
    assert 1<=limit<=60
    p,_=checked_inputs();source=read(SOURCE);assert source['protocol_sha256']==digest(PROTOCOL)
    directory=OUT/'launches';directory.mkdir(exist_ok=True);api=HfApi();submitted=0
    for row in p['shards']:
        receipt=directory/f"{row['shard']:02d}.json";intent=directory/f"{row['shard']:02d}.intent.json"
        if receipt.exists():
            prior=read(receipt);assert prior['shard']==row['shard'] and prior['source_sha256']==digest(SOURCE)
            checked=read(directory/f"{row['shard']:02d}.checked.json")
            assert checked['effective_configuration_verified'] and checked['job_id']==prior['job_id']
            assert checked['receipt_sha256']==digest(receipt)
            continue
        assert not intent.exists(), 'Ambiguous previous launch: inspect actual original handle before any retry'
        if row['shard'] > 0:
            pilot=read(ROOT/'ai/strong/auction-discount-teacher-initial-audit-v2.json')
            assert pilot['independently_audited'] and pilot['roots']>=3 and pilot['caps']==0
            assert pilot['protocol_sha256']==digest(PROTOCOL)
        base=p['current_source']
        env={'SOURCE_ARCHIVE':base['archive'],'SOURCE_REVISION':base['revision'],
             'SOURCE_SHA256':base['sha256'],'SOURCE_MANIFEST_SHA256':base['source_manifest_sha256'],
             'PILOT_ARCHIVE':source['archive'],'PILOT_REVISION':source['revision'],
             'PILOT_SHA256':source['sha256'],'PILOT_MANIFEST_SHA256':source['manifest_sha256'],
             'TEACHER_SHARD':str(row['shard']),'HF_HUB_DISABLE_PROGRESS_BARS':'1',
             'OMP_NUM_THREADS':'1','OPENBLAS_NUM_THREADS':'1','MKL_NUM_THREADS':'1'}
        config={'image':'python:3.11-slim-bookworm','command':['bash','-lc',bootstrap()],
            'env':env,'flavor':'cpu-upgrade','timeout':'24h',
            'labels':{'name':row['name'],'project':'powergrid-ai','stage':'auction-discount-teacher-v2'}}
        save(intent,{'created_at':datetime.now(timezone.utc).isoformat(),'config':config,
                     'source_sha256':digest(SOURCE),'shard':row['shard'],'automatic_retries':False})
        token=get_token();assert token
        job=api.run_job(**config,secrets={'HF_TOKEN':token})
        record={'shard':row['shard'],'job_id':job.id,'name':row['name'],'roots':row['roots'],
            'rollouts':row['rollouts'],'source_sha256':digest(SOURCE),
            'intent_sha256':digest(intent),'created_at':datetime.now(timezone.utc).isoformat()}
        save(receipt,record)
        response=get_session().get(f'{api.endpoint}/api/jobs/coyotte508/{job.id}',headers=api._build_hf_headers(),timeout=60)
        hf_raise_for_status(response);raw=response.json()
        assert raw['id']==job.id and raw['dockerImage']==config['image'] and raw['flavor']==config['flavor']
        assert raw['command']==config['command'] and raw['environment']==env and raw['timeout']==86400
        assert raw['labels']['name']==row['name']
        save(directory/f"{row['shard']:02d}.checked.json",{'job_id':job.id,'stage':raw['status']['stage'],
            'effective_configuration_verified':True,'receipt_sha256':digest(receipt)})
        receipts=[read(path) for path in sorted(directory.glob('[0-9][0-9].json'))]
        summary={'source':source,'protocol_sha256':digest(PROTOCOL),'jobs':receipts,
            'planned_jobs':60,'submitted_jobs':len(receipts),'roots_submitted':sum(r['roots'] for r in receipts),
            'new_gradient_updates':0,'automatic_retries':False,'qualified':False,'reserved_final_seeds_used':False}
        tmp=LAUNCH.with_suffix('.tmp');tmp.write_text(json.dumps(summary,indent=2)+'\n');tmp.replace(LAUNCH)
        print(json.dumps({'submitted':row['name'],'job_id':job.id,'stage':raw['status']['stage']}),flush=True)
        submitted+=1
        if submitted==limit:break


if __name__=='__main__':
    parser=argparse.ArgumentParser(__doc__);group=parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--publish-source',action='store_true');group.add_argument('--launch',type=int)
    args=parser.parse_args()
    if args.publish_source:publish()
    else:launch(args.launch)
