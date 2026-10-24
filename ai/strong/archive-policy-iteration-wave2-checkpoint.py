"""Archive verified labels, hardware replacement identities and evaluation tools."""
import shutil

from huggingface_hub import HfApi, hf_hub_download
from strategic_collection import ROOT, read, write, digest
from policy_iteration_label_attempts import ATTEMPTS, effective_guard


def main():
    labels = read(ROOT/'ai/strong/policy-iteration-labels-results-v2.json')
    status = read(ROOT/'ai/strong/policy-iteration-labels-status-v2.json')
    admission = read(ROOT/'ai/strong/policy-iteration-cpu-upgrade-wave2-admission-v2.json')
    controls = read(ROOT/'ai/strong/policy-iteration-collection-grid-controls-v2.json')
    assert labels['complete_shards'] >= 207 and not labels['complete']
    assert admission['admitted'] and admission['rollouts'] >= 34176
    assert controls['code_checks_passed'] and controls['training_collector_incomplete_grid_rejected']
    attempts = sorted(ATTEMPTS.glob('*.json'))
    assert all(read(p)['stage'] in ['launched', 'skipped'] for p in attempts)
    replacements = [read(p) for p in attempts if read(p)['stage'] == 'launched']
    assert 60 < len(replacements) <= 180
    assert {r['job_id'] for r in replacements} == {j['job_id'] for j in status['jobs'] if 'original_job_id' in j}
    guards = sorted((ROOT/'ai/runs/policy-iteration-labels-launches-v2').glob('*.json'))
    assert len(guards) == 948 and len({effective_guard(g)['job_id'] for g in guards}) == 948
    out = ROOT/'ai/runs/policy-iteration-wave2-checkpoint-v2'
    out.mkdir(exist_ok=False)
    names = [*controls['code'], 'policy-iteration-collection-grid-controls-v2.json',
        'policy-iteration-labels-results-v2.json', 'policy-iteration-labels-status-v2.json',
        'policy-iteration-labels-source-v2.json', 'policy-iteration-labels-protocol-v2.json',
        'policy-iteration-cpu-upgrade-wave2-admission-v2.json', 'policy-iteration-cpu-upgrade-profile-results-v2.json',
        'assess-policy-iteration-cpu-capacity.py', 'migrate-policy-iteration-labels-cpu.py',
        'policy_iteration_label_attempts.py', 'manage-policy-iteration-labels.py',
        'policy-iteration-development-protocol-v2.json', 'policy-iteration-development-source-v2.json',
        'policy-iteration-development-status-v2.json', 'policy-iteration-development-runtime-probes-v2.json',
        'policy-iteration-development-preflight-v2.json', 'manage-policy-iteration-development.py',
        'policy-iteration-training-design-v2.json', 'policy-iteration-training-source-code-check-v2.json',
        'policy-iteration-job-controls-v2.json', 'archive-policy-iteration-wave2-checkpoint.py']
    for name, sha in controls['code'].items():
        assert digest(ROOT/'ai/strong'/name) == sha
    for name in names:
        shutil.copy2(ROOT/'ai/strong'/name, out/name)
    for label, paths in [('original-guards', guards), ('replacement-attempts', attempts),
                         ('development-guards', sorted((ROOT/'ai/runs/policy-iteration-development-launches-v2').glob('*.json')))]:
        destination = out/label
        destination.mkdir()
        for path in paths:
            shutil.copy2(path, destination/path.name)
    destination = out/'verified-labels'
    destination.mkdir()
    for key, case in labels['cases'].items():
        path = ROOT/'ai/runs/policy-iteration-labels-verified-v2'/key/'verified.json'
        assert digest(path) == case['verified_sha256']
        shutil.copy2(path, destination/(key+'.json'))
    shutil.copytree(ROOT/'ai/runs/policy-iteration-development-verified-v2', out/'verified-development')
    for name in [*controls['logs'], 'policy-iteration-labels-cpu-upgrade-wave2-launch-v2.log']:
        shutil.copy2(ROOT/'ai/runs'/name, out/name)
    write(out/'manifest.json', {str(p.relative_to(out)): digest(p) for p in out.rglob('*') if p.is_file()})
    repo, prefix = 'coyotte508/powergrid-ai-germany-v1', 'runs/'+out.name
    commit = HfApi().upload_folder(repo_id=repo, folder_path=out, path_in_repo=prefix)
    sha = digest(out/'manifest.json')
    assert digest(hf_hub_download(repo, prefix+'/manifest.json', revision=commit.oid)) == sha
    result = {'repo': repo, 'revision': commit.oid, 'prefix': prefix, 'manifest_sha256': sha,
              'status_checked_at': status['checked_at'], 'status_counts': status['status_counts'],
              'replacement_jobs': len(replacements), 'complete_new_shards': labels['complete_shards'],
              'rollouts_including_pilot': labels['rollouts'],
              'new_collector_and_grid_contracts_passed': True, 'gradients': False,
              'reserved_final_seeds_used': False, 'qualification_eligible': False}
    write(ROOT/'ai/strong/policy-iteration-wave2-checkpoint-v2.json', result)
    print(result, flush=True)


if __name__ == '__main__':
    main()
