"""Independent, bounded audit of the immutable ten-arm Germany phase-gap study.

Run with ai/.venv/bin/python -B ai/multimap/audit_gap.py. Writes only the new
requested gap-results-v1.json. No fitting, action traces, new deals or selection.
Plan, outcomes, routing, counters and statistics are derived here independently;
only WorkerRuntime/play_game are reused for ten exact deterministic replays.
The frozen audit_neural integrity helpers are reused with private FunctionType
namespaces, never by changing old module globals or rewriting old source.
"""
import argparse
import ast
from collections import Counter, defaultdict
from fractions import Fraction
import hashlib
import importlib.metadata
import json
import math
import os
from pathlib import Path, PurePosixPath
import shlex
import statistics
import subprocess
import sys
import time
import types

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
RUN = 'multimap-phase-gap-20261102-v1'
JOB = '6ae9042a0e0338d1bb7e9ddb'
REPO = 'coyotte508/powergrid-ai-multimap-v1'
REVISION = 'f01d97bab8207af74930d0cfa6add36d0cf5df2d'
SOURCE = '61ed445ef0b27516f8eb74089d31dc0f4f1a83e6'
RECEIPT_COMMIT = '874de09d60b8daa80c3882a0675b851766b4ea8c'
NAMESPACE = 'pg-multimap-phase-gap-20261102-v1'
LIMIT = 128 * 1024**2
PHASES = ('Auction', 'Resources', 'Building', 'Bureaucracy')
POLICIES = ('reference', 'teacher', *('reference-except-' + p for p in PHASES),
            *('teacher-except-' + p for p in PHASES))
ACTORS = ('focalReference', 'focalTeacher', 'nonfocalReference')
BOUNDS = (0, 2, 4, 8, 12, 16, 20)
EPSILON = 1e-9
UNREACHABLE = 'cannotOutscoreTeacherBestWithCurrentBound'
COUNTERS = ('multiActionDecisions', 'forcedMoves', 'teacherExpertAgreement',
            'priorGapSum', 'priorGapMax', 'priorGapHistogram', UNREACHABLE, 'exactFloor20')
TERMINAL_FIELDS = ('allSeatCredit', 'steps', 'rounds', 'counts', 'decisions', 'phaseCounters', 'publicChecks')
ARTIFACT_NAMES = {'artifacts.json', 'protocol.json', 'environment.json', 'recovery.json',
                  'status.json', 'study/plan.json', 'study/games.jsonl', 'study/summary.json'}
SOURCE_NAMES = {f'ai/multimap/{name}' for name in (
    'gap-protocol-v1.json', 'gap_game.cjs', 'gap_study.py', 'job_gap.py', 'test_gap.cjs', 'test_gap.py',
    'neural_study.py', 'neural-study-v1.json', 'job_neural.py', 'reference_evaluate.py',
    'reference_recover.py', 'reference_game.cjs', 'game_rl.cjs', 'game.cjs', 'features.cjs',
    'teacher.cjs', 'data.py', 'protocol.json', 'ppo-protocol-v1.json', 'requirements-cpu.txt')}
SOURCE_NAMES |= {'ai/core.cjs', 'ai/strong/economics.cjs', 'ai/requirements-serve.txt',
                 'engine/package.json', 'engine/pnpm-lock.yaml'}
# verify_source separately checks the entire compiled-engine file set against the archive.
SOURCE_NAMES |= {p.relative_to(ROOT).as_posix() for p in (ROOT / 'engine/dist').rglob('*.js')}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def object_sha(value):
    return sha(canonical(value).encode())


def git_bytes(name, revision=SOURCE):
    return subprocess.check_output(['git', 'show', f'{revision}:{name}'], cwd=ROOT)


def reuse(function, **overrides):
    """No old global is mutated; defaults/closure are preserved explicitly."""
    scope = dict(function.__globals__)
    scope.update(overrides)
    bound = types.FunctionType(function.__code__, scope, function.__name__,
                               function.__defaults__, function.__closure__)
    bound.__kwdefaults__ = function.__kwdefaults__
    return bound


def local_source_difference(name, archived_sha, local_sha):
    if archived_sha == local_sha:
        return None
    allowed = {'ai/multimap/runs.json', 'ai/multimap/README.md', 'ai/multimap/launch.py',
               'ai/multimap/gap-launch-v1.json'}
    require(name in allowed and name not in SOURCE_NAMES, 'Local serving/source drift: ' + name)
    return dict(sourceSha256=archived_sha, localSha256=local_sha,
                note='Explicit nonserving docs/launcher/bookkeeping/launch receipt difference; frozen archive still verified against Git.')


def integrity_helpers():
    # Authenticate the reused helper before importing it, even when running unit tests.
    require(digest(HERE / 'audit_neural.py') == sha(git_bytes('ai/multimap/audit_neural.py')),
            'Reused integrity helper differs from frozen source Git')
    import audit_neural as old
    scope = dict(ROOT=ROOT, HERE=HERE, SOURCE=SOURCE, SOURCE_NAMES=SOURCE_NAMES, LIMIT=LIMIT,
                 git_bytes=git_bytes, local_source_difference=local_source_difference)
    return old, reuse(old.verify_source, **scope), verify_reference


def equal(actual, expected, label):
    """Exact JSON structure, finite numeric tolerance only for summation order."""
    if isinstance(expected, dict):
        require(isinstance(actual, dict) and actual.keys() == expected.keys(), label + ': keys')
        for k in expected:
            equal(actual[k], expected[k], label + '.' + k)
    elif isinstance(expected, list):
        require(isinstance(actual, list) and len(actual) == len(expected), label + ': length')
        for i, (a, b) in enumerate(zip(actual, expected)):
            equal(a, b, label + f'[{i}]')
    elif type(actual) in (int, float) and type(expected) in (int, float):
        require(math.isfinite(actual) and math.isfinite(expected) and
                math.isclose(actual, expected, rel_tol=1e-12, abs_tol=1e-12), label + ': number')
    else:
        require(type(actual) is type(expected) and actual == expected, label + ': value')


def finite(value, low=0, high=math.inf):
    return type(value) in (int, float) and math.isfinite(value) and low <= value <= high


def integer(value, high=4000):
    return type(value) is int and 0 <= value <= high


