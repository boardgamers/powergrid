"""Record and archive selection-gate engineering checks; never select a policy.

Exercise the incomplete-owner rejection on the real live study and the technical
checks on saved, completed target/export evidence. No new games or inference.
"""
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
from unittest.mock import patch

from huggingface_hub import HfApi
import current_auction_final_selection_v1 as gate
from policy_iteration_evidence_archive import upload_evidence
from selected_public_policy_final_dispatch_v1 import durable_write

ROOT = gate.ROOT
STRONG = ROOT / 'ai/strong'
RUNS = ROOT / 'ai/runs'
OUT = RUNS / 'current-auction-final-selection-preflight-v1'
REPORT = STRONG / 'current-auction-final-selection-preflight-v1.json'
ARCHIVE_OUT = RUNS / 'current-auction-final-selection-evidence-v1'
DESCRIPTOR = STRONG / 'current-auction-final-selection-evidence-v1.json'


def main():
    assert all(not p.exists() for p in (OUT, REPORT, ARCHIVE_OUT, DESCRIPTOR,
        ARCHIVE_OUT.with_suffix('.tgz'), ARCHIVE_OUT.with_suffix('.intent.json'))), 'Inspect prior preflight/archive outcome; do not rerun'
    owner = gate.read(ROOT / gate.OWNER)
    process = Path('/proc') / str(owner['pid'])
    assert owner['pid'] == 3788704 and process.is_dir()
    command = (process / 'cmdline').read_text().replace('\0', ' ')
    assert 'coordinate-current-auction-network-resume-v1.py --start-reviewed' in command
    assert (process / 'stat').read_text().split()[2] != 'Z'
    gate.pinned_files(ROOT, owner['code_hashes'])
    log = RUNS / 'current-auction-final-selection-tests-v1-first.log'
    assert 'Ran 13 tests' in log.read_text() and log.read_text().rstrip().endswith('OK')
    inputs = [Path(__file__).resolve(), STRONG / 'current_auction_final_selection_v1.py',
        STRONG / 'test_current_auction_final_selection_v1.py', log,
        STRONG / 'current-auction-confirmation-protocol-v1.json', STRONG / 'final-protocol-multiplayer.json',
        STRONG / 'current_auction_confirmation_analysis_v1.py',
        STRONG / 'compare-current-auction-confirmation-parallel-v1.py',
        STRONG / 'public_policy_final_audit_v1.py', STRONG / 'public_policy_final_contract_v1.py',
        STRONG / 'current-full-serving-results-evidence-v1.json', STRONG / 'current-engine-export-evidence-v1.json']
    inputs += [ROOT / p for p in (gate.TECHNICAL, gate.BINDING, gate.EXPORT, gate.EXPORT_AUDIT)]
    pins = {str(p.relative_to(ROOT)): gate.digest(p) for p in inputs}
    OUT.mkdir()
    durable_write(OUT / 'owner-state-observed.json', owner, exclusive=True)
    durable_write(OUT / 'intent.json', {'stage': 'selection_gate_engineering_check',
        'started_at': datetime.now(timezone.utc).isoformat(), 'input_hashes': pins,
        'automatic_retries': False, 'candidate_selection_authorized_by_this_check': False}, exclusive=True)
    with patch.object(gate, 'read', wraps=gate.read) as reads:
        try:
            gate.verify(OUT / 'NO-ACTUAL-SELECTION-REVIEW.json')
        except ValueError as error:
            rejection = str(error)
        else:
            raise AssertionError('Incomplete study did not block candidate selection')
        assert rejection == 'Wait for all original confirmation jobs before selection'
        reads.assert_called_once_with(ROOT / gate.OWNER)
    values = [gate.read(ROOT / p) for p in (gate.TECHNICAL, gate.BINDING, gate.EXPORT, gate.EXPORT_AUDIT)]
    technical, binding, export, audit = values
    artifact = RUNS / 'current-auction-grid-prepared-v1/source/artifact'
    identities = {arm: gate.artifact_identity(artifact, f'policies/{arm}.json') for arm in gate.statistics.ARMS}
    gate.technical_gate(*values, pins, identities)
    gate.pinned_files(ROOT, export['input_hashes'])
    target = RUNS / 'current-full-serving-8840u-collected-v1'
    assert gate.digest(target / 'output/receipts.jsonl') == binding['target_receipts_sha256']
    assert gate.digest(target / 'output/status.json') == technical['status_sha256']
    assert gate.read(target / 'audit.json') == technical
    assert gate.digest(RUNS / 'current-engine-export-parity-v1/receipts.jsonl') == export['receipts_sha256']
    gate.pinned_files(ROOT, pins); gate.pinned_files(ROOT, owner['code_hashes'])
    assert process.is_dir() and (process / 'stat').read_text().split()[2] != 'Z'
    report = {'passed': True, 'completed_at': datetime.now(timezone.utc).isoformat(), 'unit_tests': 13,
        'scope': 'Selection-gate engineering only. Positive confirmation cases are synthetic. Real unfinished study rejected before outcomes; existing complete technical proof accepted. No actual successful end-to-end candidate admission has occurred.',
        'incomplete_owner_rejected': rejection, 'real_gate_read_calls': 1, 'partial_game_outcomes_opened': 0,
        'existing_target_requests_checked': technical['requests'], 'native_positions_checked': export['positions'],
        'input_hashes': pins, 'owner_snapshot_sha256': gate.digest(OUT / 'owner-state-observed.json'),
        'owner_pid': owner['pid'], 'owner_verified_live': True, 'unchanged_owner_pins': len(owner['code_hashes']),
        'observed_owner_stage': owner['stage'], 'observed_audited_jobs': owner['verified_jobs'],
        'observed_submitted_jobs': owner['submitted_jobs'], 'new_games': 0, 'new_policy_calls': 0,
        'new_hf_jobs_by_this_work': 0, 'candidate_selected': False, 'final_launch_admitted': False,
        'qualified': False, 'reserved_final_seeds_used': False}
    durable_write(REPORT, report, exclusive=True)
    repo = 'coyotte508/powergrid-ai-germany-v1'; api = HfApi()
    assert api.model_info(repo).private and not api.file_exists(repo, 'archives/' + ARCHIVE_OUT.name + '.tgz')
    sources = {ROOT / n for n in pins}
    sources.update({REPORT, OUT / 'owner-state-observed.json', OUT / 'intent.json',
                    STRONG / 'policy_iteration_evidence_archive.py'})
    ARCHIVE_OUT.mkdir(); manifest = {}
    for path in sorted(sources):
        assert path.is_file() and not path.is_symlink()
        name = str(path.relative_to(ROOT)); dest = ARCHIVE_OUT / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        with path.open('rb') as src, dest.open('xb') as dst: shutil.copyfileobj(src, dst)
        assert gate.digest(dest) == gate.digest(path); manifest[name] = gate.digest(path)
    durable_write(ARCHIVE_OUT / 'manifest.json', manifest, exclusive=True)
    durable_write(ARCHIVE_OUT.with_suffix('.intent.json'), {'stage': 'upload_intent', 'report_sha256': gate.digest(REPORT)}, exclusive=True)
    evidence = upload_evidence(ARCHIVE_OUT)
    durable_write(DESCRIPTOR, {'complete': True, 'archive': evidence, 'preflight_sha256': gate.digest(REPORT),
        'tests': 13, 'candidate_selected': False, 'final_launch_admitted': False, 'qualified': False,
        'reserved_final_seeds_used': False}, exclusive=True)
    durable_write(ARCHIVE_OUT.with_suffix('.intent.json'), {'stage': 'uploaded_download_verified',
        'archive': evidence, 'descriptor_sha256': gate.digest(DESCRIPTOR)})
    print(json.dumps({'passed': True, 'tests': 13, 'incomplete_study_rejected': True,
        'existing_technical_proof_passed': True, 'archive': evidence}), flush=True)


if __name__ == '__main__': main()
