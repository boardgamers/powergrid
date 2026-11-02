"""Frozen paired Germany screen, not training, selection, or qualification.

Only this module's fresh namespace is used. The exact public reference owns all
nonfocal phases; reference_game owns the authoritative state and legal moves.
No requests, observations, action traces, or hidden states are persisted.
"""
import argparse
from collections import defaultdict
import hashlib
import importlib.metadata
import itertools
import json
import math
import multiprocessing
from pathlib import Path
import os
import queue
import signal
import statistics
import subprocess
import sys
import time

from data import ROOT, atomic_json, digest, generator_digest
from reference_evaluate import LineProcess, ReferenceProcess
from reference_recover import CACHE, DESCRIPTOR_SHA, MANIFEST_SHA, PINS, budget

HERE = Path(__file__).resolve().parent
PROTOCOL = json.loads((HERE / 'neural-study-v1.json').read_text())
CANDIDATES = ('ppo0', 'ppo1', 'ppo2', 'ensemble')
OUTCOME_SCHEMA = 'multimap-neural-outcome-v1'
MAX_LINE = 64 * 1024
THREAD_ENV = ('OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'OPENBLAS_NUM_THREADS',
              'NUMEXPR_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS')


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def object_sha(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def validate_protocol():
    """Fail closed before downloads or games if the predeclared pins drift."""
    pool = json.loads((HERE / 'candidate-pool-v1.json').read_text())
    if object_sha(pool) != PROTOCOL['candidatePoolSha256']:
        raise ValueError('Frozen candidate pool changed')
    if {p['name']: p['update'] for p in pool['members']} != PROTOCOL['candidateUpdates']:
        raise ValueError('Candidate update pins changed')
    if pool['ensemble']['members'] != list(CANDIDATES[:3]) or pool['ensemble']['weights'] != [1, 1, 1]:
        raise ValueError('Only the frozen equal-logit ensemble is allowed')
    ref = PROTOCOL['reference']
    if (ref['runtimeManifestSha256'] != MANIFEST_SHA or ref['policySha256'] != DESCRIPTOR_SHA or
            ref['modelSha256'] != PINS['model']['sha256'] or ref['sourcePin'] != PINS['source'] or
            ref['modelPin'] != PINS['model']):
        raise ValueError('Frozen reference identity changed')
    if digest(ROOT / 'ai/requirements-serve.txt') != PROTOCOL['referenceRequirementsSha256']:
        raise ValueError('Exact reference requirements changed')
    if json.loads((ROOT / 'engine/package.json').read_text())['version'] != PROTOCOL['authoritativeEngineRelease']:
        raise ValueError('Authoritative engine release changed')
    return pool


def plan(smoke=False):
    tasks = []
    namespace = PROTOCOL['smokeNamespace'] if smoke else PROTOCOL['seedNamespace']
    for m, n, v, fast in itertools.product(PROTOCOL['maps'], PROTOCOL['players'], PROTOCOL['variants'], PROTOCOL['fastBids']):
        if smoke and (n != 2 or v != 'original' or fast):
            continue
        cell = f'{m}|{n}|{v}|{int(fast)}'
        for deal in range(1 if smoke else PROTOCOL['dealsPerCell']):
            seed = f'{namespace}:{cell}:{deal}'
            for seat in range(n):
                for policy in PROTOCOL['policies']:
                    spec = dict(map=m, players=n, variant=v, fastBid=fast, cell=cell,
                                seed=seed, deal=deal, focalSeat=seat, maxSteps=PROTOCOL['maxSteps'],
                                focalPolicy='selected' if policy in CANDIDATES else policy)
                    tasks.append(dict(spec=spec, policy=policy))
    return tasks


def key(record):
    return record['spec']['seed'], record['spec']['focalSeat'], record['policy']


def runtime_versions(reference_python):
    """Version metadata only; never load old ONNX into the Torch interpreter."""
    code = ('import sys,json,importlib.metadata as m;print(json.dumps(dict('
            'python=list(sys.version_info[:3]),numpy=m.version("numpy"),'
            'onnxruntime=m.version("onnxruntime"))))')
    ref = json.loads(subprocess.check_output([str(reference_python), '-B', '-c', code], text=True, timeout=30))
    expected_numpy = PROTOCOL['referenceEnvironment']['numpyPython312Plus' if ref['python'][:2] >= [3, 12] else 'numpyPython311']
    if ref['numpy'] != expected_numpy or ref['onnxruntime'] != PROTOCOL['referenceEnvironment']['onnxruntime']:
        raise ValueError('Wrong isolated reference environment')
    current = {name: importlib.metadata.version(name) for name in ('torch', 'numpy', 'huggingface-hub')}
    if any(current[name] != value for name, value in PROTOCOL['torchEnvironment'].items()):
        raise ValueError('Torch environment changed (do not upgrade its NumPy)')
    return dict(reference=ref, candidate=dict(current, python=list(sys.version_info[:3])),
                node=subprocess.check_output(['node', '--version'], text=True, timeout=30).strip())


def identity(smoke=False, *, versions, workers=6):
    pool = validate_protocol()
    names = ('neural_study.py', 'neural-study-v1.json', 'job_neural.py', 'candidate-pool-v1.json',
             'candidates.py', 'reference_evaluate.py', 'reference_recover.py', 'reference_game.cjs',
             'game_rl.cjs', 'game.cjs', 'features.cjs', 'teacher.cjs', 'model.py', 'residual.py',
             'data.py', 'protocol.json', 'ppo-protocol-v1.json', 'requirements-cpu.txt')
    sources = {f'ai/multimap/{name}': digest(HERE / name) for name in names}
    for name in ('ai/requirements-serve.txt', 'engine/package.json', 'engine/pnpm-lock.yaml'):
        sources[name] = digest(ROOT / name)
    return dict(schema='multimap-neural-plan-v1', protocol=PROTOCOL, smoke=smoke,
                tasks=plan(smoke), candidatePool=pool, generatorDigest=generator_digest(),
                sourceFiles=sources, runtimeVersions=versions, execution=dict(workers=workers, startMethod='spawn', torchThreads=1))


def artifact_budget(directory, additional=0):
    total = additional
    for path in Path(directory).rglob('*'):
        if path.is_symlink():
            raise ValueError('Study artifact symlinks are forbidden')
        if path.is_file():
            total += path.stat().st_size
    if total > PROTOCOL['studyArtifactMaxBytes']:
        raise ValueError('Compact study artifact budget exceeded 128 MiB')
    return total


def prepare_output(output, frozen_identity):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    artifact_budget(output)
    path = output / 'plan.json'
    if path.exists():
        if canonical(json.loads(path.read_text())) != canonical(frozen_identity):
            raise ValueError('Study full identity/source/plan mismatch')
    else:
        if (output / 'games.jsonl').exists() or (output / 'summary.json').exists():
            raise ValueError('Outcomes without an immutable plan')
        artifact_budget(output, len(canonical(frozen_identity).encode()) * 2)
        # Compact plan, atomic replace; identities include every frozen spec.
        tmp = path.with_suffix('.json.tmp')
        tmp.write_text(canonical(frozen_identity) + '\n')
        tmp.replace(path)
    return object_sha(frozen_identity)


def finite(value, low=0, high=float('inf')):
    return type(value) in (int, float) and math.isfinite(value) and low <= value <= high


def validate_record(record, task, identity_sha):
    common = {'schema', 'identitySha256', 'spec', 'policy', 'terminal', 'credit', 'decisions', 'seconds'}
    terminal_fields = {'allSeatCredit', 'steps', 'rounds', 'counts', 'hiddenChecks'}
    required = common | (terminal_fields if record.get('terminal') is True else {'error'})
    if set(record) != required or record.get('schema') != OUTCOME_SCHEMA or record.get('identitySha256') != identity_sha:
        raise ValueError('Invalid outcome schema/identity (no trajectories allowed)')
    if canonical(record['spec']) != canonical(task['spec']) or record['policy'] != task['policy'] or type(record['terminal']) is not bool:
        raise ValueError('Saved task/spec mismatch')
    if not finite(record['credit'], 0, 1) or not finite(record['seconds']):
        raise ValueError('Invalid evaluation credit/timing')
    counts = record['decisions']
    if (not isinstance(counts, dict) or set(counts) != {'ppo', 'reference'} or
            any(type(v) is not int or not 0 <= v <= task['spec']['maxSteps'] for v in counts.values())):
        raise ValueError('Invalid decision counts')
    if not record['terminal']:
        if record['credit'] != 0 or not isinstance(record['error'], dict) or set(record['error']) != {'type', 'code'}:
            raise ValueError('Failure must have explicit error and zero evaluation credit, not a terminal reward')
        if any(not isinstance(v, str) or not 1 <= len(v) <= 100 for v in record['error'].values()):
            raise ValueError('Invalid bounded failure code')
        return
    spec = task['spec']
    credits = record['allSeatCredit']
    if (not isinstance(credits, list) or len(credits) != spec['players'] or
            any(not finite(c, 0, 1) for c in credits) or not math.isclose(sum(credits), 1, abs_tol=1e-9) or
            record['credit'] != credits[spec['focalSeat']]):
        raise ValueError('Invalid actual terminal credit vector')
    if type(record['steps']) is not int or not 1 <= record['steps'] <= spec['maxSteps']:
        raise ValueError('Invalid terminal step count')
    if type(record['rounds']) is not int or not 1 <= record['rounds'] <= spec['maxSteps']:
        raise ValueError('Invalid terminal round count')
    phases = record['counts']
    if not isinstance(phases, dict) or set(phases) != {'ppo', 'reference', 'fixed'}:
        raise ValueError('Invalid terminal actor counts')
    for actor, values in phases.items():
        if not isinstance(values, dict) or any(not isinstance(k, str) or len(k) > 64 or
                type(v) is not int or v < 1 for k, v in values.items()):
            raise ValueError('Invalid phase counts')
    if sum(sum(v.values()) for v in phases.values()) != record['steps']:
        raise ValueError('Terminal phase counts do not sum to steps')
    if any(sum(phases[k].values()) != counts[k] for k in counts):
        raise ValueError('Bridge/service decision counts disagree')
    if type(record['hiddenChecks']) is not int or record['hiddenChecks'] != counts['reference']:
        raise ValueError('Missing public hidden-invariance check')
    if task['policy'] not in CANDIDATES and counts['ppo']:
        raise ValueError('Control must not route to PPO')
    if task['policy'] == 'reference' and phases['fixed']:
        raise ValueError('Reference must control all its phases')


def read_existing(path, tasks, identity_sha):
    """Only a non-newline-terminated last write is recoverable; never skip errors."""
    path = Path(path)
    expected = {key(t): t for t in tasks}
    if len(expected) != len(tasks):
        raise ValueError('Duplicate planned task')
    if not path.exists():
        return [], set()
    if path.stat().st_size > PROTOCOL['studyArtifactMaxBytes']:
        raise ValueError('Oversized saved outcomes')
    records, seen = [], set()
    with path.open('r+b') as stream:
        while True:
            start = stream.tell()
            line = stream.readline(MAX_LINE + 1)
            if not line:
                break
            if len(line) > MAX_LINE:
                raise ValueError('Oversized outcome line')
            if not line.endswith(b'\n'):
                stream.truncate(start)
                stream.flush()
                os.fsync(stream.fileno())
                break
            record = json.loads(line)
            k = key(record)
            if k in seen or k not in expected:
                raise ValueError('Invalid/duplicate saved task')
            validate_record(record, expected[k], identity_sha)
            records.append(record)
            seen.add(k)
    return records, seen


def greedy_index(model, observation):
    import torch
    from residual import row, batch
    with torch.inference_mode():
        inputs = batch([row(observation)])
        logits, _ = model(inputs)
        if not torch.isfinite(logits[inputs['actionMask']]).all():
            raise ValueError('Nonfinite candidate logits')
        return int(logits[0].argmax())


def play_game(task, bridge, reference, models, identity_sha, choose=greedy_index):
    """One loop; both subprocesses and all candidate models belong to the worker.

    Failure credit is an evaluation bookkeeping zero, NOT a fabricated reward.
    Error text is deliberately not persisted: third-party exceptions can contain
    requests or states. Bounded type/code suffices to classify the failed game.
    """
    started = time.monotonic()
    result = dict(schema=OUTCOME_SCHEMA, identitySha256=identity_sha, **task,
                  terminal=False, credit=0.0, decisions=dict(ppo=0, reference=0), seconds=0.0)
    try:
        state = bridge.call(dict(op='start', spec=task['spec']))
        while not state['terminal']:
            if sum(result['decisions'].values()) >= task['spec']['maxSteps']:
                raise ValueError('game-cap')
            kind = state['kind']
            if kind == 'reference':
                if (task['policy'] != 'reference' and state['request']['player'] == task['spec']['focalSeat']):
                    raise ValueError('wrong-reference-actor')
                response = reference.decide(state['request'])
                result['decisions']['reference'] += 1
                state = bridge.call(dict(op='step', response=response))
            elif kind == 'ppo' and task['policy'] in CANDIDATES:
                index = choose(models[task['policy']], state['observation'])
                result['decisions']['ppo'] += 1
                state = bridge.call(dict(op='step', index=index))
            else:
                raise ValueError('wrong-comparison-actor')
        result.update(terminal=True, credit=state['credit'][task['spec']['focalSeat']],
                      allSeatCredit=state['credit'], steps=state['steps'], rounds=state['rounds'],
                      counts=state['counts'], hiddenChecks=state['hiddenChecks'], seconds=time.monotonic() - started)
        validate_record(result, task, identity_sha)
    except Exception as error:
        for name in ('allSeatCredit', 'steps', 'rounds', 'counts', 'hiddenChecks'):
            result.pop(name, None)
        code = 'response-timeout' if isinstance(error, TimeoutError) else 'game-or-policy-error'
        if 'capped' in str(error) or 'game-cap' in str(error):
            code = 'nonterminal-cap'
        result.update(terminal=False, credit=0.0, error=dict(type=type(error).__name__[:100], code=code))
    result['seconds'] = time.monotonic() - started
    return result


def close_process(process):
    """Kill the entire dedicated group, even if its leader already exited."""
    if process is None:
        return
    child = getattr(process, 'process', None)
    try:
        if child is not None:
            try:
                os.killpg(child.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
        process.close()
    finally:
        if child is not None:
            try:
                os.killpg(child.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass


class WorkerRuntime:
    def __init__(self, artifact, reference_python):
        self.reference = self.bridge = None
        self.models = {}
        try:
            for name in THREAD_ENV:
                os.environ[name] = '1'
            import torch
            from candidates import load_candidates
            torch.set_num_threads(1)
            torch.set_num_interop_threads(1)
            validate_protocol()
            self.models = load_candidates(list(CANDIDATES))
            # Complete immutable artifact verification happens once per worker.
            self.reference = ReferenceProcess(artifact, reference_python)
            self.bridge = LineProcess(['node', ROOT / 'ai/multimap/reference_game.cjs'])
        except BaseException:
            self.close()
            raise

    def close(self):
        bridge, reference = self.bridge, self.reference
        self.bridge = self.reference = None
        try:
            close_process(bridge)
        finally:
            close_process(reference)


def worker_main(incoming, outgoing, artifact, reference_python, identity_sha):
    runtime = None

    def interrupted(signum, frame):
        # The finally block also covers startup and all service/model errors.
        raise SystemExit(128 + signum)

    signal.signal(signal.SIGTERM, interrupted)
    signal.signal(signal.SIGINT, interrupted)
    try:
        runtime = WorkerRuntime(artifact, reference_python)
        while True:
            task = incoming.get()
            if task is None:
                return
            result = play_game(task, runtime.bridge, runtime.reference, runtime.models, identity_sha)
            outgoing.put(('outcome', result))
            if not result['terminal']:
                return
    except SystemExit:
        raise
    except BaseException as error:
        outgoing.put(('worker-error', dict(type=type(error).__name__, code='worker-startup-or-process-error')))
        raise
    finally:
        if runtime is not None:
            runtime.close()


def mean_se(values):
    return dict(mean=statistics.fmean(values) if values else None, independentDeals=len(values),
                dealStandardError=statistics.stdev(values) / math.sqrt(len(values)) if len(values) > 1 else None)


def summarize(records, tasks=None):
    """Report all six policies, all cells, errors, and independent-deal contrasts."""
    tasks = plan() if tasks is None else tasks
    expected = {key(t): t for t in tasks}
    if len(expected) != len(tasks) or len({key(r) for r in records}) != len(records):
        raise ValueError('Duplicate summary task')
    if any(key(r) not in expected or canonical(r['spec']) != canonical(expected[key(r)]['spec']) for r in records):
        raise ValueError('Unexpected summary task')
    by_deal = defaultdict(list)
    cells = sorted({t['spec']['cell'] for t in tasks})
    for r in records:
        by_deal[(r['policy'], r['spec']['seed'])].append(r)
    deal_means = {k: statistics.fmean(r['credit'] for r in rs) for k, rs in by_deal.items()
                  if len(rs) == rs[0]['spec']['players']}
    cell_rows = []
    for cell in cells:
        for policy in PROTOCOL['policies']:
            items = [r for r in records if r['spec']['cell'] == cell and r['policy'] == policy]
            planned = [t for t in tasks if t['spec']['cell'] == cell and t['policy'] == policy]
            seeds = {t['spec']['seed'] for t in planned}
            values = [deal_means[(policy, seed)] for seed in seeds if (policy, seed) in deal_means]
            cell_rows.append(dict(cell=cell, policy=policy, plannedGames=len(planned), games=len(items),
                terminalGames=sum(r['terminal'] for r in items), failures=sum(not r['terminal'] for r in items),
                creditSum=sum(r['credit'] for r in items), gameMeanCredit=statistics.fmean(r['credit'] for r in items) if items else None,
                plannedIndependentDeals=len(seeds), **mean_se(values)))
    policies = {}
    for policy in PROTOCOL['policies']:
        rows = [r for r in cell_rows if r['policy'] == policy]
        items = [r for r in records if r['policy'] == policy]
        complete_cells = [r['mean'] for r in rows if r['independentDeals'] == r['plannedIndependentDeals']]
        paired = {}
        for control in ('reference', 'teacher'):
            seeds = sorted(seed for p, seed in deal_means if p == policy and (control, seed) in deal_means)
            paired[control] = mean_se([deal_means[(policy, s)] - deal_means[(control, s)] for s in seeds])
        policies[policy] = dict(games=len(items), plannedGames=sum(r['plannedGames'] for r in rows),
            failures=sum(not r['terminal'] for r in items), creditSum=sum(r['credit'] for r in items),
            gameMeanCredit=statistics.fmean(r['credit'] for r in items) if items else None,
            completeCells=len(complete_cells), macroCellCredit=statistics.fmean(complete_cells) if complete_cells else None,
            pairedDealDifferences=paired)
    baseline = []
    violations = []
    for (policy, seed), items in sorted(by_deal.items()):
        if policy != 'reference' or len(items) != items[0]['spec']['players']:
            continue
        terminal = all(r['terminal'] for r in items)
        credit_sum = sum(r['credit'] for r in items)
        same = terminal and all(r['allSeatCredit'] == items[0]['allSeatCredit'] for r in items)
        passed = terminal and same and math.isclose(credit_sum, 1, abs_tol=1e-9)
        baseline.append(dict(seed=seed, games=len(items), terminal=terminal,
                             focalCreditSum=credit_sum, sameCreditVector=same, passed=passed))
        if not passed:
            violations.append(seed)
    failures = sum(not r['terminal'] for r in records)
    return dict(schema='multimap-neural-summary-v1', games=len(records), plannedGames=len(tasks),
        complete=len(records) == len(tasks), failures=failures, cells=cell_rows, policies=policies,
        independentDeals=len({r['spec']['seed'] for r in records}),
        plannedIndependentDeals=len({t['spec']['seed'] for t in tasks}),
        allReferenceControl=baseline, baselineViolations=violations,
        qualificationStopped=bool(failures or violations), qualified=False, qualification_eligible=False,
        reserved_final_seeds_used=False, fitted=False, selected=False,
        note='Descriptive frozen Germany screen only. Seat/policy repeats are paired, not independent deals. '
             'Failures have zero evaluation credit in the recorded-game denominator. Incomplete cells are not '
             'included in macroCellCredit. All six policies are reported without best-seed selection; no qualification.')


def run(output, *, artifact=CACHE / 'artifact', reference_python=ROOT / 'ai/.venv-reference/bin/python',
        workers=6, smoke=False, callback=None):
    if type(workers) is not int or workers not in PROTOCOL['allowedWorkers']:
        raise ValueError('Frozen screen permits 1..6 spawn workers')
    for name in THREAD_ENV:
        os.environ[name] = '1'
    artifact = Path(artifact).resolve()
    output = Path(output).resolve()
    if output.is_relative_to(artifact.parent) or artifact.parent.is_relative_to(output):
        raise ValueError('Reference cache must be separate from compact study artifacts')
    budget(artifact.parent)
    frozen_identity = identity(smoke, versions=runtime_versions(reference_python), workers=workers)
    identity_sha = prepare_output(output, frozen_identity)
    tasks = frozen_identity['tasks']
    records, done = read_existing(output / 'games.jsonl', tasks, identity_sha)

    def checkpoint(stage):
        report = summarize(records, tasks)
        report['identitySha256'] = identity_sha
        atomic_json(output / 'summary.json', report)
        artifact_budget(output)
        print(json.dumps(dict(stage=stage, games=len(records), plannedGames=len(tasks),
                              failures=report['failures'], qualified=False)), flush=True)
        if callback:
            callback(stage)
        return report

    existing = checkpoint('planned' if not records else f'resumed-{len(records)}')
    if existing['failures'] or existing['baselineViolations']:
        raise RuntimeError('Saved failures/baseline violations are immutable; no silent retries or qualification')
    todo = iter(t for t in tasks if key(t) not in done)
    if len(done) == len(tasks):
        return existing
    context = multiprocessing.get_context('spawn')
    incoming, outgoing = context.Queue(maxsize=workers), context.Queue(maxsize=workers * 2)
    children = [context.Process(target=worker_main, args=(incoming, outgoing, str(artifact),
                str(reference_python), identity_sha), name=f'neural-screen-{i}') for i in range(workers)]
    active, stopping, success = set(), False, False
    old_term = signal.getsignal(signal.SIGTERM)

    def terminate(signum, frame):
        raise SystemExit(128 + signum)

    signal.signal(signal.SIGTERM, terminate)
    try:
        for child in children:
            child.start()
        for _ in children:
            task = next(todo, None)
            if task is not None:
                incoming.put(task)
                active.add(key(task))
        with (output / 'games.jsonl').open('a') as file:
            while active:
                try:
                    kind, result = outgoing.get(timeout=1)
                except queue.Empty:
                    if (not stopping and any(c.exitcode is not None for c in children)) or all(c.exitcode is not None for c in children):
                        raise RuntimeError('Spawn worker exited before all pending outcomes were received')
                    continue
                if kind != 'outcome':
                    raise RuntimeError('Neural screen worker error: ' + canonical(result))
                k = key(result)
                if k not in active:
                    raise ValueError('Duplicate/unassigned worker outcome')
                validate_record(result, next(t for t in tasks if key(t) == k), identity_sha)
                line = canonical(result) + '\n'
                if len(line.encode()) > MAX_LINE:
                    raise ValueError('Oversized compact outcome')
                artifact_budget(output, len(line.encode()))
                file.write(line)
                file.flush()
                os.fsync(file.fileno())
                records.append(result)
                active.remove(k)
                stopping = stopping or not result['terminal']
                if len(records) % PROTOCOL['uploadEveryGames'] == 0 or stopping or len(records) == len(tasks):
                    report = checkpoint(f'games-{len(records)}')
                    stopping = stopping or bool(report['baselineViolations'])
                if not stopping:
                    task = next(todo, None)
                    if task is not None:
                        incoming.put(task)
                        active.add(key(task))
        report = checkpoint('screen-stopped' if stopping else 'screen-complete')
        if stopping or report['failures'] or report['baselineViolations'] or not report['complete']:
            raise RuntimeError('Neural screen stopped with explicit failures; no qualification')
        success = True
        return report
    except BaseException:
        # Preserve every committed outcome and partial coverage even on infrastructure failure.
        report = summarize(records, tasks)
        report.update(identitySha256=identity_sha,
                      infrastructureStopped=not bool(report['failures'] or report['baselineViolations']),
                      qualificationStopped=True)
        atomic_json(output / 'summary.json', report)
        raise
    finally:
        signal.signal(signal.SIGTERM, old_term)
        for child in children:
            if child.is_alive():
                if success:
                    incoming.put(None)
                else:
                    child.terminate()  # handler closes both dedicated server process groups
        for child in children:
            if child.pid is not None:
                child.join(timeout=15)
                if child.is_alive():
                    child.terminate()
                    child.join(timeout=10)
                if child.is_alive():
                    child.kill()
                    child.join(timeout=5)
        incoming.close()
        incoming.cancel_join_thread()
        outgoing.close()
        outgoing.cancel_join_thread()


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
