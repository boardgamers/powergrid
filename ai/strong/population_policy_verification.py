"""Independent checks of population-policy decision receipts and game reports.

Does not run inference, generate games, submit jobs, or select a policy.
"""
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import re
import tarfile

import numpy as np
from arena_statistics import validate_pairs

ROLES = {'neural', 'economic', 'legacy', 'rush'}
MOVES = {'ChoosePowerPlant','Bid','DiscardPowerPlant','DiscardResources','BuyResource',
         'Build','UsePowerPlant','ChooseRegion','ChooseColor','Pass'}


def read(path):
    return json.loads(Path(path).read_text())


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def integer(value, minimum=0):
    assert type(value) is int and value >= minimum


def finite(value, minimum=0):
    assert type(value) in (int,float) and math.isfinite(value) and value >= minimum


def extract_verified(archive, output):
    """Check every archive member before extracting a fresh directory."""
    output = Path(output)
    assert not output.exists()
    with tarfile.open(archive) as bundle:
        members = bundle.getmembers()
        names = [m.name for m in members]
        assert len(names) == len(set(names)) and 'manifest.json' in names
        assert all(m.isfile() and not Path(m.name).is_absolute() and '..' not in Path(m.name).parts for m in members)
        manifest = json.load(bundle.extractfile('manifest.json'))
        assert 'manifest.json' not in manifest and set(names) == set(manifest) | {'manifest.json'}
        for name, sha in manifest.items():
            assert re.fullmatch('[a-f0-9]{64}',sha)
            assert hashlib.sha256(bundle.extractfile(name).read()).hexdigest() == sha, name
        output.mkdir(parents=True)
        bundle.extractall(output, filter='data')
    assert all(digest(output/name) == sha for name,sha in manifest.items())
    return {'files':len(names),'archive_sha256':digest(archive),'manifest_sha256':digest(output/'manifest.json')}


