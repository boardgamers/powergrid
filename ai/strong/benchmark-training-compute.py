"""Isolated compute timings on real public observations, not model-strength evidence.

HF Jobs only for gradient measurements. Uniform value targets and fixed advantages
are synthetic timing inputs; modified parameters are discarded and never exported.
"""
import argparse
import copy
import gzip
import hashlib
import json
import os
from pathlib import Path
import platform
import time

import numpy as np
import torch
from torch.distributions import Categorical
from huggingface_hub import hf_hub_download, HfApi
from model import policy_from_checkpoint, tensors


def synchronize(device):
    if device == 'cuda':
        torch.cuda.synchronize()


def measure(fn, device, repeats, warmup=3):
    for i in range(warmup):
        fn(i)
    synchronize(device)
    times = []
    for i in range(repeats):
        synchronize(device)
        start = time.perf_counter()
        fn(i)
        synchronize(device)
        times.append((time.perf_counter() - start) * 1000)
    return {'repeats': repeats, 'p50_ms': float(np.median(times)),
            'p95_ms': float(np.percentile(times, 95)), 'mean_ms': float(np.mean(times))}


def run(args):
    if not args.inference_only and os.getenv('POWERGRID_BENCHMARK_PLATFORM') != 'hf-job':
        raise ValueError('Gradient timing is allowed only inside HF Jobs')
    device = args.device
    if device == 'cuda' and not torch.cuda.is_available():
        raise ValueError('CUDA unavailable')
    torch.manual_seed(10021)
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    compressed = args.fixtures.read_bytes()
    if hashlib.sha256(compressed).hexdigest() != args.fixtures_sha256:
        raise ValueError('Fixture hash mismatch')
    rows = [json.loads(line) for line in gzip.decompress(compressed).splitlines()]
    if len(rows) != 2553 or {r['players'] for r in rows} != {2, 3, 4, 5, 6}:
        raise ValueError('Wrong fixture coverage')
    path = Path(hf_hub_download('coyotte508/powergrid-ai-germany-v1',
        'runs/multiplayer-refine-hard-v1/latest.pt', revision='0aeacd5b8e36ece36ba06a77ddfd7b86110d4f3a'))
    model_sha = hashlib.sha256(path.read_bytes()).hexdigest()
    if model_sha != '1f9d1c89908ab036f6e6a54facba94b352bbae005e1ac042d88c60067e895224':
        raise ValueError('Wrong benchmark parent')
    checkpoint = torch.load(path, map_location='cpu', weights_only=True)
    report = {'device': device, 'flavor': os.getenv('BENCHMARK_FLAVOR'),
        'processor': platform.processor(), 'logical_cpus': os.cpu_count(),
        'torch_version': torch.__version__, 'gpu': torch.cuda.get_device_name() if device == 'cuda' else None,
        'model_sha256': model_sha, 'fixtures_sha256': args.fixtures_sha256, 'positions': len(rows),
        'inference_only': args.inference_only, 'tf32': False, 'results': [],
        'limitations': ['Isolated kernels and tensor conversion, without concurrent engine workers or search stragglers.',
            'Serving fixtures are real positions but their mixture need not match new self-play trajectories.',
            'Synthetic optimization targets are for timing only; all modified weights discarded.',
            'Thread and accelerator comparisons use the same indices but run on different hosts. No end-to-end speed claim.']}
    if Path('/proc/cpuinfo').exists():
        report['processor'] = next((s.split(':', 1)[1].strip() for s in Path('/proc/cpuinfo').read_text().splitlines()
                                    if s.startswith('model name')), report['processor'])
    for threads in args.threads:
        torch.set_num_threads(threads)
        for size in args.batch_sizes:
            net = policy_from_checkpoint(checkpoint).to(device).eval()
            indices = np.random.default_rng(10021 + size).integers(len(rows), size=(max(3, args.repeats), size))
            batches = [[rows[i] for i in batch] for batch in indices]
            cached = [tensors(batch, device) for batch in batches]
            def encode(i):
                return tensors(batches[i], device)
            def forward(i):
                with torch.no_grad():
                    return net(*cached[i])
            def rollout(i):
                with torch.no_grad():
                    logits, value = net(*tensors(batches[i], device))
                    distribution = Categorical(logits=logits)
                    chosen = distribution.sample()
                    return chosen.cpu().tolist(), distribution.log_prob(chosen).cpu().tolist(), value.cpu().tolist()
            result = {'threads': threads, 'batch_size': size,
                'batch_indices_sha256': hashlib.sha256(indices.astype('<i8').tobytes()).hexdigest(),
                'max_candidates_per_batch': [int(x[1].shape[1]) for x in cached],
                'valid_actions': [int(x[2].sum().item()) for x in cached],
                'tensorize': measure(encode, device, args.repeats),
                'forward_only': measure(forward, device, args.repeats),
                'rollout_with_tensorize_and_cpu_results': measure(rollout, device, args.repeats)}
            if not args.inference_only and size == 512:
                anchor = copy.deepcopy(net).eval().requires_grad_(False)
                old = []
                with torch.no_grad():
                    for x in cached:
                        logits, _ = anchor(*x)
                        act = logits.argmax(-1)
                        old.append((act, Categorical(logits=logits).log_prob(act)))
                optimizer = torch.optim.AdamW(net.parameters(), lr=.00005, weight_decay=1e-5)
                net.train()
                def update(i):
                    x = tensors(batches[i], device)
                    logits, value = net(*x)
                    distribution = Categorical(logits=logits)
                    act, oldlogp = old[i]
                    ratio = (distribution.log_prob(act) - oldlogp).exp()
                    advantage = torch.linspace(-1, 1, size, device=device)
                    pg = -torch.minimum(ratio * advantage, ratio.clamp(.8, 1.2) * advantage).mean()
                    active = x[0][:, :6]
                    target = active / active.sum(-1, keepdim=True)
                    with torch.no_grad():
                        anchor_probs = anchor(*x)[0].softmax(-1)
                    kl = torch.nn.functional.kl_div(logits.log_softmax(-1), anchor_probs, reduction='none').sum(-1).mean()
                    loss = pg + .5 * (((value - target) ** 2).sum(-1) / active.sum(-1)).mean() \
                        - .005 * distribution.entropy().mean() + .03 * kl
                    optimizer.zero_grad()
                    loss.backward()
                    torch.nn.utils.clip_grad_norm_(net.parameters(), 1)
                    optimizer.step()
                    return float(loss.detach())
                result['optimization_step_with_tensorize'] = measure(update, device, args.repeats)
                del optimizer, anchor
            report['results'].append(result)
            print(json.dumps(result), flush=True)
            del net, cached
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    if args.upload_path:
        HfApi().upload_file(repo_id='coyotte508/powergrid-ai-germany-v1',
            path_in_repo=args.upload_path, path_or_fileobj=args.output)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('fixtures', type=Path)
    p.add_argument('--fixtures-sha256', required=True)
    p.add_argument('--device', choices=['cpu', 'cuda'], required=True)
    p.add_argument('--threads', type=int, nargs='+', default=[1, 4])
    p.add_argument('--batch-sizes', type=int, nargs='+', default=[8, 32, 128, 512])
    p.add_argument('--repeats', type=int, default=15)
    p.add_argument('--inference-only', action='store_true')
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--upload-path')
    run(p.parse_args())
