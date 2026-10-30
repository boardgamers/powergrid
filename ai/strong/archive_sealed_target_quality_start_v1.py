"""Back up completed pilot evidence and the original finite assessment launch."""
from pathlib import Path
import re
import shutil

from huggingface_hub import HfApi
from policy_iteration_evidence_archive import upload_evidence
from run_sealed_target_quality_v1 import read, save, digest, now

ROOT = Path(__file__).resolve().parents[2]
NAME = 'sealed-target-quality-start-evidence-v1'
DIRECTORY = ROOT/'ai/runs'/NAME
DESCRIPTOR = ROOT/'ai/strong'/f'{NAME}.json'
INTENT = ROOT/'ai/runs'/f'{NAME}.intent.json'
REPO = 'coyotte508/powergrid-ai-germany-v1'


def main():
    assert not DESCRIPTOR.exists() and not INTENT.exists() and not DIRECTORY.exists()
    assert not DIRECTORY.with_suffix('.tgz').exists(), 'Inspect prior archive/remote outcome before retry'
    assert HfApi().model_info(REPO).private, 'Evidence must remain private'
    pilot = ROOT/'ai/runs/sealed-target-pilot-v1/collected'
    assert read(pilot/'state.json')['complete']
    files = [p for p in pilot.rglob('*') if p.is_file()]
    run = ROOT/'ai/runs/sealed-target-quality-v1'
    files += list((run/'package').glob('*'))
    files += [run/n for n in ('remote-preflight.json', 'package-receipt.json', 'launch-intent.json', 'last-status.json', 'ledger-entry.json')]
    names = ['run_sealed_target_quality_v1.py', 'manage_sealed_target_quality_v1.py',
        'test_sealed_target_quality_v1.py', 'archive_sealed_target_quality_start_v1.py',
        'run_sealed_target_pilot_v1.py', 'manage_sealed_target_pilot_v1.py', 'test_sealed_target_pilot_v1.py',
        'policy_iteration_evidence_archive.py', 'sealed-target-pilot-complete-v1.json',
        'sealed-target-pilot-cost-v1.json', 'sealed-target-pilot-launch-v1.json',
        'sealed-target-diagnostic-evidence-v1.json', 'sealed-target-quality-protocol-v1.json',
        'sealed-target-quality-launch-v1.json', 'node-runtime-cache-v1.json']
    files += [ROOT/'ai/strong'/n for n in names]
    files += [ROOT/'ai/RESUME.md', ROOT/'ai/SEALED-TARGET-DIAGNOSTIC-2026-10-30.md']
    assert len(files) == len(set(files))
    for path in files:
        assert path.is_file() and not path.is_symlink()
        assert not re.search(rb'hf_[A-Za-z0-9]{25,}', path.read_bytes()), 'Credential-pattern scan failed'
    DIRECTORY.mkdir()
    for path in files:
        target = DIRECTORY/path.relative_to(ROOT); target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
    manifest = {str(p.relative_to(DIRECTORY)): digest(p) for p in DIRECTORY.rglob('*') if p.is_file()}
    save(DIRECTORY/'manifest.json', manifest)
    save(INTENT, {'created_at': now(), 'repo': REPO, 'archive_path': f'archives/{NAME}.tgz',
        'manifest_sha256': digest(DIRECTORY/'manifest.json'), 'automatic_retries': False,
        'scope': 'Complete original 440-rollout pilot plus original 6160-rollout assessment launch/recovery; no new training or final seeds.'})
    outcome = upload_evidence(DIRECTORY, REPO)
    save(DESCRIPTOR, outcome)
    print(outcome, flush=True)


if __name__ == '__main__': main()
