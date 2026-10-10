"""Independently verify an immutable HF smoke artifact snapshot; no optimization."""
import argparse
import hashlib
import json
from pathlib import Path
import torch
from huggingface_hub import hf_hub_download
from model import policy_from_checkpoint

p = argparse.ArgumentParser(__doc__)
p.add_argument('revision')
p.add_argument('output')
args = p.parse_args()
out = Path(args.output)
out.mkdir(parents=True, exist_ok=True)
root = Path(__file__).resolve().parent
protocol = json.loads((root / 'five-plant-smoke-protocol-v1.json').read_text())
source = json.loads((root / 'five-plant-source-v1.json').read_text())
repo, prefix = protocol['env']['HF_MODEL_REPO'], 'runs/' + protocol['env']['RUN_NAME']

def fetch(name):
    path = Path(hf_hub_download(repo, prefix + '/' + name, revision=args.revision))
    data = path.read_bytes()
    (out / name).write_bytes(data)
    return data

raw = fetch('smoke-check.json')
report = json.loads(raw)
assert report['status'] == 'complete' and report['qualification_eligible'] is False
assert report['source_revision'] == source['revision'] and report['source_sha256'] == source['sha256']
assert report['protocol_sha256'] == hashlib.sha256((root / 'five-plant-smoke-protocol-v1.json').read_bytes()).hexdigest()
for name, digest in report['artifact_sha256'].items():
    assert '/' not in name and name != 'smoke-check.json'
    assert hashlib.sha256(fetch(name)).hexdigest() == digest, name
metrics = json.loads((out / 'metrics.json').read_text())
rows = [r for r in metrics if r.get('stage') == 'train']
assert len(rows) == 1 and rows[0] == report['training']
row = rows[0]
assert row['update'] == 0 and row['episodes'] == 80 and row['truncated'] == 0
assert set(row['by_player_count']) == set('23456')
assert all(x['episodes'] == 16 and x['truncated'] == 0 for x in row['by_player_count'].values())
assert row['search_rollouts_reported'] and row['search_stats']
assert all(x['truncated'] == 0 for x in row['search_stats'].values())
assert sum(row['opponent_seats'].values()) == 320
assert all(row['opponent_seats'].get(f'frozen{i}', 0) > 0 for i in range(3))
checkpoint = torch.load(out / 'latest.pt', map_location='cpu', weights_only=True)
assert checkpoint['update'] == 0 and checkpoint['snapshot_updates'] == [-1, 0]
assert checkpoint['initial_sha256'] == protocol['env']['INIT_SHA256']
assert checkpoint['initial_revision'] == protocol['env']['INIT_REVISION']
assert checkpoint['initial_transfer']['trained'] is False
assert checkpoint['frozen_opponents'] == json.loads((root / 'population-opponents-v1.json').read_text())
assert checkpoint['opponent_mode'] == protocol['env']['OPPONENT_MODE']
assert checkpoint['training_device'] == 'cuda' and checkpoint['async_rollout']
net = policy_from_checkpoint(checkpoint).eval()
assert all(torch.isfinite(v).all().item() for v in net.state_dict().values())
norms = {key: checkpoint['state_dict'][key].norm().item() for key in ['extra_player.weight', 'extra_action.weight']}
assert norms == report['new_parameter_norms'] and all(v > 0 for v in norms.values())
export = json.loads((out / 'export-check.json').read_text())
assert export == report['export'] and export['positions'] == 2553
assert export['by_player_count'] == {'2': 349, '3': 427, '4': 527, '5': 609, '6': 641}
assert export['all_actions_match'] and export['inactive_values_zero']
assert export['feature_revision'] == '4.1-five-plants'
assert export['model_sha256'] == report['artifact_sha256']['latest.onnx']
summary = dict(artifact_revision=args.revision, smoke_report_sha256=hashlib.sha256(raw).hexdigest(),
               verified=True, qualification_eligible=False, games=80, games_per_count=16,
               game_truncations=0, search_stats=row['search_stats'], new_parameter_norms=norms,
               update_seconds=row['seconds'], export=export, source=source['revision'],
               initial_revision=checkpoint['initial_revision'], hashes=report['artifact_sha256'])
(out / 'verified.json').write_text(json.dumps(summary, indent=2) + '\n')
print(json.dumps(summary))
