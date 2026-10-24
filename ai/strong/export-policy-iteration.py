"""Unchanged float32 weights, explicit float64 derivative for new head ensembles."""
import argparse
from pathlib import Path
import torch
import onnx
from model_policy_iteration import policy_from_checkpoint
from feature_contract import METADATA_KEY
from strategic_collection import digest, write


def export(checkpoint, output):
    torch.set_num_threads(1)
    original = torch.load(checkpoint, map_location='cpu', weights_only=True)
    assert original['architecture'] in ['policy_iteration_head', 'policy_iteration_ensemble']
    assert original.get('inference_precision', 'float32') == 'float32'
    assert all(v.dtype == torch.float32 for v in original['state_dict'].values())
    derivative = {**original, 'inference_precision': 'float64', 'inference_only': True,
                  'inference_transform': 'float64-exp-div-silu-v1',
                  'numerical_derivative': {'source_checkpoint_sha256': digest(checkpoint),
                      'trained': False, 'stored_weights_unchanged': True,
                      'input_contract': 'Float32 feature values, then float64 network arithmetic.'}}
    net = policy_from_checkpoint(derivative).eval()
    assert all(torch.equal(net.policy.state_dict()[k], v.double()) for k, v in original['state_dict'].items())
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    pt, exported = output/'inference64.pt', output/'inference64.onnx'
    torch.save(derivative, pt)
    torch.onnx.export(net, (torch.zeros(1, original['state_dim']), torch.zeros(1, 8, original['action_dim']),
        torch.ones(1, 8, dtype=torch.bool)), str(exported),
        input_names=['state', 'actions', 'mask'], output_names=['logits', 'values'],
        dynamic_axes={'state': {0: 'batch'}, 'actions': {0: 'batch', 1: 'candidates'},
                      'mask': {0: 'batch', 1: 'candidates'}, 'logits': {0: 'batch', 1: 'candidates'},
                      'values': {0: 'batch'}}, opset_version=17, dynamo=False)
    graph = onnx.load(exported)
    onnx.helper.set_model_props(graph, {METADATA_KEY: original['feature_revision'],
        'powergrid.inference_precision': 'float64', 'powergrid.inference_transform': derivative['inference_transform'],
        'powergrid.source_checkpoint_sha256': digest(checkpoint)})
    onnx.checker.check_model(graph)
    onnx.save(graph, exported)
    report = {**derivative['numerical_derivative'], 'feature_revision': original['feature_revision'],
              'inference_precision': 'float64', 'inference_transform': derivative['inference_transform'],
              'torch': str(torch.__version__), 'files': {f.name: digest(f) for f in [pt, exported]},
              'qualification_eligible': False}
    write(output/'derivative.json', report)
    return report


if __name__ == '__main__':
    p = argparse.ArgumentParser(__doc__)
    p.add_argument('checkpoint', type=Path)
    p.add_argument('output', type=Path)
    args = p.parse_args()
    print(export(args.checkpoint, args.output), flush=True)
