"""Prepare an immutable GPU package and explicitly launch the four fixed arms."""
import argparse
from datetime import datetime,timezone
import json
from pathlib import Path
import shutil
import subprocess
import sys
from huggingface_hub import HfApi,get_token,hf_hub_download
from huggingface_hub.utils import get_session,hf_raise_for_status
from checkpoint_bucket_archives_v3 import archive_directory
from prepare_auction_discount_teacher_v2 import ROOT,read,save,digest

OUT=ROOT/'ai/runs/nomination-discount-training-source-v1'
SOURCE=ROOT/'ai/strong/nomination-discount-training-source-v1.json'
DESIGN=ROOT/'ai/strong/nomination-discount-training-design-v1.json'
REPO='coyotte508/powergrid-ai-training-v1'
CODE=['model.py','model_v4.py','model_discard.py','model_strategic.py','model_policy_iteration.py',
      'model_auction_discount_v1.py','model_nomination_discount_v1.py','strategic_correction_targets.py',
      'train_nomination_discount_v1.py']
BOOTSTRAP=r'''set -euo pipefail
python -m pip install --quiet huggingface_hub==2.0.0 numpy==2.4.6
mkdir -p /workspace
python -B - <<'SOURCE'
import os,hashlib,json,tarfile
from pathlib import Path
from huggingface_hub import hf_hub_download
file=hf_hub_download('coyotte508/powergrid-ai-training-v1',os.environ['SOURCE_ARCHIVE'],repo_type='dataset',revision=os.environ['SOURCE_REVISION'])
assert hashlib.sha256(Path(file).read_bytes()).hexdigest()==os.environ['SOURCE_SHA256']
out=Path('/workspace/nomination');assert not out.exists()
with tarfile.open(file) as bundle:
 members=bundle.getmembers();names=[m.name for m in members]
 assert len(names)==len(set(names)) and all(m.isfile() and not Path(m.name).is_absolute() and '..' not in Path(m.name).parts for m in members)
 manifest=bundle.extractfile('manifest.json').read();assert hashlib.sha256(manifest).hexdigest()==os.environ['MANIFEST_SHA256']
 pins=json.loads(manifest);assert set(names)==set(pins)|{'manifest.json'}
 assert all(hashlib.sha256(bundle.extractfile(name).read()).hexdigest()==sha for name,sha in pins.items())
 out.mkdir();bundle.extractall(out,filter='data')
SOURCE
python -u -B /workspace/nomination/code/train_nomination_discount_v1.py --bundle /workspace/nomination --output "/workspace/pg-nomination-train-v1-$ARM" --arm "$ARM" --upload
'''


def prepare():
    assert not OUT.exists() and not SOURCE.exists(),'Inspect prior source preparation/upload'
    design=read(DESIGN);evidence=read(ROOT/'ai/strong/auction-discount-teacher-evidence-v2.json')
    assert evidence['remote_archive_verified'] and evidence['independently_audited'] and evidence['roots']==5770
    check=read(ROOT/'ai/strong/nomination-discount-model-check-v1.json');assert check['complete']
    assert check['model_sha256']==digest(ROOT/'ai/strong/model_nomination_discount_v1.py')
    assert design['model_check_sha256']==digest(ROOT/'ai/strong/nomination-discount-model-check-v1.json')
    data=ROOT/'ai/runs/nomination-discount-training-data-v1';assert digest(data/'report.json')==design['data_report_sha256']
    OUT.mkdir();bundle=OUT/'bundle';(bundle/'code').mkdir(parents=True)
    for name in CODE:shutil.copyfile(ROOT/'ai/strong'/name,bundle/'code'/name)
    shutil.copytree(data,bundle/'data')
    shutil.copytree(ROOT/'ai/runs/auction-discount-teacher-prepared-v1/bundle/transport',bundle/'transport')
    parent=ROOT/'ai/runs/policy-iteration-training-verified-v2/frozen/ensemble-1/best.pt'
    assert digest(parent)==design['parent_sha256'];shutil.copyfile(parent,bundle/'parent.pt')
    shutil.copyfile(DESIGN,bundle/'design.json')
    save(bundle/'teacher-evidence.json',evidence);save(bundle/'model-check.json',check)
    subprocess.run([sys.executable,'-B',str(bundle/'code/train_nomination_discount_v1.py'),'--help'],cwd='/tmp',check=True,stdout=subprocess.DEVNULL)
    save(bundle/'manifest.json',{str(p.relative_to(bundle)):digest(p) for p in sorted(bundle.rglob('*')) if p.is_file()})
    api=HfApi();assert api.dataset_info(REPO).private
    remote='strong-source-nomination-discount-training-v1.tgz';assert not api.file_exists(REPO,remote,repo_type='dataset')
    archive=archive_directory(bundle);save(OUT/'upload-intent.json',{'archive':remote,'sha256':digest(archive)})
    commit=api.upload_file(repo_id=REPO,repo_type='dataset',path_or_fileobj=archive,path_in_repo=remote)
    save(OUT/'upload-commit.json',{'archive':remote,'revision':commit.oid})
    assert digest(hf_hub_download(REPO,remote,repo_type='dataset',revision=commit.oid))==digest(archive)
    save(SOURCE,{'repo':REPO,'revision':commit.oid,'archive':remote,'sha256':digest(archive),
        'manifest_sha256':digest(bundle/'manifest.json'),'design_sha256':digest(DESIGN),
        'data_report_sha256':design['data_report_sha256'],'remote_archive_verified':True,'teacher_evidence':evidence})
    print({'source_prepared':True,'revision':commit.oid,'bytes':archive.stat().st_size},flush=True)


