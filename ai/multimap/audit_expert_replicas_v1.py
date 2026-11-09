"""Offline, independent reporting for BOTH expert-v2 training replicas.

API / snapshot contract
-----------------------
``audit_complete(root, replica, *, integrity=None)`` reads a FULL, unmodified
original or one-continuation final worker snapshot. ``root`` contains
artifacts.json (the worker's name -> SHA256 manifest), protocol.json, status.json,
environment.json, recovery.json and expert/{config,history,result}.json,
expert/{initial,warmup,best,last}.pt, the three *-plan.json files,
train-plan-{1..32}.json, warmup.json, train-{1..32}.json,
selection-{0,teacher,warmup,8,16,24,32}.json and
confirmation-{selected,teacher}.json. Exactly 88 manifest members, plus the
manifest itself; no extra/missing files, symlinks, temporary files or raw traces.
All outcomes must appear in canonical task order. File mtimes are NOT evidence.

No network, model loading, torch, training, game play, job operations or writes.
Only the hash-authenticated low-level outcome validator from audit_expert.py is
reused, in an isolated minimal namespace with NO old protocol/default scope.
Plans, summaries, selection and statistics are independently implemented here.

Trust boundary: a local manifest alone proves neither remote provenance nor
checkpoint contents/chronology. Confirmation-only resume may consume one extra
Torch RNG advance from constructing/loading the best model: the external audit
must reproduce that narrowly explained advance, NOT demand arbitrary final RNG
identity. No optimizer/model/evaluation change is allowed after selection.
Without ``integrity``, complete JSON is reported
as ``integrity-pending``, with expectedCheckpointProjection and hashes for an
external integrity auditor; NO strength statistics are emitted. Never manufacture
an integrity receipt from these expected values. A trusted caller may supply an
independently produced receipt (not an extra file inside the snapshot):

  schema: multimap-expert-replica-external-integrity-v1
  replica: integer 1 or 2
  manifestSha256: SHA256 of this snapshot's artifacts.json
  evidenceSha256: SHA256 of separately retained independent verification evidence
  checks: exactly EXTERNAL_CHECKS, each true
  finalCheckpoint: the JSON projection of last.pt described by
                   expectedCheckpointProjection (including actual tensor metadata)
  selectionCommit: {revision: immutable 40-hex commit, checkpointSha256: 64-hex,
                    projection: same projection, but result=null, confirmations={}}

The external auditor MUST authenticate immutable source/remote manifests, all
source/config/runtime/reference/model pins, initial zero-head/warm-start tensor
parity, actual initial/warmup/best/last tensor/config/optimizer/RNG transactions,
embedded best bytes, both committed confirmation hashes, and an authenticated
update-32 selection commit strictly BEFORE either confirmation. It must also
verify actual job chronology, maximum two segments, same-source exact resume,
no rerun/replacement after observing success, and source/model provenance.
``inheritedCommittedOutputsUnchanged`` requires inspecting the authenticated
original snapshot's last.pt stage/update/confirmations to establish the committed
boundary, then verifying that all inherited committed immutable outputs retain
exact bytes. An uploaded failed snapshot may also contain uncommitted outputs;
only those may be replayed/overwritten on continuation. The inherited manifest
alone cannot identify that boundary. Config and initial.pt always retain exact
bytes and are also checked locally. The receipt is a caller attestation, NOT a
cryptographic proof generated here. This module checks its binding and projected
values; it never claims to inspect .pt.

``report_all({1: root_or_None, 2: root_or_None}, statuses=None, integrity=None)``
REQUIRES both IDs, never excludes failures/fallbacks, and emits fold summaries
only when BOTH independent audits and external checks pass. Optional statuses
is an ID -> operational status mapping; integrity is ID -> receipt. Operational
status never upgrades a snapshot. Partial/failed roots get explicit observed
counts (unverified, not strength estimates). No pooled inference, winner choice,
new qualification, transfer claim or success-dependent job replacement.
"""
import argparse
import ast
from collections import Counter, defaultdict
import copy
import hashlib
import itertools
import json
import math
from pathlib import Path
import re
import statistics

HERE = Path(__file__).resolve().parent
TRAIN_MAPS = ('Germany', 'USA', 'France', 'UK & Ireland')
PHASES = ('Auction', 'Resources', 'Building', 'Bureaucracy')
FROZEN = ('ppo0', 'ppo1', 'ppo2')
CONTROLLERS = ('learner', 'warmupExpert', 'reference', 'self', *FROZEN,
               'fixedV2', 'fixedV1', 'focalTeacher')
SEEDS = {1: 190731, 2: 827119}
STAGES = ('initial', 'warmup', '8', '16', '24', '32')
LIMIT = 134217728
HELPER_SHA256 = '0755762b04c6d74b26a3e277780ef46a5be73b8c1407437fb3f8f385ef8d0f8e'
FROZEN_SOURCES = {
    'expert-protocol-v2.json': 'd9180c76ce072fe03fb1c325466d8d768a919d040ffd27229d4f375f61065796',
    'expert_ppo.py': '4357357fde973deff89d9df908622297ccce6fb89446c6e4cf314f20a5383bd0',
    'expert_rollout.py': '3deb6af55d5210caa04d02210a14bd3ff9c7af413afa2b39ef72bb3e3ebfb77e',
    'expert_game.cjs': '6d0580b5054e5fb18b5b872827796665125d9997dd31b720dfe2becb00369942',
    'expert_policy.py': '5304112f56195eec7aa6f89967503e6d08768be7ffb4fc232a7fcfe3349b4213',
    'job_expert.py': '58a1d8bfe189228f48a4f139e4b8727a58cdfd65d8efd0ff6a8d0e182c24a8cb',
    'teacher_v2.cjs': '89a5b6c9e8520224eeb1cb34d8543cfccb2d8313002626a50907d4fa996cbdf6',
    'economics_v2.cjs': 'dbb2216b3572e4afc882a3da11f683abd998a54b8672c7acda4843ee142d1897',
    'candidate-pool-v1.json': 'a4f5d80966d9dd5b7af712459dffea255590eeb158b3a8e73cb66b0045d29a4b',
}
COUNTS = dict(trainingGamesPerReplica=2720, selectionGamesPerReplica=2240,
              confirmationGamesPerArmPerReplica=640, confirmationDealRootsPerReplica=160,
              totalGamesPerReplica=6240, totalGames=12480)
ANALYSIS = dict(primary='selected-minus-teacher-v2', unit='paired-all-seat-deal',
               weighting='equal-80-map-count-rule-cells', dealsPerCell=2, normal95Z=1.96,
               pooledInference=False, winnerSelection=False,
               betweenReplicaSpread='descriptive-includes-evaluation-noise')
