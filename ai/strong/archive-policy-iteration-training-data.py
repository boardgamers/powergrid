"""Pin the compact, complete training bundle after strict local revalidation."""
from huggingface_hub import HfApi, hf_hub_download
from strategic_collection import ROOT, read, write, digest
from policy_iteration_data import validate_manifest, PROTOCOL, SOURCE
from policy_iteration_training import load_bundle


def main():
    manifest_path = ROOT/'ai/strong/policy-iteration-labels-results-v2.json'
    validate_manifest(read(manifest_path), read(PROTOCOL), read(SOURCE))
    design = read(ROOT/'ai/strong/policy-iteration-training-design-v2.json')
    directory = ROOT/'ai/runs/policy-iteration-training-data-v2'
    data, metadata, report = load_bundle(directory, design)
    assert report['label_manifest_sha256'] == digest(manifest_path)
    for file, sha in report['code'].items():
        assert digest(ROOT/file) == sha
    assert {f.name for f in directory.iterdir()} == {'features.npz', 'targets.npz', 'metadata.json',
        'feature-check.json', 'label-manifest.json', 'data-check.json'}
    files = {f.name: digest(f) for f in directory.iterdir()}
    descriptor_path = ROOT/'ai/strong/policy-iteration-training-data-evidence-v2.json'
    assert not descriptor_path.exists(), 'Use the existing immutable data pin'
    repo, prefix = 'coyotte508/powergrid-ai-germany-v1', 'runs/' + directory.name
    commit = HfApi().upload_folder(repo_id=repo, folder_path=directory, path_in_repo=prefix)
    for file, sha in files.items():
        assert digest(hf_hub_download(repo, prefix+'/'+file, revision=commit.oid)) == sha
    descriptor = {'repo': repo, 'revision': commit.oid, 'prefix': prefix, 'files': files,
                  'positions': len(metadata), 'split_counts': report['split_counts'],
                  'design_sha256': digest(ROOT/'ai/strong/policy-iteration-training-design-v2.json'),
                  'label_manifest_sha256': report['label_manifest_sha256'], 'gradients': False,
                  'qualification_eligible': False}
    write(descriptor_path, descriptor)
    print(descriptor, flush=True)


if __name__ == '__main__':
    main()
