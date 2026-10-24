"""Freeze full-data shards only after the complete, assessed teacher pilot."""
from collections import Counter, defaultdict
import hashlib
import math

from strategic_collection import ROOT, read, write, digest

PILOT = ROOT/'ai/strong/policy-iteration-teacher-protocol-v2.json'
RESULTS = ROOT/'ai/strong/policy-iteration-teacher-pilot-results-v2.json'
ASSESSMENT = ROOT/'ai/strong/policy-iteration-teacher-pilot-assessment-v2.json'
OUTPUT = ROOT/'ai/strong/policy-iteration-labels-protocol-v2.json'


def partition(index, pilot_ids, costs):
    """Outcome-blind assignment; only measured wall time determines shard size."""
    assert len({r['rootId'] for r in index}) == len(index)
    assert pilot_ids <= {r['rootId'] for r in index}
    groups = defaultdict(list)
    for row in index:
        if row['rootId'] not in pilot_ids:
            groups[row['players'], row['behavior'], row['mode']].append(row['rootId'])
    shards = []
    for (n, behavior, opponent), ids in sorted(groups.items(), reverse=True):
        ids.sort(key=lambda rid: hashlib.sha256(('policy-iteration-labels-v2:' + rid).encode()).hexdigest())
        for mode in ['neural', 'neural_economic']:
            seconds = costs[n, mode]
            assert math.isfinite(seconds) and seconds > 0
            # 8h timeout, 25% headroom, 10min startup/upload, 2x slowest paired
            # pilot position at the same player count and continuation mode.
            size = min(96, math.floor((28800*.75 - 600)/(2*seconds)))
            assert size >= 1, 'Version a longer timeout; do not shorten games'
            for start in range(0, len(ids), size):
                root_ids = ids[start:start + size]
                shards.append({'id': f'{n}p-{behavior}-{opponent}-{mode}-{start:04d}',
                               'players': n, 'behavior': behavior, 'opponent': opponent,
                               'mode': mode, 'root_ids': root_ids,
                               'admission': {'slowest_pilot_root_seconds': seconds,
                                             'conservative_seconds': len(root_ids)*2*seconds + 600,
                                             'timeout_seconds': 28800, 'headroom': .25}})
    expected = Counter((r['rootId'], mode) for r in index if r['rootId'] not in pilot_ids
                       for mode in ['neural', 'neural_economic'])
    actual = Counter((rid, s['mode']) for s in shards for rid in s['root_ids'])
    assert actual == expected and all(v == 1 for v in actual.values())
    assert all(s['admission']['conservative_seconds'] <= 21600 for s in shards)
    return shards


