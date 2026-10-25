"""Whole-game development evaluation through the standalone public JSON API.

The arena applies the returned move itself against its private legal menu. It
never sends private observations, opponent identities or future cards to the
policy process. Optional engineering audits compare every decision and engine
transition with the original direct-policy arena. No final seeds or selection.
"""
import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

from hybrid_search import Model, Node, model_revision
from population_hybrid_policy import PopulationPolicy
from arena_statistics import validate_pairs
from public_policy_runtime_v1 import checked_path, digest, encode


def read(path):
    return json.loads(Path(path).read_text())


def write(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False)+'\n')


def wire_json(value):
    # The frozen engine enumerates availableMoves in insertion order. Canonical
    # sorted JSON is suitable for hashing/equality, not this request transport.
    # Preserve the original order in raw receipts as well, for exact replay.
    return json.dumps(value, separators=(',', ':'), allow_nan=False)


def semantic(value):
    if isinstance(value, dict):
        return {k: semantic(v) for k, v in value.items() if k != 'elapsedMs'}
    if isinstance(value, list):
        return [semantic(v) for v in value]
    return value


def arena_semantic(response):
    """Only legacy bot wall-clock bookkeeping differs between two processes."""
    result = json.loads(encode(response))
    for row in result['observations']:
        if row is None:
            continue
        row.pop('moves', None)
        state = row['request']['state']
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
    return result


def validate_response(response, request, moves, ordering, identity):
    if not isinstance(response, dict) or 'error' in response:
        raise ValueError('Public policy failed: '+str(response))
    if any(encode(response.get(k)) != encode(request.get(k)) for k in ('requestId', 'revision')):
        raise ValueError('Public response has stale request metadata')
    if encode(response.get('playerOrder')) != encode(ordering):
        raise ValueError('Public response differs from arena player order')
    if any(encode(response.get(k)) != encode(v) for k, v in identity.items()):
        raise ValueError('Public response changed frozen policy identity')
    matches = [i for i, move in enumerate(moves) if encode(move) == encode(response.get('move'))]
    if len(matches) != 1:
        raise ValueError('Returned move is not uniquely legal in the independent arena')
    decision = response['decision']
    if (type(decision.get('index')) is not int or decision['index'] != matches[0]
            or encode(decision.get('move')) != encode(response['move'])):
        raise ValueError('Diagnostics differ from returned move')
    if response.get('qualification_eligible') is not False:
        raise ValueError('Research transport cannot claim qualification')
    return matches[0]


