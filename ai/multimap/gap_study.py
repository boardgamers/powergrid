"""Frozen phase-gap attribution, not learning/selection/qualification.

API: plan(smoke=False), run(output, *, artifact, reference_python, workers=6,
smoke=False, callback=None). CLI --smoke runs 20 games, full plan 1600.
Only compact per-game aggregates are saved. Exact public requests are transient.

The proven neural_study collector is composed with diagnostic callbacks through
an isolated function-global namespace. This is dependency injection, NOT module
monkeypatching: no old helper/global/file is changed, and spawn targets remain
normal top-level functions. The shared coordinator supplies bounded queues,
fsynced JSONL, strict resume, stop-on-error, process-group cleanup and checkpoints.
No candidate loading, Torch import or forward occurs on this execution path.
"""
import argparse
from collections import defaultdict
import itertools
import json
import math
import os
from pathlib import Path
import time
import types

import neural_study as shared
from data import ROOT, atomic_json, digest, generator_digest
from reference_evaluate import LineProcess, ReferenceProcess
from reference_recover import CACHE, DESCRIPTOR_SHA, MANIFEST_SHA, PINS, budget

HERE = Path(__file__).resolve().parent
PROTOCOL = json.loads((HERE / 'gap-protocol-v1.json').read_text())
OUTCOME_SCHEMA = 'multimap-phase-gap-outcome-v1'
THREAD_ENV = shared.THREAD_ENV
MAX_LINE = shared.MAX_LINE
canonical, object_sha, finite, key = shared.canonical, shared.object_sha, shared.finite, shared.key
PHASES = ('Auction', 'Resources', 'Building', 'Bureaucracy')
ACTORS = ('focalReference', 'focalTeacher', 'nonfocalReference')
CHECKS = ('hiddenInvariant', 'expertAtomicLegal', 'fullMenuPrior', 'teacherAtomicLegal')
COUNTERS = ('multiActionDecisions', 'forcedMoves', 'teacherExpertAgreement', 'priorGapSum',
            'priorGapMax', 'priorGapHistogram', 'cannotOutscoreTeacherBestWithCurrentBound', 'exactFloor20')


def reuse(function, **overrides):
    """Bind the unchanged generic helper to a private dependency snapshot.

    No exec/source rewriting, mutation of function.__globals__, or modifications
    to frozen modules. Source hashes include all modules whose code is reused.
    Construct per invocation so test dependency injection is also local.
    """
    namespace = dict(function.__globals__)
    namespace.update(globals())
    namespace.update(overrides)
    bound = types.FunctionType(function.__code__, namespace, function.__name__,
                               function.__defaults__, function.__closure__)
    bound.__kwdefaults__ = function.__kwdefaults__
    return bound


def controller(policy, phase):
    if policy not in PROTOCOL['policies'] or phase not in PHASES:
        raise ValueError('Unknown diagnostic arm/phase')
    return PROTOCOL['phaseRoutes'][policy][phase]


