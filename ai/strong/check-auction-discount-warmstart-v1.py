"""Check an untrained feature extension against the exact best development model."""
from collections import Counter
from datetime import datetime, timezone
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import time

import numpy as np
import onnx
import onnxruntime as ort
import torch

from model_auction_discount_v1 import extend_checkpoint, policy_from_checkpoint
from model_policy_iteration import policy_from_checkpoint as parent_from_checkpoint
from strategic_correction_check import serving_fixtures
from feature_contract import METADATA_KEY

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'ai/runs/auction-discount-warmstart-v1'
RESULT = ROOT / 'ai/strong/auction-discount-warmstart-results-v1.json'


def read(p): return json.loads(p.read_text())
def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p, value):
    with p.open('x') as f:
        json.dump(value, f, indent=2, allow_nan=False); f.write('\n')


def main():
    assert not OUT.exists() and not RESULT.exists(), 'Inspect prior warm-start evidence before retrying'
    torch.set_num_threads(1)
    torch.manual_seed(14401)
    trained = ROOT / 'ai/runs/policy-iteration-training-verified-v2/frozen'
    pin = read(ROOT / 'ai/strong/policy-iteration-trained-frozen-evidence-v2.json')['candidate_pins']['frozen-1']['pin']
    assert digest(trained / 'verified.json') == pin['training_verified_sha256']
    verified = read(trained / 'verified.json'); assert verified['verified']
    cp_path = trained / 'ensemble-1/best.pt'
    derivative_path = trained / 'ensemble-1/derivative/inference64.pt'
    onnx_path = trained / 'ensemble-1/derivative/inference64.onnx'
    assert digest(cp_path) == verified['artifacts']['ensemble-1/best.pt']
    assert digest(derivative_path) == pin['files']['inference64.pt']
    assert digest(onnx_path) == pin['files']['inference64.onnx']
    old = torch.load(cp_path, map_location='cpu', weights_only=True)
    old64 = torch.load(derivative_path, map_location='cpu', weights_only=True)
    assert old64['numerical_derivative']['source_checkpoint_sha256'] == digest(cp_path)
    assert old['state_dict'].keys() == old64['state_dict'].keys()
    assert all(torch.equal(v, old64['state_dict'][k]) for k, v in old['state_dict'].items())
    artifact = ROOT / 'ai/runs/resource-turn-full-artifact-v4'
    assert digest(artifact / 'manifest.json') == 'ce05c01a314305f5f0b3f7b55f6a8e13355ee0edb9bf5cae2c9688efd55cf795'
    for name, sha in read(artifact / 'manifest.json').items(): assert digest(artifact / name) == sha
    cache = ROOT / 'ai/runs/auction-discount-features-v1/features.npz'
    cache_pin = read(ROOT / 'ai/strong/auction-discount-features-evidence-v1.json')
    assert digest(cache) == cache_pin['feature_cache_sha256']
    fixtures = serving_fixtures()
    worker = ROOT / 'ai/strong/auction-discount-warmstart-inputs-v1.cjs'
    modules = [Path(__file__), worker, ROOT / 'ai/strong/model_auction_discount_v1.py',
        ROOT / 'ai/strong/features-v4_4.cjs', ROOT / 'ai/strong/model_policy_iteration.py',
        ROOT / 'ai/strong/model_strategic.py', ROOT / 'ai/strong/model_discard.py', ROOT / 'ai/strong/model.py']
    OUT.mkdir()
    design = {'created_at': datetime.now(timezone.utc).isoformat(), 'parent': pin,
        'parent_training_checkpoint_sha256': digest(cp_path), 'feature_cache_sha256': digest(cache),
        'serving_fixtures_sha256': digest(fixtures), 'artifact_manifest_sha256': digest(artifact / 'manifest.json'),
        'code': {str(p.relative_to(ROOT)): digest(p) for p in modules},
        'batch_size': 64, 'native_parity': 'Exact outputs against original float32 and float64 networks.',
        'export_parity': 'Exact legal choices; output tolerance 1e-8 absolute / 1e-10 relative, inherited from the existing export checks.',
        'architecture_scope': 'Four frozen-context correction heads; separate zero-initialized 1-to-128 state and 2-to-64 action projections. Existing tensors, shapes, shortlist and fallback routing preserved.',
        'scope': 'Untrained warm-start and export preparation, not experiment admission or strength evidence.',
        'new_hf_jobs': 0, 'new_games': 0, 'new_rollouts': 0, 'new_gradient_updates': 0,
        'qualification_eligible': False, 'reserved_final_seeds_used': False}
    initial = OUT.with_name(OUT.name + '-initial')
    if initial.exists():
        failure = read(initial / 'numerical-first-failure.json')
        assert failure['precision'] == 'float64' and failure['original_extension']['choice_changes'] == 0
        assert failure['copy_parent_prefix_control']['exact'] == [True, True]
        design['preserved_initial_attempt'] = {'directory': str(initial.relative_to(ROOT)),
            'design_sha256': digest(initial / 'design.json'),
            'numerical_diagnosis_sha256': digest(initial / 'numerical-first-failure.json'),
            'repair': 'Preserve original contiguous prefix layout before parent/embedding operations; exact native-output requirement unchanged.'}
    save(OUT / 'design.json', design)
    new = extend_checkpoint(old, parent_sha256=digest(cp_path))
    torch.save(new, OUT / 'warmstart.pt')
    new = torch.load(OUT / 'warmstart.pt', map_location='cpu', weights_only=True)
    new64 = {**new, 'inference_precision': 'float64', 'inference_only': True,
        'inference_transform': old64['inference_transform']}
    torch.save(new64, OUT / 'inference64.pt')
    native_parent = [parent_from_checkpoint(old).eval(), parent_from_checkpoint(old64).eval()]
    native_new = [policy_from_checkpoint(new).eval(), policy_from_checkpoint(new64).eval()]
    torch.onnx.export(native_new[1], (torch.zeros(1, 1218), torch.zeros(1, 8, 103), torch.ones(1, 8, dtype=torch.bool)),
        str(OUT / 'inference64.onnx'), input_names=['state', 'actions', 'mask'], output_names=['logits', 'values'],
        dynamic_axes={'state': {0: 'batch'}, 'actions': {0: 'batch', 1: 'candidates'}, 'mask': {0: 'batch', 1: 'candidates'},
            'logits': {0: 'batch', 1: 'candidates'}, 'values': {0: 'batch'}}, opset_version=17, dynamo=False)
    graph = onnx.load(OUT / 'inference64.onnx')
    onnx.helper.set_model_props(graph, {METADATA_KEY: '4.4-auction-discount', 'powergrid.inference_precision': 'float64',
        'powergrid.inference_transform': old64['inference_transform'], 'powergrid.source_checkpoint_sha256': digest(OUT / 'warmstart.pt')})
    onnx.checker.check_model(graph); onnx.save(graph, OUT / 'inference64.onnx')
    options = ort.SessionOptions(); options.intra_op_num_threads = 1; options.inter_op_num_threads = 1
    exported_parent = ort.InferenceSession(str(onnx_path), options, providers=['CPUExecutionProvider'])
    exported_new = ort.InferenceSession(str(OUT / 'inference64.onnx'), options, providers=['CPUExecutionProvider'])
    report = {'passed': False, 'groups': {}, 'native_exact_positions': 0, 'export_choices_equal': 0,
        'max_export_parent_error': [0., 0.], 'max_export_native_error': [0., 0.]}
    started = time.monotonic()

    def compare(batch, group):
        old_batch = {'state': np.ascontiguousarray(batch['state'][:, :1217]),
            'actions': np.ascontiguousarray(batch['actions'][:, :, :101]), 'mask': batch['mask']}
        with torch.inference_mode():
            for a, b in zip(native_parent, native_new):
                left = a(*(torch.from_numpy(old_batch[k]) for k in ['state', 'actions', 'mask']))
                right = b(*(torch.from_numpy(batch[k]) for k in ['state', 'actions', 'mask']))
                assert all(torch.equal(x, y) for x, y in zip(left, right)), f'Native warm start changed {group}'
            expected = [x.numpy() for x in right]
        previous = exported_parent.run(None, old_batch); actual = exported_new.run(None, batch)
        for i, (a, b, c) in enumerate(zip(actual, previous, expected)):
            assert np.isfinite(a).all()
            np.testing.assert_allclose(a, b, atol=1e-8, rtol=1e-10)
            np.testing.assert_allclose(a, c, atol=1e-8, rtol=1e-10)
            report['max_export_parent_error'][i] = max(report['max_export_parent_error'][i], float(np.abs(a - b).max()))
            report['max_export_native_error'][i] = max(report['max_export_native_error'][i], float(np.abs(a - c).max()))
        choice = actual[0].argmax(1)
        np.testing.assert_array_equal(choice, previous[0].argmax(1))
        np.testing.assert_array_equal(choice, expected[0].argmax(1))
        assert batch['mask'][np.arange(len(choice)), choice].all()
        report['native_exact_positions'] += len(choice); report['export_choices_equal'] += len(choice)
        report['groups'][group] = report['groups'].get(group, 0) + len(choice)

    with np.load(cache, allow_pickle=False) as f:
        data = {k: f[k] for k in ['state', 'actions', 'mask']}
    for start in range(0, 17280, 64):
        compare({k: v[start:start + 64] for k, v in data.items()}, 'cached_training_and_validation')
    print({'cached_positions_exact': 17280, 'seconds': time.monotonic() - started}, flush=True)
    natural = []
    for version in [1, 2]:
        p = ROOT / f'ai/runs/auction-training-history-v{version}/newly-affordable-roots.jsonl'
        receipt = read(ROOT / f'ai/strong/auction-training-history-results-v{version}.json')
        assert digest(p) == receipt['artifacts'][p.name]
        natural.extend(json.loads(line) for line in p.read_text().splitlines())
    assert len(natural) == 10
    positions = [json.loads(line) for line in fixtures.read_text().splitlines()]
    assert len(positions) == 2553
    counts = Counter()
    with (OUT / 'encoder.stderr.log').open('x') as log:
        process = subprocess.Popen(['node', str(worker), str(artifact / 'runtime')], cwd='/tmp',
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=log, text=True)
        try:
            for group, cases in [('serving', positions), ('natural_discount', natural)]:
                for start in range(0, len(cases), 32):
                    chunk = cases[start:start + 32]
                    process.stdin.write(json.dumps([{'request': r['request'], 'legal': r['legal']} for r in chunk]) + '\n'); process.stdin.flush()
                    line = process.stdout.readline(); assert line, 'Encoder failed; inspect preserved stderr'
                    rows = json.loads(line); assert len(rows) == len(chunk)
                    for row, fixture in zip(rows, chunk):
                        batch = {'state': np.asarray([row['state']], np.float32),
                            'actions': np.asarray([row['actions']], np.float32), 'mask': np.ones((1, len(row['actions'])), bool)}
                        compare(batch, group)
                        if group == 'serving': counts[len(fixture['request']['state']['players'])] += 1
                print({'group': group, 'positions_exact': report['groups'][group], 'seconds': time.monotonic() - started}, flush=True)
        finally:
            process.stdin.close()
            try: code = process.wait(timeout=15)
            except subprocess.TimeoutExpired: process.terminate(); process.wait(timeout=5); raise
            process.stdout.close()
        assert code == 0
    # Nonzero diagnostic copies show the new paths are connected; no optimizer or gradient call.
    diagnostic = policy_from_checkpoint(new64).eval()
    batch = {k: torch.from_numpy(v[:64]) for k, v in data.items()}
    with torch.inference_mode():
        context, actions = diagnostic.policy.embeddings(batch['state'].double(), batch['actions'].double())
        head = diagnostic.policy.heads[0]
        def score(s, a): return head(context, actions, s, a)
        s = batch['state'].double(); a = batch['actions'].double()
        zero = s.clone(); zero[:, 1217] = 0
        one = s.clone(); one[:, 1217] = 1
        head.discount_state.weight[0, 0] = .25
        assert not torch.equal(score(zero, a), score(one, a))
        head.discount_state.weight.zero_()
        left = a.clone(); left[:, :, 101:] = 0
        right = left.clone(); right[:, :, 101:] = 1
        head.nomination_price.weight[0, 0] = .25
        assert not torch.equal(score(s, left), score(s, right))
    assert report['native_exact_positions'] == report['export_choices_equal'] == 19843
    assert all(torch.equal(new['state_dict'][k], v) for k, v in old['state_dict'].items())
    assert all(torch.count_nonzero(new['state_dict'][k]) == 0 for k in new['initialized_new_tensors'])
    report.update(passed=True, serving_players=dict(counts), new_tensors=8, new_parameters=1024,
        stored_parent_tensors_unchanged=True, stored_new_tensors_zero=True, diagnostic_paths_connected=True,
        policy_forward_positions=6 * report['native_exact_positions'],
        diagnostic_head_forward_positions=256,
        new_gradient_updates=0, new_hf_jobs=0, new_games=0, new_rollouts=0, training_admitted=False,
        qualification_eligible=False, reserved_final_seeds_used=False, seconds=time.monotonic() - started,
        design_sha256=digest(OUT / 'design.json'),
        artifacts={p.name: digest(p) for p in OUT.iterdir() if p.is_file()},
        interpretation='Untrained schema-4.4 extension and export preserve the old policy on these inputs. Original shortlist/fallback routing remains; missing teacher targets are not repaired by this prototype. No playing-strength claim, training admission or target-8840U latency measurement.')
    save(OUT / 'assessment.json', report); save(RESULT, report)
    print(json.dumps(report), flush=True)


if __name__ == '__main__': main()
