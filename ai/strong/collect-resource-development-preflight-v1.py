"""Archive the unlaunched protocol, checker tests and exact existing inputs."""
from pathlib import Path
import shutil

from strategic_collection import ROOT, read, write, digest
from resource_development_v1 import PROTOCOL, CURRENT_PLAN, CURRENT_PROTOCOL, verify_pins, case_rows
from policy_iteration_evidence_archive import upload_evidence


def main():
    protocol = read(PROTOCOL)
    verify_pins(protocol)
    base = ROOT / 'ai/runs/resource-development-preflight-v1'
    log = base / 'all-tests-v1.log'
    text = log.read_text()
    assert 'Ran 11 tests in ' in text and text.endswith('\nOK\n')
    assert text.count(' ... ok\n') == 11
    paths = [PROTOCOL, CURRENT_PLAN, CURRENT_PROTOCOL, Path(__file__), log]
    paths += [ROOT / 'ai/strong' / name for name in [
        'resource_development_v1.py', 'resource_policy_verification_v1.py',
        'test_resource_development_v1.py', 'test_resource_policy_verification_v1.py',
        'policy_iteration_evidence_archive.py']]
    paths += [ROOT / path for path in {
        **read(CURRENT_PLAN)['dependency_hashes'],
        **protocol['source_overlays'], **protocol['evidence_hashes']}]
    atomic = ROOT / 'ai/runs/resource-replanning-v1'
    paths += [atomic / path for path in ['checks-v2/turns.jsonl', 'checks-v2/cap.json',
        'replays/6p-recharged-sealed-economic-slow-root.json', 'selection.json', 'preparation.json']]
    paths += list((atomic / 'games').glob('*/*.json')) + list((atomic / 'games').glob('*/*.jsonl'))
    paths += list((ROOT / 'ai/runs/population-policy-arena-controls-v1').glob('*/*'))
    paths += [ROOT / 'ai/runs' / name for name in [
        'resource-turn-search-v1/trained/prefix.json', 'resource-turn-search-v1/selection.json',
        'trained-hybrid-probe-v2/selected-fixtures.json', 'population-policy-trained-probe-v1/results.jsonl']]
    paths += list(base.glob('*.log'))
    files = sorted({path for path in paths if path.is_file()})
    input_hashes = {str(p.relative_to(ROOT)): digest(p) for p in files}
    assessment = {
        'status': 'verified_resource_ablation_preflight_not_launched',
        'protocol_sha256': digest(PROTOCOL),
        'tests': 11, 'real_phase_decisions': 112, 'real_full_game_decisions': 540,
        'checked_resource_rollouts': 11900,
        'unchanged_complete_control_games': 80, 'unchanged_control_decisions': 10207,
        'composed_existing_auction_building_envelopes': 8,
        'eight_world_resource_plan_checked': True,
        'single_pass_bundle_searches_checked': 1,
        'corrupt_decision_mutations_rejected': 24,
        'consistent_wrong_selection_rejected': True,
        'corrupt_complete_report_mutations_rejected': 4,
        'weakened_protocol_mutations_rejected': 20, 'stale_pins_rejected': 2,
        'deliberate_cap_rejected_for_strength': True,
        'candidate_shard_counts': {str(size): len(case_rows(protocol, size)) for size in [1, 2, 4]},
        'planned_games': 3360, 'planned_arms': ['filter', 'resource-filter'],
        'runtime_admitted': False, 'source_uploaded_for_jobs': False,
        'current_hybrid_screen_unchanged': True,
        'input_hashes': input_hashes,
        'limits': [
            'Receipt consistency and recomputed scores do not independently prove engine legality or model inference. Earlier exact replays provide engineering evidence on the four existing games.',
            'No new full paired resource-specific report exists yet. The complete-game adapter matches the existing 80 base-policy controls; resource decisions are checked separately on the existing four smokes and 23 turns.',
            'Eight wrapped auction/building receipts test composition only, not newly executed resource-combined games.',
            'Protocol planning and integrity checks provide no new playing-strength estimate. Four-deal future intervals remain coarse.',
            'No resource pilot or strength job may launch until the active fixed comparison finishes. Source/job packaging and measured resource-specific runtime admission remain to be done.'],
        'new_hf_jobs': 0, 'new_games': 0, 'gradients': False,
        'qualification_eligible': False, 'reserved_final_seeds_used': False}
    write(base / 'assessment.json', assessment)
    out = ROOT / 'ai/runs/resource-development-preflight-evidence-v1'
    out.mkdir(exist_ok=False)
    for source in files:
        dest = out / source.relative_to(ROOT)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, dest)
        assert digest(dest) == input_hashes[str(source.relative_to(ROOT))]
    write(out / 'assessment.json', assessment)
    write(out / 'manifest.json', {str(p.relative_to(out)): digest(p) for p in out.rglob('*') if p.is_file()})
    receipt = upload_evidence(out)
    descriptor = {**assessment, **receipt}
    del descriptor['input_hashes']
    write(ROOT / 'ai/strong/resource-development-preflight-evidence-v1.json', descriptor)
    print(receipt, flush=True)


if __name__ == '__main__':
    main()