def validate_protocol():
    policies = ['reference', 'teacher'] + [f'reference-except-{p}' for p in PHASES] + [f'teacher-except-{p}' for p in PHASES]
    expected = dict(schema='multimap-phase-gap-protocol-v1',
                    seedNamespace='pg-multimap-phase-gap-20261102-v1',
                    smokeNamespace='pg-multimap-phase-gap-smoke-20261102-v1', maps=['Germany'],
                    players=[2, 3, 4, 5, 6], variants=['original', 'recharged'], fastBids=[False, True],
                    dealsPerCell=2, allFocalSeats=True, phases=list(PHASES), policies=policies,
                    cells=20, independentDeals=40, gamesPerPolicy=160, games=1600, smokeGames=20,
                    maxSteps=4000, workers=6, allowedWorkers=[1, 2, 3, 4, 5, 6], threads=1,
                    referenceThreads=1, startMethod='spawn', uploadEveryGames=120,
                    authoritativeEngineRelease='2.0.22', referenceCacheMaxBytes=512 * 1024**2,
                    studyArtifactMaxBytes=128 * 1024**2, referenceVenvMaxBytes=256 * 1024**2,
                    compressedArchiveRamMaxBytes=256 * 1024**2,
                    priorFloor=-20, residualBound=8, priorGapEpsilon=1e-9,
                    priorGapHistogramUpperBounds=[0, 2, 4, 8, 12, 16, 20],
                    modelRepo='coyotte508/powergrid-ai-multimap-v1',
                    qualificationEligible=False, fitting=False, selection=False, reservedFinalSeedsUsed=False)
    for name, value in expected.items():
        if canonical(PROTOCOL.get(name)) != canonical(value):
            raise ValueError('Frozen diagnostic protocol changed: ' + name)
    for arm in policies:
        for phase in PHASES:
            teacher = arm == 'teacher' or arm == f'reference-except-{phase}' or (
                arm.startswith('teacher-except-') and arm != f'teacher-except-{phase}')
            if controller(arm, phase) != ('teacher' if teacher else 'reference'):
                raise ValueError('Frozen diagnostic phase routing changed')
    ref = PROTOCOL['reference']
    if (ref != shared.PROTOCOL['reference'] or ref['runtimeManifestSha256'] != MANIFEST_SHA or
            ref['policySha256'] != DESCRIPTOR_SHA or ref['modelSha256'] != PINS['model']['sha256'] or
            ref['sourcePin'] != PINS['source'] or ref['modelPin'] != PINS['model']):
        raise ValueError('Frozen reference identity changed')
    prior = json.loads((HERE / 'ppo-protocol-v1.json').read_text())
    if prior['priorFloor'] != -20 or prior['residualBound'] != 8:
        raise ValueError('Frozen prior-bound math changed')
    if digest(ROOT / 'ai/requirements-serve.txt') != PROTOCOL['referenceRequirementsSha256']:
        raise ValueError('Exact reference requirements changed')
    if json.loads((ROOT / 'engine/package.json').read_text())['version'] != '2.0.22':
        raise ValueError('Authoritative engine release changed')
    if not (ROOT / 'engine/dist/index.js').is_file():
        raise ValueError('Authoritative compiled engine missing')
    return PROTOCOL


def plan(smoke=False):
    if type(smoke) is not bool:
        raise ValueError('smoke must be boolean')
    tasks = []
    namespace = PROTOCOL['smokeNamespace'] if smoke else PROTOCOL['seedNamespace']
    for m, n, v, fast in itertools.product(PROTOCOL['maps'], PROTOCOL['players'], PROTOCOL['variants'], PROTOCOL['fastBids']):
        if smoke and (n != 2 or v != 'original' or fast):
            continue
        cell = f'{m}|{n}|{v}|{int(fast)}'
        for deal in range(1 if smoke else PROTOCOL['dealsPerCell']):
            for seat in range(n):
                for policy in PROTOCOL['policies']:
                    spec = dict(map=m, players=n, variant=v, fastBid=fast, cell=cell,
                                seed=f'{namespace}:{cell}:{deal}', deal=deal, focalSeat=seat,
                                maxSteps=PROTOCOL['maxSteps'], focalPolicy=policy)
                    tasks.append(dict(spec=spec, policy=policy))
    return tasks


def runtime_versions(reference_python):
    # Metadata only, including the existing parent environment's unchanged pins.
    versions = shared.runtime_versions(reference_python)
    versions['controllerEnvironment'] = versions.pop('candidate')
    versions['torchInferenceUsed'] = False
    return versions


def identity(smoke=False, *, versions, workers=6):
    validate_protocol()
    if type(workers) is not int or workers not in PROTOCOL['allowedWorkers']:
        raise ValueError('Diagnostic permits 1..6 spawn workers')
    names = ('gap-protocol-v1.json', 'gap_game.cjs', 'gap_study.py', 'job_gap.py', 'test_gap.cjs', 'test_gap.py',
             'neural_study.py', 'neural-study-v1.json', 'job_neural.py', 'reference_evaluate.py',
             'reference_recover.py', 'reference_game.cjs', 'game_rl.cjs', 'game.cjs', 'features.cjs',
             'teacher.cjs', 'data.py', 'protocol.json', 'ppo-protocol-v1.json', 'requirements-cpu.txt')
    paths = [HERE / name for name in names]
    paths += [ROOT / name for name in ('ai/core.cjs', 'ai/strong/economics.cjs', 'ai/requirements-serve.txt',
                                      'engine/package.json', 'engine/pnpm-lock.yaml')]
    paths += sorted((ROOT / 'engine/dist').rglob('*.js'))
    return dict(schema='multimap-phase-gap-plan-v1', protocol=PROTOCOL, smoke=smoke,
                tasks=plan(smoke), generatorDigest=generator_digest(),
                sourceFiles={p.relative_to(ROOT).as_posix(): digest(p) for p in paths},
                runtimeVersions=versions, execution=dict(workers=workers, startMethod='spawn', threads=1,
                                                        referenceThreads=1, torchInferenceUsed=False))


