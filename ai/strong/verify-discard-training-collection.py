"""Verify complete paired games, public roots and whole-deal training splits."""
import argparse
from collections import Counter, defaultdict
import gzip
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'ai'))
from infer import Model, Node
from arena_statistics import validate_pairs
from huggingface_hub import hf_hub_download
def read(path):
    return json.loads(Path(path).read_text())
def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def write(path, value):
    Path(path).write_text(json.dumps(value, indent=2) + '\n')


def main():
    p = argparse.ArgumentParser(__doc__)
    p.add_argument('players', type=int, choices=range(2, 7))
    p.add_argument('revision')
    p.add_argument('output', type=Path)
    a = p.parse_args()
    assert re.fullmatch('[a-f0-9]{40}', a.revision)
    protocol_path = ROOT / 'ai/strong/discard-training-collection-protocol-v1.json'
    protocol = read(protocol_path)
    source = read(ROOT / 'ai/strong/discard-training-collection-source-v1.json')
    out = a.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    prefix = f'runs/discard-training-collection-v1-{a.players}p'
    def fetch(name):
        assert Path(name).name == name
        raw = Path(hf_hub_download(protocol['repo'], prefix + '/' + name, revision=a.revision)).read_bytes()
        (out / name).write_bytes(raw)
    fetch('collection-check.json')
    status = read(out / 'collection-check.json')
    games = protocol['games_by_players'][str(a.players)]
    expected = {'status': 'complete', 'players': a.players, 'smoke': False,
        'protocol_sha256': digest(protocol_path), 'model_sha256': protocol['model']['sha256'],
        'source_revision': source['revision'], 'source_sha256': source['sha256'],
        'games': games, 'engine_game_runs': games * 2, 'truncations': 0,
        'all_twin_controls_match': True, 'trained': False, 'labels_generated': False, 'qualification_eligible': False}
    for key, value in expected.items():
        assert status[key] == value, key
    modes = protocol['modes_by_players'][str(a.players)]
    assert set(status['artifact_sha256']) == {'roots.jsonl.gz', *(m + '.json' for m in modes)}
    for name, sha in status['artifact_sha256'].items():
        fetch(name)
        assert digest(out / name) == sha
    per_game = {}
    for mode in modes:
        report = read(out / (mode + '.json'))
        assert {k: v for k, v in report.items() if k != 'results'} == status['counts'][mode]
        rows = report['results']
        expected_count = protocol['deals_per_mode_count'] * 4 * a.players
        assert len(rows) == report['games'] == expected_count
        assert report['engine_game_runs'] == 2 * expected_count
        assert {r['episode'] for r in rows} == set(range(expected_count))
        validate_pairs(rows, a.players)
        seed = protocol['seed_template'].format(players=a.players, mode=mode)
        assert {r['gameSeed'] for r in rows} == {seed + '-' + str(i) for i in range(protocol['deals_per_mode_count'])}
        assert all(not r['truncated'] and not r['searchStats'] for r in rows)
        per_game[mode] = {r['episode']: r for r in rows}
    pin = protocol['model']
    model = Model(hf_hub_download(protocol['repo'], pin['path'], revision=pin['revision']), threads=4)
    assert model.sha256 == pin['sha256']
    worker = Node('strong/worker.cjs')
    counts, ordinals, seen, split_groups, coverage = Counter(), Counter(), set(), {}, Counter()
    index = 0
    try:
        with gzip.open(out / 'roots.jsonl.gz', 'rt') as file:
            for line in file:
                r = json.loads(line)
                mode, episode = r['mode'], r['episode']
                game = per_game[mode][episode]
                ordinal = ordinals[mode, episode]
                assert r['players'] == a.players and r['rootIndex'] == index
                assert r['ordinal'] == ordinal and r['rootId'] == f'{a.players}:{mode}:{episode}:{ordinal}'
                ordinals[mode, episode] += 1
                deal = episode // (4 * a.players)
                split = 'validation' if deal in protocol['validation_deal_indices'] else 'train'
                assert r['deal'] == deal and r['split'] == split
                assert r['gameSeed'] == game['gameSeed']
                assert all(r[k] == game[k] for k in ['variant', 'sealed'])
                assert split_groups.setdefault((mode, r['gameSeed']), split) == split
                state, seat = r['request']['state'], r['request']['player']
                assert seat == game['seat'] and state['round'] == r['round']
                assert state['options']['showMoney'] and len(state['players']) == a.players
                assert max(len(p['cities']) for p in state['players']) >= state['citiesToEndGame'] - 3
                assert not state['powerPlantsDeck'] and not state['hiddenLog'] and state['seed'] == 'secret'
                assert 'powerPlantDeckAfterStep3' not in state and not state.get('automation', {}).get('plans')
                if state['options']['fastBid']:
                    assert state['currentBid'] == 0
                sha = hashlib.sha256(json.dumps(r['request'], sort_keys=True).encode()).hexdigest()
                assert sha == r['public_root_sha256'] and (mode, episode, sha) not in seen
                seen.add((mode, episode, sha))
                obs = worker.call({**r['request'], 'featureRevision': pin['feature_revision']})
                assert obs['moves'] == r['legal'] and len(r['legal']) > 1
                assert all(m['name'] == 'DiscardPowerPlant' for m in r['legal'])
                assert model.predict(obs['state'], obs['actions'])[0] == r['model_proposal']
                assert r['model_move'] == r['legal'][r['model_proposal']]
                counts[mode, split] += 1
                coverage[mode, split, r['variant'], r['sealed'], seat] += 1
                index += 1
    finally:
        worker.close()
    assert index == status['roots'] == sum(counts.values())
    for mode in modes:
        assert status['counts'][mode]['root_splits'] == {split: counts[mode, split] for split in ['train', 'validation']}
        assert status['counts'][mode]['games_with_roots'] == sum(m == mode for m, _ in ordinals)
        assert status['counts'][mode]['games_with_multiple_roots'] == sum(m == mode and n > 1 for (m, _), n in ordinals.items())
    report = {'revision': a.revision, 'prefix': prefix, 'players': a.players, 'games': games,
        'engine_game_runs': games * 2, 'roots': index, 'truncations': 0,
        'public_model_proposals_reproduced': index, 'no_deal_split_leakage': True,
        'root_splits': {split: sum(n for (_, s), n in counts.items() if s == split) for split in ['train', 'validation']},
        'counts': {m: {s: counts[m, s] for s in ['train', 'validation']} for m in modes},
        'coverage': {'/'.join(map(str, key)): value for key, value in sorted(coverage.items())},
        'sha256': {p.name: digest(p) for p in out.iterdir() if p.is_file()},
        'trained': False, 'labels_generated': False, 'qualification_eligible': False}
    write(out / 'verified.json', report)
    print({k: report[k] for k in ['players', 'games', 'roots', 'root_splits', 'truncations']})


if __name__ == '__main__':
    main()
