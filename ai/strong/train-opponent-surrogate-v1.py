"""HF-only supervised opponent imitation; never consumes test labels."""
import argparse
import importlib.util
import math
import os
from pathlib import Path
import time

import numpy as np
import torch
from torch.nn import functional as F

from strategic_collection import ROOT, read, write, digest
from model_opponent_surrogate_v1 import OpponentSurrogate
from opponent_surrogate_training_v1 import load_bundle, group_weights, metrics
from policy_iteration_evidence_archive import upload_evidence

DESIGN = ROOT/'ai/strong/opponent-surrogate-training-design-v1.json'


def require_hf():
    assert os.environ.get('POWERGRID_HF_TRAINING') == '1', 'Gradients run on HF Jobs only'
    assert os.environ.get('SOURCE_REVISION') and os.environ.get('SOURCE_SHA256')
    assert torch.cuda.is_available(), 'A measured HF GPU job is required'


def train(seed, data, report, design, data_sha, output):
    require_hf()
    assert seed in design['seeds'] and set(data) == {'train', 'validation'}
    torch.manual_seed(seed); np.random.seed(seed)
    model = OpponentSurrogate(**design['model_args']).cuda()
    assert sum(p.numel() for p in model.parameters()) == design['parameters']
    optimizer = torch.optim.AdamW(model.parameters(), lr=design['learning_rate'], weight_decay=design['weight_decay'])
    rng = np.random.default_rng(seed); output.mkdir(parents=True, exist_ok=False)
    fields = ('state', 'actions', 'mask', 'target')
    nbytes = sum(data[s][k].nbytes for s in data for k in fields)
    resident = nbytes <= .5 * torch.cuda.mem_get_info()[0]
    gpu = {s: {k: torch.from_numpy(np.array(data[s][k], copy=True)).cuda() for k in fields} for s in data} if resident else None
    weights = torch.from_numpy(group_weights(data['train'])).cuda()
    active = np.flatnonzero(data['train']['mask'].sum(1) > 1)
    history = []; best_nll = float('inf'); best_epoch = None; updates = 0
    started = time.monotonic(); torch.cuda.reset_peak_memory_stats()

    def batch(split, ids):
        if gpu is not None:
            indices = torch.as_tensor(ids, dtype=torch.long, device='cuda')
            return {k: v[indices] for k, v in gpu[split].items()}
        return {k: torch.from_numpy(np.array(data[split][k][ids], copy=True)).cuda() for k in fields}

    def evaluate(split):
        predictions = []
        model.eval()
        with torch.inference_mode():
            for start in range(0, len(data[split]['target']), design['batch_size']):
                ids = np.arange(start, min(start + design['batch_size'], len(data[split]['target'])))
                b = batch(split, ids)
                predictions.append(model(b['state'], b['actions'], b['mask']).cpu().numpy())
        return metrics(np.concatenate(predictions), data[split])

    def checkpoint(epoch):
        return {'architecture': 'opponent_surrogate_v1', 'model_args': design['model_args'],
                'state_dict': {k: v.detach().cpu().clone() for k, v in model.state_dict().items()},
                'feature_revision': design['feature_revision'], 'state_dim': 1217, 'action_dim': 101,
                'max_candidates': 6, 'seed': seed, 'epoch': epoch, 'updates': updates,
                'design_sha256': digest(DESIGN), 'data_check_sha256': data_sha,
                'collection_index_sha256': report['collection_index_sha256'],
                'training_location': 'HF Jobs', 'training_device': 'cuda',
                'purpose': 'Opponent behaviour inside simulated continuations; not a qualified focal-player policy.',
                'test_labels_used': False, 'qualification_eligible': False}

    for epoch in range(design['epochs'] + 1):
        mean_loss = None
        if epoch:
            model.train(); order = rng.permutation(active); loss_sum = 0.
            fraction = (epoch - 1) / max(1, design['epochs'] - 1)
            rate = design['learning_rate'] * (.05 + .95 * .5 * (1 + math.cos(math.pi * fraction)))
            for group in optimizer.param_groups: group['lr'] = rate
            for start in range(0, len(order), design['batch_size']):
                ids = order[start:start + design['batch_size']]; b = batch('train', ids)
                logits = model(b['state'], b['actions'], b['mask'])
                loss = (F.cross_entropy(logits, b['target'], reduction='none') * weights[torch.as_tensor(ids, device='cuda')]).mean()
                assert torch.isfinite(loss)
                optimizer.zero_grad(set_to_none=True); loss.backward()
                norm = torch.nn.utils.clip_grad_norm_(model.parameters(), design['max_grad_norm'])
                assert torch.isfinite(norm)
                optimizer.step(); updates += 1; loss_sum += float(loss.detach()) * len(ids)
            mean_loss = loss_sum / len(active)
        row = {'epoch': epoch, 'updates': updates, 'seconds': time.monotonic() - started,
               'training_loss': mean_loss, 'validation': evaluate('validation')}
        if epoch in (0, design['epochs']): row['train'] = evaluate('train')
        key = row['validation']['macro_nll']
        if key < best_nll:
            best_nll, best_epoch = key, epoch
            torch.save(checkpoint(epoch), output/'best.pt')
        history.append(row); write(output/'metrics.json', history)
        print({'seed': seed, 'epoch': epoch, 'best_epoch': best_epoch, 'macro_nll': key,
               'macro_agreement': row['validation']['macro_agreement']}, flush=True)
    torch.save(checkpoint(design['epochs']), output/'latest.pt')
    torch.save(optimizer.state_dict(), output/'optimizer.pt')
    result = {'seed': seed, 'best_epoch': best_epoch, 'best_validation_macro_nll': best_nll,
              'updates': updates, 'seconds': time.monotonic() - started, 'gpu': torch.cuda.get_device_name(),
              'gpu_resident_inputs': resident, 'input_bytes': nbytes,
              'max_allocated_bytes': torch.cuda.max_memory_allocated(), 'torch_version': str(torch.__version__),
              'training_location': 'HF Jobs', 'training_device': 'cuda', 'tf32': False,
              'train_rows': len(data['train']['target']), 'nonforced_train_rows': len(active),
              'validation_rows': len(data['validation']['target']), 'test_labels_used': False,
              'best_checkpoint_sha256': digest(output/'best.pt'), 'qualification_eligible': False}
    write(output/'training.json', result); return result


