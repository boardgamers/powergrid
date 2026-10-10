"""Verify pinned population checkpoints and prepare paired development arenas."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys

import torch
from huggingface_hub import hf_hub_download

ROOT = Path(__file__).resolve().parents[2]
REPO = 'coyotte508/powergrid-ai-germany-v1'


def validate_training(checkpoint, metrics, protocol, arm, update):
    expected = {
        'update': update, 'architecture': 'multiplayer_ordered',
        'feature_revision': '4.0-multiplayer', 'mixed_player_counts': True,
        'snapshot_admission': 'periodic_anchor', 'snapshot_interval': 5,
        'opponent_mode': protocol['arms'][arm]['mode'],
        'initial_checkpoint': protocol['initial']['path'],
        'initial_revision': protocol['initial']['revision'],
        'initial_sha256': protocol['initial']['sha256'],
        'frozen_opponents': [] if arm == 'control' else protocol['frozen_opponents'],
        'snapshot_updates': [-1, update - 5, update],
    }
    for key, value in expected.items():
        if checkpoint.get(key) != value:
            raise ValueError('Checkpoint provenance mismatch: ' + key)
    batches = [m for m in metrics if m.get('stage') == 'train']
    if [m['update'] for m in batches] != list(range(update + 1)):
        raise ValueError('Missing or duplicate training updates')
    roles = set()
    for m in batches:
        if m['episodes'] != 240 or m['truncated'] or set(m['by_player_count']) != {'2', '3', '4', '5', '6'}:
            raise ValueError('Incomplete training batch')
        if any(v['episodes'] != 48 or v['truncated'] for v in m['by_player_count'].values()):
            raise ValueError('Unbalanced or truncated player-count batch')
        if not m.get('search_rollouts_reported') or not m.get('search_stats'):
            raise ValueError('Missing search diagnostics')
        if any(v['truncated'] for v in m['search_stats'].values()):
            raise ValueError('Truncated training search')
        if sum(m.get('opponent_seats', {}).values()) != 960:
            raise ValueError('Missing opponent-seat accounting')
        roles.update(m['opponent_seats'])
        if arm == 'homogeneous' and any(k.startswith('mixed:') for k in m['training_opponents']):
            raise ValueError('Unexpected mixed table in homogeneous arm')
    frozen = {r for r in roles if r.startswith('frozen')}
    if frozen != (set() if arm == 'control' else {'frozen0', 'frozen1', 'frozen2'}):
        raise ValueError('Missing or unexpected frozen opponents')
    if arm == 'heterogeneous' and not any(
        k.startswith('mixed:') for m in batches for k in m['training_opponents']
    ):
        raise ValueError('No heterogeneous training tables')


def prepare(arm, update, revision, output, fixtures):
    protocol = json.loads((ROOT / 'ai/strong/population-training-protocol-v1.json').read_text())
    if arm == 'parent':
        if update != 79 or revision != protocol['initial']['revision']:
            raise ValueError('Parent must be the frozen H200 update79')
        run = str(Path(protocol['initial']['path']).parent).removeprefix('runs/')
    else:
        if arm not in protocol['arms'] or update not in protocol['checkpoint_updates']:
            raise ValueError('Outside scheduled comparison')
        run = protocol['arms'][arm]['run']
    if not re.fullmatch('[0-9a-f]{40}', revision):
        raise ValueError('Pin immutable repository revision')
    output.mkdir(parents=True, exist_ok=True)
    pin = {'arm': arm, 'run': run, 'update': update, 'revision': revision}
    pin_file = output / 'pin.json'
    if pin_file.exists() and json.loads(pin_file.read_text()) != pin:
        raise ValueError('Output directory already pins a different checkpoint')
    pin_file.write_text(json.dumps(pin, indent=2) + '\n')
    hashes = {}
    for name in ['latest.pt', 'latest.onnx', 'metrics.json', 'schema.json']:
        file = output / name
        shutil.copyfile(hf_hub_download(REPO, f'runs/{run}/{name}', revision=revision), file)
        hashes[name] = hashlib.sha256(file.read_bytes()).hexdigest()
    checkpoint = torch.load(output / 'latest.pt', map_location='cpu', weights_only=True)
    if arm == 'parent':
        if hashes['latest.pt'] != protocol['initial']['sha256'] or checkpoint['update'] != 79:
            raise ValueError('Wrong parent checkpoint')
    else:
        validate_training(checkpoint, json.loads((output / 'metrics.json').read_text()), protocol, arm, update)
    manifest = {**pin, 'hashes': hashes, 'strict_parity': 'pending', 'qualification_eligible': False}
    manifest_file = output / 'checkpoint.json'
    manifest_file.write_text(json.dumps(manifest, indent=2) + '\n')
    parity_file = output / 'parity.json'
    result = subprocess.run([sys.executable, str(ROOT / 'ai/strong/check-export.py'),
        str(output / 'latest.pt'), str(output / 'latest.onnx'), str(fixtures),
        '--output', str(parity_file)], cwd=ROOT, capture_output=True, text=True)
    (output / 'parity-check.log').write_text(result.stdout + result.stderr)
    manifest['strict_parity'] = 'failed'
    if result.returncode == 0:
        parity = json.loads(parity_file.read_text())
        if (parity['positions'] == 2553 and parity['all_actions_match']
                and parity['model_sha256'] == hashes['latest.onnx']):
            manifest['strict_parity'] = 'passed'
    manifest_file.write_text(json.dumps(manifest, indent=2) + '\n')
    if manifest['strict_parity'] != 'passed':
        raise ValueError('Full checkpoint/export parity failed; inspect parity-check.log')
    evaluation = protocol['evaluation']
    jobs = []
    for screen in evaluation['screens']:
        n, opponent = screen['players'], screen['opponent']
        name = f'population-v1-{arm}-u{update}-{opponent}-{n}p'
        env = {'PLAYER_COUNT': str(n), 'ASYNC_ARENA': '0', 'DEAL_OFFSET': '0',
            'DISABLE_SEARCH_PROPOSAL': '0', 'SEARCH_SCOPE': 'all',
            'OPPONENT_MODEL_PATH': '', 'OPPONENT_MODEL_REVISION': ''}
        if opponent == 'a260':
            env.update(OPPONENT_MODEL_PATH=screen['model_path'], OPPONENT_MODEL_REVISION=screen['revision'])
        jobs.append({'run': name, 'env': env, 'argv': ['bash', 'ai/strong/launch-multiplayer-arena.sh',
            name, f'runs/{run}/latest.onnx', revision, 'economic', '0', '0',
            str(screen['games']), evaluation['seed_template'].format(players=n)]})
    (output / 'screen-plan.json').write_text(json.dumps(jobs, indent=2) + '\n')
    print(json.dumps({'checkpoint': str(manifest_file), 'strict_parity': 'passed', 'planned_jobs': len(jobs)}))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('arm', choices=['parent', 'control', 'homogeneous', 'heterogeneous'])
    p.add_argument('update', type=int)
    p.add_argument('revision')
    p.add_argument('output', type=Path)
    p.add_argument('--fixtures', type=Path, default=ROOT / 'ai/runs/multiplayer-serving-fixtures.jsonl')
    a = p.parse_args()
    prepare(a.arm, a.update, a.revision, a.output.resolve(), a.fixtures.resolve())
