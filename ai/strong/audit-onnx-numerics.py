"""Read-only export diagnosis; preserve the exact existing tolerance and weights."""
import argparse
import hashlib
import json
from pathlib import Path
import platform
import sys
import time

import numpy as np
import onnxruntime as ort
import torch
from model import policy_from_checkpoint, tensors
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from infer import Node

p = argparse.ArgumentParser(__doc__)
p.add_argument('checkpoint', type=Path)
p.add_argument('model', type=Path)
p.add_argument('fixtures', type=Path)
p.add_argument('--output', type=Path, required=True)
a = p.parse_args()
torch.set_num_threads(1)
checkpoint = torch.load(a.checkpoint, map_location='cpu', weights_only=True)
net = policy_from_checkpoint(checkpoint).eval()
levels = {'all': ort.GraphOptimizationLevel.ORT_ENABLE_ALL,
          'extended': ort.GraphOptimizationLevel.ORT_ENABLE_EXTENDED,
          'basic': ort.GraphOptimizationLevel.ORT_ENABLE_BASIC,
          'disabled': ort.GraphOptimizationLevel.ORT_DISABLE_ALL}
sessions, results = {}, {}
for name, level in levels.items():
    options = ort.SessionOptions(); options.intra_op_num_threads = 1; options.inter_op_num_threads = 1
    options.graph_optimization_level = level
    sessions[name] = ort.InferenceSession(str(a.model), options, providers=['CPUExecutionProvider'])
    results[name] = {'positions': 0, 'failed_logit_positions': 0, 'failed_value_positions': 0,
                     'different_actions': 0, 'max_logit_error': 0., 'max_value_error': 0.,
                     'failing_examples': [], 'inference_seconds': 0.}
node = Node('strong/worker.cjs')
by_count = {}
try:
    for index, line in enumerate(a.fixtures.read_text().splitlines()):
        request = json.loads(line)['request']; request['featureRevision'] = checkpoint['feature_revision']
        row = node.call(request); assert 'error' not in row, row
        inputs = tensors([row], 'cpu')
        with torch.inference_mode(): expected = [x.numpy() for x in net(*inputs)]
        feed = dict(zip(['state', 'actions', 'mask'], [x.numpy() for x in inputs]))
        n = len(request['state']['players']); by_count[str(n)] = by_count.get(str(n), 0) + 1
        for name, session in sessions.items():
            stats = results[name]; begin = time.perf_counter(); actual = session.run(None, feed)
            stats['inference_seconds'] += time.perf_counter() - begin
            stats['positions'] += 1
            stats['different_actions'] += int(np.argmax(actual[0]) != np.argmax(expected[0]))
            for component, label in enumerate(['logit', 'value']):
                errors = np.abs(actual[component] - expected[component])
                stats['max_' + label + '_error'] = max(stats['max_' + label + '_error'], float(errors.max()))
                mask = ~np.isclose(actual[component], expected[component], rtol=1e-4, atol=1e-5)
                if mask.any():
                    stats['failed_' + label + '_positions'] += 1
                    if len(stats['failing_examples']) < 10:
                        stats['failing_examples'].append({'fixture_index': index, 'players': n,
                            'component': label, 'actual': actual[component][mask].tolist(),
                            'expected': expected[component][mask].tolist()})
            assert np.isfinite(actual[0]).all() and np.isfinite(actual[1]).all()
            assert np.all(actual[1][:, n:] == 0) and np.isclose(actual[1].sum(), 1)
finally:
    node.close()
report = {'model_sha256': hashlib.sha256(a.model.read_bytes()).hexdigest(),
          'checkpoint_sha256': hashlib.sha256(a.checkpoint.read_bytes()).hexdigest(),
          'fixture_sha256': hashlib.sha256(a.fixtures.read_bytes()).hexdigest(),
          'feature_revision': checkpoint['feature_revision'], 'by_player_count': by_count,
          'rtol': 1e-4, 'atol': 1e-5, 'results': results,
          'runtime': {'torch': torch.__version__, 'onnxruntime': ort.__version__,
                      'numpy': np.__version__, 'machine': platform.machine()},
          'scope': 'Local export diagnosis only. No change to model, production runtime, tolerance or qualification.'}
a.output.write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({k: {f: v[f] for f in ['positions', 'failed_logit_positions',
    'failed_value_positions', 'different_actions', 'max_logit_error']} for k, v in results.items()}))
