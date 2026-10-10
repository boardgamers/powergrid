"""Compare explicit precision derivatives without asserting FP32 decisions are identical."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
import onnxruntime as ort
import torch
from model import policy_from_checkpoint, tensors
from feature_contract import METADATA_KEY
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from infer import Node


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def audit(original, original_onnx, derivative, derivative_onnx, fixtures):
    torch.set_num_threads(1)
    source = torch.load(original, map_location='cpu', weights_only=True)
    cp = torch.load(derivative, map_location='cpu', weights_only=True)
    assert source.get('inference_precision', 'float32') == 'float32'
    assert cp['inference_precision'] == 'float64' and cp['inference_only']
    assert cp['inference_transform'] == 'float64-exp-div-silu-v1'
    assert cp['numerical_derivative']['source_checkpoint_sha256'] == digest(original)
    assert cp['state_dict'].keys() == source['state_dict'].keys()
    assert all(torch.equal(v, source['state_dict'][k]) for k, v in cp['state_dict'].items())
    assert cp['feature_revision'] == source['feature_revision']
    fp32 = policy_from_checkpoint(source).eval()
    native = policy_from_checkpoint({**cp, 'inference_transform': 'float64-native-silu-v1'}).eval()
    opts = ort.SessionOptions()
    opts.intra_op_num_threads = opts.inter_op_num_threads = 1
    old = ort.InferenceSession(str(original_onnx), opts, providers=['CPUExecutionProvider'])
    new = ort.InferenceSession(str(derivative_onnx), opts, providers=['CPUExecutionProvider'])
    assert old.get_modelmeta().custom_metadata_map[METADATA_KEY] == cp['feature_revision']
    assert new.get_modelmeta().custom_metadata_map[METADATA_KEY] == cp['feature_revision']
    report = {
        'positions': 0, 'by_player_count': {}, 'by_rules': {},
        'source_checkpoint_sha256': digest(original), 'source_onnx_sha256': digest(original_onnx),
        'derivative_checkpoint_sha256': digest(derivative), 'derivative_onnx_sha256': digest(derivative_onnx),
        'fixture_sha256': digest(fixtures), 'feature_revision': cp['feature_revision'],
        'rtol': 1e-4, 'atol': 1e-5, 'native64_max_errors': [0., 0.],
        'native64_strict_pass': True, 'stored_weights_identical': True,
        'action_changes': {'pytorch32_to_native64': [], 'onnx32_to_onnx64': [], 'pytorch32_to_onnx32': []},
        'trained': False, 'qualification_eligible': False,
        'scope': 'Every serving fixture, single request. Action equivalence here does not prove identical complete-game trajectories.'}
    worker = Node('strong/worker.cjs')
    try:
        with Path(fixtures).open() as file:
            for index, line in enumerate(file):
                request = json.loads(line)['request']
                request['featureRevision'] = cp['feature_revision']
                row = worker.call(request)
                assert 'error' not in row, row
                inputs = tensors([row], 'cpu')
                feed = dict(zip(['state', 'actions', 'mask'], [x.numpy() for x in inputs]))
                with torch.inference_mode():
                    pt32 = [x.numpy() for x in fp32(*inputs)]
                    pt64 = [x.numpy() for x in native(*inputs)]
                ort32, ort64 = old.run(None, feed), new.run(None, feed)
                for c in range(2):
                    np.testing.assert_allclose(ort64[c], pt64[c], rtol=1e-4, atol=1e-5)
                    assert np.isfinite(ort64[c]).all()
                    report['native64_max_errors'][c] = max(report['native64_max_errors'][c], float(np.abs(ort64[c]-pt64[c]).max()))
                assert np.argmax(ort64[0]) == np.argmax(pt64[0])
                n = len(request['state']['players'])
                options = request['state']['options']
                rules = options.get('variant', 'original') + ('/sealed' if options.get('fastBid') else '/open')
                for key, value in [('by_player_count', str(n)), ('by_rules', rules)]:
                    report[key][value] = report[key].get(value, 0) + 1
                for name, a, b in [('pytorch32_to_native64', pt32, pt64), ('onnx32_to_onnx64', ort32, ort64), ('pytorch32_to_onnx32', pt32, ort32)]:
                    before, after = int(np.argmax(a[0])), int(np.argmax(b[0]))
                    if before != after:
                        report['action_changes'][name].append({'fixture': index, 'players': n, 'rules': rules,
                            'before': before, 'after': after,
                            'old_logits': [float(a[0][0, i]) for i in [before, after]],
                            'new_logits': [float(b[0][0, i]) for i in [before, after]]})
                report['positions'] += 1
    finally:
        worker.close()
    report['action_change_counts'] = {k: len(v) for k, v in report['action_changes'].items()}
    return report


if __name__ == '__main__':
    p = argparse.ArgumentParser(__doc__)
    for name in ['original', 'original_onnx', 'derivative', 'derivative_onnx', 'fixtures']:
        p.add_argument(name, type=Path)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    assert not a.output.exists(), 'Preserve earlier audits'
    report = audit(a.original, a.original_onnx, a.derivative, a.derivative_onnx, a.fixtures)
    a.output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k: report[k] for k in ['positions', 'native64_max_errors', 'action_change_counts']}))
