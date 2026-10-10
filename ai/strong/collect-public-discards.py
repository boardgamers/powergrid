"""Collect fresh public roots with a parallel uninstrumented exact-replay control."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'ai'))
from infer import Model
from pool import EnginePool
from feature_contract import model_revision
from arena_statistics import validate_pairs


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path, value):
    Path(path).write_text(json.dumps(value, indent=2) + '\n')


def run(args):
    protocol = json.loads((ROOT / 'ai/strong/public-discard-collection-protocol-v1.json').read_text())
    model = Model(args.model)
    assert model.sha256 == protocol['model']['sha256']
    assert model_revision(model) == protocol['model']['feature_revision']
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    roots, reports = [], {}
    status = {'status': 'running', 'protocol_sha256': digest(ROOT / 'ai/strong/public-discard-collection-protocol-v1.json'),
        'source_revision': os.environ.get('SOURCE_REVISION'), 'source_sha256': os.environ.get('SOURCE_SHA256'),
        'model_sha256': model.sha256, 'trained': False, 'qualification_eligible': False}
    try:
        assert not os.environ.get('NODE_OPTIONS'), 'Do not inherit unknown instrumentation'
        for n in ([args.smoke_players] if args.smoke_players else protocol['players']):
            deals = 1 if args.smoke_players else protocol['deals_per_player_count']
            games = deals * n * 4
            seed = (protocol['smoke_seed_template'] if args.smoke_players else protocol['seed_template']).format(players=n)
            workers = min(24, games)
            control = EnginePool(workers, script='ai/strong/bridge.cjs')
            try:
                os.environ['NODE_OPTIONS'] = '--require ' + str(ROOT / 'ai/strong/capture-public-discard.cjs')
                captured = EnginePool(workers, script='ai/strong/bridge.cjs')
            finally:
                os.environ.pop('NODE_OPTIONS', None)
            ended, steps, decisions = [], 0, 0
            trajectory_hash = hashlib.sha256()
            begin = time.monotonic()
            try:
                request = {'op': 'reset', 'n': games, 'playerCount': n, 'mode': 'economic',
                           'arenaSeed': seed, 'featureRevisions': {'learner': model_revision(model)}}
                left, right = control.call(request), captured.call(request)
                while any(r is not None for r in left['observations']):
                    actions = []
                    assert len(left['observations']) == len(right['observations']) == games
                    assert left['ended'] == right['ended']
                    ended.extend(left['ended'])
                    for plain, instrumented in zip(left['observations'], right['observations']):
                        if plain is None:
                            assert instrumented is None
                            actions.append(None)
                            continue
                        root = instrumented.pop('discardRoot', None)
                        assert plain == instrumented, 'Capture changed model inputs or action order'
                        action, _ = model.predict(plain['state'], plain['actions'])
                        trajectory_hash.update(json.dumps([plain, action], sort_keys=True).encode())
                        actions.append(action)
                        decisions += 1
                        if root:
                            assert plain['roles'][root['request']['player']] == 'learner'
                            assert len(root['legal']) == len(plain['actions'])
                            roots.append({**root, 'rootIndex': len(roots), 'players': n,
                                'episode': plain['episode'], 'gameSeed': seed + '-' + str(plain['episode'] // (4*n)),
                                'variant': plain['variant'], 'sealed': plain['sealed'], 'round': plain['round'],
                                'model_proposal': action, 'model_move': root['legal'][action]})
                    left, right = control.call({'op': 'step', 'actions': actions}), captured.call({'op': 'step', 'actions': actions})
                    steps += 1
                assert left == right
                ended.extend(left['ended'])
            finally:
                control.close()
                captured.close()
            assert len(ended) == games and len({r['episode'] for r in ended}) == games
            assert all(not r['truncated'] and not r['searchStats'] for r in ended)
            rows = [{**r, 'seat': r['roles'].index('learner'), 'win': r['value'][r['roles'].index('learner')]} for r in ended]
            validate_pairs(rows, n)
            assert {r['gameSeed'] for r in rows} == {seed + '-' + str(i) for i in range(deals)}
            reports[str(n)] = {'games': games, 'exact_observations_actions_and_terminal_records': True,
                'truncations': 0, 'trajectory_sha256': trajectory_hash.hexdigest(), 'decisions': decisions,
                'seconds': time.monotonic() - begin, 'roots': sum(r['players'] == n for r in roots), 'results': rows}
            write(out / f'{n}p.json', reports[str(n)])
            (out / 'roots.jsonl').write_text(''.join(json.dumps(r) + '\n' for r in roots))
            print({k: v for k, v in reports[str(n)].items() if k != 'results'}, flush=True)
        expected = 4 * args.smoke_players if args.smoke_players else protocol['unique_games']
        assert sum(r['games'] for r in reports.values()) == expected
        assert len({(r['players'], r['episode']) for r in roots}) == len(roots)
        status.update(status='complete', unique_games=expected, engine_game_runs=expected*2,
            roots=len(roots), counts={n: {k: v for k, v in r.items() if k != 'results'} for n, r in reports.items()},
            smoke=bool(args.smoke_players), all_trace_controls_match=True, truncations=0)
    except BaseException as error:
        status.update(status='failed', error=type(error).__name__ + ': ' + str(error))
        raise
    finally:
        status['artifact_sha256'] = {p.name: digest(p) for p in out.iterdir() if p.is_file()}
        write(out / 'collection-check.json', status)
        if args.upload:
            assert not args.smoke_players
            from huggingface_hub import HfApi
            HfApi().upload_folder(repo_id=protocol['repo'], folder_path=out, path_in_repo=protocol['output_prefix'])
        print({k: v for k, v in status.items() if k not in ['artifact_sha256', 'counts']}, flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser(__doc__)
    p.add_argument('model', type=Path)
    p.add_argument('output', type=Path)
    p.add_argument('--smoke-players', type=int, choices=range(2, 7))
    p.add_argument('--upload', action='store_true')
    run(p.parse_args())