EXTERNAL_CHECKS = (
    'immutableRemoteManifestAndSource', 'completeServingConfigAndRuntime',
    'referenceAndFrozenModelProvenance', 'initialZeroHeadAndWarmStartTensors',
    'checkpointModelOptimizerRngTransactions', 'embeddedBestBytesAndMetadata',
    'committedHistoryBaselineResultAndConfirmations', 'selectionStrictlyBeforeConfirmation',
    'boundedOriginalOrSameReplicaContinuation', 'inheritedCommittedOutputsUnchanged',
    'noSuccessDependentReplacement',
)
FLAGS = dict(qualified=False, qualificationEligible=False, reservedFinalSeedsUsed=False)
BASE_SOURCE_NAMES = (
    'expert-protocol-v2.json', 'expert_policy.py', 'expert_rollout.py', 'expert_game.cjs',
    'expert_ppo.py', 'job_expert.py', 'job_gap.py', 'job_neural.py', 'job.py', 'gap_study.py',
    'gap-protocol-v1.json', 'teacher_v2.cjs', 'economics_v2.cjs', 'teacher-repairs-v2.json',
    'features.cjs', 'teacher.cjs', 'game.cjs', 'game_rl.cjs', 'model.py', 'residual.py',
    'candidates.py', 'candidate-pool-v1.json', 'ppo-protocol-v1.json', 'data.py', 'protocol.json',
    'reference_evaluate.py', 'reference_recover.py', 'reference_game.cjs', 'neural_study.py',
    'neural-study-v1.json', 'requirements-cpu.txt',
)
REPLICA_SOURCE_NAMES = (
    'expert-replicas-protocol-v1.json', 'expert_replicas_v1.py', 'replica_game_v1.cjs',
    'replica_protocol_v1.cjs', 'job_expert_replicas_v1.py', 'test_expert_replicas_v1.py',
    'launch_expert_replicas_v1.py', 'test_launch_expert_replicas_v1.py',
    'preflight_expert_replicas_v1.py', 'test_preflight_expert_replicas_v1.py',
)
ROOT_SOURCE_NAMES = ('ai/core.cjs', 'ai/strong/economics.cjs', 'ai/requirements-serve.txt',
                     'engine/package.json', 'engine/pnpm-lock.yaml')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def exact(actual, expected, label):
    require(canonical(actual) == canonical(expected), label)


def finite(value, low=-math.inf, high=math.inf):
    return type(value) in (int, float) and math.isfinite(value) and low <= value <= high


def integer(value, low=0, high=100000):
    return type(value) is int and low <= value <= high


def equal_summary(actual, expected, label):
    """Strict schemas/types; roundoff tolerance ONLY for genuine float metrics."""
    if type(expected) is dict:
        require(type(actual) is dict and actual.keys() == expected.keys(), label + ': keys')
        for key, value in expected.items():
            equal_summary(actual[key], value, label + '.' + key)
    elif type(expected) is float:
        require(finite(actual) and math.isclose(actual, expected, rel_tol=1e-12, abs_tol=1e-12), label)
    else:
        exact(actual, expected, label)


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def read(path):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, 'Duplicate JSON key')
            result[key] = value
        return result
    path = Path(path)
    require(path.is_file() and not path.is_symlink() and path.stat().st_size <= LIMIT,
            'Missing/unsafe/oversized JSON file: ' + path.name)
    def number(text):
        value = float(text)
        require(math.isfinite(value), 'Nonfinite JSON number')
        return value
    return json.loads(path.read_text(), object_pairs_hook=pairs, parse_float=number,
                      parse_constant=lambda _: require(False, 'Nonfinite JSON'))


def hash_string(value, size=64):
    return type(value) is str and re.fullmatch('[0-9a-f]{' + str(size) + '}', value) is not None


def replica_id(replica):
    require(type(replica) is int and replica in SEEDS, 'Replica must be integer 1 or 2')
    return replica


def namespace(replica):
    return 'pg-multimap-expert-replicas-v1-r' + str(replica_id(replica))


def study_protocol():
    study = read(HERE / 'expert-replicas-protocol-v1.json')
    critical = dict(schema='multimap-expert-replicas-v1', baseProtocol='expert-protocol-v2.json',
        frozenSources=FROZEN_SOURCES,
        replicas=[dict(id=i, seed=SEEDS[i], seedNamespace=namespace(i)) for i in (1, 2)],
        transferMaps=[], qualificationEligible=False, reservedFinalSeedsUsed=False,
        counts=COUNTS, analysis=ANALYSIS,
        budget=dict(replicas=2, workers=6, flavor='cpu-upgrade', timeout='3h', maxSegmentsPerReplica=2,
                    maxTotalJobHours=12, studyArtifactMaxBytes=LIMIT,
                    localStorageMaxBytes=8589934592, minimumFreeBytes=2147483648))
    require(type(study) is dict and study.keys() == critical.keys() | {'selection', 'evaluation', 'reporting', 'resume'},
            'Replica protocol fields')
    exact({k: study[k] for k in critical}, critical, 'Replica protocol critical pins/analysis/counts')
    require(all(type(study[k]) is str and study[k] for k in ('selection', 'evaluation', 'reporting', 'resume')),
            'Replica protocol documentation')
    return study


def protocol_for(replica):
    replica_id(replica)
    study_protocol()
    path = HERE / 'expert-protocol-v2.json'
    require(digest(path) == FROZEN_SOURCES[path.name], 'Frozen base protocol hash')
    protocol = read(path)
    return dict(protocol, seed=SEEDS[replica], seedNamespace=namespace(replica), transferMaps=[])


def _outcome_helper(path=HERE / 'audit_expert.py'):
    """Load ONLY authenticated validator constants/functions, never old scope."""
    source = Path(path).read_bytes()
    require(hashlib.sha256(source).hexdigest() == HELPER_SHA256, 'Outcome helper hash changed')
    functions = {'require', 'canonical', 'finite', 'integer', 'validate_outcome'}
    constants = {'PHASES', 'FROZEN', 'CONTROLLERS', 'TIMINGS', 'FIELDS'}
    nodes, found = [], set()
    for node in ast.parse(source).body:
        if isinstance(node, ast.FunctionDef) and node.name in functions:
            nodes.append(node); found.add(node.name)
        elif isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            if node.targets[0].id in constants:
                nodes.append(node); found.add(node.targets[0].id)
    require(found == functions | constants, 'Authenticated helper function set')
    scope = dict(math=math, json=json)
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(path), 'exec'), scope)
    require('NAMESPACE' not in scope and 'PROTOCOL' not in scope and 'expected_plan' not in scope,
            'No old protocol defaults in helper')
    return scope['validate_outcome']


