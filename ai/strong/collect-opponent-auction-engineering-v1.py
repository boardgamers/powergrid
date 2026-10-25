"""Audit the original eight standalone engineering games, then archive evidence.

No new games, inference, training or job submission. This does not select a
candidate or convert a small engineering exercise into strength evidence.
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil

from opponent_auction_verification_v1 import verify_evaluation
from public_policy_arena_v1 import validate_response, wire_json
from policy_iteration_evidence_archive import upload_evidence

ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT / 'ai/runs/opponent-auction-engineering-games-v1'
PACKAGE = ROOT / 'ai/runs/opponent-auction-runtime-preflight-v1/package'
RESULT = ROOT / 'ai/runs/opponent-auction-engineering-verification-v1.json'
OUT = ROOT / 'ai/runs/opponent-auction-engineering-evidence-v1'
DESCRIPTOR = ROOT / 'ai/strong/opponent-auction-engineering-evidence-v1.json'
PROTOCOL_SHA = '7f0336c8784faf8f18e046b95b88e0ab1be7c2de1c0ec4d3eec96f0a415286ce'


def read(path):
    return json.loads(path.read_text())


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def write_new(path, value):
    with path.open('x') as stream:
        stream.write(json.dumps(value, indent=2) + '\n')


def evidence_sources():
    sources = {p for p in RUN.rglob('*') if p.is_file()}
    for name in ['opponent-auction-engineering-games-v1-launch.json',
                 'opponent-auction-engineering-games-v1.log']:
        sources.add(ROOT / 'ai/runs' / name)
    for name in ['collect-opponent-auction-engineering-v1.py',
                 'opponent_auction_verification_v1.py', 'population_policy_verification.py',
                 'surrogate_continuation_study_v1.py', 'public_policy_arena_v1.py',
                 'public_policy_runtime_v1.py', 'policy_iteration_evidence_archive.py',
                 'opponent-auction-runtime-preflight-v1.json', 'final-protocol-multiplayer.json']:
        sources.add(ROOT / 'ai/strong' / name)
    return sources


def verify():
    assert not RESULT.exists(), 'Preserve the original audit; do not rerun unchanged work'
    launch = read(ROOT / 'ai/runs/opponent-auction-engineering-games-v1-launch.json')
    preflight = read(ROOT / 'ai/strong/opponent-auction-runtime-preflight-v1.json')
    report = read(RUN / 'evaluation.json')
    assert report['passed'] and report['validation_error'] is None
    assert not list(RUN.glob('failure-*.json'))
    assert digest(PACKAGE / 'manifest.json') == launch['manifest_sha256'] == preflight['manifest_sha256']
    assert digest(PACKAGE / 'policy.json') == launch['policy_sha256'] == preflight['policy_sha256']
    manifest = read(PACKAGE / 'manifest.json')
    assert all(digest(PACKAGE / name) == sha for name, sha in manifest.items())
    spec = read(PACKAGE / 'policy.json')
    identity = {'policySha256': launch['policy_sha256'],
                'runtimeManifestSha256': launch['manifest_sha256'],
                'modelSha256': spec['model']['sha256'], 'featureRevision': spec['feature_revision'],
                'backend': spec['backend'], 'settings': spec['settings'],
                'opponentPolicySha256': spec['opponent']['sha256']}
    config = report['config']
    expected = {'players': 2, 'opponent': 'economic', 'opponent_model': None,
                'opponent_sha256': None, 'arm': 'opponent-auction-v1',
                'seed': 'opponent-auction-engineering-v1-2p', 'start': 0, 'deals': 1,
                'workers': 4, 'samples': 8, 'search_workers': 4,
                'artifact': str(PACKAGE), 'runtime': str(PACKAGE), 'descriptor': 'policy.json',
                'output': str(RUN), 'model': str(PACKAGE / spec['model']['path']),
                'model_sha256': spec['model']['sha256'], 'identity': identity,
                'reference_artifact': None}
    assessment = verify_evaluation(RUN, expected)
    decisions = 0
    phase_counts = Counter()
    for record in report['results']:
        assert record['public_runtime_identity'] == identity
        assert record['direct_reference_trajectory_checked'] is False
        with (RUN / f'decisions-{record["episode"]}.jsonl').open() as stream:
            for line in stream:
                row = json.loads(line)
                response, request = row['publicResponse'], row['publicRequest']
                choice = validate_response(response, request, row['arenaMoves'], row['arenaPlayerOrder'], identity)
                assert choice == row['index']
                # Both copies are retained verbatim, including menu ordering and
                # timing. The independent continuation/terminal audit ran above.
                assert all(wire_json(row[k]) == wire_json(v) for k, v in response['decision'].items())
                assert row['directReference'] is None
                assert request['player'] == record['terminal']['seat']
                assert request['requestId'] == f'{record["episode"]}:{row["decision"]}'
                assert request['revision'] == row['decision']
                state = request['state']
                assert state['seed'] == 'secret' and state['powerPlantsDeck'] == []
                assert not state.get('hiddenLog') and 'powerPlantDeckAfterStep3' not in state
                if state['options']['fastBid']:
                    assert all(p['bid'] == 0 for p in state['players'])
                phase_counts[row['phase']] += 1
                decisions += 1
    assert assessment['games'] == launch['expected_engineering_games'] == 8
    assert assessment['counts']['decisions'] == decisions
    assert assessment['counts']['search_changes'] > 0
    assert digest(ROOT / 'ai/strong/final-protocol-multiplayer.json') == PROTOCOL_SHA
    ledger = read(ROOT / 'ai/strong/experiments.json')
    assert ledger['final_seed_prefix_used'] is False
    study = read(ROOT / 'ai/runs/surrogate-continuation-study-coordinator-v1/state.json')
    assert all(digest(ROOT / name) == sha for name, sha in study['code_hashes'].items())
    sources = evidence_sources()
    result = {'complete': True, 'checked_at': datetime.now(timezone.utc).isoformat(),
              'identity': identity, 'assessment': assessment, 'phase_counts': dict(phase_counts),
              'original_launch': launch, 'runtime_preflight_archive': preflight['archive'],
              'runtime_files_verified': len(manifest), 'all_public_responses_verified': True,
              'full_game_direct_policy_parity_claimed': False,
              'source_hashes': {str(p.relative_to(ROOT)): digest(p) for p in sorted(sources)},
              'study_checkpoint': {k: study[k] for k in ['pid', 'stage', 'jobs_submitted',
                                                       'jobs_verified', 'caps', 'failed_jobs', 'updated_at']},
              'study_pinned_code_unchanged': True, 'final_protocol_sha256': PROTOCOL_SHA,
              'new_hf_jobs': 0, 'new_strength_games': 0, 'gradients': False,
              'candidate_selected': False, 'qualification_eligible': False,
              'reserved_final_seeds_used': False,
              'scope': 'Eight original two-player economic-opponent engineering games, all seats/rules, one deal. Full raw receipt and standalone transport checks; not strength evidence or target-hardware timing.'}
    write_new(RESULT, result)
    print(json.dumps({'complete': True, 'games': 8, 'decisions': decisions,
                      'counts': assessment['counts'], 'phase_counts': dict(phase_counts)}), flush=True)


def archive():
    result = read(RESULT)
    assert result['complete'] and result['all_public_responses_verified']
    assert not DESCRIPTOR.exists() and not OUT.exists() and not OUT.with_suffix('.tgz').exists()
    hashes = result['source_hashes']
    assert set(hashes) == {str(p.relative_to(ROOT)) for p in evidence_sources()}
    assert all(digest(ROOT / name) == sha for name, sha in hashes.items())
    hashes = {**hashes, str(RESULT.relative_to(ROOT)): digest(RESULT)}
    OUT.mkdir()
    for name, sha in hashes.items():
        target = OUT / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / name, target)
        assert digest(target) == sha
    note = OUT / 'README.md'
    note.write_text('''# Standalone opponent-aware auction engineering games

All eight ORIGINAL two-player games completed: one deal, all seats and rule
combinations, economic opponents. The saved-receipt audit checks full terminal
tie credits, every sampled continuation, the population-consensus override rule,
all returned public moves and their request/revision/player identity. Raw results,
requests, responses, launch guard, code and logs are retained. The runtime package
is pinned by the earlier private archive recorded in the verification result.

These are engineering games, NOT playing-strength evidence. The prototype's
eight worlds, equal population weights and strict 1/8 margin are not selected
settings. No whole-game direct-policy parity or actual 8840U latency is claimed.
The ongoing 480-root fidelity study is separate. No new jobs, training, production
change or reserved final seeds were used to collect this evidence. Freeze a recipe
only after reviewing full findings; use fresh full games and the unchanged final
strength gate, with an adapter that binds the complete standalone policy identity.
''')
    hashes['README.md'] = digest(note)
    write_new(OUT / 'manifest.json', hashes)
    print(json.dumps({'stage': 'uploading', 'files': len(hashes) + 1}), flush=True)
    archived = upload_evidence(OUT)
    write_new(DESCRIPTOR, {**result, 'verification_sha256': digest(RESULT), 'archive': archived})
    print(json.dumps(archived), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('operation', choices=['verify', 'archive'])
    globals()[parser.parse_args().operation]()
