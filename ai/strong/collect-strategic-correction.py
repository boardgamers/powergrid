"""Independently verify trained weights, fixed selection, scope and serving exports."""
import argparse
import math
from pathlib import Path
import re
import subprocess
import sys
import numpy as np
import torch
from huggingface_hub import hf_hub_download
from strategic_collection import ROOT, read, write, digest
from strategic_correction_data import load, arrays, metrics
from strategic_correction_check import check as check_scope, serving_fixtures
from strategic_correction_screen import same
from model import policy_from_checkpoint


def compare_metrics(actual, stored):
    assert actual.keys() == stored.keys()
    for key, value in actual.items():
        if isinstance(value, dict):
            compare_metrics(value, stored[key])
        elif isinstance(value, float) and key.startswith('mean_'):
            # Target reductions use float32; counts and selected action fractions remain exact.
            assert math.isfinite(value) and math.isfinite(stored[key]) and abs(value-stored[key]) <= 1e-7, key
        else:
            assert value == stored[key], key


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('revision')
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    assert re.fullmatch('[0-9a-f]{40}', args.revision)
    torch.set_num_threads(1)
    design_path = ROOT/'ai/strong/strategic-correction-design-v1.json'
    manifest_path = ROOT/'ai/strong/strategic-teacher-training-results-v1.json'
    design, manifest = read(design_path), read(manifest_path)
    source = read(ROOT/'ai/strong/strategic-correction-source-v1.json')
    assert digest(design_path) == source['design_sha256']
    assert digest(manifest_path) == source['data_manifest_sha256']
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    repo, prefix = design['parent']['repo'], 'runs/strategic-correction-v1'
    def fetch(name):
        assert not Path(name).is_absolute() and '..' not in Path(name).parts
        target = out/name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(Path(hf_hub_download(repo, prefix+'/'+name, revision=args.revision)).read_bytes())
        return target
    status = read(fetch('training-check.json'))
    for name, value in {'status':'complete', 'source_revision':source['revision'], 'source_sha256':source['sha256'],
        'design_sha256':digest(design_path), 'manifest_sha256':digest(manifest_path),
        'training_location':'HF Jobs', 'qualification_eligible':False}.items():
        assert status[name] == value, name
    assert set(status['runs']) == {str(seed) for seed in design['seeds']}
    for name, sha in status['artifacts'].items(): assert digest(fetch(name)) == sha, name
    rows = load(manifest, design)
    data_summary = read(out/'data-summary.json')
    assert data_summary == {'roots':1920, 'split_counts':{'train':1440,'validation':480},
        'root_ids':[row['rootId'] for row in rows], 'manifest_sha256':digest(manifest_path)}
    parent_pin = design['parent']
    parent_path = hf_hub_download(repo, parent_pin['path'], revision=parent_pin['revision'])
    assert digest(parent_path) == parent_pin['sha256']
    parent = torch.load(parent_path, map_location='cpu', weights_only=True)
    updates_per_epoch = math.ceil(design['train_roots']/design['batch_size'])
    summaries = {}
    fixtures = serving_fixtures()
    for seed in design['seeds']:
        directory = out/str(seed)
        training, history = read(directory/'training.json'), read(directory/'metrics.json')
        assert training == status['runs'][str(seed)] and training['seed'] == seed
        assert training['training_location'] == 'HF Jobs' and training['training_device'] == 'cuda' and training['tf32'] is False
        assert training['parent_tensors_identical'] and training['head_parameters'] == 97473
        assert training['train_roots'] == 1440 and training['validation_roots'] == 480
        assert training['max_allocated_bytes'] > 0 and training['gpu']
        assert [row['epoch'] for row in history] == list(range(0, design['epochs']+1, design['evaluate_every']))
        for row in history:
            assert row['updates'] == row['epoch']*updates_per_epoch
            for split, count in [('train',1440), ('validation',480)]:
                metric = row[split]
                assert metric['roots'] == count and 0 <= metric['changed_fraction'] <= 1
                assert math.isfinite(metric['mean_simulated_regret']) and metric['mean_simulated_regret'] >= 0
                assert len(metric['by_rules_count']) == 20 and sum(x['roots'] for x in metric['by_rules_count'].values()) == count
        selected = min(history, key=lambda row: row['validation']['mean_simulated_regret'])
        assert training['best_epoch'] == selected['epoch']
        assert training['updates'] == design['epochs']*updates_per_epoch
        best = torch.load(directory/'best.pt', map_location='cpu', weights_only=True)
        latest = torch.load(directory/'latest.pt', map_location='cpu', weights_only=True)
        for name, cp in [('best',best), ('latest',latest)]:
            epoch = selected['epoch'] if name == 'best' else design['epochs']
            for field, value in {'architecture':'multiplayer_strategic_correction',
                'feature_revision':design['feature_revision'], 'state_dim':1217, 'action_dim':101,
                'seed':seed, 'epoch':epoch, 'updates':epoch*updates_per_epoch, 'parent':parent_pin,
                'model_args':{'margin':design['margin'], 'parent_margin':design['parent_margin']},
                'design_sha256':digest(design_path), 'data_manifest_sha256':digest(manifest_path),
                'parent_frozen':True, 'training_device':'cuda', 'qualification_eligible':False}.items():
                assert cp[field] == value, (name, field)
            assert all(t.dtype == torch.float32 and torch.isfinite(t).all() for t in cp['state_dict'].values())
            assert all(torch.equal(cp['state_dict']['parent.'+key], value) for key, value in parent['state_dict'].items())
            net = policy_from_checkpoint(cp)
            assert not any(p.requires_grad for p in net.parent.parameters())
            assert sum(p.numel() for p in net.head.parameters()) == 97473
        optimizer = torch.load(directory/'optimizer.pt', map_location='cpu', weights_only=True)
        assert len(optimizer['param_groups']) == 1
        group = optimizer['param_groups'][0]
        assert group['lr'] == design['learning_rate'] and group['weight_decay'] == design['weight_decay']
        assert len(group['params']) == len(list(net.head.parameters())) and set(group['params']) == set(optimizer['state'])
        assert optimizer['state'] and all(int(row['step']) == training['updates'] for row in optimizer['state'].values())
        assert any(torch.count_nonzero(row['exp_avg']) for row in optimizer['state'].values())
        derivative = torch.load(directory/'derivative/inference64.pt', map_location='cpu', weights_only=True)
        assert derivative['inference_only'] and derivative['inference_precision'] == 'float64'
        assert derivative['inference_transform'] == 'float64-exp-div-silu-v1'
        assert derivative['numerical_derivative']['source_checkpoint_sha256'] == digest(directory/'best.pt')
        assert derivative['state_dict'].keys() == best['state_dict'].keys()
        assert all(torch.equal(t, best['state_dict'][key]) for key, t in derivative['state_dict'].items())
        net = policy_from_checkpoint(derivative).eval()
        recomputed = {}
        for split in ['train','validation']:
            subset = [row for row in rows if row['split'] == split]
            data = arrays(subset)
            scores = []
            with torch.inference_mode():
                for begin in range(0, len(subset), 64):
                    state = torch.from_numpy(data['state'][begin:begin+64]).double()
                    actions = torch.from_numpy(data['actions'][begin:begin+64]).double()
                    context, embedding = net.policy.embeddings(state, actions)
                    scores.append(net.policy.head(context, embedding, state, actions).numpy())
            recomputed[split] = metrics(np.concatenate(scores), data, subset, design['margin'])
            compare_metrics(recomputed[split], selected[split])
        for script, label, arguments in [
            ('check-export.py', 'parity', [directory/'derivative/inference64.pt',directory/'derivative/inference64.onnx',fixtures]),
            ('benchmark-serving.py', 'serving', [directory/'derivative/inference64.onnx',fixtures])]:
            with (directory/('independent-'+label+'.log')).open('w') as log:
                subprocess.run([sys.executable, str(ROOT/'ai/strong'/script), *map(str,arguments),
                    '--output', str(directory/('independent-'+label+'.json'))], cwd=ROOT,
                    stdout=log, stderr=subprocess.STDOUT, check=True)
        scope = check_scope(directory/'derivative/inference64.pt', directory/'derivative/inference64.onnx', fixtures, rows)
        write(directory/'independent-scope.json', scope)
        stored_scope = read(directory/'scope.json')
        for field in ['positions', 'eligible', 'changed_eligible', 'outside_scope_actions_preserved',
                      'parent_values_preserved', 'labels_strict_parity', 'label_metrics',
                      'checkpoint_sha256', 'model_sha256']:
            same(scope[field], stored_scope[field])
        parity, serving = read(directory/'independent-parity.json'), read(directory/'independent-serving.json')
        assert parity['positions'] == serving['positions'] == scope['positions'] == 2553
        assert parity['all_actions_match'] and serving['all_moves_legal'] and scope['labels_strict_parity'] == 1920
        assert parity['model_sha256'] == serving['model_sha256'] == scope['model_sha256'] == digest(directory/'derivative/inference64.onnx')
        summaries[str(seed)] = {'training':training, 'selected_epoch':selected['epoch'], 'recomputed':recomputed,
            'scope':scope, 'parity':parity, 'serving':serving, 'parent_tensors_identical':True,
            'model_sha256':scope['model_sha256'], 'best_checkpoint_sha256':digest(directory/'best.pt')}
        print({'seed':seed, 'selected_epoch':selected['epoch'], 'validation':recomputed['validation'], 'verified':True}, flush=True)
    summary = {'verified':True, 'revision':args.revision, 'prefix':prefix, 'source_revision':source['revision'],
        'source_sha256':source['sha256'], 'design_sha256':digest(design_path), 'manifest_sha256':digest(manifest_path),
        'seeds':summaries, 'qualification_eligible':False,
        'scope':'Verified tensors, fixed validation selection, native/ONNX actions and unchanged parent behavior outside strategic choices. Full-game strength remains unproven.'}
    write(out/'verified.json', summary)
    pins = ROOT/'ai/strong/strategic-correction-screen-pins-v1'
    pins.mkdir(exist_ok=True)
    for seed in design['seeds']:
        directory = out/str(seed)
        pin = {'key':str(seed), 'repo':repo, 'revision':args.revision, 'prefix':prefix+f'/{seed}/derivative',
            'files':{name:digest(directory/'derivative'/name) for name in ['inference64.onnx','inference64.pt']},
            'feature_revision':design['feature_revision'], 'seed':seed, 'selected_epoch':summaries[str(seed)]['selected_epoch'],
            'training_verified':True, 'parent_frozen':True, 'strict_parity_positions':2553,
            'training_verified_sha256':digest(out/'verified.json'), 'qualification_eligible':False}
        with (pins/(str(seed)+'.json')).open('x') as stream:
            import json
            json.dump(pin, stream, indent=2)
            stream.write('\n')
    write(ROOT/'ai/strong/strategic-correction-training-results-v1.json', summary)


if __name__ == '__main__':
    main()
