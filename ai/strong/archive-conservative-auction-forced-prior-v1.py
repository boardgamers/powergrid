"""Archive verified runtime-recovery evidence, referencing immutable originals.

No job submission. Inspect existing intent/outcome before retrying an upload.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil

from huggingface_hub import HfApi
from policy_iteration_evidence_archive import upload_evidence
from strategic_collection import digest, read

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT/'ai/runs/conservative-auction-forced-prior-evidence-v1'
INTENT = OUT.with_suffix('.intent.json')
DEST = ROOT/'ai/strong/conservative-auction-forced-prior-evidence-v1.json'
RECOVERY = ROOT/'ai/runs/conservative-auction-forced-prior-v1'
REPO = 'coyotte508/powergrid-ai-germany-v1'


def write(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2, allow_nan=False); stream.write('\n')


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--archive', action='store_true', required=True); parser.parse_args()
    assert not any(p.exists() for p in (OUT, OUT.with_suffix('.tgz'), INTENT, DEST)), 'Inspect previous archive intent/outcome first'
    api = HfApi(); assert api.repo_info(REPO).private
    assert 'archives/'+OUT.name+'.tgz' not in api.list_repo_files(REPO), 'Remote archive already exists; recover its outcome'
    result_path = ROOT/'ai/strong/conservative-auction-forced-prior-results-v1.json'
    report = read(result_path)
    assert report['audit'] == read(RECOVERY/'audit.json') and report['audit']['complete']
    assert report['audit']['counts']['rollouts'] == 96 and report['audit']['counts']['rollout_caps'] == 0
    assert report['new_hf_jobs_submitted'] == report['new_strength_games'] == report['gradient_updates'] == 0
    assert report['grid_admitted'] is report['qualified'] is report['reserved_final_seeds_used'] is False
    paths = {result_path}
    for name in ('RESUME.md', 'CONSERVATIVE-AUCTION-RECOVERY-2026-10-27.md'):
        paths.add(ROOT/'ai'/name)
    for name in ('experiments.json', 'replay-conservative-auction-failure-v1.py',
                 'diagnose-conservative-auction-request-v1.py', 'verify-conservative-auction-forced-prior-v1.py',
                 'archive-conservative-auction-forced-prior-v1.py', 'opponent_surrogate_policy_v1.py',
                 'surrogate-opponent-continuations-v1.cjs', 'test_opponent_surrogate_policy_v1.py',
                 'test-surrogate-opponent-continuations-v1.cjs', 'fixtures/conservative-auction-forced-prior-v1.json',
                 'conservative-auction-runtime-source-v1.json', 'conservative-auction-runtime-results-v1.json',
                 'paused-handoff-archive-2026-10-25.json', 'policy_iteration_evidence_archive.py'):
        paths.add(ROOT/'ai/strong'/name)
    paths.update(p for p in (ROOT/'ai/runs/conservative-auction-failure-diagnosis-v1').iterdir() if p.is_file())
    paths.update(p for p in RECOVERY.iterdir() if p.is_file())
    paths.update((RECOVERY/'logs').glob('*.log'))
    paths.add(RECOVERY/'artifact/manifest.json'); paths.add(RECOVERY/'artifact/policy.json')
    paths.update((RECOVERY/'artifact/policies').glob('*.json'))
    hashes = {str(p.relative_to(ROOT)): digest(p) for p in sorted(paths)}
    for name, sha in report['tests']['logs'].items(): assert hashes[name] == sha
    assert digest(RECOVERY/'response-5-21.json') == report['audit']['response_sha256']
    for name, change in report['derivation']['changed_runtime_files'].items():
        assert hashes[name] == change['new_sha256']
    write(INTENT, {'created_at': datetime.now(timezone.utc).isoformat(), 'repo': REPO,
                   'archive_path': 'archives/'+OUT.name+'.tgz', 'files': hashes,
                   'new_hf_jobs_submitted': 0})
    OUT.mkdir()
    for name, sha in hashes.items():
        target = OUT/name; target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT/name, target); assert digest(target) == sha
    write(OUT/'manifest.json', hashes)
    print(json.dumps({'stage': 'uploading_evidence_only', 'files': len(hashes)+1}), flush=True)
    evidence = upload_evidence(OUT, repo=REPO)
    descriptor = {'complete': True, 'scope': report['audit']['scope'],
                  'archive': evidence, 'results_sha256': digest(result_path),
                  'derivation': report['derivation'], 'original_run': report['original_run'],
                  'audit_counts': report['audit']['counts'],
                  'new_hf_jobs_submitted': 0, 'new_strength_games': 0, 'gradient_updates': 0,
                  'grid_admitted': False, 'qualified': False, 'reserved_final_seeds_used': False}
    write(DEST, descriptor); print(json.dumps(evidence), flush=True)


if __name__ == '__main__': main()