def controller(arm, phase):
    require(arm in POLICIES and phase in PHASES, 'Unknown arm/phase')
    if arm == 'reference':
        return 'reference'
    if arm == 'teacher':
        return 'teacher'
    base, swapped = arm.split('-except-')
    return ('teacher' if base == 'reference' else 'reference') if swapped == phase else base


def prior_diagnostic(gap, agreement=False):
    """Independent specification, including strict epsilon and exact floor."""
    require(finite(gap, 0, 20) and type(agreement) is bool and (not agreement or gap == 0), 'Invalid prior gap')
    return dict(histogramIndex=next(i for i, high in enumerate(BOUNDS) if gap <= high),
                cannotOutscoreTeacherBestWithCurrentBound=gap > 16 + EPSILON,
                exactFloor20=gap == 20, teacherExpertAgreement=agreement)


def expected_plan():
    tasks = []
    for n in range(2, 7):
        for variant in ('original', 'recharged'):
            for fast in (False, True):
                cell = f'Germany|{n}|{variant}|{int(fast)}'
                for deal in range(2):
                    for seat in range(n):
                        for policy in POLICIES:
                            tasks.append(dict(policy=policy, spec=dict(map='Germany', players=n,
                                variant=variant, fastBid=fast, cell=cell, deal=deal,
                                seed=f'{NAMESPACE}:{cell}:{deal}', focalSeat=seat,
                                maxSteps=4000, focalPolicy=policy)))
    return tasks


def key(record):
    return record['spec']['seed'], record['spec']['focalSeat'], record['policy']


def validate_phase(row, high=4000):
    require(isinstance(row, dict) and set(row) == set(COUNTERS), 'Phase counter schema')
    for name in set(COUNTERS) - {'priorGapSum', 'priorGapMax', 'priorGapHistogram'}:
        require(integer(row[name], high), 'Noninteger/out-of-range phase counter')
    n, forced = row['multiActionDecisions'], row['forcedMoves']
    hist, total, maximum = row['priorGapHistogram'], row['priorGapSum'], row['priorGapMax']
    unreachable, floor = row[UNREACHABLE], row['exactFloor20']
    require(n + forced <= high, 'Phase multi+forced exceeds steps')
    require(isinstance(hist, list) and len(hist) == 7 and all(integer(v, n) for v in hist)
            and sum(hist) == n, 'Histogram decision denominator (forced moves excluded)')
    require(row['teacherExpertAgreement'] <= hist[0], 'Agreement requires zero prior gap, not conversely')
    require(finite(total, 0, 20*n) and finite(maximum, 0, 20), 'Invalid gap sum/max')
    require(maximum <= total + 1e-8 and total <= n*maximum + 1e-8, 'Gap sum/max contradiction')
    require(0 <= floor <= unreachable <= hist[-1], 'Floor/unreachable counts')
    require((unreachable > 0) == (maximum > 16 + EPSILON), 'Strict >16+epsilon bound/max contradiction')
    require((floor > 0) == (maximum == 20), 'Exact floor20/max contradiction')
    if n == 0:
        require(total == maximum == 0, 'Nonzero empty diagnostic')
        return
    last = max(i for i, count in enumerate(hist) if count)
    require(maximum <= BOUNDS[last] and (maximum > BOUNDS[last-1] if last else maximum == 0),
            'Histogram occupied bin/max contradiction')
    lower = math.fsum(count*low for count, low in zip(hist, (0, *BOUNDS[:-1])))
    upper = math.fsum(count*min(top, maximum) for count, top in zip(hist, BOUNDS))
    # Last bin splits into (16,16+epsilon], strictly unreachable nonfloor, exact20.
    lower += 4*floor + EPSILON*(unreachable-floor)
    upper -= hist[-1]*min(20, maximum)
    upper += floor*20 + (unreachable-floor)*maximum + (hist[-1]-unreachable)*min(maximum, 16+EPSILON)
    require(lower-1e-7 <= total <= upper+1e-7, 'Histogram/floor/unreachable sum contradiction')


def validate_outcome(record, task, identity_sha):
    fields = {'schema', 'identitySha256', 'spec', 'policy', 'terminal', 'credit', 'seconds', *TERMINAL_FIELDS}
    require(set(record) == fields and record['schema'] == 'multimap-phase-gap-outcome-v1', 'Outcome schema/error')
    require(record['identitySha256'] == identity_sha, 'Outcome identity')
    require(canonical(record['spec']) == canonical(task['spec']) and record['policy'] == task['policy'], 'Task/spec types')
    require(record['terminal'] is True and finite(record['seconds']), 'Nonterminal/error/timing')
    s, credits = task['spec'], record['allSeatCredit']
    require(isinstance(credits, list) and len(credits) == s['players'] and
            all(finite(c, 0, 1) for c in credits), 'Credit vector dimensions/range')
    winners = sum(c > 0 for c in credits)
    require(winners > 0 and all(c == 0 or c == 1/winners for c in credits), 'Credit must be exactly 0 or 1/k')
    require(math.fsum(credits) == 1 and finite(record['credit'], 0, 1) and
            record['credit'] == credits[s['focalSeat']], 'Focal/total credit')
    require(integer(record['steps'], s['maxSteps']) and record['steps'] > 0, 'Steps/cap')
    require(integer(record['rounds'], record['steps']) and record['rounds'] > 0, 'Rounds')
    counts = record['counts']
    require(isinstance(counts, dict) and set(counts) == set(ACTORS), 'Actual-controller schema')
    for phases in counts.values():
        require(isinstance(phases, dict) and set(phases) == set(PHASES) and
                all(integer(v, record['steps']) for v in phases.values()), 'Actual-controller phase counts')
    require(sum(sum(p.values()) for p in counts.values()) == record['steps'], 'Actual-controller total')
    require(isinstance(record['phaseCounters'], dict) and set(record['phaseCounters']) == set(PHASES), 'All diagnostic phases')
    multi, counterfactual, teacher_forced = 0, 0, 0
    for phase in PHASES:
        row = record['phaseCounters'][phase]
        validate_phase(row, record['steps'])
        teacher = controller(task['policy'], phase) == 'teacher'
        own, other = ('focalTeacher', 'focalReference') if teacher else ('focalReference', 'focalTeacher')
        require(counts[own][phase] == row['multiActionDecisions'] + row['forcedMoves'] and
                counts[other][phase] == 0, 'Actual focal routing/forced/multi counts')
        multi += row['multiActionDecisions']
        counterfactual += row['multiActionDecisions'] if teacher else 0
        teacher_forced += row['forcedMoves'] if teacher else 0
    requests = record['steps'] - teacher_forced
    expected = dict(referenceRequests=requests, counterfactualOnly=counterfactual)
    require(isinstance(record['decisions'], dict) and all(integer(v, record['steps']) for v in record['decisions'].values())
            and record['decisions'] == expected, 'Exact expert requests/counterfactual-only counts')
    expected = dict(hiddenInvariant=requests, expertAtomicLegal=requests, fullMenuPrior=multi, teacherAtomicLegal=multi)
    require(isinstance(record['publicChecks'], dict) and all(integer(v, record['steps']) for v in record['publicChecks'].values())
            and record['publicChecks'] == expected, 'Public/legal/full-menu checks')


