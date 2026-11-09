"""Three-arm replica stress-v1: equal-cell paired analysis and atomic deal resume.

Versioned changes only; no mutation of old guards, no labels/training/selection.
Shared PPO2 outcomes are collected once and paired with each fixed replica.
"""
import argparse
import copy
from collections import defaultdict
import json
import math
from pathlib import Path
import statistics
import types

from data import ROOT, atomic_json, digest
from replica_stress_rollout_v1 import (PROTOCOL, POLICIES, plans, collect, load_models,
    validate_outcome, validate_tasks, model_provenance, _protocol)
import stress_study as _legacy

HERE = Path(__file__).resolve().parent
ARTIFACT = ROOT / 'ai/runs/multimap-reference-preflight-v1/artifact'
REFERENCE_PYTHON = ROOT / 'ai/.venv-reference/bin/python'
SOURCE_NAMES = (
    'replica-stress-protocol-v1.json', 'replica_stress_game_v1.cjs',
    'replica_stress_rollout_v1.py', 'replica_stress_study_v1.py',
    'job_replica_stress_v1.py', 'launch_replica_stress_v1.py',
    'preflight_replica_stress_v1.py', 'test_replica_stress_v1.cjs',
    'test_replica_stress_rollout_v1.py', 'test_replica_stress_study_v1.py',
    'test_job_replica_stress_v1.py', 'test_launch_replica_stress_v1.py',
    'test_preflight_replica_stress_v1.py',
)
SOURCES = SOURCE_NAMES


def _bind(function):
    result = types.FunctionType(function.__code__, globals(), function.__name__,
                                function.__defaults__, function.__closure__)
    result.__kwdefaults__ = function.__kwdefaults__
    return result


# Generic serialization/budget helpers use private globals, never global monkeypatches.
canonical = _bind(_legacy.canonical)
read = _bind(_legacy.read)
task_hash = _bind(_legacy.task_hash)
artifact_budget = _bind(_legacy.artifact_budget)


def _commit_json(path, value):
    """Budget the actual indented atomic-write bytes, not a compact-size guess."""
    encoded = (json.dumps(value, indent=2, allow_nan=False) + '\n').encode()
    artifact_budget(Path(path).parent, len(encoded))
    atomic_json(path, value)
    artifact_budget(Path(path).parent)


def plan(panel, smoke=False):
    if panel not in ('strong', 'mixed') or type(smoke) is not bool:
        raise ValueError('Frozen panel and boolean smoke required')
    tasks = [s for s in plans(smoke=smoke) if s['panel'] == panel]
    if len(tasks) != (99 if smoke else 7680):
        raise ValueError('Frozen three-arm panel coverage changed')
    return tasks


def _whole_batch(tasks):
    validate_tasks(tasks)
    first = tasks[0]
    if (len({t['seed'] for t in tasks}) != 1 or
            [(t['focalSeat'], t['policy']) for t in tasks] !=
            [(seat, policy) for seat in range(first['players']) for policy in POLICIES]):
        raise ValueError('Whole three-arm all-seat deal batch required')


def batches(tasks):
    groups = {}
    for task in tasks:
        groups.setdefault(task['seed'], []).append(task)
    for group in groups.values():
        _whole_batch(group)
    return list(groups.values())


def identity(panel, smoke, workers, artifact, reference_python):
    protocol = _protocol()
    if type(workers) is not int or not 1 <= workers <= 6 or (not smoke and workers != 6):
        raise ValueError('Six production workers required; smoke permits 1..6')
    return dict(schema='multimap-replica-stress-identity-v1', protocol=protocol, panel=panel,
        smoke=smoke, tasks=plan(panel, smoke), modelProvenance=model_provenance(artifact, reference_python),
        sourceFiles={name: digest(HERE / name) for name in SOURCE_NAMES},
        frozenSources=copy.deepcopy(protocol['frozenSources']),
        workers=workers, threads=1, collector='lockstep-central-torch-child-processes',
        fitting=False, selection=False, qualificationEligible=False, reservedFinalSeedsUsed=False)


def verify_batch(record, index, tasks):
    _whole_batch(tasks)
    if (not isinstance(record, dict) or set(record) != {'schema', 'index', 'taskSha256', 'games'} or
            record['schema'] != 'multimap-replica-stress-batch-v1' or type(record['index']) is not int or
            record['index'] != index or record['taskSha256'] != task_hash(tasks) or
            not isinstance(record['games'], list) or len(record['games']) != len(tasks)):
        raise ValueError('Invalid immutable whole-three-arm deal batch')
    for game, task in zip(record['games'], tasks):
        validate_outcome(game, task)
    return record['games']


