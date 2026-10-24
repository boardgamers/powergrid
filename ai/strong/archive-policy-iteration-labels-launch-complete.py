"""Persist all exact handles after the remaining-wave launcher has finished."""
from collections import Counter
import shutil
from huggingface_hub import HfApi, hf_hub_download
from strategic_collection import ROOT, read, write, digest


def main():
    p = read(ROOT/'ai/strong/policy-iteration-labels-protocol-v2.json')
    source = read(ROOT/'ai/strong/policy-iteration-labels-source-v2.json')
    expected = {s['id']: s for s in p['shards']}
    guards = [read(f) for f in sorted((ROOT/'ai/runs/policy-iteration-labels-launches-v2').glob('*.json'))]
    status = read(ROOT/'ai/strong/policy-iteration-labels-status-v2.json')
    assert len(guards) == len(expected) == len(status['jobs']) == 948
    assert len({g['job_id'] for g in guards}) == 948
    assert {g['shard']['id'] for g in guards} == set(expected)
    assert Counter(g['wave'] for g in guards) == {'first': 60, 'remaining': 888}
    for guard in guards:
        assert guard['stage'] == 'launched' and guard['source'] == source
        assert guard['shard'] == expected[guard['shard']['id']]
        assert guard['protocol_sha256'] == source['protocol_sha256']
    assert {g['job_id'] for g in guards} == {j['job_id'] for j in status['jobs']}
    out = ROOT/'ai/runs/policy-iteration-labels-complete-launch-evidence-v2'
    out.mkdir(exist_ok=False)
    (out/'guards').mkdir()
    for guard in guards:
        write(out/'guards'/(guard['shard']['id'] + '.json'), guard)
    for file in ['policy-iteration-labels-status-v2.json', 'policy-iteration-labels-source-v2.json',
                 'policy-iteration-labels-protocol-v2.json', 'policy-iteration-labels-first-wave-evidence-v2.json',
                 'manage-policy-iteration-labels.py', 'archive-policy-iteration-labels-launch-complete.py']:
        shutil.copy2(ROOT/'ai/strong'/file, out/file)
    write(out/'manifest.json', {str(f.relative_to(out)): digest(f) for f in out.rglob('*') if f.is_file()})
    repo, prefix = 'coyotte508/powergrid-ai-germany-v1', 'runs/' + out.name
    commit = HfApi().upload_folder(repo_id=repo, folder_path=out, path_in_repo=prefix)
    sha = digest(out/'manifest.json')
    assert digest(hf_hub_download(repo, prefix+'/manifest.json', revision=commit.oid)) == sha
    descriptor = {'repo': repo, 'revision': commit.oid, 'prefix': prefix, 'manifest_sha256': sha,
                  'jobs_submitted': 948, 'remaining_jobs_submitted': 888, 'root_mode_pairs': 33840,
                  'status_checked_at': status['checked_at'], 'status_counts': status['status_counts'],
                  'full_data_complete': False, 'gradients': False, 'qualification_eligible': False}
    write(ROOT/'ai/strong'/(out.name + '.json'), descriptor)
    print(descriptor, flush=True)


if __name__ == '__main__':
    main()
