"""Preserve a partial-label checkpoint without changing immutable raw shard pins."""
import argparse
import shutil
from huggingface_hub import HfApi, hf_hub_download
from strategic_collection import ROOT, read, write, digest


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--name', required=True)
    args = parser.parse_args()
    assert args.name.startswith('policy-iteration-labels-') and '/' not in args.name and '..' not in args.name
    result = read(ROOT/'ai/strong/policy-iteration-labels-results-v2.json')
    assert not result['complete'] and 0 < result['complete_shards'] < result['planned_shards']
    out = ROOT/'ai/runs'/args.name
    out.mkdir(exist_ok=False)
    for file in ['policy-iteration-labels-results-v2.json', 'policy-iteration-labels-status-v2.json',
                 'policy-iteration-labels-source-v2.json', 'policy-iteration-labels-protocol-v2.json',
                 'policy-iteration-labels-launch-evidence-v2.json', 'policy-iteration-data-first-labels-preflight-v2.json',
                 'manage-policy-iteration-labels.py', 'policy_iteration_label_attempts.py',
                 'archive-policy-iteration-labels-progress.py']:
        shutil.copy2(ROOT/'ai/strong'/file, out/file)
    first_parser_manifest = ROOT/'ai/runs/policy-iteration-data-first-labels-manifest-v2.json'
    assert digest(first_parser_manifest) == read(out/'policy-iteration-data-first-labels-preflight-v2.json')['manifest_sha256']
    shutil.copy2(first_parser_manifest, out/first_parser_manifest.name)
    for key, case in result['cases'].items():
        source = ROOT/'ai/runs/policy-iteration-labels-verified-v2'/key/'verified.json'
        assert digest(source) == case['verified_sha256']
        destination = out/'verified'/(key + '.json')
        destination.parent.mkdir(exist_ok=True)
        shutil.copy2(source, destination)
    write(out/'manifest.json', {str(f.relative_to(out)): digest(f) for f in out.rglob('*') if f.is_file()})
    repo, prefix = 'coyotte508/powergrid-ai-germany-v1', 'runs/' + out.name
    commit = HfApi().upload_folder(repo_id=repo, folder_path=out, path_in_repo=prefix)
    sha = digest(out/'manifest.json')
    assert digest(hf_hub_download(repo, prefix + '/manifest.json', revision=commit.oid)) == sha
    descriptor = {'repo': repo, 'revision': commit.oid, 'prefix': prefix, 'manifest_sha256': sha,
                  'complete_new_shards': result['complete_shards'], 'verified_root_mode_pairs': result['verified_root_mode_pairs'],
                  'rollouts_including_pilot': result['rollouts'], 'full_labels_complete': False,
                  'gradients': False, 'qualification_eligible': False}
    write(ROOT/'ai/strong'/(args.name + '.json'), descriptor)
    print(descriptor, flush=True)


if __name__ == '__main__':
    main()
