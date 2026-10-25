"""Fresh focal roots chosen independently of outcomes and surrogate predictions."""
import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import time

from strategic_collection import ROOT, read, write, digest
from hybrid_search import Model, Node
from population_hybrid_policy import PopulationPolicy

STRONG = ROOT/'ai/strong'
PROTOCOL = STRONG/'surrogate-continuation-protocol-v1.json'
PHASES = ('plant', 'bid', 'building')


def object_hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def contract(players, deal, seat, rule, mode):
    p = read(PROTOCOL)
    assert type(players) is int and players in p['player_counts']
    assert type(deal) is int and 0 <= deal < p['deals_per_count']
    assert type(seat) is int and 0 <= seat < players
    assert type(rule) is int and rule in range(4)
    assert mode in ('root', 'runtime', 'preflight')
    if mode != 'root': assert deal == 0
    return {'players': players, 'deal': deal, 'seat': seat, 'rule': rule,
            'episode': 4*(deal*players+seat)+rule,
            'seed': p[mode+'_seed_template'].format(players=players), 'mode': mode,
            'training_eligible': False, 'qualification_eligible': False}


def candidate(request, prepared, receipt, identity, decision):
    """Use only public inputs and the already executed focal-policy decision."""
    assert type(decision) is int and decision >= 0
    state = request['state']; n = identity['players']
    assert len(state['players']) == n and request['player'] == identity['seat']
    assert state['options']['map'] == 'Germany' and state['options']['showMoney'] is True
    assert state['options']['variant'] == ('recharged' if identity['rule'] % 2 else 'original')
    assert bool(state['options'].get('fastBid')) is (identity['rule'] < 2)
    assert state['seed'] == 'secret' and state['powerPlantsDeck'] == [] and state['hiddenLog'] == []
    assert 'powerPlantDeckAfterStep3' not in state and 'automation' not in state
    assert all(p['lastMove'] is None for p in state['players'])
    if identity['rule'] < 2:
        assert state['currentBid'] == 0 and all(p['bid'] == 0 for p in state['players'])
    moves = prepared['moves']; names = {m['name'] for m in moves}
    phase = 'plant' if 'ChoosePowerPlant' in names else 'bid' if 'Bid' in names else 'building' if 'Build' in names else None
    if phase is None or len(moves) < 2: return None
    assert receipt['arm'] == 'filter' and receipt['search'] is None
    assert receipt['modelSha256'] == read(PROTOCOL)['focal_model_sha256']
    baseline, proposal = receipt['index'], receipt['modelProposal']
    assert type(baseline) is type(proposal) is int and 0 <= baseline < len(moves) and 0 <= proposal < len(moves)
    proof = prepared['lossFilter']
    assert baseline == (proof['passIndex'] if proposal in proof['forbidden'] else proposal)
    assert receipt['move'] == moves[baseline]
    choices = [i for i in prepared['options'] if i != baseline and i not in proof['forbidden']]
    if not choices: return None
    assert all(prepared['observation']['actions'][i][100] == 1 for i in choices)
    alternative = max(choices, key=lambda i: (prepared['observation']['actions'][i][74], -i))
    rank = object_hash([identity['seed'], identity['episode'], phase, decision])
    return {'identity': deepcopy(identity), 'decision': decision, 'phase': phase, 'rank': rank,
            'request': deepcopy(request), 'public_root_sha256': object_hash(request),
            'moves': deepcopy(moves), 'options': [baseline, alternative], 'model_proposal': proposal,
            'round': state['round'], 'prior_actors': [p['actor'] for p in prepared['prior']]}


class RootSampler:
    def __init__(self):
        self.roots = {}; self.eligible = []; self.seen = set()

    def add(self, row):
        if row is None: return
        key = (row['phase'], row['decision'])
        assert key not in self.seen; self.seen.add(key)
        summary = {k: deepcopy(row[k]) for k in ('decision', 'phase', 'rank', 'public_root_sha256', 'options', 'round', 'prior_actors')}
        self.eligible.append(summary)
        old = self.roots.get(row['phase'])
        if old is None or (row['rank'], row['decision']) < (old['rank'], old['decision']):
            self.roots[row['phase']] = deepcopy(row)

    def result(self):
        return {'roots': {phase: self.roots[phase] for phase in PHASES if phase in self.roots},
                'missing_phases': [phase for phase in PHASES if phase not in self.roots],
                'eligible': sorted(self.eligible, key=lambda row: row['decision'])}


