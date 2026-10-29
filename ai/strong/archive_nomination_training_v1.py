"""Archive the completed training outputs and independent audits once."""
import shutil
from huggingface_hub import HfApi, hf_hub_download
from checkpoint_bucket_archives_v3 import archive_directory
from prepare_auction_discount_teacher_v2 import ROOT, read, save, digest


def main():
    out = ROOT/'ai/runs/nomination-discount-training-evidence-v1'
    descriptor = ROOT/'ai/strong/nomination-discount-training-evidence-v1.json'
    assert not out.exists() and not descriptor.exists(), 'Inspect prior archive intent/outcome'
    report = read(ROOT/'ai/strong/nomination-discount-training-results-v1.json')
    assert report['complete'] and len(report['arms']) == 4 and report['new_gradient_updates'] == 32640
    repo = 'coyotte508/powergrid-ai-training-v1'
    remote = 'evidence/nomination-discount-training-v1.tgz'
    api = HfApi(); assert api.dataset_info(repo).private and not api.file_exists(repo, remote, repo_type='dataset')
    shutil.copytree(ROOT/'ai/runs/nomination-discount-training-collected-v1', out)
    for name in ('nomination-discount-training-results-v1.json', 'nomination-discount-training-source-v1.json',
                 'nomination-discount-training-design-v1.json', 'nomination-discount-training-launch-v1.json',
                 'collect_nomination_training_v1.py', 'model_nomination_discount_v1.py'):
        shutil.copyfile(ROOT/'ai/strong'/name, out/name)
    save(out/'manifest.json', {str(p.relative_to(out)): digest(p) for p in sorted(out.rglob('*')) if p.is_file()})
    archive = archive_directory(out)
    save(out.with_name(out.name+'-upload-intent.json'), {'repo': repo, 'archive': remote, 'sha256': digest(archive)})
    commit = api.upload_file(repo_id=repo, repo_type='dataset', path_or_fileobj=archive, path_in_repo=remote)
    save(out.with_name(out.name+'-upload-commit.json'), {'revision': commit.oid, 'archive': remote})
    assert digest(hf_hub_download(repo, remote, repo_type='dataset', revision=commit.oid)) == digest(archive)
    save(descriptor, {'repo': repo, 'repo_type': 'dataset', 'revision': commit.oid, 'archive': remote,
                     'sha256': digest(archive), 'manifest_sha256': digest(out/'manifest.json'),
                     'remote_archive_verified': True, 'independently_audited': True, 'arms': 4,
                     'seeds_per_arm': 4, 'new_gradient_updates': 32640, 'qualified': False})
    print({'archived': True, 'revision': commit.oid}, flush=True)


if __name__ == '__main__': main()