def phase_totals(record):
    return {p: sum(record['counts'][a][p] for a in ACTORS) for p in PHASES}


def normalized_counts(record):
    return dict(focal={p: record['counts']['focalTeacher'][p] + record['counts']['focalReference'][p]
                       for p in PHASES}, nonfocal=record['counts']['nonfocalReference'])


def verify_outcomes(records, tasks, identity_sha):
    expected = {key(t): t for t in tasks}
    require(len(expected) == len(tasks), 'Duplicate plan')
    actual = {}
    for r in records:
        k = key(r)
        require(k in expected and k not in actual, 'Duplicate/unplanned outcome')
        validate_outcome(r, expected[k], identity_sha)
        actual[k] = r
    require(actual.keys() == expected.keys(), 'Missing arm/seat/deal outcome')
    controls = defaultdict(list)
    for r in records:
        if r['policy'] == 'reference':
            controls[r['spec']['seed']].append(r)
    baseline = []
    for seed, items in sorted(controls.items()):
        n = items[0]['spec']['players']
        require({r['spec']['focalSeat'] for r in items} == set(range(n)), 'Reference seats')
        for field in ('allSeatCredit', 'steps', 'rounds', 'decisions'):
            require(all(r[field] == items[0][field] for r in items), 'Reference rotations disagree: ' + field)
        require(all(phase_totals(r) == phase_totals(items[0]) for r in items), 'Reference full-game phase counts')
        require({p: sum(r['counts']['focalReference'][p] for r in items) for p in PHASES} == phase_totals(items[0]),
                'Reference focal rotations do not partition full-game phase counts')
        rational = [Fraction(1, sum(c > 0 for c in r['allSeatCredit'])) if r['credit'] else Fraction(0) for r in items]
        require(sum(rational) == 1 and math.fsum(r['credit'] for r in items) == 1, 'Reference credits must sum exactly one')
        baseline.append(dict(seed=seed, games=n, terminal=True, focalCreditSum=1,
                             sameCreditVector=True, passed=True, sameTerminalCounts=True))
    return actual, baseline


def read_outcomes(path):
    require(Path(path).stat().st_size <= LIMIT, 'Outcome byte budget')
    result = []
    with Path(path).open('rb') as stream:
        for line in stream:
            require(line.endswith(b'\n') and len(line) <= 64*1024, 'Oversized/truncated JSONL record')
            value = json.loads(line)
            require(line == (canonical(value) + '\n').encode(), 'Noncanonical compact JSONL')
            result.append(value)
    return result


def deal_table(records):
    rows = defaultdict(dict)
    for r in records:
        s = r['spec']
        k = s['cell'], s['deal'], r['policy']
        require(s['focalSeat'] not in rows[k], 'Duplicate paired seat')
        rows[k][s['focalSeat']] = r['credit']
    cells = sorted({k[0] for k in rows})
    require(set(rows) == {(c, d, p) for c in cells for d in range(2) for p in POLICIES}, 'Missing paired deal/arm')
    table = {}
    for (cell, deal, arm), seats in rows.items():
        n = int(cell.split('|')[1])
        require(set(seats) == set(range(n)), 'Missing paired seat')
        table[cell, deal, arm] = math.fsum(seats.values())/n
    return cells, table


def stratified_estimate(strata):
    require(bool(strata) and all(len(xs) == 2 and all(finite(x, -1, 1) for x in xs) for xs in strata), 'Exactly two paired deals per cell required')
    point = statistics.fmean(statistics.fmean(xs) for xs in strata)
    se = math.sqrt(math.fsum(statistics.variance(xs)/2 for xs in strata))/len(strata)
    return dict(mean=point, unbiasedStratifiedPairedSE=se,
                approximateNormal95=[point-1.96*se, point+1.96*se])


def paired_statistics(records):
    cells, table = deal_table(records)
    groups = {'all': cells}
    groups.update({f'players:{n}': [c for c in cells if c.split('|')[1] == str(n)] for n in range(2, 7)})
    for variant in ('original', 'recharged'):
        for fast in (0, 1):
            groups[f'rules:{variant}|{fast}'] = [c for c in cells if c.split('|')[2:] == [variant, str(fast)]]
    groups.update({'cell:' + c: [c] for c in cells})
    result = {}
    for label, group in groups.items():
        arms = {}
        for arm in POLICIES:
            selected = [r for r in records if r['policy'] == arm and r['spec']['cell'] in group]
            estimate = stratified_estimate([[table[c, d, arm] for d in range(2)] for c in group])
            arms[arm] = dict(games=len(selected), creditSum=math.fsum(r['credit'] for r in selected),
                gameMeanCredit=statistics.fmean(r['credit'] for r in selected), macroCellCredit=estimate.pop('mean'),
                **estimate, pairedDealDifferences={control: stratified_estimate(
                    [[table[c, d, arm]-table[c, d, control] for d in range(2)] for c in group])
                    for control in ('reference', 'teacher')})
        result[label] = dict(strata=len(group), independentDeals=2*len(group),
                            seatsPerArm=sum(2*int(c.split('|')[1]) for c in group), policies=arms)
    return result


