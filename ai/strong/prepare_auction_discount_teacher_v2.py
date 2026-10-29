"""Prepare all saved nomination roots, preserving whole-deal data splits."""
from collections import Counter
from datetime import datetime, timezone
import gzip
import hashlib
from pathlib import Path
import shutil

from prepare_auction_discount_teacher_v1 import ROOT, digest, read, save, object_hash

OUT = ROOT/'ai/runs/auction-discount-teacher-prepared-v2'
PROTOCOL = ROOT/'ai/strong/auction-discount-teacher-protocol-v2.json'
JOBS = 60


def main():
    assert not OUT.exists() and not PROTOCOL.exists(), 'Inspect prior full teacher preparation'
    pilot_path = ROOT/'ai/strong/auction-discount-teacher-results-v1.json'
    pilot = read(pilot_path); previous = read(ROOT/'ai/strong/auction-discount-teacher-protocol-v1.json')
    assert pilot['independently_audited'] and pilot['roots'] == 70 and pilot['caps'] == 0
    path = ROOT/'ai/runs/policy-iteration-selected-v2/roots.jsonl.gz'
    assert digest(path) == previous['parent_roots']['files']['roots.jsonl.gz']
    metadata_path = ROOT/'ai/runs/policy-iteration-features-v2/metadata.json'
    check = read(ROOT/'ai/runs/policy-iteration-features-v2/feature-check.json')
    assert digest(metadata_path) == check['artifacts']['metadata.json']
    metadata = {r['rootId']: r for r in read(metadata_path)}
    roots = []
    with gzip.open(path, 'rt') as stream:
        import json
        for line in stream:
            root = json.loads(line)
            if root['decision'] != 'nomination': continue
            state = root['request']['state']; kind = 'original_control'
            if root['variant'] == 'recharged':
                kind = 'recharged_no_discount'
                if state['plantDiscountActive']:
                    cheap = state['actualMarket'][0]['number']
                    ix = [i for i,m in enumerate(root['legal']) if m['name'] == 'ChoosePowerPlant' and m['data'] == cheap]
                    assert len(ix) == 1
                    kind = 'discount_included' if ix[0] in metadata[root['rootId']]['options'] else 'discount_excluded'
            roots.append({'rootId': root['rootId'], 'players': root['players'], 'sealed': root['sealed'],
                'variant': root['variant'], 'split': root['split'], 'deal': root['deal'], 'kind': kind,
                'source_game_seed': root['gameSeed'], 'public_root_sha256': root['public_root_sha256'],
                'request': root['request'], 'legal': root['legal'], 'old_label_options': metadata[root['rootId']]['options']})
    assert len(roots) == 5760
    roots += [r for r in read(ROOT/previous['roots']['file']) if r['kind'] == 'newly_affordable']
    assert len(roots) == 5770 and len({r['rootId'] for r in roots}) == 5770
    assert len({r['public_root_sha256'] for r in roots}) == 5770
    for r in roots:
        assert r['split'] == ('validation' if r['deal'] in (0,4,8,12) else 'train')
        assert r['source_game_seed'].startswith('policy-iteration-training-v2-')
        assert object_hash(r['request']) == r['public_root_sha256']
    splits = dict(Counter(r['split'] for r in roots)); assert splits == {'validation': 1444, 'train': 4326}
    kinds = dict(Counter(r['kind'] for r in roots)); assert kinds['discount_excluded'] == 397
    # Balance by measured continuation cost without reading action values.
    def cost(r): return 64*len(r['legal'])*pilot['costs_by_player_count'][str(r['players'])]['seconds_per_rollout']
    bins = [[] for _ in range(JOBS)]; costs = [0.]*JOBS
    for root in sorted(roots, key=lambda r: (-cost(r), hashlib.sha256(r['rootId'].encode()).hexdigest())):
        index = min(range(JOBS), key=lambda i: (costs[i], i)); bins[index].append(root); costs[index] += cost(root)
    OUT.mkdir(); bundle = OUT/'bundle'; (bundle/'shards').mkdir(parents=True)
    for index, rows in enumerate(bins): save(bundle/f'shards/{index:02d}.json', rows)
    index_rows = [{'shard': i, 'name': f'pg-discount-teacher-v2-{i:02d}', 'file': f'shards/{i:02d}.json',
                   'sha256': digest(bundle/f'shards/{i:02d}.json'), 'roots': len(rows),
                   'rollouts': sum(64*len(r['legal']) for r in rows), 'estimated_seconds': costs[i]}
                  for i,rows in enumerate(bins)]
    protocol = {**{k: previous[k] for k in ('current_source','artifact_manifest_sha256','teacher_policy',
                 'teacher_policy_sha256','parent_roots','historical_roots')},
        'version': 2, 'created_at': datetime.now(timezone.utc).isoformat(),
        'purpose': 'Current-engine all-legal nomination labels for a controlled discount/coverage training experiment.',
        'selection': 'All 5760 saved nomination positions plus all ten naturally recovered newly affordable positions. No outcome filtering.',
        'pilot_results_sha256': digest(pilot_path), 'roots': 5770, 'splits': splits, 'kinds': kinds,
        'worlds': 64, 'independent_halves': [[0,32],[32,64]], 'workers': 4, 'threads': 1,
        'max_steps': 2400, 'mode': 'neural_population', 'shards': index_rows,
        'planned_rollouts': sum(r['rollouts'] for r in index_rows), 'estimated_job_hours': sum(costs)/3600,
        'estimate_limit': 'Linear extrapolation from the small stratified pilot; excludes setup/upload overhead and is not a completion guarantee.',
        'target_policy': 'Retain all terminal outcomes, exact credits and paired margins. Require independent audit and assess agreement between fixed 32-world halves before admitting training targets. Keep capped/failed data as evidence; never treat it as a loss or silently replace it.',
        'candidate_experiment': previous['candidate_experiment'], 'evaluation': previous['evaluation'],
        'whole_deal_split_preserved': True, 'no_target_reuse_from_old_engine': True,
        'automatic_retries': False, 'gradients_in_teacher_jobs': False,
        'candidate_selected': False, 'qualified': False, 'reserved_final_seeds_used': False}
    save(PROTOCOL, protocol); shutil.copyfile(PROTOCOL, bundle/'protocol.json')
    shutil.copyfile(ROOT/'ai/strong/run_auction_discount_teacher_v2.py', bundle/'run_auction_discount_teacher_v2.py')
    shutil.copytree(ROOT/'ai/runs/auction-discount-teacher-prepared-v1/bundle/transport', bundle/'transport')
    save(bundle/'manifest.json', {str(p.relative_to(bundle)):digest(p) for p in sorted(bundle.rglob('*')) if p.is_file()})
    import json
    print(json.dumps({k:protocol[k] for k in ('roots','splits','kinds','planned_rollouts','estimated_job_hours')}),flush=True)


if __name__ == '__main__': main()
