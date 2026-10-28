"""Full-game research evaluator for the four pinned resource execution controls."""
import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
import hashlib
import json
import os
from pathlib import Path
import select
import signal
import subprocess
import sys
import time

from resource_turn_full_policy_v1 import DESCRIPTOR, MODES, load_artifact
from resource_turn_public_policy_v1 import digest, encode


def wire(value):
    # Engine legal-menu insertion order must survive the JSON transport.
    return json.dumps(value, separators=(',', ':'), allow_nan=False)


def write(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2, allow_nan=False); stream.write('\n')


class Process:
    def __init__(self, argv, log):
        self.log = Path(log).open('x')
        self.proc = subprocess.Popen(argv, cwd='/tmp', stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=self.log, text=True, bufsize=1,
            start_new_session=True, env={**os.environ, 'PYTHONDONTWRITEBYTECODE':'1'})

    def call(self, value):
        self.proc.stdin.write(wire(value)+'\n'); self.proc.stdin.flush()
        if not select.select([self.proc.stdout], [], [], 600)[0]:
            raise TimeoutError('Public process response timeout; inspect retained stderr')
        line = self.proc.stdout.readline()
        if not line:
            raise RuntimeError('Public process exited; inspect retained stderr')
        response = json.loads(line)
        if isinstance(response, dict) and 'error' in response:
            raise ValueError('Public process rejected request: '+response['error'])
        return response

    def close(self):
        try:
            self.proc.stdin.close()
            code = self.proc.wait(timeout=30)
            if code:
                raise RuntimeError('Public process exited with code '+str(code))
        finally:
            if self.proc.poll() is None:
                os.killpg(self.proc.pid, signal.SIGTERM); self.proc.wait(timeout=30)
            self.proc.stdout.close(); self.log.close()


def description_checked(description, root, spec, mode):
    policy = description['specification']
    assert policy['revision'] == 'resource-turn-full-policy-v1'
    assert policy['mode'] == mode and policy['artifactDescriptorSha256'] == digest(root/DESCRIPTOR)
    assert policy['otherPhases'] == 'frozen-filtered-model' and policy['qualification_eligible'] is False
    resource = policy['resourcePolicy']
    assert resource['mode'] == ('search' if mode in ('search-turn','atomic-search') else 'model')
    assert resource['settings'] == spec['settings']
    assert resource['modelSha256'] == spec['model']['sha256']
    assert resource['runtimeManifestSha256'] == spec['runtime']['sha256']
    for name, sha in resource['adapterHashes'].items():
        assert digest(root/'policy'/name) == sha
    for key, value in [('identity',policy), ('resourceIdentity',resource)]:
        assert description[key] == {
            'policySha256':hashlib.sha256(encode(value).encode()).hexdigest(),
            'modelSha256':spec['model']['sha256'], 'runtimeManifestSha256':spec['runtime']['sha256']}
    assert description['qualification_eligible'] is False


def action_checked(value, request, moves, description, mode):
    assert value['identity'] == description['identity'] and value['qualification_eligible'] is False
    assert all(value[k] == request[k] for k in ('requestId','revision'))
    whole = request['state']['phase'] == 'Resources' and mode in ('model-turn','search-turn')
    assert value['kind'] == ('resource-turn' if whole else 'atomic')
    if whole:
        response = value['resource']
        assert response['identity'] == description['resourceIdentity']
        assert all(response[k] == request[k] for k in ('requestId','revision'))
        actions = response['transaction']['actions']
        assert actions and actions[-1] == {'name':'Pass','data':True}
        assert all(move['name'] == 'BuyResource' for move in actions[:-1])
        plan = value['diagnostics']['searchResult']
        assert (plan is None) == (mode == 'model-turn')
        chosen = [x['move'] for x in value['diagnostics']['baselineDecisions']] if plan is None else plan['actions']
        assert chosen == actions
        return {'publicResourceTurn':response}, actions
    decision = value['decision']
    matches = [i for i, move in enumerate(moves) if move == value['move']]
    assert len(matches) == 1 and type(decision['index']) is int and decision['index'] == matches[0]
    assert decision['move'] == value['move']
    return {'publicMove':value['move']}, [value['move']]


def response_counts(value, actions):
    result = Counter(policy_requests=1, atomic_moves=len(actions), resource_turns=0,
                     root_filter_overrides=0, rollouts=0, rollout_caps=0, neural_decisions=0)
    if value['kind'] == 'resource-turn':
        result['resource_turns'] = 1
        plan = value['diagnostics']['searchResult']
        search = None if plan is None else plan['search']
    else:
        decision = value['decision']
        result['root_filter_overrides'] = int(decision['filterApplied'])
        search = decision['search']
    if search is not None:
        result.update(rollouts=search['evaluations'], rollout_caps=search['truncated'],
                      neural_decisions=search['neuralDecisions'])
    return result


