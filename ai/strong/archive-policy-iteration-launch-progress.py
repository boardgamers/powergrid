"""Snapshot confirmed submission handles while the guarded launcher is active."""
from collections import Counter
from datetime import datetime, timezone
import json
import shutil
from huggingface_hub import HfApi, hf_hub_download
from strategic_collection import ROOT, read, write, digest


def main():
    protocol = ROOT/'ai/strong/policy-iteration-labels-protocol-v2.json'
    p = read(protocol)
    source = read(ROOT/'ai/strong/policy-iteration-labels-source-v2.json')
    expected = {s['id']: s for s in p['shards']}
    guards, incomplete_reads, stages = [], 0, Counter()
    for path in sorted((ROOT/'ai/runs/policy-iteration-labels-launches-v2').glob('*.json')):
        try:
            row = read(path)
        except json.JSONDecodeError:
            incomplete_reads += 1  # Writer may be between creating and filling its current guard.
            continue
        stages[row['stage']] += 1
        assert row['stage'] in ['launched', 'launch_intent'], 'Reconcile the failed submission first'
        if row['stage'] != 'launched':
            continue
        assert row['source'] == source and row['protocol_sha256'] == digest(protocol)
        assert row['shard'] == expected[row['shard']['id']]
        guards.append(row)
    remaining = [g for g in guards if g['wave'] == 'remaining']
    assert 0 < len(remaining) < 888 and len(guards)-len(remaining) == 60
    assert len({g['job_id'] for g in guards}) == len(guards)
    report = {'checked_at': datetime.now(timezone.utc).isoformat(), 'confirmed_jobs': len(guards),
              'confirmed_remaining_jobs': len(remaining), 'planned_remaining_jobs': 888,
              'observed_guard_stages': dict(stages), 'incomplete_guard_reads': incomplete_reads,
              'launcher_complete': False, 'qualification_eligible': False}
    out = ROOT/'ai/runs/policy-iteration-labels-remaining-launch-progress-v2'
    out.mkdir(exist_ok=False)
    (out/'guards').mkdir()
    for row in guards:
        write(out/'guards'/(row['shard']['id'] + '.json'), row)
    for file in ['policy-iteration-labels-source-v2.json', 'policy-iteration-labels-protocol-v2.json',
                 'policy-iteration-labels-first-wave-evidence-v2.json', 'manage-policy-iteration-labels.py',
                 'archive-policy-iteration-launch-progress.py']:
        shutil.copy2(ROOT/'ai/strong'/file, out/file)
    write(out/'snapshot.json', report)
    write(out/'manifest.json', {str(f.relative_to(out)): digest(f) for f in out.rglob('*') if f.is_file()})
    repo, prefix = 'coyotte508/powergrid-ai-germany-v1', 'runs/' + out.name
    commit = HfApi().upload_folder(repo_id=repo, folder_path=out, path_in_repo=prefix)
    sha = digest(out/'manifest.json')
    assert digest(hf_hub_download(repo, prefix+'/manifest.json', revision=commit.oid)) == sha
    descriptor = {**report, 'repo': repo, 'revision': commit.oid, 'prefix': prefix, 'manifest_sha256': sha}
    write(ROOT/'ai/strong'/(out.name + '.json'), descriptor)
    print(descriptor, flush=True)


if __name__ == '__main__':
    main()
