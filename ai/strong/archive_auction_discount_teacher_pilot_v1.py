"""Retain audited pilot results at an immutable private dataset revision."""
import shutil
from huggingface_hub import HfApi, hf_hub_download
from checkpoint_bucket_archives_v3 import archive_directory
from prepare_auction_discount_teacher_v1 import ROOT, digest, read, save


def main():
    descriptor=ROOT/'ai/strong/auction-discount-teacher-evidence-v1.json'
    out=ROOT/'ai/runs/auction-discount-teacher-evidence-v1'
    assert not descriptor.exists() and not out.exists() and not out.with_suffix('.tgz').exists(), 'Inspect existing archive intents/outcomes first'
    report=read(ROOT/'ai/strong/auction-discount-teacher-results-v1.json')
    assert report['independently_audited'] and report['roots']==70 and report['caps']==0
    repo='coyotte508/powergrid-ai-training-v1';remote='evidence/auction-discount-teacher-pilot-v1.tgz';api=HfApi()
    assert api.dataset_info(repo).private and not api.file_exists(repo,remote,repo_type='dataset')
    out.mkdir();shutil.copytree(ROOT/'ai/runs/auction-discount-teacher-collected-v1',out/'collected')
    for name in ('protocol','source','launch','results'):
        p=ROOT/f'ai/strong/auction-discount-teacher-{name}-v1.json';shutil.copyfile(p,out/p.name)
    for name in ('prepare','run','launch','collect'):
        p=ROOT/f'ai/strong/{name}_auction_discount_teacher_v1.py';shutil.copyfile(p,out/p.name)
    p=ROOT/'ai/strong/test_auction_discount_teacher_audit_v1.py';shutil.copyfile(p,out/p.name)
    shutil.copyfile(ROOT/'ai/runs/auction-discount-teacher-preflight-v1/report.json',out/'preflight.json')
    save(out/'manifest.json',{str(p.relative_to(out)):digest(p) for p in sorted(out.rglob('*')) if p.is_file()})
    archive=archive_directory(out);intent=out.with_name(out.name+'-upload-intent.json')
    save(intent,{'repo':repo,'archive':remote,'sha256':digest(archive)})
    commit=api.upload_file(repo_id=repo,repo_type='dataset',path_or_fileobj=archive,path_in_repo=remote)
    save(out.with_name(out.name+'-upload-commit.json'),{'revision':commit.oid,'archive':remote})
    assert digest(hf_hub_download(repo,remote,repo_type='dataset',revision=commit.oid))==digest(archive)
    save(descriptor,{'repo':repo,'repo_type':'dataset','revision':commit.oid,'archive':remote,
        'sha256':digest(archive),'manifest_sha256':digest(out/'manifest.json'),'remote_archive_verified':True,
        'roots_independently_audited':70,'rollouts_independently_audited':1444,
        'pilot_targets_training_ready':False,'qualified':False,'reserved_final_seeds_used':False})
    print({'archived':True,'revision':commit.oid,'bytes':archive.stat().st_size},flush=True)


if __name__=='__main__':main()
