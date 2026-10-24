"""Preserve a partial-label checkpoint without changing immutable raw shard pins."""
import argparse
import shutil
from strategic_collection import ROOT, read, write, digest
from policy_iteration_evidence_archive import upload_evidence


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
                 'archive-policy-iteration-labels-progress.py', 'policy_iteration_evidence_archive.py']:
        shutil.copy2(ROOT/'ai/strong'/file, out/file)
    assert read(out/'policy-iteration-labels-results-v2.json') == result, 'Labels changed while copying; preserve and inspect snapshot'
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
    archive = upload_evidence(out)
    descriptor = {**archive,
                  'complete_new_shards': result['complete_shards'], 'verified_root_mode_pairs': result['verified_root_mode_pairs'],
                  'rollouts_including_pilot': result['rollouts'], 'full_labels_complete': False,
                  'gradients': False, 'qualification_eligible': False}
    write(ROOT/'ai/strong'/(args.name + '.json'), descriptor)
    print(descriptor, flush=True)


if __name__ == '__main__':
    main()
