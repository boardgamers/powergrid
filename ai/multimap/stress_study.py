"""Frozen, evaluation-only population stress; atomic paired deal-batch resume.

Each panel is an independent job. Report paired deal-cluster estimates only once
that panel is complete; do not interpret the whole experiment until both finish.
No old serving module is mutated, no training rows or optimization API exists.
"""
import argparse
from collections import defaultdict
import json
import math
from pathlib import Path
import statistics

from data import ROOT, atomic_json, digest
from expert_ppo import config as expert_config
from stress_rollout import PROTOCOL, plans, collect, load_models, validate_outcome

HERE = Path(__file__).resolve().parent
ARTIFACT = ROOT / 'ai/runs/multimap-reference-preflight-v1/artifact'
REFERENCE_PYTHON = ROOT / 'ai/.venv-reference/bin/python'
SMOKE_CELLS = (
    'Germany|2|original|0', 'Germany|3|original|1', 'Germany|4|recharged|0',
    'Germany|5|recharged|1', 'Germany|6|original|0', 'USA|3|recharged|0',
    'France|3|recharged|1', 'UK & Ireland|4|original|1',
)
SOURCE_NAMES = ('stress-protocol-v1.json', 'stress_game.cjs', 'stress_rollout.py',
                'stress_study.py', 'job_stress.py', 'launch_stress.py', 'preflight_stress.py', 'launch.py',
                'test_stress.cjs', 'test_stress_rollout.py', 'test_stress_study.py')


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def read(path):
    def pairs(items):
        out = {}
        for k, v in items:
            if k in out:
                raise ValueError('Duplicate JSON key')
            out[k] = v
        return out
    def invalid(_):
        raise ValueError('Nonfinite JSON')
    return json.loads(Path(path).read_text(), object_pairs_hook=pairs, parse_constant=invalid)


def task_hash(tasks):
    import hashlib
    return hashlib.sha256(canonical(tasks).encode()).hexdigest()


def plan(panel, smoke=False):
    if panel not in ('strong', 'mixed') or type(smoke) is not bool:
        raise ValueError('Frozen panel and boolean smoke required')
    tasks = [s for s in plans(smoke=smoke) if s['panel'] == panel and
             (not smoke or s['cell'] in SMOKE_CELLS)]
    if len(tasks) != (60 if smoke else 2560):
        raise ValueError('Frozen panel task coverage changed')
    return tasks


def batches(tasks):
    groups = {}
    for s in tasks:
        groups.setdefault(s['seed'], []).append(s)
    return list(groups.values())


def identity(panel, smoke, workers, artifact, reference_python):
    if type(workers) is not int or not 1 <= workers <= 6:
        raise ValueError('Workers must be 1..6')
    frozen = expert_config(False, workers=6, artifact=artifact, reference_python=reference_python)
    return dict(schema='multimap-stress-identity-v1', protocol=PROTOCOL, panel=panel,
                smoke=smoke, tasks=plan(panel, smoke), expertIdentity=frozen,
                sourceFiles={name: digest(HERE / name) for name in SOURCE_NAMES},
                workers=workers, threads=1, collector='lockstep-central-torch-child-processes',
                fitting=False, selection=False, qualificationEligible=False, reservedFinalSeedsUsed=False)


def artifact_budget(path, additional=0):
    path = Path(path)
    if path.is_symlink() or type(additional) is not int or additional < 0:
        raise ValueError('Unsafe artifact budget/path')
    total = additional
    for p in path.rglob('*'):
        if p.is_symlink():
            raise ValueError('Study artifact symlink forbidden')
        if p.is_file():
            total += p.stat().st_size
    if total > PROTOCOL['studyArtifactMaxBytes']:
        raise ValueError('Study artifact budget exceeded 64 MiB')
    return total


def verify_batch(record, index, tasks):
    if (not isinstance(record, dict) or set(record) != {'schema', 'index', 'taskSha256', 'games'} or
        record['schema'] != 'multimap-stress-batch-v1' or type(record['index']) is not int or
        record['index'] != index or record['taskSha256'] != task_hash(tasks) or
        not isinstance(record['games'], list) or len(record['games']) != len(tasks)):
        raise ValueError('Invalid immutable paired deal-batch')
    for game, task in zip(record['games'], tasks):
        validate_outcome(game, task)
    return record['games']