def estimate(strata, *, smoke=False):
    if (type(smoke) is not bool or not isinstance(strata, dict) or not strata or
            any(not values or any(type(x) not in (int, float) or not math.isfinite(x) or not -1 <= x <= 1
                                  for x in values) for values in strata.values())):
        raise ValueError('Invalid clustered observations')
    if not smoke and any(len(v) < 2 for v in strata.values()):
        raise ValueError('N=1 uncertainty is forbidden outside descriptive smoke')
    mean = statistics.mean(statistics.mean(v) for v in strata.values())
    se = None if smoke else math.sqrt(math.fsum(statistics.variance(v) / len(v)
                                               for v in strata.values())) / len(strata)
    return dict(mean=mean, standardError=se, cells=len(strata), independentDeals=sum(map(len, strata.values())),
        approximateNormal95=None if smoke else [mean - 1.96*se, mean + 1.96*se],
        fourPrimaryBonferroniNormal9875=None if smoke else
            [mean - 2.4977054744123737*se, mean + 2.4977054744123737*se],
        descriptiveOnly=smoke)


def analyze(games, panel, smoke=False):
    tasks = plan(panel, smoke)
    if not isinstance(games, list) or len(games) != len(tasks):
        raise ValueError('No partial-data inference or duplicated shared control')
    for game, spec in zip(games, tasks):
        validate_outcome(game, spec)
    paired = defaultdict(dict)
    for game in games:
        spec = game['spec']; key = (spec['cell'], spec['deal'], spec['focalSeat'])
        if spec['policy'] in paired[key]:
            raise ValueError('Duplicate paired policy/shared control')
        paired[key][spec['policy']] = game
    by_cell = defaultdict(lambda: defaultdict(list))
    occupancy = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    for (cell, deal, seat), arms in paired.items():
        if set(arms) != set(POLICIES):
            raise ValueError('Missing arm/shared PPO2 control')
        anchor = arms['ppo2']['spec']
        for game in arms.values():
            spec = game['spec']
            if (any(canonical(spec[k]) != canonical(anchor[k]) for k in set(spec) - {'policy', 'controllers'}) or
                    any(a != b for i, (a, b) in enumerate(zip(spec['controllers'], anchor['controllers'])) if i != seat)):
                raise ValueError('Three-arm paired scope/opponent mismatch')
        values = {p: arms[p]['credit'] for p in POLICIES}
        by_cell[cell][deal].append(values)
        strong = sum(c in ('expert24', 'reference') for i, c in enumerate(anchor['controllers']) if i != seat)
        occupancy[strong][cell][deal].append(values)
    expected_deals = 1 if smoke else 8
    for cell, deals in by_cell.items():
        if set(deals) != set(range(expected_deals)) or any(len(v) != int(cell.split('|')[1]) for v in deals.values()):
            raise ValueError('Incomplete all-seat independent-deal cluster')
    # No homogeneous expert24 symmetry/neutrality assertion: both focals are distinct replicas.
    cells = list(by_cell)
    subsets = {'allMaps': cells}
    subsets.update({'map:'+m: [c for c in cells if c.split('|')[0] == m] for m in PROTOCOL['maps']})
    subsets.update({'players:'+str(n): [c for c in cells if int(c.split('|')[1]) == n] for n in range(2, 7)})
    subsets.update({'rule:'+v+'|'+str(f): [c for c in cells if c.split('|')[2:] == [v, str(f)]]
                    for v in ('original', 'recharged') for f in (0, 1)})
    subsets.update({'mapPlayers:'+m+'|'+str(n): [c for c in cells if c.split('|')[:2] == [m, str(n)]]
                    for m in PROTOCOL['maps'] for n in range(2, 7)})
    subsets.update({'cell:'+c: [c] for c in cells})

    def exploratory(strata):
        value = estimate(strata, smoke=smoke)
        value.pop('fourPrimaryBonferroniNormal9875')
        return value

    def scores(table, *, scheduled_occupancy=False):
        answer = {}
        for label in (*POLICIES, 'replica1MinusPpo2', 'replica2MinusPpo2'):
            strata = {}
            for cell, deals in table.items():
                means = {d: statistics.mean(v[label] if label in POLICIES else
                         v[label.split('Minus')[0]] - v['ppo2'] for v in values)
                         for d, values in deals.items()}
                # Fixed schedule estimator: K selected roots among all D roots.
                # The zero contributions are analytic nonmembership, NOT games
                # or fabricated credit. Normalize by D here to retain estimate's
                # bounded-input guard, then rescale the complete estimate by D.
                strata[cell] = ([means.get(d, 0.) / len(means) for d in range(expected_deals)]
                                if scheduled_occupancy else [v for _, v in sorted(means.items())])
            value = exploratory(strata)
            if scheduled_occupancy:
                value['mean'] *= expected_deals
                if value['standardError'] is not None:
                    value['standardError'] *= expected_deals
                    value['approximateNormal95'] = [x * expected_deals for x in value['approximateNormal95']]
                value['selectedDeals'] = sum(len(ds) for ds in table.values())
                value['selectedDealsByCell'] = {c: len(ds) for c, ds in table.items()}
                value['scheduleVariance'] = 'all-roots-zero-nonmembership-fixed-D-over-K-weights'
            answer[label] = value
        return answer

    results = {name: scores({c: by_cell[c] for c in cs}) for name, cs in subsets.items() if cs}
    # Only these two macro contrasts per panel belong to the four-primary family.
    # Do not attach multiplicity-shaped fields to raw means, subgroups or context.
    primary = {}
    for policy in ('replica1', 'replica2'):
        value = dict(results['allMaps'][policy+'MinusPpo2'])
        mean, se = value['mean'], value['standardError']
        value['fourPrimaryBonferroniNormal9875'] = (None if smoke else
            [mean - 2.4977054744123737*se, mean + 2.4977054744123737*se])
        primary[policy] = value
    germany = None
    if panel == 'strong':
        germany = dict(benchmark=.29, newlyPlayedReferenceControlGames=0,
            replicaMinusNeutral={p: exploratory({c: [statistics.mean(v[p] for v in values) - 1/int(c.split('|')[1])
                for values in deals.values()] for c, deals in by_cell.items() if c.startswith('Germany|')})
                for p in ('replica1', 'replica2')},
            note='Analytical all-reference 1/n context, not played control or qualification. Smoke is not a balanced grid.')
    reciprocal = []
    for cell in cells:
        if int(cell.split('|')[1]) != 2:
            continue
        for deal in range(expected_deals):
            rows = [paired[cell, deal, seat] for seat in (0, 1)]
            opponents = [rows[seat]['ppo2']['spec']['controllers'][1-seat] for seat in (0, 1)]
            if opponents[0] != opponents[1]:
                raise ValueError('Reciprocal two-player opponent mismatch')
            reciprocal.append(dict(cell=cell, deal=deal, opponent=opponents[0],
                focalCredits={p: [r[p]['credit'] for r in rows] for p in POLICIES},
                allSeatCredits={p: [r[p]['allSeatCredit'] for r in rows] for p in POLICIES}))
    return dict(schema='multimap-replica-stress-summary-v1', panel=panel, smoke=smoke,
        descriptiveOnly=smoke, games=len(games), failures=0, primary=primary,
        sharedPpo2Games=sum(g['spec']['policy'] == 'ppo2' for g in games),
        subgroups=results, strongOpponentOccupancy={str(k): scores(v, scheduled_occupancy=True) for k, v in occupancy.items()},
        reciprocalTwoPlayerGames=sum(g['spec']['players'] == 2 for g in games),
        reciprocalTwoPlayerOutcomes=reciprocal, GermanyAnalyticalReferenceBenchmark=germany,
        cellDealMeans={c: {str(d): {p: statistics.mean(v[p] for v in values) for p in POLICIES}
                            for d, values in deals.items()} for c, deals in by_cell.items()},
        watchpoints={key: results[key] for key in PROTOCOL['watchpoints'] if key in results},
        bothPanelsRequired=True, automaticProgression=False, winnerSelection=False,
        caveats=[
            'Eight independent roots/cell, fixed policies/populations; normal coverage remains approximate.',
            'Mixed deterministic lineups use actual deal 0..7, not modulo four; this extends the old schedule, not its identical four-lineup distribution.',
            'Mixed ddof=1 includes lineup-mean variation and is conservative in expectation for the fixed-schedule mean, not unbiased.',
            'Four primary replica-by-panel comparisons share one played PPO2 control per seat/deal; Bonferroni does not assume comparison independence.',
            'Only the four macro primary contrasts have Bonferroni 98.75% intervals; raw means, subgroups, occupancy and neutral context have exploratory unadjusted 95% intervals only. Occupancy conditions on the schedule and is not randomized causal evidence.',
            'Occupancy preserves equal-cell selected-deal point means; all eight scheduled roots enter variance with fixed 8/K weights and zero analytic nonmembership contributions. Sparse occupancy coverage can be especially poor; selected-deal counts are exposed.',
            'No pooled population or training-variance inference, homogeneous-expert neutral control, winner selection, automatic progression, qualification or deployment.',
            'Smoke is descriptive engineering evidence only; production requires every frozen task before inference.'
        ], fitting=False, selection=False, qualified=False, qualificationEligible=False, reservedFinalSeedsUsed=False)