validate_outcome = _outcome_helper()


def expected_plan(replica, split, update=0, teacher=False):
    replica_id(replica)
    require(split in ('warmup', 'train', 'selection', 'confirmation'), 'Unknown/reserved split')
    require(type(update) is int and (1 <= update <= 32 if split == 'train' else update == 0), 'Update namespace')
    require(type(teacher) is bool and (not teacher or split in ('selection', 'confirmation')), 'Teacher eval only')
    maps = ('Germany',) if split == 'warmup' else TRAIN_MAPS
    deals = 8 if split == 'warmup' else 2 if split == 'confirmation' else 1
    tasks = []
    for ci, (name, n, variant, fast) in enumerate(itertools.product(maps, range(2, 7), ('original', 'recharged'), (False, True))):
        cell = f'{name}|{n}|{variant}|{int(fast)}'
        for deal in range(deals):
            seats = [(ci + deal) % n] if split == 'warmup' else [(ci + update - 1) % n] if split == 'train' else range(n)
            for focal in seats:
                reference = name == 'Germany' and (split != 'train' or (ci + update) % 2 == 0)
                opponents, ordinal = [], 0
                for seat in range(n):
                    if seat == focal:
                        opponents.append('learner')
                    elif reference:
                        opponents.append('reference')
                    else:
                        pool = (*FROZEN, 'self') if split == 'train' else FROZEN
                        offset = update + ordinal if split == 'train' else seat
                        opponents.append(pool[(ci + deal + offset) % len(pool)])
                        ordinal += 1
                task = dict(map=name, players=n, variant=variant, fastBid=fast, cell=cell, split=split,
                    update=update, deal=deal, focalSeat=focal, smoke=False, maxSteps=4000,
                    seed=f'{namespace(replica)}:{split}:{update}:{cell}:{deal}',
                    opponentMode='reference' if reference else 'mixed', opponents=opponents)
                if teacher:
                    task['focalTeacher'] = True
                tasks.append(task)
    return tasks


def schedules(replica):
    records = {'warmup.json': expected_plan(replica, 'warmup')}
    records.update({f'train-{u}.json': expected_plan(replica, 'train', u) for u in range(1, 33)})
    records.update({f'selection-{s}.json': expected_plan(replica, 'selection', teacher=s == 'teacher')
                    for s in ('0', 'teacher', 'warmup', '8', '16', '24', '32')})
    records.update({f'confirmation-{s}.json': expected_plan(replica, 'confirmation', teacher=s == 'teacher')
                    for s in ('selected', 'teacher')})
    return records


def expected_names():
    names = {'protocol.json', 'environment.json', 'recovery.json', 'status.json'}
    names |= {'expert/' + n for n in ('config.json', 'history.json', 'result.json',
        'initial.pt', 'warmup.pt', 'best.pt', 'last.pt', 'warmup-plan.json', 'selection-plan.json', 'confirmation-plan.json')}
    names |= {'expert/' + n for n in schedules(1)}
    names |= {f'expert/train-plan-{u}.json' for u in range(1, 33)}
    require(len(names) == 88, 'Auditor full snapshot file count')
    return names


def compact_json(value, parent=None):
    forbidden = {'observation', 'observations', 'trace', 'trajectories', 'actions', 'request',
                 'state_dict', 'response', 'state', 'move', 'rows', 'trajectory'}
    if type(value) is dict:
        for key, child in value.items():
            require(key not in forbidden or (key == 'rows' and parent == 'optimization' and integer(child)),
                    'Raw decision/trajectory JSON forbidden')
            compact_json(child, key)
    elif type(value) is list:
        for child in value:
            compact_json(child)


def verify_manifest(root):
    root = Path(root)
    require(root.is_dir() and not any(p.is_symlink() for p in (root, *root.parents)), 'Unsafe snapshot root')
    paths = list(root.rglob('*'))
    require(not any(p.is_symlink() for p in paths), 'Snapshot symlink')
    require(all(p.is_file() or p.is_dir() for p in paths), 'Special snapshot file')
    require({p.relative_to(root).as_posix() for p in paths if p.is_dir()} == {'expert'}, 'Unexpected snapshot directory')
    require({p.relative_to(root).as_posix() for p in paths if p.is_file()} == expected_names() | {'artifacts.json'},
            'Full snapshot missing/extra files')
    total = sum(p.stat().st_size for p in paths if p.is_file())
    require(total <= LIMIT, 'Snapshot exceeds 128 MiB')
    manifest = read(root / 'artifacts.json')
    require(type(manifest) is dict and manifest.keys() == expected_names(), 'Exact manifest names')
    require(all(hash_string(v) for v in manifest.values()), 'Manifest SHA256 type')
    for name, checksum in manifest.items():
        require(digest(root / name) == checksum, 'Manifest content mismatch: ' + name)
        if name.endswith('.json'):
            compact_json(read(root / name))
    return manifest, total


def verify_outcomes(rows, tasks):
    require(type(rows) is list and len(rows) == len(tasks), 'Missing/extra outcomes')
    keys = set()
    for row, task in zip(rows, tasks):
        require(type(row) is dict and type(row.get('spec')) is dict, 'Outcome object/schema')
        # The full spec equality also rejects reordered outcomes, bool-as-int,
        # cross-replica, old/smoke/final namespaces and altered opponent assignments.
        validate_outcome(row, task)
        key = task['seed'], task['focalSeat']
        require(key not in keys, 'Duplicate scheduled outcome')
        keys.add(key)
    return rows


def summary(rows):
    require(rows, 'Empty summary')
    cells = defaultdict(list)
    for row in rows:
        require(finite(row['credit'], 0, 1), 'Summary credit')
        cells[row['spec']['cell']].append(row['credit'])
    means = {c: float(statistics.mean(v)) for c, v in cells.items()}
    maps = {m: float(statistics.mean(v for c, v in means.items() if c.split('|')[0] == m))
            for m in sorted({c.split('|')[0] for c in means})}
    return dict(games=len(rows), failures=0, macroCredit=float(statistics.mean(maps.values())), maps=maps, cells=means)


def eligible(candidate, baseline):
    if (type(candidate.get('failures')) is not int or candidate['failures'] != 0 or
            set(candidate.get('maps', {})) != set(TRAIN_MAPS) or not finite(candidate.get('macroCredit'), 0, 1)):
        return False
    return all(finite(candidate['maps'][m], 0, 1) and
               candidate['maps'][m] >= baseline['maps'][m] - (0 if m == 'Germany' else .05) - 1e-12
               for m in TRAIN_MAPS)