class PublicPolicyProcess:
    def __init__(self, root, descriptor, stderr):
        self.proc = subprocess.Popen([sys.executable, '-u', '-B',
            str(root/'ai/strong/public_policy_runtime_v1.py'), str(root),
            '--descriptor', descriptor, '--diagnostics'], cwd='/tmp',
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=stderr,
            text=True, bufsize=1, env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'})

    def call(self, request):
        self.proc.stdin.write(wire_json(request)+'\n'); self.proc.stdin.flush()
        line = self.proc.stdout.readline()
        if not line:
            raise RuntimeError('Standalone public policy exited; inspect its preserved stderr')
        return json.loads(line)

    def close(self):
        self.proc.stdin.close()
        code = self.proc.wait(timeout=30)
        self.proc.stdout.close()
        if code:
            raise RuntimeError('Standalone public policy exited with code '+str(code))


def configuration(args):
    root = args.artifact.resolve()
    spec_path = checked_path(root, args.descriptor)
    spec = read(spec_path)
    manifest_path = checked_path(root, spec['runtime_manifest']['path'])
    if digest(manifest_path) != spec['runtime_manifest']['sha256']:
        raise ValueError('Artifact manifest changed')
    manifest = read(manifest_path)
    for name, sha in manifest.items():
        if digest(checked_path(root, name)) != sha:
            raise ValueError('Artifact changed: '+name)
    entry = 'ai/strong/public_policy_arena_v1.py'
    if Path(__file__).resolve() != checked_path(root, entry) or manifest.get(entry) != digest(__file__):
        raise ValueError('Run the evaluator from its pinned standalone artifact')
    settings = spec['settings']
    if settings['max_steps'] != 2400:
        raise ValueError('Whole-game development uses the full frozen continuation horizon')
    if (not args.seed or 'reserved' in args.seed.lower() or args.start < 0
            or args.deals < 1 or args.workers < 1):
        raise ValueError('Invalid development schedule or forbidden final seed')
    if (args.opponent == 'a260') != bool(args.opponent_model):
        raise ValueError('Snapshot opponent requires its pinned model')
    identity = {'policySha256': digest(spec_path), 'modelSha256': spec['model']['sha256'],
        'runtimeManifestSha256': digest(manifest_path), 'featureRevision': spec['feature_revision'],
        'backend': spec['backend'], 'settings': settings}
    return {**vars(args), 'artifact': str(root), 'runtime': str(root),
        'output': str(args.output.resolve()), 'arm': settings['arm'], 'samples': settings['samples'],
        'search_workers': settings['workers'], 'model': str(checked_path(root, spec['model']['path'])),
        'model_sha256': spec['model']['sha256'], 'identity': identity,
        'reference_artifact': str(args.reference_artifact.resolve()) if args.reference_artifact else None,
        'opponent_model': str(args.opponent_model.resolve()) if args.opponent_model else None,
        'opponent_sha256': digest(args.opponent_model) if args.opponent_model else None}


def play(config, episode):
    root, output = Path(config['artifact']), Path(config['output'])
    model = Model(config['model'], threads=config['identity']['settings']['threads'])
    assert model.sha256 == config['model_sha256']
    bridge = reference_bridge = direct = policy = None
    logs = (output/f'policy-{episode}.stderr.log').open('x')
    receipt = output/f'decisions-{episode}.jsonl'
    counts = dict(decisions=0, root_filter_overrides=0, search_changes=0,
                  rollouts=0, rollout_caps=0, neural_decisions=0)
    began = time.perf_counter()
    try:
        bridge = Node(str(root/'ai/strong/public-arena-bridge.cjs'))
        policy = PublicPolicyProcess(root, config['descriptor'], logs)
        opponent = Model(config['opponent_model'], threads=1) if config.get('opponent_model') else None
        if opponent:
            assert opponent.sha256 == config['opponent_sha256']
        revisions = {'learner': model_revision(model)}
        if opponent:
            revisions['snapshot0'] = model_revision(opponent)
        reset = {'op': 'reset', 'n': 1, 'offset': episode, 'arenaSeed': config['seed'],
                 'playerCount': config['players'], 'mode': 'snapshot0' if opponent else config['opponent'],
                 'featureRevisions': revisions}
        if config.get('reference_artifact'):
            old = Path(config['reference_artifact'])
            reference_bridge = Node(str(old/'ai/strong/public-arena-bridge.cjs'))
            direct = PopulationPolicy(model, old/'ai/strong/population-hybrid-policy.cjs',
                arm=config['arm'], samples=config['samples'], workers=config['search_workers'], max_steps=2400)
            reference = reference_bridge.call(reset)
        state = bridge.call({**reset, 'publicMoves': True})
        with receipt.open('x') as stream:
            while True:
                if reference_bridge:
                    assert arena_semantic(state) == arena_semantic(reference), 'Public-move arena differs from original logical engine trajectory'
                if state['ended']:
                    assert len(state['ended']) == 1 and state['observations'] == [None]
                    terminal = state['ended'][0]
                    seat = terminal['roles'].index('learner')
                    terminal = {**terminal, 'seat': seat, 'win': terminal['value'][seat]}
                    record = {'episode': episode, 'terminal': terminal, **counts,
                        'seconds': time.perf_counter()-began, 'decision_receipt_sha256': digest(receipt),
                        'public_runtime_identity': config['identity'],
                        'direct_reference_trajectory_checked': bool(reference_bridge)}
                    write(output/f'game-{episode}.json', record)
                    return record
                row = state['observations'][0]
                if row is None:
                    raise RuntimeError('Arena stopped without a terminal result')
                actor = row['roles'][row['seat']]
                if actor == 'learner':
                    q = {**row['request'], 'requestId': f'{episode}:{counts["decisions"]+1}',
                         'revision': counts['decisions']+1}
                    assert q['player'] == row['seat']
                    public = q['state']
                    assert public['seed'] == 'secret' and public['powerPlantsDeck'] == []
                    assert not public.get('hiddenLog') and 'powerPlantDeckAfterStep3' not in public
                    if public['options']['fastBid']:
                        assert all(p['bid'] == 0 for p in public['players'])
                    response = policy.call(q)
                    choice = validate_response(response, q, row['moves'], row['playerOrder'], config['identity'])
                    result = response['decision']
                    assert result['modelProposal'] == model.predict(row['state'], row['actions'])[0]
                    gold = direct.choose(q) if direct else None
                    if direct:
                        assert semantic(result) == semantic(gold), 'Standalone decision differs from original policy'
                    counts['decisions'] += 1
                    counts['root_filter_overrides'] += int(result['filterApplied'])
                    if result['search']:
                        search = result['search']
                        counts['rollouts'] += search['evaluations']
                        counts['rollout_caps'] += search['truncated']
                        counts['neural_decisions'] += search['neuralDecisions']
                        counts['search_changes'] += int(choice != result['modelProposal'] and not result['filterApplied'])
                    stream.write(wire_json({'decision': counts['decisions'], 'round': row['round'], **result,
                        'publicRequest': q, 'publicResponse': response, 'arenaMoves': row['moves'],
                        'arenaPlayerOrder': row['playerOrder'], 'directReference': gold})+'\n'); stream.flush()
                    action = {'publicMove': response['move']}
                else:
                    assert actor == 'snapshot0' and opponent is not None
                    choice = opponent.predict(row['state'], row['actions'])[0]
                    action = choice
                state = bridge.call({'op': 'step', 'actions': [action]})
                if reference_bridge:
                    reference = reference_bridge.call({'op': 'step', 'actions': [choice]})
    except BaseException as error:
        write(output/f'failure-{episode}.json', {'episode': episode, 'error': type(error).__name__+': '+str(error),
            'partial_counts': counts, 'receipt_sha256': digest(receipt) if receipt.exists() else None})
        raise
    finally:
        try:
            if policy:
                policy.close()
        finally:
            logs.close()
            for handle in (direct, reference_bridge, bridge):
                if handle:
                    handle.close()


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--artifact', type=Path, required=True)
    parser.add_argument('--descriptor', default='policy.json')
    parser.add_argument('--players', type=int, choices=range(2, 7), required=True)
    parser.add_argument('--opponent', choices=['legacy', 'heuristic', 'economic', 'rush', 'search_geo', 'economic_capacity_v1', 'a260'], required=True)
    parser.add_argument('--opponent-model', type=Path)
    parser.add_argument('--seed', required=True)
    parser.add_argument('--start', type=int, default=0)
    parser.add_argument('--deals', type=int, default=1)
    parser.add_argument('--workers', type=int, default=8)
    parser.add_argument('--reference-artifact', type=Path,
                        help='Engineering only: compare every move and engine transition with the original arena')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(); config = configuration(args)
    args.output.mkdir(parents=True, exist_ok=False)
    episodes = list(range(args.start*4*args.players, (args.start+args.deals)*4*args.players))
    records, errors = [], []
    began = time.perf_counter(); passed = False; validation_error = None
    try:
        with ProcessPoolExecutor(max_workers=min(args.workers, len(episodes))) as pool:
            pending = {pool.submit(play, config, episode): episode for episode in episodes}
            for future in as_completed(pending):
                episode = pending[future]
                try:
                    record = future.result(); records.append(record)
                    print(encode({'episode': episode, 'complete': len(records), 'expected': len(episodes),
                                  'seconds': record['seconds']}), flush=True)
                except Exception as error:
                    errors.append({'episode': episode, 'error': type(error).__name__+': '+str(error)})
                    print(encode(errors[-1]), flush=True)
        assert not errors and len(records) == len(episodes)
        validate_pairs([r['terminal'] for r in records], args.players)
        assert not any(r['terminal']['truncated'] or r['rollout_caps'] for r in records)
        assert all(not s['truncated'] for r in records for s in r['terminal']['searchStats'].values())
        passed = True
    except BaseException as error:
        validation_error = type(error).__name__+': '+str(error)
        raise
    finally:
        write(args.output/'evaluation.json', {'config': config, 'results': sorted(records, key=lambda r: r['episode']),
            'errors': errors, 'validation_error': validation_error, 'passed': passed,
            'expected_games': len(episodes), 'completed_games': len(records),
            'all_complete': len(records) == len(episodes) and not errors,
            'game_caps': sum(r['terminal']['truncated'] for r in records),
            'rollout_caps': sum(r['rollout_caps'] for r in records), 'seconds': time.perf_counter()-began,
            'qualification_eligible': False, 'reserved_final_seeds_used': False})


if __name__ == '__main__':
    main()
