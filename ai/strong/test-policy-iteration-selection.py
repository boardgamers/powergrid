"""Leakage, balancing and independent float32 hashing checks, without gradients."""
from copy import deepcopy
import gzip, hashlib, json, random, subprocess
import numpy as np
from policy_iteration_selection import ROOT, RUNTIME, PROTOCOL, read, write, digest, choose, representatives

p = read(PROTOCOL)
def synthetic(i, split='train', band=1):
    return {'rootId': str(i), 'policy_input_sha256': 'input' + str(i), 'public_root_sha256': 'public' + str(i),
            'players': 2, 'behavior': 'parent', 'mode': 'economic', 'variant': 'original', 'sealed': True,
            'decision': 'bid', 'split': split, 'round': band, 'deal': i % 12, 'episode': i % 24}

rows = [synthetic(i, band=[1, 5, 9][i % 3]) for i in range(180)]
rows += [synthetic(i, 'validation', band=[1, 5, 9][i % 3]) for i in range(180, 240)]
duplicate = synthetic(1000, 'validation'); duplicate['policy_input_sha256'] = rows[0]['policy_input_sha256']
rows.append(duplicate)
unique, _ = representatives(rows)
assert duplicate in unique and rows[0] not in unique
selected, coverage, stats = choose(rows, p)
assert len(selected) == 48 and len(coverage) == 2
assert all(v['shortfall'] == 0 and len(set(v['round_bands'].values())) == 1 for v in coverage.values())
assert len({r['policy_input_sha256'] for r in selected}) == len(selected)
shuffled = deepcopy(rows); random.Random(12007).shuffle(shuffled)
assert choose(shuffled, p) == (selected, coverage, stats), 'Ordering changed the selection'
contaminated = deepcopy(rows)
for r in contaminated: r.update(win=99, reward=-3, teacher_value=1, behavior_proposal=100)
selected2 = choose(contaminated, p)[0]
assert [r['rootId'] for r in selected2] == [r['rootId'] for r in selected]
short, cov, _ = choose(rows[:5], p)
assert len(short) == 5 and next(iter(cov.values()))['shortfall'] == 31
bad = deepcopy(rows[:2]); bad[1]['public_root_sha256'] = bad[0]['public_root_sha256']
try: representatives(bad)
except AssertionError: pass
else: raise AssertionError('Inconsistent public input hash accepted')

# Independent Python implementation of the Node hash, against actual archived
# states from all 12 plumbing cases and both behavior feature schemas.
proc = subprocess.Popen(['node', str(ROOT/'ai/strong/policy-iteration-input-hashes.cjs'), str(RUNTIME)],
                        stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
encoder = subprocess.Popen(['node', str(RUNTIME/'ai/strong/worker.cjs')],
                           stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
def bytes32(v):
    a = np.asarray(v, dtype='<f4').copy(); a[a == 0] = 0
    assert np.isfinite(a).all(); return a.tobytes()
checks = 0
try:
    for folder in sorted((ROOT/'ai/runs/policy-iteration-collection-source-v2/ai/runs/policy-iteration-preflight-v2').glob('*p-*')):
        with gzip.open(folder/'roots.jsonl.gz', 'rt') as f:
            real = sorted(map(json.loads, f), key=lambda r: hashlib.sha256(r['rootId'].encode()).hexdigest())[:16]
        proc.stdin.write(json.dumps(real) + '\n'); proc.stdin.flush(); hashes = json.loads(proc.stdout.readline())
        for r, h in zip(real, hashes):
            encoder.stdin.write(json.dumps({**r['request'], 'featureRevision': '4.2-discard-correction'}) + '\n'); encoder.stdin.flush()
            x = json.loads(encoder.stdout.readline()); assert x['moves'] == r['legal']
            value = hashlib.sha256(json.dumps([1216, len(x['actions']), 100], separators=(',', ':')).encode())
            value.update(bytes32(x['state']))
            for a in sorted(map(bytes32, x['actions'])): value.update(a)
            assert h == {'rootId': r['rootId'], 'policy_input_sha256': value.hexdigest()}; checks += 1
finally:
    for child in [proc, encoder]:
        child.stdin.close(); child.wait(timeout=10); child.stdout.close(); assert child.returncode == 0
assert checks == 192

# Same observable values, reordered actions and signed zero have identical
# hashes. Changing public cash input or action multiplicity changes the hash.
code = '''
process.argv[2]=process.argv[1];
const {inputHash}=require(process.argv[3]);
const assert=require('node:assert/strict');
const state=Array(1216).fill(0), a=Array(100).fill(0), b=Array(100).fill(0); b[0]=1;
const h=inputHash(state,[a,b]); assert.equal(h,inputHash(state,[b,a]));
state[0]=-0; state[1]=-1e-50; assert.equal(h,inputHash(state,[a,b]));
state[2]=.25; assert.notEqual(h,inputHash(state,[a,b])); state[2]=0;
assert.notEqual(h,inputHash(state,[a,b,a]));
state[0]=Infinity; assert.throws(()=>inputHash(state,[a,b]));
'''
subprocess.run(['node', '-e', code, str(RUNTIME), 'unused', str(ROOT/'ai/strong/policy-iteration-input-hashes.cjs')], check=True)
report = {'passed': True, 'real_input_hash_checks': checks, 'split_leakage_contract': True,
          'order_and_outcome_independent_selection': True, 'round_and_deal_balance_contract': True,
          'shortages_explicit': True, 'float32_hash_contract': True, 'protocol_sha256': digest(PROTOCOL),
          'files': {str(f.relative_to(ROOT)): digest(f) for f in [PROTOCOL, ROOT/'ai/strong/policy_iteration_selection.py',
                    ROOT/'ai/strong/policy-iteration-input-hashes.cjs', ROOT/'ai/strong/test-policy-iteration-selection.py']},
          'labels_generated': False, 'trained': False, 'qualification_eligible': False}
write(ROOT/'ai/strong/policy-iteration-selection-preflight-v2.json', report)
print(report)