def choose_selection(stages):
    require([stage for stage, _ in stages] == list(STAGES), 'Only ordered scheduled selection stages')
    baseline = stages[0][1]
    require(eligible(baseline, baseline), 'Invalid teacher fallback')
    best, score, decisions = 'initial', baseline['macroCredit'], []
    for stage, candidate in stages:
        ok = eligible(candidate, baseline)
        if ok and candidate['macroCredit'] > score + 1e-12:
            best, score = stage, candidate['macroCredit']
        decisions.append(dict(stage=stage, eligible=ok, macroCredit=candidate['macroCredit'],
                              maps=candidate['maps'], bestSoFar=best))
    return best, score, decisions


def initial_parity(initial, teacher):
    require(len(initial) == len(teacher) and initial, 'Initial parity coverage')
    for left, right in zip(initial, teacher):
        exact(left['spec'], {k: v for k, v in right['spec'].items() if k != 'focalTeacher'}, 'Initial parity task/order')
        require(right['spec'].get('focalTeacher') is True, 'Teacher parity arm')
        for field in ('terminal', 'credit', 'allSeatCredit', 'steps', 'rounds',
                      'referenceRequests', 'expertRequests', 'expertCounts'):
            exact(left[field], right[field], 'Initial terminal parity: ' + field)
        for actor in ('reference', 'fixedV1', 'warmupExpert', 'self', *FROZEN):
            exact(left['counts'][actor], right['counts'][actor], 'Initial nonfocal routing parity')
        for phase in PHASES:
            require(left['counts']['learner'][phase] + left['counts']['fixedV2'][phase] ==
                    right['counts']['focalTeacher'][phase], 'Initial focal routing parity')


def stratified_estimate(strata):
    require(type(strata) is dict and strata and all(len(v) == 2 and all(finite(x, -1, 1) for x in v)
                                                   for v in strata.values()), 'Exactly two independent deals per cell')
    count = len(strata)
    mean = statistics.mean(statistics.mean(v) for v in strata.values())
    variance = math.fsum(statistics.variance(v) / 2 for v in strata.values()) / count**2
    se = math.sqrt(variance)
    return dict(mean=mean, standardError=se, approximateNormal95=[mean - 1.96*se, mean + 1.96*se],
                cells=count, independentDeals=2*count)


def deal_table(rows):
    groups = defaultdict(dict)
    for row in rows:
        s = row['spec']; cell = s['cell']; parts = cell.split('|')
        require(len(parts) == 4 and parts[0] in TRAIN_MAPS and parts[1] in ('2', '3', '4', '5', '6') and
                parts[2] in ('original', 'recharged') and parts[3] in ('0', '1'), 'Cell namespace')
        require(type(s['deal']) is int and s['deal'] in (0, 1) and
                type(s['focalSeat']) is int and 0 <= s['focalSeat'] < int(parts[1]), 'Deal/seat types')
        group = groups[cell, s['deal']]
        require(s['focalSeat'] not in group and finite(row['credit'], 0, 1), 'Duplicate seat or invalid credit')
        group[s['focalSeat']] = row['credit']
    result = {}
    for (cell, deal), seats in groups.items():
        require(set(seats) == set(range(int(cell.split('|')[1]))), 'Incomplete all-seat deal cluster')
        result[cell, deal] = statistics.mean(seats.values())
    return result


def statistics_report(selected, teacher):
    require(type(selected) is list and type(teacher) is list and len(selected) == len(teacher) == 640,
            'Two complete confirmation arms')
    seed = selected[0].get('spec', {}).get('seed') if type(selected[0]) is dict else None
    match = re.match(r'^pg-multimap-expert-replicas-v1-r([12]):confirmation:', seed) if type(seed) is str else None
    require(match is not None, 'Fresh replica confirmation namespace required for statistics')
    replica = int(match.group(1))
    verify_outcomes(selected, expected_plan(replica, 'confirmation'))
    verify_outcomes(teacher, expected_plan(replica, 'confirmation', teacher=True))
    for left, right in zip(selected, teacher):
        require(left['spec']['split'] == right['spec']['split'] == 'confirmation' and
                'focalTeacher' not in left['spec'] and right['spec'].get('focalTeacher') is True,
                'Confirmation selected/teacher arms')
        exact(left['spec'], {k: v for k, v in right['spec'].items() if k != 'focalTeacher'},
              'Paired identical roots/opponents/all seats; no cross-replica pairing')
    a, b = deal_table(selected), deal_table(teacher)
    cells = sorted({s['cell'] for s in expected_plan(1, 'confirmation')})
    require(set(a) == set(b) == set(itertools.product(cells, (0, 1))), 'Full paired 80-cell/160-deal grid')
    subsets = {'macro': cells}
    subsets.update({'map:' + m: [c for c in cells if c.split('|')[0] == m] for m in TRAIN_MAPS})
    subsets.update({'players:' + str(n): [c for c in cells if int(c.split('|')[1]) == n] for n in range(2, 7)})
    subsets.update({'rule:' + v + '|' + str(f): [c for c in cells if c.split('|')[2:] == [v, str(f)]]
                    for v in ('original', 'recharged') for f in (0, 1)})
    subsets.update({'mapPlayers:' + m + '|' + str(n): [c for c in cells if c.split('|')[:2] == [m, str(n)]]
                    for m in TRAIN_MAPS for n in range(2, 7)})
    subsets.update({'cell:' + c: [c] for c in cells})
    out = {}
    for label, subset in subsets.items():
        out[label] = dict(selected=stratified_estimate({c: [a[c, d] for d in (0, 1)] for c in subset}),
            teacherV2=stratified_estimate({c: [b[c, d] for d in (0, 1)] for c in subset}),
            pairedDifference=stratified_estimate({c: [a[c, d] - b[c, d] for d in (0, 1)] for c in subset}),
            gamesPerArm=sum(2*int(c.split('|')[1]) for c in subset))
    return dict(analysis=copy.deepcopy(ANALYSIS), subsets=out,
        cellDealMeans={c: dict(selected=[a[c, d] for d in (0, 1)], teacherV2=[b[c, d] for d in (0, 1)]) for c in cells},
        method='Average all seats within each paired deal, then two deals per fixed cell, then equal cell weights. '
               'SE=sqrt(sum_c unbiased_sample_variance(delta_c)/2 / C^2); approximate normal 95% = mean +/-1.96 SE.',
        caveats=['Conditional on each selected checkpoint and fixed opponents; two deals per cell give noisy variance estimates.',
                 'Map/count/rule/mapPlayers/cell intervals are descriptive, unadjusted multiple comparisons.',
                 'Germany uses exact reference; other maps use fixed PPO0/1/2. No Italy/Benelux transfer observations.',
                 'No significance gate, promotion, deployment, qualification or winner selection.'])


