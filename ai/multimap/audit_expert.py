"""Independent audit of frozen expert-PPO v2; no fitting, selection on holdouts or launch.

Only this new auditor, its tests and expert-results-v2.json are written. Existing
compact caches are rehashed against immutable HF metadata. The 451 MB historical
reference is reused, never redownloaded. Old integrity functions are rebound in
private namespaces, not modified. Replay uses authenticated original serving code.
Run: ai/.venv/bin/python -B ai/multimap/audit_expert.py
"""
import argparse
import ast
from collections import Counter, defaultdict
import hashlib
import itertools
import json
import math
from pathlib import Path
import re
import shlex
import statistics
import subprocess
import sys
import time
import types

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
RUN = 'multimap-expert-ppo-20261102-v2-r1'
ORIGINAL = 'multimap-expert-ppo-20261102-v2'
JOB = '6ae949e9c78863f9c6313c59'
ORIGINAL_JOB = '6ae91d7fc78863f9c63119e3'
REPO = 'coyotte508/powergrid-ai-multimap-v1'
REVISION = '39976d5e864638fe73d241061bc4dfd4b46ce0a4'
RECOVERY_REVISION = '8ca6e47686e06edc7a24c2e85cc2b31e5140f860'
SOURCE = 'db144fc87d6745fe595ec7e28afc68de496b7966'
SOURCE_REVISION = '93fb8f56455c11693864df8883a24ef5ddf37777'
SOURCE_SHA = 'a3e3a1e8da85160069c3ad0648636efdfac582f4092ed3270abee05fe7aef8b2'
BEST_SHA = '1377fc2112c3b9ff3c2a20078ed341305b2a9006a4f7a1df413eeb0b509e6fbd'
NAMESPACE = 'pg-multimap-expert-ppo-20261102-v2'
TRAIN_MAPS = ('Germany', 'USA', 'France', 'UK & Ireland')
TRANSFER_MAPS = ('Italy', 'Benelux')
MAPS = TRAIN_MAPS + TRANSFER_MAPS
PHASES = ('Auction', 'Resources', 'Building', 'Bureaucracy')
FROZEN = ('ppo0', 'ppo1', 'ppo2')
CONTROLLERS = ('learner', 'warmupExpert', 'reference', 'self', *FROZEN, 'fixedV2', 'fixedV1', 'focalTeacher')
TIMINGS = {'featureMs', 'inferenceMs', 'referenceMs', 'seconds'}
FIELDS = {'spec', 'terminal', 'credit', 'allSeatCredit', 'steps', 'rounds', 'counts', 'expertCounts',
          'publicChecks', 'decisions', 'referenceRequests', 'expertRequests', *TIMINGS}
LIMIT = 128 * 1024**2
BASE = ROOT / 'ai/runs' / RUN / 'audit/restored'
OLD_BASE = ROOT / 'ai/runs/multimap-expert-recovery-v2/restored'


def require(condition, message):
    if not condition:
        raise ValueError(message)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def sha(value):
    return hashlib.sha256(value).hexdigest()


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
    return json.loads(Path(path).read_text(), object_pairs_hook=pairs,
                      parse_constant=lambda _: require(False, 'Nonfinite JSON'))


def equal(actual, expected, label):
    if isinstance(expected, dict):
        require(isinstance(actual, dict) and actual.keys() == expected.keys(), label + ': keys')
        for key in expected:
            equal(actual[key], expected[key], label + '.' + str(key))
    elif isinstance(expected, list):
        require(isinstance(actual, list) and len(actual) == len(expected), label + ': length')
        for i, (a, b) in enumerate(zip(actual, expected)):
            equal(a, b, label + '.' + str(i))
    elif type(expected) in (int, float) and type(actual) in (int, float):
        require(math.isfinite(actual) and math.isfinite(expected) and
                math.isclose(actual, expected, rel_tol=1e-12, abs_tol=1e-12), label + ': numeric')
    else:
        require(type(actual) is type(expected) and actual == expected, label + ': value')


def finite(value, low=0, high=math.inf):
    return type(value) in (int, float) and math.isfinite(value) and low <= value <= high


def integer(value, high=4000):
    return type(value) is int and 0 <= value <= high


def expected_plan(split, update=0, teacher=False):
    """Independent specification, not expert_rollout.plans or its validators."""
    require(split in ('warmup', 'train', 'selection', 'confirmation'), 'Reserved/unknown split')
    require(type(update) is int and (1 <= update <= 32 if split == 'train' else update == 0), 'Update namespace')
    require(type(teacher) is bool and (not teacher or split in ('selection', 'confirmation')), 'Teacher is eval-only')
    maps = ('Germany',) if split == 'warmup' else MAPS if split == 'confirmation' else TRAIN_MAPS
    deals = 8 if split == 'warmup' else 2 if split == 'confirmation' else 1
    tasks = []
    for ci, (m, n, variant, fast) in enumerate(itertools.product(maps, range(2, 7), ('original', 'recharged'), (False, True))):
        cell = f'{m}|{n}|{variant}|{int(fast)}'
        for deal in range(deals):
            seats = [(ci + deal) % n] if split == 'warmup' else [(ci + update - 1) % n] if split == 'train' else range(n)
            for focal in seats:
                reference = m == 'Germany' and (split != 'train' or (ci + update) % 2 == 0)
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
                s = dict(map=m, players=n, variant=variant, fastBid=fast, cell=cell, split=split,
                         update=update, deal=deal, focalSeat=focal, smoke=False, maxSteps=4000,
                         seed=f'{NAMESPACE}:{split}:{update}:{cell}:{deal}',
                         opponentMode='reference' if reference else 'mixed', opponents=opponents)
                if teacher:
                    s['focalTeacher'] = True
                tasks.append(s)
    return tasks


def key(record):
    return record['spec']['seed'], record['spec']['focalSeat']


