"""Independent, standard-library-only replica population stress JSON auditor.

No serving/planner/statistics imports, model loading, games, network or writes.
The literal plan and controller routing below are independent of the collector.
Production only: smoke, partial panels and locally complete JSON WITHOUT external
integrity evidence never release strength statistics. Both panels are mandatory.

External trust boundary
-----------------------
A manifest binds local bytes, not their provenance. ``report_all`` accepts an
OPTIONAL, separately supplied receipt for EACH panel. It is a trusted external
attestation, not cryptographic proof manufactured from expected JSON fields.
Never generate a receipt by copying ``expectedModelProjection`` or flags. The
external auditor must retain genuine independent evidence and authenticate its
SHA256 before supplying the receipt. The exact contract is EXTERNAL_CHECKS and
``validate_integrity`` below. In particular it must decode all six checkpoints,
verify their complete saved config and actual tensor architecture/finite values,
authenticate model/source/runtime/reference provenance, source-before-tasks,
all job submissions (including ambiguous/unknown ones), and committed prefixes.
Requested limits, not elapsed time, govern the 6h + 3h + one shared 3h budget.
Recovery is allowed only after both originals terminate, from an actual ERROR
with message Job timeout, with fixed strong priority if both are incomplete.
Committed batches retain exact bytes, INCLUDING timing. Only uncommitted work
can replay with changed timing; replay observations never increase sample size.

Receipt fields (exact): schema, panel, manifestSha256, evidenceSha256, checks,
sourceIdentitySha256, runtimeIdentitySha256, protocolSha256, fullTaskSha256,
modelProjection, committedBatchSha256, jobBudgetEvidenceSha256. All SHA fields
refer to retained authenticated evidence, not claimed flags. modelProjection
includes the actual decoded schema/update/width/bound/prior flag, the immutable
pin and a SHA256 of the COMPLETE decoded config for EACH of the six models.
The latter MUST hash the actual decoded SAVED config: PPO0's checkpointConfig,
not its current serving config; all other roles use config. PPO0's only allowed
historical exception is the literal original Git/source pin below. The runtime
identity separately binds the complete current provenance, including this
historical evidence. Equality with a claimed config alone is insufficient. External evidence must also authenticate original/continued
committed batch boundaries (not merely enumerate files in a failed manifest).

CLI: python -B ai/multimap/audit_replica_stress_v1.py STRONG_ROOT MIXED_ROOT
     [--integrity EXTERNAL_RECEIPTS.json]
Missing panel roots may be represented as '-' and remain explicitly missing.
On joint release, primaryContrasts indexes the four panel primary estimates by
JSON Pointer; estimates are not duplicated in the serialized report. Exactly
four fields carry adjusted intervals; every exploratory estimate omits them.
No pooled recipe/population inference, winner choice, direct replica superiority,
new progression or qualification gate is defined by this auditor.
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
POLICIES = ('replica1', 'replica2', 'ppo2')
EXPERT_MODELS = ('expert24', 'replica1', 'replica2')
PPO_MODELS = ('ppo0', 'ppo1', 'ppo2')
MODELS = (*EXPERT_MODELS, *PPO_MODELS)
CONTROLLERS = (*MODELS, 'reference', 'teacherV2', 'fixedV2', 'fixedV1')
PHASES = ('Auction', 'Resources', 'Building', 'Bureaucracy')
NAMESPACE = 'pg-multimap-replica-stress-20261109-v1'
SCHEMA = 'multimap-replica-population-stress-v1'
PROTOCOL_SHA256 = '99d6e0e4eac7808f2de8c335361c5611ae4a93edfe8778b30dbe4139fb265d69'
PROTOCOL_FILE_SHA256 = '1ca5a8fd0979f785cec0656a8738fbc7d5b92f9eb70a9729e0c26ec7916477d3'
# Independently pinned original training provenance, NEVER an arbitrary override.
PPO0_HISTORICAL_TRAINING = {
    'sourceGit': 'a3b492b650dec51c34b6f9322d87088b1e863f0e',
    'sourceFiles': {
        'data.py': '3a166d6baf8e294aff56ac13310867d34892347fc754493def1d347d65670492',
        'model.py': '4f790d8fc718ed63f4df1a34c4a71ce1815abfaff50171cb1f6f256fe2f62a3e',
        'features.cjs': '1ced47a4a5e65946a8fdb207f0d6f87d9b535c698729ec36e008d39e0914803b',
        'teacher.cjs': 'd741947ba120f56a17953b92dc553a30cd4476f9594b3161a8a0adb1af0e88cb',
        'game.cjs': '3a36d6a74407d7a8454edba898fabf9848a4c0615e960bb94554ae363b5b1e2b',
        'game_rl.cjs': 'b3e8996da51841340b6f4f77b803dcbf01e2f72938ee44b7ba66f593d8167157',
        'residual.py': '83e8cac000a05b2a015fa4f6612e0e4193ecd134e72f79e77123a2a10346e480',
        'rollout.py': '57c3bcf0ebdfa11090ca68af3111702f5ccd0692e21a4391ce79b5c4dcb8e321',
        'ppo.py': '63e99daba0df6f47fe6e2447caa14b67537ac3d91e5ecfe9246e5c7c21fd24c0',
        'ppo-protocol-v1.json': '51f86acbbd1a495213c40554b3cc0c7933c92a2fc1608690397fbee76dad3cfe',
        'requirements-cpu.txt': '975c2199adeee3550ce7ca31644833fa3fe5605789e6067e86b48610acb8ecf4',
    },
    'nonservingDifferences': ['ppo.py', 'rollout.py'],
}
WATCHPOINTS = ('cell:Germany|2|recharged|1', 'cell:USA|3|original|1',
               'cell:USA|3|recharged|1', 'mapPlayers:USA|2')
LIMIT = 64 * 1024**2
MANIFEST_LIMIT = 64 * 1024
Z_PRIMARY = 2.4977054744123737
SMOKE_SCOPES = (
    ('Germany', 2, 'recharged', True), ('Germany', 6, 'recharged', True),
    ('USA', 3, 'recharged', True), ('USA', 5, 'original', True),
    ('France', 4, 'recharged', False), ('France', 2, 'original', True),
    ('UK & Ireland', 5, 'recharged', True), ('UK & Ireland', 6, 'original', False),
)
MODEL_REPO = 'coyotte508/powergrid-ai-multimap-v1'
# Literal immutable pins, not copied at runtime from an untrusted protocol.
_PIN_ROWS = (
    ('expert24', '39976d5e864638fe73d241061bc4dfd4b46ce0a4',
     'runs/multimap-expert-ppo-20261102-v2-r1/expert/best.pt',
     '1377fc2112c3b9ff3c2a20078ed341305b2a9006a4f7a1df413eeb0b509e6fbd', 24),
    ('replica1', 'ebb354b5c2206376fb65ee7d8e19e2809bb72a70',
     'runs/multimap-expert-replicas-20261109-v1-continuation-r1/expert/best.pt',
     '7918c5ceec29ee181721eaaa3a38f63fd94cf0248c34d192e0b3f65960c729e5', 24),
    ('replica2', '9a116e30b14eb32b48603475f5036d510177f1b9',
     'runs/multimap-expert-replicas-20261109-v1-continuation-r2/expert/best.pt',
     '89d03f5b23fd6d088e175d32ff9c90ff88bd947f7e8b17d508b1b2f641a037fa', 32),
    ('ppo0', 'b1392c4dea3eb956b0e171d558f2f642c0367831',
     'runs/multimap-ppo-20261102-v1/ppo/best.pt',
     '50ac24ad28d8fced065133e90980286e0cf4c592afe81df07aaed33cbf181e0c', 8),
    ('ppo1', '4a7f94fca8a2bdcbb9256c730edc83c64a5d17e9',
     'runs/multimap-ppo-20261102-replica-1/ppo/best.pt',
     'dd79d3fc6d67594c0a60af24e0acd28a2ec0f5798771148b92748b6781ceda15', 16),
    ('ppo2', 'af87f0b46382e4f06d420f339fd1a65a4ba9ef45',
     'runs/multimap-ppo-20261102-replica-2/ppo/best.pt',
     '3d2ffeb02feb17462385ff2a4d2ccd930e58bb445bf97df386b7eef5fce9dc91', 12),
)
MODEL_PINS = {name: dict(name=name, repo=MODEL_REPO, revision=revision, path=path,
                        sha256=sha, update=update,
                        **({'id': int(name[-1])} if name.startswith('replica') else {}))
              for name, revision, path, sha, update in _PIN_ROWS}
EXTERNAL_CHECKS = (
    'immutableRemoteManifestAndSource', 'completeServingConfigAndRuntime',
    'decodedSixCheckpointTensorsAndFullConfigs', 'referenceAndModelProvenance',
    'sourceCommittedBeforeTasks', 'exactEngineReplayAndGreedyRouting',
    'allSubmissionsIncludingUnknownCounted', 'sixPlusThreePlusSharedThreeHourBudget',
    'recoveryOnlyAfterBothOriginalsTerminalActualJobTimeout',
    'fixedStrongPriorityIfBothIncomplete', 'inheritedCommittedBatchesUnchanged',
    'sameSourceRuntimeTasksOnContinuation', 'noOutcomeDependentReplacement',
    'historicalArtifactsAndQualificationUnchanged',
)
FLAGS = dict(fitting=False, selection=False, qualified=False,
             qualificationEligible=False, reservedFinalSeedsUsed=False)
CAVEATS = [
    'Eight independent deal roots per cell; all focal seats are averaged within each deal, then 80 fixed cells receive equal weight.',
    'Normal intervals have approximate coverage, conditional on these frozen policies and fixed schedules; a zero estimated SE is not proof of certainty.',
    'Mixed lineups vary deterministically by actual deal 0..7. ddof=1 includes between-lineup mean variability and is conservative in expectation, not unbiased.',
    'Only the four primary contrasts use Bonferroni 98.75% intervals; all subgroup and occupancy intervals are exploratory unadjusted 95%.',
    'The shared PPO2 observations are counted once and reused in both contrasts; the contrasts are dependent. Bonferroni does not require independence.',
    'Occupancy subsets condition on the deterministic schedule and may have different cell mixes; no randomized causal interpretation.',
    'Occupancy uses equal-cell selected-deal point means and all eight roots with fixed 8/K weights for variance. Nonmembership zeros are analytical contributions, not fabricated outcomes. Sparse occupancy coverage can be especially poor.',
    'Original expert24 is opponent-only. No homogeneous-expert self-play or neutral-credit assertion applies to replica focal games.',
    'Germany mean(1/n)=.29 is analytical context only, not a newly played control or qualification threshold.',
    'Report both panels and all four macros jointly, including negative results; no finished-subset strength conclusion if any panel is incomplete or integrity-pending.',
    'Between-replica spread is descriptive conditional on the fixed policies and common panels, includes evaluation noise, and is not a training-variance estimate or direct superiority test.',
    'No pooled recipe/population inference, winner selection, checkpoint selection, new progression gate, qualification, fitting or deployment.',
]


def require(condition, label):
    if not condition:
        raise ValueError(label)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def task_hash(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def hash_string(value, size=64):
    return type(value) is str and re.fullmatch('[0-9a-f]{' + str(size) + '}', value) is not None


def exact(actual, expected, label):
    require(canonical(actual) == canonical(expected), label)


def finite(value, lower=0, upper=math.inf):
    return type(value) in (int, float) and math.isfinite(value) and lower <= value <= upper


def equal(actual, expected, label='summary'):
    """Strict keys/types/sequence, with 1e-12 tolerance only on float metrics."""
    if type(expected) is dict:
        require(type(actual) is dict and actual.keys() == expected.keys(), label + ': keys')
        for key in expected:
            equal(actual[key], expected[key], label + '.' + str(key))
    elif type(expected) is list:
        require(type(actual) is list and len(actual) == len(expected), label + ': length')
        for left, right in zip(actual, expected):
            equal(left, right, label)
    elif type(expected) is float:
        require(finite(actual, -math.inf) and math.isclose(actual, expected,
                rel_tol=1e-12, abs_tol=1e-12), label + ': number')
    else:
        require(type(actual) is type(expected) and actual == expected, label + ': value/type')


def read(path, limit=LIMIT):
    """Bounded JSON; duplicate keys, NaN, Infinity and exponent overflow reject."""
    path = Path(path).absolute()
    require(path.is_file() and all(not p.is_symlink() for p in (path, *path.parents)) and
            path.stat().st_size <= limit, 'Missing/unsafe/oversized JSON: ' + path.name)

    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, 'Duplicate JSON key: ' + key)
            result[key] = value
        return result

    def number(text):
        value = float(text)
        require(math.isfinite(value), 'Nonfinite JSON number')
        return value

    return json.loads(path.read_text(), object_pairs_hook=pairs, parse_float=number,
                      parse_constant=lambda _: require(False, 'Nonfinite JSON constant'))


def protocol():
    path = HERE / 'replica-stress-protocol-v1.json'
    value = read(path)
    require(digest(path) == PROTOCOL_FILE_SHA256, 'Frozen replica stress protocol bytes changed')
    require(task_hash(value) == PROTOCOL_SHA256, 'Frozen replica stress protocol changed')
    exact(value['ppo0HistoricalTraining'], PPO0_HISTORICAL_TRAINING, 'Literal PPO0 historical source pin')
    return value


def expected_tasks(panel, *, smoke=False):
    """Independent literal ring rotation: three arms, 80 cells, EIGHT deals."""
    require(type(panel) is str and panel in PANELS, 'Production panel required')
    require(type(smoke) is bool, 'Boolean smoke flag required')
    tasks = []
    grid = itertools.product(MAPS, range(2, 7), ('original', 'recharged'), (False, True))
    for ci, scope in enumerate(grid):
        map_name, n, variant, fast = scope
        if smoke and scope not in SMOKE_SCOPES:
            continue
        cell = f'{map_name}|{n}|{variant}|{int(fast)}'
        weak = [*PPO_MODELS, 'teacherV2'] + (['reference'] if map_name == 'Germany' else [])
        for deal in range(1 if smoke else 8):
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
                    namespace = NAMESPACE + (':smoke' if smoke else '')
                    tasks.append(dict(map=map_name, players=n, variant=variant, fastBid=fast,
                        cell=cell, seed=f'{namespace}:{panel}:{cell}:{deal}', smoke=smoke,
                        deal=deal, focalSeat=focal, panel=panel, policy=policy,
                        controllers=controllers, maxSteps=4000))
    require(len(tasks) == (99 if smoke else 7680), 'Independent plan size')
    return tasks


def expected_batches(panel, *, smoke=False):
    batches = []
    for task in expected_tasks(panel, smoke=smoke):
        if not batches or batches[-1][0]['seed'] != task['seed']:
            batches.append([])
        batches[-1].append(task)
    require(len(batches) == (8 if smoke else 640), 'Independent root count')
    return batches


def _counter(value, keys, label):
    require(type(value) is dict and set(value) == set(keys) and
            all(type(v) is int and v >= 0 for v in value.values()), label)


def validate_outcome(game, task):
    """Independent terminal, ten-controller/actual-seat and no-label validation."""
    fields = {'spec', 'terminal', 'credit', 'allSeatCredit', 'steps', 'rounds',
              'counts', 'seatCounts', 'publicChecks', 'policyRequests',
              'referenceRequests', 'featureMs', 'inferenceMs', 'referenceMs', 'seconds'}
    require(type(game) is dict and set(game) == fields, 'Compact outcome schema')
    exact(game['spec'], task, 'Outcome canonical task/order/scope')
    require(game['terminal'] is True, 'Nonterminal outcome')
    require(all(finite(game[k]) for k in ('featureMs', 'inferenceMs', 'referenceMs', 'seconds')),
            'Invalid outcome timing')
    credits = game['allSeatCredit']
    require(type(credits) is list and len(credits) == task['players'] and
            all(finite(v, 0, 1) for v in credits), 'Terminal credit vector')
    winners = sum(v > 0 for v in credits)
    require(winners > 0 and all(v == 0 or v == 1 / winners for v in credits) and
            math.isclose(math.fsum(credits), 1, rel_tol=0, abs_tol=1e-12), 'Equal-share winner credit')
    require(finite(game['credit'], 0, 1) and game['credit'] == credits[task['focalSeat']],
            'Focal credit disagrees with complete vector')
    require(type(game['steps']) is int and 0 < game['steps'] <= 4000 and
            type(game['rounds']) is int and 0 < game['rounds'] <= game['steps'], 'Steps/rounds/cap')
    counts, seats = game['counts'], game['seatCounts']
    require(type(counts) is dict and set(counts) == set(CONTROLLERS), 'Controller counter schema')
    require(type(seats) is list and len(seats) == task['players'], 'Actual seat counter coverage')
    for counter in [*counts.values(), *seats]:
        _counter(counter, PHASES, 'Phase counters must be nonnegative integers')
    require(sum(sum(c.values()) for c in counts.values()) == game['steps'] ==
            sum(sum(c.values()) for c in seats), 'Controller/seat totals account for all steps')
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
        for fixed, family in (('fixedV2', EXPERT_MODELS), ('fixedV1', PPO_MODELS)):
            require(counts[fixed][phase] == sum(assigned[c] - counts[c][phase] for c in family),
                    'Actual seat ' + fixed + ' routing')
    totals = {c: sum(counts[c].values()) for c in CONTROLLERS}
    require(task['map'] == 'Germany' or totals['reference'] == 0, 'Reference escaped Germany')
    checks = dict(hiddenInvariant=totals['reference'], referenceAtomicLegal=totals['reference'],
                  fullMenuPrior=sum(totals[c] for c in MODELS), expertAtomicLegal=0)
    _counter(game['publicChecks'], checks, 'Public counter schema/types')
    exact(game['publicChecks'], checks, 'Public/full-menu/zero-label counters')
    _counter(game['policyRequests'], MODELS, 'Policy request schema/types')
    exact(game['policyRequests'], {c: totals[c] for c in MODELS}, 'Policy request mismatch')
    require(type(game['referenceRequests']) is int and game['referenceRequests'] == totals['reference'],
            'Reference request mismatch')
    return credits[task['focalSeat']]


def verify_batch(record, index, tasks):
    require(type(record) is dict and set(record) == {'schema', 'index', 'taskSha256', 'games'} and
            record['schema'] == 'multimap-replica-stress-batch-v1' and type(record['index']) is int and
            record['index'] == index and record['taskSha256'] == task_hash(tasks) and
            type(record['games']) is list and len(record['games']) == len(tasks),
            'Batch schema/index/task hash/size')
    for game, task in zip(record['games'], tasks):
        validate_outcome(game, task)
    return record['games']


def _mean(values):
    values = list(values)
    require(bool(values), 'Empty mean')
    return math.fsum(values) / len(values)


def estimate(strata, *, primary=False):
    """Equal-cell mean with ddof=1 deal variance; NEVER independent-arm SEs."""
    require(type(primary) is bool and type(strata) is dict and bool(strata) and
            all(isinstance(v, (list, tuple)) and v and all(finite(x, -1, 1) for x in v)
                for v in strata.values()), 'Invalid deal-cluster observations')
    means = {c: _mean(v) for c, v in strata.items()}
    mean = _mean(means.values())
    se = None
    if all(len(v) >= 2 for v in strata.values()):
        terms = [math.fsum((v - means[c]) ** 2 for v in values) /
                 ((len(values) - 1) * len(values)) for c, values in strata.items()]
        se = math.sqrt(math.fsum(terms)) / len(strata)
    result = dict(mean=mean, standardError=se, cells=len(strata),
        independentDeals=sum(len(v) for v in strata.values()),
        approximateNormal95=None if se is None else [mean - 1.96 * se, mean + 1.96 * se])
    if primary:
        require(len(strata) == 80 and all(len(v) == 8 for v in strata.values()),
                'Primary requires eight deals in all 80 cells')
        result['fourPrimaryBonferroniNormal9875'] = [mean - Z_PRIMARY * se, mean + Z_PRIMARY * se]
    return result


def _subsets(cells):
    out = {'allMaps': cells}
    out.update({'map:' + m: [c for c in cells if c.split('|')[0] == m] for m in MAPS})
    out.update({'players:' + str(n): [c for c in cells if c.split('|')[1] == str(n)] for n in range(2, 7)})
    out.update({'rule:' + v + '|' + str(f): [c for c in cells if c.split('|')[2:] == [v, str(f)]]
                for v in ('original', 'recharged') for f in (0, 1)})
    out.update({'mapPlayers:' + m + '|' + str(n): [c for c in cells if c.split('|')[:2] == [m, str(n)]]
                for m in MAPS for n in range(2, 7)})
    out.update({'cell:' + c: [c] for c in cells})
    return out


def _scores(table):
    result = {}
    for policy in POLICIES:
        result[policy] = estimate({c: [row[policy] for _, row in sorted(deals.items())]
                                   for c, deals in table.items()})
    for replica in POLICIES[:2]:
        result[replica + 'MinusPpo2'] = estimate({
            c: [row[replica] - row['ppo2'] for _, row in sorted(deals.items())]
            for c, deals in table.items()})
    return result


def _occupancy_scores(table):
    """Fixed-schedule occupancy: independent direct 8/K weighted-root variance.

    A root outside the stratum contributes analytic zero, not an observed loss.
    Selected-deal point means remain equally weighted across represented cells.
    For sparse membership, particularly K=1, approximate coverage can be poor.
    """
    result = {}
    for label in (*POLICIES, 'replica1MinusPpo2', 'replica2MinusPpo2'):
        contributions, selected = {}, {}
        for cell, deals in table.items():
            selected[cell] = len(deals)
            values = []
            for deal in range(8):
                row = deals.get(deal)
                observation = 0.0 if row is None else (row[label] if label in POLICIES else
                    row[label.split('Minus')[0]] - row['ppo2'])
                values.append(8 * observation / len(deals))
            contributions[cell] = values
        means = {c: _mean(v) for c, v in contributions.items()}
        mean = _mean(means.values())
        variance = math.fsum(math.fsum((x - means[c])**2 for x in values) / (7 * 8)
                             for c, values in contributions.items())
        se = math.sqrt(variance) / len(table)
        result[label] = dict(mean=mean, standardError=se, cells=len(table),
            independentDeals=8 * len(table), approximateNormal95=[mean - 1.96 * se, mean + 1.96 * se],
            selectedDeals=sum(selected.values()), selectedDealsByCell=selected,
            scheduleVariance='all-roots-zero-nonmembership-fixed-D-over-K-weights')
    return result


def _summary_from_verified(games, panel):
    table = defaultdict(dict)
    occupancy = defaultdict(lambda: defaultdict(dict))
    reciprocal = []
    offset = 0
    for tasks in expected_batches(panel):
        records = games[offset:offset + len(tasks)]
        offset += len(tasks)
        spec = tasks[0]
        cell, deal, n = spec['cell'], spec['deal'], spec['players']
        arms = {p: records[i::3] for i, p in enumerate(POLICIES)}
        means = {p: _mean(g['credit'] for g in arms[p]) for p in POLICIES}
        strengths = {sum(c in ('expert24', 'reference') for i, c in enumerate(t['controllers'])
                         if i != t['focalSeat']) for t in tasks}
        require(len(strengths) == 1, 'Rotated scheduled occupancy coverage')
        table[cell][deal] = means
        occupancy[str(next(iter(strengths)))][cell][deal] = means
        if n == 2:
            reciprocal.append(dict(cell=cell, deal=deal,
                opponent=tasks[0]['controllers'][1],
                focalCreditByPolicy={p: [g['credit'] for g in arms[p]] for p in POLICIES},
                allSeatCredits={p: [g['allSeatCredit'] for g in arms[p]] for p in POLICIES}))
    require(offset == 7680 and len(table) == 80 and all(set(ds) == set(range(8)) for ds in table.values()),
            'Full fixed-cell/eight-deal grid')
    primary = {replica + 'MinusPpo2': estimate({
        c: [row[replica] - row['ppo2'] for _, row in sorted(ds.items())]
        for c, ds in table.items()}, primary=True) for replica in POLICIES[:2]}
    germany = dict(benchmark=.29, newlyPlayedReferenceControlGames=0,
        note='Analytical mean(1/n) across the balanced Germany player counts; context only, not a control or threshold.')
    subgroups = {name: _scores({c: table[c] for c in cells}) for name, cells in _subsets(list(table)).items()}
    return dict(schema='multimap-replica-stress-independent-summary-v1', panel=panel,
        smoke=False, games=7680, gamesByPolicy={p: 2560 for p in POLICIES}, failures=0,
        primary=primary, subgroups=subgroups,
        watchpoints={key: subgroups[key] for key in WATCHPOINTS},
        strongOpponentOccupancy={k: _occupancy_scores(v) for k, v in sorted(occupancy.items())},
        reciprocalTwoPlayerGames=768, reciprocalTwoPlayerOutcomes=reciprocal,
        GermanyAnalyticalReferenceBenchmark=germany,
        cellDealMeans={c: {str(d): row for d, row in ds.items()} for c, ds in table.items()},
        betweenReplicaSpread=dict(primaryMeans={p: primary[p + 'MinusPpo2']['mean'] for p in POLICIES[:2]},
            absoluteRange=abs(primary['replica1MinusPpo2']['mean'] - primary['replica2MinusPpo2']['mean']),
            descriptiveOnly=True, trainingVarianceEstimate=False, directSuperiorityTest=False),
        bothPanelsRequired=True, caveats=list(CAVEATS), **FLAGS)


def recompute_summary(games, panel):
    """Low-level independent math, for tests/internal validation, not a release API.

    A caller must NOT publish this as an audited result without report_all's
    both-panel external integrity gate.
    """
    tasks = expected_tasks(panel)
    require(type(games) is list and len(games) == 7680, 'No partial-data inference')
    for game, task in zip(games, tasks):
        validate_outcome(game, task)
    return _summary_from_verified(games, panel)


SOURCE_NAMES = (
    'replica-stress-protocol-v1.json', 'replica_stress_game_v1.cjs',
    'replica_stress_rollout_v1.py', 'replica_stress_study_v1.py',
    'job_replica_stress_v1.py', 'launch_replica_stress_v1.py',
    'preflight_replica_stress_v1.py', 'test_replica_stress_v1.cjs',
    'test_replica_stress_rollout_v1.py', 'test_replica_stress_study_v1.py',
    'test_job_replica_stress_v1.py', 'test_launch_replica_stress_v1.py',
    'test_preflight_replica_stress_v1.py',
)
FORBIDDEN = {
    'observation', 'observations', 'request', 'requests', 'response', 'responses',
    'state', 'states', 'move', 'moves', 'rows', 'action', 'actions', 'state_dict',
    'trajectory', 'trajectories', 'trace', 'traces', 'optimizer', 'gradients',
}
RUNNER_CAVEATS = [
    'Eight independent roots/cell, fixed policies/populations; normal coverage remains approximate.',
    'Mixed deterministic lineups use actual deal 0..7, not modulo four; this extends the old schedule, not its identical four-lineup distribution.',
    'Mixed ddof=1 includes lineup-mean variation and is conservative in expectation for the fixed-schedule mean, not unbiased.',
    'Four primary replica-by-panel comparisons share one played PPO2 control per seat/deal; Bonferroni does not assume comparison independence.',
    'Only the four macro primary contrasts have Bonferroni 98.75% intervals; raw means, subgroups, occupancy and neutral context have exploratory unadjusted 95% intervals only. Occupancy conditions on the schedule and is not randomized causal evidence.',
    'Occupancy preserves equal-cell selected-deal point means; all eight scheduled roots enter variance with fixed 8/K weights and zero analytic nonmembership contributions. Sparse occupancy coverage can be especially poor; selected-deal counts are exposed.',
    'No pooled population or training-variance inference, homogeneous-expert neutral control, winner selection, automatic progression, qualification or deployment.',
    'Smoke is descriptive engineering evidence only; production requires every frozen task before inference.',
]


def _runner_summary(summary):
    """Independent serialization of the runner's saved schema, NOT its stats.

    Only the two macro contrasts per panel have adjusted intervals. Preserve
    exact key checking: even allMaps, raw arms, occupancy, watchpoints and the
    Germany neutral context must OMIT multiplicity-shaped fields.
    """
    def metric(value):
        return dict(value, descriptiveOnly=False)

    subgroups = {name: {k: metric(v) for k, v in scores.items()}
                 for name, scores in summary['subgroups'].items()}
    germany = None
    if summary['panel'] == 'strong':
        means = summary['cellDealMeans']
        germany = dict(benchmark=.29, newlyPlayedReferenceControlGames=0,
            replicaMinusNeutral={p: metric(estimate({
                c: [row[p] - 1 / int(c.split('|')[1]) for row in ds.values()]
                for c, ds in means.items() if c.startswith('Germany|')})) for p in POLICIES[:2]},
            note='Analytical all-reference 1/n context, not played control or qualification. Smoke is not a balanced grid.')
    return dict(schema='multimap-replica-stress-summary-v1', panel=summary['panel'], smoke=False,
        descriptiveOnly=False, games=7680, failures=0,
        primary={p: metric(summary['primary'][p + 'MinusPpo2']) for p in POLICIES[:2]},
        sharedPpo2Games=2560, subgroups=subgroups,
        strongOpponentOccupancy={k: {p: metric(v) for p, v in scores.items()}
                                 for k, scores in summary['strongOpponentOccupancy'].items()},
        reciprocalTwoPlayerGames=768,
        reciprocalTwoPlayerOutcomes=[dict(cell=r['cell'], deal=r['deal'], opponent=r['opponent'],
            focalCredits=r['focalCreditByPolicy'], allSeatCredits=r['allSeatCredits'])
            for r in summary['reciprocalTwoPlayerOutcomes']],
        GermanyAnalyticalReferenceBenchmark=germany, cellDealMeans=summary['cellDealMeans'],
        watchpoints={key: subgroups[key] for key in WATCHPOINTS},
        bothPanelsRequired=True, automaticProgression=False,
        winnerSelection=False, caveats=list(RUNNER_CAVEATS), **FLAGS)


def compact_json(value):
    if type(value) is dict:
        require(not FORBIDDEN.intersection(value), 'Raw decision/optimization payload forbidden')
        for child in value.values():
            compact_json(child)
    elif type(value) is list:
        for child in value:
            compact_json(child)
    elif type(value) is float:
        require(math.isfinite(value), 'Nonfinite JSON')


def _hashes(value, names, label):
    require(type(value) is dict and set(value) == set(names) and
            all(hash_string(v) for v in value.values()), label)


def _snapshot(root):
    root = Path(root).absolute()
    require(all(not p.is_symlink() for p in (root, *root.parents)) and root.is_dir(),
            'Missing/unsafe snapshot directory')
    metadata = {'status.json', 'protocol.json', 'environment.json', 'recovery.json'}
    allowed = metadata | {'study/plan.json', 'study/summary.json', 'artifacts.json'} | {
        f'study/batch-{i:03}.json' for i in range(640)}
    files, dirs, size = set(), set(), 0
    for path in root.rglob('*'):
        require(not path.is_symlink(), 'Snapshot symlink forbidden')
        name = path.relative_to(root).as_posix()
        if path.is_dir():
            dirs.add(name)
        else:
            require(path.is_file(), 'Snapshot nonregular file')
            files.add(name)
            size += path.stat().st_size
    require(metadata | {'study/plan.json', 'artifacts.json'} <= files <= allowed and dirs == {'study'},
            'Snapshot missing/extra files or directories (including stale .tmp)')
    require(size <= LIMIT, 'Snapshot exceeds 64 MiB aggregate budget')
    manifest = read(root / 'artifacts.json', MANIFEST_LIMIT)
    _hashes(manifest, files - {'artifacts.json'}, 'Complete exact manifest file coverage')
    for name, sha in manifest.items():
        require(digest(root / name) == sha, 'Artifact hash mismatch: ' + name)
    present = sorted(n for n in files if n.startswith('study/batch-'))
    require(present == [f'study/batch-{i:03}.json' for i in range(len(present))],
            'Noncontiguous committed batches')
    require('study/summary.json' not in files or len(present) == 640, 'Partial summary forbidden')
    return root, manifest, size, present


def _model_projection(provenance):
    """Expected DECODED SAVED-config hashes, not self-authenticating evidence.

    ``config`` is always the complete CURRENT serving identity. Only PPO0 has
    checkpointConfig, exactly that config except the pinned original 11-file
    source map. The full record remains bound by runtimeIdentitySha256.
    """
    require(type(provenance) is dict and set(provenance) == set(MODELS), 'Six full model identities required')
    frozen = protocol()
    historical = PPO0_HISTORICAL_TRAINING
    current_sources = {name: frozen['frozenSources'][name] for name in historical['sourceFiles']}
    require(sorted(name for name, sha in current_sources.items()
                   if sha != historical['sourceFiles'][name]) == ['ppo.py', 'rollout.py'],
            'Exactly two pinned training-only source differences')
    result = {}
    for name in MODELS:
        record = provenance[name]
        record_fields = {'pin', 'config', 'role'}
        if name == 'ppo0':
            record_fields |= {'checkpointConfig', 'historicalTrainingSource'}
        require(type(record) is dict and set(record) == record_fields, 'Model provenance schema ' + name)
        exact(record['pin'], MODEL_PINS[name], 'Immutable model pin ' + name)
        role = ('focal-only' if name.startswith('replica') else
                'shared-focal-control-and-opponent' if name == 'ppo2' else 'opponent-only')
        require(record['role'] == role, 'Frozen model role ' + name)
        config = record['config']
        expert = name in EXPERT_MODELS
        fields = {'protocol', 'smoke', 'generatorDigest', 'sourceFiles'}
        if expert:
            fields |= {'schema', 'engineDependencies', 'referenceSourceFiles', 'referenceManifestSha256',
                       'referenceFiles', 'runtimeVersions', 'execution', 'sourcePins'}
        if name.startswith('replica'):
            fields |= {'replica', 'replicaStudy'}
        require(type(config) is dict and set(config) == fields, 'Complete current serving config schema ' + name)
        require(config['smoke'] is False and hash_string(config['generatorDigest']) and
                type(config['protocol']) is dict and bool(config['protocol']) and
                type(config['sourceFiles']) is dict and bool(config['sourceFiles']) and
                all(type(k) is str and hash_string(v) for k, v in config['sourceFiles'].items()),
                'Current serving config identity ' + name)
        saved_config = config
        if not expert:
            exact(config['sourceFiles'], current_sources, 'Pinned current PPO serving sources ' + name)
        if name == 'ppo0':
            exact(record['historicalTrainingSource'], historical, 'Pinned PPO0 historical training provenance')
            saved_config = record['checkpointConfig']
            exact(saved_config, dict(config, sourceFiles=historical['sourceFiles']),
                  'PPO0 complete checkpoint config must differ ONLY by pinned historical sourceFiles')
        if expert:
            require(config['schema'] == ('multimap-expert-replica-identity-v1' if name.startswith('replica')
                    else 'multimap-expert-training-identity-v2') and
                    hash_string(config['referenceManifestSha256']) and
                    all(type(config[k]) is dict and bool(config[k]) for k in
                        ('referenceSourceFiles', 'runtimeVersions', 'execution', 'sourcePins')),
                    'Expert runtime identity ' + name)
        if name.startswith('replica'):
            require(type(config['replica']) is int and config['replica'] == int(name[-1]) and
                    type(config['replicaStudy']) is dict and bool(config['replicaStudy']), 'Replica identity')
        projection = dict(pin=MODEL_PINS[name], configSha256=task_hash(saved_config),
            schema='multimap-expert-ppo-v2' if expert else 'multimap-residual-ppo-v1',
            update=MODEL_PINS[name]['update'], width=64, bound=16 if expert else 8)
        if expert:
            projection.update(stage='train', priorAsActionFeature=True)
        result[name] = projection
    return result


def _metadata(root, panel, tasks, manifest):
    frozen = protocol()
    exact(read(root / 'protocol.json'), frozen, 'Snapshot frozen protocol mismatch')
    identity = read(root / 'study/plan.json')
    fields = {'schema', 'protocol', 'panel', 'smoke', 'tasks', 'modelProvenance', 'sourceFiles',
              'frozenSources', 'workers', 'threads', 'collector', 'fitting', 'selection',
              'qualificationEligible', 'reservedFinalSeedsUsed'}
    require(type(identity) is dict and set(identity) == fields, 'Plan identity schema')
    expected = dict(schema='multimap-replica-stress-identity-v1', protocol=frozen,
        panel=panel, smoke=False, tasks=tasks, frozenSources=frozen['frozenSources'],
        workers=6, threads=1, collector='lockstep-central-torch-child-processes',
        fitting=False, selection=False, qualificationEligible=False, reservedFinalSeedsUsed=False)
    exact({k: identity[k] for k in expected}, expected, 'Full production plan/tasks/source/flags')
    _hashes(identity['sourceFiles'], SOURCE_NAMES, 'Complete versioned source hash schema')
    projection = _model_projection(identity['modelProvenance'])
    status = read(root / 'status.json')
    group = 'multimap-replica-stress-20261109-v1'
    base = dict(workflow='replica-stress-v1', group=group, panel=panel, smoke=False, workers=6,
        protocol=frozen, sourceRepo='coyotte508/powergrid-ai-training-v1',
        sourcePath=f'multimap/{group}/source.tgz',
        qualified=False, qualificationEligible=False, reservedFinalSeedsUsed=False)
    fields = set(base) | {'run', 'segment', 'slot', 'sourceRevision', 'sourceCommit', 'sourceSha256', 'stage', 'receipts'}
    require(type(status) is dict and fields <= set(status) <= fields | {'result', 'error', 'resume'},
            'Worker status schema')
    exact({k: status[k] for k in base}, base, 'Worker source/scope/flags')
    require(type(status['segment']) is int and status['segment'] in (1, 2), 'Original or single recovery segment')
    continuation = status['segment'] == 2
    require(status['run'] == group + ('-recovery-' if continuation else '-') + panel and
            status['slot'] == ('recovery' if continuation else panel) and
            hash_string(status['sourceRevision'], 40) and hash_string(status['sourceCommit'], 40) and
            hash_string(status['sourceSha256']), 'Run/source identity')
    require(('resume' in status) == continuation, 'Continuation must bind original committed snapshot')
    if continuation:
        resume = status['resume']
        require(type(resume) is dict and set(resume) == {'run', 'revision', 'manifestSha256', 'files',
                'allFileHashes', 'totalBytes', 'transaction'} and resume['run'] == group + '-' + panel and
                hash_string(resume['revision'], 40) and hash_string(resume['manifestSha256']) and
                type(resume['totalBytes']) is int and 0 < resume['totalBytes'] <= LIMIT,
                'Original snapshot resume evidence')
        transaction = resume['transaction']
        require(type(transaction) is dict and set(transaction) == {'committedBatches', 'committedGames', 'complete', 'planSha256'} and
                type(transaction['committedBatches']) is int and 0 <= transaction['committedBatches'] < 640 and
                transaction['complete'] is False and transaction['planSha256'] == manifest['study/plan.json'],
                'Resume committed transaction boundary')
        count = transaction['committedBatches']
        expected_names = {'study/plan.json'} | {f'study/batch-{i:03}.json' for i in range(count)}
        _hashes(resume['files'], expected_names, 'Inherited committed file coverage')
        require(type(transaction['committedGames']) is int and transaction['committedGames'] ==
                sum(len(batch) for batch in expected_batches(panel)[:count]), 'Inherited committed game count')
        require(type(resume['allFileHashes']) is dict and set(resume['allFileHashes']) ==
                expected_names | {'status.json', 'protocol.json', 'environment.json', 'recovery.json'} and
                all(hash_string(v) for v in resume['allFileHashes'].values()), 'Original manifest members')
        for name, sha in resume['files'].items():
            require(manifest.get(name) == sha == resume['allFileHashes'][name], 'Committed prefix changed (including timing)')
    stage = status['stage']
    require(type(stage) is str and (stage in ('runtime-ready', 'complete', 'failed') or
            re.fullmatch(r'batches-(?:[1-9][0-9]{0,2})', stage)), 'Worker stage')
    if stage.startswith('batches-'):
        number = int(stage.split('-')[1])
        require(number % 16 == 0 and 16 <= number <= 640, 'Worker checkpoint stage')
    require(('error' in status) == (stage == 'failed'), 'Failed status/error consistency')
    if 'error' in status:
        exact(status['error'], {'code': 'replica-stress-job-stopped'}, 'Fixed compact failure code')
    receipts = status['receipts']
    require(type(receipts) is list and len(receipts) <= 43, 'Worker receipt coverage')
    previous = -1
    for receipt in receipts:
        require(type(receipt) is dict and set(receipt) == {'stage', 'revision'} and
                type(receipt['stage']) is str and hash_string(receipt['revision'], 40), 'Worker receipt schema')
        label = receipt['stage']
        if label == 'runtime-ready':
            ordinal = 0
        elif label == 'complete':
            ordinal = 641
        else:
            require(re.fullmatch(r'batches-[1-9][0-9]{0,2}', label), 'Committed receipt stage')
            ordinal = int(label.split('-')[1])
            require(16 <= ordinal <= 640 and ordinal % 16 == 0, 'Committed batch receipt')
        require(ordinal > previous, 'Receipt order/duplicate')
        previous = ordinal
    require(len({r['revision'] for r in receipts}) == len(receipts), 'Duplicate receipt revision')
    present_count = sum(name.startswith('study/batch-') for name in manifest)
    require(previous <= present_count or previous == 641 and present_count == 640,
            'Receipt claims uncommitted batches')
    if stage.startswith('batches-'):
        require(int(stage.split('-')[1]) <= present_count, 'Checkpoint stage exceeds committed prefix')
    if stage == 'complete':
        inherited = status['resume']['transaction']['committedBatches'] if continuation else 0
        expected_stages = ['runtime-ready', *(f'batches-{n}' for n in range(16, 641, 16) if n > inherited)]
        actual_stages = [r['stage'] for r in receipts]
        require(actual_stages in (expected_stages, [*expected_stages, 'complete']),
                'Complete original/continuation checkpoint receipt coverage')
    environment, recovery = read(root / 'environment.json'), read(root / 'recovery.json')
    require(type(environment) is dict and bool(environment) and type(recovery) is dict and bool(recovery),
            'Missing source/runtime/reference evidence')
    for value in (identity, status, environment, recovery):
        compact_json(value)
    source = {k: status[k] for k in ('sourceRepo', 'sourcePath', 'sourceRevision', 'sourceCommit', 'sourceSha256')}
    return dict(status=status, projection=projection,
        sourceIdentitySha256=task_hash(dict(source=source, sourceFiles=identity['sourceFiles'],
                                           frozenSources=identity['frozenSources'])),
        runtimeIdentitySha256=task_hash(dict(modelProvenance=identity['modelProvenance'],
                                             environment=environment, recovery=recovery)))


def validate_integrity(receipt, report):
    """Validate bindings of a trusted EXTERNAL attestation, never produce one."""
    fields = {'schema', 'panel', 'manifestSha256', 'evidenceSha256', 'checks',
              'sourceIdentitySha256', 'runtimeIdentitySha256', 'protocolSha256',
              'fullTaskSha256', 'modelProjection', 'committedBatchSha256', 'jobBudgetEvidenceSha256'}
    require(type(receipt) is dict and set(receipt) == fields, 'External integrity receipt schema')
    require(receipt['schema'] == 'multimap-replica-stress-external-integrity-v1', 'External integrity schema')
    checks = receipt['checks']
    require(type(checks) is dict and set(checks) == set(EXTERNAL_CHECKS) and
            all(v is True for v in checks.values()), 'All independent external integrity checks required')
    for field in ('evidenceSha256', 'jobBudgetEvidenceSha256'):
        require(hash_string(receipt[field]), 'Genuine separately retained external evidence SHA256 required')
    binding = report['integrityBinding']
    for field in ('panel', 'manifestSha256', 'sourceIdentitySha256', 'runtimeIdentitySha256',
                  'protocolSha256', 'fullTaskSha256', 'committedBatchSha256'):
        exact(receipt[field], binding[field], 'External receipt binding: ' + field)
    exact(receipt['modelProjection'], report['expectedModelProjection'], 'Decoded fixed model/config projection')
    return dict(evidenceSha256=receipt['evidenceSha256'], jobBudgetEvidenceSha256=receipt['jobBudgetEvidenceSha256'],
                allExternalChecksPassed=True, receiptIsTrustedExternalAttestation=True)


def _counter_totals(games):
    return dict(steps=sum(g['steps'] for g in games),
        controllerPhases={c: {p: sum(g['counts'][c][p] for g in games) for p in PHASES} for c in CONTROLLERS},
        policyRequests={c: sum(g['policyRequests'][c] for g in games) for c in MODELS},
        referenceRequests=sum(g['referenceRequests'] for g in games),
        publicChecks={k: sum(g['publicChecks'][k] for g in games) for k in
                      ('hiddenInvariant', 'referenceAtomicLegal', 'fullMenuPrior', 'expertAtomicLegal')},
        expertLabels=0)


def _audit_panel(root, panel, integrity=None):
    tasks = expected_tasks(panel)
    root, manifest, size, present = _snapshot(root)
    meta = _metadata(root, panel, tasks, manifest)
    status = meta['status']
    games = []
    for index, batch in enumerate(expected_batches(panel)[:len(present)]):
        record = read(root / present[index])
        compact_json(record)
        games.extend(verify_batch(record, index, batch))
    complete_json = len(present) == 640 and 'study/summary.json' in manifest
    require(status['stage'] != 'complete' or complete_json, 'Complete status requires all outputs')
    if 'result' in status:
        require(complete_json, 'Partial status.result forbidden')
        equal(status['result'], read(root / 'study/summary.json'), 'status.result differs from committed summary')
    summary = None
    if complete_json:
        summary = _summary_from_verified(games, panel)
        saved = read(root / 'study/summary.json')
        compact_json(saved)
        equal(saved, _runner_summary(summary), 'Saved versus independent summary')
    report = dict(schema='multimap-replica-stress-panel-independent-audit-v1', panel=panel,
        status='integrity-pending' if complete_json else 'incomplete', jsonComplete=complete_json,
        workerStage=status['stage'], workerError=status.get('error'), segment=status['segment'],
        counts=dict(batches=len(present), expectedBatches=640, games=len(games), expectedGames=7680,
            independentDeals=len(present), gamesByPolicy=dict(Counter(g['spec']['policy'] for g in games)),
            scheduledGamesByPolicy={p: 2560 for p in POLICIES}, remainingGames=7680-len(games)),
        localJsonChecksPassed=True, snapshotBytes=size, manifestFiles=len(manifest),
        expectedModelProjection=meta['projection'], counters=_counter_totals(games),
        integrityBinding=dict(panel=panel, manifestSha256=digest(root / 'artifacts.json'),
            sourceIdentitySha256=meta['sourceIdentitySha256'], runtimeIdentitySha256=meta['runtimeIdentitySha256'],
            protocolSha256=PROTOCOL_SHA256, fullTaskSha256=task_hash(tasks),
            committedBatchSha256={name: manifest[name] for name in present}),
        externalChecksRequired=list(EXTERNAL_CHECKS), strengthStatisticsReleased=False, **FLAGS)
    if integrity is not None:
        require(complete_json, 'Cannot accept integrity receipt for incomplete panel')
        report['externalIntegrity'] = validate_integrity(integrity, report)
        report['status'] = 'complete-integrity-verified'
    return report, summary


def audit_panel(root, panel, *, integrity=None):
    """Read-only panel validation. Never releases one-panel strength estimates."""
    return _audit_panel(root, panel, integrity)[0]


def _observed_counts(root):
    """Best-effort UNSCORED counts after rejection; never fabricate losses."""
    result = dict(batches=0, games=0, gamesByPolicy={p: 0 for p in POLICIES}, verified=False)
    if root is None:
        return result
    try:
        root = Path(root).absolute()
        if not root.is_dir() or any(p.is_symlink() for p in (root, *root.parents)):
            return result
        total = 0
        for index in range(640):
            path = root / 'study' / f'batch-{index:03}.json'
            if not path.is_file() or path.is_symlink():
                continue
            total += path.stat().st_size
            if total > LIMIT:
                break
            record = read(path)
            if type(record) is dict and type(record.get('games')) is list:
                result['batches'] += 1
                result['games'] += len(record['games'])
                for game in record['games']:
                    if type(game) is dict and type(game.get('spec')) is dict:
                        policy = game['spec'].get('policy')
                        if type(policy) is str and policy in POLICIES:
                            result['gamesByPolicy'][policy] += 1
    except (OSError, ValueError, TypeError, KeyError, RecursionError):
        pass
    return result


def report_all(roots, *, statuses=None, integrity=None):
    """Require BOTH IDs; preserve failures/counts; release all four or NONE.

    primaryContrasts is a JSON-Pointer index into panel summaries, not duplicate
    estimates: the joint JSON has exactly FOUR adjusted-interval fields.
    """
    require(type(roots) is dict and set(roots) == set(PANELS), 'Both panel roots are mandatory')
    statuses = {} if statuses is None else statuses
    integrity = {} if integrity is None else integrity
    require(type(statuses) is dict and set(statuses) <= set(PANELS) and
            all(type(v) is str and len(v) <= 256 for v in statuses.values()), 'Operational status mapping')
    require(type(integrity) is dict and set(integrity) <= set(PANELS), 'External receipt mapping')
    paths = [Path(roots[p]).absolute() for p in PANELS if roots[p] is not None]
    if len(paths) == 2:
        left, right = (p.resolve() for p in paths)
        require(left != right and left not in right.parents and right not in left.parents,
                'Panel roots must be separate nonnested directories')
    seed_sets = [{t['seed'] for t in expected_tasks(p)} for p in PANELS]
    require(len(seed_sets[0]) == len(seed_sets[1]) == 640 and not seed_sets[0] & seed_sets[1],
            'Panel seed-root separation')
    panels, summaries = {}, {}
    for panel in PANELS:
        root = roots[panel]
        if root is None:
            report = dict(panel=panel, status='missing', jsonComplete=False,
                          counts=_observed_counts(None), strengthStatisticsReleased=False)
        else:
            try:
                report, summaries[panel] = _audit_panel(root, panel, integrity.get(panel))
            except (ValueError, OSError, KeyError, TypeError, OverflowError, RecursionError) as exc:
                report = dict(panel=panel, status='invalid-or-incomplete', jsonComplete=False,
                    error=str(exc), counts=_observed_counts(root), strengthStatisticsReleased=False)
        report['operationalStatus'] = statuses.get(panel, 'not-supplied')
        panels[panel] = report
    ready = all(panels[p]['status'] == 'complete-integrity-verified' for p in PANELS)
    if ready:
        # The same budget evidence must cover BOTH originals and any shared recovery.
        require(len({panels[p]['externalIntegrity']['jobBudgetEvidenceSha256'] for p in PANELS}) == 1,
                'Joint actual-job budget evidence required')
        require(len({panels[p]['integrityBinding']['sourceIdentitySha256'] for p in PANELS}) == 1,
                'Both panels require identical frozen source')
        # Full runtime evidence remains individually receipt-bound; cache sizes
        # and fresh-download metadata can differ without changing serving identity.
        require(len({task_hash(panels[p]['expectedModelProjection']) for p in PANELS}) == 1,
                'Both panels require identical decoded model/full-config identity')
        for panel in PANELS:
            panels[panel].update(summary=summaries[panel], strengthStatisticsReleased=True)
    return dict(schema='multimap-replica-stress-independent-audit-v1', panels=panels,
        status='complete-integrity-verified' if ready else 'incomplete-or-integrity-pending',
        bothPanelsComplete=all(p['jsonComplete'] for p in panels.values()),
        strengthStatisticsReleased=ready,
        primaryContrasts=({panel + ':' + replica + 'MinusPpo2':
                           '/panels/' + panel + '/summary/primary/' + replica + 'MinusPpo2'
                           for panel in PANELS for replica in POLICIES[:2]} if ready else None),
        counts=dict(games=sum(p['counts']['games'] for p in panels.values()),
                    batches=sum(p['counts']['batches'] for p in panels.values()),
                    scheduledGames=15360, scheduledIndependentDeals=1280,
                    sharedControlDuplicated=False),
        independentSeedRoots=True, bothPanelsRequired=True, automaticProgression=False,
        winnerSelection=False, pooledInference=False, caveats=list(CAVEATS), **FLAGS)


def audit_both(strong_root, mixed_root, *, integrity=None, statuses=None):
    return report_all(dict(strong=strong_root, mixed=mixed_root), integrity=integrity, statuses=statuses)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('strong_root')
    parser.add_argument('mixed_root')
    parser.add_argument('--integrity', type=Path, help='Separately authenticated external receipts; not self-attested JSON')
    args = parser.parse_args()
    result = audit_both(None if args.strong_root == '-' else args.strong_root,
                        None if args.mixed_root == '-' else args.mixed_root,
                        integrity=None if args.integrity is None else read(args.integrity))
    print(json.dumps(result, indent=2, allow_nan=False))
