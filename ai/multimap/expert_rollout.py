"""Bounded RAM-only v2 expert trajectories; persistent engines and exact public service.

All Torch inference is central and batched. Slots exchange requests in sorted
lockstep; private per-game generators make sampling independent of service races.
No optimizer runs here, no reference request or atomic action is persisted.
"""
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import hashlib
import itertools
import json
import math
import os
from pathlib import Path
import queue
import signal
import subprocess
import threading
import time

import torch
from candidates import load_candidates
from expert_policy import PROTOCOL, row, batch
from residual import row as old_row, batch as old_batch
from reference_evaluate import ReferenceProcess
from reference_recover import CACHE, ROOT

HERE = Path(__file__).resolve().parent
_FROZEN_PROTOCOL = json.loads((HERE / 'expert-protocol-v2.json').read_text())
FROZEN = ('ppo0', 'ppo1', 'ppo2')
SPLITS = ('warmup', 'train', 'selection', 'confirmation')
OBSERVATION_FIELDS = {'schema', 'global', 'players', 'nodes', 'relations', 'actions', 'actionCity', 'prior'}


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def _protocol(protocol):
    if _canonical(protocol) != _canonical(_FROZEN_PROTOCOL):
        raise ValueError('Expert protocol is frozen; overrides are forbidden')


def _opponents(spec, ci):
    reference = spec['map'] == 'Germany' and (spec['split'] != 'train' or (ci + spec['update']) % 2 == 0)
    pool = FROZEN + ('self',) if spec['split'] == 'train' else FROZEN
    seats, ordinal = [], 0
    for seat in range(spec['players']):
        if seat == spec['focalSeat']:
            seats.append('learner')
        elif reference:
            seats.append('reference')
        else:
            offset = spec['update'] + ordinal if spec['split'] == 'train' else seat
            seats.append(pool[(ci + spec['deal'] + offset) % len(pool)])
            ordinal += 1
    return dict(opponentMode='reference' if reference else 'mixed', opponents=seats)


def plans(split, update=0, *, smoke=False, protocol=PROTOCOL):
    """Fresh training deals, fixed paired evaluation deals, explicit seat controllers.

    Smoke uses a disjoint namespace and only the four in-map 2p original/open
    cells. At update 1 its four training opponents cover ppo0/1/2/self; warmup
    and evaluation additionally exercise the exact reference in all phases.
    """
    _protocol(protocol)
    if split not in SPLITS or type(smoke) is not bool or type(update) is not int or not 0 <= update <= protocol['updates']:
        raise ValueError('Invalid expert split/update/smoke; final seeds are reserved')
    if (split != 'train' and update != 0) or (split == 'train' and update < 1):
        raise ValueError('Only training has an update namespace; evaluation tasks are fixed')
    maps = ['Germany'] if split == 'warmup' else protocol['trainMaps']
    if split == 'confirmation' and not smoke:
        maps = maps + protocol['transferMaps']
    counts = (2 if split == 'warmup' else 1) if smoke else (
        protocol['warmupGamesPerCell'] if split == 'warmup' else
        protocol['gamesPerCellPerUpdate'] if split == 'train' else protocol[split + 'DealsPerCell'])
    cells = itertools.product(maps, [2] if smoke else protocol['players'],
        ['original'] if smoke else protocol['variants'], [False] if smoke else protocol['fastBids'])
    namespace = protocol['seedNamespace'] + (':smoke' if smoke else '')
    tasks = []
    for ci, (map_name, players, variant, fast) in enumerate(cells):
        cell = f'{map_name}|{players}|{variant}|{int(fast)}'
        for deal in range(counts):
            seats = [(ci + deal) % players] if split == 'warmup' else (
                [(ci + update - 1) % players] if split == 'train' else range(players))
            for seat in seats:
                spec = dict(map=map_name, players=players, variant=variant, fastBid=fast, cell=cell,
                    seed=f'{namespace}:{split}:{update}:{cell}:{deal}', split=split, update=update,
                    smoke=smoke, deal=deal, focalSeat=seat, maxSteps=protocol['maxSteps'])
                spec.update(_opponents(spec, ci))
                tasks.append(spec)
    return tasks