def validate_outcome(r, task):
    require(set(r) == FIELDS, 'Outcome fields/error/trace')
    require(canonical(r['spec']) == canonical(task), 'Full task/namespace/opponents/types')
    require(r['terminal'] is True and all(finite(r[k]) for k in TIMINGS), 'Terminal/timings')
    credits = r['allSeatCredit']
    require(isinstance(credits, list) and len(credits) == task['players'] and
            all(finite(x, 0, 1) for x in credits), 'Credit dimensions/range')
    winners = sum(x > 0 for x in credits)
    require(winners > 0 and all(x == 0 or x == 1/winners for x in credits) and
            math.isclose(math.fsum(credits), 1, abs_tol=1e-15), 'Full 0 or 1/k credit')
    require(finite(r['credit'], 0, 1) and r['credit'] == credits[task['focalSeat']], 'Focal credit')
    require(integer(r['steps'], task['maxSteps']) and r['steps'] > 0 and
            integer(r['rounds'], r['steps']) and r['rounds'] > 0, 'Steps/rounds/cap')
    counts, labels, checks = r['counts'], r['expertCounts'], r['publicChecks']
    require(isinstance(counts, dict) and set(counts) == set(CONTROLLERS), 'Controller set')
    for c in [*counts.values(), labels]:
        require(isinstance(c, dict) and set(c) == set(PHASES) and
                all(integer(v, r['steps']) for v in c.values()), 'Phase counter types/schema')
    totals = {a: sum(c.values()) for a, c in counts.items()}
    require(sum(totals.values()) == r['steps'], 'Every step controller-accounted')
    for a in ('learner', 'warmupExpert', 'self', *FROZEN):
        require(counts[a]['Resources'] == counts[a]['Bureaucracy'] == 0, 'Learned fixed-phase leakage')
    allowed = set(task['opponents']) - {'learner'}
    if task.get('focalTeacher'):
        allowed.add('focalTeacher')
    else:
        allowed.add('warmupExpert' if task['split'] == 'warmup' else 'learner')
    if allowed & {'learner', 'warmupExpert', 'self'}:
        allowed.add('fixedV2')
    if allowed & set(FROZEN):
        allowed.add('fixedV1')
    require(all(not totals[a] for a in set(CONTROLLERS) - allowed), 'Absent controller/fixed teacher routing')
    for actor in allowed:
        phases = PHASES if actor in ('reference', 'focalTeacher') else (
            ('Resources', 'Bureaucracy') if actor in ('fixedV1', 'fixedV2') else ('Auction', 'Building'))
        require(all(counts[actor][p] > 0 for p in phases), 'Required controller/phase has no decisions')
    require(task['map'] == 'Germany' or totals['reference'] == 0, 'Germany-only reference')
    expected_labels = dict.fromkeys(PHASES, 0)
    if task['map'] == 'Germany' and task['split'] in ('warmup', 'train'):
        expected_labels = counts['warmupExpert' if task['split'] == 'warmup' else 'learner']
    require(labels == expected_labels, 'Germany training-only expert labels')
    expected_checks = dict(hiddenInvariant=totals['reference'] + sum(labels.values()),
                           referenceAtomicLegal=totals['reference'], expertAtomicLegal=sum(labels.values()),
                           fullMenuPrior=sum(totals[a] for a in ('learner', 'warmupExpert', 'self', *FROZEN)))
    require(isinstance(checks, dict) and set(checks) == set(expected_checks) and
            all(integer(v, 2*r['steps']) for v in checks.values()) and checks == expected_checks, 'Public/atomic/full-menu counters')
    for name, value in dict(decisions=totals['learner']+totals['warmupExpert'],
                            referenceRequests=expected_checks['hiddenInvariant'], expertRequests=sum(labels.values())).items():
        require(integer(r[name], 2*r['steps']) and r[name] == value, 'Collector request/decision counters')


def verify_outcomes(rows, tasks):
    require(len(rows) == len(tasks) and len({key(r) for r in rows}) == len(rows), 'Missing/duplicate outcomes')
    actual = {key(r): r for r in rows}
    for task in tasks:
        k = (task['seed'], task['focalSeat'])
        require(k in actual, 'Missing planned task')
        validate_outcome(actual[k], task)
    return actual


def summary(rows):
    cells = defaultdict(list)
    for r in rows:
        cells[r['spec']['cell']].append(r['credit'])
    cells = {c: statistics.mean(v) for c, v in cells.items()}
    maps = {m: statistics.mean(v for c, v in cells.items() if c.split('|')[0] == m)
            for m in sorted({c.split('|')[0] for c in cells})}
    require(maps, 'Empty summary')
    return dict(games=len(rows), failures=0, macroCredit=statistics.mean(maps.values()), maps=maps, cells=cells)


def eligible(candidate, baseline):
    if candidate.get('failures') != 0 or set(candidate.get('maps', {})) != set(TRAIN_MAPS):
        return False
    return finite(candidate['macroCredit'], 0, 1) and all(finite(candidate['maps'][m], 0, 1) and
        candidate['maps'][m] >= baseline['maps'][m] - (0 if m == 'Germany' else .05) - 1e-12 for m in TRAIN_MAPS)


def choose_selection(stages):
    require([x[0] for x in stages] == ['initial', 'warmup', '8', '16', '24', '32'], 'Scheduled selection only; never confirmation')
    baseline = stages[0][1]
    require(eligible(baseline, baseline), 'Invalid fallback')
    best, score, decisions = 'initial', baseline['macroCredit'], []
    for stage, result in stages:
        ok = eligible(result, baseline)
        if ok and result['macroCredit'] > score + 1e-12:
            best, score = stage, result['macroCredit']
        decisions.append(dict(stage=stage, eligible=ok, macroCredit=result['macroCredit'], maps=result['maps'], bestSoFar=best))
    return best, score, decisions