def one_game(task):
    runtime, model_path, out = (Path(task[k]).resolve() for k in ('runtime', 'model', 'output'))
    p = read(PROTOCOL); q = contract(task['players'], task['deal'], task['seat'], task['rule'], task['mode'])
    assert not os.environ.get('NODE_OPTIONS') and not os.environ.get('PG_TRACE_PATH')
    assert task.get('twin', False) is True or task.get('twin', False) is False
    out.mkdir(parents=True, exist_ok=False); write(out/'contract.json', q)
    model = Model(model_path, threads=p['ort_threads']); assert model.sha256 == p['focal_model_sha256']
    arena = twin = policy = None; start = time.perf_counter(); sampler = RootSampler(); trajectory = hashlib.sha256()
    decisions = 0
    try:
        arena = Node(str(runtime/'ai/strong/public-arena-bridge.cjs'))
        if task.get('twin', False): twin = Node(str(runtime/'ai/strong/public-arena-bridge.cjs'))
        policy = PopulationPolicy(model, runtime/'ai/strong/population-hybrid-policy.cjs', arm='filter')
        command = {'op': 'reset', 'n': 1, 'offset': q['episode'], 'playerCount': q['players'],
                   'mode': 'search_geo', 'arenaSeed': q['seed'], 'featureRevisions': {'learner': p['feature_revision']}}
        response = arena.call(command)
        if twin: assert twin.call(command) == response
        with (out/'decisions.jsonl').open('x') as log:
            while True:
                trajectory.update(object_hash(response).encode())
                if response['ended']:
                    assert len(response['ended']) == 1 and response['observations'] == [None]
                    terminal = response['ended'][0]; assert not terminal['truncated']
                    assert terminal['episode'] == q['episode'] and terminal['gameSeed'] == q['seed']+'-'+str(q['deal'])
                    assert terminal['roles'] == ['learner' if i == q['seat'] else 'search_geo' for i in range(q['players'])]
                    assert terminal['variant'] == ('recharged' if q['rule'] % 2 else 'original') and terminal['sealed'] is (q['rule'] < 2)
                    assert terminal['searchStats']['search_geo']['truncated'] == 0
                    scores = [tuple(player[k] for k in ('powered', 'money', 'cities')) for player in terminal['final']['players']]
                    top = max(scores); assert terminal['value'] == [1/scores.count(top) if s == top else 0 for s in scores]
                    break
                row = response['observations'][0]; request = row['request']; before = object_hash(response)
                receipt = policy.choose(request)
                assert receipt['modelProposal'] == model.predict(row['state'], row['actions'])[0]
                prepared = policy.node.call({**request, 'op': 'prepare', 'featureRevision': p['feature_revision']})
                sample = candidate(request, prepared, receipt, q, decisions); sampler.add(sample)
                assert object_hash(response) == before, 'Sampling changed the observed game'
                log.write(json.dumps({'decision': decisions, 'response_sha256': before,
                    'index': receipt['index'], 'model_proposal': receipt['modelProposal'],
                    'filter_applied': receipt['filterApplied'], 'eligible_rank': sample['rank'] if sample else None})+'\n')
                command = {'op': 'step', 'actions': [receipt['index']]}; trajectory.update(object_hash(command).encode())
                response = arena.call(command)
                if twin: assert twin.call(command) == response
                decisions += 1; assert decisions <= p['game_max_steps']
        # Root selection is complete before any terminal is passed to reporting.
        selected = sampler.result(); write(out/'roots.json', selected); write(out/'terminal.json', terminal)
        result = {**q, 'complete': True, 'focal_decisions': decisions, 'eligible_decisions': len(selected['eligible']),
                  'selected_roots': len(selected['roots']), 'missing_phases': selected['missing_phases'],
                  'twin_exact': bool(twin), 'trajectory_sha256': trajectory.hexdigest(), 'caps': 0,
                  'teacher_search': terminal['searchStats']['search_geo'], 'seconds': time.perf_counter()-start,
                  'protocol_sha256': digest(PROTOCOL), 'runner_sha256': digest(__file__),
                  'files': {p.name: digest(p) for p in sorted(out.iterdir()) if p.is_file()}}
        write(out/'verified.json', result); return result
    finally:
        for process in (policy, arena, twin):
            if process: process.close()


