"""HF-only four-seed representation comparison, admitted only with all labels."""
import argparse
import copy
import importlib.util
import os
from pathlib import Path
import time

import numpy as np
import torch
from huggingface_hub import HfApi, hf_hub_download
from strategic_collection import ROOT, read, write, digest
from model_policy_iteration import PolicyIterationPolicy, policy_from_checkpoint, ensemble_advantages
from strategic_correction_targets import regression_loss
from policy_iteration_training import load_bundle, metrics, assemble
from policy_iteration_check import check

DESIGN = ROOT/'ai/strong/policy-iteration-training-design-v2.json'


def raw_scores(net, data, device, batch_size=256):
    output = []
    with torch.inference_mode():
        for start in range(0, len(data['state']), batch_size):
            state = torch.from_numpy(data['state'][start:start+batch_size]).to(device)
            actions = torch.from_numpy(data['actions'][start:start+batch_size]).to(device)
            proposal = torch.from_numpy(data['proposal_index'][start:start+batch_size]).to(device)
            if next(net.parameters()).dtype == torch.float64:
                state, actions = state.double(), actions.double()
            context, embedding = net.embeddings(state, actions)
            values = torch.stack([head(context, embedding, state, actions) for head in net.heads])
            output.append(ensemble_advantages(values, proposal, net.disagreement_penalty).cpu().numpy())
    return np.concatenate(output)