def verify_decision(row, config, seat, *, horizon=2400, allow_caps=False):
    n, arm, samples = config['players'], config['arm'], config['samples']
    assert n in range(2,7) and 0 <= seat < n
    assert arm in ['model','filter','auction','building','combined']
    assert row['arm'] == arm and row['modelSha256'] == config['model_sha256']
    assert row['featureRevision'] == '4.3-strategic-correction'
    assert row['qualification_eligible'] is False
    integer(row['index']);integer(row['modelProposal']);finite(row['elapsedMs'])
    assert row['phase'] in [None,'auction','building'] and type(row['filterApplied']) is bool
    move = row['move'];assert isinstance(move,dict) and move['name'] in MOVES and 'data' in move
    if move['name'] in ['ChoosePowerPlant','Bid']:assert row['phase'] == 'auction'
    if move['name'] == 'Build':assert row['phase'] == 'building'
    proof = row['filterCertificate']
    if proof is not None:
        assert arm != 'model' and row['phase'] == 'building'
        assert proof['reason'] == 'strict-fueled-output-loss' and proof['qualification_eligible'] is False
        for key in ['threshold','fuelUpperBound','opponentLowerBound']:integer(proof[key])
        assert proof['threshold'] > 0 and proof['fuelUpperBound'] < proof['opponentLowerBound']
        assert proof['replacement'] == {'name':'Pass','data':True}
    if row['filterApplied']:
        assert proof is not None and row['index'] != row['modelProposal'] and move == proof['replacement']
    if arm == 'model':assert proof is None and not row['filterApplied']
    counts = {'decisions':1,'root_filter_overrides':int(row['filterApplied']),
        'rollouts':0,'rollout_caps':0,'neural_decisions':0,'search_changes':0,'search_decisions':0}
    search = row['search']
    if search is None:
        assert row['filterApplied'] or row['index'] == row['modelProposal']
        return counts
    assert arm not in ['model','filter'] and row['phase'] is not None
    assert arm == 'combined' or arm == row['phase']
    # In this version every Build at a certified threshold shares the bound;
    # only Pass remains, so a certified root cannot also launch a search.
    assert proof is None and not row['filterApplied']
    assert search['samples'] == samples and samples in range(4,65,4)
    assert search['mode'] == 'neural_population' and search['maxSteps'] == horizon
    assert re.fullmatch('hybrid-public-v1-[a-f0-9]{64}',search['seed'])
    assert search['valueStatus'] == 'simulated-terminal-credits-not-calibrated-win-probabilities'
    options = search['options'];assert 2 <= len(options) <= 7 and len(options) == len(set(options))
    for option in options:integer(option)
    assert row['modelProposal'] in options and row['index'] in options
    assert search['evaluations'] == samples * len(options)
    for key in ['neuralDecisions','continuationFilterOverrides','truncated']:integer(search[key])
    assert search['continuationFilterOverrides'] <= search['neuralDecisions']
    outcomes = search['sampleOutcomes'];assert set(outcomes) == {str(i) for i in options}
    missing = 0
    for values in outcomes.values():
        assert len(values) == samples
        for value in values:
            if value is None:missing += 1
            else:finite(value);assert value <= 1
    assert missing == search['truncated'] and search['usable'] is (missing == 0)
    worlds = search['worlds'];assert set(worlds) == {str(i) for i in range(samples)}
    earlier = None;neural_bids = {}
    for world in worlds.values():
        roles = world['roles'];assert len(roles) == n and set(roles) <= ROLES and roles[seat] == 'neural'
        belief = world['initialBelief'];assert belief['kind'] == 'policy_population_v1'
        committed = belief['committed'];actors = [r['actor'] for r in committed]
        assert len(actors) == len(set(actors)) and seat not in actors
        if earlier is None:earlier = actors
        assert actors == earlier
        if not config.get('sealed',True) or row['phase'] != 'auction':assert not actors
        for bid in committed:
            integer(bid['actor']);assert bid['actor'] < n and bid['role'] == roles[bid['actor']]
            action = bid['action'];assert action['name'] in ['Pass','Bid']
            if action['name'] == 'Pass':assert action['data'] is True
            else:integer(action['data'])
            if bid['role'] == 'neural':
                previous = neural_bids.setdefault(bid['actor'],action)
                assert previous == action
    for player in range(n):
        if player == seat:continue
        assert Counter(world['roles'][player] for world in worlds.values()) == {r:samples//4 for r in ROLES}
        assert all(worlds[str(i)]['roles'][player] == worlds[str(i%4)]['roles'][player] for i in range(samples))
    if missing:
        assert allow_caps, 'Incomplete rollout invalidates this strength/runtime result'
        assert search['fallbackReason'] == 'incomplete-rollouts' and 'meanCredits' not in search
        assert row['index'] == row['modelProposal']
    else:
        assert 'fallbackReason' not in search
        means = {i:float(np.mean(outcomes[str(i)])) for i in options}
        assert set(search['meanCredits']) == set(outcomes)
        assert all(abs(means[i]-search['meanCredits'][str(i)]) < 1e-12 for i in options)
        chosen = max(options,key=lambda i:(means[i],i==row['modelProposal'],-options.index(i)))
        assert row['index'] == chosen, 'Selected action differs from recomputed terminal-credit choice'
    counts.update(rollouts=search['evaluations'],rollout_caps=missing,neural_decisions=search['neuralDecisions'],
        search_changes=int(row['index']!=row['modelProposal']),search_decisions=1)
    return counts


def verify_evaluation(directory, expected):
    directory = Path(directory);report = read(directory/'evaluation.json');config = report['config']
    for key,value in expected.items():assert config[key] == value, key
    n,start,deals = config['players'],config['start'],config['deals']
    assert n in range(2,7);integer(start);integer(deals,1)
    episodes = set(range(start*4*n,(start+deals)*4*n));records = report['results']
    assert report['all_complete'] is True and report['errors'] == []
    assert report['expected_games'] == report['completed_games'] == len(records) == len(episodes)
    assert {r['episode'] for r in records} == episodes
    assert report['game_caps'] == report['rollout_caps'] == 0
    assert report['qualification_eligible'] is report['reserved_final_seeds_used'] is False
    finite(report['seconds']);assert report['seconds'] > 0
    totals = Counter();latencies = [];game_seconds=[];terminals=[]
    for record in records:
        episode = record['episode'];terminal = record['terminal'];seat = episode//4%n
        assert read(directory/f'game-{episode}.json') == record
        assert terminal['episode'] == episode and terminal['env'] == 0 and terminal['seat'] == seat
        assert terminal['playerCount'] == n and terminal['truncated'] is False
        assert terminal['gameSeed'] == config['seed']+'-'+str(episode//(4*n))
        assert terminal['variant'] == ('recharged' if episode%2 else 'original')
        assert terminal['sealed'] is (episode%4<2)
        opponent = 'snapshot0' if config['opponent']=='a260' else config['opponent']
        assert terminal['roles'] == ['learner' if i==seat else opponent for i in range(n)]
        integer(terminal['steps'],1);assert terminal['steps'] <= 1600
        final = terminal['final'];integer(final['round'],1);assert len(final['players'])==n
        scores=[]
        for player in final['players']:
            for name in ['cities','powered','money','capacity']:integer(player[name])
            assert player['powered'] <= min(player['cities'],player['capacity'])
            assert len(player['plants']) <= (4 if n==2 else 3)
            scores.append(tuple(player[k] for k in ['powered','money','cities']))
        top=max(scores);winners=scores.count(top)
        assert all(abs(value-(1/winners if score==top else 0))<1e-12 for value,score in zip(terminal['value'],scores))
        assert set(terminal['searchStats']) <= ({'search_geo'} if config['opponent']=='search_geo' else set())
        for stats in terminal['searchStats'].values():
            for value in stats.values():integer(value)
            assert stats['truncated']==0 and stats['decisions']>0 and stats['evaluations']>0
        if config['opponent']=='search_geo':assert 'search_geo' in terminal['searchStats']
        receipt=directory/f'decisions-{episode}.jsonl';assert digest(receipt)==record['decision_receipt_sha256']
        with receipt.open() as stream:rows=[json.loads(line) for line in stream]
        assert len(rows)==record['decisions']
        counts=Counter();moves=Counter();previous_round=0
        for index,row in enumerate(rows,1):
            assert row['decision']==index;integer(row['round'],1)
            assert previous_round <= row['round'] <= final['round'];previous_round=row['round']
            counts.update(verify_decision(row,{**config,'sealed':terminal['sealed']},seat))
            moves[row['move']['name']]+=1;latencies.append(row['elapsedMs'])
        for key in ['decisions','root_filter_overrides','rollouts','rollout_caps','neural_decisions','search_changes']:
            assert record[key]==counts[key],key
        assert terminal['policyMoves']==dict(moves)
        finite(record['seconds']);assert record['seconds']>0
        assert sum(row['elapsedMs'] for row in rows) <= record['seconds']*1000+1
        totals.update(counts);game_seconds.append(record['seconds']);terminals.append(terminal)
    validate_pairs(terminals,n)
    assert not totals['rollout_caps']
    return {'games':len(records),'independent_deals':deals,'counts':dict(totals),
        'wall_seconds':report['seconds'],'sum_game_seconds':sum(game_seconds),'max_game_seconds':max(game_seconds),
        'decision_p50_ms':float(np.percentile(latencies,50)),'decision_p95_ms':float(np.percentile(latencies,95)),
        'report_sha256':digest(directory/'evaluation.json'),'all_receipts_verified':True,
        'qualification_eligible':False,'reserved_final_seeds_used':False}
