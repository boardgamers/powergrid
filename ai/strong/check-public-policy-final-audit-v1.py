"""Check new final-game auditing against immutable existing engineering receipts."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import tarfile

from public_policy_final_audit_v1 import artifact_identity, audit_shard, digest, protocol, read, schedule
from policy_iteration_evidence_archive import upload_evidence

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'ai/runs/public-policy-final-audit-preflight-v2'
ARCHIVE = ROOT / 'ai/runs/public-policy-final-audit-evidence-v2'
DESCRIPTOR = ROOT / 'ai/strong/public-policy-final-audit-evidence-v2.json'
SOURCES = ['public_policy_final_audit_v1.py', 'test_public_policy_final_audit_v1.py',
           'check-public-policy-final-audit-v1.py', 'public_policy_arena_v1.py',
           'public_policy_runtime_v1.py', 'population_policy_verification.py',
           'opponent_auction_verification_v1.py', 'surrogate_continuation_study_v1.py',
           'arena_statistics.py', 'opponent_auction_policy_v1.py', 'final-protocol-multiplayer.json']


def write_new(path, value):
    with path.open('x') as stream:
        stream.write(json.dumps(value, indent=2) + '\n')


def archived_files(descriptor):
    proof = read(descriptor)['archive']
    archive = ROOT / 'ai/runs' / Path(proof['archive_path']).name
    assert digest(archive) == proof['archive_sha256'] and proof['remote_archive_verified']
    with tarfile.open(archive) as bundle:
        data = bundle.extractfile('manifest.json').read()
    assert hashlib.sha256(data).hexdigest() == proof['manifest_sha256']
    return json.loads(data), proof


def verify():
    assert not OUT.exists(), 'Preserve the original audit outcome'
    sources = {str((ROOT/'ai/strong'/name).relative_to(ROOT)): digest(ROOT/'ai/strong'/name) for name in SOURCES}
    descriptors = [ROOT/'ai/strong/public-policy-arena-preflight-v1.json',
                   ROOT/'ai/strong/opponent-auction-engineering-evidence-v1.json']
    previous = [archived_files(path) for path in descriptors]
    directories = [(ROOT/f'ai/runs/public-policy-arena-preflight-v1/{n}p', 0) for n in range(2, 7)]
    directories.append((ROOT/'ai/runs/opponent-auction-engineering-games-v1', 1))
    OUT.mkdir()
    audits = []; inputs = {}; checked_artifacts = {}
    for directory, origin in directories:
        report = read(directory/'evaluation.json'); config = report['config']
        artifact = config['artifact']
        if artifact not in checked_artifacts:
            checked_artifacts[artifact] = artifact_identity(artifact, config['descriptor'])
        identity = checked_artifacts[artifact]
        expected = {key: config[key] for key in ['players', 'start', 'deals', 'seed', 'opponent', 'opponent_sha256']}
        result = audit_shard(directory, expected, identity, reserved=False)
        for name, sha in result['input_hashes'].items():
            relative = str((directory/name).relative_to(ROOT))
            assert previous[origin][0][relative] == sha
            inputs[relative] = sha
        label = 'auction-2p' if origin else f'filter-{config["players"]}p'
        write_new(OUT/(label+'.json'), result)
        audits.append({'label': label, 'games': len(result['terminals']), 'counts': result['counts'],
                       'identity': identity, 'audit_sha256': digest(OUT/(label+'.json'))})
    assert all(digest(ROOT/name) == sha for name, sha in sources.items())
    games = sum(a['games'] for a in audits); decisions = sum(a['counts']['decisions'] for a in audits)
    assert games == 88 and decisions == 11618
    assert sum(a['counts']['rollouts'] for a in audits) == 22048
    assert not any(a['counts']['rollout_caps'] for a in audits)
    tests = ROOT/'ai/runs/public-policy-final-audit-tests-v2.log'
    assert 'Ran 14 tests' in tests.read_text() and tests.read_text().rstrip().endswith('OK')
    sources[str(tests.relative_to(ROOT))] = digest(tests)
    regression = ROOT/'ai/runs/public-policy-final-audit-order-regression-v2.json'
    assert read(regression)['old_code_failed_order_invariance']
    sources[str(regression.relative_to(ROOT))] = digest(regression)
    predecessor = ROOT/'ai/strong/public-policy-final-audit-evidence-v1.json'
    sources[str(predecessor.relative_to(ROOT))] = digest(predecessor)
    sources.update({str(path.relative_to(ROOT)): digest(path) for path in descriptors})
    state = read(ROOT/'ai/runs/surrogate-continuation-study-coordinator-v1/state.json')
    assert all(digest(ROOT/name) == sha for name, sha in state['code_hashes'].items())
    command = Path('/proc')/str(state['pid'])/'cmdline'
    live = command.exists() and b'coordinate-surrogate-continuation-study-v1.py' in command.read_bytes()
    assert live or state['stage'] == 'complete', 'Inspect original study owner; never restart on a polling timeout'
    assert read(ROOT/'ai/strong/experiments.json')['final_seed_prefix_used'] is False
    planned = schedule(); protocol()
    result = {'complete': True, 'checked_at': datetime.now(timezone.utc).isoformat(),
              'engineering_games_reaudited': games, 'public_decisions_verified': decisions,
              'continuations_reaudited': 22048, 'caps': 0, 'contract_tests': 14,
              'bootstrap_deal_order': 'canonical episode order, independent of shard completion/receipt presentation',
              'supersedes': 'public-policy-final-audit-evidence-v1.json',
              'original_input_archives': [proof for _, proof in previous],
              'input_hashes': inputs, 'source_hashes': sources, 'audits': audits,
              'unchanged_final_schedule': {'shards': len(planned), 'games': sum(s['games'] for s in planned),
                                           'groups': len({s['group'] for s in planned})},
              'original_study_owner_live': live, 'study_pinned_code_unchanged': True,
              'study_checkpoint': {k: state[k] for k in ['pid', 'stage', 'jobs_submitted', 'jobs_verified', 'caps', 'failed_jobs', 'updated_at']},
              'gradient_updates': 0, 'new_games': 0, 'new_hf_jobs': 0,
              'candidate_selected': False, 'qualification_eligible': False, 'reserved_final_seeds_used': False,
              'remaining_integration': ['selected-policy final launcher and source/job admission',
                  'actual final wrapper engineering execution', 'complete-policy export/8840U/package evidence binding'],
              'scope': 'Read-only final-game audit verified on immutable prior engineering receipts and synthetic contract tests. No final games, qualification, selection or new strength result.'}
    write_new(OUT/'result.json', result)
    print(json.dumps({k: result[k] for k in ['complete', 'engineering_games_reaudited', 'public_decisions_verified',
                                           'continuations_reaudited', 'contract_tests']}), flush=True)


def archive():
    result = read(OUT/'result.json')
    assert result['complete'] and not result['reserved_final_seeds_used']
    assert all(digest(ROOT/name) == sha for name, sha in result['input_hashes'].items())
    assert all(digest(ROOT/name) == sha for name, sha in result['source_hashes'].items())
    assert not ARCHIVE.exists() and not ARCHIVE.with_suffix('.tgz').exists() and not DESCRIPTOR.exists()
    sources = {ROOT/name for name in result['source_hashes']}
    sources.update(p for p in OUT.iterdir() if p.is_file())
    ARCHIVE.mkdir(); hashes = {}
    for source in sorted(sources):
        name = str(source.relative_to(ROOT)); target = ARCHIVE/name
        target.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(source, target)
        hashes[name] = digest(source); assert digest(target) == hashes[name]
    note = ARCHIVE/'README.md'
    note.write_text('''# Standalone public-policy final-game audit: engineering evidence

The new read-only audit binds every raw public response to the full policy
identity, including the opponent ensemble and explicit override settings. It
recomputes game and continuation credits and applies the unchanged 320-shard,
20,160-game, 26-group final protocol. Fourteen synthetic contract tests include
missing shards, crossed identities, hidden inputs, unexecuted search, bad rule
subsets, order-invariant bootstrap results and the unchanged 90% default-bot floor.
This second evidence revision fixes deal ordering before bootstrap; the first
archive is retained. A strength pass alone explicitly
cannot qualify a candidate.

Existing immutable evidence was rechecked: 80 filtered-model and eight prototype
auction engineering games, 11,618 public decisions and 22,048 continuations, no
caps. The two original private archives retain all raw game receipts and runtime
packages; this archive includes their pins, full hashes, new audit outputs/code
and test log. No games, inference, training, jobs, final seeds or candidate
selection occurred. The selected-policy launcher, actual final wrapper execution
and complete-policy export/8840U/package evidence integration remain required.
''')
    hashes['README.md'] = digest(note)
    write_new(ARCHIVE/'manifest.json', hashes)
    print(json.dumps({'stage': 'uploading', 'files': len(hashes)+1}), flush=True)
    proof = upload_evidence(ARCHIVE)
    write_new(DESCRIPTOR, {**result, 'archive': proof, 'raw_result_sha256': digest(OUT/'result.json')})
    print(json.dumps(proof), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('operation', choices=['verify', 'archive'])
    globals()[parser.parse_args().operation]()