def _safe_hash_map(value, label):
    require(type(value) is dict and value, label)
    require(all(type(k) is str and k and not k.startswith('/') and '..' not in k.split('/') and hash_string(v)
                for k, v in value.items()), label)


def validate_identity(root, replica, protocol, manifest):
    config, status = read(root / 'expert/config.json'), read(root / 'status.json')
    config_keys = {'schema', 'replica', 'protocol', 'replicaStudy', 'smoke', 'generatorDigest', 'sourceFiles',
                   'engineDependencies', 'referenceSourceFiles', 'referenceManifestSha256', 'referenceFiles',
                   'runtimeVersions', 'execution', 'sourcePins'}
    require(type(config) is dict and config.keys() == config_keys, 'Exact replica config schema')
    exact(config['schema'], 'multimap-expert-replica-identity-v1', 'Replica identity schema')
    exact(config['replica'], replica, 'Config replica')
    exact(config['protocol'], protocol, 'Config derived protocol')
    exact(config['replicaStudy'], study_protocol(), 'Config replica study')
    exact(config['smoke'], False, 'Full recipe only')
    exact(read(root / 'protocol.json'), protocol, 'Protocol artifact')
    exact(config['execution'], dict(workers=6, collector='thread-pool-lockstep-central-torch-with-child-processes',
          inferenceThreads=1, optimizerThreads=4, deterministicAlgorithms=True), 'Execution identity')
    exact(config['sourcePins'], dict(warmStart=protocol['warmStart'], opponents=protocol['opponentPool'],
                                   reference=protocol['reference']), 'Frozen model/reference pins')
    require(hash_string(config['generatorDigest']), 'Generator identity')
    _safe_hash_map(config['sourceFiles'], 'Source file hashes')
    for name, value in FROZEN_SOURCES.items():
        exact(config['sourceFiles'].get('ai/multimap/' + name), value, 'Frozen source: ' + name)
    exact(config['sourceFiles'].get('ai/multimap/expert-replicas-protocol-v1.json'),
          digest(HERE / 'expert-replicas-protocol-v1.json'), 'Study protocol source hash')
    sources = config['sourceFiles']
    engine_names = {n for n in sources if n.startswith('engine/dist/') and n.endswith('.js')}
    require(len(engine_names) == 42, 'All 42 compiled engine source identities')
    require(set(sources) == engine_names | set(ROOT_SOURCE_NAMES) |
            {'ai/multimap/' + n for n in (*BASE_SOURCE_NAMES, *REPLICA_SOURCE_NAMES)}, 'Complete serving source identity names')
    generator_names = engine_names | {'ai/core.cjs', 'ai/strong/economics.cjs'} | {
        'ai/multimap/' + n for n in ('features.cjs', 'game.cjs', 'teacher.cjs', 'protocol.json')}
    generator_digest = hashlib.sha256(json.dumps({n: sources[n] for n in generator_names}, sort_keys=True).encode()).hexdigest()
    exact(config['generatorDigest'], generator_digest, 'Recomputed generator source digest')
    exact(sources['ai/requirements-serve.txt'], protocol['referenceRequirementsSha256'], 'Reference requirements source pin')
    _safe_hash_map(config['referenceSourceFiles'], 'Reference source identities')
    require(config['referenceManifestSha256'] == protocol['reference']['runtimeManifestSha256'] and
            integer(config['referenceFiles'], 1, 1000000), 'Complete reference manifest identity')
    require(type(config['engineDependencies']) is dict and config['engineDependencies'], 'Engine dependency identities')
    for item in config['engineDependencies'].values():
        require(type(item) is dict and set(item) == {'files', 'sha256'} and
                integer(item['files'], 1) and hash_string(item['sha256']), 'Engine dependency identity')
    versions = config['runtimeVersions']
    require(type(versions) is dict and set(versions) == {'candidate', 'reference', 'node'} and
            type(versions['node']) is str and versions['node'], 'Runtime versions schema')
    for role, fields in (('candidate', {'python', 'numpy', 'torch', 'huggingface-hub'}),
                         ('reference', {'python', 'numpy', 'onnxruntime'})):
        v = versions[role]
        require(type(v) is dict and set(v) == fields and type(v['python']) is list and len(v['python']) == 3 and
                all(integer(x, 0, 100) for x in v['python']) and
                all(type(v[k]) is str and v[k] for k in fields - {'python'}), 'Runtime version types')
    environment = read(root / 'environment.json')
    require(type(environment) is dict and set(environment) == {'versions', 'referenceVenvBytes', 'requirementsSha256'},
            'Environment schema')
    exact(environment['versions'], versions, 'Environment runtime identity')
    require(environment['requirementsSha256'] == protocol['referenceRequirementsSha256'] and
            integer(environment['referenceVenvBytes'], 1, protocol['referenceVenvMaxBytes']), 'Environment budget/pin')
    recovery = read(root / 'recovery.json')
    expected = dict(schema='multimap-phase-gap-recovery-v1',
        pins=dict(source=protocol['reference']['sourcePin'], model=protocol['reference']['modelPin']),
        runtimeManifestSha256=protocol['reference']['runtimeManifestSha256'], policySha256=protocol['reference']['policySha256'],
        locallyVerifiedFiles=config['referenceFiles'], omitted=[], exactServiceReady=True,
        diskBudgetBytes=protocol['referenceCacheMaxBytes'], modelSha256=protocol['reference']['modelSha256'],
        recoveryMode='complete-unchanged-manifest-no-candidate-fetch', reserved_final_seeds_used=False)
    require(type(recovery) is dict and set(recovery) == expected.keys() | {'cacheBytes', 'sourceDownload'}, 'Recovery schema')
    exact({k: recovery[k] for k in expected}, expected, 'Recovery reference pins/counts')
    require(integer(recovery['cacheBytes'], 1, protocol['referenceCacheMaxBytes']) and
            (recovery['sourceDownload'] is None or type(recovery['sourceDownload']) is dict), 'Recovery budget/download metadata')
    required = {'run', 'workflow', 'protocol', 'smoke', 'workers', 'sourceRevision', 'sourceSha256', 'sourcePath',
                'sourceRepo', *FLAGS, 'stage', 'receipts', 'checkpointBytes', 'result'}
    require(type(status) is dict and set(status) in (required, required | {'resume'}), 'Exact complete status schema')
    for name, value in dict(workflow='expert', protocol=protocol, smoke=False, workers=6, stage='complete', **FLAGS).items():
        exact(status[name], value, 'Final status: ' + name)
    require(hash_string(status['sourceRevision'], 40) and hash_string(status['sourceSha256']) and
            type(status['sourcePath']) is str and status['sourcePath'] and type(status['sourceRepo']) is str and status['sourceRepo'],
            'Immutable source status identity')
    require(type(status['checkpointBytes']) is list and len(status['checkpointBytes']) == 4 and
            all(integer(x, 1, 16*1024**2) for x in status['checkpointBytes']), 'Bounded four model metadata sizes')
    run = status['run']; suffix = '-r' + str(replica)
    require(type(run) is str and re.fullmatch('[A-Za-z0-9_-]+', run) and
            run.endswith(suffix) and len(run) > len(suffix), 'Replica run namespace')
    resumed = 'resume' in status
    if resumed:
        resume = status['resume']
        require(type(resume) is dict and set(resume) == {'run', 'revision', 'files'} and
                type(resume['run']) is str and resume['run'].endswith(suffix) and
                not resume['run'][:-len(suffix)].endswith('-continuation') and
                run == resume['run'][:-len(suffix)] + '-continuation' + suffix and
                hash_string(resume['revision'], 40), 'One same-replica continuation')
        _safe_hash_map(resume['files'], 'Inherited manifest')
        require({'expert/config.json', 'expert/initial.pt', 'expert/last.pt'} <= resume['files'].keys() <=
                {n for n in manifest if n.startswith('expert/')}, 'Inherited transaction file scope')
        # Uploads can contain train/selection/confirmation (even warmup.pt)
        # written before last.pt commits them. Exact resume can rewrite those
        # bytes, including outcome timings. Only the external auditor of the
        # original last.pt can establish which outputs were already committed.
        for name in ('expert/config.json', 'expert/initial.pt'):
            require(manifest[name] == resume['files'][name], 'Inherited immutable artifact changed: ' + name)
    else:
        require(not run[:-len(suffix)].endswith('-continuation'), 'Original cannot be a continuation')
    receipts = status['receipts']
    require(type(receipts) is list and all(type(r) is dict and set(r) == {'stage', 'revision'} and
            hash_string(r['revision'], 40) for r in receipts), 'Immutable upload receipt schema')
    require(len({r['revision'] for r in receipts}) == len(receipts), 'Duplicate upload revisions')
    labels = [r['stage'] for r in receipts]
    # Trainer commit('complete') uploads once; the worker uploads again after
    # receiving result. Each upload serializes earlier receipts, so final status
    # contains exactly one complete receipt (not two).
    schedule = ['initial', 'warmup', *('update-' + str(i) for i in range(1, 33)),
                'confirmation-selected', 'confirmation-teacher', 'complete']
    require(labels and labels[0] == 'runtime-ready', 'Runtime-ready receipt first')
    if resumed:
        require(len(labels) >= 2 and labels[1] in schedule and labels[1:] == schedule[schedule.index(labels[1]):],
                'Continuation receipt schedule must be a strict contiguous suffix')
    else:
        exact(labels, ['runtime-ready', *schedule], 'Original chronological receipt schedule')
    return config, status


