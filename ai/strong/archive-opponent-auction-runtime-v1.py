"""Archive verified prototype execution; full-game/strength work stays separate."""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import shutil

from policy_iteration_evidence_archive import upload_evidence
from opponent_auction_verification_v1 import verify_decision

ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT / 'ai/runs/opponent-auction-runtime-preflight-v1'
OUT = ROOT / 'ai/runs/opponent-auction-runtime-evidence-v1'


def read(path):
    return json.loads(path.read_text())


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--archive', action='store_true', required=True)
    parser.parse_args()
    package = RUN / 'package'
    result, prepared = read(RUN / 'result.json'), read(RUN / 'prepared.json')
    assert result['complete'] and result['caps'] == 0 and result['exact_archived_continuations'] == 512
    assert digest(package / 'manifest.json') == result['manifest_sha256'] == prepared['manifest_sha256']
    assert digest(package / 'policy.json') == result['policy_sha256']
    manifest = read(package / 'manifest.json')
    assert all(digest(package / name) == sha for name, sha in manifest.items())
    assert all(digest(ROOT / name) == sha for name, sha in prepared['overlays'].items())
    assert digest(ROOT / 'ai/strong/check-opponent-auction-runtime-v1.py') == prepared['checker_sha256']
    assert all(digest(RUN / name) == sha for name, sha in prepared['gold_hashes'].items())
    roots = read(package / 'ai/strong/fixtures/surrogate-continuation-runtime-roots-v1.json')['roots']
    spec = read(package / 'policy.json')
    identity = {'policySha256': result['policy_sha256'], 'runtimeManifestSha256': result['manifest_sha256'],
                'modelSha256': spec['model']['sha256'], 'featureRevision': spec['feature_revision'],
                'backend': spec['backend'], 'settings': spec['settings'], 'opponentPolicySha256': spec['opponent']['sha256']}
    fixtures = rollouts = exact = overrides = 0
    with (RUN / 'decisions.jsonl').open() as stream:
        for line in stream:
            saved = json.loads(line)
            root = roots[saved['name']]
            response = saved['response']
            assert all(response[k] == v for k, v in identity.items())
            row = {**response['decision'], 'arenaMoves': root['moves']}
            assert response['move'] == root['moves'][row['index']]
            config = {'players': root['identity']['players'], 'arm': 'opponent-auction-v1',
                      'samples': 8, 'model_sha256': spec['model']['sha256'], 'identity': identity}
            checked = verify_decision(row, config, root['identity']['seat'])
            assert checked == saved['verification']
            fixtures += 1; rollouts += checked['rollouts']; overrides += checked['search_changes']
            if row['search']:
                for component in row['search']['components']:
                    gold = read(RUN / 'reference' / saved['name'] / (component['mode'] + '.json'))
                    actual = {(r['sample'], r['actionIndex']): r for r in component['rows']}
                    for reference in gold['rows']:
                        current = actual[reference['sample'], reference['actionIndex']]
                        assert {k: v for k, v in current.items() if k != 'env'} == {
                            k: v for k, v in reference.items() if k != 'env'}
                        exact += 1
    assert fixtures == 24 and rollouts == result['continuations'] == 1328 and exact == 512 and overrides == result['overrides'] == 3
    study = read(ROOT / 'ai/runs/surrogate-continuation-study-coordinator-v1/state.json')
    study_command = Path('/proc') / str(study['pid']) / 'cmdline'
    assert study_command.exists() and b'coordinate-surrogate-continuation-study-v1.py' in study_command.read_bytes()
    assert all(digest(ROOT / name) == sha for name, sha in study['code_hashes'].items())
    engineering = read(ROOT / 'ai/runs/opponent-auction-engineering-games-v1-launch.json')
    engineering_command = Path('/proc') / str(engineering['pid']) / 'cmdline'
    live = engineering_command.exists() and str(package).encode() in engineering_command.read_bytes()
    report = ROOT / 'ai/runs/opponent-auction-engineering-games-v1/evaluation.json'
    assert live or report.exists(), 'Inspect original engineering process; do not restart it'
    checkpoint = {'checked_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                  'previous_goal_turn': 'progress: full resource-plan consistency diagnosis archived and pushed',
                  'current_goal_turn': 'progress: prototype standalone auction implementation and verified engineering fixtures',
                  'original_study_owner_live': True, 'study_pinned_code_unchanged': True, 'study_state': study,
                  'engineering_launch': engineering, 'engineering_process_live': live,
                  'engineering_report_present': report.exists(),
                  'engineering_games_verified_in_this_archive': False}
    checkpoint_path = ROOT / 'ai/runs/opponent-auction-runtime-completion-checkpoint-v1.json'
    assert not checkpoint_path.exists()
    checkpoint_path.write_text(json.dumps(checkpoint, indent=2) + '\n')
    sources = set(p for p in RUN.rglob('*') if p.is_file())
    for name in ['opponent_auction_policy_v1.py', 'opponent_auction_verification_v1.py',
                 'check-opponent-auction-runtime-v1.py', 'test_opponent_auction_policy_v1.py',
                 'public_policy_runtime_v1.py', 'public_policy_arena_v1.py',
                 'test_public_policy_runtime_v1.py', 'test_public_policy_arena_v1.py',
                 'archive-opponent-auction-runtime-v1.py', 'final-protocol-multiplayer.json']:
        sources.add(ROOT / 'ai/strong' / name)
    for name in ['opponent-auction-runtime-preflight-v1.log', 'opponent-auction-contract-tests-v1.log',
                 'opponent-auction-public-contract-tests-v1.log', 'opponent-auction-engineering-games-v1-launch.json',
                 'opponent-auction-runtime-completion-checkpoint-v1.json']:
        sources.add(ROOT / 'ai/runs' / name)
    assert not OUT.exists() and not OUT.with_suffix('.tgz').exists()
    OUT.mkdir()
    hashes = {}
    for source in sorted(sources):
        name = str(source.relative_to(ROOT)); target = OUT / name
        target.parent.mkdir(parents=True, exist_ok=True)
        hashes[name] = digest(source); shutil.copy2(source, target)
        assert digest(target) == hashes[name]
    README = OUT / 'README.md'
    README.write_text('''# Opponent-aware auction prototype: execution evidence only

The standalone public JSON worker now supports an auction-only backend combining
the unchanged population and frozen learned-opponent continuation paths. Full
receipts independently reconstruct exact terminal tie credits and the empirical
selection rule. Engineering settings use eight worlds per population, equal
population weights, a strict pooled advantage over 1/8 and no negative advantage
in either population. These settings are not a selected candidate, calibrated
confidence bound, guarantee of improvement or retrospective variant router.

The 24 existing two/six-player runtime fixtures cover all rules and plant/bid/
building phases: 16 searched auction roots, eight unchanged building choices,
1,328 continuations, 512 exact archived continuation matches, three experimental
overrides and zero unexpected caps. A repeated root matches the direct class.
An intentional one-step cap keeps the model; a corrupt opponent pin is rejected.
Ten old model/filter checks cover all five player counts. Seven chooser tests and
eleven public transport/arena tests passed. No new strength games or gradients.

The complete artifact, original reference rows, raw requests/responses, code and
logs are included. The original 480-root fidelity study and its code are unchanged.
Eight two-player/all-rule engineering games were started separately; their original
PID and command are preserved in the checkpoint. They are NOT verified by this
archive and must be collected without replacing the original process on timeout.
Their outcomes are not strength evidence. The selected-policy final adapter and
actual complete-policy AMD 8840U benchmark remain required after policy selection.
''')
    hashes['README.md'] = digest(README)
    (OUT / 'manifest.json').write_text(json.dumps(hashes, indent=2) + '\n')
    print(json.dumps({'stage': 'uploading', 'files': len(hashes) + 1}), flush=True)
    archive = upload_evidence(OUT)
    descriptor = {**result, 'archive': archive, 'raw_result_sha256': digest(RUN / 'result.json'),
                  'independently_reaudited_saved_receipts': True, 'chooser_contract_tests': 7,
                  'transport_arena_contract_tests': 11, 'engineering_games_launch': engineering,
                  'engineering_games_verified': False, 'candidate_selected': False}
    path = ROOT / 'ai/strong/opponent-auction-runtime-preflight-v1.json'
    assert not path.exists()
    path.write_text(json.dumps(descriptor, indent=2) + '\n')
    print(json.dumps(archive), flush=True)


if __name__ == '__main__':
    main()
