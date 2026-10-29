"""Bounded original-job observation and independent CPU audit; never submits jobs."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path

import numpy as np
import torch
from huggingface_hub import HfApi

from checkpoint_bucket_archives_v3 import checked_receipt, download_archive
from current_auction_resource_job_v2 import tree
from model_nomination_discount_v1 import from_checkpoint
from prepare_auction_discount_teacher_v2 import ROOT, read, save, digest

OUT = ROOT/'ai/runs/nomination-discount-training-collected-v1'
LAUNCH = ROOT/'ai/strong/nomination-discount-training-launch-v1.json'
DESIGN = ROOT/'ai/strong/nomination-discount-training-design-v1.json'
BUNDLE = ROOT/'ai/runs/nomination-discount-training-source-v1/bundle'
REPORT = ROOT/'ai/strong/nomination-discount-training-results-v1.json'


def snapshot(path, value):
    """Only the mutable observation is replaced; final receipts/audits stay immutable."""
    path = Path(path)
    temp = path.with_suffix('.tmp')
    temp.write_text(json.dumps(value, indent=2, allow_nan=False)+'\n')
    temp.replace(path)


def independent_metrics(head_scores, data, ids, all_legal, margin):
    """Recompute routing and measured targets without the training metric function."""
    scores = np.asarray(head_scores, np.float64)[:, ids]
    parent = data['proposal_index'][ids]
    baseline = np.take_along_axis(scores, parent[None, :, None], axis=2)
    advantages = scores-baseline
    conservative = advantages.mean(0)-advantages.std(0, ddof=0)
    allowed = data['mask'][ids] if all_legal else data['old_mask'][ids]
    conservative[~allowed] = -np.inf
    selected = conservative.argmax(1)
    row = np.arange(len(ids))
    selected = np.where(conservative[row, selected] > margin, selected, parent)
    achieved = data['target'][ids][row, selected]
    best = np.where(data['mask'][ids], data['target'][ids], -np.inf).max(1)
    delta = advantages.mean(0)-advantages.std(0, ddof=0)
    weight = data['precision'][ids]*allowed*(np.arange(allowed.shape[1])[None] != parent[:, None])
    mse = ((delta-data['target'][ids])**2*weight).sum(1)/np.maximum(weight.sum(1), 1e-12)
    return {
        'roots': len(ids), 'weighted_mse': float(mse.mean()),
        'mean_simulated_regret': float((best-achieved).mean()),
        'mean_simulated_advantage': float(achieved.mean()),
        'changes': int((selected != parent).sum()),
        'negative_changes': int(((selected != parent) & (achieved < 0)).sum()),
        'half_a_advantage': float(data['target_a'][ids][row, selected].mean()),
        'half_b_advantage': float(data['target_b'][ids][row, selected].mean()),
    }


def audit(folder, arm, design):
    result = read(folder/'training.json')
    cp = torch.load(folder/'ensemble.pt', map_location='cpu', weights_only=True)
    parent = torch.load(BUNDLE/'parent.pt', map_location='cpu', weights_only=True)
    assert digest(BUNDLE/'parent.pt') == design['parent_sha256']
    assert digest(folder/'ensemble.pt') == result['ensemble_sha256']
    args = {'discount_inputs': arm['discount_inputs'], 'all_legal': arm['all_legal'],
            'heads': 4, 'margin': design['margin'], 'disagreement_penalty': design['ensemble_disagreement_penalty']}
    assert cp['model_args'] == args and cp['seeds'] == design['seeds']
    assert cp['parent_sha256'] == design['parent_sha256']
    assert cp['design_sha256'] == result['design_sha256'] == digest(DESIGN)
    assert cp['data_report_sha256'] == result['data_report_sha256'] == design['data_report_sha256']
    assert result['arm'] == arm and result['complete'] and cp['parent_frozen']
    assert result['training_location'] == 'HF Jobs' and result['training_device'] == 'cuda'
    assert not cp['qualified'] and not result['qualified'] and not result['reserved_final_seeds_used']
    net = from_checkpoint(cp).eval()
    assert all(torch.equal(tensor, parent['state_dict'][key]) for key, tensor in net.parent.state_dict().items())
    assert not any(p.requires_grad for p in net.parent.parameters())
    history = read(folder/'history.json')
    assert set(history) == set(map(str, design['seeds']))
    expected_updates = design['epochs']*((4326+design['batch_size']-1)//design['batch_size'])
    assert result['new_gradient_updates'] == 4*expected_updates
    assert cp['members'] == result['members'] and len(cp['members']) == 4
    for i, (seed, member) in enumerate(zip(design['seeds'], cp['members'])):
        h = history[str(seed)]
        assert [r['epoch'] for r in h] == list(range(0, design['epochs']+1, design['evaluate_every']))
        assert all(r['updates'] == r['epoch']*((4326+design['batch_size']-1)//design['batch_size']) for r in h)
        best = min(h, key=lambda r: r['validation']['mean_simulated_regret'])
        saved = torch.load(folder/f'head-{seed}.pt', map_location='cpu', weights_only=True)
        assert saved['epoch'] == member['best_epoch'] == best['epoch']
        assert saved['updates'] == member['updates'] == expected_updates
        assert saved['seed'] == member['seed'] == seed
        assert saved['parent_sha256'] == design['parent_sha256'] and saved['design_sha256'] == digest(DESIGN)
        assert all(torch.equal(t, saved['head_state'][k]) for k, t in net.heads[i].state_dict().items())
        if not arm['discount_inputs']:
            assert not torch.count_nonzero(saved['head_state']['discount_state.weight'])
            assert not torch.count_nonzero(saved['head_state']['nomination_price.weight'])
    data_report = read(BUNDLE/'data/report.json')
    assert digest(BUNDLE/'data/report.json') == design['data_report_sha256']
    assert all(digest(BUNDLE/'data'/name) == sha for name, sha in data_report['files'].items())
    data = dict(np.load(BUNDLE/'data/data.npz', allow_pickle=False))
    torch.set_num_threads(1)
    scores = []
    with torch.inference_mode():
        for start in range(0, len(data['state']), 128):
            s = torch.from_numpy(data['state'][start:start+128])
            a = torch.from_numpy(data['actions'][start:start+128])
            context, embedding = net.embeddings(s, a)
            scores.append(net.score_heads(context, embedding, s, a).numpy())
    scores = np.concatenate(scores, axis=1)
    recomputed = {}
    for split, ids in [('train', np.flatnonzero(data['train'])), ('validation', np.flatnonzero(~data['train']))]:
        actual = independent_metrics(scores, data, ids, arm['all_legal'], design['margin'])
        expected = result['metrics'][split]
        assert all(actual[k] == expected[k] if isinstance(actual[k], int)
                   else abs(actual[k]-expected[k]) < 1e-5 for k in actual), (arm['name'], split, actual, expected)
        recomputed[split] = actual
    # Actual stored non-nomination positions check the trained routing, not just initialization.
    old = dict(np.load(ROOT/'ai/runs/policy-iteration-features-v2/features.npz', allow_pickle=False))
    ids = np.flatnonzero(~((old['actions'][:, :, 0] > .5) & old['mask']).any(1))[:256]
    s = torch.from_numpy(np.pad(old['state'][ids], ((0, 0), (0, 1))))
    a = torch.from_numpy(np.pad(old['actions'][ids], ((0, 0), (0, 0), (0, 2))))
    m = torch.from_numpy(old['mask'][ids])
    with torch.inference_mode():
        actual = net(s, a, m)
        before = net.parent(s[:, :1217].contiguous(), a[:, :, :101].contiguous(), m)
        assert all(torch.equal(x, y) for x, y in zip(actual, before))
    return {'complete': True, 'arm': arm['name'], 'independently_audited': True,
            'parent_tensors_identical': True, 'non_nomination_rows_exact': len(ids),
            'ensemble_sha256': digest(folder/'ensemble.pt'), 'training_report_sha256': digest(folder/'training.json'),
            'members': cp['members'], 'new_gradient_updates': result['new_gradient_updates'],
            'seconds': result['seconds'], 'metrics': recomputed, 'qualified': False,
            'scope': 'Target fit and frozen-parent scope checks only; no whole-game strength conclusion.'}


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--collect', action='store_true')
    args = parser.parse_args()
    assert not REPORT.exists(), 'Inspect the completed report instead of repeating collection'
    launch = read(LAUNCH); design = read(DESIGN)
    assert launch['design_sha256'] == digest(DESIGN)
    OUT.mkdir(exist_ok=True); api = HfApi(); observations = []; audits = []
    for job in launch['jobs']:
        name = job['arm']; folder = OUT/name; folder.mkdir(exist_ok=True)
        status = api.inspect_job(job_id=job['job_id']).status.stage
        observation = {'arm': name, 'job_id': job['job_id'], 'stage': status}
        final_log = folder/'final.log'
        log = final_log.read_text() if final_log.exists() else '\n'.join(api.fetch_job_logs(job_id=job['job_id'], follow=False))
        if not final_log.exists(): (folder/'observed.log').write_text(log)
        parsed = []
        for line in log.splitlines():
            try: row = json.loads(line)
            except json.JSONDecodeError: continue
            if isinstance(row, dict) and row.get('training_complete'): parsed.append(row)
        observation['final_receipts'] = len(parsed)
        observations.append(observation); print(json.dumps(observation), flush=True)
        if not args.collect or status != 'COMPLETED': continue
        assert len(parsed) == 1 and parsed[0]['arm'] == name, 'Missing or ambiguous original receipt'
        if not final_log.exists():
            with final_log.open('x') as stream: stream.write(log)
        receipt = parsed[0]['bucket_evidence']; checked_receipt(receipt, 'pg-nomination-train-v1-'+name)
        if (folder/'receipt.json').exists(): assert read(folder/'receipt.json') == receipt
        else: save(folder/'receipt.json', receipt)
        raw = folder/'raw'
        if raw.exists(): tree(raw, 'manifest.json', receipt['manifest_sha256'])
        else: download_archive(receipt, 'pg-nomination-train-v1-'+name, raw, api)
        arm = next(a for a in design['arms'] if a['name'] == name)
        audit_path = folder/'audit.json'
        if audit_path.exists():
            report = read(audit_path)
            assert report['collector_sha256'] == digest(__file__) and report['design_sha256'] == digest(DESIGN)
            assert report['job_id'] == job['job_id'] and report['receipt'] == receipt
            assert report['job_log_sha256'] == digest(final_log)
            assert report['ensemble_sha256'] == digest(raw/'ensemble.pt')
            assert report['training_report_sha256'] == digest(raw/'training.json')
        else:
            report = audit(raw, arm, design)
            report.update(job_id=job['job_id'], receipt=receipt, job_log_sha256=digest(final_log),
                          collector_sha256=digest(__file__), design_sha256=digest(DESIGN))
            save(audit_path, report)
        audits.append(report)
    snapshot(OUT/'state.json', {'checked_at': datetime.now(timezone.utc).isoformat(), 'jobs': observations,
                              'collected': len(audits), 'automatic_retries': False})
    if args.collect and len(audits) == len(design['arms']) == 4:
        save(REPORT, {'complete': True, 'created_at': datetime.now(timezone.utc).isoformat(), 'arms': audits,
                      'source': launch['source'], 'design_sha256': digest(DESIGN),
                      'collector_sha256': digest(__file__), 'new_gradient_updates': sum(r['new_gradient_updates'] for r in audits),
                      'qualified': False, 'reserved_final_seeds_used': False,
                      'next': 'Export/serving parity checks and new whole-game development comparison; target fit is not playing strength.'})


if __name__ == '__main__': main()
