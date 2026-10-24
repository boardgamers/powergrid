"""Outcome-blind, balanced selection with global public/input de-duplication."""
import argparse
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
import gzip, hashlib, json, subprocess
from pathlib import Path
from strategic_collection import ROOT, read, write, digest

PROTOCOL = ROOT/'ai/strong/policy-iteration-selection-protocol-v2.json'
SOURCE = ROOT/'ai/strong/policy-iteration-collection-source-v2.json'
VERIFIED = ROOT/'ai/runs/policy-iteration-collection-verified-v2'
INDEX = ROOT/'ai/runs/policy-iteration-selection-index-v2'
RUNTIME = ROOT/'ai/runs/policy-iteration-collection-collector-v2'


def rank(row):
    return hashlib.sha256(('policy-iteration-selection-v2:' + row['rootId']).encode()).hexdigest()


def round_band(row):
    return 'early' if row['round'] <= 4 else 'middle' if row['round'] <= 8 else 'late'


def cell(row):
    return '/'.join(map(str, [row['players'], row['behavior'], row['mode'], row['variant'],
                            'sealed' if row['sealed'] else 'open', row['decision'], row['split']]))


def representatives(rows):
    """A validation occurrence excludes every identical input from training."""
    by_input = {}; public_inputs = {}; counts = Counter()
    for row in rows:
        key = row['policy_input_sha256']; public = row['public_root_sha256']
        previous_input = public_inputs.setdefault(public, key)
        assert previous_input == key, 'One public request produced inconsistent inputs'
        counts['raw_' + row['split']] += 1
        previous = by_input.get(key)
        priority = (row['split'] != 'validation', rank(row))
        if previous is None or priority < (previous['split'] != 'validation', rank(previous)):
            by_input[key] = row
    for row in by_input.values(): counts['unique_' + row['split']] += 1
    counts['removed_duplicates'] = len(rows) - len(by_input)
    return list(by_input.values()), dict(counts)


def choose(rows, protocol):
    unique, dedup = representatives(rows)
    groups = defaultdict(list)
    for row in unique: groups[cell(row)].append(row)
    selected = []; coverage = {}
    for key in sorted(groups):
        candidates = groups[key]; split = candidates[0]['split']
        target = protocol['per_cell'][split]; band_target = target // 3
        chosen = []; used = set(); game_counts = Counter(); deal_counts = Counter()
        def take(pool, count):
            # Round robin deals and seats before repeating a trajectory. Hash
            # ranking is independent of rewards, policy agreement or move value.
            for _ in range(count):
                remaining = [r for r in pool if r['rootId'] not in used]
                if not remaining: break
                r = min(remaining, key=lambda x: (deal_counts[x['deal']], game_counts[x['episode']], rank(x)))
                used.add(r['rootId']); chosen.append(r)
                game_counts[r['episode']] += 1; deal_counts[r['deal']] += 1
        for band in protocol['round_bands']:
            take([r for r in candidates if round_band(r) == band], band_target)
        take(candidates, target - len(chosen))
        selected.extend(chosen)
        coverage[key] = {'available': len(candidates), 'selected': len(chosen), 'target': target,
                         'shortfall': target - len(chosen),
                         'round_bands': dict(Counter(round_band(r) for r in chosen)),
                         'deals': len(deal_counts), 'games': len(game_counts)}
    return sorted(selected, key=lambda r: r['rootId']), coverage, dedup


