"""Offline, independent post-run audit of the frozen population stress v1.

API: ``audit_panel(restored_root, 'strong'|'mixed')`` requires the *complete*
original-job snapshot (study/, status/protocol/environment/recovery/artifacts.json).
It returns counts, the independently rebuilt full summary, scheduledCoverage,
integrity and gate. ``audit_both(strong_root, mixed_root)`` additionally requires
separate directories and seed roots and returns both reports and the predeclared
combined gate. Invalid/incomplete evidence raises ValueError; a failed research
gate is a valid audit result, never a reason to change the recipe.

No serving/study analysis, planner, model, network, training or replay is used.
Task literals and arithmetic are independent of stress_study/stress_rollout.
Manifest hashes, private immutable download provenance, source/runtime/reference
identity and exact engine replays remain the caller's separate responsibilities.
Their verification must accompany this report before interpreting both panels.
The saved subgroup Bonferroni-shaped fields are checked for schema fidelity, but
ONLY the two panel primaries use adjustment; subgroup inference is unadjusted.

CLI (read-only, JSON on stdout):
  python -B ai/multimap/audit_stress.py STRONG_SNAPSHOT MIXED_SNAPSHOT
"""
import argparse
from collections import Counter, defaultdict
import hashlib
import itertools
import json
import math
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
MAPS = ('Germany', 'USA', 'France', 'UK & Ireland')
PANELS = ('strong', 'mixed')
POLICIES = ('expert24', 'ppo2')
MODELS = ('expert24', 'ppo0', 'ppo1', 'ppo2')
PHASES = ('Auction', 'Resources', 'Building', 'Bureaucracy')
CONTROLLERS = (*MODELS, 'reference', 'teacherV2', 'fixedV2', 'fixedV1')
NAMESPACE = 'pg-multimap-stress-20261103-v1'
Z_PRIMARY = 2.241402727604947
TOLERANCE = 1e-12
LIMIT = 64 * 1024**2
PROTOCOL_SHA256 = '9e2931e24e33fee611c12fed2cf41f60303f170f6a2be112a7fa1a5fb110bcc1'
SOURCE_REVISION = '034ec3e2bda35de8e59e570bcc9cdcc20ef760d7'
SOURCE_SHA256 = '5231bece1d79622072ae907a8470f6e6b248409a0b8ffbc4bc305732d9b4a870'
SOURCE_NAMES = {
    'stress-protocol-v1.json', 'stress_game.cjs', 'stress_rollout.py',
    'stress_study.py', 'job_stress.py', 'launch_stress.py', 'preflight_stress.py',
    'launch.py', 'test_stress.cjs', 'test_stress_rollout.py', 'test_stress_study.py',
}
PLAN_HASHES = {
    'strong': '7aff53cb54ecb8d1ea8a92afa4ace7b1d966fa68016f103681b1490dbd3523d7',
    'mixed': '21bd50d1ef9e717125913b1638d0f72ee5b6973e8d8594eeb1b32101bd67440f',
}
CAVEATS = [
    'Four deals/cell; clustered normal intervals remain approximate and conditional on fixed policies/populations.',
    'Mixed lineups vary deterministically with deal; ddof=1 variance includes lineup mean variation and is conservative in expectation for the fixed-schedule mean, not an unbiased estimator of it.',
    'Only the two panel primary intervals use Bonferroni; all subgroup/occupancy intervals are exploratory and unadjusted.',
    'Occupancy strata condition on the predeclared schedule; their observed cell mix may differ and is not randomized causal evidence.',
    'Frozen expert24 self-play is an integrity control, not independent algorithm diversity or strength evidence.',
    'No qualification, human-strength claim, component attribution, checkpoint selection or fitting.',
]


def require(condition, label):
    if not condition:
        raise ValueError(label)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def task_hash(tasks):
    return hashlib.sha256(canonical(tasks).encode()).hexdigest()


