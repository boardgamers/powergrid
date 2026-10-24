"""Persist hardware controls, replacement identities, labels and job preparation."""
import shutil
from huggingface_hub import HfApi, hf_hub_download
from strategic_collection import ROOT, read, write, digest
from policy_iteration_label_attempts import ATTEMPTS, effective_guard


def main():
    status = read(ROOT/'ai/strong/policy-iteration-labels-status-v2.json')
    labels = read(ROOT/'ai/strong/policy-iteration-labels-results-v2.json')
    profile = read(ROOT/'ai/strong/policy-iteration-cpu-upgrade-profile-results-v2.json')
    code_check = read(ROOT/'ai/strong/policy-iteration-training-source-code-check-v2.json')
    assert profile['verified'] and code_check['passed'] and code_check['code_only']
    assert len(status['jobs']) == len({j['job_id'] for j in status['jobs']}) == 948
    attempts = list(sorted(ATTEMPTS.glob('*.json')))
    assert attempts and all(read(p)['stage'] in ['launched', 'skipped'] for p in attempts)
    replacements = [read(p) for p in attempts if read(p)['stage'] == 'launched']
    assert {j['job_id'] for j in status['jobs'] if 'original_job_id' in j} == {a['job_id'] for a in replacements}
    out = ROOT/'ai/runs/policy-iteration-capacity-checkpoint-v2'
    out.mkdir(exist_ok=False)
    names = [
        'policy-iteration-labels-results-v2.json', 'policy-iteration-labels-status-v2.json',
        'policy-iteration-labels-source-v2.json', 'policy-iteration-labels-complete-launch-evidence-v2.json',
        'policy-iteration-labels-protocol-v2.json', 'manage-policy-iteration-labels.py',
        'policy_iteration_label_attempts.py', 'migrate-policy-iteration-labels-cpu.py',
        'launch-policy-iteration-cpu-upgrade-profile.py', 'collect-policy-iteration-cpu-upgrade-profile.py',
        'policy-iteration-cpu-upgrade-profile-status-v2.json', 'policy-iteration-cpu-upgrade-profile-results-v2.json',
        'profile-policy-iteration-verification.py', 'policy-iteration-verification-profile-v2.json',
        'policy_iteration_job.py', 'preflight-policy-iteration-training-source.py',
        'build-policy-iteration-training-source.py', 'launch-policy-iteration-training.py',
        'policy-iteration-training-source-code-check-v2.json', 'policy-iteration-training-design-v2.json',
        'policy-iteration-job-controls-v2.json', 'archive-policy-iteration-capacity-checkpoint.py',
    ]
    for name in names:
        shutil.copy2(ROOT/'ai/strong'/name, out/name)
    # Include the exact package additions so recovery does not depend on Git state.
    for rel, sha in code_check['overlays'].items():
        assert digest(ROOT/rel) == sha
        destination = out/'training-code'/rel
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT/rel, destination)
    for path in attempts:
        original = ROOT/'ai/runs/policy-iteration-labels-launches-v2'/path.name
        effective_guard(original)
        destination = out/'attempts'/path.name
        destination.parent.mkdir(exist_ok=True)
        shutil.copy2(path, destination)
    for key, case in labels['cases'].items():
        source = ROOT/'ai/runs/policy-iteration-labels-verified-v2'/key/'verified.json'
        assert digest(source) == case['verified_sha256']
        destination = out/'verified-labels'/(key+'.json')
        destination.parent.mkdir(exist_ok=True)
        shutil.copy2(source, destination)
    shutil.copy2(ROOT/'ai/runs/policy-iteration-cpu-upgrade-profile-launch-v2.json', out/'cpu-upgrade-profile-launch.json')
    shutil.copytree(ROOT/'ai/runs/policy-iteration-cpu-upgrade-profile-verified-v2', out/'hardware-profile')
    for name in ['policy-iteration-training-source-code-v2', 'policy-iteration-training-source-code-v3']:
        source = ROOT/'ai/runs'/name/'ai/runs/policy-iteration-training-source-checks-v2'
        shutil.copytree(source, out/name)
    write(out/'manifest.json', {str(f.relative_to(out)): digest(f) for f in out.rglob('*') if f.is_file()})
    repo, prefix = 'coyotte508/powergrid-ai-germany-v1', 'runs/'+out.name
    commit = HfApi().upload_folder(repo_id=repo, folder_path=out, path_in_repo=prefix)
    sha = digest(out/'manifest.json')
    assert digest(hf_hub_download(repo, prefix+'/manifest.json', revision=commit.oid)) == sha
    result = {'repo': repo, 'revision': commit.oid, 'prefix': prefix, 'manifest_sha256': sha,
              'status_checked_at': status['checked_at'], 'effective_job_counts': status['status_counts'],
              'replacement_jobs': len(replacements), 'complete_new_shards': labels['complete_shards'],
              'rollouts_including_pilot': labels['rollouts'], 'hardware_profile_exact': True,
              'training_source_code_checked': True, 'full_training_source_admitted': False,
              'gradients': False, 'qualification_eligible': False}
    write(ROOT/'ai/strong/policy-iteration-capacity-checkpoint-v2.json', result)
    print(result, flush=True)


if __name__ == '__main__':
    main()