def validate_optimization(metrics, rows, update):
    common = {'rows', 'expertRows', 'optimizerSteps', 'loss', 'value', 'expertCE', 'gradNorm'}
    keys = common | ({'earlyStopped', 'expertCoefficient', 'actor', 'entropy', 'approxKl'} if update else {'epochs'})
    require(type(metrics) is dict and set(metrics) == keys, 'Optimization metric schema')
    require(integer(metrics['rows'], 1) and metrics['rows'] == sum(r['decisions'] for r in rows) and
            integer(metrics['expertRows']) and metrics['expertRows'] == sum(r['expertRequests'] for r in rows),
            'Optimization decisions/labels totals')
    require(integer(metrics['optimizerSteps'], 1), 'Integer optimizer step count')
    for key in keys - {'earlyStopped'}:
        require(finite(metrics[key]), 'Finite optimization metrics')
    require(all(metrics[k] >= 0 for k in ('value', 'expertCE', 'gradNorm')), 'Nonnegative optimization metrics')
    batches = math.ceil(metrics['rows'] / 64)
    if update:
        require(type(metrics['earlyStopped']) is bool and metrics['optimizerSteps'] <= 4*batches and
                (metrics['earlyStopped'] or metrics['optimizerSteps'] == 4*batches), 'PPO fixed four epochs / early-stop bound')
        require(metrics['entropy'] >= 0, 'Nonnegative entropy')
        equal_summary(metrics['expertCoefficient'], .5*.97**(update - 1), 'Expert coefficient decay')
    else:
        exact(metrics['epochs'], 24, 'Warmup fixed 24 epochs')
        require(metrics['optimizerSteps'] == 24*batches, 'Warmup optimizer steps')


def _external_gate(receipt, replica, manifest_sha, expected, selection_revision=None):
    require(type(receipt) is dict and set(receipt) == {'schema', 'replica', 'manifestSha256', 'evidenceSha256',
            'checks', 'finalCheckpoint', 'selectionCommit'}, 'External integrity receipt schema')
    exact(receipt['schema'], 'multimap-expert-replica-external-integrity-v1', 'External receipt version')
    exact(receipt['replica'], replica, 'External receipt replica')
    exact(receipt['manifestSha256'], manifest_sha, 'External receipt snapshot binding')
    require(hash_string(receipt['evidenceSha256']), 'External retained evidence hash')
    exact(receipt['checks'], dict.fromkeys(EXTERNAL_CHECKS, True), 'All external integrity checks required')
    equal_summary(receipt['finalCheckpoint'], expected, 'Actual final committed checkpoint projection')
    commit = receipt['selectionCommit']
    require(type(commit) is dict and set(commit) == {'revision', 'checkpointSha256', 'projection'} and
            hash_string(commit['revision'], 40) and hash_string(commit['checkpointSha256']), 'Preconfirmation commit identity')
    require(commit['checkpointSha256'] != expected['lastSha256'], 'Selection evidence must predate final transaction')
    if selection_revision is not None:
        exact(commit['revision'], selection_revision, 'Selection evidence must bind recorded update-32 upload')
    before = dict(expected, confirmations={}, result=None, lastSha256=commit['checkpointSha256'])
    equal_summary(commit['projection'], before, 'Actual preconfirmation selection checkpoint projection')


