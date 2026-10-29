"""Export audited weights and check native/ONNX choices on existing inputs only."""
import json
import numpy as np
import onnx
import onnxruntime as ort
import torch
from model import Inference64Policy
from model_nomination_discount_v1 import from_checkpoint
from prepare_auction_discount_teacher_v2 import ROOT, read, save, digest

OUT = ROOT/'ai/runs/nomination-discount-export-v1'
RESULT = ROOT/'ai/strong/nomination-discount-export-v1.json'


def session(path):
    options = ort.SessionOptions(); options.intra_op_num_threads = options.inter_op_num_threads = 1
    return ort.InferenceSession(str(path), sess_options=options, providers=['CPUExecutionProvider'])


def main():
    assert not OUT.exists() and not RESULT.exists(), 'Inspect prior export outcome'
    report = read(ROOT/'ai/strong/nomination-discount-training-results-v1.json')
    assert report['complete'] and len(report['arms']) == 4
    inputs = dict(np.load(ROOT/'ai/runs/nomination-discount-training-data-v1/data.npz', allow_pickle=False))
    old = dict(np.load(ROOT/'ai/runs/policy-iteration-features-v2/features.npz', allow_pickle=False))
    ids = np.flatnonzero(~((old['actions'][:, :, 0] > .5) & old['mask']).any(1))[:256]
    other = {'state': np.pad(old['state'][ids], ((0, 0), (0, 1))),
             'actions': np.pad(old['actions'][ids], ((0, 0), (0, 0), (0, 2))), 'mask': old['mask'][ids]}
    frozen = ROOT/'ai/runs/current-auction-grid-prepared-v1/source/artifact/policy.onnx'
    assert digest(frozen) == '55331f43379e8fe89025d93b1a7a48c88e0ea39b4ebd3a7ef8240d4b62753530'
    parent = session(frozen); torch.set_num_threads(1); OUT.mkdir(); results = []
    for arm in report['arms']:
        name = arm['arm']; folder = OUT/name; folder.mkdir()
        source = ROOT/f'ai/runs/nomination-discount-training-collected-v1/{name}/raw/ensemble.pt'
        assert digest(source) == arm['ensemble_sha256']
        cp = torch.load(source, map_location='cpu', weights_only=True)
        net = Inference64Policy(from_checkpoint(cp), 'float64-exp-div-silu-v1').eval()
        assert all(torch.equal(net.policy.state_dict()[k], v.double()) for k, v in cp['state_dict'].items())
        derivative = {**cp, 'inference_precision': 'float64', 'inference_only': True,
                      'inference_transform': 'float64-exp-div-silu-v1', 'source_checkpoint_sha256': digest(source)}
        torch.save(derivative, folder/'inference64.pt')
        exported = folder/'inference64.onnx'
        torch.onnx.export(net, (torch.zeros(1, 1218), torch.zeros(1, 8, 103), torch.ones(1, 8, dtype=torch.bool)),
                          str(exported), input_names=['state', 'actions', 'mask'], output_names=['logits', 'values'],
                          dynamic_axes={'state': {0: 'batch'}, 'actions': {0: 'batch', 1: 'candidates'},
                                        'mask': {0: 'batch', 1: 'candidates'}, 'logits': {0: 'batch', 1: 'candidates'},
                                        'values': {0: 'batch'}}, opset_version=17, dynamo=False)
        graph = onnx.load(exported)
        onnx.helper.set_model_props(graph, {'powergrid.feature_revision': '4.4-auction-discount',
            'powergrid.inference_precision': 'float64', 'powergrid.inference_transform': derivative['inference_transform'],
            'powergrid.source_checkpoint_sha256': digest(source)})
        onnx.checker.check_model(graph); onnx.save(graph, exported); runtime = session(exported)
        max_errors = [0., 0.]; checks = {}; non_nomination_equal = 0
        for label, data in [('nomination', inputs), ('other_phases', other)]:
            for start in range(0, len(data['state']), 64):
                batch = {k: np.ascontiguousarray(data[k][start:start+64]) for k in ('state', 'actions', 'mask')}
                with torch.inference_mode(): native = net(*(torch.from_numpy(batch[k]) for k in ('state', 'actions', 'mask')))
                actual = runtime.run(None, batch)
                for i, (a, b) in enumerate(zip(native, actual)):
                    np.testing.assert_allclose(a.numpy(), b, atol=1e-8, rtol=1e-10)
                    max_errors[i] = max(max_errors[i], float(np.abs(a.numpy()-b).max()))
                np.testing.assert_array_equal(native[0].argmax(1).numpy(), actual[0].argmax(1))
                assert batch['mask'][np.arange(len(actual[0])), actual[0].argmax(1)].all()
                if label == 'other_phases':
                    before = parent.run(None, {'state': np.ascontiguousarray(batch['state'][:, :1217]),
                        'actions': np.ascontiguousarray(batch['actions'][:, :, :101]), 'mask': batch['mask']})
                    np.testing.assert_array_equal(before[0].argmax(1), actual[0].argmax(1))
                    for a, b in zip(before, actual): np.testing.assert_allclose(a, b, atol=1e-8, rtol=1e-10)
                    non_nomination_equal += len(batch['state'])
            checks[label] = len(data['state'])
        result = {'arm': name, 'complete': True, 'checks': checks, 'all_native_onnx_choices_equal': True,
                  'other_phase_parent_choices_equal': non_nomination_equal, 'max_absolute_errors': max_errors,
                  'source_checkpoint_sha256': digest(source),
                  'files': {p.name: digest(p) for p in folder.iterdir() if p.is_file()}, 'qualified': False}
        save(folder/'report.json', result); results.append(result); print(json.dumps(result), flush=True)
    save(RESULT, {'complete': True, 'arms': results, 'training_results_sha256': digest(ROOT/'ai/strong/nomination-discount-training-results-v1.json'),
                  'exporter_sha256': digest(__file__), 'new_games': 0, 'new_gradients': 0, 'qualified': False,
                  'remaining': 'Current public-serving fixtures and fresh full-game development evaluation.'})


if __name__ == '__main__': main()