def phase_aggregates(records):
    result = {}
    for arm in POLICIES:
        items = [r for r in records if r['policy'] == arm]
        result[arm] = {}
        for phase in PHASES:
            rows = [r['phaseCounters'][phase] for r in items]
            row = {k: math.fsum(r[k] for r in rows) if k == 'priorGapSum' else sum(r[k] for r in rows)
                   for k in COUNTERS if k not in ('priorGapMax', 'priorGapHistogram')}
            row['priorGapMax'] = max(r['priorGapMax'] for r in rows)
            row['priorGapHistogram'] = [sum(r['priorGapHistogram'][i] for r in rows) for i in range(7)]
            n = row['multiActionDecisions']
            validate_phase(row, sum(r['steps'] for r in items))
            row.update(terminalGames=len(items), agreementRate=row['teacherExpertAgreement']/n if n else None,
                       meanPriorGap=row['priorGapSum']/n if n else None, actualController=controller(arm, phase))
            result[arm][phase] = row
    return result


def legacy_mean_se(values):
    return dict(mean=statistics.fmean(values), independentDeals=len(values),
                dealStandardError=statistics.stdev(values)/math.sqrt(len(values)))


def verify_summary(stored, records, baseline, identity_sha, protocol):
    cells, table = deal_table(records)
    cell_rows, policies = [], {}
    for c in cells:
        n = int(c.split('|')[1])
        for p in POLICIES:
            items = [r for r in records if r['policy'] == p and r['spec']['cell'] == c]
            cell_rows.append(dict(cell=c, policy=p, plannedGames=2*n, games=2*n, terminalGames=2*n,
                failures=0, creditSum=math.fsum(r['credit'] for r in items),
                gameMeanCredit=statistics.fmean(r['credit'] for r in items), plannedIndependentDeals=2,
                **legacy_mean_se([table[c, d, p] for d in range(2)])))
    for p in POLICIES:
        items = [r for r in records if r['policy'] == p]
        policies[p] = dict(games=160, plannedGames=160, failures=0,
            creditSum=math.fsum(r['credit'] for r in items), gameMeanCredit=statistics.fmean(r['credit'] for r in items),
            completeCells=20, macroCellCredit=statistics.fmean(table[c, d, p] for c in cells for d in range(2)),
            pairedDealDifferences={b: legacy_mean_se([table[c, d, p]-table[c, d, b] for c in cells for d in range(2)])
                                   for b in ('reference', 'teacher')})
    expected = dict(schema='multimap-phase-gap-summary-v1', games=1600, plannedGames=1600, complete=True,
        failures=0, cells=cell_rows, policies=policies, independentDeals=40, plannedIndependentDeals=40,
        allReferenceControl=baseline, baselineViolations=[], qualificationStopped=False, qualified=False,
        qualification_eligible=False, reserved_final_seeds_used=False, fitted=False, selected=False,
        identitySha256=identity_sha, phaseDiagnostics=phase_aggregates(records),
        priorGapHistogramLabels=['zero', '(0,2]', '(2,4]', '(4,8]', '(8,12]', '(12,16]', '(16,20]'],
        priorBoundExplanation=protocol['priorBoundExplanation'])
    require(set(stored) == set(expected) | {'note'} and isinstance(stored['note'], str), 'Stored summary schema')
    equal({k: stored[k] for k in expected}, expected, 'Independently reconstructed summary including legacy unstratified SE')


def resource_comparisons(actual):
    report = {}
    for base in ('reference', 'teacher'):
        rows = []
        for (seed, seat, arm), r in actual.items():
            if arm != base:
                continue
            other = actual[seed, seat, base + '-except-Resources']
            rows.append((r, other))
        changed = {f: sum(a[f] != b[f] for a, b in rows) for f in ('credit', *TERMINAL_FIELDS)}
        report[base + '-except-Resources'] = dict(control=base, pairedSeatGames=len(rows),
            differingFields=changed,
            differingNormalizedActualCounts=sum(normalized_counts(a) != normalized_counts(b) for a, b in rows),
            differingPhaseCounters={p: sum(a['phaseCounters'][p] != b['phaseCounters'][p] for a, b in rows) for p in PHASES},
            differingPhaseCounterFields={p: {k: sum(a['phaseCounters'][p][k] != b['phaseCounters'][p][k] for a, b in rows)
                                            for k in COUNTERS} for p in PHASES},
            changedTerminalVectorCases=[dict(seed=a['spec']['seed'], focalSeat=a['spec']['focalSeat'],
                controlVector=a['allSeatCredit'], resourceSwapVector=b['allSeatCredit'],
                controlSteps=a['steps'], resourceSwapSteps=b['steps'], focalCredit=a['credit'])
                for a, b in rows if a['allSeatCredit'] != b['allSeatCredit']],
            caveat='Only compact terminal/counter signatures were saved. Different counters do not identify the action sequence; '
                   'equal signatures do not prove identical trajectories. Resource-order differences could preserve bought fuel, '
                   'but identical bought fuel is NOT verified by these records. Controller labels/service counts also change by design.')
    return report


def timings(records):
    result = {}
    for arm in ('all', *POLICIES):
        rows = records if arm == 'all' else [r for r in records if r['policy'] == arm]
        result[arm] = dict(games=len(rows), summedGameSeconds=math.fsum(r['seconds'] for r in rows),
            meanGameSeconds=statistics.fmean(r['seconds'] for r in rows),
            minSteps=min(r['steps'] for r in rows), maxSteps=max(r['steps'] for r in rows),
            totalSteps=sum(r['steps'] for r in rows), totalRounds=sum(r['rounds'] for r in rows),
            actualControllerCounts={a: {p: sum(r['counts'][a][p] for r in rows) for p in PHASES} for a in ACTORS},
            decisions={k: sum(r['decisions'][k] for r in rows) for k in ('referenceRequests', 'counterfactualOnly')},
            publicChecks={k: sum(r['publicChecks'][k] for r in rows) for k in rows[0]['publicChecks']},
            tiedTerminalGames=sum(sum(c > 0 for c in r['allSeatCredit']) > 1 for r in rows))
    return result


