"""Record engineering proof, not candidate selection or reserved admission."""
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
from unittest.mock import patch

from huggingface_hub import HfApi
import prepare_selected_public_policy_final_v1 as prep
from policy_iteration_evidence_archive import upload_evidence

ROOT = prep.ROOT
OUT = ROOT/'ai/runs/selected-public-policy-final-preparation-preflight-v1'
REPORT = ROOT/'ai/strong/selected-public-policy-final-preparation-preflight-v1.json'
ARCHIVE = ROOT/'ai/runs/selected-public-policy-final-preparation-evidence-v1'
DESCRIPTOR = ROOT/'ai/strong/selected-public-policy-final-preparation-evidence-v1.json'


def main():
    assert all(not p.exists() for p in (OUT, REPORT, ARCHIVE, DESCRIPTOR,
        ARCHIVE.with_suffix('.tgz'), ARCHIVE.with_suffix('.intent.json'))), 'Inspect prior engineering archive outcome'
    assert not prep.OUT.exists(), 'Actual candidate preparation must remain absent'
    owner = prep.read(ROOT/prep.selection.OWNER)
    process = Path('/proc')/str(owner['pid'])
    assert owner['pid'] == 3788704 and process.is_dir()
    assert 'coordinate-current-auction-network-resume-v1.py --start-reviewed' in (process/'cmdline').read_text().replace('\0', ' ')
    assert (process/'stat').read_text().split()[2] != 'Z'
    prep.selection.pinned_files(ROOT, owner['code_hashes'])
    log = ROOT/'ai/runs/selected-public-policy-final-preparation-tests-v1-final.log'
    assert 'Ran 16 tests' in log.read_text() and log.read_text().rstrip().endswith('OK')
    paths = [Path(__file__).resolve(), Path(prep.__file__).resolve(), Path(prep.selection.__file__).resolve(),
             Path(prep.source_builder.__file__).resolve(), log,
             ROOT/'ai/runs/selected-public-policy-final-preparation-tests-v1-first.log']
    paths += [ROOT/'ai/strong'/name for name in (
        'test_prepare_selected_public_policy_final_v1.py', 'current-auction-grid-source-v1.json',
        'current-auction-confirmation-protocol-v1.json', 'final-protocol-multiplayer.json',
        'public_policy_final_audit_v1.py', 'public_policy_final_contract_v1.py',
        'selected_public_policy_final_dispatch_v1.py', 'selected_public_policy_final_collection_v1.py',
        'selected_public_policy_final_streaming_v1.py', 'public_policy_selected_final_job_v1.py',
        'manage-current-auction-runtime-v1.py', 'policy_iteration_evidence_archive.py',
        'current-auction-final-selection-evidence-v1.json', 'selected-public-policy-final-timeout-evidence-v2.json',
        'current-full-serving-results-evidence-v1.json', 'current-engine-export-evidence-v1.json')]
    pins = {str(p.relative_to(ROOT)): prep.digest(p) for p in paths}
    OUT.mkdir()
    prep.durable_write(OUT/'owner-state-observed.json', owner, exclusive=True)
    prep.durable_write(OUT/'intent.json', {'stage': 'engineering_preflight_only',
        'started_at': prep.now(), 'input_hashes': pins, 'automatic_retries': False}, exclusive=True)
    with patch.object(prep.selection, 'read', wraps=prep.selection.read) as reads, \
         patch.object(prep, 'HfApi', side_effect=AssertionError('No preparation API call permitted')) as api:
        try:
            prep.prepare(OUT/'NO-ACTUAL-SELECTION-REVIEW.json')
        except ValueError as error:
            rejection = str(error)
        else:
            raise AssertionError('Incomplete actual study admitted candidate preparation')
        assert rejection == 'Wait for all original confirmation jobs before selection'
        reads.assert_called_once_with(ROOT/prep.selection.OWNER); api.assert_not_called()
    assert not prep.OUT.exists()
    prep.selection.pinned_files(ROOT, pins); prep.selection.pinned_files(ROOT, owner['code_hashes'])
    assert process.is_dir() and (process/'stat').read_text().split()[2] != 'Z'
    report = {'passed': True, 'created_at': prep.now(), 'tests': 16,
        'scope': 'Engineering proof only. Positive selection/artifact identities and transport are synthetic in tests; real controls, schedule, archives and release verification are exercised. Actual incomplete study rejected before outcomes or preparation API calls.',
        'actual_rejection': rejection, 'actual_gate_read_calls': 1, 'partial_outcomes_opened': 0,
        'actual_preparation_directory_created': False, 'actual_source_published': False,
        'synthetic_unchanged_schedule': {'jobs': 320, 'games': 20160},
        'synthetic_tests_cover': ['complete selected-arm costs and provenance', 'measured workers and memory/timeout limits',
            'candidate/selection archive binding', 'every job control and worker allocation',
            'unknown selection/source upload outcomes', 'failed upload verification retains original receipt',
            'existing archive preservation', 'private evidence repositories', 'immutable downloaded source verification'],
        'input_hashes': pins, 'owner_snapshot_sha256': prep.digest(OUT/'owner-state-observed.json'),
        'owner_pid': owner['pid'], 'owner_verified_live': True, 'unchanged_owner_pins': len(owner['code_hashes']),
        'owner_checkpoint': {k: owner[k] for k in ('updated_at', 'stage', 'verified_jobs', 'submitted_jobs')},
        'new_hf_jobs_by_this_work': 0, 'new_games': 0, 'new_policy_calls': 0,
        'candidate_selected': False, 'final_launch_admitted': False, 'qualified': False,
        'reserved_final_seeds_used': False,
        'previous_goal_turn_classification': 'no_progress',
        'previous_goal_turn_note': 'The intervening engine recap was informational. The earlier research turn completed the timeout fix. This turn revalidated the live original owner and completed preparation workflow engineering.',
        'current_goal_turn_classification': 'progress', 'goal_status': 'active'}
    prep.durable_write(REPORT, report, exclusive=True)
    repo = 'coyotte508/powergrid-ai-germany-v1'; api = HfApi()
    assert api.model_info(repo).private and not api.file_exists(repo, 'archives/'+ARCHIVE.name+'.tgz')
    sources = {ROOT/name for name in pins} | {REPORT, OUT/'owner-state-observed.json', OUT/'intent.json'}
    ARCHIVE.mkdir(); manifest = {}
    for path in sorted(sources):
        assert path.is_file() and not path.is_symlink()
        name = str(path.relative_to(ROOT)); destination = ARCHIVE/name; destination.parent.mkdir(parents=True, exist_ok=True)
        with path.open('rb') as src, destination.open('xb') as dst: shutil.copyfileobj(src, dst)
        assert prep.digest(destination) == prep.digest(path); manifest[name] = prep.digest(path)
    prep.durable_write(ARCHIVE/'manifest.json', manifest, exclusive=True)
    prep.durable_write(ARCHIVE.with_suffix('.intent.json'), {'stage': 'upload_intent', 'report_sha256': prep.digest(REPORT)}, exclusive=True)
    evidence = upload_evidence(ARCHIVE)
    prep.durable_write(DESCRIPTOR, {'complete': True, 'archive': evidence, 'report_sha256': prep.digest(REPORT),
        'tests': 16, 'candidate_selected': False, 'final_launch_admitted': False,
        'qualified': False, 'reserved_final_seeds_used': False}, exclusive=True)
    prep.durable_write(ARCHIVE.with_suffix('.intent.json'), {'stage': 'uploaded_download_verified',
        'archive': evidence, 'descriptor_sha256': prep.digest(DESCRIPTOR)})
    print(json.dumps({'passed': True, 'tests': 16, 'actual_incomplete_study_rejected': True, 'archive': evidence}), flush=True)


if __name__ == '__main__': main()