def play(config, episode, reference=None):
    root, spec, _ = load_artifact(config['artifact'])
    out = Path(config['output'])
    assert config['descriptor_sha256'] == digest(root/DESCRIPTOR)
    policy = arena = None
    counts = Counter(policy_requests=0, atomic_moves=0, resource_turns=0,
                     root_filter_overrides=0, rollouts=0, rollout_caps=0, neural_decisions=0)
    receipt = out/f'decisions-{episode}.jsonl'
    began = time.perf_counter(); reference_index = 0
    try:
        policy = Process([sys.executable,'-u','-B',str(root/'policy/resource_turn_full_policy_v1.py'),
            '--artifact',str(root),'--mode',config['mode']],out/f'policy-{episode}.stderr.log')
        description = policy.call({'op':'describe'})
        description_checked(description,root,spec,config['mode'])
        arena = Process(['node',str(root/'policy/resource-turn-arena-bridge-v1.cjs'),
            str(root/spec['runtime']['directory'])],out/f'arena-{episode}.stderr.log')
        state = arena.call({'op':'reset','n':1,'offset':episode,'arenaSeed':config['seed'],
            'playerCount':config['players'],'mode':config['opponent'],
            'featureRevisions':{'learner':'4.3-strategic-correction'},
            'publicMoves':True,'publicResourceTurns':True,'policyIdentity':description['resourceIdentity']})
        with receipt.open('x') as stream:
            while not state['ended']:
                row = state['observations'][0]
                assert row is not None and row['roles'][row['seat']] == 'learner'
                request = row['request']; public = request['state']
                assert request['player'] == row['seat'] and request['requestId'] == f'{episode}:{request["revision"]}'
                assert public['seed'] == 'secret' and public['powerPlantsDeck'] == []
                assert not public.get('hiddenLog') and 'powerPlantDeckAfterStep3' not in public
                if public['options']['fastBid']:
                    assert all(p['bid'] == 0 for p in public['players'])
                response = policy.call({'op':'decide','request':request})
                action, actions = action_checked(response,request,row['moves'],description,config['mode'])
                if reference is not None:
                    gold = reference['decisions'][reference_index:reference_index+len(actions)]
                    assert actions == [r['move'] for r in gold], 'Actual inference differs from recorded original choices'
                    if response['kind'] == 'atomic':
                        assert {k:v for k,v in response['decision'].items() if k!='elapsedMs'} == {
                            k:v for k,v in gold[0].items() if k not in ('elapsedMs','decision','round')}
                    else:
                        assert response['diagnostics']['baselineDecisions'] == [
                            {'index':r['index'],'move':r['move']} for r in gold]
                    reference_index += len(actions)
                counts.update(response_counts(response,actions))
                stream.write(wire({'request':request,'response':response,'arenaMoves':row['moves'],
                    'arenaPlayerOrder':row['playerOrder'],'executedActions':actions})+'\n'); stream.flush()
                state = arena.call({'op':'step','actions':[action]})
        assert len(state['ended']) == 1 and state['observations'] == [None]
        terminal = state['ended'][0]; seat = terminal['roles'].index('learner')
        terminal = {**terminal,'seat':seat,'win':terminal['value'][seat]}
        assert not terminal['truncated'] and counts['rollout_caps'] == 0
        assert all(v['truncated'] == 0 for v in terminal['searchStats'].values())
        assert sum(terminal['policyMoves'].values()) == counts['atomic_moves']
        if reference is not None:
            assert reference_index == len(reference['decisions'])
            assert terminal == reference['terminal'], 'Terminal differs from the recorded original game'
        record = {'episode':episode,'terminal':terminal,'counts':dict(counts),
            'description':description,'seconds':time.perf_counter()-began,
            'decision_receipt_sha256':digest(receipt),'recorded_reference_checked':reference is not None,
            'qualification_eligible':False,'reserved_final_seeds_used':False}
        write(out/f'game-{episode}.json',record)
        return record
    except BaseException as error:
        write(out/f'failure-{episode}.json',{'episode':episode,'error':type(error).__name__+': '+str(error),
            'partial_counts':dict(counts),'receipt_sha256':digest(receipt) if receipt.exists() else None})
        raise
    finally:
        try:
            if policy is not None: policy.close()
        finally:
            if arena is not None: arena.close()


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--artifact',type=Path,required=True)
    parser.add_argument('--mode',choices=MODES,required=True)
    parser.add_argument('--players',type=int,choices=range(2,7),required=True)
    parser.add_argument('--opponent',choices=['economic','economic_capacity_v1','legacy','heuristic','rush','search_geo'],required=True)
    parser.add_argument('--seed',required=True)
    parser.add_argument('--start',type=int,default=0)
    parser.add_argument('--deals',type=int,default=1)
    parser.add_argument('--workers',type=int,default=1)
    parser.add_argument('--output',type=Path,required=True)
    args = parser.parse_args()
    root, _, hashes = load_artifact(args.artifact)
    assert Path(__file__).resolve() == root/'policy/resource_turn_full_arena_v1.py'
    assert digest(__file__) == hashes['policy/resource_turn_full_arena_v1.py']
    assert args.seed.startswith(('resource-turn-','resource-replanning-development-v1-'))
    assert 'reserved' not in args.seed.lower() and 'final' not in args.seed.lower()
    assert args.start >= 0 and args.deals > 0 and 1 <= args.workers <= 64
    args.output.mkdir(exist_ok=False)
    config = {**vars(args),'artifact':str(root),'output':str(args.output.resolve()),
              'descriptor_sha256':digest(root/DESCRIPTOR)}
    episodes = list(range(args.start*4*args.players,(args.start+args.deals)*4*args.players))
    records, errors = [], []
    began = time.perf_counter()
    try:
        with ProcessPoolExecutor(max_workers=min(args.workers,len(episodes))) as pool:
            pending = {pool.submit(play,config,episode):episode for episode in episodes}
            for future in as_completed(pending):
                episode = pending[future]
                try:
                    records.append(future.result())
                    print(json.dumps({'completed_games':len(records),'expected_games':len(episodes)}),flush=True)
                except Exception as error:
                    errors.append({'episode':episode,'error':type(error).__name__+': '+str(error)})
        assert not errors and len(records) == len(episodes)
    finally:
        write(args.output/'evaluation.json',{'config':config,'results':sorted(records,key=lambda r:r['episode']),
            'errors':errors,'expected_games':len(episodes),'completed_games':len(records),
            'all_complete':not errors and len(records)==len(episodes),'seconds':time.perf_counter()-began,
            'qualification_eligible':False,'reserved_final_seeds_used':False})


if __name__ == '__main__':
    main()
