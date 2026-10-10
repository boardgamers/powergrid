"""Paired public-scenario teacher audit with batched frozen-model continuations.

This measures target reliability and runtime, not arena playing strength. No gradients.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np
from infer import Model, Node
from pool import EnginePool
from feature_contract import model_revision


def predict_batch(model, rows):
    counts = [len(r['actions']) for r in rows]
    actions = np.zeros((len(rows), max(counts), 98), dtype=np.float32)
    mask = np.zeros(actions.shape[:2], dtype=bool)
    for i, row in enumerate(rows):
        if row['featureRevision'] != '4.0-multiplayer':
            raise ValueError('Continuation encoder mismatch')
        actions[i, :counts[i]] = row['actions']
        mask[i, :counts[i]] = True
    logits, _ = model.session.run(None, {
        'state': np.asarray([r['state'] for r in rows], dtype=np.float32),
        'actions': actions, 'mask': mask,
    })
    selected = logits.argmax(-1).tolist()
    assert all(0 <= a < n for a, n in zip(selected, counts))
    return selected


def evaluate_position(pool, model, fixture, options, batch, samples, max_steps):
    seed = f"teacher-reliability-v1-{fixture['fixtureIndex']}-{batch}"
    count = samples * len(options)
    start = time.perf_counter()
    response = pool.call({
        'op': 'reset', 'n': count, 'state': fixture['request']['state'],
        'player': fixture['request']['player'], 'options': options,
        'samples': samples, 'seed': seed, 'maxSteps': max_steps,
        'featureRevision': '4.0-multiplayer', 'continuation': 'neural',
    })
    engine_seconds = time.perf_counter() - start
    policy_seconds = 0.0
    decisions = 0
    ended = response['ended']
    last_progress = time.perf_counter()
    while any(r is not None for r in response['observations']):
        rows = response['observations']
        live = [i for i, r in enumerate(rows) if r is not None]
        begin = time.perf_counter()
        choices = predict_batch(model, [rows[i] for i in live])
        policy_seconds += time.perf_counter() - begin
        decisions += len(live)
        actions = [None] * count
        for i, choice in zip(live, choices):
            actions[i] = choice
        begin = time.perf_counter()
        response = pool.call({'op': 'step', 'actions': actions})
        engine_seconds += time.perf_counter() - begin
        ended.extend(response['ended'])
        if time.perf_counter() - last_progress >= 60:
            print(json.dumps({'stage': 'progress', 'fixtureIndex': fixture['fixtureIndex'],
                              'batch': batch, 'completed': len(ended), 'requested': count,
                              'decisions': decisions}), flush=True)
            last_progress = time.perf_counter()
    assert len(ended) == count and {r['env'] for r in ended} == set(range(count))
    outcomes = {str(i): [None] * samples for i in options}
    seen = set()
    for row in ended:
        key = row['actionIndex'], row['sample']
        assert key not in seen and key[0] in options and 0 <= key[1] < samples
        seen.add(key)
        assert (row['value'] is None) == row['truncated']
        if row['value'] is not None:
            assert 0 <= row['value'] <= 1
        outcomes[str(key[0])][key[1]] = row['value']
    truncated = sum(r['truncated'] for r in ended)
    values = {i: sum(v for v in xs if v is not None) for i, xs in outcomes.items()}
    # A cap is missing evidence, never an implicit defeat or a qualified target.
    winners = [] if truncated else [int(i) for i, v in values.items() if v == max(values.values())]
    return {'fixtureIndex': fixture['fixtureIndex'], 'cell': fixture['cell'],
            'batch': batch, 'samples': samples, 'continuation': 'neural',
            'result': {'evaluations': count, 'truncated': truncated, 'values': values,
                       'sampleOutcomes': outcomes, 'winnerSet': winners},
            'timing': {'seconds': time.perf_counter() - start, 'engine_seconds': engine_seconds,
                       'policy_seconds': policy_seconds, 'policy_decisions': decisions}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('model', type=Path)
    parser.add_argument('--fixtures', type=Path, required=True)
    parser.add_argument('--players', type=int, choices=range(2, 7), required=True)
    parser.add_argument('--samples', type=int, default=48)
    parser.add_argument('--workers', type=int, default=24)
    parser.add_argument('--threads', type=int, default=4)
    parser.add_argument('--max-steps', type=int, default=2400)
    parser.add_argument('--limit', type=int, default=0, help='Smoke check only; zero means all cells')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--model-revision', required=True)
    parser.add_argument('--expected-model-sha256', required=True)
    parser.add_argument('--upload-repo')
    parser.add_argument('--run', default='teacher-neural-continuation-v1')
    args = parser.parse_args()
    if min(args.samples, args.workers, args.threads, args.max_steps) < 1:
        parser.error('Positive budgets required')
    fixture_hash = hashlib.sha256(args.fixtures.read_bytes()).hexdigest()
    if fixture_hash != '855b34ad7f07665dfcb012a673147f0780820a9e7560fda268a9a39478c60ff4':
        raise ValueError('Unexpected audit fixtures')
    model = Model(args.model, threads=args.threads)
    if model.sha256 != args.expected_model_sha256 or model_revision(model) != '4.0-multiplayer':
        raise ValueError('Frozen model contract mismatch')
    fixtures = [json.loads(line) for line in args.fixtures.read_text().splitlines()]
    fixtures = [r for r in fixtures if r['cell'][0] == args.players]
    assert len(fixtures) == 12
    if args.limit:
        fixtures = fixtures[:args.limit]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    node = Node('strong/continuation-rollouts.cjs')
    rows = []
    try:
        with args.output.open('w') as output:
            for fixture in fixtures:
                prepared = node.call({'op': 'prepare', **fixture['request'], 'featureRevision': '4.0-multiplayer'})
                options = prepared['options']
                # Confirm batching retains the single-position root action.
                root = prepared['observation']
                proposal = predict_batch(model, [root])[0]
                assert proposal == model.predict(root['state'], root['actions'])[0]
                pool = EnginePool(min(args.workers, args.samples * len(options)),
                                  script='ai/strong/continuation-rollouts.cjs')
                try:
                    for batch in ['a', 'b']:
                        row = evaluate_position(pool, model, fixture, options, batch, args.samples, args.max_steps)
                        row['root_model_proposal'] = proposal
                        row['root_model_proposal_in_fixed_shortlist'] = proposal in options
                        rows.append(row)
                        output.write(json.dumps(row) + '\n')
                        output.flush()
                        print(json.dumps({'stage': 'completed', 'fixtureIndex': fixture['fixtureIndex'],
                                          'batch': batch, 'truncated': row['result']['truncated'],
                                          **row['timing']}), flush=True)
                finally:
                    pool.close()
    finally:
        node.close()
    manifest = {'players': args.players, 'positions': len(fixtures), 'searches': len(rows),
                'samples': args.samples, 'max_steps': args.max_steps, 'workers': args.workers,
                'model_sha256': model.sha256, 'model_revision': args.model_revision,
                'fixture_sha256': fixture_hash,
                'output_sha256': hashlib.sha256(args.output.read_bytes()).hexdigest(),
                'evaluations': sum(r['result']['evaluations'] for r in rows),
                'truncated': sum(r['result']['truncated'] for r in rows),
                'engine_seconds': sum(r['timing']['engine_seconds'] for r in rows),
                'policy_seconds': sum(r['timing']['policy_seconds'] for r in rows),
                'scope': 'Reused development positions, fixed reference shortlist and scenarios; no strength claim.',
                'changes': 'Only continuation policy changes. Root model proposals are recorded, not added to the reference shortlist.'}
    manifest_path = args.output.with_suffix('.manifest.json')
    manifest_path.write_text(json.dumps(manifest, indent=2) + '\n')
    if args.upload_repo:
        from huggingface_hub import HfApi
        api = HfApi()
        for path in [args.output, manifest_path]:
            api.upload_file(repo_id=args.upload_repo, path_or_fileobj=path,
                            path_in_repo=f'runs/{args.run}/{path.name}')
    print(json.dumps(manifest), flush=True)


if __name__ == '__main__':
    main()
