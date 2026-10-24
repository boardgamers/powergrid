"""Preserve the bounded third capacity wave and independently verified results."""
from collections import Counter
import shutil

from huggingface_hub import HfApi, hf_hub_download
from strategic_collection import ROOT, read, write, digest
from policy_iteration_label_attempts import ATTEMPTS, effective_guard


def main():
    strong = ROOT/'ai/strong'
    labels = read(strong/'policy-iteration-labels-results-v2.json')
    status = read(strong/'policy-iteration-labels-status-v2.json')
    admission = read(strong/'policy-iteration-cpu-upgrade-wave3-admission-v2.json')
    reference = read(strong/'policy-iteration-parent-reference-progress-90-v2.json')
    development = read(strong/'policy-iteration-development-status-v2.json')
    assert labels['complete_shards'] >= 312 and not labels['complete']
    assert admission['admitted'] and admission['maximum_total_replacements'] == 300
    assert admission['frozen_worker_unchanged'] and admission['second_wave_all120_started']
    attempts = sorted(ATTEMPTS.glob('*.json'))
    assert all(read(p)['stage'] in ['launched', 'skipped'] for p in attempts)
    replacements = [read(p) for p in attempts if read(p)['stage'] == 'launched']
    skipped = [read(p) for p in attempts if read(p)['stage'] == 'skipped']
    assert len(replacements) == 300 and len(skipped) == 3
    assert {r['job_id'] for r in replacements} == {j['job_id'] for j in status['jobs'] if 'original_job_id' in j}
    for record in replacements:
        assert record['before']['stage'] == 'SCHEDULING'
        assert record['before']['started_at'] == record['cancellation']['started_at'] == 'None'
        assert record['cancellation']['stage'] in ['CANCELED', 'CANCELLED']
    guards = sorted((ROOT/'ai/runs/policy-iteration-labels-launches-v2').glob('*.json'))
    effective = [effective_guard(path) for path in guards]
    assert len(guards) == len({r['job_id'] for r in effective}) == 948
    assert {r['job_id'] for r in effective} == {r['job_id'] for r in status['jobs']}
    for descriptor in ['policy-iteration-labels-source-v2.json', 'policy-iteration-development-source-v2.json']:
        for file, sha in read(strong/descriptor)['overlays'].items():
            assert digest(ROOT/file) == sha, 'Frozen worker changed'
    assert reference['verified_shards'] == 90 and reference['verified_games'] == 5504
    assert not reference['qualification_eligible'] and not reference['reserved_final_seeds_used']
    out = ROOT/'ai/runs/policy-iteration-wave3-checkpoint-v2'
    out.mkdir(exist_ok=False)
    names = [
        'policy-iteration-labels-results-v2.json', 'policy-iteration-labels-status-v2.json',
        'policy-iteration-labels-source-v2.json', 'policy-iteration-labels-protocol-v2.json',
        'policy-iteration-cpu-upgrade-wave3-admission-v2.json', 'policy-iteration-cpu-upgrade-profile-results-v2.json',
        'assess-policy-iteration-cpu-wave3.py', 'migrate-policy-iteration-labels-cpu.py',
        'policy_iteration_label_attempts.py', 'manage-policy-iteration-labels.py',
        'policy-iteration-development-protocol-v2.json', 'policy-iteration-development-source-v2.json',
        'policy-iteration-development-status-v2.json', 'policy-iteration-development-runtime-probes-v2.json',
        'policy-iteration-development-preflight-v2.json', 'manage-policy-iteration-development.py',
        'manage-policy-iteration-development-grid.py', 'compare-policy-iteration-development.py',
        'inspect-policy-iteration-reference.py', 'policy-iteration-parent-reference-progress-88-v2.json',
        'policy-iteration-parent-reference-progress-90-v2.json',
        'policy-iteration-training-design-v2.json', 'policy-iteration-training-source-code-check-v2.json',
        'policy-iteration-job-controls-v2.json', 'archive-policy-iteration-wave3-checkpoint.py']
    for name in names:
        shutil.copy2(strong/name, out/name)
    shutil.copy2(strong/'policy-iteration-development-plans-v2/parent.json', out/'parent-plan.json')
    for label, paths in [
            ('original-guards', guards), ('replacement-attempts', attempts),
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
    for case, provenance in reference['provenance'].items():
        directory = ROOT/'ai/runs/policy-iteration-development-verified-v2'/case
        assert digest(directory/'verified.json') == provenance['verified_sha256']
        record = read(directory/'verified.json')
        for file, sha in record['artifacts'].items():
            assert digest(directory/file) == sha
        shutil.copytree(directory, out/'verified-development'/case)
    for name in ['policy-iteration-labels-cpu-upgrade-wave3-launch-v2.log',
                 'policy-iteration-labels-cpu-upgrade-wave3-fill-v2.log',
                 'policy-iteration-parent-reference-inspect-90-v2.log']:
        shutil.copy2(ROOT/'ai/runs'/name, out/name)
    write(out/'manifest.json', {str(p.relative_to(out)): digest(p) for p in out.rglob('*') if p.is_file()})
    repo, prefix = 'coyotte508/powergrid-ai-germany-v1', 'runs/'+out.name
    commit = HfApi().upload_folder(repo_id=repo, folder_path=out, path_in_repo=prefix)
    sha = digest(out/'manifest.json')
    assert digest(hf_hub_download(repo, prefix+'/manifest.json', revision=commit.oid)) == sha
    parent_jobs = [j for j in development['jobs'] if j['case'].startswith('development-parent-')]
    result = {
        'repo': repo, 'revision': commit.oid, 'prefix': prefix, 'manifest_sha256': sha,
        'status_checked_at': status['checked_at'], 'status_counts': status['status_counts'],
        'replacement_jobs': len(replacements), 'skipped_started_originals': len(skipped),
        'all_replaced_originals_canceled_before_start': True, 'original_guards_preserved': True,
        'complete_new_shards': labels['complete_shards'], 'root_mode_pairs': labels['verified_root_mode_pairs'],
        'rollouts_including_pilot': labels['rollouts'],
        'parent_status_checked_at': development['checked_at'],
        'parent_status_counts': dict(Counter(j['authoritative_status'] for j in parent_jobs)),
        'verified_parent_shards': reference['verified_shards'], 'verified_parent_games': reference['verified_games'],
        'parent_complete_cells': len(reference['complete_cells']),
        'parent_development_point_deficits': reference['development_point_deficits'],
        'gradients': False, 'reserved_final_seeds_used': False, 'qualification_eligible': False}
    write(strong/'policy-iteration-wave3-checkpoint-v2.json', result)
    print(result, flush=True)


if __name__ == '__main__':
    main()
