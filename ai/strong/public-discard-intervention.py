"""Paired complete games with one public-belief discard intervention per game."""
import argparse
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
from arena_statistics import validate_pairs, win_summary
from huggingface_hub import HfApi, hf_hub_download

spec = importlib.util.spec_from_file_location('discard_audit', Path(__file__).with_name('audit-public-discard-teacher.py'))
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)
def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def write(path, x):
    Path(path).write_text(json.dumps(x, indent=2) + '\n')


def main():
    p = argparse.ArgumentParser(__doc__)
    p.add_argument('arm', choices=['parent', 'economic', 'neural'])
    p.add_argument('output', type=Path)
    p.add_argument('--smoke', action='store_true')
    p.add_argument('--upload', action='store_true')
    a = p.parse_args()
    assert not (a.smoke and a.upload)
    assert not os.environ.get('NODE_OPTIONS')
    protocol_path = ROOT / 'ai/strong/public-discard-intervention-protocol-v1.json'
    protocol = json.loads(protocol_path.read_text())
    players, deals = protocol['players'], 1 if a.smoke else protocol['deals']
    games = deals * players * 4
    arena_seed = protocol['smoke_arena_seed'] if a.smoke else protocol['arena_seed']
    samples = 2 if a.smoke else protocol['samples_per_batch']
    pin = protocol['model']
    model = Model(hf_hub_download(protocol['repo'], pin['path'], revision=pin['revision']), threads=protocol['ort_threads'])
    assert model.sha256 == pin['sha256'] and model_revision(model) == pin['feature_revision']
    assert model.session.get_modelmeta().custom_metadata_map['powergrid.inference_precision'] == 'float64'
    out = a.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    status = {'status': 'running', 'arm': a.arm, 'smoke': a.smoke, 'players': players,
        'model_sha256': model.sha256, 'protocol_sha256': digest(protocol_path),
        'source_revision': os.environ.get('SOURCE_REVISION'), 'source_sha256': os.environ.get('SOURCE_SHA256'),
        'trained': False, 'qualification_eligible': False}
    search_protocol = {**protocol, 'seed_template': protocol[
        'smoke_search_seed_template' if a.smoke else 'search_seed_template']}
    os.environ['NODE_OPTIONS'] = '--require ' + str(ROOT / 'ai/strong/capture-public-discard.cjs')
    try:
        live = EnginePool(min(games, protocol['workers']), script='ai/strong/bridge.cjs')
    finally:
        os.environ.pop('NODE_OPTIONS', None)
    rollouts = None if a.arm == 'parent' else EnginePool(min(protocol['workers'], samples * 4),
        script='ai/strong/continuation-rollouts.cjs')
    begin = time.monotonic()
    decisions, results, roots, seen = 0, [], [], set()
    try:
        response = live.call({'op': 'reset', 'n': games, 'playerCount': players,
            'mode': protocol['opponent'], 'arenaSeed': arena_seed,
            'featureRevisions': {'learner': pin['feature_revision']}})
        with (out / 'roots.jsonl').open('w') as file:
            while any(r is not None for r in response['observations']):
                assert len(response['observations']) == games
                results.extend(response['ended'])
                actions = []
                for row in response['observations']:
                    if row is None:
                        actions.append(None)
                        continue
                    root = row.pop('discardRoot', None)
                    proposal = model.predict(row['state'], row['actions'])[0]
                    choice = proposal
                    decisions += 1
                    if root:
                        episode = row['episode']
                        assert episode not in seen and row['roles'][root['request']['player']] == 'learner'
                        seen.add(episode)
                        assert len(root['legal']) == len(row['actions'])
                        root.update(rootIndex=episode, episode=episode, players=players,
                            variant=row['variant'], sealed=row['sealed'], round=row['round'],
                            model_proposal=proposal, model_move=root['legal'][proposal])
                        root['public_root_sha256'] = hashlib.sha256(json.dumps(root['request'], sort_keys=True).encode()).hexdigest()
                        if rollouts:
                            guidance = audit.search(rollouts, model, root, a.arm,
                                protocol['search_batch'], samples, search_protocol)
                            root['guidance'] = guidance
                            if not guidance['truncated'] and proposal not in guidance['winner_set']:
                                choice = min(guidance['winner_set'])
                        root['selected'] = choice
                        root['selected_move'] = root['legal'][choice]
                        roots.append(root)
                        file.write(json.dumps(root) + '\n')
                        file.flush()
                        print({'arm': a.arm, 'roots': len(roots), 'episode': episode,
                               'changed': choice != proposal, 'seconds': time.monotonic() - begin}, flush=True)
                    actions.append(choice)
                response = live.call({'op': 'step', 'actions': actions})
            results.extend(response['ended'])
        assert len(results) == games and {r['episode'] for r in results} == set(range(games))
        results = [{**r, 'seat': r['roles'].index('learner'),
                    'win': r['value'][r['roles'].index('learner')]} for r in results]
        validate_pairs(results, players)
        assert {r['gameSeed'] for r in results} == {arena_seed + '-' + str(i) for i in range(deals)}
        assert all(not r['searchStats'] for r in results), 'Unexpected baseline search'
        search_caps = sum(r.get('guidance', {}).get('truncated', 0) for r in roots)
        game_caps = sum(r['truncated'] for r in results)
        report = {'arm': a.arm, 'results': results, 'summary': win_summary(results),
            'search_evaluations': sum(r.get('guidance', {}).get('evaluations', 0) for r in roots),
            'search_caps': search_caps, 'interventions': sum(r['selected'] != r['model_proposal'] for r in roots)}
        write(out / 'games.json', report)
        status.update(games=games, game_caps=game_caps, search_caps=search_caps,
            roots=len(roots), decisions=decisions, seconds=time.monotonic() - begin,
            search_evaluations=report['search_evaluations'], interventions=report['interventions'])
        assert not game_caps and not search_caps, 'Caps invalidate the intervention screen'
        status['status'] = 'complete'
    except BaseException as error:
        status.update(status='failed', error=type(error).__name__ + ': ' + str(error))
        raise
    finally:
        live.close()
        if rollouts:
            rollouts.close()
        status['artifact_sha256'] = {p.name: digest(p) for p in out.iterdir() if p.is_file()}
        write(out / 'intervention-check.json', status)
        if a.upload:
            HfApi().upload_folder(repo_id=protocol['repo'], folder_path=out,
                path_in_repo='runs/public-discard-intervention-v1-' + a.arm)
        print(status, flush=True)


if __name__ == '__main__':
    main()
