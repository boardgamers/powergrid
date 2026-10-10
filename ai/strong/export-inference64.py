"""Explicit numerical derivative: unchanged stored weights and float32 inputs."""
import argparse
import hashlib
import json
from pathlib import Path
import torch
import onnx
from model import policy_from_checkpoint
from feature_contract import METADATA_KEY

p = argparse.ArgumentParser(__doc__)
p.add_argument('checkpoint', type=Path)
p.add_argument('output', type=Path)
a = p.parse_args()
torch.set_num_threads(1)
original = torch.load(a.checkpoint, map_location='cpu', weights_only=True)
assert original.get('inference_precision', 'float32') == 'float32'
assert original['architecture'] in ['multiplayer_ordered', 'multiplayer_ordered_plants']
assert all(v.dtype == torch.float32 for v in original['state_dict'].values())
derivative = {**original, 'inference_precision': 'float64', 'inference_only': True,
    'inference_transform': 'float64-exp-div-silu-v1',
    'numerical_derivative': {'source_checkpoint_sha256': hashlib.sha256(a.checkpoint.read_bytes()).hexdigest(),
        'trained': False, 'stored_weights_unchanged': True,
        'input_contract': 'Float32 feature values, then cast to float64 for all network arithmetic.'}}
net = policy_from_checkpoint(derivative).eval()
assert all(torch.equal(net.policy.state_dict()[k], v.double()) for k, v in original['state_dict'].items())
a.output.mkdir(parents=True, exist_ok=True)
pt, exported = a.output / 'inference64.pt', a.output / 'inference64.onnx'
assert not pt.exists() and not exported.exists(), 'Preserve prior numerical experiments'
torch.save(derivative, pt)
torch.onnx.export(net, (torch.zeros(1, original['state_dim']),
    torch.zeros(1, 8, original['action_dim']), torch.ones(1, 8, dtype=torch.bool)),
    str(exported), input_names=['state', 'actions', 'mask'], output_names=['logits', 'values'],
    dynamic_axes={'state': {0: 'batch'}, 'actions': {0: 'batch', 1: 'candidates'},
                  'mask': {0: 'batch', 1: 'candidates'}, 'logits': {0: 'batch', 1: 'candidates'},
                  'values': {0: 'batch'}}, opset_version=17, dynamo=False)
graph = onnx.load(exported)
onnx.helper.set_model_props(graph, {METADATA_KEY: original['feature_revision'],
    'powergrid.inference_precision': 'float64',
    'powergrid.inference_transform': derivative['inference_transform'],
    'powergrid.source_checkpoint_sha256': derivative['numerical_derivative']['source_checkpoint_sha256']})
onnx.save(graph, exported)
report = {**derivative['numerical_derivative'], 'feature_revision': original['feature_revision'],
          'inference_precision': 'float64', 'torch': torch.__version__,
          'inference_transform': derivative['inference_transform'],
          'files': {f.name: hashlib.sha256(f.read_bytes()).hexdigest() for f in [pt, exported]},
          'qualification_eligible': False,
          'scope': 'Numerical repair candidate; requires independent strict parity, legal serving, fresh evaluation and actual8840U benchmark.'}
(a.output / 'derivative.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report))
