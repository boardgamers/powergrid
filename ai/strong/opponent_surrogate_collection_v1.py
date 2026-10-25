"""Fresh whole-deal opponent behaviour collection; no gradients or strength claims."""
import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

from strategic_collection import ROOT, read, write, digest
from hybrid_search import Model, Node
from population_hybrid_policy import PopulationPolicy

STRONG = ROOT / 'ai/strong'
PROTOCOL = STRONG / 'opponent-surrogate-collection-protocol-v1.json'


def split(protocol, deal, mode):
    assert mode in ('collection', 'runtime', 'preflight')
    assert type(deal) is int and deal >= 0
    if mode != 'collection':
        assert deal == 0
        return mode
    matches = [name for name, deals in protocol['splits'].items() if deal in deals]
    assert len(matches) == 1
    return matches[0]


def contract(protocol, players, deal, seat, rule, mode):
    assert type(players) is int and players in protocol['player_counts']
    assert type(seat) is int and 0 <= seat < players
    assert type(rule) is int and rule in range(4)
    stage = split(protocol, deal, mode)
    return {'players':players, 'deal':deal, 'focal_seat':seat, 'rule':rule,
            'episode':4 * (deal * players + seat) + rule,
            'seed':protocol[mode + '_seed_template'].format(players=players),
            'split':stage, 'twin':mode != 'collection' or deal % 4 == 0,
            'training_eligible':stage == 'train', 'qualification_eligible':False}


def one_game(task):
    runtime, model_path, output = (Path(task[key]).resolve() for key in ('runtime','model','output'))
    protocol = read(PROTOCOL)
    q = contract(protocol, task['players'], task['deal'], task['seat'], task['rule'], task['mode'])
    output.mkdir(parents=True, exist_ok=False)
    write(output / 'contract.json', q)
    capture = output / 'opponent-decisions.jsonl'
    assert not os.environ.get('NODE_OPTIONS') and not os.environ.get('PG_TRACE_PATH')
    model = Model(model_path)
    assert model.sha256 == protocol['focal']['model']['files']['inference64.onnx']
    old_env = {key:os.environ.get(key) for key in ('PG_OPPONENT_CAPTURE_RUNTIME','PG_OPPONENT_CAPTURE_OUTPUT')}
    recorded = plain = policy = None
    began = time.perf_counter()
    transcript, decisions = hashlib.sha256(), 0
    try:
        try:
            os.environ['PG_OPPONENT_CAPTURE_RUNTIME'] = str(runtime.resolve())
            os.environ['PG_OPPONENT_CAPTURE_OUTPUT'] = str(capture.resolve())
            recorded = Node(str(STRONG / 'capture-reference-opponent-v1.cjs'))
        finally:
            for key,value in old_env.items():
                if value is None: os.environ.pop(key, None)
                else: os.environ[key] = value
        if q['twin']:
            plain = Node(str(runtime / 'ai/strong/public-arena-bridge.cjs'))
        policy = PopulationPolicy(model, runtime / 'ai/strong/population-hybrid-policy.cjs', arm='filter')
        command = {'op':'reset','n':1,'offset':q['episode'],'playerCount':q['players'],
                   'mode':'search_geo','arenaSeed':q['seed'],
                   'featureRevisions':{'learner':'4.3-strategic-correction'}}
        response = recorded.call(command)
        if plain: assert plain.call(command) == response
        with (output / 'focal-decisions.jsonl').open('x') as log:
            while True:
                transcript.update(json.dumps(response, sort_keys=True).encode())
                if response['ended']:
                    assert response['observations'] == [None] and len(response['ended']) == 1
                    terminal = response['ended'][0]
                    assert terminal['episode'] == q['episode'] and not terminal['truncated']
                    assert terminal['gameSeed'] == q['seed'] + '-' + str(q['deal'])
                    assert terminal['roles'] == ['learner' if i == q['focal_seat'] else 'search_geo' for i in range(q['players'])]
                    assert terminal['searchStats']['search_geo']['truncated'] == 0
                    assert terminal['variant'] == ('recharged' if q['rule'] % 2 else 'original')
                    assert terminal['sealed'] is (q['rule'] < 2)
                    scores = [tuple(p[k] for k in ('powered','money','cities')) for p in terminal['final']['players']]
                    best = max(scores)
                    assert terminal['value'] == [1/scores.count(best) if s == best else 0 for s in scores]
                    break
                row = response['observations'][0]
                assert row['request']['player'] == q['focal_seat']
                choice = policy.choose(row['request'])
                assert choice['modelProposal'] == model.predict(row['state'], row['actions'])[0]
                log.write(json.dumps({'decision':decisions,'index':choice['index'],'move':choice['move'],
                                      'model_proposal':choice['modelProposal'], 'filter_applied':choice['filterApplied']}) + '\n')
                command = {'op':'step','actions':[choice['index']]}
                transcript.update(json.dumps(command, sort_keys=True).encode())
                response = recorded.call(command)
                if plain: assert plain.call(command) == response
                decisions += 1
                assert decisions <= protocol['game_max_steps']
        write(output / 'terminal.json', terminal)
    finally:
        if policy: policy.close()
        if recorded: recorded.close()
        if plain: plain.close()
    with (output / 'verification.log').open('x') as log:
        subprocess.run(['node', str(STRONG / 'verify-opponent-surrogate-collection-v1.cjs'), str(runtime),
                        str(capture), str(output / 'contract.json'), str(output / 'verification.json')],
                       stdout=log, stderr=subprocess.STDOUT, check=True)
    verification = read(output / 'verification.json')
    assert verification == read(output / 'verification.log')
    assert verification['totals'] == terminal['searchStats']['search_geo']
    result = {**q, 'complete':True,'focal_decisions':decisions,'teacher_rows':verification['rows'],
              'teacher_rollouts':verification['totals']['evaluations'],
              'public_replays':len(verification['public_replays']), 'phase_rows':verification['phase_rows'],
              'trajectory_sha256':transcript.hexdigest(),'twin_exact':q['twin'],
              'files':{p.name:digest(p) for p in sorted(output.iterdir()) if p.is_file()},
              'seconds':time.perf_counter()-began, 'caps':0}
    write(output / 'verified.json', result)
    return result


