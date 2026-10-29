"""Promote all checked teacher archives to one immutable private revision."""
import os
import shutil
from huggingface_hub import HfApi,hf_hub_download
from checkpoint_bucket_archives_v3 import archive_directory
from prepare_auction_discount_teacher_v2 import ROOT,read,save,digest


def main():
    descriptor=ROOT/'ai/strong/auction-discount-teacher-evidence-v2.json'
    out=ROOT/'ai/runs/auction-discount-teacher-evidence-v2'
    assert not out.exists() and not descriptor.exists(),'Inspect any prior archive intent/outcome'
    report=read(ROOT/'ai/strong/auction-discount-teacher-results-v2.json')
    assert report['complete'] and report['independently_audited'] and report['roots']==5770
    repo='coyotte508/powergrid-ai-training-v1';remote='evidence/auction-discount-teacher-complete-v2.tgz'
    api=HfApi();assert api.dataset_info(repo).private and not api.file_exists(repo,remote,repo_type='dataset')
    out.mkdir();collection=ROOT/'ai/runs/auction-discount-teacher-collection-v2'
    for shard in report['shards']:
        src=collection/f"shard-{shard['shard']:02d}";dst=out/src.name;(dst/'archives').mkdir(parents=True)
        assert digest(src/'audit.json')==shard['audit_sha256']
        for name in ('audit.json','receipts.json','job.log'):shutil.copyfile(src/name,dst/name)
        for archive in sorted((src/'archives').glob('*.tgz')):os.link(archive,dst/'archives'/archive.name)
    shutil.copyfile(collection/'state.json',out/'state.json')
    for name in ('auction-discount-teacher-results-v2.json','auction-discount-teacher-source-v2.json',
                 'auction-discount-teacher-protocol-v2.json','auction-discount-teacher-launch-v2.json',
                 'audit_auction_discount_teacher_v2.py','collect_auction_discount_teacher_v2.py'):
        shutil.copyfile(ROOT/'ai/strong'/name,out/name)
    save(out/'manifest.json',{str(p.relative_to(out)):digest(p) for p in sorted(out.rglob('*')) if p.is_file()})
    archive=archive_directory(out);save(out.with_name(out.name+'-upload-intent.json'),{'repo':repo,'archive':remote,'sha256':digest(archive)})
    commit=api.upload_file(repo_id=repo,repo_type='dataset',path_or_fileobj=archive,path_in_repo=remote)
    save(out.with_name(out.name+'-upload-commit.json'),{'revision':commit.oid,'archive':remote})
    assert digest(hf_hub_download(repo,remote,repo_type='dataset',revision=commit.oid))==digest(archive)
    save(descriptor,{'repo':repo,'repo_type':'dataset','revision':commit.oid,'archive':remote,'sha256':digest(archive),
        'manifest_sha256':digest(out/'manifest.json'),'remote_archive_verified':True,'roots':5770,'rollouts':1940544,
        'independently_audited':True,'caps':0,'qualified':False,'reserved_final_seeds_used':False})
    print({'archived':True,'revision':commit.oid,'bytes':archive.stat().st_size},flush=True)


if __name__=='__main__':main()
