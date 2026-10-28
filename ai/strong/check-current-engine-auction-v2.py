"""Replay the repaired policy and exercise actual simultaneous-wrapper inputs.

Require exact complete canonical decisions/continuations, except elapsed time,
against the finished v1 engineering run. Then audit both policies on every
wrapper case. No HF jobs, training or new whole-game strength observations.
"""
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import time

from public_policy_arena_v1 import PublicPolicyProcess, validate_response, semantic
from public_policy_final_audit_v1 import artifact_identity
from public_policy_development_job_v1 import digest, read
from population_policy_verification import verify_decision as verify_filter
from opponent_auction_verification_v1 import verify_decision as verify_auction

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'ai/runs/current-engine-auction-v1'
OUT = ROOT / 'ai/runs/current-engine-auction-v2'
ARTIFACT = OUT / 'artifact'
RESULT = ROOT / 'ai/strong/current-engine-auction-fixtures-v2.json'
ARMS = ('filter', 'conservative_population')


def save(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2, allow_nan=False); stream.write('\n')


WRAPPER_INPUTS = '''const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const artifact=process.argv[1],cases=JSON.parse(fs.readFileSync(process.argv[2],'utf8'));
const c=require(path.join(artifact,'ai/core.cjs'));
const prepare=require(path.join(artifact,'ai/strong/population-hybrid-policy.cjs')).preparePolicy;
const rows=cases.map(row=>{const q=row.request,legal=c.candidates(q.state,q.player);
assert.deepEqual(prepare({...q,featureRevision:'4.3-strategic-correction'}).moves,legal);
return {name:row.name,request:q,legal};});
console.log(JSON.stringify(rows));'''