def audit_complete(root, replica, *, integrity=None):
    """Reject invalid complete snapshots; pending external checks suppress inference."""
    replica_id(replica)
    root = Path(root)
    protocol = protocol_for(replica)
    manifest, total = verify_manifest(root)
    config, status = validate_identity(root, replica, protocol, manifest)
    history = read(root / 'expert/history.json')
    require(type(history) is list and len(history) == 33, 'Single full 33-stage history')
    plans = {'warmup-plan.json': expected_plan(replica, 'warmup'),
             'selection-plan.json': expected_plan(replica, 'selection'),
             'confirmation-plan.json': expected_plan(replica, 'confirmation')}
    plans.update({f'train-plan-{u}.json': expected_plan(replica, 'train', u) for u in range(1, 33)})
    for name, tasks in plans.items():
        exact(read(root / 'expert' / name), tasks, 'Independent canonical ordered plan: ' + name)
    records, summaries = {}, {}
    for name, tasks in schedules(replica).items():
        record = read(root / 'expert' / name)
        keys = {'games', 'optimization'} if name == 'warmup.json' else {'games'} if name.startswith('train-') else {'games', 'summary'}
        require(type(record) is dict and set(record) == keys, 'Outcome file schema: ' + name)
        verify_outcomes(record['games'], tasks)
        score = summary(record['games'])
        if 'summary' in record:
            equal_summary(record['summary'], score, 'Independent summary: ' + name)
        records[name], summaries[name] = record, score
    for u, h in enumerate(history):
        selected = u == 0 or u % 8 == 0
        require(type(h) is dict and set(h) == {'stage', 'update', 'training', 'optimization'} | ({'selection'} if selected else set()),
                'History schema / scheduled selection only')
        exact(h['stage'], 'train' if u else 'warmup', 'Ordered history stage')
        exact(h['update'], u, 'Ordered history update')
        name = f'train-{u}.json' if u else 'warmup.json'
        equal_summary(h['training'], summaries[name], 'Training history summary')
        validate_optimization(h['optimization'], records[name]['games'], u)
        if not u:
            equal_summary(h['optimization'], records[name]['optimization'], 'Warmup file/history optimization')
        if selected:
            equal_summary(h['selection'], summaries[f'selection-{u if u else "warmup"}.json'], 'Scheduled history selection')
    initial_parity(records['selection-0.json']['games'], records['selection-teacher.json']['games'])
    stages = [(s, summaries[f'selection-{"0" if s == "initial" else s}.json']) for s in STAGES]
    best, score, decisions = choose_selection(stages)
    best_stage, best_update = (best, 0) if best in ('initial', 'warmup') else ('train', int(best))
    confirmations = {label: summaries[f'confirmation-{label}.json'] for label in ('selected', 'teacher')}
    result = read(root / 'expert/result.json')
    expected_result = dict(selectedUpdate=best_update, selectedStage=best_stage, selectionScore=score,
        baselineSelectionScore=stages[0][1]['macroCredit'], confirmation=confirmations, trainedUpdates=32,
        warmupEpochs=24, smoke=False, **FLAGS,
        note='Fresh-root expert/PPO experiment. Teacher-v2 baseline is an eligible fallback; confirmation never selects.')
    equal_summary(result, expected_result, 'Independently selected earliest eligible final result')
    equal_summary(status['result'], expected_result, 'Status result')
    training = [r for name, record in records.items() if name == 'warmup.json' or name.startswith('train-') for r in record['games']]
    selection = [r for name, record in records.items() if name.startswith('selection-') for r in record['games']]
    selected_rows, teacher_rows = [records[f'confirmation-{label}.json']['games'] for label in ('selected', 'teacher')]
    roots = [{r['spec']['seed'] for r in rows} for rows in (training, selection, selected_rows)]
    require([len(r) for r in roots] == [2720, 80, 160] and
            all(not a & b for a, b in itertools.combinations(roots, 2)), 'Fresh disjoint training/selection/confirmation roots')
    all_rows = training + selection + selected_rows + teacher_rows
    require(len(training) == 2720 and len(selection) == 2240 and len(all_rows) == 6240, 'Full 6240-outcome schedule')
    expected_checkpoint = dict(stage='train', update=32, bestStage=best_stage, bestUpdate=best_update,
        bestScore=score, baseline=stages[0][1], history=history, result=result,
        config=config, width=64, bound=16, priorAsActionFeature=True,
        bestSha256=manifest['expert/best.pt'], lastSha256=manifest['expert/last.pt'],
        confirmations={k: dict(summary=v, sha256=manifest[f'expert/confirmation-{k}.json']) for k, v in confirmations.items()})
    answer = dict(schema='multimap-expert-replica-json-audit-v1', replica=replica, seed=SEEDS[replica],
        seedNamespace=namespace(replica), run=status['run'], status='integrity-pending',
        jsonChecksPassed=True, allChecksPassed=False, strengthInferenceAvailable=False,
        **FLAGS, promoted=False, deployed=False, transferMaps=[],
        manifestSha256=digest(root / 'artifacts.json'), artifactFiles=len(manifest), artifactBytes=total,
        helperSha256=HELPER_SHA256, selectedStage=best_stage, selectedUpdate=best_update,
        teacherFallback=best_stage == 'initial', selection=dict(confirmationUsed=False, decisions=decisions),
        coverage=dict(savedTerminalOutcomes=len(all_rows), warmup=160, ppo=2560, training=2720,
            selectionAndControl=2240, confirmation=1280, confirmationPerArm=640,
            cells=80, confirmationDealRoots=160, trainingRoots=2720, selectionDealRoots=80,
            failures=0, missing=0, duplicateScheduledTasks=0, allSplitsDisjoint=True,
            freshGermanyExpertLabels=sum(r['expertRequests'] for r in training),
            zeroEvaluationExpertLabels=True, nonGermanyReferenceRequests=0,
            initialTeacherParityOutcomes=320,
            controllerPhases={actor: dict(sum((Counter(r['counts'][actor]) for r in all_rows), Counter())) for actor in CONTROLLERS},
            publicChecks=dict(sum((Counter(r['publicChecks']) for r in all_rows), Counter()))),
        externalChecksNeeded=list(EXTERNAL_CHECKS), expectedCheckpointProjection=expected_checkpoint,
        expectedSelectionRevision=next((r['revision'] for r in status['receipts'] if r['stage'] == 'update-32'), None),
        integrityTrustBoundary='JSON/manifest checks are local. Caller-supplied independent integrity evidence is required for tensor/provenance/chronology claims.')
    if integrity is not None:
        _external_gate(integrity, replica, answer['manifestSha256'], expected_checkpoint,
                       answer['expectedSelectionRevision'])
        answer.update(status='complete', allChecksPassed=True, strengthInferenceAvailable=True,
                      externalChecksNeeded=[], externalIntegrityEvidenceSha256=integrity['evidenceSha256'],
                      confirmationStatistics=statistics_report(selected_rows, teacher_rows))
    return answer