def verify_reference(protocol, recovery, remote):
    """Rehash the complete existing artifact; the gap recovery fetched NO PPO."""
    artifact = ROOT / 'ai/runs/multimap-reference-preflight-v1/artifact'
    ref = protocol['reference']
    for file, name in (('manifest.json', 'runtimeManifestSha256'), ('policy.json', 'policySha256')):
        equal(digest(artifact / file), ref[name], 'Reference ' + name)
        equal(recovery[name], ref[name], 'Recovery ' + name)
    require(not artifact.is_symlink(), 'Reference root symlink')
    manifest = json.loads((artifact / 'manifest.json').read_text())
    actual = set()
    for path in artifact.rglob('*'):
        require(not path.is_symlink(), 'Reference artifact symlink')
        if path.is_file():
            actual.add(path.relative_to(artifact).as_posix())
    require(actual == set(manifest) | {'manifest.json', 'policy.json'}, 'Complete unchanged reference file set')
    require(len(manifest) == 1467, 'All 1467 reference members required')
    for name, checksum in manifest.items():
        path = PurePosixPath(name)
        require(not path.is_absolute() and '..' not in path.parts and '\\' not in name
                and path.as_posix() == name, 'Unsafe reference member')
        equal(digest(artifact / name), checksum, 'Reference member ' + name)
    descriptor = json.loads((artifact / 'policy.json').read_text())
    equal(descriptor, dict(backend=ref['backend'], feature_revision=ref['featureRevision'],
        model=dict(path='policy.onnx', sha256=ref['modelSha256']),
        runtime_manifest=dict(path='manifest.json', sha256=ref['runtimeManifestSha256']),
        settings=ref['settings'], version=1), 'Exact FILTER descriptor/settings')
    equal(manifest['policy.onnx'], ref['modelSha256'], 'Reference ONNX manifest')
    equal(recovery['modelSha256'], ref['modelSha256'], 'Recovery ONNX pin')
    equal(recovery['pins'], dict(source=ref['sourcePin'], model=ref['modelPin']), 'Gap recovery pins, no candidate')
    metadata = {}
    for kind, pin in recovery['pins'].items():
        entry = remote.describe(pin)
        metadata[kind] = dict(bytes=entry.size, gitBlob=entry.blob_id,
            lfsSha256=entry.lfs.sha256 if entry.lfs else None,
            contentVerification='All recovered members independently rehashed; old archive not downloaded' if kind == 'source' else 'Local recovered ONNX independently hashed')
        if kind == 'source':
            equal(recovery['sourceDownload'], dict(bytes=entry.size, revision=pin['revision']), 'HF original reference recovery metadata')
            require(entry.size <= protocol['compressedArchiveRamMaxBytes'], 'Original recovery RAM budget')
        else:
            equal(digest(artifact / 'policy.onnx'), pin['sha256'], 'Reference model content')
            equal((artifact / 'policy.onnx').stat().st_size, entry.size, 'Reference model bytes')
    require(recovery['schema'] == 'multimap-phase-gap-recovery-v1' and recovery['exactServiceReady'] is True
            and recovery['omitted'] == [] and recovery['reserved_final_seeds_used'] is False
            and recovery['recoveryMode'] == 'complete-unchanged-manifest-no-candidate-fetch', 'Recovery completeness/no model substitution')
    equal(recovery['locallyVerifiedFiles'], len(manifest), 'Recovered member count')
    artifact_bytes = sum((artifact / name).stat().st_size for name in actual)
    equal(recovery['cacheBytes'], artifact_bytes, 'HF complete artifact bytes (no candidate)')
    equal(recovery['diskBudgetBytes'], protocol['referenceCacheMaxBytes'], 'Recovery disk budget')
    local_bytes = sum(p.stat().st_size for p in artifact.parent.rglob('*') if p.is_file())
    require(artifact_bytes <= local_bytes <= protocol['referenceCacheMaxBytes'], 'Local cache budget')
    return dict(manifestFiles=len(manifest), artifactBytes=artifact_bytes, localCacheBytes=local_bytes,
        runtimeManifestSha256=ref['runtimeManifestSha256'], policySha256=ref['policySha256'],
        modelSha256=ref['modelSha256'], settings=descriptor['settings'], pins=recovery['pins'],
        immutableRemoteMetadata=metadata, recoveredArtifactAllHashesVerified=True,
        archivedSourceVerification='Old 130442976-byte compressed reference source was NOT downloaded again. '
            'Immutable HF metadata/LFS pointer and original job recovery receipt checked; all 1467 recovered '
            'manifest members independently rehashed locally with exact file-set/descriptor/model checks. '
            'Existing 451257098-byte artifact reused without omission, repair or loader bypass.')


def verify_environment(protocol, environment, plan):
    expected_versions = dict(environment['versions'], torchInferenceUsed=False)
    equal(plan['runtimeVersions'], expected_versions, 'Plan/environment versions')
    require(environment['torchInferenceUsed'] is False and environment['referenceVenvBytes'] <= protocol['referenceVenvMaxBytes'], 'Inference/environment budget')
    equal(environment['requirementsSha256'], protocol['referenceRequirementsSha256'], 'Requirements pin')
    code = ('import json,sys,importlib.metadata as m;print(json.dumps(dict(python=list(sys.version_info[:3]),'
            'packages={d.metadata["Name"]:d.version for d in m.distributions()})))')
    local_ref = json.loads(subprocess.check_output([str(ROOT / 'ai/.venv-reference/bin/python'), '-B', '-c', code], text=True))
    local = dict(reference=dict(python=local_ref['python'], numpy=local_ref['packages']['numpy'],
        onnxruntime=local_ref['packages']['onnxruntime']), controllerEnvironment=dict(python=list(sys.version_info[:3]),
        **{n: importlib.metadata.version(n) for n in ('torch', 'numpy', 'huggingface-hub')}),
        node=subprocess.check_output(['node', '--version'], text=True).strip())
    equal(local, environment['versions'], 'Exact recorded local/HF principal versions')
    for label, versions in (('HF', environment['versions']), ('local', local)):
        ref = versions['reference']
        equal(ref['numpy'], protocol['referenceEnvironment']['numpyPython312Plus' if ref['python'][:2] >= [3, 12] else 'numpyPython311'], label + ' reference NumPy')
        equal(ref['onnxruntime'], protocol['referenceEnvironment']['onnxruntime'], label + ' reference ONNX')
        for name, version in protocol['torchEnvironment'].items():
            equal(versions['controllerEnvironment'][name], version, label + ' controller metadata')
    return dict(recorded=environment, replayVersions=local, localReferencePackages=local_ref['packages'],
        caveat='Historical requirements-serve pins only NumPy and ONNX Runtime. Transitive dependencies are not fully pinned '
               'and no full package inventory was recorded by the HF job. Matching principal versions is not a complete '
               'Python environment reproducibility claim. Torch metadata only: no candidate load/forward in this diagnostic.')