def estimate(strata):
    if not strata or any(not v or any(not math.isfinite(x) or not -1 <= x <= 1 for x in v)
                        for v in strata.values()):
        raise ValueError('Invalid clustered observations')
    mean = statistics.mean(statistics.mean(v) for v in strata.values())
    enough = all(len(v) >= 2 for v in strata.values())
    se = math.sqrt(math.fsum(statistics.variance(v) / len(v) for v in strata.values())) / len(strata) if enough else None
    return dict(mean=mean, standardError=se, cells=len(strata), independentDeals=sum(map(len, strata.values())),
                approximateNormal95=[mean-1.96*se, mean+1.96*se] if enough else None,
                twoPrimaryBonferroniNormal975=[mean-2.241402727604947*se, mean+2.241402727604947*se] if enough else None)


def analyze(games, panel, smoke=False):
    tasks = plan(panel, smoke)
    if len(games) != len(tasks):
        raise ValueError('No partial-data inference')
    for g, s in zip(games, tasks):
        validate_outcome(g, s)
    paired = defaultdict(dict)
    for r in games:
        s = r['spec']; k = (s['cell'], s['deal'], s['focalSeat'])
        if s['policy'] in paired[k]:
            raise ValueError('Duplicate paired policy')
        paired[k][s['policy']] = r
    by_cell = defaultdict(lambda: defaultdict(list))
    occupancy = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    symmetry = defaultdict(list)
    for (cell, deal, seat), arms in paired.items():
        if set(arms) != {'expert24', 'ppo2'}:
            raise ValueError('Unpaired focal policies')
        a, b = arms['expert24'], arms['ppo2']
        sa, sb = a['spec'], b['spec']
        if any(sa[k] != sb[k] for k in set(sa) - {'policy', 'controllers'}):
            raise ValueError('Paired task mismatch')
        if any(x != y for i, (x, y) in enumerate(zip(sa['controllers'], sb['controllers'])) if i != seat):
            raise ValueError('Paired nonfocal opponents differ')
        by_cell[cell][deal].append((a['credit'], b['credit']))
        strong = sum(c in ('expert24', 'reference') for i, c in enumerate(sa['controllers']) if i != seat)
        occupancy[strong][cell][deal].append((a['credit'], b['credit']))
        if panel == 'strong' and sa['map'] != 'Germany':
            symmetry[cell, deal].append(a)
    expected_deals = 1 if smoke else 4
    for cell, deals in by_cell.items():
        if set(deals) != set(range(expected_deals)) or any(len(v) != int(cell.split('|')[1]) for v in deals.values()):
            raise ValueError('Incomplete all-seat independent-deal cluster')
    # Homogeneous frozen-policy seat rotations must be identical games, not
    # additional independent strength evidence. Focal identity changes no routing.
    for records in symmetry.values():
        for r in records:
            for k in ('allSeatCredit', 'steps', 'rounds', 'counts', 'seatCounts', 'publicChecks', 'policyRequests', 'referenceRequests'):
                if r[k] != records[0][k]:
                    raise ValueError('Homogeneous all-expert symmetry replay mismatch')
        if not math.isclose(sum(r['credit'] for r in records), 1, abs_tol=1e-12):
            raise ValueError('Homogeneous all-seat credit symmetry mismatch')
    cells = list(by_cell)
    subsets = {'allMaps': cells}
    subsets.update({'map:'+m: [c for c in cells if c.split('|')[0] == m] for m in PROTOCOL['maps']})
    subsets.update({'players:'+str(n): [c for c in cells if int(c.split('|')[1]) == n] for n in range(2,7)})
    subsets.update({'rule:'+v+'|'+str(f): [c for c in cells if c.split('|')[2:] == [v, str(f)]]
                    for v in ('original','recharged') for f in (0,1)})
    subsets.update({'mapPlayers:'+m+'|'+str(n): [c for c in cells if c.split('|')[:2] == [m,str(n)]]
                    for m in PROTOCOL['maps'] for n in range(2,7)})
    def scores(table):
        return {label: estimate({c: [statistics.mean((a-b if column == 2 else (a,b)[column]) for a,b in v)
                                     for v in deals.values()] for c,deals in table.items()})
                for label,column in (('expert24',0),('ppo2',1),('pairedDifference',2))}
    results = {name:scores({c:by_cell[c] for c in cs}) for name,cs in subsets.items() if cs}
    Germany = None
    if panel == 'strong':
        Germany = dict(benchmark=.29, newlyPlayedReferenceControlGames=0,
            selectedMinusNeutral=estimate({c:[statistics.mean(a for a,b in v)-1/int(c.split('|')[1])
                for v in ds.values()] for c,ds in by_cell.items() if c.startswith('Germany|')}),
            note='Analytical all-reference 1/n neutrality, not an additional played control; smoke grid is not balanced.')
    reciprocal = []
    for cell in cells:
        if int(cell.split('|')[1]) != 2:
            continue
        for deal in range(expected_deals):
            rows = [paired[cell, deal, seat] for seat in (0, 1)]
            opponents = [rows[seat]['expert24']['spec']['controllers'][1-seat] for seat in (0,1)]
            if opponents[0] != opponents[1]:
                raise ValueError('Reciprocal two-player matchup changed opponent')
            reciprocal.append(dict(cell=cell, deal=deal, opponent=opponents[0],
                expert24ByFocalSeat=[r['expert24']['credit'] for r in rows],
                ppo2ByFocalSeat=[r['ppo2']['credit'] for r in rows],
                allSeatCredits={p:[r[p]['allSeatCredit'] for r in rows] for p in ('expert24','ppo2')}))
    primary = results['allMaps']['pairedDifference']
    interval = primary['twoPrimaryBonferroniNormal975']
    eligible = (not smoke and interval is not None and interval[0] > 0 and
                min(results['map:'+m]['pairedDifference']['mean'] for m in PROTOCOL['maps']) >= -.05)
    return dict(schema='multimap-stress-summary-v1', panel=panel, smoke=smoke, games=len(games), failures=0,
                primary=primary, subgroups=results, strongOpponentOccupancy={str(k):scores(v) for k,v in occupancy.items()},
                reciprocalTwoPlayerGames=sum(r['spec']['players']==2 for r in games),
                reciprocalTwoPlayerOutcomes=reciprocal,
                GermanyAnalyticalReferenceBenchmark=Germany, homogeneousExpertDealControls=len(symmetry),
                cellDealMeans={c:{str(d):dict(expert24=statistics.mean(a for a,b in v),ppo2=statistics.mean(b for a,b in v))
                                 for d,v in ds.items()} for c,ds in by_cell.items()},
                panelResearchProgressionGate=eligible, bothPanelsRequired=True,
                caveats=['Four deals/cell; clustered normal intervals remain approximate and conditional on fixed policies/populations.',
                         'Mixed lineups vary deterministically with deal; ddof=1 variance includes lineup mean variation and is conservative in expectation for the fixed-schedule mean, not an unbiased estimator of it.',
                         'Only the two panel primary intervals use Bonferroni; all subgroup/occupancy intervals are exploratory and unadjusted.',
                         'Occupancy strata condition on the predeclared schedule; their observed cell mix may differ and is not randomized causal evidence.',
                         'Frozen expert24 self-play is an integrity control, not independent algorithm diversity or strength evidence.',
                         'No qualification, human-strength claim, component attribution, checkpoint selection or fitting.'],
                qualified=False, qualificationEligible=False, reservedFinalSeedsUsed=False)


