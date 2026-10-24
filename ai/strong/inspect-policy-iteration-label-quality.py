"""Read-only cross-batch diagnostics on a frozen snapshot of verified labels.

Partial completion is selected by scheduling/runtime, so these summaries cannot
estimate the full cohort or qualify a model. They never prepare training inputs,
change thresholds, run gradients, or launch jobs.
"""
import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import gzip
import importlib.util
import json
from pathlib import Path
import shutil

import numpy as np
from strategic_collection import ROOT, read, write, digest
from policy_iteration_data import PROTOCOL, SOURCE, packed_row
from strategic_correction_targets import MODES, BATCHES

MANIFEST = ROOT/'ai/strong/policy-iteration-labels-results-v2.json'
PILOT_MANAGER = ROOT/'ai/strong/manage-policy-iteration-teacher.py'
SPEC = importlib.util.spec_from_file_location('label_quality_pilot', PILOT_MANAGER)
pilot = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(pilot)


def analyze(meta, rows, reused):
    assert set(rows) == {(mode, batch) for mode in MODES for batch in BATCHES}
    options = rows[MODES[0], BATCHES[0]]['options']
    assert all(row['options'] == options for row in rows.values())
    parent = options.index(meta['model_proposal'])
    paired = {}
    for batch in BATCHES:
        paired[batch] = np.mean([[rows[mode, batch]['paired_advantages_over_proposal'][str(i)]
                                 for i in options] for mode in MODES], axis=0)
        assert paired[batch].shape == (len(options), 96)
        assert np.isfinite(paired[batch]).all() and (paired[batch][parent] == 0).all()
    directions = pilot.cross_batch_recommendations(paired, options, parent)
    for direction in directions:
        action = options.index(direction['action'])
        direction['selection_gain'] = float(paired[direction['selection_batch']][action].mean())
    return {**meta, 'reused_pilot': reused, 'directions': directions,
            'unmargined_batches_agree': len({d['action'] for d in directions if d['margin'] == 0.}) == 1}


def summarize(rows):
    result = {'roots': len(rows),
              'deals_represented': len({(r['players'], r['behavior'], r['mode'], r['deal']) for r in rows}),
              'unmargined_batch_agreement': float(np.mean([r['unmargined_batches_agree'] for r in rows])),
              'margins': {}}
    for margin in [0., .025]:
        ds = [d for r in rows for d in r['directions'] if d['margin'] == margin]
        changed = [d for d in ds if d['changed']]
        result['margins'][str(margin)] = {
            'directions': len(ds), 'changes': len(changed),
            'mean_selection_gain': float(np.mean([d['selection_gain'] for d in ds])),
            'mean_cross_batch_simulated_gain': float(np.mean([d['evaluation_gain'] for d in ds])),
            'changed_negative_directions': sum(d['evaluation_gain'] < 0 for d in changed),
            'mean_cross_batch_gain_when_changed': float(np.mean([d['evaluation_gain'] for d in changed])) if changed else None}
    return result


