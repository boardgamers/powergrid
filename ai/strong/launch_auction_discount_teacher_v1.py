"""Publish and launch one fixed teacher-data pilot; no training or retries."""
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path

from huggingface_hub import HfApi,get_token,hf_hub_download
from huggingface_hub.utils import get_session,hf_raise_for_status
from checkpoint_bucket_archives_v3 import archive_directory
import manage_current_auction_resource_recovery_v2 as setup
from prepare_auction_discount_teacher_v1 import ROOT,OUT,PROTOCOL,digest,read,save

SOURCE=ROOT/'ai/strong/auction-discount-teacher-source-v1.json'
LAUNCH=ROOT/'ai/strong/auction-discount-teacher-launch-v1.json'
REPO='coyotte508/powergrid-ai-training-v1'
NAME='pg-discount-teacher-pilot-v1'


def bootstrap():
    prefix=setup.bootstrap().split("python -B - <<'RECOVERY_BUNDLE'")[0]
    return prefix+r'''python -B - <<'PILOT'
import hashlib,json,os,tarfile
from pathlib import Path
from huggingface_hub import hf_hub_download
file=hf_hub_download('coyotte508/powergrid-ai-training-v1',os.environ['PILOT_ARCHIVE'],repo_type='dataset',revision=os.environ['PILOT_REVISION'])
assert hashlib.sha256(Path(file).read_bytes()).hexdigest()==os.environ['PILOT_SHA256']
root=Path('/workspace/discount-teacher');assert not root.exists()
with tarfile.open(file) as bundle:
    members=bundle.getmembers();names=[m.name for m in members]
    assert len(names)==len(set(names)) and all(m.isfile() and not Path(m.name).is_absolute() and '..' not in Path(m.name).parts for m in members)
    manifest=bundle.extractfile('manifest.json').read()
    assert hashlib.sha256(manifest).hexdigest()==os.environ['PILOT_MANIFEST_SHA256']
    pins=json.loads(manifest);assert set(names)==set(pins)|{'manifest.json'}
    assert all(hashlib.sha256(bundle.extractfile(name).read()).hexdigest()==sha for name,sha in pins.items())
    root.mkdir();bundle.extractall(root,filter='data')
PILOT
python -u -B /workspace/discount-teacher/run_auction_discount_teacher_v1.py --artifact /workspace/source/artifact --bundle /workspace/discount-teacher --output /workspace/pg-discount-teacher-pilot-v1 --execute --upload
'''


def main():
    bundle=OUT/'bundle';intent=OUT/'launch-intent.json';upload_intent=OUT/'upload-intent.json'
    assert not SOURCE.exists() and not LAUNCH.exists() and not intent.exists() and not upload_intent.exists(), 'Inspect prior upload/submission before retry'
    p=read(PROTOCOL);preflight=read(ROOT/'ai/runs/auction-discount-teacher-preflight-v1/report.json')
    assert preflight['complete'] and preflight['executed'] is False and preflight['roots']==70
    assert preflight['protocol_sha256']==digest(PROTOCOL)==digest(bundle/'protocol.json')
    assert digest(bundle/'run_auction_discount_teacher_v1.py')==digest(ROOT/'ai/strong/run_auction_discount_teacher_v1.py')
    assert p['pilot']=={'worlds':4,'workers':4,'threads':1,'max_steps':2400,'mode':'neural_population'}
    assert preflight['identity']['settings']['workers']==4 and preflight['identity']['settings']['threads']==1
    api=HfApi();assert api.dataset_info(REPO).private
    remote='strong-source-auction-discount-teacher-pilot-v1.tgz'
    assert not api.file_exists(REPO,remote,repo_type='dataset'), 'Inspect prior remote source'
    archive=archive_directory(bundle)
    save(upload_intent,{'archive':remote,'sha256':digest(archive),'manifest_sha256':digest(bundle/'manifest.json')})
    commit=api.upload_file(repo_id=REPO,repo_type='dataset',path_or_fileobj=archive,path_in_repo=remote)
    save(OUT/'upload-commit.json',{'revision':commit.oid,'archive':remote})
    assert digest(hf_hub_download(REPO,remote,repo_type='dataset',revision=commit.oid))==digest(archive)
    source={'repo':REPO,'revision':commit.oid,'archive':remote,'sha256':digest(archive),
        'manifest_sha256':digest(bundle/'manifest.json'),'remote_archive_verified':True,
        'protocol_sha256':digest(PROTOCOL),'preflight_sha256':digest(ROOT/'ai/runs/auction-discount-teacher-preflight-v1/report.json')}
    save(SOURCE,source)
    base=p['current_source']
    env={'SOURCE_ARCHIVE':base['archive'],'SOURCE_REVISION':base['revision'],
         'SOURCE_SHA256':base['sha256'],'SOURCE_MANIFEST_SHA256':base['source_manifest_sha256'],
         'PILOT_ARCHIVE':source['archive'],'PILOT_REVISION':source['revision'],
         'PILOT_SHA256':source['sha256'],'PILOT_MANIFEST_SHA256':source['manifest_sha256'],
         'HF_HUB_DISABLE_PROGRESS_BARS':'1','OMP_NUM_THREADS':'1','OPENBLAS_NUM_THREADS':'1','MKL_NUM_THREADS':'1'}
    command=['bash','-lc',bootstrap()]
    config={'image':'python:3.11-slim-bookworm','command':command,'env':env,'flavor':'cpu-upgrade','timeout':'5h',
            'labels':{'name':NAME,'project':'powergrid-ai','stage':'auction-discount-teacher-pilot-v1'}}
    save(intent,{'created_at':datetime.now(timezone.utc).isoformat(),'config':config,'source_sha256':digest(SOURCE),
                 'roots':70,'worlds_per_root':4,'new_gradients':0,'automatic_job_retries':False})
    token=get_token();assert token
    job=api.run_job(**config,secrets={'HF_TOKEN':token})
    save(LAUNCH,{'job_id':job.id,'created_at':datetime.now(timezone.utc).isoformat(),
        'name':NAME,'source':source,'launch_intent_sha256':digest(intent),'roots':70,'worlds_per_root':4,
        'scope':'Teacher coverage/runtime pilot only; labels not yet admitted for training.',
        'new_gradient_updates':0,'qualified':False,'reserved_final_seeds_used':False})
    response=get_session().get(f'{api.endpoint}/api/jobs/coyotte508/{job.id}',headers=api._build_hf_headers(),timeout=60)
    hf_raise_for_status(response);raw=response.json()
    assert raw['id']==job.id and raw['dockerImage']==config['image'] and raw['flavor']==config['flavor']
    assert raw['command']==command and raw['environment']==env and raw['timeout']==18000
    assert raw['labels']['name']==NAME
    checked={'checked_at':datetime.now(timezone.utc).isoformat(),'job_id':job.id,'stage':raw['status']['stage'],
        'effective_configuration_verified':True,'source_sha256':digest(SOURCE),'launch_sha256':digest(LAUNCH)}
    save(OUT/'initial-status.json',checked)
    print(json.dumps(checked),flush=True)


if __name__=='__main__':main()