def run(output, panel, *, artifact=ARTIFACT, reference_python=REFERENCE_PYTHON,
        workers=6, smoke=False, callback=None, stop_after_batches=None):
    if stop_after_batches is not None and (type(stop_after_batches) is not int or stop_after_batches < 0):
        raise ValueError('Invalid engineering interruption boundary')
    output = Path(output); output.mkdir(parents=True, exist_ok=True)
    artifact_budget(output)
    config = identity(panel, smoke, workers, artifact, reference_python)
    p = output/'plan.json'
    if p.exists():
        if canonical(read(p)) != canonical(config):
            raise ValueError('Frozen study identity/source/runtime/task mismatch')
    elif any(path.name != 'plan.json.tmp' or not path.is_file() for path in output.iterdir()):
        raise ValueError('Output without frozen identity')
    else:
        atomic_json(p, config)
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
        result = analyze(games,panel,smoke); atomic_json(summary_path,result)
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
        record=dict(schema='multimap-stress-batch-v1',index=i,taskSha256=task_hash(tasks),games=outcomes)
        verify_batch(record,i,tasks)
        artifact_budget(output,2*len(canonical(record).encode()))
        atomic_json(output/f'batch-{i:03}.json',record)
        games.extend(outcomes)
        if callback and (i+1)%PROTOCOL['uploadEveryBatches']==0:
            callback(f'batches-{i+1}')
        print(json.dumps(dict(stage='stress-batch',panel=panel,batches=i+1,totalBatches=len(groups),games=len(games))),flush=True)
    result=analyze(games,panel,smoke)
    atomic_json(summary_path,result); artifact_budget(output)
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
