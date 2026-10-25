"""Preserve learned weights and verify a standalone float64 CPU inference model."""
import argparse
from pathlib import Path

import numpy as np
import onnx
import onnxruntime as ort
import torch
from model_opponent_surrogate_v1 import from_checkpoint
from opponent_surrogate_training_v1 import metrics
from strategic_collection import read, write, digest


def export(checkpoint, output):
    original = torch.load(checkpoint, map_location='cpu', weights_only=True)
    assert original.get('inference_precision', 'float32') == 'float32'
    assert all(v.dtype == torch.float32 for v in original['state_dict'].values())
    derivative = {**original, 'inference_precision': 'float64', 'inference_only': True,
                  'inference_transform': 'float64-exp-div-silu-v1',
                  'numerical_derivative': {'source_checkpoint_sha256': digest(checkpoint),
                      'trained': False, 'stored_weights_unchanged': True,
                      'input_contract': 'Float32 public features followed by float64 network arithmetic.'}}
    net = from_checkpoint(derivative).eval()
    assert all(torch.equal(net.policy.state_dict()[k], v.double()) for k, v in original['state_dict'].items())
    output = Path(output); output.mkdir(parents=True, exist_ok=False)
    torch.save(derivative, output/'inference64.pt')
    path = output/'inference64.onnx'
    torch.onnx.export(net, (torch.zeros(1, 1217), torch.zeros(1, 6, 101), torch.ones(1, 6, dtype=torch.bool)),
        str(path), input_names=['state', 'actions', 'mask'], output_names=['logits'],
        dynamic_axes={k: {0: 'batch'} for k in ('state', 'actions', 'mask', 'logits')}, opset_version=17, dynamo=False)
    graph = onnx.load(path)
    onnx.helper.set_model_props(graph, {'powergrid.feature_revision': original['feature_revision'],
        'powergrid.inference_precision': 'float64', 'powergrid.inference_transform': derivative['inference_transform'],
        'powergrid.role': 'opponent_surrogate_v1', 'powergrid.source_checkpoint_sha256': digest(checkpoint)})
    onnx.checker.check_model(graph); onnx.save(graph, path)
    report = {**derivative['numerical_derivative'], 'inference_precision': 'float64', 'max_candidates': 6,
              'files': {name: digest(output/name) for name in ('inference64.pt', 'inference64.onnx')},
              'qualification_eligible': False}
    write(output/'derivative.json', report); return report


def verify(output, data, batch_size=256):
    output = Path(output); report = read(output/'derivative.json')
    assert all(digest(output/name) == sha for name, sha in report['files'].items())
    cp = torch.load(output/'inference64.pt', map_location='cpu', weights_only=True)
    net = from_checkpoint(cp).eval()
    options = ort.SessionOptions(); options.intra_op_num_threads = 1; options.inter_op_num_threads = 1
    session = ort.InferenceSession(str(output/'inference64.onnx'), sess_options=options, providers=['CPUExecutionProvider'])
    result = {}; maximum = 0.; total = 0
    for split, d in data.items():
        scores = []
        for start in range(0, len(d['target']), batch_size):
            feed = {k: np.array(d[k][start:start+batch_size], copy=True) for k in ('state', 'actions', 'mask')}
            with torch.inference_mode(): expected = net(*(torch.from_numpy(feed[k]) for k in feed)).numpy()
            actual = session.run(['logits'], feed)[0]
            assert expected.shape == actual.shape and actual.dtype == np.float64
            np.testing.assert_allclose(actual, expected, rtol=1e-10, atol=1e-10)
            np.testing.assert_array_equal(actual.argmax(1), expected.argmax(1))
            maximum = max(maximum, float(np.max(np.abs(actual - expected)))); total += len(actual)
            scores.append(actual)
        result[split] = metrics(np.concatenate(scores), d)
    proof = {'complete': True, 'positions': total, 'exact_choices': total, 'max_absolute_logit_error': maximum,
             'scores_rtol': 1e-10, 'scores_atol': 1e-10, 'derivative_sha256': digest(output/'derivative.json'),
             'exported_behaviour_metrics': result, 'gradients': False, 'qualification_eligible': False,
             'scope': 'CPU ONNX vs matching float64 checkpoint on supplied records. Neither target-hardware latency nor full-game strength.'}
    write(output/'parity.json', proof); return proof


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__); parser.add_argument('checkpoint', type=Path); parser.add_argument('output', type=Path)
    a = parser.parse_args(); print(export(a.checkpoint, a.output))
