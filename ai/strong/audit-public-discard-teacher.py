"""Paired public-belief discard guidance audit; no gradients or strength claim."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'ai'))
from infer import Model, Node
from pool import EnginePool
from feature_contract import model_revision
from five_plant_screen import read, write, digest
from huggingface_hub import HfApi, hf_hub_download

spec = importlib.util.spec_from_file_location('neural_continuation', Path(__file__).with_name('audit-neural-continuations.py'))
neural = importlib.util.module_from_spec(spec)
spec.loader.exec_module(neural)


def search(pool, model, root, policy, batch, samples, protocol):
    options = list(range(len(root['legal'])))
    count = len(options) * samples
    begin = time.perf_counter()
    response = pool.call({'op': 'reset', **root['request'], 'n': count, 'options': options,
        'samples': samples, 'seed': protocol['seed_template'].format(rootIndex=root['rootIndex'], batch=batch),
        'maxSteps': protocol['max_steps'], 'featureRevision': protocol['model']['feature_revision'],
        'continuation': policy})
    engine_seconds, policy_seconds, decisions = time.perf_counter() - begin, 0., 0
    ended = list(response['ended'])
    while any(r is not None for r in response['observations']):
        assert policy == 'neural', 'Non-neural continuations should run inside the engine'
        rows = response['observations']
        live = [i for i, r in enumerate(rows) if r is not None]
        tick = time.perf_counter()
        choices = neural.predict_batch(model, [rows[i] for i in live])
        policy_seconds += time.perf_counter() - tick
        decisions += len(live)
        actions = [None] * count
        for i, choice in zip(live, choices):
            actions[i] = choice
        tick = time.perf_counter()
        response = pool.call({'op': 'step', 'actions': actions})
        engine_seconds += time.perf_counter() - tick
        ended.extend(response['ended'])
    assert len(ended) == count and {r['env'] for r in ended} == set(range(count))
    assert {(r['actionIndex'], r['sample']) for r in ended} == {(a, s) for a in options for s in range(samples)}
    outcomes = {str(a): [None] * samples for a in options}
    for row in ended:
        assert row['truncated'] == (row['value'] is None)
        assert row['steps'] <= protocol['max_steps']
        if row['value'] is not None:
            assert 0 <= row['value'] <= 1
        outcomes[str(row['actionIndex'])][row['sample']] = row['value']
    caps = sum(r['truncated'] for r in ended)
    values = None if caps else {a: sum(xs) / samples for a, xs in outcomes.items()}
    winners = [] if caps else [int(a) for a, value in values.items() if value == max(values.values())]
    return {'rootIndex': root['rootIndex'], 'players': root['players'], 'episode': root['episode'],
        'variant': root['variant'], 'sealed': root['sealed'], 'round': root['round'],
        'continuation': policy, 'batch': batch, 'samples': samples, 'options': options,
        'original_proposal': root['model_proposal'], 'sample_outcomes': outcomes,
        'values': values, 'winner_set': winners, 'evaluations': count, 'truncated': caps,
        'timing': {'seconds': time.perf_counter() - begin, 'engine_seconds': engine_seconds,
                   'policy_seconds': policy_seconds, 'policy_decisions': decisions}}


def main():
    p = argparse.ArgumentParser(__doc__)
    p.add_argument('players', type=int, choices=range(2, 7))
    p.add_argument('output', type=Path)
    p.add_argument('--smoke', action='store_true')
    p.add_argument('--upload', action='store_true')
    args = p.parse_args()
    assert not (args.smoke and args.upload)
    assert not os.environ.get('NODE_OPTIONS'), 'No additional instrumentation permitted'
    protocol_path = ROOT / 'ai/strong/public-discard-teacher-protocol-v1.json'
    protocol = read(protocol_path)
    dataset, pin = protocol['dataset'], protocol['model']
    fixtures = Path(hf_hub_download(protocol['repo'], dataset['path'], revision=dataset['revision']))
    assert digest(fixtures) == dataset['sha256']
    all_roots = [json.loads(line) for line in fixtures.read_text().splitlines()]
    assert len(all_roots) == dataset['roots']
    roots = [r for r in all_roots if r['players'] == args.players]
    if args.smoke:
        roots = roots[:1]
    assert roots
    samples = 2 if args.smoke else protocol['samples_per_batch']
    model = Model(hf_hub_download(protocol['repo'], pin['path'], revision=pin['revision']), threads=protocol['ort_threads'])
    assert model.sha256 == pin['sha256'] and model_revision(model) == pin['feature_revision']
    assert model.session.get_modelmeta().custom_metadata_map['powergrid.inference_precision'] == 'float64'
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    status = {'status': 'running', 'players': args.players, 'positions': len(roots), 'smoke': args.smoke,
        'model_sha256': model.sha256, 'dataset_sha256': digest(fixtures), 'protocol_sha256': digest(protocol_path),
        'source_revision': os.environ.get('SOURCE_REVISION'), 'source_sha256': os.environ.get('SOURCE_SHA256'),
        'trained': False, 'qualification_eligible': False}
    rows = []
    worker = Node('strong/worker.cjs')
    pool = EnginePool(min(protocol['workers'], samples * min(len(r['legal']) for r in roots)),
                      script='ai/strong/continuation-rollouts.cjs')
    try:
        with (out / 'rows.jsonl').open('w') as output:
            for root in roots:
                prepared = worker.call({**root['request'], 'featureRevision': pin['feature_revision']})
                assert 'error' not in prepared and prepared['moves'] == root['legal']
                proposal = model.predict(prepared['state'], prepared['actions'])[0]
                assert proposal == root['model_proposal']
                assert all(a['name'] == 'DiscardPowerPlant' for a in root['legal'])
                for policy in protocol['continuations']:
                    for batch in protocol['batches']:
                        row = search(pool, model, root, policy, batch, samples, protocol)
                        rows.append(row)
                        output.write(json.dumps(row) + '\n')
                        output.flush()
                recent = rows[-len(protocol['continuations']) * len(protocol['batches']):]
                print({'root': root['rootIndex'], 'searches': len(rows),
                    'truncated': sum(r['truncated'] for r in recent),
                    'seconds': sum(r['timing']['seconds'] for r in recent)}, flush=True)
        assert len(rows) == len(roots) * len(protocol['continuations']) * len(protocol['batches'])
        evaluations = sum(r['evaluations'] for r in rows)
        if not args.smoke:
            assert evaluations == protocol['rollouts_by_player_count'][str(args.players)]
        status.update(status='complete', searches=len(rows), evaluations=evaluations,
            truncated=sum(r['truncated'] for r in rows),
            engine_seconds=sum(r['timing']['engine_seconds'] for r in rows),
            policy_seconds=sum(r['timing']['policy_seconds'] for r in rows),
            policy_decisions=sum(r['timing']['policy_decisions'] for r in rows))
    except BaseException as error:
        status.update(status='failed', error=type(error).__name__ + ': ' + str(error))
        raise
    finally:
        worker.close()
        pool.close()
        status['artifact_sha256'] = {p.name: digest(p) for p in out.iterdir() if p.is_file()}
        write(out / 'audit-check.json', status)
        if args.upload:
            HfApi().upload_folder(repo_id=protocol['repo'], folder_path=out,
                path_in_repo=f'runs/public-discard-teacher-v1-{args.players}p')
        print(status, flush=True)


if __name__ == '__main__':
    main()
