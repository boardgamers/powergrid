"""Engineering parity of complete public-runtime games, never strength selection."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

from huggingface_hub import hf_hub_download
from population_policy_verification import verify_evaluation, digest, read

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT/'ai/runs/public-policy-runtime-preflight-v1/package'
OUT = ROOT/'ai/runs/public-policy-arena-preflight-v1'
SCHEDULE = [(2, 'legacy'), (3, 'a260'), (4, 'economic'), (5, 'rush'), (6, 'heuristic')]
ENTRY = 'ai/strong/public_policy_arena_v1.py'
BRIDGE = 'ai/strong/public-arena-bridge.cjs'


def write(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False)+'\n')


def prepare():
    assert not OUT.exists(), 'Inspect the original preflight rather than overwrite or repeat it'
    baseline = read(ROOT/'ai/strong/public-policy-runtime-preflight-v1.json')
    assert baseline['complete'] and baseline['runtime_manifest_sha256'] == digest(BASE/'manifest.json')
    manifest = read(BASE/'manifest.json')
    assert all(digest(BASE/name) == sha for name, sha in manifest.items())
    package = OUT/'package'; package.mkdir(parents=True)
    for name in manifest:
        target = package/name; target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(BASE/name, target)
    changed = [ENTRY, BRIDGE]
    for name in changed:
        shutil.copy2(ROOT/name, package/name); manifest[name] = digest(package/name)
    opponent = Path(hf_hub_download('coyotte508/powergrid-ai-germany-v1', 'runs/strong-league-v2-a/best.onnx',
                                  revision='b38515c29e57826de05b55b645c29591e4a886bf'))
    assert digest(opponent) == '9b46db558669a0c3085412fe2544359eda55ed9f092dffb67bead6af3c409ecd'
    shutil.copy2(opponent, package/'opponent.onnx'); manifest['opponent.onnx'] = digest(opponent)
    write(package/'manifest.json', manifest)
    spec = read(BASE/'policy.json'); spec['runtime_manifest']['sha256'] = digest(package/'manifest.json')
    write(package/'policy.json', spec)
    write(OUT/'prepared.json', {'baseline_evidence_sha256': digest(ROOT/'ai/strong/public-policy-runtime-preflight-v1.json'),
        'baseline_manifest_sha256': digest(BASE/'manifest.json'), 'manifest_sha256': digest(package/'manifest.json'),
        'policy_sha256': digest(package/'policy.json'), 'changed_runtime_files': {p: digest(package/p) for p in changed},
        'unchanged_policy_entry_sha256': digest(package/'ai/strong/public_policy_runtime_v1.py'),
        'checker_sha256': digest(__file__), 'schedule': SCHEDULE,
        'seed': 'public-runtime-engineering-v1', 'final_protocol_sha256': digest(ROOT/'ai/strong/final-protocol-multiplayer.json'),
        'qualification_eligible': False, 'reserved_final_seeds_used': False})
    for players, opponent_name in SCHEDULE:
        command = [sys.executable, '-u', '-B', str(package/ENTRY), '--artifact', str(package),
                   '--players', str(players), '--opponent', opponent_name, '--seed', 'public-runtime-engineering-v1',
                   '--workers', '4', '--reference-artifact', str(BASE), '--output', str(OUT/f'{players}p')]
        if opponent_name == 'a260':
            command += ['--opponent-model', str(package/'opponent.onnx')]
        with (OUT/f'{players}p.log').open('x') as log:
            subprocess.run(command, cwd='/tmp', stdout=log, stderr=subprocess.STDOUT, check=True,
                           env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'})
        print({'players': players, 'opponent': opponent_name, 'paired_engineering_games': 4*players}, flush=True)
    verify()


def verify():
    package = OUT/'package'; prep = read(OUT/'prepared.json')
    assert prep['checker_sha256'] == digest(__file__)
    assert prep['baseline_manifest_sha256'] == digest(BASE/'manifest.json')
    assert all(digest(BASE/name) == sha for name, sha in read(BASE/'manifest.json').items())
    assert prep['manifest_sha256'] == digest(package/'manifest.json')
    assert all(digest(package/name) == sha for name, sha in read(package/'manifest.json').items())
    assert prep['policy_sha256'] == digest(package/'policy.json')
    assert prep['final_protocol_sha256'] == digest(ROOT/'ai/strong/final-protocol-multiplayer.json')
    # Import only pure validation helpers; all actual policy execution above was
    # in its separately pinned subprocess, outside the repository working dir.
    from public_policy_arena_v1 import validate_response, semantic
    assessments = {}; decisions = 0
    for players, opponent in SCHEDULE:
        directory = OUT/f'{players}p'
        report = read(directory/'evaluation.json')
        config = report['config']
        assert report['passed'] and report['validation_error'] is None
        assessments[str(players)] = verify_evaluation(directory, {'players': players, 'opponent': opponent,
            'arm': 'filter', 'seed': prep['seed'], 'start': 0, 'deals': 1})
        for record in report['results']:
            assert record['direct_reference_trajectory_checked'] is True
            assert record['public_runtime_identity'] == config['identity']
            with (directory/f'decisions-{record["episode"]}.jsonl').open() as stream:
                for line in stream:
                    row = json.loads(line)
                    response, request = row['publicResponse'], row['publicRequest']
                    index = validate_response(response, request, row['arenaMoves'], row['arenaPlayerOrder'], config['identity'])
                    assert index == row['index']
                    assert semantic(response['decision']) == semantic(row['directReference'])
                    assert all(semantic(row[k]) == semantic(v) for k, v in response['decision'].items())
                    assert request['player'] == record['terminal']['seat']
                    assert request['requestId'] == f'{record["episode"]}:{row["decision"]}'
                    assert request['revision'] == row['decision']
                    state = request['state']
                    assert state['seed'] == 'secret' and state['powerPlantsDeck'] == []
                    assert not state.get('hiddenLog') and 'powerPlantDeckAfterStep3' not in state
                    if state['options']['fastBid']:
                        assert all(p['bid'] == 0 for p in state['players'])
                    decisions += 1
    result = {'complete': True, 'checked_at': datetime.now(timezone.utc).isoformat(),
        'engineering_games': sum(v['games'] for v in assessments.values()), 'exact_decisions': decisions,
        'all_logical_engine_transitions_exact': True, 'caps': 0, 'by_player_count': assessments,
        'normalized_reference_fields': ['public state players.clockStartedAt', 'public state players.totalTimeUsed',
            'public state players.lastMove.time/serverTime', 'public state log.move.time/serverTime'],
        'prepared_sha256': digest(OUT/'prepared.json'), 'manifest_sha256': prep['manifest_sha256'],
        'policy_sha256': prep['policy_sha256'], 'checker_sha256': digest(__file__),
        'new_hf_jobs': 0, 'new_strength_games': 0, 'gradients': False,
        'qualification_eligible': False, 'reserved_final_seeds_used': False,
        'scope': 'Complete filtered-policy engineering games through standalone JSON process versus unchanged direct policy and original engine. All seats/rules at 2–6 players, five opponent implementations. Not a selected-policy strength result, final adapter or target-hardware benchmark.'}
    assert result['engineering_games'] == 80
    write(OUT/'result.json', result); print({k: result[k] for k in ['complete', 'engineering_games', 'exact_decisions', 'caps']}, flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__); parser.add_argument('operation', choices=['prepare', 'verify'])
    globals()[parser.parse_args().operation]()