def initial_parity(initial, control):
    a, b = {key(r): r for r in initial}, {key(r): r for r in control}
    require(a.keys() == b.keys() and len(a) == len(initial) == len(control), 'Initial parity coverage')
    for k, left in a.items():
        right = b[k]
        for field in ('terminal', 'credit', 'allSeatCredit', 'steps', 'rounds', 'referenceRequests', 'expertRequests', 'expertCounts'):
            require(left[field] == right[field], 'Initial full terminal parity: ' + field)
        for actor in ('reference', 'fixedV1', 'warmupExpert', 'self', *FROZEN):
            require(left['counts'][actor] == right['counts'][actor], 'Initial nonfocal parity')
        for phase in PHASES:
            require(left['counts']['learner'][phase] + left['counts']['fixedV2'][phase] ==
                    right['counts']['focalTeacher'][phase], 'Initial transformed focal routing parity')


def check_disjoint(training, selection, confirmation):
    roots = [{r['spec']['seed'] for r in rows} for rows in (training, selection, confirmation)]
    require(len(roots[0]) == len(training), 'Duplicate fresh training root')
    require(all(not (a & b) for a, b in itertools.combinations(roots, 2)), 'Training/selection/confirmation leakage')
    require(all(r['spec']['map'] in TRAIN_MAPS and r['spec']['split'] in ('warmup', 'train') for r in training), 'Heldout map training')
    return dict(trainingRoots=len(roots[0]), selectionDeals=len(roots[1]), confirmationDeals=len(roots[2]),
                trainingMaps=list(TRAIN_MAPS), heldoutMaps=list(TRANSFER_MAPS), allDisjoint=True,
                note='Selection roots deliberately repeat across checkpoints and teacher; transferred artifacts are not new observations.')


def stratified_estimate(strata):
    require(strata and all(len(v) >= 2 and all(finite(x, -1, 1) for x in v) for v in strata.values()), 'At least two deals per fixed cell')
    c = len(strata)
    mean = statistics.mean(statistics.mean(v) for v in strata.values())
    variance = math.fsum(statistics.variance(v)/len(v) for v in strata.values())/(c*c)
    se = math.sqrt(variance)
    return dict(mean=mean, standardError=se, approximateNormal95=[mean-1.96*se, mean+1.96*se],
                cells=c, independentDeals=sum(map(len, strata.values())))


def deal_table(rows):
    groups = defaultdict(dict)
    for r in rows:
        s = r['spec']; group = groups[(s['cell'], s['deal'])]
        require(s['focalSeat'] not in group, 'Duplicate focal seat')
        group[s['focalSeat']] = r['credit']
    result = {}
    for (cell, deal), seats in groups.items():
        n = int(cell.split('|')[1])
        require(set(seats) == set(range(n)), 'Incomplete all-seat deal cluster')
        result[cell, deal] = statistics.mean(seats.values())
    return result


def statistics_report(selected, teacher):
    a, b = deal_table(selected), deal_table(teacher)
    require(a.keys() == b.keys(), 'Unpaired confirmation deals')
    cells = sorted({c for c, _ in a})
    require(len(cells) == 120 and all((c, d) in a for c in cells for d in (0, 1)) and len(a) == 240, 'Full two-deal confirmation coverage')
    subsets = {'allMaps': cells, 'trainingMaps': [c for c in cells if c.split('|')[0] in TRAIN_MAPS],
               'transferMaps': [c for c in cells if c.split('|')[0] in TRANSFER_MAPS],
               'nonGermany': [c for c in cells if not c.startswith('Germany|')]}
    subsets.update({'map:'+m: [c for c in cells if c.split('|')[0] == m] for m in MAPS})
    subsets.update({'players:'+str(n): [c for c in cells if int(c.split('|')[1]) == n] for n in range(2, 7)})
    subsets.update({'rule:'+v+'|'+str(f): [c for c in cells if c.split('|')[2:] == [v, str(f)]]
                    for v in ('original', 'recharged') for f in (0, 1)})
    out = {}
    for name, subset in subsets.items():
        result = {}
        for label, table in (('selected', a), ('teacherV2', b)):
            result[label] = stratified_estimate({c: [table[c, d] for d in (0, 1)] for c in subset})
        result['pairedDifference'] = stratified_estimate({c: [a[c, d]-b[c, d] for d in (0, 1)] for c in subset})
        result['gamesPerArm'] = sum(2*int(c.split('|')[1]) for c in subset)
        out[name] = result
    cell_delta = {c: statistics.mean(a[c,d]-b[c,d] for d in (0,1)) for c in cells}
    germany = subsets['map:Germany']
    neutral = statistics.mean(1/int(c.split('|')[1]) for c in germany)
    out['GermanyAnalyticalReferenceBenchmark'] = dict(benchmark=neutral,
        selectedMinusNeutral=stratified_estimate({c: [a[c, d]-1/int(c.split('|')[1]) for d in (0, 1)] for c in germany}),
        teacherMinusNeutral=stratified_estimate({c: [b[c, d]-1/int(c.split('|')[1]) for d in (0, 1)] for c in germany}),
        newlyPlayedReferenceControlGames=0,
        note='Analytical symmetric all-reference all-seat mean 1/n, macro .29; NOT an additional played control. '
             'Selected deal averages are compared against that neutral identity. Interval includes zero: no demonstrated superiority to exact reference.')
    return dict(method='Equal fixed-cell weights, equal map weights on this balanced grid; all focal seats averaged within each deal. '
                'Paired delta formed on identical task/opponent assignments; SE=sqrt(sum_c s_c^2/D_c / C^2), '
                's_c^2 unbiased sample variance (ddof=1), D_c=2 independent deals. Approximate normal mean +/-1.96 SE.',
                caveats=['Exploratory, unadjusted multiple comparisons; two deals per cell give imprecise variance estimates.',
                         'No independent training-seed replication; inference is conditional on this selected checkpoint and fixed populations.',
                         'Positive map/count/rule aggregates do not imply improvement in every cell; 14 of 120 observed cell means regress.',
                         'Germany uses exact reference opponents; other maps use fixed mixed PPO0/1/2, NOT the old reference.',
                         'All-map credit is not universal neural-population or human strength; teacher-v2 differs from v1, so earlier raw credits are not a causal comparison.'],
                subsets=out, cellSigns=dict(positive=sum(v>1e-12 for v in cell_delta.values()),
                    tied=sum(abs(v)<=1e-12 for v in cell_delta.values()), negative=sum(v< -1e-12 for v in cell_delta.values())),
                cellPairedMeanDifferences=cell_delta, cellDealMeans={c: dict(selected=[a[c,d] for d in (0,1)], teacherV2=[b[c,d] for d in (0,1)]) for c in cells})


