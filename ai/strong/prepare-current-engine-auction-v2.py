"""Repair simultaneous-auction input order in a separate current-engine copy.

The historical evaluated recipe and v1 fixture run remain immutable. Normal
canonical inputs retain exactly the original prior-prompt construction.
"""
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil

from public_policy_development_job_v1 import digest, read

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'ai/runs/current-engine-auction-v1'
OUT = ROOT / 'ai/runs/current-engine-auction-v2'
RESULT = ROOT / 'ai/strong/current-engine-auction-prepared-v2.json'


def save(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2, allow_nan=False); stream.write('\n')


def main():
    assert not OUT.exists() and not RESULT.exists(), 'Inspect previous preparation before retry'
    original = BASE / 'artifact'; previous = read(BASE / 'prepared.json')
    assert digest(original / 'manifest.json') == previous['runtime_manifest_sha256']
    manifest = read(original / 'manifest.json')
    assert all(digest(original / name) == sha for name, sha in manifest.items())
    diagnostic = ROOT / 'ai/runs/current-engine-auction-wrapper-diagnostic-v3'
    failure = read(diagnostic / 'assessment.json')
    assert failure['cases'] == 20 and failure['compatible'] == 4 and len(failure['incompatible']) == 16
    assert failure['runtime_manifest_sha256'] == previous['runtime_manifest_sha256']
    assert digest(diagnostic / 'cases.json') == failure['cases_sha256']
    assert all(row['error']['name'] == 'AssertionError' for row in failure['incompatible'])
    OUT.mkdir(); artifact = OUT / 'artifact'; shutil.copytree(original, artifact)
    worker = artifact / 'ai/strong/sealed-policy-beliefs.cjs'
    old = worker.read_text()
    before = '''    assert.equal(g.currentPlayers[0], seat, 'Teacher uses the canonical simulator actor order');
    const eligible = g.playerOrder.filter(i => !g.players[i].skipAuction && !g.players[i].isDropped);
    const at = eligible.indexOf(seat); assert(at >= 0);
    assert.deepEqual(g.currentPlayers, eligible.slice(at), 'Cannot infer a prior submission order');
    return eligible.slice(0, at).map((actor, index) => {
        const earlier = clone(g);
        earlier.currentPlayers = eligible.slice(index);'''
    after = '''    const eligible = g.playerOrder.filter(i => !g.players[i].skipAuction && !g.players[i].isDropped);
    const waiting = new Set(g.currentPlayers);
    assert.equal(waiting.size, g.currentPlayers.length, 'Duplicate pending player');
    assert(g.currentPlayers.every(i => eligible.includes(i)), 'Ineligible pending player');
    assert(waiting.has(seat), 'The requested player has already submitted');
    const pending = eligible.filter(i => waiting.has(i));
    const committed = eligible.filter(i => !waiting.has(i));
    // Only membership is public: simultaneous submissions and automatic passes
    // need not follow player order. Use deterministic public ordering for the
    // counterfactual prior prompts; never inspect hidden bids or submission times.
    // A canonical prefix gives exactly the historical eligible.slice(index).
    return committed.map((actor, index) => {
        const earlier = clone(g);
        earlier.currentPlayers = [...committed.slice(index), ...pending];'''
    assert old.count(before) == 1, 'Unexpected frozen belief implementation'
    worker.write_text(old.replace(before, after))
    changed_name = 'ai/strong/sealed-policy-beliefs.cjs'
    changed = {**manifest, changed_name: digest(worker)}
    assert changed[changed_name] != manifest[changed_name]
    (artifact / 'manifest.json').write_text(json.dumps(changed, indent=2) + '\n')
    for arm in ('filter', 'conservative_population'):
        p = artifact / f'policies/{arm}.json'; spec = read(p)
        spec['runtime_manifest']['sha256'] = digest(artifact / 'manifest.json')
        p.write_text(json.dumps(spec, indent=2) + '\n')
    assert all(digest(artifact / name) == sha for name, sha in changed.items())
    result = {'created_at': datetime.now(timezone.utc).isoformat(), 'stage': 'prepared_not_admitted',
        'base_prepared_sha256': digest(BASE / 'prepared.json'),
        'base_runtime_manifest_sha256': digest(original / 'manifest.json'),
        'runtime_manifest_sha256': digest(artifact / 'manifest.json'),
        'current_engine_commit': previous['current_engine_commit'],
        'wrapper_diagnostic_sha256': digest(diagnostic / 'assessment.json'),
        'wrapper_cases_sha256': digest(diagnostic / 'cases.json'),
        'changed_files': [changed_name], 'unchanged_files': len(manifest) - 1,
        'preparer_sha256': digest(__file__), 'model_sha256': changed['policy.onnx'],
        'descriptors': {a: read(artifact / f'policies/{a}.json') for a in ('filter', 'conservative_population')},
        'policy_sha256': {a: digest(artifact / f'policies/{a}.json') for a in ('filter', 'conservative_population')},
        'interpretation': 'Public pending-set compatibility repair, not a new learned policy or tuned search setting. Canonical equivalence and actual noncanonical continuations must be tested before admission.',
        'new_hf_jobs': 0, 'new_inference': 0, 'new_full_games': 0, 'new_gradients': 0,
        'qualification_eligible': False, 'reserved_final_seeds_used': False}
    save(OUT / 'prepared.json', result); save(RESULT, result)
    print(json.dumps({'prepared': True, 'manifest_sha256': result['runtime_manifest_sha256'],
                      'changed_files': result['changed_files']}), flush=True)


if __name__ == '__main__': main()