def train(seed, head_type, data, metadata, parent, out, design, data_sha):
    assert os.environ.get('POWERGRID_HF_TRAINING') == '1' and torch.cuda.is_available()
    torch.manual_seed(seed)
    np.random.seed(seed)
    args = {'head_type': head_type, 'heads': 1, 'margin': design['margin'],
            'parent_margin': design['parent_margin'], 'disagreement_penalty': 0.}
    net = PolicyIterationPolicy(**args).cuda().eval()
    net.parent.load_state_dict(parent['state_dict'])
    assert not any(p.requires_grad for p in net.parent.parameters())
    assert sum(p.numel() for p in net.heads[0].parameters()) == design['representations'][head_type]['parameters_per_head']
    splits = {s: np.asarray([i for i, m in enumerate(metadata) if m['split'] == s]) for s in ['train', 'validation']}
    split_data = {s: {k: v[ix] for k, v in data.items()} for s, ix in splits.items()}
    split_meta = {s: [metadata[i] for i in ix] for s, ix in splits.items()}
    tensors = {}
    for split, d in split_data.items():
        tensors[split] = {k: torch.from_numpy(d[k].astype(np.float32) if k in ['target', 'precision'] else d[k]).cuda()
                          for k in ['state', 'actions', 'mask', 'proposal_index', 'target', 'precision']}
        t = tensors[split]
        with torch.no_grad():
            t['context'], t['action_embedding'] = net.embeddings(t['state'], t['actions'])
    optimizer = torch.optim.AdamW(net.heads[0].parameters(), lr=design['learning_rate'], weight_decay=design['weight_decay'])
    rng = np.random.default_rng(seed)
    out.mkdir(exist_ok=False)
    best, best_epoch, best_state = float('inf'), None, None
    history, updates = [], 0
    started = time.monotonic()
    torch.cuda.reset_peak_memory_stats()

    def save(file, epoch, state):
        assert all(torch.equal(net.parent.state_dict()[k].cpu(), v) for k, v in parent['state_dict'].items())
        cp = {'state_dict': {'parent.'+k: v for k, v in parent['state_dict'].items()} |
              {'heads.0.'+k: v.detach().cpu().clone() for k, v in state.items()},
              'architecture': 'policy_iteration_head', 'model_args': args,
              'feature_revision': design['feature_revision'], 'state_dim': design['state_dim'], 'action_dim': design['action_dim'],
              'seed': seed, 'epoch': epoch, 'updates': updates, 'parent': design['parent'], 'parent_frozen': True,
              'design_sha256': digest(DESIGN), 'data_check_sha256': data_sha,
              'training_device': 'cuda', 'qualification_eligible': False}
        torch.save(cp, out/file)

    for epoch in range(design['epochs'] + 1):
        if epoch:
            net.heads[0].train()
            t = tensors['train']
            order = rng.permutation(len(splits['train']))
            for start in range(0, len(order), design['batch_size']):
                ids = torch.as_tensor(order[start:start+design['batch_size']], device='cuda')
                scores = net.heads[0](t['context'][ids], t['action_embedding'][ids], t['state'][ids], t['actions'][ids])
                loss = regression_loss(scores, t['target'][ids], t['precision'][ids], t['mask'][ids], t['proposal_index'][ids])
                assert torch.isfinite(loss)
                optimizer.zero_grad(set_to_none=True)
                loss.backward()
                norm = torch.nn.utils.clip_grad_norm_(net.heads[0].parameters(), design['max_grad_norm'])
                assert torch.isfinite(norm)
                optimizer.step()
                updates += 1
        if epoch % design['evaluate_every'] == 0:
            net.heads[0].eval()
            result = {'epoch': epoch, 'updates': updates, 'seconds': time.monotonic() - started}
            with torch.inference_mode():
                for split, t in tensors.items():
                    scores = []
                    for start in range(0, len(splits[split]), design['batch_size']):
                        ix = slice(start, start + design['batch_size'])
                        scores.append(net.heads[0](t['context'][ix], t['action_embedding'][ix], t['state'][ix], t['actions'][ix]).cpu().numpy())
                    result[split] = metrics(np.concatenate(scores), split_data[split], split_meta[split], design['margin'])
            key = result['validation']['mean_simulated_regret']
            if key < best:
                best, best_epoch, best_state = key, epoch, copy.deepcopy(net.heads[0].state_dict())
                save('best.pt', epoch, best_state)
            history.append(result)
            write(out/'metrics.json', history)
            print({'head_type': head_type, 'seed': seed, 'epoch': epoch, 'best_epoch': best_epoch,
                   'validation': {k: v for k, v in result['validation'].items() if k not in ['groups', 'scope']}}, flush=True)
    save('latest.pt', design['epochs'], net.heads[0].state_dict())
    torch.save(optimizer.state_dict(), out/'optimizer.pt')
    report = {'head_type': head_type, 'seed': seed, 'best_epoch': best_epoch, 'updates': updates,
              'seconds': time.monotonic() - started, 'gpu': torch.cuda.get_device_name(),
              'max_allocated_bytes': torch.cuda.max_memory_allocated(), 'torch_version': str(torch.__version__),
              'training_device': 'cuda', 'training_location': 'HF Jobs', 'tf32': False,
              'parent_tensors_identical': True, 'head_parameters': design['representations'][head_type]['parameters_per_head'],
              'train_roots': 12960, 'validation_roots': 4320, 'qualification_eligible': False}
    write(out/'training.json', report)
    return report


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('data', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--head-type', choices=['frozen', 'public'], required=True)
    parser.add_argument('--upload', action='store_true')
    args = parser.parse_args()
    assert os.environ.get('POWERGRID_HF_TRAINING') == '1', 'Gradients run on HF Jobs only'
    assert os.environ.get('SOURCE_REVISION') and os.environ.get('SOURCE_SHA256') and torch.cuda.is_available()
    assert os.environ['DESIGN_SHA256'] == digest(DESIGN)
    data_sha = digest(args.data/'data-check.json')
    assert os.environ['DATA_CHECK_SHA256'] == data_sha
    torch.set_num_threads(4)
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    design = read(DESIGN)
    data, metadata, data_report = load_bundle(args.data, design)
    pin = design['parent']
    parent_path = hf_hub_download(pin['repo'], pin['path'], revision=pin['revision'])
    assert digest(parent_path) == pin['sha256']
    parent = torch.load(parent_path, map_location='cpu', weights_only=True)
    assert not parent.get('inference_only', False)
    assert all(parent[k] == pin[k] for k in ['architecture', 'seed', 'epoch'])
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    status = {'status': 'running', 'source_revision': os.environ['SOURCE_REVISION'], 'source_sha256': os.environ['SOURCE_SHA256'],
              'design_sha256': digest(DESIGN), 'data_check_sha256': data_sha,
              'head_type': args.head_type, 'training_location': 'HF Jobs', 'qualification_eligible': False}
    try:
        runs = {}
        for seed in design['seeds']:
            runs[str(seed)] = train(seed, args.head_type, data, metadata, parent, out/str(seed), design, data_sha)
        checkpoints = [torch.load(out/str(seed)/'best.pt', map_location='cpu', weights_only=True) for seed in design['seeds']]
        spec = importlib.util.spec_from_file_location('new_export', Path(__file__).with_name('export-policy-iteration.py'))
        exporter = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(exporter)
        ensembles = {}
        for penalty in design['ensemble_disagreement_penalties']:
            key = 'ensemble-' + str(int(penalty))
            directory = out/key
            directory.mkdir(exist_ok=False)
            cp = assemble(checkpoints, design, args.head_type, penalty, digest(DESIGN))
            cp['members'] = [{'seed': seed, 'checkpoint_sha256': digest(out/str(seed)/'best.pt')} for seed in design['seeds']]
            torch.save(cp, directory/'best.pt')
            exporter.export(directory/'best.pt', directory/'derivative')
            parity = check(directory/'derivative/inference64.pt', directory/'derivative/inference64.onnx', args.data)
            write(directory/'parity-scope.json', parity)
            exported = torch.load(directory/'derivative/inference64.pt', map_location='cpu', weights_only=True)
            net = policy_from_checkpoint(exported).eval()
            scores = raw_scores(net.policy, data, 'cpu')
            diagnostics = {}
            for split in ['train', 'validation']:
                ids = np.asarray([i for i, m in enumerate(metadata) if m['split'] == split])
                diagnostics[split] = metrics(scores[ids], {k: v[ids] for k, v in data.items()}, [metadata[i] for i in ids], design['margin'])
            write(directory/'calibration.json', diagnostics)
            ensembles[key] = {'penalty': penalty, 'calibration': diagnostics, 'parity': parity,
                              'member_seeds': design['seeds'], 'qualification_eligible': False}
        status.update(status='complete', runs=runs, ensembles=ensembles)
    except BaseException as error:
        status.update(status='failed', error=type(error).__name__ + ': ' + str(error))
        raise
    finally:
        status['artifacts'] = {str(p.relative_to(out)): digest(p) for p in out.rglob('*') if p.is_file()}
        write(out/'training-check.json', status)
        if args.upload:
            HfApi().upload_folder(repo_id=design['parent']['repo'], folder_path=out,
                                 path_in_repo='runs/policy-iteration-training-v2-' + args.head_type)
        print({k: v for k, v in status.items() if k not in ['runs', 'ensembles', 'artifacts']}, flush=True)


if __name__ == '__main__':
    main()
