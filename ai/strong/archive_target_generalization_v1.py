"""Retain completed sealed evidence and the original HF learner-probe recovery."""
from pathlib import Path
import re
import shutil

from huggingface_hub import HfApi
from policy_iteration_evidence_archive import upload_evidence
from run_sealed_target_quality_v1 import read, save, digest, now

ROOT = Path(__file__).resolve().parents[2]
NAME = 'target-generalization-evidence-v1'
DIRECTORY = ROOT/'ai/runs'/NAME
INTENT = ROOT/'ai/runs'/f'{NAME}.intent.json'
DESCRIPTOR = ROOT/'ai/strong'/f'{NAME}.json'
REPO = 'coyotte508/powergrid-ai-germany-v1'


def main():
    assert not any(p.exists() for p in (DIRECTORY, INTENT, DESCRIPTOR, DIRECTORY.with_suffix('.tgz'))), 'Inspect prior archive intents/outcomes before retry'
    assert HfApi().model_info(REPO).private
    original = ROOT/'ai/runs/sealed-target-quality-v1/collected'
    assert read(original/'state.json')['complete']
    assert read(ROOT/'ai/strong/sealed-target-quality-complete-v1.json')['rollouts'] == 6160
    files = [p for p in original.rglob('*') if p.is_file()]
    files += [ROOT/'ai'/name for name in ('RESUME.md', 'SEALED-TARGET-DIAGNOSTIC-2026-10-30.md', 'TARGET-GENERALIZATION-2026-10-31.md')]
    names = ['sealed-target-quality-complete-v1.json', 'sealed-target-quality-protocol-v1.json',
        'sealed-target-quality-launch-v1.json', 'sealed-target-quality-start-evidence-v1.json',
        'target-generalization-analysis-v1.json', 'analyze_target_generalization_v1.py',
        'target_learner_probe_v1.py', 'manage_target_learner_probe_v1.py', 'test_target_learner_probe_v1.py',
        'target-learner-probe-design-v1.json', 'target-learner-probe-source-v1.json', 'target-learner-probe-launch-v1.json',
        'archive_target_generalization_v1.py', 'policy_iteration_evidence_archive.py',
        'run_sealed_target_quality_v1.py', 'manage_sealed_target_quality_v1.py', 'test_sealed_target_quality_v1.py',
        'nomination-discount-training-evidence-v1.json']
    files += [ROOT/'ai/strong'/n for n in names]
    run = ROOT/'ai/runs/target-learner-probe-v1'
    files += [run/n for n in ('upload-intent.json', 'upload-commit.json', 'launch-intent.json', 'effective-configuration.json', 'ledger-entry.json')]
    for folder in sorted((ROOT/'ai/runs/nomination-discount-training-collected-v1').iterdir()):
        if (folder/'raw/history.json').exists():
            files += [folder/n for n in ('raw/history.json', 'raw/training.json', 'raw/manifest.json', 'receipt.json', 'audit.json')]
    assert len(files) == len(set(files))
    for path in files:
        assert path.is_file() and not path.is_symlink()
        assert not re.search(rb'hf_[A-Za-z0-9]{25,}', path.read_bytes()), 'Credential-pattern scan failed'
    DIRECTORY.mkdir()
    for path in files:
        target = DIRECTORY/path.relative_to(ROOT); target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
    save(DIRECTORY/'manifest.json', {str(p.relative_to(DIRECTORY)): digest(p) for p in DIRECTORY.rglob('*') if p.is_file()})
    save(INTENT, {'created_at': now(), 'repo': REPO, 'archive_path': f'archives/{NAME}.tgz',
        'manifest_sha256': digest(DIRECTORY/'manifest.json'), 'automatic_retries': False,
        'scope': 'Completed original 6160-rollout assessment and original HF learner-probe launch; training outputs are not yet part of this snapshot.'})
    outcome = upload_evidence(DIRECTORY, REPO); save(DESCRIPTOR, outcome)
    print(outcome, flush=True)


if __name__ == '__main__': main()
