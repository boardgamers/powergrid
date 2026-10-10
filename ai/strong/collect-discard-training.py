"""Fresh public training roots with exact uninstrumented twin controls; no labels."""
import argparse
import gzip
import hashlib
import importlib.util
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
from huggingface_hub import HfApi, hf_hub_download
spec = importlib.util.spec_from_file_location('discard_batch_inference', Path(__file__).with_name('audit-neural-continuations.py'))
batch = importlib.util.module_from_spec(spec)
spec.loader.exec_module(batch)
def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def write(path, value):
    Path(path).write_text(json.dumps(value, indent=2) + '\n')


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('players', type=int, choices=range(2, 7))
    parser.add_argument('output', type=Path)
    parser.add_argument('--smoke', action='store_true')
    parser.add_argument('--upload', action='store_true')
    a = parser.parse_args()
    assert not (a.smoke and a.upload)
    assert not os.environ.get('NODE_OPTIONS')
    protocol_path = ROOT / 'ai/strong/discard-training-collection-protocol-v1.json'
    protocol = json.loads(protocol_path.read_text())
    pin = protocol['model']
    model = Model(hf_hub_download(protocol['repo'], pin['path'], revision=pin['revision']), threads=protocol['ort_threads'])
    assert model.sha256 == pin['sha256'] and model_revision(model) == pin['feature_revision']
    assert model.session.get_modelmeta().custom_metadata_map['powergrid.inference_precision'] == 'float64'
    out = a.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    status = {'status': 'running', 'players': a.players, 'smoke': a.smoke,
        'protocol_sha256': digest(protocol_path), 'model_sha256': model.sha256,
        'source_revision': os.environ.get('SOURCE_REVISION'), 'source_sha256': os.environ.get('SOURCE_SHA256'),
        'trained': False, 'labels_generated': False, 'qualification_eligible': False}
    root_count, reports = 0, {}
    begin = time.monotonic()
    try:
        with gzip.open(out / 'roots.jsonl.gz', 'wt') as root_file:
            for mode in protocol['modes_by_players'][str(a.players)]:
                deals = 1 if a.smoke else protocol['deals_per_mode_count']
                games = deals * a.players * 4
                seed = protocol['smoke_seed_template' if a.smoke else 'seed_template'].format(players=a.players, mode=mode)
                control = EnginePool(min(protocol['workers'], games), script='ai/strong/bridge.cjs')
                os.environ['NODE_OPTIONS'] = '--require ' + str(ROOT / 'ai/strong/capture-discard-training.cjs')
                try:
                    captured = EnginePool(min(protocol['workers'], games), script='ai/strong/bridge.cjs')
                finally:
                    os.environ.pop('NODE_OPTIONS', None)
                results, root_ordinals, root_keys, root_counts = [], {}, set(), {'train': 0, 'validation': 0}
                decisions, steps, policy_seconds, engine_seconds = 0, 0, 0., 0.
                trajectory = hashlib.sha256()
                mode_begin = time.monotonic()
                try:
                    reset = {'op': 'reset', 'n': games, 'playerCount': a.players, 'mode': mode,
                        'arenaSeed': seed, 'featureRevisions': {'learner': pin['feature_revision'], 'snapshot0': pin['feature_revision']}}
                    tick = time.perf_counter()
                    left, right = control.call(reset), captured.call(reset)
                    engine_seconds += time.perf_counter() - tick
                    while any(r is not None for r in left['observations']):
                        assert len(left['observations']) == len(right['observations']) == games
                        assert left['ended'] == right['ended']
                        results.extend(left['ended'])
                        active = [i for i, r in enumerate(left['observations']) if r is not None]
                        actions = [None] * games
                        tick = time.perf_counter()
                        for offset in range(0, len(active), protocol['batch_size']):
                            indices = active[offset:offset + protocol['batch_size']]
                            chosen = batch.predict_batch(model, [left['observations'][i] for i in indices])
                            for i, action in zip(indices, chosen):
                                actions[i] = action
                        policy_seconds += time.perf_counter() - tick
                        decisions += len(active)
                        for i, (plain, instrumented) in enumerate(zip(left['observations'], right['observations'])):
                            if plain is None:
                                assert instrumented is None
                                continue
                            root = instrumented.pop('discardRoot', None)
                            assert plain == instrumented, 'Capture changed public inputs or legal action order'
                            trajectory.update(json.dumps([plain, actions[i]], sort_keys=True).encode())
                            if root and plain['roles'][root['request']['player']] == 'learner':
                                episode = plain['episode']
                                deal = episode // (4 * a.players)
                                split = 'validation' if deal in protocol['validation_deal_indices'] else 'train'
                                assert len(root['legal']) == len(plain['actions'])
                                assert model.predict(plain['state'], plain['actions'])[0] == actions[i], 'Batched root proposal differs from serial inference'
                                ordinal = root_ordinals.get(episode, 0)
                                root_ordinals[episode] = ordinal + 1
                                state_hash = hashlib.sha256(json.dumps(root['request'], sort_keys=True).encode()).hexdigest()
                                assert (episode, state_hash) not in root_keys, 'Duplicate unchanged public root'
                                root_keys.add((episode, state_hash))
                                root.update(rootIndex=root_count, rootId=f'{a.players}:{mode}:{episode}:{ordinal}',
                                    players=a.players, mode=mode, episode=episode, ordinal=ordinal,
                                    deal=deal, gameSeed=seed + '-' + str(deal), split=split,
                                    variant=plain['variant'], sealed=plain['sealed'], round=plain['round'],
                                    public_root_sha256=state_hash, model_proposal=actions[i], model_move=root['legal'][actions[i]])
                                root_file.write(json.dumps(root) + '\n')
                                root_count += 1
                                root_counts[split] += 1
                        tick = time.perf_counter()
                        left, right = control.call({'op': 'step', 'actions': actions}), captured.call({'op': 'step', 'actions': actions})
                        engine_seconds += time.perf_counter() - tick
                        steps += 1
                    assert left == right
                    results.extend(left['ended'])
                finally:
                    control.close()
                    captured.close()
                assert len(results) == games and {r['episode'] for r in results} == set(range(games))
                rows = [{**r, 'seat': r['roles'].index('learner'), 'win': r['value'][r['roles'].index('learner')]} for r in results]
                validate_pairs(rows, a.players)
                assert {r['gameSeed'] for r in rows} == {seed + '-' + str(i) for i in range(deals)}
                assert all(not r['truncated'] and not r['searchStats'] for r in rows)
                reports[mode] = {'mode': mode, 'games': games, 'engine_game_runs': games * 2,
                    'roots': sum(root_counts.values()), 'root_splits': root_counts,
                    'games_with_roots': len(root_ordinals), 'games_with_multiple_roots': sum(v > 1 for v in root_ordinals.values()),
                    'exact_observations_actions_and_terminal_records': True,
                    'trajectory_sha256': trajectory.hexdigest(), 'decisions': decisions, 'steps': steps,
                    'seconds': time.monotonic() - mode_begin, 'engine_seconds': engine_seconds,
                    'policy_seconds': policy_seconds, 'truncations': 0, 'results': rows}
                write(out / (mode + '.json'), reports[mode])
                root_file.flush()
                print({k: v for k, v in reports[mode].items() if k != 'results'}, flush=True)
        expected = 4 * a.players * 4 if a.smoke else protocol['games_by_players'][str(a.players)]
        assert sum(r['games'] for r in reports.values()) == expected
        status.update(status='complete', games=expected, engine_game_runs=expected * 2, roots=root_count,
            counts={k: {x: v for x, v in r.items() if x != 'results'} for k, r in reports.items()},
            truncations=0, all_twin_controls_match=True, seconds=time.monotonic() - begin)
    except BaseException as error:
        status.update(status='failed', error=type(error).__name__ + ': ' + str(error))
        raise
    finally:
        status['artifact_sha256'] = {p.name: digest(p) for p in out.iterdir() if p.is_file()}
        write(out / 'collection-check.json', status)
        if a.upload:
            HfApi().upload_folder(repo_id=protocol['repo'], folder_path=out,
                path_in_repo=f'runs/discard-training-collection-v1-{a.players}p')
        print({k: v for k, v in status.items() if k not in ['counts', 'artifact_sha256']}, flush=True)


if __name__ == '__main__':
    main()
