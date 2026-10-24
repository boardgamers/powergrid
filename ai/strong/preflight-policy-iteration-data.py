"""Exercise new target reduction on every verified pilot sample, without gradients."""
from collections import defaultdict
from copy import deepcopy
import gzip
import json
from unittest.mock import patch

import numpy as np
from strategic_collection import ROOT, read, write, digest
from policy_iteration_data import packed_row, target_arrays, load_labels, MODES, BATCHES


def rejected(fn):
    try:
        fn()
    except AssertionError:
        return
    raise AssertionError('Invalid evidence was accepted')


def main():
    p = read(ROOT/'ai/strong/policy-iteration-labels-protocol-v2.json')
    features = ROOT/'ai/runs/policy-iteration-features-v2'
    check = read(features/'feature-check.json')
    for file, sha in check['artifacts'].items():
        assert digest(features/file) == sha
    metadata = read(features/'metadata.json')
    index = {m['rootId']: m for m in metadata}
    with np.load(features/'features.npz', allow_pickle=False) as f:
        mask = f['mask']
    manifest = read(ROOT/'ai/strong/policy-iteration-labels-results-v2.json')
    # Even a complete manifest must not become usable after losing one shard.
    incomplete = deepcopy(manifest)
    incomplete['complete'] = False
    with patch('policy_iteration_data.hf_hub_download', side_effect=AssertionError('Network called')) as download:
        rejected(lambda: load_labels(incomplete, metadata))
        download.assert_not_called()
    bank, independent = defaultdict(dict), defaultdict(dict)
    rollouts = searches = 0
    first = None
    for shard in p['reuse_pilot']:
        file = ROOT/'ai/runs/policy-iteration-teacher-pilot-verified-v2'/shard['id']/'labels.jsonl.gz'
        assert digest(file) == shard['artifacts']['labels.jsonl.gz']
        with gzip.open(file, 'rt') as stream:
            for row in map(json.loads, stream):
                rid, mode, batch = row['rootId'], row['mode'], row['batch']
                assert rid in shard['root_ids'] and mode == shard['case'][3]
                assert (mode, batch) not in bank[rid]
                bank[rid][mode, batch] = packed_row(row, index[rid], mode)
                options = index[rid]['options']
                outcomes = np.asarray([row['sample_outcomes'][str(i)] for i in options], np.float64)
                independent[rid][mode, batch] = outcomes - outcomes[options.index(index[rid]['model_proposal'])]
                rollouts += len(row['rollouts'])
                searches += 1
                if first is None:
                    first = row
    assert len(bank) == 360 and searches == 1440 and rollouts == 705408
    slots = [i for i, m in enumerate(metadata) if m['rootId'] in bank]
    meta = [metadata[i] for i in slots]
    result = target_arrays(bank, meta, mask[slots])
    for i, m in enumerate(meta):
        rows = independent[m['rootId']]
        worlds = np.concatenate([(rows[MODES[0], b] + rows[MODES[1], b])/2 for b in BATCHES], axis=1)
        n = len(m['options'])
        expected, variance = worlds.mean(1), worlds.var(1, ddof=1)/192
        np.testing.assert_array_equal(result['target'][i, :n], expected)
        np.testing.assert_array_equal(result['variance_of_mean'][i, :n], variance)
        np.testing.assert_array_equal(result['precision'][i, :n], np.clip(.05**2/(.05**2 + variance), .25, 1.))
    adversarial = []
    changes = {
        'public_identity': lambda r: r.update(public_root_sha256='wrong'),
        'whole_deal_split': lambda r: r.update(split='train' if r['split'] == 'validation' else 'validation'),
        'sample_seed': lambda r: r.update(seed='wrong'),
        'missing_terminal': lambda r: r['rollouts'].pop(),
        'duplicate_terminal': lambda r: r['rollouts'].append(deepcopy(r['rollouts'][0])),
        'capped_terminal': lambda r: r['rollouts'][0].update(truncated=True),
        'wrong_roles': lambda r: r['rollouts'][0].update(roles=['economic']*6),
        'wrong_outcome': lambda r: r['rollouts'][0].update(value=r['rollouts'][0]['value'] + .125),
        'extra_unchecked_action': lambda r: r['sample_outcomes'].update({'-9': [0]*96}),
        'missing_batch': None,
    }
    for name, change in changes.items():
        if change:
            row = deepcopy(first)
            change(row)
            rejected(lambda: packed_row(row, index[row['rootId']], row['mode']))
        else:
            broken = deepcopy(bank)
            del broken[meta[0]['rootId']][MODES[0], BATCHES[0]]
            rejected(lambda: target_arrays(broken, meta, mask[slots]))
        adversarial.append(name)
    # Deliberately anticorrelated continuation modes must cancel before variance.
    synthetic = deepcopy(bank[meta[0]['rootId']])
    for (mode, batch), row in synthetic.items():
        for action in row['options']:
            row['paired_advantages_over_proposal'][str(action)] = np.zeros(96) if action == row['model_proposal'] else np.tile([1., -1.], 48)*(1 if mode == MODES[0] else -1)
    cancelled = target_arrays({meta[0]['rootId']: synthetic}, meta[:1], mask[slots[:1]])
    assert (cancelled['target'] == 0).all() and (cancelled['variance_of_mean'] == 0).all()
    report = {'complete': True, 'pilot_positions': 360, 'searches': searches, 'raw_terminal_records_checked': rollouts,
              'independent_target_and_variance_checks': True, 'common_world_covariance_preserved': True,
              'incomplete_manifest_rejected_before_download': True, 'rejected_mutations': adversarial,
              'negative_advantages_retained': int((result['target'][mask[slots]] < 0).sum()),
              'code': {f: digest(ROOT/f) for f in ['ai/strong/policy_iteration_data.py', 'ai/strong/preflight-policy-iteration-data.py']},
              'feature_check_sha256': digest(features/'feature-check.json'),
              'pilot_results_sha256': p['pilot_results_sha256'], 'gradients': False, 'qualification_eligible': False}
    write(ROOT/'ai/strong/policy-iteration-data-preflight-v2.json', report)
    print(report, flush=True)


if __name__ == '__main__':
    main()