def read(path):
    """Reject duplicate keys and every nonfinite encoding, including 1e999."""
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, 'Duplicate JSON key: ' + key)
            result[key] = value
        return result

    def number(value):
        result = float(value)
        require(math.isfinite(result), 'Nonfinite JSON number')
        return result

    def invalid(value):
        raise ValueError('Nonfinite JSON constant: ' + value)

    return json.loads(Path(path).read_text(), object_pairs_hook=pairs,
                      parse_float=number, parse_constant=invalid)


def equal(actual, expected, label='summary'):
    """Exact key/sequence/type coverage; floating arithmetic tolerance 1e-12.

    Booleans and integer counters are never coerced to each other or floats.
    Only floating-valued estimates accept an integer representation.
    """
    if isinstance(expected, dict):
        require(isinstance(actual, dict) and actual.keys() == expected.keys(), label + ': keys')
        for key in expected:
            equal(actual[key], expected[key], label + '.' + str(key))
    elif isinstance(expected, list):
        require(isinstance(actual, list) and len(actual) == len(expected), label + ': length')
        for i, (left, right) in enumerate(zip(actual, expected)):
            equal(left, right, label + '.' + str(i))
    elif type(expected) is float:
        require(type(actual) in (int, float) and math.isfinite(actual) and
                math.isclose(actual, expected, rel_tol=TOLERANCE, abs_tol=TOLERANCE), label + ': numeric')
    else:
        require(type(actual) is type(expected) and actual == expected, label + ': value/type')


def exact(actual, expected, label):
    require(canonical(actual) == canonical(expected), label)


