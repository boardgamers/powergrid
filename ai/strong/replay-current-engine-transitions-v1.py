"""Replay 33 fixed historical games through frozen and current engines.

No new policy inference, search, strength games, training, or HF jobs.
"""
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess

from public_policy_development_job_v1 import digest, read

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'ai/runs/current-engine-transitions-v1'
RESULT = ROOT / 'ai/strong/current-engine-transitions-results-v1.json'
ENGINE = ROOT / 'ai/runs/current-engine-compatibility-v1'
ARTIFACT = ROOT / 'ai/runs/resource-turn-full-artifact-v4'
RECORDED = ROOT / 'ai/runs/resource-turn-full-integration-v2'


def save(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write('\n')


def main():
    assert not OUT.exists() and not RESULT.exists(), 'Inspect prior replay before retrying'
    design = read(ENGINE / 'design.json')
    build = read(ENGINE / 'build.json')
    proof = read(ROOT / 'ai/strong/current-engine-compatibility-evidence-v1.json')
    assert proof['design_sha256'] == digest(ENGINE / 'design.json')
    assert proof['build_sha256'] == digest(ENGINE / 'build.json')
    assert all(digest(ENGINE / 'source/engine' / n) == h for n, h in build['compiled_files'].items())
    assert digest(ARTIFACT / 'manifest.json') == design['frozen_artifact_manifest_sha256']
    assert all(digest(ARTIFACT / n) == h for n, h in read(ARTIFACT / 'manifest.json').items())
    prior = read(RECORDED / 'assessment.json')
    assert digest(RECORDED / 'assessment.json') == design['recorded_assessment_sha256']
    assert prior['passed']
    games = []
    inputs = {}
    for name, sha in sorted(design['recorded_inputs'].items()):
        decisions = ROOT / name
        assert digest(decisions) == sha
        episode = int(decisions.stem.split('-')[1])
        record = decisions.with_name(f'game-{episode}.json')
        record_name = str(record.relative_to(ROOT))
        assert digest(record) == prior['output_hashes'][str(record.relative_to(RECORDED))]
        data = read(record)
        assert data['decision_receipt_sha256'] == sha and data['recorded_reference_checked']
        opponent = decisions.parent.name.split('-')[-1]
        assert opponent in ('economic', 'legacy')
        games.append({'decisions': name, 'record': record_name, 'opponent': opponent})
        inputs[name] = sha
        inputs[record_name] = digest(record)
    assert len(games) == 33
    worker = Path(__file__).with_suffix('.cjs')
    OUT.mkdir()
    save(OUT / 'design.json', {
        'created_at': datetime.now(timezone.utc).isoformat(),
        'current_engine_commit': proof['current_engine_commit'],
        'current_engine_evidence': proof['archive'],
        'compiled_build_sha256': digest(ENGINE / 'build.json'),
        'frozen_artifact_manifest_sha256': digest(ARTIFACT / 'manifest.json'),
        'recorded_assessment_sha256': digest(RECORDED / 'assessment.json'),
        'recorded_inputs': inputs, 'games': games,
        'python_checker_sha256': digest(__file__), 'node_checker_sha256': digest(worker),
        'selection': 'Unchanged prior 33-game corpus; every recorded learner action, deterministic original economic/legacy opponent choices, all transitions and final economies.',
        'economic_comparison_exclusions': ['log', 'hiddenLog', 'poweringChoices', 'pendingMessages',
                                          'players.clockStartedAt', 'players.totalTimeUsed', 'players.availableMoves'],
        'historical_request_comparison_exclusions': ['players.clockStartedAt', 'players.totalTimeUsed',
            'players.lastMove.time', 'players.lastMove.serverTime', 'log/hiddenLog.move.time', 'log/hiddenLog.move.serverTime'],
        'initial_harness_failure_preserved': 'ai/runs/current-engine-transitions-v1-initial',
        'second_harness_failure_preserved': 'ai/runs/current-engine-transitions-v1-second',
        'move_annotation_handling': 'Derived usedPlantDiscount/fromSupply fields are not passed into either engine; resulting lastMove fields are compared, requiring independent derivation.',
        'separate_comparisons': 'Legal menus and semantic logs/hidden logs; retain ordinary move payloads, all private deck state, and all economic fields.',
        'expected_menu_difference': 'Current one-Elektro discounted nomination, if naturally encountered; old actions must remain legal.',
        'new_inference': 0, 'new_search_rollouts': 0, 'new_hf_jobs': 0,
        'new_full_game_trajectories': 0, 'qualification_eligible': False, 'reserved_final_seeds_used': False})
    with (OUT / 'replay.log').open('x') as log:
        subprocess.run(['node', str(worker), str(ROOT), str(OUT)], cwd='/tmp',
                       stdout=log, stderr=subprocess.STDOUT, check=True)
    report = read(OUT / 'assessment.json')
    assert report['passed'] and report['recorded_games'] == report['terminal_economies_exact'] == 33
    assert report['original_requests_exact'] == 3443 and report['learner_moves'] == 4720
    assert all(digest(ROOT / n) == h for n, h in inputs.items())
    save(RESULT, {**report, 'design_sha256': digest(OUT / 'design.json'),
                  'assessment_sha256': digest(OUT / 'assessment.json'),
                  'differences_sha256': digest(OUT / 'differences.jsonl')})
    print(json.dumps({k: v for k, v in report.items() if k != 'games'}), flush=True)


if __name__ == '__main__':
    main()