def launch(name):
    source=read(SOURCE);design=read(DESIGN)
    assert source['design_sha256']==digest(DESIGN) and source['remote_archive_verified']
    assert name in [a['name'] for a in design['arms']]
    assert digest(OUT/'bundle/design.json')==digest(DESIGN)
    pins=read(OUT/'bundle/manifest.json')
    assert all(digest(ROOT/'ai/strong'/f)==pins['code/'+f] for f in CODE)
    folder=OUT/'launches';folder.mkdir(exist_ok=True)
    intent=folder/(name+'.intent.json');receipt=folder/(name+'.json')
    assert not intent.exists() and not receipt.exists(),'Inspect prior arm handle before any retry'
    env={'SOURCE_ARCHIVE':source['archive'],'SOURCE_REVISION':source['revision'],'SOURCE_SHA256':source['sha256'],
         'MANIFEST_SHA256':source['manifest_sha256'],'ARM':name,'POWERGRID_HF_TRAINING':'1',
         'HF_HUB_DISABLE_PROGRESS_BARS':'1','OMP_NUM_THREADS':'4','OPENBLAS_NUM_THREADS':'1'}
    config={'image':'pytorch/pytorch:2.6.0-cuda12.4-cudnn9-runtime','command':['bash','-lc',BOOTSTRAP],
            'env':env,'flavor':'l4x1','timeout':'3h','labels':{'name':'pg-nomination-train-v1-'+name,'project':'powergrid-ai'}}
    save(intent,{'created_at':datetime.now(timezone.utc).isoformat(),'config':config,'source_sha256':digest(SOURCE),'automatic_retries':False})
    token=get_token();assert token;api=HfApi();job=api.run_job(**config,secrets={'HF_TOKEN':token})
    record={'arm':name,'job_id':job.id,'source_sha256':digest(SOURCE),'intent_sha256':digest(intent),'created_at':datetime.now(timezone.utc).isoformat()}
    save(receipt,record)
    response=get_session().get(f'{api.endpoint}/api/jobs/coyotte508/{job.id}',headers=api._build_hf_headers(),timeout=60)
    hf_raise_for_status(response);raw=response.json()
    assert raw['id']==job.id and raw['dockerImage']==config['image'] and raw['flavor']==config['flavor']
    assert raw['command']==config['command'] and raw['environment']==env and raw['timeout']==10800
    save(folder/(name+'.checked.json'),{'job_id':job.id,'stage':raw['status']['stage'],'effective_configuration_verified':True})
    summary={'source':source,'jobs':[read(folder/(a['name']+'.json')) for a in design['arms'] if (folder/(a['name']+'.json')).exists()],
             'design_sha256':digest(DESIGN),'qualified':False,'reserved_final_seeds_used':False}
    target=ROOT/'ai/strong/nomination-discount-training-launch-v1.json';temp=target.with_suffix('.tmp')
    temp.write_text(json.dumps(summary,indent=2)+'\n');temp.replace(target)
    print({'arm':name,'job_id':job.id,'stage':raw['status']['stage']},flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(__doc__);g=p.add_mutually_exclusive_group(required=True)
    g.add_argument('--prepare',action='store_true');g.add_argument('--launch');a=p.parse_args()
    if a.prepare:prepare()
    else:launch(a.launch)