def expected_tasks(panel):
    """Literal 80-cell x four-deal x all-seat x two-arm production recipe."""
    require(type(panel) is str and panel in PANELS, 'Original production panel required')
    tasks = []
    grid = itertools.product(MAPS, range(2, 7), ('original', 'recharged'), (False, True))
    for ci, (map_name, n, variant, fast) in enumerate(grid):
        cell = f'{map_name}|{n}|{variant}|{int(fast)}'
        weak = ['ppo0', 'ppo1', 'ppo2', 'teacherV2']
        if map_name == 'Germany':
            weak.append('reference')
        for deal in range(4):
            # Construct the opponent ring once, then rotate into actual seats.
            ring = []
            for ordinal in range(n - 1):
                index = ci + deal + ordinal
                if panel == 'strong':
                    opponent = 'reference' if map_name == 'Germany' else 'expert24'
                else:
                    opponent = 'expert24' if index % 2 == 0 else weak[(index // 2) % len(weak)]
                ring.append(opponent)
            for focal in range(n):
                for policy in POLICIES:
                    controllers = [None] * n
                    controllers[focal] = policy
                    for offset, opponent in enumerate(ring, 1):
                        controllers[(focal + offset) % n] = opponent
                    tasks.append(dict(map=map_name, players=n, variant=variant, fastBid=fast,
                        cell=cell, seed=f'{NAMESPACE}:{panel}:{cell}:{deal}', smoke=False,
                        deal=deal, focalSeat=focal, panel=panel, policy=policy,
                        controllers=controllers, maxSteps=4000))
    require(len(tasks) == 2560 and task_hash(tasks) == PLAN_HASHES[panel],
            'Independent task reconstruction differs from prelaunch production pin')
    return tasks


def expected_batches(panel):
    groups = []
    for task in expected_tasks(panel):
        if not groups or groups[-1][0]['seed'] != task['seed']:
            groups.append([])
        groups[-1].append(task)
    require(len(groups) == 320, '320 independent deal batches required')
    return groups


def _counter(value, keys, label):
    require(isinstance(value, dict) and set(value) == set(keys) and
            all(type(v) is int and v >= 0 for v in value.values()), label)


def _finite(value, lower=0, upper=math.inf):
    return type(value) in (int, float) and math.isfinite(value) and lower <= value <= upper


def validate_outcome(game, task):
    """Independent terminal credit, actual-seat routing and counter validation.

    Learned models may delegate forced Auction/Building actions to their fixed
    teacher; only reference/teacherV2 must account for every assigned action.
    """
    fields = {'spec', 'terminal', 'credit', 'allSeatCredit', 'steps', 'rounds',
              'counts', 'seatCounts', 'publicChecks', 'policyRequests',
              'referenceRequests', 'featureMs', 'inferenceMs', 'referenceMs', 'seconds'}
    require(isinstance(game, dict) and set(game) == fields, 'Compact outcome schema')
    exact(game['spec'], task, 'Outcome canonical task/order/scope')
    require(game['terminal'] is True, 'Nonterminal outcome')
    require(all(_finite(game[k]) for k in ('featureMs', 'inferenceMs', 'referenceMs', 'seconds')),
            'Invalid outcome timing')
    credits = game['allSeatCredit']
    require(isinstance(credits, list) and len(credits) == task['players'] and
            all(_finite(v, 0, 1) for v in credits), 'Terminal credit vector')
    winners = sum(v > 0 for v in credits)
    require(winners > 0 and all(v == 0 or v == 1 / winners for v in credits) and
            math.isclose(math.fsum(credits), 1, rel_tol=0, abs_tol=1e-12), 'Equal-share winner credit')
    require(_finite(game['credit'], 0, 1) and game['credit'] == credits[task['focalSeat']],
            'Focal credit disagrees with complete vector')
    require(type(game['steps']) is int and 0 < game['steps'] <= 4000 and
            type(game['rounds']) is int and 0 < game['rounds'] <= game['steps'], 'Steps/rounds/cap')
    counts, seats = game['counts'], game['seatCounts']
    require(isinstance(counts, dict) and set(counts) == set(CONTROLLERS), 'Controller counter schema')
    require(isinstance(seats, list) and len(seats) == task['players'], 'Actual seat counter coverage')
    for counter in [*counts.values(), *seats]:
        _counter(counter, PHASES, 'Phase counters must be nonnegative integers')
    require(sum(sum(c.values()) for c in counts.values()) == game['steps'] ==
            sum(sum(c.values()) for c in seats), 'Controller/seat totals must account for all steps')
    for phase in PHASES:
        require(sum(c[phase] for c in counts.values()) == sum(c[phase] for c in seats),
                'Controller/seat phase totals differ')
        assigned = Counter()
        for controller, counter in zip(task['controllers'], seats):
            assigned[controller] += counter[phase]
        for controller in ('reference', 'teacherV2'):
            require(counts[controller][phase] == assigned[controller], 'Actual seat reference/teacher routing')
        for controller in MODELS:
            require(counts[controller][phase] <= assigned[controller], 'Actual seat learned routing')
            if phase in ('Resources', 'Bureaucracy'):
                require(counts[controller][phase] == 0, 'Learned policy escaped Auction/Building')
        require(counts['fixedV2'][phase] == assigned['expert24'] - counts['expert24'][phase],
                'Actual seat fixedV2 routing')
        require(counts['fixedV1'][phase] == sum(assigned[c] - counts[c][phase] for c in MODELS[1:]),
                'Actual seat fixedV1 routing')
    totals = {c: sum(counts[c].values()) for c in CONTROLLERS}
    require(task['map'] == 'Germany' or totals['reference'] == 0, 'Reference escaped Germany')
    checks = dict(hiddenInvariant=totals['reference'], referenceAtomicLegal=totals['reference'],
                  fullMenuPrior=sum(totals[c] for c in MODELS), expertAtomicLegal=0)
    _counter(game['publicChecks'], checks, 'Public counter schema/types')
    exact(game['publicChecks'], checks, 'Public/full-menu/zero-label counters')
    _counter(game['policyRequests'], MODELS, 'Policy request schema/types')
    exact(game['policyRequests'], {c: totals[c] for c in MODELS}, 'Policy request counter mismatch')
    require(type(game['referenceRequests']) is int and game['referenceRequests'] == totals['reference'],
            'Reference request counter mismatch')
    return credits[task['focalSeat']]


def verify_batch(record, index, tasks):
    require(isinstance(record, dict) and set(record) == {'schema', 'index', 'taskSha256', 'games'} and
            record['schema'] == 'multimap-stress-batch-v1' and type(record['index']) is int and
            record['index'] == index and record['taskSha256'] == task_hash(tasks) and
            isinstance(record['games'], list) and len(record['games']) == len(tasks),
            'Batch schema/index/task hash/size')
    for game, task in zip(record['games'], tasks):
        validate_outcome(game, task)
    return record['games']


def _mean(values):
    values = list(values)
    require(bool(values), 'Empty mean')
    return math.fsum(values) / len(values)


def estimate(strata):
    """Equal fixed-cell mean; own ddof=1 variance of independent deal means.

    Production primaries have four deals/cell. Occupancy subgroups can have only
    one scheduled deal in some cells, in which case no interval is estimable.
    Mixed-lineup variance is conservative in expectation, NOT unbiased.
    """
    require(isinstance(strata, dict) and bool(strata) and
            all(isinstance(v, (list, tuple)) and v and all(_finite(x, -1, 1) for x in v)
                for v in strata.values()), 'Invalid deal-cluster observations')
    means = {c: _mean(v) for c, v in strata.items()}
    mean = _mean(means.values())
    enough = all(len(v) >= 2 for v in strata.values())
    se = None
    if enough:
        variance_terms = []
        for cell, values in strata.items():
            sample_variance = math.fsum((v - means[cell]) ** 2 for v in values) / (len(values) - 1)
            variance_terms.append(sample_variance / len(values))
        se = math.sqrt(math.fsum(variance_terms)) / len(strata)
    return dict(mean=mean, standardError=se, cells=len(strata),
        independentDeals=sum(len(v) for v in strata.values()),
        approximateNormal95=[mean - 1.96 * se, mean + 1.96 * se] if enough else None,
        twoPrimaryBonferroniNormal975=[mean - Z_PRIMARY * se, mean + Z_PRIMARY * se] if enough else None)


def _scores(table):
    # table[cell][deal] contains all paired focal seats, never raw-game weights.
    return {label: estimate({cell: [_mean((a, b, a - b)[column] for a, b in pairs)
                                   for _, pairs in sorted(deals.items())]
                             for cell, deals in table.items()})
            for column, label in enumerate((*POLICIES, 'pairedDifference'))}


def _subsets(cells):
    out = {'allMaps': cells}
    out.update({'map:' + m: [c for c in cells if c.split('|')[0] == m] for m in MAPS})
    out.update({'players:' + str(n): [c for c in cells if c.split('|')[1] == str(n)] for n in range(2, 7)})
    out.update({'rule:' + v + '|' + str(f): [c for c in cells if c.split('|')[2:] == [v, str(f)]]
                for v in ('original', 'recharged') for f in (0, 1)})
    out.update({'mapPlayers:' + m + '|' + str(n): [c for c in cells if c.split('|')[:2] == [m, str(n)]]
                for m in MAPS for n in range(2, 7)})
    return out


def panel_gate(summary):
    """Strict positive adjusted lower bound AND all map means >= -.05."""
    interval = summary['primary']['twoPrimaryBonferroniNormal975']
    minimum = min(summary['subgroups']['map:' + m]['pairedDifference']['mean'] for m in MAPS)
    require(isinstance(interval, list) and len(interval) == 2 and
            all(_finite(x, -math.inf) for x in interval) and _finite(minimum, -1, 1), 'Gate estimates')
    return dict(adjustedLower=interval[0], minimumMapPairedMean=minimum,
                adjustedLowerPositive=interval[0] > 0, mapGuardPassed=minimum >= -.05,
                passed=interval[0] > 0 and minimum >= -.05)


def recompute_summary(games, panel):
    """Rebuild every frozen summary field, rejecting incomplete/reordered data."""
    tasks = expected_tasks(panel)
    require(isinstance(games, list) and len(games) == 2560, 'No partial-data inference')
    for game, task in zip(games, tasks):
        validate_outcome(game, task)
    return _summary_from_verified(games, panel)


def _summary_from_verified(games, panel):
    table = defaultdict(dict)
    occupancy = defaultdict(lambda: defaultdict(dict))
    controls, reciprocal = 0, []
    offset = 0
    for tasks in expected_batches(panel):
        records = games[offset:offset + len(tasks)]
        offset += len(tasks)
        spec = tasks[0]
        cell, deal, n = spec['cell'], spec['deal'], spec['players']
        arms = {p: records[i::2] for i, p in enumerate(POLICIES)}
        pairs, strengths = [], set()
        for seat in range(n):
            left, right = arms['expert24'][seat], arms['ppo2'][seat]
            ls, rs = left['spec'], right['spec']
            exact({k: v for k, v in ls.items() if k not in ('policy', 'controllers')},
                  {k: v for k, v in rs.items() if k not in ('policy', 'controllers')}, 'Paired task identity')
            require(all(a == b for i, (a, b) in enumerate(zip(ls['controllers'], rs['controllers'])) if i != seat),
                    'Paired opponents changed')
            pairs.append((left['allSeatCredit'][seat], right['allSeatCredit'][seat]))
            strengths.add(sum(c in ('expert24', 'reference') for i, c in enumerate(ls['controllers']) if i != seat))
        require(len(strengths) == 1 and len(pairs) == n, 'All-seat scheduled occupancy coverage')
        strength = next(iter(strengths))
        table[cell][deal] = pairs
        occupancy[str(strength)][cell][deal] = pairs
        if panel == 'strong' and spec['map'] != 'Germany':
            fields = ('allSeatCredit', 'steps', 'rounds', 'counts', 'seatCounts',
                      'publicChecks', 'policyRequests', 'referenceRequests')
            first = {k: arms['expert24'][0][k] for k in fields}
            for record in arms['expert24'][1:]:
                exact({k: record[k] for k in fields}, first, 'Homogeneous expert symmetry mismatch')
            require(math.isclose(math.fsum(a for a, _ in pairs), 1, rel_tol=0, abs_tol=1e-12),
                    'Homogeneous all-seat credit symmetry')
            controls += 1
        if n == 2:
            opponents = [arms['expert24'][s]['spec']['controllers'][1 - s] for s in (0, 1)]
            require(opponents[0] == opponents[1], 'Reciprocal opponent mismatch')
            reciprocal.append(dict(cell=cell, deal=deal, opponent=opponents[0],
                expert24ByFocalSeat=[a for a, _ in pairs], ppo2ByFocalSeat=[b for _, b in pairs],
                allSeatCredits={p: [r['allSeatCredit'] for r in arms[p]] for p in POLICIES}))
    require(len(table) == 80 and all(set(ds) == set(range(4)) for ds in table.values()), 'Full fixed-cell/deal grid')
    subsets = {name: _scores({c: table[c] for c in cells}) for name, cells in _subsets(list(table)).items()}
    germany = None
    if panel == 'strong':
        german = {c: deals for c, deals in table.items() if c.split('|')[0] == 'Germany'}
        neutral = _mean(1 / int(c.split('|')[1]) for c in german)
        require(math.isclose(neutral, .29, rel_tol=0, abs_tol=1e-15), 'Germany analytical .29 neutrality')
        germany = dict(benchmark=neutral, newlyPlayedReferenceControlGames=0,
            selectedMinusNeutral=estimate({c: [_mean(a for a, _ in pairs) - 1 / int(c.split('|')[1])
                for _, pairs in sorted(ds.items())] for c, ds in german.items()}),
            note='Analytical all-reference 1/n neutrality, not an additional played control; smoke grid is not balanced.')
    result = dict(schema='multimap-stress-summary-v1', panel=panel, smoke=False, games=2560, failures=0,
        primary=subsets['allMaps']['pairedDifference'], subgroups=subsets,
        strongOpponentOccupancy={k: _scores(v) for k, v in occupancy.items()},
        reciprocalTwoPlayerGames=256, reciprocalTwoPlayerOutcomes=reciprocal,
        GermanyAnalyticalReferenceBenchmark=germany, homogeneousExpertDealControls=controls,
        cellDealMeans={c: {str(d): dict(expert24=_mean(a for a, _ in pairs), ppo2=_mean(b for _, b in pairs))
                          for d, pairs in ds.items()} for c, ds in table.items()},
        panelResearchProgressionGate=False, bothPanelsRequired=True, caveats=list(CAVEATS),
        qualified=False, qualificationEligible=False, reservedFinalSeedsUsed=False)
    result['panelResearchProgressionGate'] = panel_gate(result)['passed']
    require(len(reciprocal) == 64 and controls == (240 if panel == 'strong' else 0), 'Reciprocal/control coverage')
    return result


def _protocol():
    path = HERE / 'stress-protocol-v1.json'
    require(hashlib.sha256(path.read_bytes()).hexdigest() == PROTOCOL_SHA256, 'Frozen protocol bytes changed')
    return read(path)


def _hashes(mapping, names, label):
    require(isinstance(mapping, dict) and set(mapping) == set(names) and
            all(isinstance(v, str) and re.fullmatch('[0-9a-f]{64}', v) for v in mapping.values()), label)


def _snapshot(root):
    root = Path(root)
    require(root.is_dir() and not root.is_symlink(), 'Missing/unsafe snapshot directory')
    names = {'status.json', 'protocol.json', 'environment.json', 'recovery.json', 'artifacts.json',
             'study/plan.json', 'study/summary.json', *(f'study/batch-{i:03}.json' for i in range(320))}
    files, directories, total = set(), set(), 0
    for path in root.rglob('*'):
        require(not path.is_symlink(), 'Snapshot symlink forbidden')
        name = path.relative_to(root).as_posix()
        if path.is_dir():
            directories.add(name)
        else:
            require(path.is_file(), 'Snapshot nonregular file')
            files.add(name)
            total += path.stat().st_size
    require(files == names and directories == {'study'}, 'Snapshot missing/extra files or directories (including stale .tmp)')
    require(total <= LIMIT, 'Snapshot exceeds 64 MiB budget')
    manifest = read(root / 'artifacts.json')
    _hashes(manifest, names - {'artifacts.json'}, 'Complete manifest schema/key coverage')
    # Integrity/provenance of these payloads is deliberately handled externally.
    for name in ('environment.json', 'recovery.json'):
        value = read(root / name)
        require(isinstance(value, dict) and bool(value), 'Missing ' + name + ' evidence')
    return root, len(files), total


def _metadata(root, panel, tasks, saved):
    protocol = _protocol()
    exact(read(root / 'protocol.json'), protocol, 'Snapshot frozen protocol mismatch')
    identity = read(root / 'study/plan.json')
    fields = {'schema', 'protocol', 'panel', 'smoke', 'tasks', 'expertIdentity', 'sourceFiles',
              'workers', 'threads', 'collector', 'fitting', 'selection', 'qualificationEligible', 'reservedFinalSeedsUsed'}
    require(isinstance(identity, dict) and set(identity) == fields, 'Plan identity schema')
    expected = dict(schema='multimap-stress-identity-v1', protocol=protocol, panel=panel, smoke=False,
        tasks=tasks, workers=6, threads=1, collector='lockstep-central-torch-child-processes',
        fitting=False, selection=False, qualificationEligible=False, reservedFinalSeedsUsed=False)
    exact({k: identity[k] for k in expected}, expected, 'Frozen production plan/tasks/flags')
    require(isinstance(identity['expertIdentity'], dict) and bool(identity['expertIdentity']), 'Missing expert runtime identity')
    _hashes(identity['sourceFiles'], SOURCE_NAMES, 'Frozen source identity hash schema')
    status = read(root / 'status.json')
    expected_status = dict(run=f'multimap-stress-20261103-v1-{panel}', workflow='stress', panel=panel,
        smoke=False, workers=6, sourceRevision=SOURCE_REVISION, sourceSha256=SOURCE_SHA256,
        sourceRepo='coyotte508/powergrid-ai-training-v1',
        sourcePath='multimap/multimap-stress-20261103-v1/source.tgz', protocol=protocol,
        qualified=False, qualificationEligible=False, reservedFinalSeedsUsed=False, stage='complete')
    require(isinstance(status, dict) and set(status) == set(expected_status) | {'receipts', 'result'},
            'Complete original-job status schema; no error/resume')
    exact({k: status[k] for k in expected_status}, expected_status, 'Complete original-job status/scope')
    receipts = status['receipts']
    stages = ['runtime-ready', *(f'batches-{i}' for i in range(16, 321, 16)), 'complete']
    require(isinstance(receipts, list) and len(receipts) == len(stages), 'Original-job checkpoint receipt coverage')
    for receipt, stage in zip(receipts, stages):
        require(isinstance(receipt, dict) and set(receipt) == {'stage', 'revision'} and
                receipt['stage'] == stage and isinstance(receipt['revision'], str) and
                re.fullmatch('[0-9a-f]{40}', receipt['revision']), 'Original-job checkpoint receipt schema/order')
    require(len({r['revision'] for r in receipts}) == len(receipts), 'Duplicate checkpoint receipt revision')
    exact(status['result'], saved, 'Complete status.result differs from saved summary')
    return status


def _coverage(tasks):
    def counts(field):
        return dict(sorted(Counter(str(t[field]) for t in tasks).items()))

    occupancy = defaultdict(lambda: dict(cells=set(), deals=set(), pairs=0))
    opponents = Counter()
    for t in tasks[::2]:
        ring = [c for i, c in enumerate(t['controllers']) if i != t['focalSeat']]
        opponents.update(ring)
        item = occupancy[str(sum(c in ('expert24', 'reference') for c in ring))]
        item['cells'].add(t['cell'])
        item['deals'].add(t['seed'])
        item['pairs'] += 1
    return dict(cells=80, independentDeals=320, pairedFocalSeats=1280, allFocalSeats=True,
        maps=list(MAPS), players=list(range(2, 7)), excludedMaps=['Italy', 'Benelux'],
        rules=[f'{v}|{f}' for v in ('original', 'recharged') for f in (0, 1)],
        gamesByPolicy=counts('policy'), gamesByMap=counts('map'), gamesByPlayers=counts('players'),
        gamesByRule=dict(sorted(Counter(f"{t['variant']}|{int(t['fastBid'])}" for t in tasks).items())),
        gamesByMapPlayers=dict(sorted(Counter(f"{t['map']}|{t['players']}" for t in tasks).items())),
        strongOpponentOccupancy={k: dict(cells=len(v['cells']), independentDeals=len(v['deals']),
            pairedFocalSeats=v['pairs'], games=2 * v['pairs']) for k, v in sorted(occupancy.items())},
        opponentSeatsPerPairedMatchup=dict(sorted(opponents.items())),
        fullTaskSha256=task_hash(tasks), seedRootsSha256=task_hash(sorted({t['seed'] for t in tasks})),
        missing=0, duplicate=0, foreign=0)


def _counter_totals(games):
    counts = {c: {p: sum(g['counts'][c][p] for g in games) for p in PHASES} for c in CONTROLLERS}
    public = {k: sum(g['publicChecks'][k] for g in games) for k in games[0]['publicChecks']}
    requests = {c: sum(g['policyRequests'][c] for g in games) for c in MODELS}
    seats = [{p: sum(g['seatCounts'][i][p] for g in games if len(g['seatCounts']) > i)
              for p in PHASES} for i in range(6)]
    steps = sum(g['steps'] for g in games)
    references = sum(g['referenceRequests'] for g in games)
    non_germany = sum(g['referenceRequests'] for g in games if g['spec']['map'] != 'Germany')
    require(steps == sum(sum(v.values()) for v in counts.values()) == sum(sum(v.values()) for v in seats),
            'Aggregate actual-seat/controller accounting')
    require(public['hiddenInvariant'] == public['referenceAtomicLegal'] == references and
            public['fullMenuPrior'] == sum(requests.values()) and public['expertAtomicLegal'] == non_germany == 0,
            'Aggregate reference/public/zero-label invariants')
    return dict(steps=steps, rounds=sum(g['rounds'] for g in games), controllerPhases=counts,
                actualSeatPhases=seats, publicChecks=public, policyRequests=requests,
                referenceRequests=references, nonGermanyReferenceRequests=non_germany,
                expertLabels=0, ties=sum(sum(x > 0 for x in g['allSeatCredit']) > 1 for g in games))


def audit_panel(root, panel):
    """Validate one complete original snapshot; does not claim both are complete."""
    tasks = expected_tasks(panel)
    root, files, size = _snapshot(root)
    saved = read(root / 'study/summary.json')
    status = _metadata(root, panel, tasks, saved)
    games = []
    for i, batch in enumerate(expected_batches(panel)):
        games.extend(verify_batch(read(root / f'study/batch-{i:03}.json'), i, batch))
    keys = {(g['spec']['seed'], g['spec']['focalSeat'], g['spec']['policy']) for g in games}
    require(len(games) == len(keys) == 2560, 'Duplicate/missing scheduled games')
    summary = _summary_from_verified(games, panel)
    equal(saved, summary, 'Saved summary versus independent reconstruction')
    return dict(schema='multimap-stress-panel-independent-audit-v1', panel=panel, run=status['run'],
        allChecksPassed=True, counts=dict(batches=320, games=2560, cells=80, independentDeals=320,
            pairedFocalSeats=1280, reciprocalTwoPlayerGames=256,
            homogeneousExpertDealControls=summary['homogeneousExpertDealControls'], failures=0),
        summary=summary, scheduledCoverage=_coverage(tasks), gate=panel_gate(summary),
        integrity=dict(snapshotFiles=files, manifestFiles=files - 1, snapshotBytes=size,
            canonicalBatchHashesVerified=320, exactTaskCoverage=True, statusResultMatchesSummary=True,
            originalJobNoErrorOrResume=True, homogeneousSymmetryVerified=True,
            counters=_counter_totals(games), artifactHashesVerifiedHere=False,
            externalChecksRequired=['private immutable artifact hashes/provenance',
                'source/runtime/reference identities', 'exact engine replays']),
        interpretationRequiresBothPanels=True, fitting=False, selection=False,
        qualified=False, qualificationEligible=False, reservedFinalSeedsUsed=False)


def audit_both(strong_root, mixed_root):
    """Audit both independent roots; never pool panels or add replay observations."""
    strong_path, mixed_path = Path(strong_root).resolve(), Path(mixed_root).resolve()
    require(strong_path != mixed_path and strong_path not in mixed_path.parents and mixed_path not in strong_path.parents,
            'Panel snapshot roots must be separate, nonnested directories')
    reports = {'strong': audit_panel(strong_root, 'strong'), 'mixed': audit_panel(mixed_root, 'mixed')}
    roots = [{t['seed'] for t in expected_tasks(p)} for p in PANELS]
    require(len(roots[0]) == len(roots[1]) == 320 and not roots[0] & roots[1], 'Panel seed-root separation')
    games = sum(r['counts']['games'] for r in reports.values())
    batches = sum(r['counts']['batches'] for r in reports.values())
    require(games == 5120 and batches == 640, 'Both complete production panels required')
    lower = {p: r['gate']['adjustedLower'] for p, r in reports.items()}
    minimum = min(r['gate']['minimumMapPairedMean'] for r in reports.values())
    passed = all(x > 0 for x in lower.values()) and minimum >= -.05
    require(passed == all(r['gate']['passed'] for r in reports.values()), 'Combined predeclared gate consistency')
    return dict(schema='multimap-stress-independent-audit-v1', allChecksPassed=True,
        bothPanelsComplete=True, counts=dict(games=games, batches=batches, independentDeals=640),
        rootSeparation=dict(snapshotDirectories=True, independentSeedRoots=True, overlap=0),
        panels=reports, gate=dict(passed=passed, adjustedLowerByPanel=lower,
            minimumMapPairedMean=minimum, bothAdjustedLowerPositive=all(x > 0 for x in lower.values()),
            mapGuardPassed=minimum >= -.05, bothPanelsRequired=True),
        caveats=list(CAVEATS), fitting=False, selection=False, qualified=False,
        qualificationEligible=False, reservedFinalSeedsUsed=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('strong_root', type=Path)
    parser.add_argument('mixed_root', type=Path)
    args = parser.parse_args()
    print(json.dumps(audit_both(args.strong_root, args.mixed_root), indent=2, allow_nan=False))