def replay_tasks(tasks):
    chosen = []
    for i, arm in enumerate(POLICIES):
        n, variant, fast = 2+i % 5, ('original', 'recharged')[(i//2) % 2], bool(i % 2)
        choices = [t for t in tasks if t['policy'] == arm and t['spec']['players'] == n
                   and t['spec']['variant'] == variant and t['spec']['fastBid'] == fast]
        chosen.append(min(choices, key=object_sha))
    require(len({key(t) for t in chosen}) == 10 and {t['policy'] for t in chosen} == set(POLICIES), 'Replay arm coverage')
    require({t['spec']['players'] for t in chosen} == set(range(2, 7)), 'Replay player-count coverage')
    require({(t['spec']['variant'], t['spec']['fastBid']) for t in chosen} ==
            {(v, f) for v in ('original', 'recharged') for f in (False, True)}, 'Replay four-rule coverage')
    return chosen


def replay(tasks, actual, identity_sha):
    from gap_study import WorkerRuntime, play_game
    start = time.monotonic()
    runtime = WorkerRuntime(ROOT / 'ai/runs/multimap-reference-preflight-v1/artifact', ROOT / 'ai/.venv-reference/bin/python')
    rows = []
    fields = ['schema', 'identitySha256', 'spec', 'policy', 'terminal', 'credit', *TERMINAL_FIELDS]
    try:
        for task in replay_tasks(tasks):
            result = play_game(task, runtime.bridge, runtime.reference, identity_sha)
            validate_outcome(result, task, identity_sha)
            original = actual[key(task)]
            for field in fields:
                require(result[field] == original[field], 'Exact deterministic replay mismatch: ' + field)
            rows.append(dict(policy=task['policy'], spec=task['spec'], matched=True,
                seconds=result['seconds'], originalSeconds=original['seconds'], steps=result['steps'], rounds=result['rounds'],
                allSeatCredit=result['allSeatCredit'], credit=result['credit'],
                comparedFieldsSha256=object_sha({f: result[f] for f in fields})))
            print(canonical(dict(stage='replay', completed=len(rows), policy=task['policy'], seconds=result['seconds'])), flush=True)
    finally:
        runtime.close()
    return dict(games=len(rows), matched=len(rows), seconds=time.monotonic()-start,
        selection='One per arm, all five counts and all four rule pairs; lowest canonical-task SHA256 in predefined slots, outcome-blind.',
        comparisonFields=fields, rows=rows,
        note='All terminal fields, actual-controller counts, phase histograms/counters and expert/public-check counters '
             'matched EXACTLY, not approximately. Timings excluded. No saved action trace or new deal.')


def local_tests():
    commands = [
        ('auditPython', [sys.executable, '-B', '-m', 'unittest', 'discover', '-s', 'ai/multimap', '-p', 'test_audit_gap.py'], 'Ran 16 tests', 16),
        ('frozenGapPython', [sys.executable, '-B', '-m', 'unittest', 'discover', '-s', 'ai/multimap', '-p', 'test_gap.py'], 'Ran 17 tests', 17),
        ('frozenGapNode', ['node', '--test', 'ai/multimap/test_gap.cjs'], 'pass 7', 7),
    ]
    result = {}
    for name, command, marker, count in commands:
        done = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=120)
        output = done.stdout + done.stderr
        require(done.returncode == 0 and marker in output and ('\nOK\n' in output if name.endswith('Python') else 'skipped 0' in output),
                'Local test failure: ' + name + '\n' + output)
        result[name] = dict(command=command, passed=count, skipped=0, outputSha256=sha(output.encode()))
    gaps = [0, 2, 4, 8, 12, 16, 16+0.5e-9, 16+1e-9, 16+2e-9, 20-1e-10, 20]
    code = "const g=require('./ai/multimap/gap_game.cjs');console.log(JSON.stringify(" + json.dumps(gaps) + ".map(x=>g.priorDiagnostic([-x,0],0,1))))"
    checked = json.loads(subprocess.check_output(['node', '-e', code], cwd=ROOT, text=True))
    expected = [dict(priorGap=g, **prior_diagnostic(g)) for g in gaps]
    equal(checked, expected, 'Frozen Node strict bound/floor diagnostics independently specified')
    result['independentNodeBoundaryCases'] = dict(cases=len(gaps), passed=len(gaps),
        note='Fixed mathematical boundary probes, not extra game trials or saved training fixtures.')
    return result


def audit(output):
    from huggingface_hub import HfApi
    started = time.monotonic()
    old, verify_source, verify_reference = integrity_helpers()
    api, remote = HfApi(), None
    remote = old.RemoteFiles(api)
    receipt_path = HERE / 'gap-launch-v1.json'
    equal(digest(receipt_path), sha(git_bytes('ai/multimap/gap-launch-v1.json', RECEIPT_COMMIT)), 'Pinned launch receipt')
    receipt = json.loads(receipt_path.read_text())
    for name, value in dict(run=RUN, jobId=JOB, sourceCommit=SOURCE).items():
        equal(receipt[name], value, 'Launch ' + name)
    job = api.inspect_job(job_id=JOB)
    require(job.status.stage == 'COMPLETED', 'HF job incomplete')
    equal(job.environment, receipt['env'], 'HF job/source environment')
    equal(job.docker_image, receipt['image'], 'HF image')
    equal(job.flavor, receipt['flavor'], 'HF flavor')
    launch_ast = ast.parse(git_bytes('ai/multimap/launch.py'))
    bootstrap_nodes = [n.value for n in launch_ast.body if isinstance(n, ast.Assign)
                       and any(isinstance(t, ast.Name) and t.id == 'BOOTSTRAP' for t in n.targets)]
    require(len(bootstrap_nodes) == 1, 'Single frozen bootstrap constant')
    bootstrap = ast.literal_eval(bootstrap_nodes[0])
    expected_command = ['bash', '-lc', 'python -m pip install --disable-pip-version-check huggingface_hub==1.29.0 && python -c '+shlex.quote(bootstrap)]
    equal(job.command, expected_command, 'HF command executes frozen hash-checked archive/bootstrap')
    require(not job.arguments, 'Unexpected HF job argument overrides')
    info = api.model_info(REPO, revision=REVISION, files_metadata=True)
    require(info.private and info.sha == REVISION, 'Private immutable model repository')
    prefix = f'runs/{RUN}/'
    metadata = {s.rfilename[len(prefix):]: s for s in info.siblings if s.rfilename.startswith(prefix)}
    require(set(metadata) == ARTIFACT_NAMES, 'Unexpected/noncompact artifacts')
    total_bytes = sum(s.size for s in metadata.values())
    require(total_bytes <= LIMIT, 'Metadata-first compact budget')
    manifest_path = remote.get(dict(repo=REPO, revision=REVISION, path=prefix+'artifacts.json'), metadata['artifacts.json'])
    manifest = json.loads(manifest_path.read_text())
    require(set(manifest) == ARTIFACT_NAMES-{'artifacts.json'}, 'Full compact manifest coverage')
    mapping = json.loads((ROOT / f'ai/runs/{RUN}/audit/files.json').read_text())
    require(set(mapping) == set(manifest), 'Cached file mapping coverage')
    files = {name: remote.get(dict(repo=REPO, revision=REVISION, path=prefix+name, sha256=checksum),
                             metadata[name], cached=mapping[name]) for name, checksum in manifest.items()}
    protocol = json.loads(git_bytes('ai/multimap/gap-protocol-v1.json'))
    equal(json.loads(files['protocol.json'].read_text()), protocol, 'Frozen uploaded protocol')
    plan = json.loads(files['study/plan.json'].read_text())
    require(set(plan) == {'schema', 'protocol', 'smoke', 'tasks', 'sourceFiles', 'generatorDigest', 'runtimeVersions', 'execution'}, 'Complete plan identity')
    equal(plan['protocol'], protocol, 'Frozen plan protocol')
    require(plan['schema'] == 'multimap-phase-gap-plan-v1' and plan['smoke'] is False, 'Full diagnostic plan')
    equal(plan['execution'], dict(workers=6, startMethod='spawn', threads=1, referenceThreads=1, torchInferenceUsed=False), 'Execution')
    for name, value in dict(policies=list(POLICIES), phases=list(PHASES), dealsPerCell=2, games=1600,
        independentDeals=40, cells=20, gamesPerPolicy=160, maxSteps=4000, priorFloor=-20,
        residualBound=8, priorGapEpsilon=EPSILON, priorGapHistogramUpperBounds=list(BOUNDS),
        qualificationEligible=False, fitting=False, selection=False, reservedFinalSeedsUsed=False).items():
        equal(protocol[name], value, 'Independent protocol ' + name)
    equal(protocol['phaseRoutes'], {a: {p: controller(a, p) for p in PHASES} for a in POLICIES}, 'Independent phase routing')
    tasks = expected_plan()
    require(len(tasks) == 1600, 'Design arithmetic')
    require(canonical(plan['tasks']) == canonical(tasks), 'Independently constructed plan with exact JSON types')
    identity_sha = object_sha(plan)
    records = read_outcomes(files['study/games.jsonl'])
    actual, baseline = verify_outcomes(records, tasks, identity_sha)
    require(len(baseline) == 40, 'All-reference control coverage')
    stored = json.loads(files['study/summary.json'].read_text())
    verify_summary(stored, records, baseline, identity_sha, protocol)
    groups = paired_statistics(records)
    status = json.loads(files['status.json'].read_text())
    require(status['stage'] == 'complete' and 'error' not in status and 'resume' not in status, 'Failed/resumed status')
    equal(status['result'], stored, 'Status/summary')
    equal(status['protocol'], protocol, 'Status/protocol')
    for name, value in dict(run=RUN, workflow='gap', smoke=False, workers=6, fitted=False, selected=False,
                            qualified=False, qualification_eligible=False, reserved_final_seeds_used=False).items():
        equal(status[name], value, 'Status ' + name)
    for field, env in (('sourceRevision', 'SOURCE_REVISION'), ('sourceSha256', 'SOURCE_SHA256'),
                       ('sourcePath', 'SOURCE_PATH'), ('sourceRepo', 'DATASET_REPO')):
        equal(status[field], receipt['env'][env], 'Source receipt ' + field)
    equal([x['stage'] for x in status['receipts']], ['runtime-ready', 'planned',
        *[f'games-{n}' for n in range(120, 1600, 120)], 'games-1600', 'screen-complete'], 'Progress receipt coverage')
    source_pin = dict(repo=receipt['env']['DATASET_REPO'], repo_type='dataset', revision=receipt['env']['SOURCE_REVISION'],
                      path=receipt['env']['SOURCE_PATH'], sha256=receipt['env']['SOURCE_SHA256'])
    source_report = verify_source(remote.get(source_pin), plan)
    source_report['note'] = ('All source archive members rehashed without extraction; full manifest/file-set coverage, '
        'tracked bytes verified against frozen Git, all local serving/engine/Node/dependency bytes matched. '
        'Only explicitly listed README/launch.py/runs.json/gap-launch-v1.json nonserving changes allowed. '
        'New unrelated files are not on the frozen execution path. gap_study reuses archived neural helpers via '
        'FunctionType with a private global snapshot; no old-module global mutation.')
    source_report['integrityHelperSha256'] = digest(HERE / 'audit_neural.py')
    source_report['dependencyVersions'] = {n: subprocess.check_output(['node', '-p',
        f"require(require.resolve('{n}/package.json',{{paths:['./engine']}})).version"], cwd=ROOT, text=True).strip()
        for n in ('lodash', 'seedrandom', 'delaunator')}
    equal(json.loads(git_bytes('engine/package.json'))['version'], '2.0.22', 'Authoritative engine release')
    recovery = json.loads(files['recovery.json'].read_text())
    reference_report = verify_reference(protocol, recovery, remote)
    environment_report = verify_environment(protocol, json.loads(files['environment.json'].read_text()), plan)
    local_test_report = local_tests()
    print(canonical(dict(stage='audit-verified', games=len(records), independentDeals=40, artifactBytes=total_bytes)), flush=True)
    replays = replay(tasks, actual, identity_sha)
    log_path = ROOT / f'ai/runs/{RUN}/job.log'
    log = log_path.read_text()
    require('pass 7' in log and 'skipped 0' in log and 'Ran 17 tests' in log and '\nOK\n' in log and REVISION in log,
            'HF job test log evidence')
    comparisons = resource_comparisons(actual)
    report = dict(schema='multimap-independent-phase-gap-audit-v1', run=RUN, jobId=JOB, repo=REPO,
        revision=REVISION, sourceCommit=SOURCE, launchReceiptCommit=RECEIPT_COMMIT,
        launchReceiptSha256=digest(receipt_path), auditorSha256=digest(__file__), testsSha256=digest(HERE / 'test_audit_gap.py'),
        identitySha256=identity_sha, artifactManifestSha256=digest(manifest_path), artifactsVerified=len(manifest),
        artifactBytes=total_bytes, boundedInputBytes=remote.bounded_bytes, inputBudgetBytes=LIMIT,
        verifiedRemoteFiles=remote.evidence, source=source_report, reference=reference_report, environment=environment_report,
        coverage=dict(cells=20, dealsPerCell=2, independentDeals=40, seatsPerArm=160, policies=list(POLICIES),
            games=1600, terminalGames=1600, failures=0, caps=0, duplicateOutcomes=0, missingOutcomes=0,
            completePlanVerified=True, allCreditVectorsEqualWinnerShares=True, allReferenceDealsVerified=40,
            allReferenceCreditVectorsAndTotalPhaseCountsIdenticalAcrossSeats=True,
            allReferenceFocalCountsPartitionFullGame=True, allReferenceFocalCreditSumsExactlyOne=True,
            actualRoutingAndExpertCounterfactualCountsVerified=True, forcedMovesExcludedFromDiagnosticDenominators=True,
            fullStoredSummaryIndependentlyReproduced=True),
        groups=groups, phaseDiagnostics=phase_aggregates(records),
        phaseDiagnosticsByPlayerCount={str(n): phase_aggregates([r for r in records if r['spec']['players'] == n]) for n in range(2, 7)},
        priorGapHistogramUpperBounds=list(BOUNDS), priorBoundExplanation=protocol['priorBoundExplanation'],
        resourceSwapComparisons=comparisons, timings=timings(records), errors=[], replays=replays, localTests=local_test_report,
        hfJob=dict(stage=job.status.stage, startedAt=str(job.started_at), finishedAt=str(job.finished_at),
            runningSeconds=job.durations.running_secs, totalSeconds=job.durations.total_secs,
            image=job.docker_image, flavor=job.flavor, nodeTestsPassed=7, nodeTestsSkipped=0,
            pythonTestsPassed=17, testLogSha256=digest(log_path), commandSha256=object_sha(job.command),
            frozenBootstrapSha256=sha(bootstrap.encode()), commandMatchedFrozenLauncher=True),
        uncertainty=dict(primaryEstimand='Equal-weight macro credit over 20 fixed Germany cells; average all focal seats within each deal first.',
            independentUnit='40 paired independent deals (2 per cell), NOT 1600 independent games. Seat and arm repetitions share deals.',
            formula='For H fixed cells: mean = mean_h mean_d (seatMean(arm)-seatMean(control)); SE = sqrt(sum_h s_h^2/2)/H; s_h^2 uses ddof=1.',
            interval='Approximate normal point +/-1.96*unbiased stratified paired SE, without clipping or bootstrap.',
            caveats=['Only two clusters per cell: each within-cell variance has ONE degree of freedom; normal intervals can be unreliable, especially in cells/subgroups.',
                'Zero observed variance with two deals is limited information, not proof of zero uncertainty or effect equivalence.',
                'All ten arms, five player counts, four rule pairs and 20 cells reported. No multiplicity correction; exploratory, not qualification.',
                'All-reference 1/n per deal is an exact all-seat design identity. Its zero stratified SE is not certainty about general playing strength.',
                'Decision counts are dependent observations along games, with correlated focal-seat/arm repeats; they are NOT independent Bernoulli trials. No naive decision-rate confidence intervals.',
                'Each arm visits its own states. Phase-swap effects include downstream interactions and do not add up; diagnostic disagreement is not a causal per-action effect.',
                'Stored summary legacy unstratified SEs were independently reproduced, but this report uses fixed-cell paired stratification.',
                'Germany-only, fixed reference population, tiny diagnostic sample; no claims about other maps, humans, production or qualification.',
                'No raw action traces were saved. Compact invariants checked for all outcomes, legality/routing replayed for ten; not an independent reconstruction of every recorded action.']),
        qualified=False, qualification_eligible=False, fitted=False, selected=False, promoted=False,
        reserved_final_seeds_used=False, auditSeconds=time.monotonic()-started,
        conclusion='Auction and Building are the next learning targets, not production candidates selected from these diagnostic arms. '
            'Auction has substantial strict >16+epsilon prior-bound exclusions; Building has consequential phase-swap effects '
            'without such exclusions here. Resources/Bureaucracy show zero unreachable counters and small/zero macro effects. '
            'Equal Resource-swap macro/focal credits do NOT imply identical trajectories or all terminal vectors: reference '
            'Resource swaps preserve all 160 vectors but change 90 phase-counter signatures; teacher Resource swaps preserve '
            'all 160 focal credits but change 2 nonfocal terminal vectors and 84 phase-counter signatures. '
            'No arm is selected, promoted, or qualification-eligible.')
    output = Path(output)
    require(output.resolve() == (HERE / 'gap-results-v1.json').resolve(), 'Only requested new result file may be written')
    output.write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
    print(canonical(dict(stage='audit-complete', output=str(output), games=1600, replays=len(replays['rows']),
                         macroCredit={p: groups['all']['policies'][p]['macroCellCredit'] for p in POLICIES})), flush=True)
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--output', type=Path, default=HERE / 'gap-results-v1.json')
    args = parser.parse_args()
    for name in ('OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'NUMEXPR_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS'):
        os.environ[name] = '1'
    os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
    audit(args.output)
