"""Pin the same Node release in the existing private HF dataset; no HF Jobs."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tarfile
import time
import urllib.request

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'ai/runs/node-runtime-cache-v1'
NAME='node-v24.14.0-linux-x64.tar.xz'
BASE='https://nodejs.org/dist/v24.14.0/'
REPO='coyotte508/powergrid-ai-training-v1'
REMOTE='bootstrap/'+NAME
RESULT=ROOT/'ai/strong/node-runtime-cache-v1.json'


def sha(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def write(path,value):
    with path.open('x') as stream:json.dump(value,stream,indent=2);stream.write('\n')


def fetch(name):
    attempts=[]
    for attempt in range(1,4):
        path=OUT/(name+'.download-'+str(attempt))
        try:
            with urllib.request.urlopen(BASE+name,timeout=45) as response,path.open('xb') as stream:
                expected=int(response.headers['Content-Length']) if response.headers.get('Content-Length') else None
                while block:=response.read(1024*1024):stream.write(block)
            assert expected is None or path.stat().st_size==expected,'Short official download'
            attempts.append({'attempt':attempt,'complete':True,'bytes':path.stat().st_size,'sha256':sha(path)})
            write(OUT/(name+'.download-receipt.json'),{'url':BASE+name,'attempts':attempts})
            return path
        except Exception as error:
            attempts.append({'attempt':attempt,'complete':False,'error_type':type(error).__name__,
                'bytes':path.stat().st_size if path.exists() else 0,'sha256':sha(path) if path.exists() else None})
            if attempt==3:
                write(OUT/(name+'.download-failure.json'),{'url':BASE+name,'attempts':attempts});raise
            time.sleep(2)


def prepare():
    assert not OUT.exists(),'Inspect existing preparation; do not erase partial downloads'
    OUT.mkdir()
    checksums=fetch('SHASUMS256.txt')
    matches=[line.split()[0] for line in checksums.read_text().splitlines()
        if len(line.split())==2 and line.split()[1]==NAME]
    assert len(matches)==1 and len(matches[0])==64
    binary=fetch(NAME);assert sha(binary)==matches[0],'Official archive checksum mismatch'
    executable=OUT/'node'
    with tarfile.open(binary,'r:xz') as bundle:
        member=bundle.getmember('node-v24.14.0-linux-x64/bin/node');assert member.isfile()
        with executable.open('xb') as stream:stream.write(bundle.extractfile(member).read())
    executable.chmod(0o755)
    version=subprocess.check_output([str(executable),'--version'],text=True).strip();assert version=='v24.14.0'
    receipt={'repo':REPO,'repo_type':'dataset','path':REMOTE,'official_url':BASE+NAME,
        'official_shasums_url':BASE+'SHASUMS256.txt','sha256':sha(binary),'bytes':binary.stat().st_size,
        'shasums_sha256':sha(checksums),'local_archive':str(binary.relative_to(ROOT)),
        'node_executable_sha256':sha(executable),'version':version,'preparer_sha256':sha(Path(__file__)),
        'new_hf_jobs':0,'qualification_eligible':False,'reserved_final_seeds_used':False}
    write(OUT/'prepared.json',receipt);print(json.dumps(receipt),flush=True)


def upload():
    from huggingface_hub import HfApi,hf_hub_download
    prepared=json.loads((OUT/'prepared.json').read_text());binary=ROOT/prepared['local_archive']
    assert sha(binary)==prepared['sha256'] and sha(Path(__file__))==prepared['preparer_sha256']
    assert not RESULT.exists() and not (OUT/'upload-intent.json').exists(),'Inspect existing upload outcome before retry'
    api=HfApi();assert api.repo_info(REPO,repo_type='dataset').private
    assert not api.file_exists(REPO,REMOTE,repo_type='dataset'),'Inspect existing remote artifact'
    write(OUT/'upload-intent.json',{'repo':REPO,'path':REMOTE,'sha256':prepared['sha256']})
    commit=api.upload_file(repo_id=REPO,repo_type='dataset',path_in_repo=REMOTE,path_or_fileobj=binary)
    write(OUT/'upload-receipt.json',{'revision':commit.oid,'repo':REPO,'path':REMOTE,'sha256':prepared['sha256']})
    assert sha(Path(hf_hub_download(REPO,REMOTE,repo_type='dataset',revision=commit.oid)))==prepared['sha256']
    result={**prepared,'revision':commit.oid,'remote_archive_verified':True,'prepared_sha256':sha(OUT/'prepared.json')}
    write(RESULT,result);print(json.dumps(result),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(__doc__);parser.add_argument('operation',choices=('prepare','upload'))
    globals()[parser.parse_args().operation]()