def tensor_equal(a, b, label='transaction'):
    import torch
    if isinstance(a, torch.Tensor):
        require(isinstance(b, torch.Tensor) and a.dtype == b.dtype and a.shape == b.shape and
                a.detach().cpu().contiguous().numpy().tobytes() == b.detach().cpu().contiguous().numpy().tobytes(), label + ': tensor bits')
    elif isinstance(a, dict):
        require(isinstance(b, dict) and a.keys() == b.keys(), label + ': keys')
        for k in a:
            tensor_equal(a[k], b[k], label + '.' + str(k))
    elif isinstance(a, (tuple, list)):
        require(type(a) is type(b) and len(a) == len(b), label + ': sequence')
        for x, y in zip(a, b):
            tensor_equal(x, y, label)
    else:
        require(type(a) is type(b) and a == b, label + ': value')


def verify_resume(old, final):
    require(old.keys() == final.keys() and old['stage'] == final['stage'] == 'train' and
            old['update'] == final['update'] == 32, 'Resume must already have completed 32 updates')
    allowed = {'confirmations', 'result', 'torchRng'}
    for name in old.keys() - allowed:
        tensor_equal(old[name], final[name], 'Unchanged resume.'+name)
    require(old['confirmations'] == {} and old['result'] is None, 'Selection predates confirmation')
    require(final['bestUpdate'] == 24 and final['bestStage'] == 'train' and final['bestSha256'] == BEST_SHA and
            sha(final['bestArtifact']) == BEST_SHA, 'Frozen selected checkpoint bytes')
    require(old['optimizer']['state'], 'Missing populated optimizer')
    return sorted(old.keys() - allowed)


def git_bytes(name):
    return subprocess.check_output(['git', 'show', f'{SOURCE}:{name}'], cwd=ROOT)


def reuse(function, **overrides):
    scope = dict(function.__globals__); scope.update(overrides)
    bound = types.FunctionType(function.__code__, scope, function.__name__, function.__defaults__, function.__closure__)
    bound.__kwdefaults__ = function.__kwdefaults__
    return bound


def local_difference(name, archived, local):
    if archived == local:
        return None
    allowed = {'ai/multimap/README.md', 'ai/multimap/runs.json',
               'ai/multimap/expert-launch-v2.json', 'ai/multimap/expert-resume-launch-v2.json'}
    require(name in allowed, 'Strict serving source drift: '+name)
    return dict(sourceSha256=archived, localSha256=local, note='Nonserving documentation/bookkeeping/launcher/receipt only')


def integrity_modules():
    for name in ('audit_gap.py', 'audit_neural.py'):
        require(digest(HERE/name) == sha(git_bytes('ai/multimap/'+name)), 'Frozen integrity helper changed')
    import audit_neural, audit_gap
    return audit_neural, audit_gap


def remote_artifacts(remote, base, revision, run, expected_count):
    pin = dict(repo=REPO, revision=revision, path=f'runs/{run}/artifacts.json')
    manifest = read(remote.get(pin))
    require(len(manifest) == expected_count, 'Complete compact manifest count')
    expected_names = {'protocol.json', 'environment.json', 'recovery.json', 'status.json',
        *('expert/'+n for n in ('config.json', 'history.json', 'initial.pt', 'warmup.pt', 'best.pt', 'last.pt',
           'selection-plan.json', 'warmup-plan.json', 'warmup.json', 'selection-0.json', 'selection-teacher.json',
           'selection-warmup.json', 'selection-8.json', 'selection-16.json', 'selection-24.json', 'selection-32.json')),
        *(f'expert/{prefix}-{i}.json' for i in range(1, 33) for prefix in ('train', 'train-plan'))}
    if run == RUN:
        expected_names |= {'expert/'+n for n in ('result.json', 'confirmation-plan.json', 'confirmation-selected.json', 'confirmation-teacher.json')}
    require(set(manifest) == expected_names, 'Artifact allowlist/full file set')
    prefix = f'runs/{run}/'
    remote_names = {e.path[len(prefix):] for e in remote.api.list_repo_tree(REPO, path_in_repo=prefix.rstrip('/'),
                    revision=revision, recursive=True) if hasattr(e, 'blob_id')}
    require(remote_names == expected_names | {'artifacts.json'}, 'Full remote compact file-set coverage')
    entries = remote.api.get_paths_info(REPO, [prefix+n for n in manifest], revision=revision)
    require(len(entries) == len(manifest), 'Remote metadata count')
    byname = {e.path[len(prefix):]: e for e in entries}
    total = 0
    for name, checksum in manifest.items():
        path = base/name
        require(path.is_file() and not path.is_symlink(), 'Missing/unsafe restored artifact')
        remote.get(dict(repo=REPO, revision=revision, path=prefix+name, sha256=checksum), metadata=byname[name], cached=path)
        total += path.stat().st_size
    require(total <= LIMIT, 'Compact byte budget')
    require({p.relative_to(base).as_posix() for p in base.rglob('*') if p.is_file()} == expected_names, 'Restored cache file set')
    return manifest, total


