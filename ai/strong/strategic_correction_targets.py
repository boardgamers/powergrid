"""Soft paired targets; retain covariance between continuations of the same world."""
import numpy as np

MODES = ('neural', 'neural_economic')
BATCHES = ('a', 'b')


def targets(rows, noise_floor=.05, minimum_weight=.25):
    assert set(rows) == {(mode, batch) for mode in MODES for batch in BATCHES}
    first = rows[MODES[0], BATCHES[0]]
    options, proposal = first['options'], first['model_proposal']
    assert len(set(options)) == len(options) and proposal in options
    combined = []
    for batch in BATCHES:
        worlds = []
        for mode in MODES:
            row = rows[mode, batch]
            assert row['mode'] == mode and row['batch'] == batch and row['usable']
            assert row['options'] == options and row['model_proposal'] == proposal
            assert row['rootId'] == first['rootId'] and row['public_root_sha256'] == first['public_root_sha256']
            assert row['seed'] == 'strategic-teacher-public-v1-'+row['rootId']+'-'+batch
            assert row['samples'] == first['samples'] and row['samples'] >= 2
            x = np.asarray([row['paired_advantages_over_proposal'][str(i)] for i in options], np.float64)
            assert x.shape == (len(options), row['samples']) and np.isfinite(x).all()
            assert (np.abs(x) <= 1).all() and (x[options.index(proposal)] == 0).all()
            worlds.append(x)
        # Both modes use the same public world draws: average per world FIRST.
        combined.append(np.mean(worlds, axis=0))
    paired = np.concatenate(combined, axis=1)
    mean = paired.mean(axis=1)
    variance_of_mean = paired.var(axis=1, ddof=1) / paired.shape[1]
    precision = np.clip(noise_floor**2 / (noise_floor**2 + variance_of_mean), minimum_weight, 1.)
    return {'target': mean, 'variance_of_mean': variance_of_mean, 'precision': precision,
            'samples': paired.shape[1], 'proposal_index': options.index(proposal)}


def regression_loss(scores, target, precision, mask, proposal_index):
    """Mean root loss; parent action is the fixed zero reference, never a winner label."""
    import torch
    delta = scores - scores.gather(1, proposal_index[:, None])
    nonparent = mask & (torch.arange(mask.shape[1], device=mask.device)[None, :] != proposal_index[:, None])
    weight = precision * nonparent
    errors = (delta - target).square() * weight
    # Equal total weight per root; uncertain actions receive less weight within a root.
    return (errors.sum(1) / weight.sum(1).clamp(min=1e-12)).mean()