def main(data_path, output, upload):
    require_hf()
    assert os.environ['DESIGN_SHA256'] == digest(DESIGN)
    assert os.environ['DATA_CHECK_SHA256'] == digest(data_path/'data-check.json')
    assert os.environ.get('CUBLAS_WORKSPACE_CONFIG') == ':4096:8'
    torch.set_num_threads(4); torch.use_deterministic_algorithms(True)
    torch.backends.cuda.matmul.allow_tf32 = False; torch.backends.cudnn.allow_tf32 = False
    design = read(DESIGN); data, report = load_bundle(data_path, design)
    assert design['training_location'] == 'HF Jobs' and design['test_labels_used'] is False
    output = output.resolve(); output.mkdir(parents=True, exist_ok=False)
    status = {'stage': 'running', 'source_revision': os.environ['SOURCE_REVISION'],
              'source_sha256': os.environ['SOURCE_SHA256'], 'design_sha256': digest(DESIGN),
              'data_check_sha256': digest(data_path/'data-check.json'), 'seeds': design['seeds'],
              'training_location': 'HF Jobs', 'qualification_eligible': False, 'test_labels_used': False}
    try:
        status['runs'] = {}
        status['exports'] = {}
        spec = importlib.util.spec_from_file_location('surrogate_exporter', Path(__file__).with_name('export-opponent-surrogate-v1.py'))
        exporter = importlib.util.module_from_spec(spec); spec.loader.exec_module(exporter)
        for seed in design['seeds']:
            torch.cuda.empty_cache()
            status['runs'][str(seed)] = train(seed, data, report, design, status['data_check_sha256'], output/str(seed))
            exported = output/str(seed)/'derivative'
            exporter.export(output/str(seed)/'best.pt', exported)
            parity = exporter.verify(exported, data)
            status['exports'][str(seed)] = {k: parity[k] for k in ('complete', 'positions', 'exact_choices', 'max_absolute_logit_error')}
            status['exports'][str(seed)]['parity_sha256'] = digest(exported/'parity.json')
        status['stage'] = 'complete'
    except BaseException as error:
        status.update(stage='failed', error=type(error).__name__ + ': ' + str(error)); raise
    finally:
        write(output/'job.json', status)
        write(output/'manifest.json', {str(p.relative_to(output)): digest(p) for p in sorted(output.rglob('*')) if p.is_file()})
        if upload: print({'status': status, 'evidence': upload_evidence(output)}, flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('data', type=Path); parser.add_argument('output', type=Path)
    parser.add_argument('--upload', action='store_true'); args = parser.parse_args()
    main(args.data, args.output, args.upload)