def partial_counts(root, replica):
    """Bounded inventory ONLY; never treats uncommitted/invalid rows as samples."""
    out = dict(expectedOutcomes=6240, observedRows=0, terminalTrueRows=0, nonterminalRows=0,
               errorRows=0, malformedRows=0, duplicateTaskRows=0, readableOutcomeFiles=0,
               missingOutcomeFiles=0, unreadableOutcomeFiles=0, verified=False)
    for name in schedules(replica):
        path = Path(root) / 'expert' / name
        if not path.exists():
            out['missingOutcomeFiles'] += 1
            continue
        try:
            record = read(path)
            require(type(record) is dict and type(record.get('games')) is list, 'Missing games list')
            rows = record['games']; out['readableOutcomeFiles'] += 1
            seen = set()
            for row in rows:
                out['observedRows'] += 1
                if type(row) is not dict:
                    out['malformedRows'] += 1
                    continue
                out['terminalTrueRows' if row.get('terminal') is True else 'nonterminalRows'] += 1
                out['errorRows'] += int('error' in row)
                spec = row.get('spec')
                if type(spec) is not dict or type(spec.get('seed')) is not str or type(spec.get('focalSeat')) is not int:
                    out['malformedRows'] += 1
                else:
                    key = spec['seed'], spec['focalSeat']
                    out['duplicateTaskRows'] += int(key in seen); seen.add(key)
        except (ValueError, OSError, TypeError):
            out['unreadableOutcomeFiles'] += 1
    out['observedRowsShortfall'] = max(0, 6240 - out['observedRows'])
    out['note'] = 'Inventory only, not a count of verified unique scheduled outcomes; partial retries/inherited files are not new samples.'
    return out


def _both_ids(mapping, label, complete):
    require(type(mapping) is dict and all(type(k) is int and k in (1, 2) for k in mapping) and
            (set(mapping) == {1, 2} if complete else set(mapping) <= {1, 2}), label + ': use explicit integer replica IDs 1 and 2')


def report_all(roots, statuses=None, *, integrity=None):
    """Never silently subset completed/successful replicas or select a winner."""
    _both_ids(roots, 'roots', True)
    statuses = {} if statuses is None else statuses
    integrity = {} if integrity is None else integrity
    _both_ids(statuses, 'statuses', False); _both_ids(integrity, 'integrity', False)
    require(all(type(v) is str and v for v in statuses.values()), 'Operational statuses must be nonempty strings')
    present = [Path(p).resolve() for p in roots.values() if p is not None]
    require(len(set(present)) == len(present), 'Replicas cannot share a snapshot root')
    reports = []
    for replica in (1, 2):
        root = roots[replica]; operational = statuses.get(replica)
        base = dict(replica=replica, seed=SEEDS[replica], seedNamespace=namespace(replica),
                    allChecksPassed=False, strengthInferenceAvailable=False, operationalStatus=operational, **FLAGS)
        if root is None or not Path(root).exists():
            reports.append(dict(base, status='absent', snapshotAvailable=False,
                observedCounts=partial_counts(Path('/__absent_replica_snapshot__'), replica)))
            continue
        try:
            stored = read(Path(root) / 'status.json')
            stage = stored.get('stage') if type(stored) is dict else None
            if stage != 'complete':
                reports.append(dict(base, status='failed' if stage == 'failed' else 'incomplete', recordedStage=stage,
                                    snapshotAvailable=True, observedCounts=partial_counts(root, replica)))
                continue
            audited = audit_complete(root, replica, integrity=integrity.get(replica))
            audited['operationalStatus'] = operational
            if operational and operational.upper() in {'ERROR', 'FAILED', 'CANCELED', 'CANCELLED', 'TIMEOUT', 'TIMED_OUT'}:
                # A failed segment/fallback is visible. Conflicting final completion
                # needs a separately reconciled integrity receipt, not strength claims.
                audited = dict(base, status='status-conflict', snapshotAvailable=True,
                               observedCounts=partial_counts(root, replica))
            reports.append(audited)
        except (ValueError, OSError, KeyError, TypeError, IndexError) as error:
            reports.append(dict(base, status='invalid' if (Path(root) / 'status.json').exists() else 'incomplete',
                snapshotAvailable=True, auditError=str(error), observedCounts=partial_counts(root, replica)))
    full = all(r['allChecksPassed'] for r in reports)
    result = dict(schema='multimap-expert-replicas-report-v1', analysis=copy.deepcopy(ANALYSIS),
        plannedCounts=copy.deepcopy(COUNTS), replicas=reports,
        statusCounts=dict(Counter(r['status'] for r in reports)), allReplicasComplete=full,
        strengthInferenceAvailable=full, **FLAGS, promoted=False, deployed=False,
        transferMaps=[], excludedReplicaIds=[], pooledInference=False, winnerSelection=False,
        originalSeedPooled=False,
        reportingPolicy='Both predeclared replicas, including failed/incomplete/teacher fallback. No replacement conditioned on success; no winner selection or new qualification.',
        limitations=['Original seed is historical context only; its different/unequal transfer panel is not pooled.',
                     'Two independent training runs share pretrained representation and opponents but have disjoint game/RNG namespaces.',
                     'Between-replica differences include training, checkpoint-selection-panel and confirmation-evaluation-panel randomness; not pure training variance. Roots are NOT paired between replicas.'])
    if full:
        subsets = reports[0]['confirmationStatistics']['subsets']
        fold = {}
        for name in subsets:
            values = [r['confirmationStatistics']['subsets'][name]['pairedDifference']['mean'] for r in reports]
            fold[name] = dict(replicaPairedMeans=values, mean=statistics.mean(values),
                              sampleStandardDeviation=statistics.stdev(values), minimum=min(values), maximum=max(values),
                              absoluteDifference=abs(values[1] - values[0]))
        result['betweenReplicaDescriptive'] = dict(replicas=2, includesEvaluationNoise=True,
            pooledInference=False, confidenceInterval=None, subsets=fold,
            note='Equal mean of the two independently selected-minus-teacher estimates; descriptive spread only. Spread includes training, checkpoint-selection-panel and evaluation-panel randomness, with no pairing between runs. No pooled SE, significance gate, ranking or zero-noise claim.')
    else:
        result['betweenReplicaDescriptive'] = None
        result['noAggregateReason'] = 'Both original-or-continued replicas must pass complete JSON AND independent external integrity checks; none is discarded.'
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--replica-1', type=Path)
    parser.add_argument('--replica-2', type=Path)
    args = parser.parse_args()
    # Intentionally stdout-only and no CLI shortcut to self-attest external checks.
    print(json.dumps(report_all({1: args.replica_1, 2: args.replica_2}), indent=2, allow_nan=False))