def artifact_budget(directory, additional=0):
    return reuse(shared.artifact_budget)(directory, additional)


def prepare_output(output, frozen_identity):
    return reuse(shared.prepare_output)(output, frozen_identity)


def integer(value, high=PROTOCOL['maxSteps']):
    return type(value) is int and 0 <= value <= high


def validate_phase_counter(row, max_steps=PROTOCOL['maxSteps']):
    if not isinstance(row, dict) or set(row) != set(COUNTERS):
        raise ValueError('Invalid compact phase counters')
    for name in set(COUNTERS) - {'priorGapSum', 'priorGapMax', 'priorGapHistogram'}:
        if not integer(row[name], max_steps):
            raise ValueError('Invalid phase count')
    n, agree = row['multiActionDecisions'], row['teacherExpertAgreement']
    hist, gap_sum, gap_max = row['priorGapHistogram'], row['priorGapSum'], row['priorGapMax']
    if (not isinstance(hist, list) or len(hist) != len(PROTOCOL['priorGapHistogramUpperBounds']) or
            any(not integer(x, n) for x in hist) or sum(hist) != n or agree > hist[0] or
            not finite(gap_sum, 0, 20 * n) or not finite(gap_max, 0, 20) or
            gap_sum + 1e-8 < gap_max or gap_sum > n * gap_max + 1e-8 or
            (n == 0 and (gap_sum != 0 or gap_max != 0)) or
            row['exactFloor20'] > row['cannotOutscoreTeacherBestWithCurrentBound'] or
            row['cannotOutscoreTeacherBestWithCurrentBound'] > hist[-1]):
        raise ValueError('Inconsistent prior/forced/agreement counters')
    bounds = PROTOCOL['priorGapHistogramUpperBounds']
    lower_sum = sum(count * low for count, low in zip(hist, [0] + bounds[:-1]))
    upper_sum = sum(count * high for count, high in zip(hist, bounds))
    if not lower_sum - 1e-7 <= gap_sum <= upper_sum + 1e-7:
        raise ValueError('Prior histogram/sum mismatch')
    occupied = [i for i, count in enumerate(hist) if count]
    if occupied:
        i = occupied[-1]
        if not (gap_max <= bounds[i] and (gap_max > bounds[i - 1] if i else gap_max == 0)):
            raise ValueError('Prior histogram/max mismatch')
    if (row['exactFloor20'] > 0) != (gap_max == 20):
        raise ValueError('Exact floor count/max mismatch')


def validate_record(record, task, identity_sha):
    common = {'schema', 'identitySha256', 'spec', 'policy', 'terminal', 'credit', 'decisions', 'seconds'}
    terminal_fields = {'allSeatCredit', 'steps', 'rounds', 'counts', 'phaseCounters', 'publicChecks'}
    required = common | (terminal_fields if record.get('terminal') is True else {'error'})
    if (set(record) != required or record.get('schema') != OUTCOME_SCHEMA or
            record.get('identitySha256') != identity_sha or
            canonical(record['spec']) != canonical(task['spec']) or record['policy'] != task['policy'] or
            type(record['terminal']) is not bool):
        raise ValueError('Invalid diagnostic outcome identity/schema/spec (no trajectories allowed)')
    if not finite(record['credit'], 0, 1) or not finite(record['seconds']):
        raise ValueError('Invalid evaluation credit/timing')
    decisions = record['decisions']
    if (not isinstance(decisions, dict) or set(decisions) != {'referenceRequests', 'counterfactualOnly'} or
            any(not integer(v) for v in decisions.values()) or decisions['counterfactualOnly'] > decisions['referenceRequests']):
        raise ValueError('Invalid service counters')
    if not record['terminal']:
        error = record['error']
        if (record['credit'] != 0 or not isinstance(error, dict) or set(error) != {'type', 'code'} or
                any(not isinstance(v, str) or not 1 <= len(v) <= 100 for v in error.values())):
            raise ValueError('Failure needs bounded error and zero evaluation bookkeeping, not terminal reward')
        return
    spec, credits = task['spec'], record['allSeatCredit']
    if (not isinstance(credits, list) or len(credits) != spec['players'] or
            any(not finite(c, 0, 1) for c in credits) or not math.isclose(sum(credits), 1, abs_tol=1e-9) or
            record['credit'] != credits[spec['focalSeat']]):
        raise ValueError('Invalid actual terminal credit vector')
    winners = [c for c in credits if c > 0]
    if any(not math.isclose(c, 1 / len(winners), rel_tol=0, abs_tol=1e-12) for c in winners):
        raise ValueError('Terminal winners must share credit equally')
    if any(not integer(record[k]) or record[k] < 1 for k in ('steps', 'rounds')):
        raise ValueError('Invalid terminal steps/rounds')
    counts, phases, checks = record['counts'], record['phaseCounters'], record['publicChecks']
    if not isinstance(counts, dict) or set(counts) != set(ACTORS):
        raise ValueError('Invalid actual-controller counts')
    for actor in ACTORS:
        if (not isinstance(counts[actor], dict) or set(counts[actor]) != set(PHASES) or
                any(not integer(v) for v in counts[actor].values())):
            raise ValueError('Invalid actual-controller phase counts')
    if sum(sum(v.values()) for v in counts.values()) != record['steps']:
        raise ValueError('Actual-controller counts do not sum to steps')
    if not isinstance(phases, dict) or set(phases) != set(PHASES):
        raise ValueError('Missing diagnostic phase')
    multi, counterfactual, teacher_forced = 0, 0, 0
    for phase, row in phases.items():
        validate_phase_counter(row)
        n, forced = row['multiActionDecisions'], row['forcedMoves']
        teacher = controller(task['policy'], phase) == 'teacher'
        own, other = ('focalTeacher', 'focalReference') if teacher else ('focalReference', 'focalTeacher')
        if counts[own][phase] != n + forced or counts[other][phase] != 0:
            raise ValueError('Focal phase routing/forced/decision mismatch')
        multi += n
        counterfactual += n if teacher else 0
        teacher_forced += forced if teacher else 0
    requests = record['steps'] - teacher_forced
    if decisions != dict(referenceRequests=requests, counterfactualOnly=counterfactual):
        raise ValueError('Reference requests/counterfactual counts mismatch')
    expected_checks = dict(hiddenInvariant=requests, expertAtomicLegal=requests, fullMenuPrior=multi, teacherAtomicLegal=multi)
    if (not isinstance(checks, dict) or any(not integer(v) for v in checks.values()) or checks != expected_checks):
        raise ValueError('Missing public invariance/legal/full-menu checks')