def controls():
    """Selection noise must not be counted as an independent improvement."""
    def rows(a, b):
        return {(m, batch): {'options': [0, 1], 'paired_advantages_over_proposal':
                {'0': np.zeros(96), '1': np.full(96, value)}}
                for m in MODES for batch, value in [('a', a), ('b', b)]}
    meta = {'model_proposal': 0, 'players': 2, 'behavior': 'fixture', 'mode': 'fixture', 'deal': 0}
    noisy = summarize([analyze(meta, rows(.5, -.5), False)])['margins']['0.025']
    assert noisy['mean_selection_gain'] == .25 and noisy['mean_cross_batch_simulated_gain'] == -.25
    assert noisy['changes'] == noisy['changed_negative_directions'] == 1
    for value, expected_changes in [(0., 0), (.025, 0), (.1, 2)]:
        result = summarize([analyze(meta, rows(value, value), False)])['margins']['0.025']
        assert result['changes'] == expected_changes
        assert abs(result['mean_cross_batch_simulated_gain'] - (value if expected_changes else 0.)) < 1e-15
    incomplete = rows(.1, .1)
    incomplete.pop((MODES[0], BATCHES[0]))
    try:
        analyze(meta, incomplete, False)
    except AssertionError:
        pass
    else:
        raise AssertionError('Incomplete continuation modes accepted')
    return {'selection_noise_evaluates_negative': True, 'zero_and_margin_ties_keep_parent': True,
            'consistent_gain_preserved': True, 'incomplete_modes_rejected': True, 'gradients': False}


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--controls-only', action='store_true')
    args = parser.parse_args()
    checked = controls()
    if args.controls_only:
        assert args.output is None
        print(checked)
        return
    assert args.output is not None
    args.output.mkdir(parents=True, exist_ok=False)
    out = args.output
    # Capture exactly one parsed manifest; later collector progress cannot change
    # this cohort or cause newly finished roots to leak into this diagnostic.
    manifest = read(MANIFEST)
    write(out/'label-manifest.json', manifest)
    protocol, source = read(PROTOCOL), read(SOURCE)
    assert manifest['source'] == source and manifest['protocol_sha256'] == digest(PROTOCOL)
    assert manifest['reused_pilot'] == protocol['reuse_pilot']
    assert manifest['complete_shards'] == len(manifest['cases'])
    expected = {s['id']: s for s in protocol['shards']}
    assert set(manifest['cases']) | set(manifest['pending']) == set(expected)
    assert not set(manifest['cases']) & set(manifest['pending'])
    features = ROOT/'ai/runs/policy-iteration-features-v2'
    feature_check = read(features/'feature-check.json')
    assert feature_check['complete'] and feature_check['label_protocol_sha256'] == digest(PROTOCOL)
    assert digest(features/'metadata.json') == feature_check['artifacts']['metadata.json']
    metadata = read(features/'metadata.json')
    assert len(metadata) == len({m['rootId'] for m in metadata}) == 17280
    index = {m['rootId']: m for m in metadata}
    shards, provenance = [], {}
    for old in protocol['reuse_pilot']:
        shards.append({**old, 'mode': old['case'][-1], 'pilot': True})
    for sid, case in manifest['cases'].items():
        assert case['verified'] and case['source'] == source and case['shard'] == expected[sid]
        shards.append({**case, 'id': sid, 'mode': case['shard']['mode'],
                       'root_ids': case['shard']['root_ids'], 'pilot': False})
    present = defaultdict(set)
    pilot_ids = set()
    for shard in shards:
        for rid in shard['root_ids']:
            assert rid in index and shard['mode'] not in present[rid]
            present[rid].add(shard['mode'])
            if shard['pilot']:
                pilot_ids.add(rid)
    complete_ids = {rid for rid, modes in present.items() if modes == set(MODES)}
    assert sum(map(len, present.values())) == manifest['verified_root_mode_pairs']
    bank = defaultdict(dict)
    for serial, shard in enumerate(shards):
        directory = ROOT/('ai/runs/policy-iteration-teacher-pilot-verified-v2' if shard['pilot']
                           else 'ai/runs/policy-iteration-labels-verified-v2')/shard['id']
        assert digest(directory/'verified.json') == shard['verified_sha256']
        verified = read(directory/'verified.json')
        assert verified['verified'] and verified['revision'] == shard['revision'] and verified['prefix'] == shard['prefix']
        for file, sha in shard['artifacts'].items():
            assert digest(directory/file) == sha
        provenance[shard['id']] = {k: shard[k] for k in ['revision', 'prefix', 'verified_sha256', 'artifacts', 'pilot']}
        selected = set(shard['root_ids']) & complete_ids
        if selected:
            seen = set()
            with gzip.open(directory/'labels.jsonl.gz', 'rt') as stream:
                for row in map(json.loads, stream):
                    rid = row['rootId']
                    if rid not in selected:
                        continue
                    key = row['mode'], row['batch']
                    assert key not in bank[rid] and row['mode'] == shard['mode']
                    bank[rid][key] = packed_row(row, index[rid], shard['mode'])
                    seen.add((rid, row['batch']))
            assert seen == {(rid, batch) for rid in selected for batch in BATCHES}
        if (serial+1) % 50 == 0:
            print({'shards_read': serial+1, 'snapshot_shards': len(shards), 'complete_roots_expected': len(complete_ids)}, flush=True)
    assert set(bank) == complete_ids
    records = [analyze(index[rid], bank[rid], rid in pilot_ids) for rid in sorted(complete_ids)]
    groups = {'all': records, 'new_only': [r for r in records if not r['reused_pilot']],
              'pilot_only': [r for r in records if r['reused_pilot']]}
    for field in ['players', 'decision', 'variant', 'sealed', 'behavior', 'mode', 'split']:
        for value in sorted({r[field] for r in metadata}):
            groups[field+'/'+str(value)] = [r for r in records if r[field] == value]
    for n in range(2, 7):
        for split in ['train', 'validation']:
            groups[f'players/{n}/{split}'] = [r for r in records if r['players'] == n and r['split'] == split]
    summaries = {key: summarize(rows) for key, rows in groups.items() if rows}
    coverage = {}
    for n in range(2, 7):
        for split in ['train', 'validation']:
            wanted = [m for m in metadata if m['players'] == n and m['split'] == split]
            coverage[f'{n}p/{split}'] = {'planned': len(wanted), 'both_modes_verified': sum(m['rootId'] in complete_ids for m in wanted)}
    with (out/'records.jsonl').open('x') as stream:
        for row in records:
            stream.write(json.dumps(row)+'\n')
    report = {'checked_at': datetime.now(timezone.utc).isoformat(), 'source': source,
              'label_manifest_sha256': digest(out/'label-manifest.json'), 'protocol_sha256': digest(PROTOCOL),
              'metadata_sha256': digest(features/'metadata.json'), 'snapshot_new_shards': len(manifest['cases']),
              'snapshot_rollouts': manifest['rollouts'], 'planned_roots': len(metadata), 'roots': len(records),
              'roots_incomplete_modes': len(set(present)-complete_ids),
              'roots_without_new_labels': len(set(index)-set(present)), 'coverage': coverage,
              'summary': summaries, 'controls': checked, 'provenance': provenance,
              'records_sha256': digest(out/'records.jsonl'), 'full_cohort': len(records) == len(metadata),
              'gradients': False, 'qualification_eligible': False, 'reserved_final_seeds_used': False,
              'scope': 'Descriptive conditional simulated label quality on a frozen completion snapshot. A chooses/B evaluates and B chooses/A evaluates, with continuation modes averaged within sampled worlds. Every adverse direction retained;fixed margins0/.025. Partial roots are excluded without imputation and listed in coverage. Completion depends on runtime/scheduling,so this cohort is not representative and its directions are not independent games. No confidence intervals,threshold tuning,new training admission,or strength claim.'}
    write(out/'assessment.json', report)
    for file in [Path(__file__), PILOT_MANAGER, ROOT/'ai/strong/policy_iteration_data.py', PROTOCOL, SOURCE]:
        shutil.copy2(file, out/file.name)
    write(out/'manifest.json', {p.name: digest(p) for p in out.iterdir() if p.is_file()})
    print({k: report[k] for k in ['snapshot_new_shards', 'roots', 'roots_incomplete_modes', 'full_cohort']}, flush=True)
    print(summaries['all'], flush=True)


if __name__ == '__main__':
    main()