def index_case(folder, output, runtime=RUNTIME, require_verified=True):
    protocol = read(PROTOCOL); source = read(SOURCE)
    inputs = {'roots_sha256': digest(folder/'roots.jsonl.gz'), 'source': source,
              'protocol_sha256': digest(PROTOCOL),
              'selection_code_sha256': digest(Path(__file__)),
              'worker_sha256': digest(ROOT/'ai/strong/policy-iteration-input-hashes.cjs')}
    if require_verified:
        v = read(folder/'verified.json'); assert v['verified'] and v['source'] == source
        assert v['artifacts']['roots.jsonl.gz'] == inputs['roots_sha256']
        inputs['verified_sha256'] = digest(folder/'verified.json')
    if output.exists():
        done = read(output/'complete.json'); assert done['inputs'] == inputs
        assert digest(output/'index.jsonl.gz') == done['index_sha256']; return done
    output.mkdir(parents=True)
    proc = subprocess.Popen(['node', str(ROOT/'ai/strong/policy-iteration-input-hashes.cjs'), str(runtime)],
                            stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
    count = 0
    try:
        with gzip.open(folder/'roots.jsonl.gz', 'rt') as f, gzip.open(output/'index.jsonl.gz', 'wt') as dest:
            while True:
                batch = []
                for _ in range(32):
                    line = f.readline()
                    if not line: break
                    batch.append(json.loads(line))
                if not batch: break
                proc.stdin.write(json.dumps([{k: r[k] for k in ['rootId', 'request', 'legal']} for r in batch]) + '\n')
                proc.stdin.flush(); answers = json.loads(proc.stdout.readline())
                assert len(answers) == len(batch)
                for r, answer in zip(batch, answers):
                    assert r['rootId'] == answer['rootId']
                    meta = {k: r[k] for k in protocol['index_fields']}
                    meta.update(answer); meta['case'] = folder.name
                    dest.write(json.dumps(meta) + '\n'); count += 1
    finally:
        proc.stdin.close(); proc.wait(timeout=10); proc.stdout.close()
        assert proc.returncode == 0
    if require_verified: assert count == v['summary']['roots']
    result = {'inputs': inputs, 'roots': count, 'index_sha256': digest(output/'index.jsonl.gz')}
    write(output/'complete.json', result); return result


def index():
    runtime_source = read(SOURCE)
    # The collector has extracted and checked the frozen archive. Verify the
    # feature entry points here too, rather than using mutable checkout code.
    import tarfile
    from huggingface_hub import hf_hub_download
    archive = Path(hf_hub_download('coyotte508/powergrid-ai-training-v1', runtime_source['archive'],
                                  repo_type='dataset', revision=runtime_source['revision']))
    assert digest(archive) == runtime_source['sha256']
    with tarfile.open(archive) as bundle:
        for member in bundle.getmembers():
            if member.isfile(): assert digest(RUNTIME/member.name) == hashlib.sha256(bundle.extractfile(member).read()).hexdigest()
    cases = sorted(v.parent for v in VERIFIED.glob('*/verified.json'))
    with ThreadPoolExecutor(max_workers=4) as pool:
        for result in pool.map(lambda f: index_case(f, INDEX/f.name), cases):
            print({'roots': result['roots'], 'index_sha256': result['index_sha256']}, flush=True)


def select():
    p = read(PROTOCOL); collection = read(ROOT/'ai/strong/policy-iteration-collection-results-v2.json')
    assert collection['complete'] and collection['games'] == 7680 and len(collection['cases']) == 30
    rows = []; provenance = {}
    for case in sorted(collection['cases']):
        folder = INDEX/case; done = read(folder/'complete.json')
        assert done['inputs']['protocol_sha256'] == digest(PROTOCOL)
        assert done['inputs']['selection_code_sha256'] == digest(Path(__file__))
        assert done['inputs']['source'] == read(SOURCE)
        assert done['inputs']['worker_sha256'] == digest(ROOT/'ai/strong/policy-iteration-input-hashes.cjs')
        assert done['inputs']['roots_sha256'] == collection['cases'][case]['artifacts']['roots.jsonl.gz']
        assert done['inputs']['verified_sha256'] == collection['cases'][case]['verified_sha256']
        assert digest(folder/'index.jsonl.gz') == done['index_sha256']
        with gzip.open(folder/'index.jsonl.gz', 'rt') as f: part = [json.loads(line) for line in f]
        assert len(part) == done['roots']; rows.extend(part); provenance[case] = done
    assert len(rows) == collection['roots']
    selected, coverage, dedup = choose(rows, p)
    assert len(coverage) == 720, 'Missing collection cell; inspect before changing selection'
    assert len({r['policy_input_sha256'] for r in selected}) == len(selected)
    assert len({r['public_root_sha256'] for r in selected}) == len(selected)
    assert len({r['rootId'] for r in selected}) == len(selected)
    out = ROOT/'ai/runs/policy-iteration-selected-v2'; out.mkdir(exist_ok=False)
    by_case = defaultdict(set)
    for r in selected: by_case[r['case']].add(r['rootId'])
    seen = set()
    with gzip.open(out/'roots.jsonl.gz', 'wt') as dest:
        for case, ids in sorted(by_case.items()):
            assert digest(VERIFIED/case/'roots.jsonl.gz') == provenance[case]['inputs']['roots_sha256']
            with gzip.open(VERIFIED/case/'roots.jsonl.gz', 'rt') as f:
                for line in f:
                    r = json.loads(line)
                    if r['rootId'] in ids:
                        assert r['rootId'] not in seen; seen.add(r['rootId']); dest.write(line)
    assert seen == {r['rootId'] for r in selected}
    write(out/'selected-index.json', selected)
    report = {'complete': True, 'protocol_sha256': digest(PROTOCOL),
              'collection_results_sha256': digest(ROOT/'ai/strong/policy-iteration-collection-results-v2.json'),
              'source': read(SOURCE), 'selected_roots': len(selected),
              'split_counts': dict(Counter(r['split'] for r in selected)), 'coverage': coverage, 'deduplication': dedup,
              'cross_split_duplicate_inputs': 0, 'cross_split_duplicate_public_states': 0,
              'provenance': provenance, 'artifacts': {f.name: digest(f) for f in out.iterdir()},
              'labels_generated': False, 'trained': False, 'qualification_eligible': False}
    write(out/'selection.json', report)
    write(ROOT/'ai/strong/policy-iteration-selection-results-v2.json', report)
    print({k: report[k] for k in ['selected_roots', 'split_counts', 'deduplication']})


if __name__ == '__main__':
    p = argparse.ArgumentParser(__doc__); p.add_argument('command', choices=['index', 'select']); a = p.parse_args()
    check = read(ROOT/'ai/strong/policy-iteration-selection-preflight-v2.json')
    assert check['passed'] and check['protocol_sha256'] == digest(PROTOCOL)
    assert read(PROTOCOL)['collection_source'] == read(SOURCE)
    for name, sha in check['files'].items(): assert digest(ROOT/name) == sha
    globals()[a.command]()
