"""Whole-plan coverage and exact control-prefix checks for the full-data wrapper."""
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path

from huggingface_hub import hf_hub_download
from policy_iteration_labels import ROOT, PROTOCOL, read, write, digest, get_model, load_roots, run, check


def normalized(row, samples=2):
    result = {k: v for k, v in row.items() if k != 'timing'}
    result['samples'] = samples
    result['rollouts'] = sorted([r for r in result['rollouts'] if r['sample'] < samples], key=lambda r: r['env'])
    for field in ['sample_outcomes', 'paired_advantages_over_proposal']:
        result[field] = {k: values[:samples] for k, values in result[field].items()}
    return result


def main():
    p = read(PROTOCOL)
    old = read(ROOT/'ai/strong/policy-iteration-teacher-protocol-v2.json')
    assert digest(ROOT/'ai/strong/policy-iteration-teacher-protocol-v2.json') == p['pilot_protocol_sha256']
    assert p['model'] == old['model'] and p['roots'] == old['roots']
    assert p['workers'] == old['workers'] == 24 and p['samples']['full'] == old['samples']['pilot'] == 96
    assert p['inference_threads'] == 4 and p['fixed_inference_batch'] == 64
    assert p['max_steps'] == old['max_steps'] == 2400
    path = ROOT/p['roots']['file']
    assert digest(path) == p['roots']['sha256']
    with gzip.open(path, 'rt') as f:
        index = [{k: r[k] for k in ['rootId', 'players', 'behavior', 'mode', 'split']} for r in map(json.loads, f)]
    assert len(index) == 17280 and Counter(r['split'] for r in index) == {'train': 12960, 'validation': 4320}
    metadata = {r['rootId']: r for r in index}
    assert len(metadata) == len(index)
    seen = Counter()
    assert len({s['id'] for s in p['shards']}) == len(p['shards'])
    for shard in p['shards']:
        assert 1 <= len(shard['root_ids']) <= 96
        a = shard['admission']
        assert a['timeout_seconds'] == 28800 and a['headroom'] == .25
        assert a['conservative_seconds'] == len(shard['root_ids'])*2*a['slowest_pilot_root_seconds'] + 600
        assert a['conservative_seconds'] <= 21600
        for rid in shard['root_ids']:
            r = metadata[rid]
            assert (r['players'], r['behavior'], r['mode']) == (shard['players'], shard['behavior'], shard['opponent'])
            seen[rid, shard['mode']] += 1
    assert len(seen) == 33840
    for reuse in p['reuse_pilot']:
        for rid in reuse['root_ids']:
            seen[rid, reuse['case'][-1]] += 1
    assert seen == Counter((r['rootId'], mode) for r in index for mode in p['modes'])

    out = ROOT/'ai/runs/policy-iteration-labels-preflight-v2'
    out.mkdir(parents=True, exist_ok=False)
    model = get_model(p)
    cases = []
    definitions = [(2, 'nomination', False), (2, 'bid', True), (6, 'bid', False), (6, 'building', True)]
    for n, decision, sealed in definitions:
        eligible = [r for r in old['pilot_roots'] if r['players'] == n and r['decision'] == decision and r['sealed'] == sealed]
        meta = min(eligible, key=lambda r: hashlib.sha256(('full-label-control-v2:' + r['rootId']).encode()).hexdigest())
        for mode in p['modes']:
            case = f"{n}p-{meta['behavior']}-{meta['mode']}-{mode}"
            reuse = next(r for r in p['reuse_pilot'] if r['id'] == case)
            gold_path = Path(hf_hub_download(p['repo'], reuse['prefix'] + '/labels.jsonl.gz', revision=reuse['revision']))
            assert digest(gold_path) == reuse['artifacts']['labels.jsonl.gz']
            with gzip.open(gold_path, 'rt') as f:
                gold = {r['batch']: r for r in map(json.loads, f) if r['rootId'] == meta['rootId']}
            assert set(gold) == {'a', 'b'}
            shard = {'id': f'control-{len(cases)}', 'players': n, 'behavior': meta['behavior'],
                     'opponent': meta['mode'], 'mode': mode, 'root_ids': [meta['rootId']]}
            roots = load_roots(p, shard)
            target = out/shard['id']
            run(target, p, shard, 'control', model, roots)
            summary = check(target, p, shard, 'control', model, roots)
            with gzip.open(target/'labels.jsonl.gz', 'rt') as f:
                rows = list(map(json.loads, f))
            for row in rows:
                assert normalized(row) == normalized(gold[row['batch']]), 'Full-data wrapper changed verified pilot terminal records'
            cases.append({'rootId': meta['rootId'], 'decision': decision, 'mode': mode, 'players': n,
                          'rollouts': summary['rollouts'], 'exact_pilot_prefix': True,
                          'labels_sha256': digest(target/'labels.jsonl.gz')})
            print(cases[-1], flush=True)
    # Also exercise two genuinely new IDs routed through an admitted shard.
    for n, mode in [(2, 'neural'), (6, 'neural_economic')]:
        original = next(s for s in p['shards'] if s['players'] == n and s['mode'] == mode)
        shard = {**original, 'root_ids': original['root_ids'][:1]}
        roots = load_roots(p, shard)
        target = out/f'new-{n}p'
        run(target, p, shard, 'control', model, roots)
        summary = check(target, p, shard, 'control', model, roots)
        cases.append({'rootId': roots[0]['rootId'], 'players': n, 'mode': mode, 'new_root_routing': True,
                      'rollouts': summary['rollouts'], 'labels_sha256': digest(target/'labels.jsonl.gz')})
    # Exercise concurrent batches at production size and compare all96 worlds
    # against the already completed serial pilot, without resimulating a control.
    candidates = [r for r in old['pilot_roots'] if r['players'] == 6 and r['decision'] == 'bid']
    meta = min(candidates, key=lambda r: (-r['round'], r['rootId']))
    mode = 'neural'
    case = f"6p-{meta['behavior']}-{meta['mode']}-{mode}"
    reuse = next(r for r in p['reuse_pilot'] if r['id'] == case)
    gold_path = Path(hf_hub_download(p['repo'], reuse['prefix'] + '/labels.jsonl.gz', revision=reuse['revision']))
    assert digest(gold_path) == reuse['artifacts']['labels.jsonl.gz']
    with gzip.open(gold_path, 'rt') as f:
        gold = {r['batch']: r for r in map(json.loads, f) if r['rootId'] == meta['rootId']}
    assert min(r['timing']['policy_decisions'] for r in gold.values()) >= 96
    shard = {'id': 'full-control', 'players': 6, 'behavior': meta['behavior'],
             'opponent': meta['mode'], 'mode': mode, 'root_ids': [meta['rootId']]}
    roots = load_roots(p, shard)
    target = out/'full-control'
    run(target, p, shard, 'full', model, roots)
    summary = check(target, p, shard, 'full', model, roots)
    with gzip.open(target/'labels.jsonl.gz', 'rt') as f:
        for row in map(json.loads, f):
            assert normalized(row, 96) == normalized(gold[row['batch']], 96)
    cases.append({'rootId': meta['rootId'], 'players': 6, 'mode': mode, 'exact_full_96_world_pilot': True,
                  'rollouts': summary['rollouts'], 'labels_sha256': digest(target/'labels.jsonl.gz')})
    report = {'passed': True, 'protocol_sha256': digest(PROTOCOL), 'model_sha256': model.sha256,
              'planned_root_mode_pairs': 34560, 'new_root_mode_pairs': 33840, 'reused_root_mode_pairs': 720,
              'control_cases': cases, 'rollouts': sum(c['rollouts'] for c in cases),
              'exact_pilot_controls': 8, 'new_root_controls': 2, 'full_96_world_pilot_controls': 1,
              'gradients': False, 'qualification_eligible': False}
    write(out/'preflight.json', report)
    print({'passed': True, 'rollouts': report['rollouts'], 'coverage': 34560}, flush=True)


if __name__ == '__main__':
    main()
