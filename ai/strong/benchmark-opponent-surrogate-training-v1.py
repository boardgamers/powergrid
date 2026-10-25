"""Bounded HF GPU gradient/runtime calibration; outputs are never candidates."""
import importlib.util
import math
import os
from pathlib import Path
import resource
import time

import numpy as np
import torch
from torch.nn import functional as F
from strategic_collection import ROOT, read, write, digest
from model_opponent_surrogate_v1 import OpponentSurrogate
from opponent_surrogate_training_v1 import group_weights, metrics
from policy_iteration_evidence_archive import upload_evidence

DESIGN = ROOT/'ai/strong/opponent-surrogate-training-design-v1.json'


def main(data, report, output, recovery_seconds):
    assert os.environ.get('POWERGRID_HF_TRAINING') == '1' and torch.cuda.is_available(), 'HF GPU calibration only'
    assert set(data) == {'train', 'validation'} and report['test_records_included'] is False
    design = read(DESIGN); output.mkdir(parents=True, exist_ok=False)
    status = {'case': 'opponent-surrogate-training-calibration-v1', 'stage': 'running', 'runtime_calibration_only': True, 'training_eligible': False,
              'source_revision': os.environ['SOURCE_REVISION'], 'source_sha256': os.environ['SOURCE_SHA256'],
              'design_sha256': digest(DESIGN), 'data_check_sha256': os.environ['DATA_CHECK_SHA256'],
              'recovery_seconds': recovery_seconds, 'gradients': True, 'training_location': 'HF Jobs',
              'qualification_eligible': False, 'test_labels_used': False, 'reserved_final_seeds_used': False}
    began = time.monotonic()
    try:
        torch.set_num_threads(4); torch.use_deterministic_algorithms(True)
        torch.backends.cuda.matmul.allow_tf32 = False; torch.backends.cudnn.allow_tf32 = False
        torch.manual_seed(14099); rng = np.random.default_rng(14099)
        model = OpponentSurrogate(**design['model_args']).cuda()
        optimizer = torch.optim.AdamW(model.parameters(), lr=design['learning_rate'], weight_decay=design['weight_decay'])
        fields = ('state', 'actions', 'mask', 'target')
        nbytes = sum(data[s][k].nbytes for s in data for k in fields)
        free, total = torch.cuda.mem_get_info(); resident = nbytes <= .5 * free
        gpu = {s: {k: torch.from_numpy(np.array(data[s][k], copy=True)).cuda() for k in fields} for s in data} if resident else None
        weights = torch.from_numpy(group_weights(data['train'])).cuda()
        active = np.flatnonzero(data['train']['mask'].sum(1) > 1)
        torch.cuda.synchronize(); initialization_seconds = time.monotonic() - began
        torch.cuda.reset_peak_memory_stats()

        def batch(split, ids):
            if gpu is not None:
                ids = torch.as_tensor(ids, dtype=torch.long, device='cuda')
                return {k: v[ids] for k, v in gpu[split].items()}
            return {k: torch.from_numpy(np.array(data[split][k][ids], copy=True)).cuda() for k in fields}

        measured_start = None
        for update in range(16 + 128):
            if update == 16:
                torch.cuda.synchronize(); measured_start = time.monotonic()
            ids = rng.choice(active, size=design['batch_size'], replace=True); b = batch('train', ids)
            logits = model(b['state'], b['actions'], b['mask'])
            loss = (F.cross_entropy(logits, b['target'], reduction='none') * weights[torch.as_tensor(ids, device='cuda')]).mean()
            assert torch.isfinite(loss)
            optimizer.zero_grad(set_to_none=True); loss.backward()
            norm = torch.nn.utils.clip_grad_norm_(model.parameters(), design['max_grad_norm'])
            assert torch.isfinite(norm)
            optimizer.step()
        torch.cuda.synchronize(); step_seconds = (time.monotonic() - measured_start) / 128
        evaluation_seconds = {}; model.eval()
        for split in ('train', 'validation'):
            start = time.monotonic(); scores = []
            with torch.inference_mode():
                for lo in range(0, len(data[split]['target']), design['batch_size']):
                    ids = np.arange(lo, min(lo + design['batch_size'], len(data[split]['target'])))
                    b = batch(split, ids); scores.append(model(b['state'], b['actions'], b['mask']).cpu().numpy())
            metrics(np.concatenate(scores), data[split])
            evaluation_seconds[split] = time.monotonic() - start
        checkpoint = {'architecture': 'opponent_surrogate_v1', 'model_args': design['model_args'],
                      'state_dict': {k: v.detach().cpu().clone() for k, v in model.state_dict().items()},
                      'feature_revision': design['feature_revision'], 'state_dim': 1217, 'action_dim': 101,
                      'max_candidates': 6, 'runtime_calibration_only': True, 'updates': 144,
                      'training_location': 'HF Jobs', 'training_eligible': False, 'qualification_eligible': False}
        torch.save(checkpoint, output/'calibration-only.pt')
        spec = importlib.util.spec_from_file_location('surrogate_calibration_export', Path(__file__).with_name('export-opponent-surrogate-v1.py'))
        exporter = importlib.util.module_from_spec(spec); spec.loader.exec_module(exporter)
        start = time.monotonic(); exporter.export(output/'calibration-only.pt', output/'derivative')
        parity = exporter.verify(output/'derivative', data); export_seconds = time.monotonic() - start
        updates = math.ceil(len(active) / design['batch_size']) * design['epochs']
        estimated = len(design['seeds']) * (initialization_seconds + updates * step_seconds +
                    (design['epochs'] + 1) * evaluation_seconds['validation'] + 2 * evaluation_seconds['train'] + export_seconds)
        status.update(stage='complete', gpu=torch.cuda.get_device_name(), gpu_total_bytes=total,
            gpu_resident_inputs=resident, input_bytes=nbytes, initialization_seconds=initialization_seconds,
            warmup_updates=16, measured_updates=128, mean_update_seconds=step_seconds,
            train_nonforced_rows=len(active), evaluation_seconds=evaluation_seconds, export_seconds=export_seconds,
            full_four_seed_estimated_seconds=estimated, peak_gpu_allocated_bytes=torch.cuda.max_memory_allocated(),
            peak_host_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
            exact_export_positions=parity['exact_choices'], parity_sha256=digest(output/'derivative/parity.json'))
    except BaseException as error:
        status.update(stage='failed', error=type(error).__name__ + ': ' + str(error)); raise
    finally:
        status['seconds'] = time.monotonic() - began; write(output/'job.json', status)
        write(output/'manifest.json', {str(p.relative_to(output)): digest(p) for p in sorted(output.rglob('*')) if p.is_file()})
        evidence = upload_evidence(output)
        print({'status': status, 'evidence': evidence}, flush=True)