def run(runtime, model, players, start, end, mode, output, workers=8):
    protocol = read(PROTOCOL)
    runtime, model, output = (Path(p).resolve() for p in (runtime,model,output))
    assert type(players) is int and players in protocol['player_counts']
    assert type(start) is type(end) is int and 0 <= start < end <= protocol['deals_per_count']
    assert type(workers) is int and 1 <= workers <= protocol['workers']
    assert mode in ('collection','runtime','preflight')
    if mode != 'collection': assert (start,end) == (0,1)
    tasks = []
    for deal in range(start,end):
        for seat in range(players):
            for rule in range(4):
                q = contract(protocol,players,deal,seat,rule,mode)
                tasks.append({'runtime':str(runtime),'model':str(model),'players':players,'deal':deal,
                              'seat':seat,'rule':rule,'mode':mode,'output':str(output / f"game-{q['episode']}")})
    output.mkdir(parents=True, exist_ok=False)
    state = {'started_at':datetime.now(timezone.utc).isoformat(),'pid':os.getpid(),'stage':'running',
             'protocol_sha256':digest(PROTOCOL),'runner_sha256':digest(__file__),
             'model_sha256':digest(model),'mode':mode,'players':players,'start':start,'end':end,
             'workers':workers,'tasks':tasks,'cases':{},'errors':[],
             'gradients':False,'qualification_eligible':False,'reserved_final_seeds_used':False}
    write(output / 'intent.json', state)
    began = time.perf_counter()
    try:
        with ProcessPoolExecutor(max_workers=workers) as pool:
            futures = {pool.submit(one_game, task):task for task in tasks}
            for future in as_completed(futures):
                task = futures[future]
                try:
                    result = future.result()
                    state['cases'][str(result['episode'])] = result
                except Exception as error:
                    state['errors'].append({'task':task,'error':type(error).__name__+': '+str(error)})
                write(output / 'status.json', state)
                print({'complete_games':len(state['cases']),'planned_games':len(tasks),'errors':state['errors']},flush=True)
        assert not state['errors'] and len(state['cases']) == len(tasks)
        assert all(result['complete'] and result['caps'] == 0 for result in state['cases'].values())
        state.update(stage='complete', teacher_rows=sum(r['teacher_rows'] for r in state['cases'].values()),
                     twin_games=sum(r['twin_exact'] for r in state['cases'].values()),
                     public_replays=sum(r['public_replays'] for r in state['cases'].values()))
    except BaseException as error:
        state.update(stage='failed',error=type(error).__name__+': '+str(error))
        raise
    finally:
        state.update(seconds=time.perf_counter()-began,updated_at=datetime.now(timezone.utc).isoformat())
        write(output / 'status.json', state)
    return state


if __name__ == '__main__':
    p = argparse.ArgumentParser(__doc__)
    p.add_argument('--runtime',type=Path,required=True)
    p.add_argument('--model',type=Path,required=True)
    p.add_argument('--players',type=int,required=True)
    p.add_argument('--start',type=int,required=True)
    p.add_argument('--end',type=int,required=True)
    p.add_argument('--mode',choices=['collection','runtime','preflight'],required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--workers',type=int,default=8)
    a=p.parse_args()
    run(a.runtime,a.model,a.players,a.start,a.end,a.mode,a.output,a.workers)
