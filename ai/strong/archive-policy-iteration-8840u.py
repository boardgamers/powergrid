"""Persist untrained target-CPU timing evidence, exact packages and current labels."""
import shutil
from huggingface_hub import HfApi, hf_hub_download
from strategic_collection import ROOT, read, write, digest


def main():
    prepared = ROOT/'ai/runs/policy-iteration-8840u-prepared-v2'
    raw = ROOT/'ai/runs/policy-iteration-8840u-results-v2'
    result = read(raw/'verified.json')
    assert result['verified'] and result['synthetic_untrained'] and result['requests'] == 10212
    assert result['gradients'] is False and result['qualification_eligible'] is False
    launch = read(ROOT/'ai/strong/policy-iteration-8840u-launch-v2.json')
    assert launch['stage'] == 'completed' and launch['returncode'] == 0
    assert digest(prepared/'manifest.json') == launch['manifest_sha256'] == result['manifest_sha256']
    for file, sha in result['artifacts'].items():
        assert digest(raw/file) == sha
    labels = read(ROOT/'ai/strong/policy-iteration-labels-results-v2.json')
    status = read(ROOT/'ai/strong/policy-iteration-labels-status-v2.json')
    out = ROOT/'ai/runs/policy-iteration-8840u-evidence-v2'
    out.mkdir(exist_ok=False)
    for p in raw.iterdir():
        if p.is_file() and p.name != 'fixtures.jsonl':
            shutil.copy2(p, out/p.name)
    for key in result['models']:
        for name in [key+'.tgz', key+'-package-manifest.json', key+'-local-check.json', key+'-local-check.log']:
            shutil.copy2(prepared/name, out/name)
    for name in ['prepare-policy-iteration-8840u.py', 'launch-policy-iteration-8840u.py',
                 'collect-policy-iteration-8840u.py', 'archive-policy-iteration-8840u.py',
                 'probe-strategic-packages-8840u.py', 'probe-search-transfer-8840u.py', 'verify-package.py',
                 'policy-iteration-8840u-launch-v2.json', 'policy-iteration-8840u-results-v2.json',
                 'policy-iteration-labels-results-v2.json', 'policy-iteration-labels-status-v2.json',
                 'policy-iteration-development-source-v2.json', 'policy-iteration-development-preflight-v2.json']:
        shutil.copy2(ROOT/'ai/strong'/name, out/name)
    for key, case in labels['cases'].items():
        p = ROOT/'ai/runs/policy-iteration-labels-verified-v2'/key/'verified.json'
        assert digest(p) == case['verified_sha256']
        destination = out/'verified-labels'/(key+'.json')
        destination.parent.mkdir(exist_ok=True)
        shutil.copy2(p, destination)
    write(out/'evidence-manifest.json', {str(p.relative_to(out)): digest(p) for p in out.rglob('*') if p.is_file()})
    repo, prefix = 'coyotte508/powergrid-ai-germany-v1', 'runs/'+out.name
    commit = HfApi().upload_folder(repo_id=repo, folder_path=out, path_in_repo=prefix)
    sha = digest(out/'evidence-manifest.json')
    assert digest(hf_hub_download(repo, prefix+'/evidence-manifest.json', revision=commit.oid)) == sha
    descriptor = {'repo': repo, 'revision': commit.oid, 'prefix': prefix, 'manifest_sha256': sha,
                  'synthetic_untrained': True, 'requests': 10212, 'all_target_moves_match_frozen_runtime': True,
                  'label_shards_verified': labels['complete_shards'], 'rollouts_including_pilot': labels['rollouts'],
                  'label_status_checked_at': status['checked_at'], 'label_status_counts': status['status_counts'],
                  'gradients': False, 'qualification_eligible': False}
    write(ROOT/'ai/strong/policy-iteration-8840u-evidence-v2.json', descriptor)
    print(descriptor, flush=True)


if __name__ == '__main__':
    main()
