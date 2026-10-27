"""Derive, replay and independently audit a separate forced-prior runtime.

No HF submission, training or fresh strength games. Preserve the failed pilot.
Run prepare, replay and audit as separate processes to keep imports pinned.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import sys
import traceback

ROOT = Path(__file__).resolve().parents[2]
ORIGINAL = ROOT/'ai/runs/conservative-auction-runtime-prepared-v1/source/artifact'
DIAGNOSIS = ROOT/'ai/runs/conservative-auction-failure-diagnosis-v1'
OUT = ROOT/'ai/runs/conservative-auction-forced-prior-v1'
ARTIFACT = OUT/'artifact'
PATCHES = ('ai/strong/opponent_surrogate_policy_v1.py', 'ai/strong/surrogate-opponent-continuations-v1.cjs')
ORIGINAL_MANIFEST = 'dcb23342088ae91379374827b45c0845d1b9494b31682fca55e3ac047d1e2f55'
DESCRIPTOR = 'policies/conservative_dual.json'


def read(path): return json.loads(Path(path).read_text())
def digest(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def write(path, value):
    with Path(path).open('x') as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False); stream.write('\n')


def check_manifest(root, expected):
    assert digest(root/'manifest.json') == expected
    manifest = read(root/'manifest.json')
    assert len(manifest) == 1502
    for name, sha in manifest.items():
        path = (root/name).resolve()
        assert path.is_relative_to(root.resolve()) and not (root/name).is_symlink()
        assert digest(path) == sha, name
    return manifest


def prepare():
    assert not OUT.exists(), 'Inspect any previous preparation; never overwrite a runtime identity'
    manifest = check_manifest(ORIGINAL, ORIGINAL_MANIFEST)
    shutil.copytree(ORIGINAL, ARTIFACT)
    changes = {}
    for name in PATCHES:
        shutil.copyfile(ROOT/name, ARTIFACT/name)
        changes[name] = {'old_sha256': manifest[name], 'new_sha256': digest(ARTIFACT/name)}
        assert changes[name]['old_sha256'] != changes[name]['new_sha256']
    updated = {name: digest(ARTIFACT/name) for name in manifest}
    assert {name for name in manifest if manifest[name] != updated[name]} == set(PATCHES)
    # The original tree is immutable. Only this fresh copy gets new identity pins.
    (ARTIFACT/'manifest.json').unlink(); write(ARTIFACT/'manifest.json', updated)
    manifest_sha = digest(ARTIFACT/'manifest.json')
    descriptors = {}
    for path in [ARTIFACT/'policy.json', *sorted((ARTIFACT/'policies').glob('*.json'))]:
        spec = read(path); original = read(ORIGINAL/path.relative_to(ARTIFACT))
        assert spec == original and spec['runtime_manifest']['sha256'] == ORIGINAL_MANIFEST
        spec['runtime_manifest']['sha256'] = manifest_sha
        path.unlink(); write(path, spec)
        descriptors[str(path.relative_to(ARTIFACT))] = digest(path)
    spec = read(ARTIFACT/DESCRIPTOR)
    report = {'created_at': datetime.now(timezone.utc).isoformat(),
              'original_job': '6addea04046eb82b1ece4fb1', 'original_pilot_status': 'ERROR; preserved',
              'original_manifest_sha256': ORIGINAL_MANIFEST, 'manifest_sha256': manifest_sha,
              'original_descriptor_sha256': digest(ORIGINAL/DESCRIPTOR), 'descriptor_sha256': digest(ARTIFACT/DESCRIPTOR),
              'runtime_files': len(updated), 'changed_runtime_files': changes, 'descriptors': descriptors,
              'unchanged_model': spec['model'], 'unchanged_opponent': spec['opponent'], 'unchanged_settings': spec['settings'],
              'new_hf_jobs': 0, 'new_strength_games': 0, 'gradient_updates': 0,
              'grid_admitted': False, 'qualification_eligible': False, 'reserved_final_seeds_used': False}
    write(OUT/'derivation.json', report)
    print(json.dumps(report), flush=True)


def checked():
    report = read(OUT/'derivation.json')
    check_manifest(ORIGINAL, ORIGINAL_MANIFEST)
    current = check_manifest(ARTIFACT, report['manifest_sha256'])
    original = read(ORIGINAL/'manifest.json')
    assert {name for name in current if current[name] != original[name]} == set(PATCHES)
    assert digest(ARTIFACT/DESCRIPTOR) == report['descriptor_sha256']
    return report


def replay():
    report = checked()
    assert not any((OUT/name).exists() for name in ('replay-intent.json', 'response-5-21.json', 'replay-error.json'))
    prefix = read(DIAGNOSIS/'prefix-replay.json')
    path = DIAGNOSIS/'request-5-21.json'
    assert digest(path) == prefix['reconstructed_request_sha256']
    request = read(path); assert request['requestId'] == '5:21'
    write(OUT/'replay-intent.json', {'request_sha256': digest(path), 'descriptor_sha256': report['descriptor_sha256'],
                                   'created_at': datetime.now(timezone.utc).isoformat()})
    sys.path.insert(0, str(ARTIFACT/'ai/strong'))
    from public_policy_runtime_v1 import PublicPolicyService, load_artifact
    service = PublicPolicyService(lambda: load_artifact(ARTIFACT, DESCRIPTOR))
    try:
        response = service.decide(request, diagnostics=True)
        write(OUT/'response-5-21.json', response)
        print(json.dumps({'requestId': response['requestId'], 'move': response['move'],
                          'elapsedMs': response['elapsedMs'], 'response_sha256': digest(OUT/'response-5-21.json')}), flush=True)
    except Exception as error:
        write(OUT/'replay-error.json', {'error_type': type(error).__name__, 'message': str(error), 'stack': traceback.format_exc()})
        raise
    finally: service.close()


def audit():
    derivation = checked()
    assert not (OUT/'audit.json').exists()
    # The independent verifier is byte-identical to the ORIGINAL artifact.
    # Load its copied file so its worker-integrity checks use the newly pinned
    # worker, while preserving all terminal-credit/selection audit logic.
    assert digest(ARTIFACT/'ai/strong/opponent_auction_verification_v1.py') == digest(ORIGINAL/'ai/strong/opponent_auction_verification_v1.py')
    assert digest(ARTIFACT/'ai/strong/surrogate_continuation_study_v1.py') == digest(ORIGINAL/'ai/strong/surrogate_continuation_study_v1.py')
    sys.path.insert(0, str(ARTIFACT/'ai/strong'))
    from opponent_auction_verification_v1 import verify_decision
    response = read(OUT/'response-5-21.json'); request = read(DIAGNOSIS/'request-5-21.json')
    observation = read(DIAGNOSIS/'observation-5-21.json')
    assert response['requestId'] == request['requestId'] == '5:21'
    assert response['policySha256'] == derivation['descriptor_sha256']
    assert response['runtimeManifestSha256'] == derivation['manifest_sha256']
    assert response['settings'] == derivation['unchanged_settings']
    assert response['modelSha256'] == derivation['unchanged_model']['sha256']
    assert response['opponentPolicySha256'] == derivation['unchanged_opponent']['sha256']
    assert response['playerOrder'] == observation['playerOrder']
    row = response['decision']
    assert response['move'] == row['move'] == observation['moves'][row['index']]
    row['arenaMoves'] = observation['moves']
    config = {'players': 6, 'arm': 'opponent-auction-v1', 'samples': 8,
              'model_sha256': response['modelSha256'], 'sealed': True, 'identity': response}
    counts = verify_decision(row, config, request['player'])
    assert counts['rollouts'] > 0 and counts['rollout_caps'] == 0
    report = {'complete': True, 'scope': 'One recovered runtime request, not a replacement pilot or strength result',
              'requestId': '5:21', 'original_job': derivation['original_job'], 'original_pilot_status': 'ERROR; preserved',
              'request_sha256': digest(DIAGNOSIS/'request-5-21.json'),
              'response_sha256': digest(OUT/'response-5-21.json'), 'derivation_sha256': digest(OUT/'derivation.json'),
              'frozen_original_verifier_sha256': digest(ORIGINAL/'ai/strong/opponent_auction_verification_v1.py'),
              'counts': counts, 'selected_move': response['move'], 'selection': row['search']['selection'],
              'elapsedMs': response['elapsedMs'], 'runtime_manifest_sha256': derivation['manifest_sha256'],
              'new_hf_jobs': 0, 'new_strength_games': 0, 'gradient_updates': 0,
              'grid_admitted': False, 'qualification_eligible': False, 'reserved_final_seeds_used': False}
    write(OUT/'audit.json', report); print(json.dumps(report), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__); parser.add_argument('operation', choices=['prepare', 'replay', 'audit'])
    globals()[parser.parse_args().operation]()
