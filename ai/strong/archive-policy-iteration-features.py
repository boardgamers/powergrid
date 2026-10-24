"""Persist verified public feature cache and its generation code at one HF pin."""
import shutil
from huggingface_hub import HfApi, hf_hub_download
from strategic_collection import ROOT, read, write, digest


def main():
    source = ROOT/'ai/runs/policy-iteration-features-v2'
    check = read(source/'feature-check.json')
    assert check['complete'] and check['positions'] == 17280 and not check['gradients']
    for file, sha in check['artifacts'].items():
        assert digest(source/file) == sha
    for file, sha in check['code'].items():
        assert digest(ROOT/file) == sha
    out = ROOT/'ai/runs/policy-iteration-feature-cache-evidence-v2'
    out.mkdir(exist_ok=False)
    for file in source.iterdir():
        shutil.copy2(file, out/file.name)
    for file in check['code']:
        target = out/'code'/file
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT/file, target)
    write(out/'manifest.json', {str(f.relative_to(out)): digest(f) for f in out.rglob('*') if f.is_file()})
    repo, prefix = 'coyotte508/powergrid-ai-germany-v1', 'runs/' + out.name
    commit = HfApi().upload_folder(repo_id=repo, folder_path=out, path_in_repo=prefix)
    files = {str(f.relative_to(out)): digest(f) for f in out.rglob('*') if f.is_file()}
    for file, sha in files.items():
        assert digest(hf_hub_download(repo, prefix + '/' + file, revision=commit.oid)) == sha
    descriptor = {'repo': repo, 'revision': commit.oid, 'prefix': prefix, 'files': files,
                  'positions': 17280, 'split_counts': check['split_counts'],
                  'label_protocol_sha256': check['label_protocol_sha256'],
                  'gradients': False, 'qualification_eligible': False}
    write(ROOT/'ai/strong/policy-iteration-feature-cache-evidence-v2.json', descriptor)
    print(descriptor, flush=True)


if __name__ == '__main__':
    main()
