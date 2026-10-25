"""Package unchanged proven engine plus fresh capture orchestration, upload once."""
import argparse
from pathlib import Path
import shutil
import tarfile

from huggingface_hub import HfApi, hf_hub_download
from strategic_collection import ROOT, read, write, digest
from opponent_surrogate_collection_v1 import PROTOCOL

STRONG = ROOT/'ai/strong'
PREP = ROOT/'ai/runs/opponent-surrogate-source-prepared-v1'
SOURCE = STRONG/'opponent-surrogate-source-v1.json'
ARCHIVE = ROOT/'ai/runs/strong-source-opponent-surrogate-v1.tgz'
PREFLIGHT = ROOT/'ai/runs/opponent-surrogate-source-preflight-v1.json'
FILES = ['capture-reference-opponent-v1.cjs','verify-opponent-surrogate-collection-v1.cjs',
         'opponent_surrogate_collection_v1.py','opponent-surrogate-collection-protocol-v1.json',
         'opponent-surrogate-collection-job-v1.py','test_opponent_surrogate_collection_v1.py',
         'test_opponent_surrogate_job_v1.py',
         'build-opponent-surrogate-source-v1.py','reference-opponent-capture-evidence-v1.json']


def prerequisites():
    protocol, preflight = read(PROTOCOL), read(PREFLIGHT)
    proof = read(STRONG/'reference-opponent-capture-evidence-v1.json')
    assert proof['remote_archive_verified'] and proof['exact_twin_games']==20 and proof['caps']==0
    assert protocol['capture_proof']['archive_sha256']==proof['archive_sha256']
    assert preflight['complete'] and preflight['full_grid_contracts']==2560
    assert preflight['real_preflight_games']==8 and preflight['exact_twins']==8 and preflight['caps']==0
    assert preflight['protocol_sha256']==digest(PROTOCOL)
    assert all(digest(ROOT/name)==sha for name,sha in preflight['tested_code_hashes'].items())
    return protocol,preflight


def prepare():
    protocol, preflight = prerequisites()
    assert not any(p.exists() for p in (PREP,SOURCE,ARCHIVE)), 'Inspect existing source preparation; do not overwrite'
    base = protocol['base_source']
    original = ROOT/'ai/runs'/base['archive']
    assert digest(original)==base['sha256']
    layout=PREP/'layout'
    layout.mkdir(parents=True)
    with tarfile.open(original) as bundle:
        members=bundle.getmembers()
        assert len(members)==base['files']==1463
        assert all(m.isfile() and not Path(m.name).is_absolute() and '..' not in Path(m.name).parts for m in members)
        bundle.extractall(layout,filter='data')
    before={str(p.relative_to(layout)):digest(p) for p in layout.rglob('*') if p.is_file()}
    assert len(before)==1463 and not (layout/'ai/runs').exists()
    tested_runtime=ROOT/'ai/runs/population-auction-regression-replays-v1/runtime'
    assert all(digest(tested_runtime/name)==sha for name,sha in before.items())
    added={}
    for filename in FILES:
        file=STRONG/filename
        name=str(file.relative_to(ROOT))
        assert name not in before
        shutil.copy2(file,layout/name)
        added[name]=digest(file)
    manifest={**before,**added}
    assert all(digest(layout/name)==sha for name,sha in manifest.items())
    write(layout/'opponent-surrogate-source-manifest.json',manifest)
    with tarfile.open(ARCHIVE,'w:gz') as bundle:
        for name in sorted([*manifest,'opponent-surrogate-source-manifest.json']):
            bundle.add(layout/name,arcname=name,recursive=False)
    prepared={'repo':base['repo'],'archive':ARCHIVE.name,'sha256':digest(ARCHIVE),'bytes':ARCHIVE.stat().st_size,
              'manifest_sha256':digest(layout/'opponent-surrogate-source-manifest.json'),
              'manifest_files':len(manifest),'protocol_sha256':digest(PROTOCOL),'base':base,
              'unchanged_base_files':1463,'new_files':added,'preflight_sha256':digest(PREFLIGHT),
              'collection_admitted':False,'runtime_admitted':False,'new_hf_jobs':0,'gradients':False,
              'qualification_eligible':False,'reserved_final_seeds_used':False}
    write(PREP/'prepared.json',prepared)
    print({k:prepared[k] for k in ('archive','sha256','manifest_files','unchanged_base_files')})


def upload():
    prerequisites()
    assert not SOURCE.exists(), 'Inspect the existing remote source before another upload'
    prepared=read(PREP/'prepared.json')
    assert digest(ARCHIVE)==prepared['sha256'] and digest(PROTOCOL)==prepared['protocol_sha256']
    assert digest(PREFLIGHT)==prepared['preflight_sha256']
    assert all(digest(ROOT/name)==sha for name,sha in prepared['new_files'].items())
    with (PREP/'upload-intent.json').open('x') as f:
        f.write('{"purpose":"One private source upload; reconcile any uncertain outcome."}\n')
    commit=HfApi().upload_file(repo_id=prepared['repo'],repo_type='dataset',path_or_fileobj=ARCHIVE,path_in_repo=ARCHIVE.name)
    write(PREP/'upload-receipt.json',{'revision':commit.oid,'sha256':prepared['sha256']})
    assert digest(hf_hub_download(prepared['repo'],ARCHIVE.name,repo_type='dataset',revision=commit.oid))==prepared['sha256']
    write(SOURCE,{**prepared,'revision':commit.oid,'remote_archive_verified':True})
    print({'revision':commit.oid,'sha256':prepared['sha256'],'remote_archive_verified':True})


if __name__=='__main__':
    p=argparse.ArgumentParser(__doc__)
    p.add_argument('operation',choices=['prepare','upload'])
    globals()[p.parse_args().operation]()