def validate_tasks(tasks, mode, training, protocol=PROTOCOL):
    _protocol(protocol)
    if mode not in ('warmup', 'train', 'evaluation') or type(training) is not bool or training != (mode != 'evaluation'):
        raise ValueError('training=True is required only for warmup/train modes')
    if not tasks:
        raise ValueError('Empty expert collection')
    allowed_splits = ('selection', 'confirmation') if mode == 'evaluation' else (mode,)
    groups, seen = {}, set()
    for spec in tasks:
        if not isinstance(spec, dict) or spec.get('split') not in allowed_splits:
            raise ValueError('Task split does not match collection mode')
        key = (spec.get('split'), spec.get('update'), spec.get('smoke'))
        if key not in groups:
            groups[key] = {_canonical(s) for s in plans(key[0], key[1], smoke=key[2], protocol=protocol)}
        if 'focalTeacher' in spec and (type(spec['focalTeacher']) is not bool or mode != 'evaluation'):
            raise ValueError('Teacher control is evaluation-only and strictly boolean')
        encoded = _canonical({k: v for k, v in spec.items() if k != 'focalTeacher'})
        if encoded not in groups[key] or encoded in seen:
            raise ValueError('Invalid/duplicate expert full spec or opponent assignment')
        seen.add(encoded)
    if len(groups) != 1:
        raise ValueError('A collection cannot mix split/update/smoke namespaces')


