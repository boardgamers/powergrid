"""Bounded private-HF frozen-policy opponent study; compact outcomes only."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import traceback
from huggingface_hub import HfApi, hf_hub_download
from data import ROOT, atomic_json, digest
from job import retry
from opponent_study import PROTOCOL, run as evaluate


def run():
    run_id=os.environ['RUN_ID'];repo=os.environ['MODEL_REPO']
    base=Path(os.environ.get('RUN_DIR','/tmp/multimap-opponents-run'));base.mkdir(parents=True,exist_ok=True)
    api=HfApi();receipts=[]
    if not api.model_info(repo).private:raise RuntimeError('Study artifacts must remain private')
    status=dict(run=run_id,sourceRevision=os.environ['SOURCE_REVISION'],sourceSha256=os.environ['SOURCE_SHA256'],protocol=PROTOCOL,qualified=False)
    def upload(stage):
        files=[p for p in base.rglob('*') if p.is_file() and p.suffix!='.tmp' and p.name!='artifacts.json']
        if sum(p.stat().st_size for p in files)>128*1024**2:raise RuntimeError('Study artifact budget exceeded 128 MiB')
        status.update(stage=stage,receipts=receipts);atomic_json(base/'status.json',status)
        atomic_json(base/'artifacts.json',{str(p.relative_to(base)):digest(p) for p in base.rglob('*') if p.is_file() and p.suffix!='.tmp' and p.name!='artifacts.json'})
        result=retry(lambda:api.upload_folder(repo_id=repo,folder_path=base,path_in_repo=f'runs/{run_id}',ignore_patterns=['*.tmp'],commit_message=f'{run_id}: {stage}'))
        receipts.append(dict(stage=stage,revision=result.oid))
        print(json.dumps(dict(stage='uploaded',label=stage,revision=result.oid)),flush=True)
    try:
        subprocess.run(['node','--test','ai/multimap/test.cjs','ai/multimap/test_rl.cjs'],cwd=ROOT,check=True)
        subprocess.run([sys.executable,'-B','-m','unittest','discover','-s','ai/multimap','-p','test_*.py'],cwd=ROOT,check=True)
        if os.environ.get('RESUME_RUN'):
            previous=os.environ['RESUME_RUN'];revision=os.environ['RESUME_REVISION']
            if len(revision)!=40 or any(c not in '0123456789abcdef' for c in revision):raise ValueError('Resume must use immutable commit')
            prefix=f'runs/{previous}/'
            manifest=json.loads(Path(hf_hub_download(repo,prefix+'artifacts.json',revision=revision)).read_text())
            assert 'study/plan.json' in manifest and 'study/games.jsonl' in manifest
            for name,sha in manifest.items():
                relative=Path(name)
                if not relative.parts or relative.parts[0]!='study':continue
                if relative.is_absolute() or '..' in relative.parts or relative.suffix not in ('.json','.jsonl'):raise ValueError('Unsafe study artifact path')
                source=Path(hf_hub_download(repo,prefix+name,revision=revision))
                if digest(source)!=sha:raise ValueError('Study resume hash mismatch')
                destination=base/relative;destination.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,destination)
            status.update(resumeRun=previous,resumeRevision=revision)
        pin=PROTOCOL['checkpoint'];checkpoint=hf_hub_download(pin['repo'],pin['path'],revision=pin['revision'])
        if digest(checkpoint)!=pin['sha256']:raise ValueError('Wrong study checkpoint')
        status['result']=evaluate(checkpoint,base/'study',workers=PROTOCOL['workers'],callback=upload)
        upload('complete')
        print(json.dumps(dict(stage='complete',run=run_id,failures=status['result']['failures'],qualified=False)),flush=True)
    except BaseException:
        status['error']=traceback.format_exc()
        try:upload('failed')
        except Exception:traceback.print_exc()
        raise


if __name__=='__main__':run()