def read_existing(path, tasks, identity_sha):
    return reuse(shared.read_existing)(path, tasks, identity_sha)


def play_game(task, bridge, reference, identity_sha):
    started = time.monotonic()
    result = dict(schema=OUTCOME_SCHEMA, identitySha256=identity_sha, **task, terminal=False,
                  credit=0.0, decisions=dict(referenceRequests=0, counterfactualOnly=0), seconds=0.0)
    terminal_fields = ('allSeatCredit', 'steps', 'rounds', 'counts', 'phaseCounters', 'publicChecks')
    try:
        state = bridge.call(dict(op='start', spec=task['spec']))
        while not state['terminal']:
            if result['decisions']['referenceRequests'] >= task['spec']['maxSteps']:
                raise ValueError('game-cap')
            if state['kind'] != 'reference' or state['phase'] not in PHASES:
                raise ValueError('wrong-diagnostic-request')
            focal = state['request']['player'] == task['spec']['focalSeat']
            actual = controller(task['policy'], state['phase']) if focal else 'reference'
            if (state['actualController'] != actual or type(state['focalComparison']) is not bool or
                    (state['focalComparison'] and not focal) or (actual == 'teacher' and not state['focalComparison'])):
                raise ValueError('wrong-diagnostic-controller')
            # Required even when actual == teacher: never replace expert with prior argmax.
            response = reference.decide(state['request'])
            result['decisions']['referenceRequests'] += 1
            result['decisions']['counterfactualOnly'] += int(actual == 'teacher')
            state = bridge.call(dict(op='step', response=response))
        result.update(terminal=True, credit=state['credit'][task['spec']['focalSeat']],
                      allSeatCredit=state['credit'], **{k: state[k] for k in terminal_fields if k != 'allSeatCredit'})
        result['seconds'] = time.monotonic() - started
        validate_record(result, task, identity_sha)
    except Exception as error:
        for name in terminal_fields:
            result.pop(name, None)
        code = 'response-timeout' if isinstance(error, TimeoutError) else 'game-or-policy-error'
        if 'capped' in str(error) or 'game-cap' in str(error):
            code = 'nonterminal-cap'
        result.update(terminal=False, credit=0.0, error=dict(type=type(error).__name__[:100], code=code))
    result['seconds'] = time.monotonic() - started
    return result


