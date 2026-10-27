"""Read-only full-game regression checks against completed original runtime pilots.

No inference, game generation, collection or job submission. All three original
passing jobs must also be verified under v2 before writing the complete report.
"""
import argparse
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CASES = (('conservative_population', 2), ('conservative_population', 6), ('conservative_dual', 2))
OUTPUT = ROOT/'ai/strong/conservative-auction-runtime-regression-v2.json'
NEW_WORKER = 'f796518c0296939e02dbd46a35c5bb925dea085035aa96e6e4f0be40f436dcc9'


def read(path): return json.loads(Path(path).read_text())
def digest(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def no_elapsed(value):
    if isinstance(value, dict): return {k: no_elapsed(v) for k, v in value.items() if k != 'elapsedMs'}
    if isinstance(value, list): return [no_elapsed(v) for v in value]
    return value


def compare_receipt(old, new, old_identity, new_identity, old_worker):
    assert set(old_identity) == set(new_identity)
    assert {k for k in old_identity if old_identity[k] != new_identity[k]} == {'runtimeManifestSha256', 'policySha256'}
    expected = deepcopy(old)
    for key, value in old_identity.items(): assert old['publicResponse'][key] == value
    for key, value in new_identity.items():
        assert new['publicResponse'][key] == value
        expected['publicResponse'][key] = value
    for previous, current in ((expected, new), (expected['publicResponse']['decision'], new['publicResponse']['decision'])):
        assert bool(previous['search']) == bool(current['search'])
        if previous['search']:
            assert len(previous['search']['components']) == len(current['search']['components'])
            for a, b in zip(previous['search']['components'], current['search']['components']):
                assert a['worker_sha256'] == old_worker and b['worker_sha256'] == NEW_WORKER
                a['worker_sha256'] = NEW_WORKER
    assert no_elapsed(expected) == no_elapsed(new), 'Behavioral receipt differs beyond the declared identity/worker changes and elapsed time'


def compare_case(arm, players):
    directories = [ROOT/f'ai/runs/conservative-auction-runtime-hf-v{v}/conservative-auction-runtime-v{v}-{arm}-{players}p' for v in (1, 2)]
    proofs = [read(d/'verified.json') for d in directories]
    identities = [p['row']['identity'] for p in proofs]
    old_manifest = ROOT/'ai/runs/conservative-auction-runtime-prepared-v1/source/artifact/manifest.json'
    assert digest(old_manifest) == identities[0]['runtimeManifestSha256']
    old_worker = read(old_manifest)['ai/strong/surrogate-opponent-continuations-v1.cjs']
    assert digest(ROOT/'ai/runs/conservative-auction-runtime-prepared-v2/source/artifact/ai/strong/surrogate-opponent-continuations-v1.cjs') == NEW_WORKER
    for proof in proofs:
        assert proof['verified'] and proof['stage'] == 'COMPLETED' and proof['review']['games'] == 4*players
        assert proof['review']['audit']['all_receipts_verified'] and proof['review']['audit']['counts']['rollout_caps'] == 0
    shards = [{k: v for k, v in p['row']['shard'].items() if k != 'name'} for p in proofs]
    assert shards[0] == shards[1]
    hashes = {}
    for directory, proof in zip(directories, proofs):
        artifact = directory/'artifacts'; manifest = read(artifact/'manifest.json')
        assert digest(artifact/'manifest.json') == proof['evidence']['manifest_sha256']
        assert proof['evidence']['remote_archive_verified']
        for name, sha in manifest.items(): assert digest(artifact/name) == sha
        for path in (directory/'verified.json', artifact/'manifest.json'):
            hashes[str(path.relative_to(ROOT))] = digest(path)
    decisions = 0
    for episode in range(4*players):
        evaluations = [d/'artifacts/job/evaluation' for d in directories]
        receipts = [p/f'decisions-{episode}.jsonl' for p in evaluations]
        rows = [[json.loads(line) for line in p.read_text().splitlines()] for p in receipts]
        assert len(rows[0]) == len(rows[1])
        for a, b in zip(*rows): compare_receipt(a, b, *identities, old_worker)
        games = [read(p/f'game-{episode}.json') for p in evaluations]
        for game, receipt, identity in zip(games, receipts, identities):
            assert game['decision_receipt_sha256'] == digest(receipt) and game['public_runtime_identity'] == identity
        semantic_games = [{k: v for k, v in g.items() if k not in ('seconds', 'decision_receipt_sha256', 'public_runtime_identity')} for g in games]
        assert no_elapsed(semantic_games[0]) == no_elapsed(semantic_games[1])
        decisions += len(rows[0])
    assert all(digest(ROOT/name) == sha for name, sha in hashes.items())
    return {'arm': arm, 'players': players, 'games': 4*players, 'exact_decisions': decisions,
            'original_job': proofs[0]['job_id'], 'corrected_job': proofs[1]['job_id'],
            'archives': [p['evidence'] for p in proofs], 'input_hashes': hashes}


def main(output):
    assert not output.exists(), 'Preserve previous regression report'
    cases = [compare_case(*case) for case in CASES]
    result = {'created_at': datetime.now(timezone.utc).isoformat(), 'complete': True,
        'games': sum(c['games'] for c in cases), 'exact_decisions': sum(c['exact_decisions'] for c in cases),
        'cases': cases, 'verifier_sha256': digest(__file__),
        'scope': 'All three original passing runtime pilots. Failed original dual-6p is excluded explicitly; its v2 run still requires full independent runtime admission. Reused engineering seeds, not strength or final qualification.',
        'allowed_differences': ['elapsedMs', 'game duration and receipt-file hash', 'pinned policy/runtime identities', 'pinned continuation worker hash'],
        'new_games': 0, 'inference': False, 'hf_jobs_submitted': 0, 'qualified': False, 'reserved_final_seeds_used': False}
    assert result['games'] == 40
    with output.open('x') as stream: json.dump(result, stream, indent=2); stream.write('\n')
    print(json.dumps({'complete': True, 'games': result['games'], 'exact_decisions': result['exact_decisions']}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__); parser.add_argument('--output', type=Path, default=OUTPUT)
    main(parser.parse_args().output)