def replay_tasks():
    plan = expected_plan('confirmation')
    chosen = []
    for i, m in enumerate(MAPS):
        n, v, f = 2+i % 5, ('original', 'recharged')[(i//2) % 2], bool(i % 2)
        options = [s for s in plan if s['map'] == m and s['players'] == n and s['variant'] == v and s['fastBid'] == f]
        chosen.append(min(options, key=canonical))
    require({s['players'] for s in chosen} == set(range(2, 7)), 'Replay player coverage')
    require({(s['variant'], s['fastBid']) for s in chosen} == set(itertools.product(('original', 'recharged'), (False, True))), 'Replay rule coverage')
    return chosen


def replay(base, selected, teacher):
    from expert_rollout import collect
    from expert_policy import load
    from candidates import load_candidates
    import torch
    began = time.monotonic()
    torch.use_deterministic_algorithms(True)
    model, _ = load(base/'expert/best.pt')
    population = load_candidates(list(FROZEN))
    report = []
    for label, stored in (('selected', selected), ('teacherV2', teacher)):
        tasks = replay_tasks()
        if label == 'teacherV2':
            tasks = [dict(s, focalTeacher=True) for s in tasks]
        rows, outcomes = collect(model, tasks, workers=6, training=False, seed=917, mode='evaluation',
            artifact=ROOT/'ai/runs/multimap-reference-preflight-v1/artifact',
            reference_python=ROOT/'ai/.venv-reference/bin/python', opponents=population)
        require(rows == [], 'Replay evaluation must return no optimization/oracle rows')
        verify_outcomes(outcomes, tasks)
        actual = {key(r): r for r in stored}
        for r in outcomes:
            old = actual[key(r)]
            left = {k:v for k,v in r.items() if k not in TIMINGS}
            right = {k:v for k,v in old.items() if k not in TIMINGS}
            require(left == right, 'Exact replay terminal/controller/public/request mismatch: '+canonical(r['spec']))
            report.append(dict(arm=label, spec=r['spec'], exactTerminalAndCountersSha256=sha(canonical(left).encode())))
    return dict(games=12, exactMatches=12, workers=6, maps=list(MAPS), players=list(range(2,7)), allFourRules=True,
                comparedFields=sorted(FIELDS-TIMINGS), excludedTimingFields=sorted(TIMINGS),
                newIndependentObservations=0, seconds=time.monotonic()-began, checks=report)


def job_evidence(api, launch, resume):
    tree = ast.parse(git_bytes('ai/multimap/launch.py'))
    values = [ast.literal_eval(n.value) for n in tree.body if isinstance(n, ast.Assign) and
              any(isinstance(t, ast.Name) and t.id == 'BOOTSTRAP' for t in n.targets)]
    require(len(values) == 1, 'Single frozen launch bootstrap')
    command = ['bash', '-lc', 'python -m pip install --disable-pip-version-check huggingface_hub==1.29.0 && python -c ' + shlex.quote(values[0])]
    reports = []
    for receipt, jid, expected in ((launch, ORIGINAL_JOB, 'ERROR'), (resume, JOB, 'COMPLETED')):
        job = api.inspect_job(job_id=jid)
        require(job.status.stage == expected and job.docker_image == receipt['image'] and
                job.flavor == receipt['flavor'] and job.environment == receipt['env'] and job.command == command and
                job.arguments == [], 'HF job/source/image/workers/environment/frozen bootstrap command')
        log = '\n'.join(api.fetch_job_logs(job_id=jid, follow=False))
        require(len(log.encode()) < 2*1024**2, 'Bounded job log')
        require(re.search(r'Ran 19 tests in .*?\n\s*\n?OK', log) and re.search(r'(?:#|ℹ) tests 7', log) and
                re.search(r'(?:#|ℹ) pass 7', log) and re.search(r'(?:#|ℹ) fail 0', log), 'HF startup 19 Python / 7 Node tests')
        marker = '{"stage": "uploaded", "label": "runtime-ready"'
        require(log.count(marker) == 1, 'Single production runtime-ready boundary')
        startup, production = log.split(marker, 1)
        updates = [int(x) for x in re.findall(r'"stage": "expert-ppo", "update": (\d+)', production)]
        synthetic = [int(x) for x in re.findall(r'"stage": "expert-ppo", "update": (\d+)', startup)]
        require(synthetic == [1,2,1,2], 'Expected mocked startup resume-test updates')
        require(updates == (list(range(1,33)) if jid == ORIGINAL_JOB else []), 'Optimization continued/repeated after resume')
        if jid == ORIGINAL_JOB:
            require(job.status.message == 'Job timeout', 'Original operational timeout')
        reports.append(dict(jobId=jid, status=job.status.stage, statusMessage=job.status.message,
            startedAt=str(job.started_at), finishedAt=str(job.finished_at), logSha256=sha(log.encode()),
            logBytes=len(log.encode()), pythonTests=19, nodeTests=7, optimizationUpdates=updates,
            syntheticStartupTestUpdates=synthetic, image=job.docker_image, environment=job.environment,
            frozenBootstrapCommandSha256=sha(canonical(command).encode()),
            note='Logs independently retrieved using fetch_job_logs(follow=False), not empty hf jobs wait/watch output. '
                 'Mocked unit tests print updates 1,2,1,2 before runtime-ready; these are NOT production optimization or observed games.'))
    return reports


def audit():
    import torch
    from huggingface_hub import HfApi, try_to_load_from_cache
    began = time.monotonic()
    protocol = read(HERE/'expert-protocol-v2.json')
    launch, resume, recovery, preflight = [read(HERE/f'expert-{n}-v2.json') for n in ('launch', 'resume-launch', 'recovery', 'preflight')]
    require(sha(git_bytes('ai/multimap/expert-protocol-v2.json')) == digest(HERE/'expert-protocol-v2.json'), 'Frozen protocol Git')
    require(launch['sourceCommit'] == resume['sourceCommit'] == SOURCE and
            launch['env']['SOURCE_REVISION'] == resume['env']['SOURCE_REVISION'] == SOURCE_REVISION and
            launch['env']['SOURCE_SHA256'] == resume['env']['SOURCE_SHA256'] == SOURCE_SHA and
            resume['resumeFromRevision'] == RECOVERY_REVISION, 'Immutable launch/resume source pins')
    require(resume['selectedCheckpointSha256'] == BEST_SHA and resume['selectedUpdate'] == 24 and
            resume['completedUpdates'] == 32 and resume['remainingConfirmationGames'] == 1920, 'Preconfirmation frozen choice')
    require(digest(HERE/'expert-preflight-v2.json') == launch['preflightSha256'] and
            digest(HERE/'expert-recovery-v2.json') == resume['recoveryEvidenceSha256'], 'Evidence receipt pins')
    old_helpers, gap_helpers = integrity_modules()
    remote = old_helpers.RemoteFiles(HfApi())
    final_manifest, final_bytes = remote_artifacts(remote, BASE, REVISION, RUN, 88)
    old_manifest, old_bytes = remote_artifacts(remote, OLD_BASE, RECOVERY_REVISION, ORIGINAL, 84)
    equal(old_manifest, recovery['manifest'], 'Recovery manifest')
    equal(read(ROOT/'ai/runs/multimap-expert-recovery-v2/verification.json'),
          {k:v for k,v in recovery.items() if k not in ('privateEvidence', 'recoveryChecks')}, 'Original independent recovery evidence')
    inherited = {n:h for n,h in old_manifest.items() if n not in ('expert/last.pt', 'status.json')}
    require(all(final_manifest[n] == h for n,h in inherited.items()), 'Inherited artifacts changed/reselected/retrained')
    require(final_manifest['expert/best.pt'] == BEST_SHA, 'Selected bytes immutable')
    config = read(BASE/'expert/config.json'); status = read(BASE/'status.json')
    equal(read(BASE/'protocol.json'), protocol, 'Protocol artifact')
    equal(status['protocol'], protocol, 'Status protocol')
    equal(status['resume'], dict(run=ORIGINAL, revision=RECOVERY_REVISION,
                                files={n:h for n,h in old_manifest.items() if n.startswith('expert/')}), 'Exact inherited transaction')
    require(status['stage'] == 'complete' and status['workers'] == 6 and status['smoke'] is False and
            status['run'] == RUN and status['sourceRevision'] == SOURCE_REVISION and status['sourceSha256'] == SOURCE_SHA, 'Completed final source status')
    require([r['stage'] for r in status['receipts']] == ['runtime-ready','confirmation-selected','confirmation-teacher','complete'], 'Confirmation-only resumed receipts')
    from expert_ppo import config as serving_config
    rebuilt = serving_config(artifact=ROOT/'ai/runs/multimap-reference-preflight-v1/artifact',
                             reference_python=ROOT/'ai/.venv-reference/bin/python', workers=6)
    equal(config, rebuilt, 'Full serving/config/engine42/dependencies/runtime/reference identity')
    equal(config['sourceFiles'], preflight['servingSourceFiles'], 'Preflight serving hashes')
    equal(config['runtimeVersions'], preflight['runtimeVersions'], 'Preflight principal runtime versions')
    environment = read(BASE/'environment.json')
    equal(environment['versions'], config['runtimeVersions'], 'Recorded environment/runtime identity')
    require(environment['requirementsSha256'] == protocol['referenceRequirementsSha256'] and
            environment['referenceVenvBytes'] <= protocol['referenceVenvMaxBytes'], 'HF reference environment requirements/budget')
    local_venv_bytes = sum(p.stat().st_size for p in (ROOT/'ai/.venv-reference').rglob('*') if p.is_file())
    require(local_venv_bytes <= protocol['referenceVenvMaxBytes'], 'Reused local reference environment budget')
    source_pin = dict(repo=launch['env']['DATASET_REPO'], repo_type='dataset', revision=SOURCE_REVISION,
                      path=launch['env']['SOURCE_PATH'], sha256=SOURCE_SHA)
    source = remote.get(source_pin)
    source_report = reuse(old_helpers.verify_source, ROOT=ROOT, HERE=HERE, SOURCE=SOURCE,
                          SOURCE_NAMES=set(rebuilt['sourceFiles']), LIMIT=LIMIT, git_bytes=git_bytes,
                          local_source_difference=local_difference)(source, config)
    source_report['note'] = ('Complete archive member manifest, Git-tracked sources, runtime Node, compiled engine and bundled '
        'dependencies independently checked; no extraction or serving edits. Only README/runs/launch receipts may differ locally. '
        'Old integrity helper globals were privately rebound; no old module was mutated.')
    reference_report = gap_helpers.verify_reference(dict(protocol, compressedArchiveRamMaxBytes=LIMIT), read(BASE/'recovery.json'), remote)
    pins = [protocol['warmStart'], *protocol['opponentPool']]
    checkpoints = []
    for pin in pins:
        cached = try_to_load_from_cache(pin['repo'], pin['path'], revision=pin['revision'])
        checkpoints.append(remote.get(pin, cached=cached if isinstance(cached, str) else None))
    initial = torch.load(BASE/'expert/initial.pt', weights_only=True, map_location='cpu')
    from expert_policy import warm_start, load
    expected_initial = warm_start(checkpoints[0])
    tensor_equal(initial['state_dict'], expected_initial.state_dict(), 'Warm-start representation/zero head')
    require(all(not torch.count_nonzero(initial['state_dict'][name]) for name in
                ('network.action.2.weight','network.action.2.bias')), 'Initial actor zero')
    old = torch.load(OLD_BASE/'expert/last.pt', weights_only=True, map_location='cpu')
    final = torch.load(BASE/'expert/last.pt', weights_only=True, map_location='cpu')
    unchanged_keys = verify_resume(old, final)
    tensor_equal(final['config'], config, 'Final checkpoint identity')
    for name, stage, update in (('initial', 'initial', 0), ('warmup', 'warmup', 0), ('best', 'train', 24)):
        saved = torch.load(BASE/f'expert/{name}.pt', weights_only=True, map_location='cpu')
        require(saved['stage'] == stage and saved['update'] == update and saved['width'] == 64 and
                saved['bound'] == 16 and saved['priorAsActionFeature'] is True, 'Stage checkpoint identity')
        tensor_equal(saved['config'], config, 'Stage checkpoint config')
    torch.set_rng_state(old['torchRng']); load(BASE/'expert/best.pt')
    tensor_equal(torch.get_rng_state(), final['torchRng'], 'Only best-model construction consumes Torch RNG on resume')
    history = read(BASE/'expert/history.json')
    equal(history, final['history'], 'History checkpoint')
    require([(r['stage'],r['update']) for r in history] == [('warmup',0)]+[('train',i) for i in range(1,33)], 'Single 32-update history')
    training, selection_rows, all_rows, stages = [], [], [], []
    for split, update in [('warmup',0)]+[('train',i) for i in range(1,33)]:
        label = 'warmup' if split == 'warmup' else f'train-{update}'
        plan_file = 'warmup-plan' if split == 'warmup' else f'train-plan-{update}'
        tasks = expected_plan(split, update)
        require(canonical(read(BASE/f'expert/{plan_file}.json')) == canonical(tasks), 'Independent train/warmup plan')
        record = read(BASE/f'expert/{label}.json'); games = record['games']
        verify_outcomes(games, tasks)
        h = history[update]
        equal(h['training'], summary(games), 'Recomputed training history')
        metrics = h['optimization']
        require(metrics['rows'] == sum(g['decisions'] for g in games) <= 100000 and
                metrics['expertRows'] == sum(g['expertRequests'] for g in games), 'Optimization row/label totals')
        require(all(type(v) is bool or finite(v, -math.inf) for v in metrics.values()) and metrics['optimizerSteps'] > 0, 'Finite optimization metrics')
        if update:
            equal(metrics['expertCoefficient'], .5*.97**(update-1), 'Expert decay')
            require(metrics['optimizerSteps'] <= 4*math.ceil(metrics['rows']/64), 'PPO step bound')
        else:
            equal(record['optimization'], metrics, 'Warmup metrics')
            require(metrics['epochs'] == 24 and metrics['optimizerSteps'] == 24*math.ceil(metrics['rows']/64), 'Warmup passes')
        training.extend(games)
    tasks = expected_plan('selection')
    require(canonical(read(BASE/'expert/selection-plan.json')) == canonical(tasks), 'Selection frozen plan')
    selection_by_label = {}
    for label in ('0','teacher','warmup','8','16','24','32'):
        record = read(BASE/f'expert/selection-{label}.json')
        verify_outcomes(record['games'], expected_plan('selection', teacher=label=='teacher'))
        score = summary(record['games']); equal(record['summary'], score, 'Selection summary '+label)
        selection_rows.extend(record['games']); selection_by_label[label] = record['games']
        if label != 'teacher':
            stages.append(('initial' if label == '0' else label, score))
            if label != '0':
                equal(history[0 if label=='warmup' else int(label)]['selection'], score, 'History selection')
    initial_parity(selection_by_label['0'], selection_by_label['teacher'])
    best, score, decisions = choose_selection(stages)
    require(best == '24', 'Independently selected earliest eligible checkpoint')
    equal(score, final['bestScore'], 'Best score')
    equal(stages[0][1], final['baseline'], 'Fallback baseline')
    confirmation = {}
    require(canonical(read(BASE/'expert/confirmation-plan.json')) == canonical(expected_plan('confirmation')), 'Independent confirmation plan')
    for label in ('selected','teacher'):
        file = BASE/f'expert/confirmation-{label}.json'; record = read(file)
        verify_outcomes(record['games'], expected_plan('confirmation', teacher=label=='teacher'))
        scores = summary(record['games']); equal(record['summary'], scores, 'Confirmation independent summary')
        equal(final['confirmations'][label], dict(summary=scores, sha256=digest(file)), 'Committed confirmation hash/summary')
        confirmation[label] = record['games']
    result = read(BASE/'expert/result.json')
    equal(result, final['result'], 'Final checkpoint result'); equal(result, status['result'], 'Final status result')
    equal(result['confirmation'], {k:summary(v) for k,v in confirmation.items()}, 'Final confirmation results')
    require(result['selectedUpdate'] == 24 and result['selectedStage'] == 'train' and result['trainedUpdates'] == 32 and
            result['warmupEpochs'] == 24 and result['smoke'] is False, 'Final recipe')
    for flags in (protocol, status, result):
        require(flags['qualificationEligible'] is False and flags['reservedFinalSeedsUsed'] is False and flags.get('qualified', False) is False, 'No qualification/reserved finals')
    leakage = check_disjoint(training, selection_rows, confirmation['selected'])
    all_rows = training + selection_rows + confirmation['selected'] + confirmation['teacher']
    require(len(training) == 2720 and len(selection_rows) == 2240 and len(all_rows) == 6880, 'All scheduled saved games')
    labels = sum(r['expertRequests'] for r in training)
    require(labels == 44262, 'Fresh Germany label total')
    stats = statistics_report(confirmation['selected'], confirmation['teacher'])
    jobs = job_evidence(remote.api, launch, resume)
    recovery_logs = {}
    for name in ('verification.json', 'python-checks.log', 'node-checks.log'):
        path = ROOT/'ai/runs/multimap-expert-recovery-v2'/name
        require(digest(path) == recovery['privateEvidence']['files'][name], 'Pinned recovery evidence bytes')
        recovery_logs[name] = digest(path)
    python_log = (ROOT/'ai/runs/multimap-expert-recovery-v2/python-checks.log').read_text()
    node_log = (ROOT/'ai/runs/multimap-expert-recovery-v2/node-checks.log').read_text()
    require(re.search(r'Ran 19 tests in .*?\n\s*\n?OK', python_log) and
            re.search(r'(?:#|ℹ) tests 7', node_log) and re.search(r'(?:#|ℹ) pass 7', node_log) and
            re.search(r'(?:#|ℹ) fail 0', node_log), 'Separately pinned recovery unit logs')
    replay_report = replay(BASE, confirmation['selected'], confirmation['teacher'])
    from unittest import TestLoader, TextTestRunner
    suite = TestLoader().discover(str(HERE), pattern='test_audit_expert.py')
    tests = TextTestRunner(verbosity=1).run(suite)
    require(tests.wasSuccessful() and tests.testsRun > 0, 'Independent adversarial audit tests')
    return dict(schema='multimap-expert-independent-audit-v2', run=RUN, repo=REPO, revision=REVISION,
        auditorSha256=digest(HERE/'audit_expert.py'), adversarialTestsSha256=digest(HERE/'test_audit_expert.py'),
        sourceGit=SOURCE, sourceDatasetRevision=SOURCE_REVISION, sourceSha256=SOURCE_SHA,
        selectedStage='train', selectedUpdate=24, selectedCheckpointSha256=BEST_SHA,
        allChecksPassed=True, qualified=False, qualificationEligible=False, promoted=False, deployed=False,
        reservedFinalSeedsUsed=False, finalArtifactFiles=88, finalArtifactBytes=final_bytes,
        originalArtifactFiles=84, originalArtifactBytes=old_bytes, finalManifest=final_manifest,
        verifiedRemoteFiles=remote.evidence, boundedCompactSourceModelBytes=remote.bounded_bytes,
        source=source_report, reference=reference_report, jobs=jobs,
        identity=dict(sourceFiles=config['sourceFiles'], engineDependencies=config['engineDependencies'],
                      runtimeVersions=config['runtimeVersions'], execution=config['execution'],
                      environmentReceipt=environment, localReferenceVenvBytes=local_venv_bytes,
                      note='All 42 compiled engine modules, serving Python/JS and reference manifest/source files checked. '
                           'Historical transitive Python dependencies are not fully pinned; matching principal versions is not a complete environment claim.'),
        resume=dict(originalRun=ORIGINAL, originalRevision=RECOVERY_REVISION, originalTimeoutAfterUpdates=32,
            finalOptimizationOrReselection=False, inheritedByteIdenticalFiles=len(inherited),
            unchangedCheckpointKeys=unchanged_keys, modelAndPopulatedOptimizerBitIdentical=True,
            expectedTorchRngChangeExactlyReproduced=True, changedCheckpointKeys=['confirmations','result','torchRng'],
            bestEmbeddedBytesVerified=True, note='Same source archive, image, runtime and six workers. '
                'Only confirmation resumed; any uncommitted original partial confirmation was not counted as a new observation.'),
        coverage=dict(savedTerminalOutcomes=6880, training=2720, warmup=160, ppo=2560, selectionAndControl=2240,
            confirmation=1920, failures=0, capped=0, missing=0, duplicateScheduledTasks=0,
            freshGermanyExpertLabels=labels, warmupLabels=sum(r['expertRequests'] for r in training[:160]),
            zeroEvaluationExpertLabels=True, nonGermanyReferenceRequests=0, initialZeroHeadFullTeacherParityGames=320,
            leakage=leakage, controllerPhases={a:dict(sum((Counter(r['counts'][a]) for r in all_rows), Counter())) for a in CONTROLLERS},
            publicChecks=dict(sum((Counter(r['publicChecks']) for r in all_rows), Counter()))),
        selection=dict(rule='Eligible initial fallback; Germany nonregression, other training maps max .05 regression; earliest tie.',
                       confirmationUsed=False, decisions=decisions),
        confirmationStatistics=stats, replay=replay_report,
        tests=dict(independentAuditPython=tests.testsRun, failures=len(tests.failures), errors=len(tests.errors),
            hfStartupPythonPerJob=19, hfStartupNodePerJob=7, recoveryPython=19, recoveryNode=7,
            separatePreflight=preflight['tests'], recoveryLogsVerified=recovery_logs,
            note='Recovery and preflight are separately pinned engineering evidence, not additional strength samples.'),
        conclusion='Positive paired confirmation gain over teacher-v2 across all six maps, including transfer; '
                   'Germany selected-minus-analytical-reference interval includes zero. Evidence supports a stronger research candidate, '
                   'not a claim of defeating exact reference or humans, and not deployment/qualification.',
        recommendation='Freeze update24. Before further training, preregister fresh, larger-deal stress evaluation on the four training maps '
                       'against frozen strong/mixed populations, including exact reference and mixed PPO opponents on Germany. '
                       'If robust, independently replicate training seeds. Do not iteratively tune on Italy/Benelux transfer results. '
                       'No implementation or new launch authorized by this audit.',
        limitations=['Compact outcomes/counters, authenticated source and checkpoints are audited; RAM-only trajectories and gradients '
                     'are not retained, so this is not a full independent replay of optimization.',
                     'Uncommitted pre-timeout partial confirmation attempts are not recoverable; only the 6880 uniquely scheduled saved '
                     'outcomes count. Replays and inherited files add zero independent observations.'],
        seconds=time.monotonic()-began)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, default=HERE/'expert-results-v2.json')
    args = parser.parse_args()
    report = audit()
    args.output.write_text(json.dumps(report, indent=2, allow_nan=False)+'\n')
    print(json.dumps({k:report[k] for k in ('allChecksPassed','selectedUpdate','conclusion','seconds')}, indent=2))