def main():
    assert not (OUT / 'check-intent.json').exists() and not RESULT.exists(), 'Inspect previous run before retry'
    prep = read(OUT / 'prepared.json'); previous = read(BASE / 'assessment.json')
    assert previous['passed'] and previous['counts']['filter']['requests'] == 2693
    assert previous['counts']['conservative_population']['requests'] == 140
    assert digest(BASE / 'decisions.jsonl') == previous['receipts_sha256']
    order = read(OUT / 'order-assessment.json')
    assert order['passed'] and order['canonical_positions_exact'] == 2693
    assert order['wrapper_cases'] == 20 and order['previously_failing_cases_fixed'] == 16
    assert digest(BASE / 'inputs.jsonl') == order['inputs_sha256']
    assert digest(ARTIFACT / 'manifest.json') == prep['runtime_manifest_sha256'] == order['runtime_manifest_sha256']
    assert all(digest(ARTIFACT / name) == sha for name, sha in read(ARTIFACT / 'manifest.json').items())
    assert digest(BASE / 'artifact/manifest.json') == prep['base_runtime_manifest_sha256']
    old_manifest = read(BASE / 'artifact/manifest.json'); manifest = read(ARTIFACT / 'manifest.json')
    assert set(old_manifest) == set(manifest)
    assert [name for name in manifest if manifest[name] != old_manifest[name]] == prep['changed_files']
    canonical = []
    with (BASE / 'decisions.jsonl').open() as stream:
        for line in stream:
            row = json.loads(line)
            if row['arm'] == 'conservative_population': canonical.append(row)
    assert len(canonical) == 140
    cases = ROOT / 'ai/runs/current-engine-auction-wrapper-diagnostic-v3/cases.json'
    assert digest(cases) == prep['wrapper_cases_sha256'] == order['cases_sha256']
    wrappers = json.loads(subprocess.check_output(['node', '-e', WRAPPER_INPUTS, str(ARTIFACT), str(cases)],
                                                 cwd='/tmp', text=True))
    assert len(wrappers) == 20
    paths = [Path(__file__), OUT / 'prepared.json', OUT / 'order-assessment.json',
             BASE / 'assessment.json', BASE / 'decisions.jsonl', BASE / 'inputs.jsonl',
             ARTIFACT / 'manifest.json', cases]
    pins = {str(p.relative_to(ROOT)): digest(p) for p in paths}
    save(OUT / 'check-intent.json', {'started_at': datetime.now(timezone.utc).isoformat(), 'input_hashes': pins,
        'canonical_population_requests': 140, 'wrapper_requests_per_policy': 20,
        'required_canonical_equivalence': 'Exact entire decision including every continuation/world/credit; only elapsedMs excluded. Runtime/descriptor identities are independently checked.',
        'new_hf_jobs': 0, 'new_full_games': 0, 'new_gradients': 0,
        'qualification_eligible': False, 'reserved_final_seeds_used': False})
    identities = {a: artifact_identity(ARTIFACT, f'policies/{a}.json') for a in ARMS}
    counts = {}; baseline = {}; started = time.monotonic()
    with (OUT / 'decisions.jsonl').open('x') as receipts:
        for arm in ARMS:
            rows = wrappers if arm == 'filter' else [*canonical, *wrappers]
            totals = Counter()
            with (OUT / (arm + '.stderr.log')).open('x') as log:
                process = PublicPolicyProcess(ARTIFACT, f'policies/{arm}.json', log)
                try:
                    for i, row in enumerate(rows):
                        q = row['request']; response = process.call(q); n = len(q['state']['players']); seat = q['player']
                        validate_response(response, q, row['legal'], [(seat+j)%n for j in range(n)], identities[arm])
                        decision = {**response['decision'], 'arenaMoves': row['legal']}
                        config = {'players': n, 'arm': 'filter' if arm == 'filter' else 'opponent-auction-v1',
                            'samples': 8, 'model_sha256': identities[arm]['modelSha256'], 'identity': identities[arm]}
                        totals.update((verify_filter if arm == 'filter' else verify_auction)(decision, config, seat))
                        totals['requests'] += 1
                        if arm == 'filter': baseline[row['name']] = response
                        elif i < len(canonical):
                            assert semantic(response['decision']) == semantic(row['response']['decision']), row['name']
                            totals['exact_canonical_decisions'] += 1
                        else:
                            assert response['decision']['modelProposal'] == baseline[row['name']]['decision']['modelProposal']
                            totals['wrapper_requests'] += 1
                        receipts.write(json.dumps({'arm': arm, 'name': row['name'], 'request': q,
                            'legal': row['legal'], 'response': response}, allow_nan=False) + '\n'); receipts.flush()
                        if (i+1) % 5 == 0:
                            print(json.dumps({'arm': arm, 'requests': i+1, 'expected': len(rows),
                                              'rollouts': totals['rollouts']}), flush=True)
                finally: process.close()
            assert totals['rollout_caps'] == 0 and totals['requests'] == len(rows)
            counts[arm] = dict(totals)
    assert counts['conservative_population']['exact_canonical_decisions'] == 140
    assert counts['conservative_population']['wrapper_requests'] == 20
    assert all(digest(ROOT / name) == sha for name, sha in pins.items())
    assert all(digest(ARTIFACT / name) == sha for name, sha in manifest.items())
    result = {'passed': True, 'completed_at': datetime.now(timezone.utc).isoformat(), 'counts': counts,
        'seconds': time.monotonic()-started, 'identities': identities, 'input_hashes': pins,
        'prepared_sha256': digest(OUT / 'prepared.json'), 'intent_sha256': digest(OUT / 'check-intent.json'),
        'receipts_sha256': digest(OUT / 'decisions.jsonl'), 'canonical_public_preparations_exact': 2693,
        'new_hf_jobs': 0, 'new_full_games': 0, 'new_gradients': 0,
        'qualification_eligible': False, 'reserved_final_seeds_used': False,
        'scope': 'Actual current-engine policy/continuation execution and simultaneous-input repair. Not a new strength result; fresh whole-game confirmation and final qualification remain required.'}
    save(OUT / 'assessment.json', result); save(RESULT, result)
    print(json.dumps({'passed': True, 'counts': counts, 'seconds': result['seconds']}), flush=True)


if __name__ == '__main__': main()
