"""Deal-range execution of the unchanged strategic collection protocol."""
import argparse
from collections import Counter
import gzip
import hashlib
import json
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'ai'))
from infer import Model, Node
from pool import EnginePool
from feature_contract import model_revision
from arena_statistics import validate_pairs
from huggingface_hub import HfApi, hf_hub_download

PROTOCOL = ROOT/'ai/strong/strategic-training-collection-protocol-v1.json'
SOURCE = ROOT/'ai/strong/strategic-training-collection-slices-source-v1.json'
def read(p): return json.loads(Path(p).read_text())
def write(p, d): Path(p).write_text(json.dumps(d, indent=2)+'\n')
def digest(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def request_hash(q): return hashlib.sha256(json.dumps(q, sort_keys=True).encode()).hexdigest()
def prefix(n, mode, smoke, start, end): return 'runs/strategic-training-collection-slices-'+('smoke-' if smoke else '')+f'v1-{n}p-{mode}-{start}-{end}'
def phase(moves):
    if len(moves) < 2: return None
    if any(m['name'] == 'Build' for m in moves): return 'building'
    if any(m['name'] in ['ChoosePowerPlant', 'Bid'] for m in moves): return 'auction'
    return None
def seed_for(p, n, mode, smoke):
    return p['smoke_seed_template' if smoke else 'seed_template'].format(players=n, mode=mode)
def get_model(p):
    pin = p['model']; model = Model(hf_hub_download(p['repo'], pin['path'], revision=pin['revision']), threads=p['ort_threads'])
    assert model.sha256 == pin['sha256'] and model_revision(model) == pin['feature_revision']
    assert model.session.get_modelmeta().custom_metadata_map['powergrid.inference_precision'] == 'float64'
    return model
def verify_games(rows, p, n, mode, smoke, start=0, end=None):
    end = (1 if smoke else p['deals_per_shard']) if end is None else end
    assert 0 <= start < end <= (1 if smoke else p['deals_per_shard'])
    games = (end-start)*4*n
    assert len(rows) == games and {r['episode'] for r in rows} == set(range(start*4*n,end*4*n))
    validate_pairs(rows, n)
    assert {r['gameSeed'] for r in rows} == {seed_for(p,n,mode,smoke)+'-'+str(i) for i in range(start,end)}
    for r in rows:
        assert not r['truncated'] and r['seat'] == r['episode']//4 % n
        assert r['variant'] == ('recharged' if r['episode'] % 2 else 'original')
        assert r['sealed'] == (r['episode'] % 4 < 2)
        assert r['roles'] == ['learner' if i == r['seat'] else mode for i in range(n)]
        assert set(r['searchStats']) == ({'search_geo'} if mode == 'search_geo' else set())
        for stats in r['searchStats'].values():
            assert stats['truncated'] == 0 and stats['decisions'] > 0 and stats['evaluations'] > 0


def run(n, mode, out, start, end, smoke=False, upload=False):
    p = read(PROTOCOL); assert n in p['players'] and mode in p['modes']
    assert 0 <= start < end <= (1 if smoke else p['deals_per_shard'])
    assert not os.environ.get('NODE_OPTIONS')
    model = get_model(p); out = Path(out).resolve(); out.mkdir(parents=True, exist_ok=False)
    games = (end-start)*4*n
    status = {'status':'running', 'players':n, 'mode':mode, 'smoke':smoke, 'deal_start':start, 'deal_end':end,
        'protocol_sha256':digest(PROTOCOL), 'model_sha256':model.sha256,
        'source_revision':os.environ.get('SOURCE_REVISION'), 'source_sha256':os.environ.get('SOURCE_SHA256'),
        'trained':False, 'labels_generated':False, 'qualification_eligible':False}
    started = time.monotonic(); control = captured = None
    try:
        control = EnginePool(min(p['workers'],games), script='ai/strong/bridge.cjs')
        os.environ['NODE_OPTIONS'] = '--require '+str(ROOT/'ai/strong/capture-strategic-training.cjs')
        try: captured = EnginePool(min(p['workers'],games), script='ai/strong/bridge.cjs')
        finally: os.environ.pop('NODE_OPTIONS', None)
        reset = {'op':'reset', 'n':games, 'offset':start*4*n, 'playerCount':n, 'mode':mode, 'arenaSeed':seed_for(p,n,mode,smoke),
                 'featureRevisions':{'learner':p['model']['feature_revision'], 'snapshot0':p['model']['feature_revision']}}
        engine_seconds = policy_seconds = 0.; tick = time.perf_counter()
        left, right = control.call(reset), captured.call(reset)
        engine_seconds += time.perf_counter()-tick
        results = []; ordinals = Counter(); counts = Counter(); decisions = steps = index = 0
        trajectory = hashlib.sha256(); last_progress = time.monotonic()
        with gzip.open(out/'roots.jsonl.gz', 'wt') as roots:
            while True:
                assert left['ended'] == right['ended'], 'Capture changed terminal games'
                results.extend(left['ended'])
                assert len(left['observations']) == len(right['observations']) == games
                if not any(r is not None for r in left['observations']):
                    assert left == right; break
                actions = [None]*games
                tick = time.perf_counter()
                for i, plain in enumerate(left['observations']):
                    if plain is not None:
                        assert plain['featureRevision'] == p['model']['feature_revision']
                        actions[i] = model.predict(plain['state'],plain['actions'])[0]; decisions += 1
                policy_seconds += time.perf_counter()-tick
                for i, (plain, instrumented) in enumerate(zip(left['observations'],right['observations'])):
                    if plain is None:
                        assert instrumented is None; continue
                    root = instrumented.pop('strategicRoot', None)
                    assert plain == instrumented, 'Capture changed model input or legal order'
                    trajectory.update(json.dumps([plain,actions[i]],sort_keys=True).encode())
                    if root and plain['roles'][root['request']['player']] == 'learner':
                        episode = plain['episode']; deal = episode//(4*n); ordinal = ordinals[episode]
                        split = 'validation' if deal in p['validation_deal_indices'] else 'train'
                        assert len(root['legal']) == len(plain['actions']) and phase(root['legal']) == root['phase']
                        root.update(rootIndex=index, rootId=f'{n}:{mode}:{episode}:{ordinal}', players=n, mode=mode,
                            episode=episode, ordinal=ordinal, deal=deal, gameSeed=seed_for(p,n,mode,smoke)+'-'+str(deal),
                            split=split, variant=plain['variant'], sealed=plain['sealed'], round=plain['round'],
                            public_root_sha256=request_hash(root['request']), model_proposal=actions[i], model_move=root['legal'][actions[i]])
                        roots.write(json.dumps(root)+'\n'); index += 1; ordinals[episode] += 1
                        counts[root['phase'],split] += 1
                tick = time.perf_counter()
                left, right = control.call({'op':'step','actions':actions}), captured.call({'op':'step','actions':actions})
                engine_seconds += time.perf_counter()-tick; steps += 1
                if time.monotonic()-last_progress >= 45:
                    print({'games_completed':len(results),'games':games,'roots':index,'seconds':time.monotonic()-started},flush=True)
                    last_progress = time.monotonic(); roots.flush()
        rows = [{**r, 'seat':r['roles'].index('learner'), 'win':r['value'][r['roles'].index('learner')]} for r in results]
        verify_games(rows,p,n,mode,smoke,start,end); assert index > 0
        write(out/'games.json',rows)
        status.update(status='complete', games=games, engine_game_runs=2*games, roots=index,
            root_counts={a:{s:counts[a,s] for s in ['train','validation']} for a in ['auction','building']},
            games_with_roots=len(ordinals), all_twin_controls_match=True, trajectory_sha256=trajectory.hexdigest(),
            decisions=decisions, steps=steps, engine_seconds=engine_seconds, policy_seconds=policy_seconds,
            game_truncations=0, search_truncations=0, seconds=time.monotonic()-started)
    except BaseException as error:
        status.update(status='failed',error=type(error).__name__+': '+str(error)); raise
    finally:
        if control: control.close()
        if captured: captured.close()
        status['artifacts']={q.name:digest(q) for q in out.iterdir() if q.is_file()}
        write(out/'collection-check.json',status)
        if upload: HfApi().upload_folder(repo_id=p['repo'],folder_path=out,path_in_repo=prefix(n,mode,smoke,start,end))
        print(status,flush=True)


def verify_local(out, n, mode, start, end, smoke=False):
    out = Path(out); p = read(PROTOCOL); source = read(SOURCE); status = read(out/'collection-check.json')
    games = (end-start)*4*n
    expected = {'status':'complete','players':n,'mode':mode,'smoke':smoke,'deal_start':start,'deal_end':end,'games':games,'engine_game_runs':2*games,
        'protocol_sha256':digest(PROTOCOL),'source_revision':source['revision'],'source_sha256':source['sha256'],
        'model_sha256':p['model']['sha256'],'trained':False,'labels_generated':False,'qualification_eligible':False,
        'game_truncations':0,'search_truncations':0,'all_twin_controls_match':True}
    for key,value in expected.items(): assert status[key] == value, key
    assert set(status['artifacts']) == {'games.json','roots.jsonl.gz'}
    for name,sha in status['artifacts'].items(): assert digest(out/name) == sha
    rows = read(out/'games.json'); verify_games(rows,p,n,mode,smoke,start,end); per_game = {r['episode']:r for r in rows}
    model = get_model(p); worker = Node('strong/worker.cjs'); ordinals = Counter(); counts = Counter(); coverage = Counter(); index = 0
    try:
        with gzip.open(out/'roots.jsonl.gz','rt') as roots:
            for line in roots:
                r = json.loads(line); episode = r['episode']; game = per_game[episode]
                ordinal = ordinals[episode]; deal = episode//(4*n)
                split = 'validation' if deal in p['validation_deal_indices'] else 'train'
                assert r['rootIndex'] == index and r['rootId'] == f'{n}:{mode}:{episode}:{ordinal}'
                assert r['ordinal'] == ordinal and r['deal'] == deal and r['split'] == split
                assert r['players'] == n and r['mode'] == mode
                assert all(r[k] == game[k] for k in ['gameSeed','variant','sealed'])
                state, seat = r['request']['state'],r['request']['player']
                assert seat == game['seat'] and state['round'] == r['round']
                assert len(state['players']) == n and state['options']['showMoney']
                assert state['options']['variant'] == r['variant'] and bool(state['options']['fastBid']) == r['sealed']
                assert not state['powerPlantsDeck'] and not state['hiddenLog'] and state['seed'] == 'secret'
                assert 'powerPlantDeckAfterStep3' not in state and not state.get('automation',{}).get('plans')
                if state['options']['fastBid']:
                    assert state['currentBid'] == 0
                    assert all(not x.get('bid') for j,x in enumerate(state['players']) if j != seat)
                assert request_hash(r['request']) == r['public_root_sha256']
                observation = worker.call({**r['request'],'featureRevision':p['model']['feature_revision']})
                assert observation['moves'] == r['legal'] and phase(r['legal']) == r['phase'] and r['phase']
                assert model.predict(observation['state'],observation['actions'])[0] == r['model_proposal']
                assert r['model_move'] == r['legal'][r['model_proposal']]
                counts[r['phase'],split] += 1; coverage[r['phase'],split,r['variant'],r['sealed'],seat] += 1
                index += 1; ordinals[episode] += 1
    finally: worker.close()
    assert index == status['roots'] > 0 and len(ordinals) == status['games_with_roots']
    assert status['root_counts'] == {a:{s:counts[a,s] for s in ['train','validation']} for a in ['auction','building']}
    return {'deal_start':start,'deal_end':end,'games':games,'roots':index,'public_model_proposals_reproduced':index,'root_counts':status['root_counts'],
        'coverage':{'/'.join(map(str,k)):v for k,v in sorted(coverage.items())},'seconds':status['seconds'],
        'engine_seconds':status['engine_seconds'],'policy_seconds':status['policy_seconds'],
        'game_truncations':0,'search_truncations':0,'qualification_eligible':False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__); parser.add_argument('players',type=int,choices=range(2,7))
    parser.add_argument('mode',choices=['economic','search_geo','snapshot0']); parser.add_argument('output',type=Path)
    parser.add_argument('start',type=int); parser.add_argument('end',type=int); parser.add_argument('--smoke',action='store_true'); parser.add_argument('--upload',action='store_true'); args=parser.parse_args()
    run(args.players,args.mode,args.output,args.start,args.end,args.smoke,args.upload)