def verify_game(directory, policy):
    """Recompute root ranks, fixed pairs and frozen focal choices from saved public data."""
    out = Path(directory); result = read(out/'verified.json'); q = read(out/'contract.json')
    assert q == contract(q['players'], q['deal'], q['seat'], q['rule'], q['mode'])
    assert all(result[k] == value for k, value in q.items())
    assert result['complete'] is True and result['caps'] == 0
    assert result['protocol_sha256'] == digest(PROTOCOL) and result['runner_sha256'] == digest(__file__)
    assert set(result['files']) == {'contract.json', 'decisions.jsonl', 'roots.json', 'terminal.json'}
    assert all(digest(out/name) == value for name, value in result['files'].items())
    rows = [json.loads(line) for line in (out/'decisions.jsonl').read_text().splitlines()]
    assert [r['decision'] for r in rows] == list(range(result['focal_decisions']))
    selected = read(out/'roots.json'); eligible = selected['eligible']
    assert len(eligible) == result['eligible_decisions'] and len(selected['roots']) == result['selected_roots']
    assert [r['decision'] for r in eligible] == sorted(set(r['decision'] for r in eligible))
    assert {r['decision']: r['eligible_rank'] for r in rows if r['eligible_rank']} == {r['decision']: r['rank'] for r in eligible}
    by_phase = {phase: [] for phase in PHASES}
    for row in eligible:
        assert row['phase'] in PHASES and row['rank'] == object_hash([q['seed'], q['episode'], row['phase'], row['decision']])
        assert len(row['options']) == len(set(row['options'])) == 2
        by_phase[row['phase']].append(row)
    missing = [phase for phase in PHASES if not by_phase[phase]]
    assert selected['missing_phases'] == result['missing_phases'] == missing
    assert set(selected['roots']) == set(PHASES)-set(missing)
    for phase, root in selected['roots'].items():
        expected = min(by_phase[phase], key=lambda row: (row['rank'], row['decision']))
        assert all(root[k] == value for k, value in expected.items()) and root['identity'] == q
        prepared = policy.node.call({**root['request'], 'op': 'prepare', 'featureRevision': read(PROTOCOL)['feature_revision']})
        receipt = policy.choose(root['request'])
        assert candidate(root['request'], prepared, receipt, q, root['decision']) == root
        logged = rows[root['decision']]
        assert logged['index'] == root['options'][0] and logged['model_proposal'] == root['model_proposal']
    terminal = read(out/'terminal.json')
    assert not terminal['truncated'] and terminal['episode'] == q['episode']
    assert terminal['gameSeed'] == q['seed']+'-'+str(q['deal'])
    assert terminal['roles'] == ['learner' if i == q['seat'] else 'search_geo' for i in range(q['players'])]
    assert terminal['variant'] == ('recharged' if q['rule'] % 2 else 'original') and terminal['sealed'] is (q['rule'] < 2)
    assert terminal['searchStats']['search_geo'] == result['teacher_search'] and result['teacher_search']['truncated'] == 0
    scores = [tuple(player[k] for k in ('powered', 'money', 'cities')) for player in terminal['final']['players']]
    best = max(scores); assert terminal['value'] == [1/scores.count(best) if score == best else 0 for score in scores]
    return {'complete': True, 'selected_roots': len(selected['roots']), 'eligible_decisions': len(eligible),
            'missing_phases': missing, 'files_checked': len(result['files'])}


def run(runtime, model, players, start, end, mode, output, workers=8):
    p = read(PROTOCOL); assert type(start) is type(end) is int and 0 <= start < end <= p['deals_per_count']
    assert type(players) is int and players in p['player_counts']
    assert type(workers) is int and 1 <= workers <= p['workers']
    if mode != 'root': assert (start, end) == (0, 1)
    out = Path(output).resolve(); out.mkdir(parents=True, exist_ok=False)
    tasks = []
    for deal in range(start, end):
        for seat in range(players):
            for rule in range(4):
                q = contract(players, deal, seat, rule, mode)
                tasks.append({'runtime': str(Path(runtime).resolve()), 'model': str(Path(model).resolve()),
                    'players': players, 'deal': deal, 'seat': seat, 'rule': rule, 'mode': mode,
                    'output': str(out/f"game-{q['episode']}"), 'twin': mode != 'root'})
    status = {'stage': 'running', 'pid': os.getpid(), 'started_at': datetime.now(timezone.utc).isoformat(),
              'protocol_sha256': digest(PROTOCOL), 'runner_sha256': digest(__file__), 'tasks': tasks,
              'cases': {}, 'errors': [], 'new_hf_jobs': 0, 'gradients': False,
              'qualification_eligible': False, 'reserved_final_seeds_used': False}
    write(out/'intent.json', status)
    try:
        with ProcessPoolExecutor(max_workers=workers) as pool:
            futures = {pool.submit(one_game, task): task for task in tasks}
            for future in as_completed(futures):
                try:
                    result = future.result(); status['cases'][str(result['episode'])] = result
                except Exception as error:
                    status['errors'].append({'task': futures[future], 'error': type(error).__name__+': '+str(error)})
                write(out/'status.json', status)
                print({'complete_games': len(status['cases']), 'planned_games': len(tasks), 'errors': status['errors']}, flush=True)
        assert not status['errors'] and len(status['cases']) == len(tasks)
        status.update(stage='complete', selected_roots=sum(r['selected_roots'] for r in status['cases'].values()))
    except BaseException as error:
        status.update(stage='failed', error=type(error).__name__+': '+str(error)); raise
    finally:
        status['updated_at'] = datetime.now(timezone.utc).isoformat(); write(out/'status.json', status)
    return status


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__)
    for name in ('runtime', 'model', 'output'): parser.add_argument('--'+name, type=Path, required=True)
    for name in ('players', 'start', 'end'): parser.add_argument('--'+name, type=int, required=True)
    parser.add_argument('--mode', choices=['root', 'runtime', 'preflight'], required=True)
    parser.add_argument('--workers', type=int, default=8)
    args = parser.parse_args(); run(args.runtime, args.model, args.players, args.start, args.end, args.mode, args.output, args.workers)