def run(output, panel, *, artifact=ARTIFACT, reference_python=REFERENCE_PYTHON,
        workers=6, smoke=False, callback=None, stop_after_batches=None):
    if stop_after_batches is not None and (type(stop_after_batches) is not int or stop_after_batches < 0):
        raise ValueError('Invalid engineering interruption boundary')
    from huggingface_hub.constants import HF_HUB_CACHE
    output = Path(output)
    resolved = output.resolve()
    for retained in (Path(artifact).resolve(), Path(reference_python).resolve().parent.parent,
                     Path(HF_HUB_CACHE).resolve()):
        if resolved == retained or resolved.is_relative_to(retained) or retained.is_relative_to(resolved):
            raise ValueError('Study output and retained reference/model caches must be nonnested')
    output.mkdir(parents=True, exist_ok=True)
    artifact_budget(output)
    config = identity(panel, smoke, workers, artifact, reference_python)
    p = output/'plan.json'
    if p.exists():
        if canonical(read(p)) != canonical(config):
            raise ValueError('Frozen study identity/source/runtime/task mismatch')
    elif any(path.name != 'plan.json.tmp' or not path.is_file() for path in output.iterdir()):
        raise ValueError('Output without frozen identity')
    else:
        _commit_json(p, config)
    groups = batches(config['tasks']); games = []
    allowed = {'plan.json', 'summary.json'} | {f'batch-{i:03}.json' for i in range(len(groups))}
    for path in output.iterdir():
        if not path.is_file() or (path.name not in allowed and
                                  not (path.name.endswith('.tmp') and path.name[:-4] in allowed)):
            raise ValueError('Unexpected study output')
        # A known .tmp file is an interrupted, uncommitted atomic write. Never
        # consume it; the same canonical batch/summary write will replace it.
    loaded = 0
    for i,tasks in enumerate(groups):
        f = output/f'batch-{i:03}.json'
        if not f.exists():
            if any((output/f'batch-{j:03}.json').exists() for j in range(i+1,len(groups))):
                raise ValueError('Noncontiguous committed batches')
            break
        games.extend(verify_batch(read(f), i, tasks)); loaded += 1
    summary_path = output/'summary.json'
    if summary_path.exists():
        if loaded != len(groups):
            raise ValueError('Summary exists for incomplete study')
        result = analyze(games,panel,smoke)
        if canonical(read(summary_path)) != canonical(result):
            raise ValueError('Committed summary mismatch')
        return result
    if loaded == len(groups):
        result = analyze(games,panel,smoke); _commit_json(summary_path,result)
        if callback: callback('complete')
        return result
    if stop_after_batches is not None and loaded >= stop_after_batches:
        return None
    models = load_models(artifact=artifact, reference_python=reference_python)
    for i in range(loaded,len(groups)):
        if stop_after_batches is not None and i >= stop_after_batches:
            if callback: callback('engineering-interruption')
            return None
        tasks=groups[i]
        outcomes=collect(tasks,workers,artifact=artifact,reference_python=reference_python,models=models)
        record=dict(schema='multimap-replica-stress-batch-v1',index=i,taskSha256=task_hash(tasks),games=outcomes)
        verify_batch(record,i,tasks)
        _commit_json(output/f'batch-{i:03}.json',record)
        games.extend(outcomes)
        if callback and (i+1)%PROTOCOL['uploadEveryBatches']==0:
            callback(f'batches-{i+1}')
        print(json.dumps(dict(stage='replica-stress-batch',panel=panel,batches=i+1,totalBatches=len(groups),games=len(games))),flush=True)
    result=analyze(games,panel,smoke)
    _commit_json(summary_path,result); artifact_budget(output)
    if callback: callback('complete')
    return result


if __name__ == '__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--output',required=True);p.add_argument('--panel',choices=['strong','mixed'],required=True)
    p.add_argument('--smoke',action='store_true');p.add_argument('--workers',type=int,default=6)
    p.add_argument('--artifact',default=ARTIFACT);p.add_argument('--reference-python',default=REFERENCE_PYTHON)
    p.add_argument('--stop-after-batches',type=int)
    a=p.parse_args()
    run(a.output,a.panel,artifact=a.artifact,reference_python=a.reference_python,workers=a.workers,
        smoke=a.smoke,stop_after_batches=a.stop_after_batches)