class WorkerRuntime(shared.WorkerRuntime):
    # Reuse only the process-group cleanup implementation, never the model loader.
    def __init__(self, artifact, reference_python):
        self.reference = self.bridge = None
        self.models = None  # Opaque unused compatibility slot for shared.worker_main.
        try:
            for name in THREAD_ENV:
                os.environ[name] = '1'
            validate_protocol()
            self.reference = ReferenceProcess(artifact, reference_python)
            env = dict(os.environ)
            for name in ('NODE_OPTIONS', 'NODE_PATH'):
                env.pop(name, None)
            self.bridge = LineProcess(['node', HERE / 'gap_game.cjs'], env=env)
        except BaseException:
            self.close()
            raise


def _worker_play(task, bridge, reference, unused, identity_sha):
    if unused is not None:
        raise ValueError('No candidate models allowed in phase diagnostic')
    return play_game(task, bridge, reference, identity_sha)


def worker_main(incoming, outgoing, artifact, reference_python, identity_sha):
    return reuse(shared.worker_main, play_game=_worker_play)(incoming, outgoing, artifact, reference_python, identity_sha)


def summarize(records, tasks=None):
    tasks = plan() if tasks is None else tasks
    # Existing paired-deal/cell estimands and all-reference vector audit are generic.
    report = reuse(shared.summarize)(records, tasks)
    report['schema'] = 'multimap-phase-gap-summary-v1'
    # Rotating only the diagnostic focal label must not alter an all-reference game.
    for control in report['allReferenceControl']:
        items = [r for r in records if r['policy'] == 'reference' and r['spec']['seed'] == control['seed']]
        counts = [(r['steps'], r['rounds'], tuple(sum(r['counts'][a][p] for a in ACTORS) for p in PHASES))
                  for r in items if r['terminal']]
        same = len(counts) == len(items) and all(c == counts[0] for c in counts)
        control['sameTerminalCounts'] = same
        control['passed'] = control['passed'] and same
        if not same and control['seed'] not in report['baselineViolations']:
            report['baselineViolations'].append(control['seed'])
    report['qualificationStopped'] = bool(report['failures'] or report['baselineViolations'])
    aggregates = {}
    for policy in PROTOCOL['policies']:
        aggregates[policy] = {}
        items = [r for r in records if r['terminal'] and r['policy'] == policy]
        for phase in PHASES:
            rows = [r['phaseCounters'][phase] for r in items]
            row = {k: sum(r[k] for r in rows) for k in COUNTERS if k not in ('priorGapMax', 'priorGapHistogram')}
            row['priorGapMax'] = max((r['priorGapMax'] for r in rows), default=0)
            row['priorGapHistogram'] = [sum(r['priorGapHistogram'][i] for r in rows)
                                       for i in range(len(PROTOCOL['priorGapHistogramUpperBounds']))]
            n = row['multiActionDecisions']
            row.update(terminalGames=len(items), agreementRate=row['teacherExpertAgreement'] / n if n else None,
                       meanPriorGap=row['priorGapSum'] / n if n else None,
                       actualController=controller(policy, phase))
            aggregates[policy][phase] = row
    report['phaseDiagnostics'] = aggregates
    report['priorGapHistogramLabels'] = PROTOCOL['priorGapHistogramLabels']
    report['priorBoundExplanation'] = PROTOCOL['priorBoundExplanation']
    report['note'] = ('Descriptive frozen ten-arm phase attribution only. All arms reported; no PPO models, fitting, '
        'selection or qualification. Independent unit is the deal, not seat/arm repetitions. Failures have zero '
        'evaluation bookkeeping in recorded-game denominators, never terminal rewards. Phase counters exclude '
        'failed games and agreement/prior denominators exclude forced moves. State visitation differs by arm; '
        'phase contrasts include downstream effects and need not add up. Incomplete cells excluded from macroCellCredit.')
    return report


def run(output, *, artifact=CACHE / 'artifact', reference_python=ROOT / 'ai/.venv-reference/bin/python',
        workers=6, smoke=False, callback=None):
    # No change to frozen coordinator. All relevant globals are locally injected.
    return reuse(shared.run)(output, artifact=artifact, reference_python=reference_python,
                             workers=workers, smoke=smoke, callback=callback)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--artifact', type=Path, default=CACHE / 'artifact')
    parser.add_argument('--reference-python', type=Path, default=ROOT / 'ai/.venv-reference/bin/python')
    parser.add_argument('--smoke', action='store_true')
    parser.add_argument('--workers', type=int, default=PROTOCOL['workers'])
    args = parser.parse_args()
    print(json.dumps(run(args.output, artifact=args.artifact, reference_python=args.reference_python,
                         smoke=args.smoke, workers=args.workers), indent=2))
