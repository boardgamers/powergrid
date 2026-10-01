"""Pin and validate one scheduled league checkpoint; never train or launch jobs."""
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


def prepare(arm, update, revision, output, fixtures):
    protocol = json.loads((ROOT / 'ai/strong/league-admission-protocol-v1.json').read_text())
    if arm not in protocol['arms'] or update not in protocol['checkpoint_updates']:
        raise ValueError('Arm/update is outside the scheduled comparison')
    if not re.fullmatch('[0-9a-f]{40}', revision):
        raise ValueError('Supply an immutable repository commit')
    run = protocol['arms'][arm]['run']
    output.mkdir(parents=True, exist_ok=True)
    # Never overwrite evidence from another checkpoint in the same directory.
    pin = {'run': run, 'update': update, 'revision': revision}
    pin_path = output / 'pin.json'
    if pin_path.exists() and json.loads(pin_path.read_text()) != pin:
        raise ValueError('Output directory is pinned to a different checkpoint')
    pin_path.write_text(json.dumps(pin, indent=2) + '\n')
    hashes = {}
    for name in ['latest.pt', 'latest.onnx', 'metrics.json', 'schema.json']:
        cached = hf_hub_download(REPO, f'runs/{run}/{name}', revision=revision)
        destination = output / name
        shutil.copyfile(cached, destination)
        hashes[name] = hashlib.sha256(destination.read_bytes()).hexdigest()
    checkpoint = torch.load(output / 'latest.pt', map_location='cpu', weights_only=True)
    expected = {'update': update, 'snapshot_admission': arm, 'snapshot_interval': 5,
                'initial_revision': 'fbdf2bf24c968bff99ab2d7d9ff9a7d97047db2b',
                'architecture': 'multiplayer_ordered', 'mixed_player_counts': True}
    for key, value in expected.items():
        if checkpoint.get(key) != value:
            raise ValueError(f'Checkpoint {key}: expected {value!r}, got {checkpoint.get(key)!r}')
    metrics = json.loads((output / 'metrics.json').read_text())
    batches = [m for m in metrics if m.get('stage') == 'train']
    if [m['update'] for m in batches] != list(range(update + 1)):
        raise ValueError('Missing, duplicate or unexpected training updates')
    for m in batches:
        if m['episodes'] != 240 or m['truncated'] != 0:
            raise ValueError('Incomplete training batch')
        if set(m['by_player_count']) != {'2', '3', '4', '5', '6'}:
            raise ValueError('Missing player count')
        if any(c['episodes'] != 48 or c['truncated'] for c in m['by_player_count'].values()):
            raise ValueError('Unbalanced or truncated training count')
        if not m.get('search_rollouts_reported') or not m.get('search_stats'):
            raise ValueError('Missing search diagnostics')
        if any(v['truncated'] for v in m['search_stats'].values()):
            raise ValueError('Truncated training search')
    manifest = {**pin, 'hashes': hashes, 'training_games': 240 * (update + 1),
                'training_truncated': 0, 'snapshot_updates': checkpoint['snapshot_updates'],
                'strict_parity': 'pending', 'scope': protocol['purpose']}
    manifest_path = output / 'checkpoint.json'
    manifest_path.write_text(json.dumps(manifest, indent=2) + '\n')
    parity_path = output / 'parity.json'
    result = subprocess.run([sys.executable, str(ROOT / 'ai/strong/check-export.py'),
                             str(output / 'latest.pt'), str(output / 'latest.onnx'),
                             str(fixtures), '--output', str(parity_path)], cwd=ROOT,
                            capture_output=True, text=True)
    (output / 'parity-check.log').write_text(result.stdout + result.stderr)
    manifest['strict_parity'] = 'passed' if result.returncode == 0 else 'failed'
    manifest_path.write_text(json.dumps(manifest, indent=2) + '\n')
    if result.returncode:
        raise RuntimeError(f'Strict parity failed; inspect {output / "parity-check.log"}')
    parity = json.loads(parity_path.read_text())
    if (parity['positions'] != 2553 or not parity['all_actions_match']
            or parity['model_sha256'] != hashes['latest.onnx']):
        manifest['strict_parity'] = 'failed'
        manifest_path.write_text(json.dumps(manifest, indent=2) + '\n')
        raise ValueError('Unexpected parity coverage or model identity')
    jobs = []
    for screen in protocol['screens']:
        n, opponent = screen['players'], screen['opponent']
        name = f'league-admission-{arm.replace("_", "-")}-u{update}-{opponent}-{n}p'
        env = {'PLAYER_COUNT': str(n), 'ASYNC_ARENA': '0', 'DEAL_OFFSET': '0',
               'DISABLE_SEARCH_PROPOSAL': '0', 'SEARCH_SCOPE': 'all',
               'OPPONENT_MODEL_PATH': '', 'OPPONENT_MODEL_REVISION': ''}
        if opponent == 'a260':
            env.update(OPPONENT_MODEL_PATH=screen['model_path'], OPPONENT_MODEL_REVISION=screen['revision'])
        jobs.append({'run': name, 'env': env, 'argv': ['bash', 'ai/strong/launch-multiplayer-arena.sh',
                     name, f'runs/{run}/latest.onnx', revision, 'economic', '0', '0',
                     str(screen['games']), protocol['seed_template'].format(players=n)]})
    (output / 'screen-plan.json').write_text(json.dumps(jobs, indent=2) + '\n')
    print(json.dumps({'checkpoint': str(manifest_path), 'strict_parity': 'passed',
                      'planned_jobs': len(jobs), 'jobs_launched': 0}))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('arm', choices=['best', 'periodic_anchor'])
    p.add_argument('update', type=int, choices=[9, 19])
    p.add_argument('revision')
    p.add_argument('output', type=Path)
    p.add_argument('--fixtures', type=Path, default=ROOT / 'ai/runs/multiplayer-serving-fixtures.jsonl')
    a = p.parse_args()
    prepare(a.arm, a.update, a.revision, a.output.resolve(), a.fixtures.resolve())
