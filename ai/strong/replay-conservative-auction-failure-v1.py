"""Recover the original failed runtime request from its verified saved prefix.

Replays only episode 5 of the failed original pilot, applies its 20 recorded
learner moves, and stops before making decision 21. The frozen arena repeats
its deterministic opponent search to recover that original prefix. No new
strength games, learned-policy decisions, training, HF submission, or changes
to the original evidence.
"""
import hashlib
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
CASE = 'conservative-auction-runtime-v1-conservative_dual-6p'
EVIDENCE = ROOT / 'ai/runs/conservative-auction-runtime-hf-v1' / CASE / 'artifacts/job/evaluation'
ARTIFACT = ROOT / 'ai/runs/conservative-auction-runtime-prepared-v1/source/artifact'
OUTPUT = ROOT / 'ai/runs/conservative-auction-failure-diagnosis-v1'


def read(path):
    return json.loads(path.read_text())


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def encode(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def normalized(request):
    """Exclude only historical wall-clock fields, as in the frozen arena audit."""
    request = json.loads(encode(request))
    state = request['state']
    for player in state['players']:
        player.pop('clockStartedAt', None)
        player.pop('totalTimeUsed', None)
        if isinstance(player.get('lastMove'), dict):
            player['lastMove'].pop('time', None)
            player['lastMove'].pop('serverTime', None)
    for event in state.get('log', []):
        if isinstance(event.get('move'), dict):
            event['move'].pop('time', None)
            event['move'].pop('serverTime', None)
    return request


def write(name, value):
    with (OUTPUT / name).open('x') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write('\n')


def main():
    assert not os.environ.get('NODE_OPTIONS'), 'Inherited Node options would change the frozen runtime'
    source = read(ROOT / 'ai/strong/conservative-auction-runtime-source-v1.json')
    assert digest(ROOT / 'ai/runs' / source['archive']) == source['sha256']
    candidate = read(EVIDENCE / 'candidate.json')['identity']
    descriptor = ARTIFACT / 'policies/conservative_dual.json'
    assert digest(descriptor) == candidate['policySha256']
    assert digest(ARTIFACT / 'manifest.json') == candidate['runtimeManifestSha256']
    manifest = read(ARTIFACT / 'manifest.json')
    for name, expected in manifest.items():
        path = (ARTIFACT / name).resolve()
        assert path.is_relative_to(ARTIFACT.resolve())
        assert digest(path) == expected, name
    failure = read(EVIDENCE / 'failure-5.json')
    receipt = EVIDENCE / 'decisions-5.jsonl'
    assert failure['episode'] == 5 and digest(receipt) == failure['receipt_sha256']
    rows = [json.loads(line) for line in receipt.read_text().splitlines()]
    assert len(rows) == failure['partial_counts']['decisions'] == 20
    config = read(EVIDENCE / 'intent.json')['config']
    assert config['players'] == 6 and config['opponent'] == 'search_geo'
    assert config['seed'] == 'conservative-auction-runtime-v1-6p'
    OUTPUT.mkdir(exist_ok=False)
    os.environ['PG_REFERENCE_RUNTIME'] = str(ARTIFACT)
    sys.path.insert(0, str(ARTIFACT / 'ai/strong'))
    from hybrid_search import Node
    bridge = Node(str(ARTIFACT / 'ai/strong/public-arena-bridge.cjs'))
    matches = []
    try:
        state = bridge.call({'op': 'reset', 'n': 1, 'offset': 5,
                             'arenaSeed': config['seed'], 'playerCount': 6,
                             'mode': 'search_geo', 'publicMoves': True,
                             'featureRevisions': {'learner': candidate['featureRevision']}})
        for i, saved in enumerate(rows, 1):
            assert not state['ended']
            observation = state['observations'][0]
            request = {**observation['request'], 'requestId': f'5:{i}', 'revision': i}
            assert normalized(request) == normalized(saved['publicRequest']), f'Prefix diverged at {i}'
            assert observation['moves'] == saved['arenaMoves'], f'Legal menu diverged at {i}'
            assert observation['playerOrder'] == saved['arenaPlayerOrder']
            assert observation['moves'][saved['index']] == saved['move']
            matches.append({'requestId': request['requestId'], 'normalizedRequestSha256':
                            hashlib.sha256(encode(normalized(request)).encode()).hexdigest()})
            state = bridge.call({'op': 'step', 'actions': [{'publicMove': saved['move']}]})
        assert not state['ended']
        observation = state['observations'][0]
        request = {**observation['request'], 'requestId': '5:21', 'revision': 21}
        write('request-5-21.json', request)
        write('observation-5-21.json', observation)
        report = {'original_job': '6addea04046eb82b1ece4fb1', 'original_episode': 5,
                  'source_archive_sha256': source['sha256'],
                  'policy_sha256': candidate['policySha256'],
                  'runtime_manifest_sha256': candidate['runtimeManifestSha256'],
                  'runtime_files_verified': len(manifest),
                  'original_receipt_sha256': digest(receipt), 'prefix_matches': matches,
                  'reconstructed_request_sha256': digest(OUTPUT / 'request-5-21.json'),
                  'round': request['state']['round'], 'phase': request['state']['phase'],
                  'legal_moves': observation['moves'], 'policy_decision_attempted': False,
                  'request_preserved_in_original_archive': False,
                  'reconstruction_claim': 'All 20 saved public requests and ordered legal menus match, excluding only wall-clock bookkeeping; next request is reconstructed, not an original saved receipt.',
                  'new_strength_games': 0, 'new_hf_jobs': 0, 'gradient_updates': 0,
                  'reserved_final_seeds_used': False, 'qualification_eligible': False}
        write('prefix-replay.json', report)
        print(encode({key: report[key] for key in ['original_job', 'runtime_files_verified',
                    'round', 'phase', 'reconstructed_request_sha256', 'policy_decision_attempted']}))
        print('Verified all 20 recorded decisions; stopped at original failed request 5:21.', flush=True)
    finally:
        bridge.close()


if __name__ == '__main__':
    main()
