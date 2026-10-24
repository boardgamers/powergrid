"""Independent whole-game arena for the isolated population-search arms.

CPU inference only. Keeps every game's decision receipts, caps and failures.
No remote submission, selection or qualification is performed here.
"""
import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
import hashlib
import json
from pathlib import Path
import time

from population_hybrid_policy import PopulationPolicy, ARMS
from hybrid_search import Model, Node, model_revision
from arena_statistics import validate_pairs


def play(config, episode):
    model = Model(config['model'], threads=1)
    assert model.sha256 == config['model_sha256']
    revision = model_revision(model)
    runtime = Path(config['runtime'])
    bridge = Node(str(runtime/'ai/strong/public-arena-bridge.cjs'))
    policy = PopulationPolicy(model, runtime/'ai/strong/population-hybrid-policy.cjs',
        arm=config['arm'], samples=config['samples'], workers=config['search_workers'], max_steps=2400)
    opponent = Model(config['opponent_model'], threads=1) if config.get('opponent_model') else None
    if opponent:
        assert opponent.sha256 == config['opponent_sha256']
    revisions = {'learner':revision}
    if opponent:
        revisions['snapshot0'] = model_revision(opponent)
    receipt = Path(config['output'])/f'decisions-{episode}.jsonl'
    count, overrides, rollouts, caps, neural, search_changes = 0, 0, 0, 0, 0, 0
    begin = time.perf_counter()
    try:
        response = bridge.call({'op':'reset', 'n':1, 'offset':episode,
            'arenaSeed':config['seed'], 'playerCount':config['players'],
            'mode':'snapshot0' if opponent else config['opponent'], 'featureRevisions':revisions})
        assert not response['ended']
        while response['observations'][0] is not None:
            row = response['observations'][0]
            actor = row['roles'][row['seat']]
            if actor == 'learner':
                q = row['request']
                assert q['player'] == row['seat']
                assert q['state']['seed'] == 'secret' and q['state']['powerPlantsDeck'] == []
                assert not q['state'].get('hiddenLog') and 'powerPlantDeckAfterStep3' not in q['state']
                if q['state']['options']['fastBid']:
                    assert all(p['bid'] == 0 for p in q['state']['players'])
                result = policy.choose(q)
                # This catches observation/menu drift between the original arena and public policy adapter.
                assert result['modelProposal'] == model.predict(row['state'],row['actions'])[0]
                choice = result['index']
                assert 0 <= choice < len(row['actions'])
                count += 1
                overrides += int(result['filterApplied'])
                if result['search']:
                    detail = result['search']
                    rollouts += detail['evaluations']
                    caps += detail['truncated']
                    neural += detail['neuralDecisions']
                    search_changes += int(choice != result['modelProposal'] and not result['filterApplied'])
                with receipt.open('a') as stream:
                    stream.write(json.dumps({'decision':count,'round':row['round'],**result},allow_nan=False)+'\n')
            else:
                assert actor == 'snapshot0' and opponent is not None
                choice = opponent.predict(row['state'], row['actions'])[0]
            response = bridge.call({'op':'step','actions':[choice]})
            if response['ended']:
                assert len(response['ended']) == 1 and response['observations'] == [None]
                terminal = response['ended'][0]
                seat = terminal['roles'].index('learner')
                terminal = {**terminal,'seat':seat,'win':terminal['value'][seat]}
                record = {'episode':episode, 'terminal':terminal, 'decisions':count,
                    'root_filter_overrides':overrides,'search_changes':search_changes,
                    'rollouts':rollouts,'rollout_caps':caps,'neural_decisions':neural,
                    'seconds':time.perf_counter()-begin,
                    'decision_receipt_sha256':hashlib.sha256(receipt.read_bytes()).hexdigest()}
                Path(config['output'],f'game-{episode}.json').write_text(json.dumps(record,indent=2)+'\n')
                return record
        raise RuntimeError('Arena stopped without a terminal result')
    finally:
        policy.close()
        bridge.close()


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--model',required=True,type=Path)
    parser.add_argument('--runtime',required=True,type=Path)
    parser.add_argument('--arm',required=True,choices=ARMS)
    parser.add_argument('--players',required=True,type=int,choices=range(2,7))
    parser.add_argument('--opponent',required=True,choices=['legacy','heuristic','economic','rush','search_geo','economic_capacity_v1','a260'])
    parser.add_argument('--opponent-model',type=Path)
    parser.add_argument('--seed',required=True)
    parser.add_argument('--start',type=int,default=0)
    parser.add_argument('--deals',type=int,default=1)
    parser.add_argument('--samples',type=int,default=8)
    parser.add_argument('--search-workers',type=int,default=1)
    parser.add_argument('--workers',type=int,default=8)
    parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args()
    assert 'reserved' not in args.seed and args.start>=0 and args.deals>0 and args.workers>0
    assert (args.opponent=='a260') == bool(args.opponent_model)
    args.output.mkdir(parents=True,exist_ok=False)
    config={**vars(args),'model':str(args.model.resolve()),'runtime':str(args.runtime.resolve()),
        'output':str(args.output.resolve()),'model_sha256':hashlib.sha256(args.model.read_bytes()).hexdigest(),
        'opponent_model':str(args.opponent_model.resolve()) if args.opponent_model else None,
        'opponent_sha256':hashlib.sha256(args.opponent_model.read_bytes()).hexdigest() if args.opponent_model else None}
    episodes=list(range(args.start*4*args.players,(args.start+args.deals)*4*args.players))
    records, errors = [], []
    begin=time.perf_counter()
    try:
        with ProcessPoolExecutor(max_workers=min(args.workers,len(episodes))) as pool:
            tasks={pool.submit(play,config,episode):episode for episode in episodes}
            for future in as_completed(tasks):
                episode=tasks[future]
                try:
                    record=future.result();records.append(record)
                    print(json.dumps({'episode':episode,'completed':len(records),'total':len(episodes),
                        'seconds':round(record['seconds'],2),'caps':record['rollout_caps'],
                        'truncated':record['terminal']['truncated']}),flush=True)
                except Exception as error:
                    errors.append({'episode':episode,'error':type(error).__name__+': '+str(error)})
                    print(json.dumps(errors[-1]),flush=True)
        assert not errors, errors
        assert len(records)==len(episodes)
        validate_pairs([r['terminal'] for r in records],args.players)
        assert not any(r['terminal']['truncated'] or r['rollout_caps'] for r in records)
        assert all(not stats['truncated'] for r in records for stats in r['terminal']['searchStats'].values())
    finally:
        report={'config':config,'results':sorted(records,key=lambda r:r['episode']),'errors':errors,
            'expected_games':len(episodes),'completed_games':len(records),
            'all_complete':len(records)==len(episodes) and not errors,
            'game_caps':sum(r['terminal']['truncated'] for r in records),
            'rollout_caps':sum(r['rollout_caps'] for r in records),'seconds':time.perf_counter()-begin,
            'qualification_eligible':False,'reserved_final_seeds_used':False}
        (args.output/'evaluation.json').write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__':
    main()