def main():
    assert not OUTPUT.exists(), 'Never overwrite an admitted plan'
    pilot, report, assessment = read(PILOT), read(RESULTS), read(ASSESSMENT)
    source = read(ROOT/'ai/strong/policy-iteration-teacher-source-v2.json')
    assert report['complete'] and report['complete_cases'] == 60 and report['source'] == source
    assert assessment['source'] == source and assessment['pilot_results_sha256'] == digest(RESULTS)
    assert len(assessment['records']) == 360
    profile_path = ROOT/'ai/strong/policy-iteration-inference-hf-profile-v2.json'
    profile = read(profile_path)
    assert profile['verified'] and profile['full_continuation_cases'] == 4 and profile['rollouts'] == 3072
    assert profile['microbenchmark_positions'] == 2553 and profile['all_microbenchmark_raw_outputs_identical']
    assert all(r['wall_speedup'] > 1.05 for r in profile['cases'])
    helper = 'ai/strong/profile-policy-iteration-continuations.py'
    assert digest(ROOT/helper) == profile['source']['overlays'][helper]
    selection = read(ROOT/'ai/strong/policy-iteration-selection-results-v2.json')
    selected = ROOT/'ai/runs/policy-iteration-selected-v2'
    assert selection['complete'] and selection['selected_roots'] == 17280
    for file, sha in selection['artifacts'].items():
        assert digest(selected/file) == sha
    index = read(selected/'selected-index.json')
    pilot_ids = {r['rootId'] for r in pilot['pilot_roots']}
    assert len(pilot_ids) == 360
    costs = defaultdict(float)
    reuse = []
    for case, entry in report['cases'].items():
        out = ROOT/'ai/runs/policy-iteration-teacher-pilot-verified-v2'/case
        assert digest(out/'verified.json') == entry['verified_sha256']
        verified = read(out/'verified.json')
        assert verified['verified'] and verified['source'] == source
        for file, sha in verified['artifacts'].items():
            assert digest(out/file) == sha
        n, behavior, opponent, mode = verified['case']
        pairs = Counter()
        for timing in entry['timings']:
            pairs[timing['rootId']] += timing['seconds']
        assert len(pairs) == 12
        costs[n, mode] = max(costs[n, mode], max(pairs.values()))
        reuse.append({'id': case, 'case': verified['case'], 'root_ids': sorted(pairs),
                      'revision': verified['revision'], 'prefix': verified['prefix'],
                      'verified_sha256': entry['verified_sha256'], 'artifacts': entry['artifacts']})
    assert Counter((rid, r['case'][-1]) for r in reuse for rid in r['root_ids']) == Counter(
        (rid, mode) for rid in pilot_ids for mode in pilot['modes'])
    shards = partition(index, pilot_ids, costs)
    protocol = {'version': 2, 'purpose': 'Full fixed balanced policy-visited labels; no gradient training.',
                'repo': pilot['repo'], 'base_source': {k: source[k] for k in ['archive', 'revision', 'sha256']},
                'pilot_protocol_sha256': digest(PILOT), 'pilot_results_sha256': digest(RESULTS),
                'pilot_assessment_sha256': digest(ASSESSMENT),
                'selection_results_sha256': digest(ROOT/'ai/strong/policy-iteration-selection-results-v2.json'),
                'roots': pilot['roots'], 'model': pilot['model'], 'ort_threads': 1, 'workers': 24,
                'inference_threads': 4, 'fixed_inference_batch': 64,
                'inference_profile': {k: profile[k] for k in ['job_id', 'revision', 'prefix', 'source', 'wall_speedup', 'artifact_sha256']},
                'inference_profile_sha256': digest(profile_path),
                'samples': {'full': 96, 'control': 2}, 'batches': ['a', 'b'], 'max_steps': 2400,
                'modes': pilot['modes'], 'shards': shards, 'reuse_pilot': reuse,
                'planned_roots': 17280, 'new_roots': 16920, 'reused_roots': 360,
                'selection': 'Exactly the previously frozen whole-deal split and all selected roots. No filtering by outcomes, disagreement, uncertainty or teacher gain.',
                'targets': pilot['targets'], 'beliefs': pilot['beliefs'], 'options': pilot['options'],
                'admission': 'Each job <=96 new roots. 2x slowest measured pilot A+B position at the same count/mode, plus600s overhead, <=75% of8h. First wave is one shard per count/behavior/opponent/mode; require independent verification of all60 before remaining planned shards.',
                'runtime': 'Frozen pilot evaluator, encoder, model, engine and checker; four concurrent inference batches retain exact64-row batches. Independent HF profile checked raw scores/values on2553 fixtures and full choice transcripts/outcomes on3072 continuations. Use conservative serial pilot runtime bounds. Reuse all720 pilot root/mode pairs without resimulation.',
                'trained': False, 'qualification_eligible': False, 'final_seeds_used': False}
    write(OUTPUT, protocol)
    print({'shards': len(shards), 'new_roots': 16920, 'reused_roots': 360,
           'sizes': dict(Counter(len(s['root_ids']) for s in shards)), 'protocol_sha256': digest(OUTPUT)})


if __name__ == '__main__':
    main()