class LineProcess:
    """Own bounded insertion-order transport (not the v1 Bridge allowlist).

    Reading uses a stoppable queue so error cleanup cannot strand a reader thread
    on queue.put. Entire child process groups are terminated, including on timeout.
    """
    def __init__(self, argv, *, cwd=ROOT, timeout=120):
        self.timeout = timeout
        self.closed = threading.Event()
        self.answers = queue.Queue(maxsize=2)
        env = dict(os.environ)
        for key in ('NODE_OPTIONS', 'NODE_PATH'):
            env.pop(key, None)
        self.process = subprocess.Popen([str(x) for x in argv], cwd=cwd, env=env,
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            text=True, bufsize=1, start_new_session=True)
        self.reader = threading.Thread(target=self._read, daemon=True)
        self.reader.start()

    def _put(self, answer):
        while not self.closed.is_set():
            try:
                self.answers.put(answer, timeout=.1)
                return
            except queue.Full:
                pass

    def _read(self):
        try:
            while not self.closed.is_set():
                line = self.process.stdout.readline(16 * 1024**2)
                if not line or not line.endswith('\n'):
                    self._put(RuntimeError('Expert worker EOF/oversized response'))
                    return
                self._put(line)
        except (OSError, ValueError):
            self._put(RuntimeError('Expert worker read failure'))

    def call(self, request):
        if self.closed.is_set():
            raise RuntimeError('Expert worker already closed')
        # Never sort public-state keys: insertion order is part of the old policy.
        payload = json.dumps(request, separators=(',', ':'), allow_nan=False) + '\n'
        if len(payload.encode()) > 16 * 1024**2:
            raise ValueError('Expert request exceeds transport budget')
        try:
            self.process.stdin.write(payload)
            self.process.stdin.flush()
            answer = self.answers.get(timeout=self.timeout)
            if isinstance(answer, BaseException):
                raise answer
            answer = json.loads(answer)
            if not isinstance(answer, dict) or 'error' in answer:
                raise RuntimeError('Expert bridge capped' if isinstance(answer, dict) and answer.get('error') == 'expert-capped'
                    else 'Expert bridge failed')
            return answer
        except queue.Empty:
            self.close()
            raise TimeoutError('Expert worker deadline exceeded') from None
        except (BrokenPipeError, OSError):
            self.close()
            raise RuntimeError('Expert worker transport failed') from None

    def close(self):
        if self.closed.is_set():
            return
        self.closed.set()
        if self.process.poll() is None:
            try:
                os.killpg(self.process.pid, signal.SIGTERM)
                self.process.wait(timeout=3)
            except ProcessLookupError:
                pass
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(self.process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                self.process.wait(timeout=3)
        for stream in (self.process.stdin, self.process.stdout):
            if stream:
                stream.close()
        self.reader.join(timeout=2)


def _close_all(processes):
    """Attempt every close even if one service cleanup itself fails."""
    first = None
    for process in processes:
        if process is not None:
            try:
                process.close()
            except Exception as error:
                first = first or error
    return first


def _row_budget(count, protocol):
    if count > protocol['maxRolloutRows']:
        raise MemoryError('Expert rollout RAM row budget exceeded')


def _finalize_rows(trace, credit):
    if not trace:
        raise ValueError('No learned decisions in a training episode')
    phases = Counter(r['phase'] for r in trace if r['expertIndex'] >= 0)
    for r in trace:
        r['return'] = credit
        r['weight'] = 1 / len(trace)
        r['expertWeight'] = 1 / (len(phases) * phases[r['phase']]) if r['expertIndex'] >= 0 else 0.


def _terminal(state, spec):
    credit = state.get('credit')
    if (state.get('terminal') is not True or not isinstance(credit, list) or len(credit) != spec['players'] or
        any(type(x) not in (int, float) or not math.isfinite(x) or not 0 <= x <= 1 for x in credit) or
        not math.isclose(sum(credit), 1., abs_tol=1e-9) or
        type(state.get('steps')) is not int or not 0 < state['steps'] <= spec['maxSteps'] or
        type(state.get('rounds')) is not int or state['rounds'] <= 0):
        raise ValueError('Invalid terminal credit/cap; no fabricated losses')
    winners = sum(x > 0 for x in credit)
    if any(x > 0 and not math.isclose(x, 1 / winners, abs_tol=1e-9) for x in credit):
        raise ValueError('Terminal winners must share credit equally')
    phases = {'Auction', 'Resources', 'Building', 'Bureaucracy'}
    controllers = {'learner', 'warmupExpert', 'reference', 'self', *FROZEN, 'fixedV2', 'fixedV1', 'focalTeacher'}
    counts, expert, checks = (state.get(k) for k in ('counts', 'expertCounts', 'publicChecks'))
    if (not isinstance(counts, dict) or set(counts) != controllers or
        not isinstance(expert, dict) or set(expert) != phases or not isinstance(checks, dict) or
        set(checks) != {'hiddenInvariant', 'referenceAtomicLegal', 'expertAtomicLegal', 'fullMenuPrior'}):
        raise ValueError('Missing terminal controller/public counters')
    for counter in [*counts.values(), expert]:
        if not isinstance(counter, dict) or set(counter) != phases:
            raise ValueError('Invalid phase counters')
    if any(type(v) is not int or v < 0 for c in [*counts.values(), expert, checks] for v in c.values()):
        raise ValueError('Invalid nonnegative integer counters')
    totals = {name: sum(c.values()) for name, c in counts.items()}
    if sum(totals.values()) != state['steps']:
        raise ValueError('Controller counts do not cover every step')
    for name in ('learner', 'warmupExpert', 'self', *FROZEN):
        if counts[name]['Resources'] or counts[name]['Bureaucracy']:
            raise ValueError('Learned controller escaped learned phases')
    expected_expert = (counts['warmupExpert'] if spec['split'] == 'warmup' else counts['learner']) if (
        spec['map'] == 'Germany' and spec['split'] in ('warmup', 'train')) else dict.fromkeys(phases, 0)
    if expert != expected_expert:
        raise ValueError('Missing or leaked expert labels')
    if (spec['split'] != 'warmup' and totals['warmupExpert']) or (spec['split'] != 'train' and totals['self']):
        raise ValueError('Warmup/self controller leaked into evaluation')
    if (spec['map'] != 'Germany' and totals['reference']) or (not spec.get('focalTeacher') and totals['focalTeacher']):
        raise ValueError('Unexpected reference/teacher controller')
    if spec.get('focalTeacher') and totals['learner']:
        raise ValueError('Teacher control called learner')
    expected_checks = dict(referenceAtomicLegal=totals['reference'], expertAtomicLegal=sum(expert.values()),
        hiddenInvariant=totals['reference'] + sum(expert.values()),
        fullMenuPrior=sum(totals[k] for k in ('learner', 'warmupExpert', 'self', *FROZEN)))
    if checks != expected_checks:
        raise ValueError('Public/atomic/full-menu counter mismatch')
    return credit[spec['focalSeat']]


def collect(model, tasks, workers=6, training=False, seed=917, *, mode='evaluation',
            artifact=CACHE / 'artifact', reference_python=ROOT / 'ai/.venv-reference/bin/python',
            opponents=None, protocol=PROTOCOL):
    """Return (RAM rows, compact outcomes); any cap/service/error aborts the batch.

    Pass the once-loaded result of candidates.load_candidates(['ppo0','ppo1',
    'ppo2']) as opponents to avoid repeated HF metadata calls across updates.
    Self always uses this collection's unchanged student, greedily. Reference
    workers are lazy per slot, remain alive across games, and are closed on error.
    """
    tasks = list(tasks)
    validate_tasks(tasks, mode, training, protocol)
    if type(workers) is not int or not 1 <= workers <= protocol['workers'] or type(seed) is not int:
        raise ValueError('Expert collection requires 1..6 workers and integer seed')
    # The canonical loader enforces checkpoint hashes AND exact legacy source identity.
    population = load_candidates(list(FROZEN)) if opponents is None else opponents
    if not isinstance(population, dict) or set(population) != set(FROZEN):
        raise ValueError('Exact ppo0/ppo1/ppo2 opponent population required')
    models = {'student': model, **population}
    if any(not callable(m) or not hasattr(m, 'eval') for m in models.values()):
        raise ValueError('Invalid inference model')
    old_threads = torch.get_num_threads()
    old_modes = [(m, m.training) for m in {id(v): v for v in models.values()}.values()]
    bridges, references = [], []
    closing = threading.Event()
    live, requests, finished = {}, {}, {}
    pending = iter(enumerate(tasks))
    total_rows = 0

    def assign(slot):
        item = next(pending, None)
        if item is None:
            live.pop(slot, None)
            return
        number, spec = item
        # Include the focal seat since paired evaluations share the deal seed.
        sampler_seed = int.from_bytes(hashlib.sha256(f'{seed}:{spec["seed"]}:{spec["focalSeat"]}'.encode()).digest()[:8], 'big') % (2**63)
        live[slot] = dict(number=number, spec=spec, trace=[], relations=None, decisions=0,
            featureMs=0., inferenceMs=0., referenceMs=0., referenceRequests=0, expertRequests=0,
            exchanges=0, start=time.monotonic(), generator=torch.Generator().manual_seed(sampler_seed))
        requests[slot] = dict(op='start', spec=spec)

    def bridge_call(slot, request):
        ep = live[slot]
        ep['exchanges'] += 1
        if ep['exchanges'] > 2 * ep['spec']['maxSteps'] + 2:
            raise RuntimeError('Expert transport decision cap exceeded')
        answer = bridges[slot].call(request)
        if not isinstance(answer, dict) or 'error' in answer:
            raise RuntimeError('Expert bridge failure/cap')
        return answer

    def reference_call(slot, state, expert):
        ep, spec = live[slot], live[slot]['spec']
        request = state.get('request')
        if spec['map'] != 'Germany' or not isinstance(request, dict):
            raise ValueError('Reference request outside Germany/public API')
        if expert and (not training or mode not in ('train', 'warmup') or state['seat'] != spec['focalSeat']):
            raise ValueError('Expert label request leaked into evaluation/opponent')
        if request.get('player') != state['seat'] or request.get('revision') != state['revision']:
            raise ValueError('Unbound public decision request')
        began = time.perf_counter()
        if closing.is_set():
            raise RuntimeError('Expert collector closing')
        if references[slot] is None:
            references[slot] = ReferenceProcess(artifact, reference_python)
        if closing.is_set():
            references[slot].close()
            raise RuntimeError('Expert collector closed during reference creation')
        response = references[slot].decide(request)
        ep['referenceMs'] += 1000 * (time.perf_counter() - began)
        ep['referenceRequests'] += 1
        ep['expertRequests'] += int(expert)
        return response

    def call(item):
        slot, request = item
        state = bridge_call(slot, request)
        spec = live[slot]['spec']
        while state.get('terminal') is False and state.get('kind') == 'reference':
            seat = state.get('seat')
            if type(seat) is not int or not 0 <= seat < spec['players'] or spec['opponents'][seat] != 'reference':
                raise ValueError('Reference controller mismatch')
            response = reference_call(slot, state, False)
            state = bridge_call(slot, dict(op='step', response=response))
        if state.get('terminal') is False:
            kind, seat = state.get('kind'), state.get('seat')
            if kind not in ('learner', 'opponent') or type(seat) is not int or not 0 <= seat < spec['players']:
                raise ValueError('Unknown expert decision kind/seat')
            expected = spec['opponents'][seat]
            if (state.get('controller') != expected or (kind == 'learner') != (seat == spec['focalSeat']) or
                expected == 'reference' or state.get('phase') not in protocol['learnedPhases']):
                raise ValueError('Policy controller/learned phase mismatch')
            required = kind == 'learner' and spec['map'] == 'Germany' and training
            if state.get('expertRequired') is not required or ('request' in state) != required:
                raise ValueError('Missing/leaked counterfactual expert request')
            state['expertIndex'] = -1
            if required:
                response = reference_call(slot, state, True)
                label = bridge_call(slot, dict(op='label', response=response))
                if (label.get('labeled') is not True or label.get('revision') != state['revision'] or
                    type(label.get('expertIndex')) is not int or label['expertIndex'] < 0):
                    raise ValueError('Missing validated full-menu expert index')
                state['expertIndex'] = label['expertIndex']
            # Drop transient public projection before batching observations.
            state.pop('request', None)
        return slot, state

    pool = None
    try:
        torch.set_num_threads(protocol['inferenceThreads'])
        for m in models.values():
            m.eval()
        for _ in range(min(workers, len(tasks))):
            bridges.append(LineProcess(['node', HERE / 'expert_game.cjs']))
            references.append(None)
        for slot in range(len(bridges)):
            assign(slot)
        pool = ThreadPoolExecutor(max_workers=len(bridges))
        with torch.inference_mode():
            while requests:
                answers = list(pool.map(call, sorted(requests.items())))
                requests = {}
                groups = {}
                for slot, state in answers:
                    ep, spec = live[slot], live[slot]['spec']
                    if state.get('terminal') is True:
                        credit = _terminal(state, spec)
                        if (ep['expertRequests'] != sum(state['expertCounts'].values()) or
                            ep['referenceRequests'] != state['publicChecks']['hiddenInvariant'] or
                            ep['decisions'] != sum(state['counts']['learner'].values()) + sum(state['counts']['warmupExpert'].values())):
                            raise ValueError('Collector/engine request counters disagree')
                        if training:
                            _finalize_rows(ep['trace'], credit)
                        result = dict(spec=spec, terminal=True, credit=credit, allSeatCredit=state['credit'],
                            steps=state['steps'], rounds=state['rounds'], counts=state['counts'],
                            expertCounts=state['expertCounts'], publicChecks=state['publicChecks'],
                            decisions=ep['decisions'], referenceRequests=ep['referenceRequests'],
                            expertRequests=ep['expertRequests'], featureMs=ep['featureMs'],
                            inferenceMs=ep['inferenceMs'], referenceMs=ep['referenceMs'], seconds=time.monotonic() - ep['start'])
                        finished[ep['number']] = (ep['trace'], result)
                        assign(slot)
                        continue
                    if state.get('terminal') is not False:
                        raise ValueError('Missing terminal flag')
                    observation = state.get('observation')
                    if not isinstance(observation, dict) or set(observation) != OBSERVATION_FIELDS:
                        raise ValueError('Neural features may contain only public tensor fields')
                    if len(observation['actions']) < 2 or state['expertIndex'] >= len(observation['actions']):
                        raise ValueError('Forced decision/invalid expert index')
                    name = 'student' if state['controller'] in ('learner', 'self') else state['controller']
                    r = (row if name == 'student' else old_row)(observation, ep['relations'])
                    if ep['relations'] is None:
                        ep['relations'] = r['relations']
                    ep['featureMs'] += state['featureMs']
                    if state['kind'] == 'learner':
                        ep['decisions'] += 1
                    groups.setdefault(name, []).append((slot, r, state))
                for name in sorted(groups):
                    items = groups[name]
                    began = time.perf_counter()
                    tensors = (batch if name == 'student' else old_batch)([r for _, r, _ in items])
                    logits, values = models[name](tensors)
                    if logits.shape != tensors['actionMask'].shape or values.shape != (len(items),):
                        raise ValueError('Inference shape mismatch')
                    if not torch.isfinite(logits[tensors['actionMask']]).all() or not torch.isfinite(values).all():
                        raise ValueError('Nonfinite policy output')
                    # Enforce padding even for a supplied model; never sample padded actions.
                    logits = logits.masked_fill(~tensors['actionMask'], -torch.inf)
                    logps = logits.log_softmax(-1)
                    elapsed = 1000 * (time.perf_counter() - began) / len(items)
                    for j, (slot, r, state) in enumerate(items):
                        ep = live[slot]
                        if state['kind'] == 'learner' and mode == 'warmup':
                            action = state['expertIndex']
                        elif state['kind'] == 'learner' and mode == 'train':
                            action = int(torch.multinomial(logps[j].exp(), 1, generator=ep['generator']))
                        else:
                            action = int(logits[j].argmax())
                        if not 0 <= action < len(r['actions']):
                            raise ValueError('Chosen action outside authoritative mask')
                        requests[slot] = dict(op='step', index=action)
                        ep['inferenceMs'] += elapsed
                        if training and state['kind'] == 'learner':
                            total_rows += 1
                            _row_budget(total_rows, protocol)
                            r.update(chosen=action, oldLog=float(logps[j, action]), oldValue=float(values[j]),
                                phase=state['phase'], expertIndex=state['expertIndex'])
                            ep['trace'].append(r)
        if len(finished) != len(tasks):
            raise RuntimeError('Incomplete expert collection')
        rows, outcomes = [], []
        for number in range(len(tasks)):
            trace, result = finished[number]
            rows.extend(trace)
            outcomes.append(result)
        return rows, outcomes
    finally:
        # Close processes BEFORE waiting for blocked service threads after failures.
        closing.set()
        close_error = _close_all(bridges + references)
        if pool is not None:
            pool.shutdown(wait=True, cancel_futures=True)
        # A lazy worker can finish constructing a reference during cleanup.
        _close_all(references)
        for m, was_training in old_modes:
            m.train(was_training)
        torch.set_num_threads(old_threads)
        # Never replace the original cap/service exception with a close failure.
        if close_error is not None and len(finished) == len(tasks):
            raise RuntimeError('Expert process cleanup failed') from close_error


def summary(outcomes):
    if not outcomes:
        raise ValueError('Cannot summarize empty expert outcomes')
    cells = {}
    for outcome in outcomes:
        if outcome.get('terminal') is not True or not math.isfinite(outcome['credit']):
            raise ValueError('Failed outcomes cannot become terminal credits')
        cells.setdefault(outcome['spec']['cell'], []).append(outcome['credit'])
    cells = {key: sum(values) / len(values) for key, values in cells.items()}
    maps = {m: sum(value for key, value in cells.items() if key.split('|')[0] == m) /
        sum(key.split('|')[0] == m for key in cells) for m in sorted({key.split('|')[0] for key in cells})}
    return dict(games=len(outcomes), failures=0, macroCredit=sum(maps.values()) / len(maps), maps=maps, cells=cells)
