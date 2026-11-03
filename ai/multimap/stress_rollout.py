"""Frozen, evaluation-only multimap stress collector.

Independent namespace validation; greedy central inference; unchanged legacy
loaders and reference transport. Only compact terminal outcomes leave collect:
no observations, trajectories, labels, reference requests, or atomic moves.
"""
import copy
from concurrent.futures import ThreadPoolExecutor
import itertools
import json
import math
from pathlib import Path
import threading
import time

import torch
from huggingface_hub import get_hf_file_metadata, hf_hub_download, hf_hub_url

from candidates import POOL, load_candidates
from data import digest
from expert_policy import load as load_expert, row, batch, SCHEMA as EXPERT_SCHEMA
from expert_rollout import LineProcess
from model import DIMS, SCHEMA as OBSERVATION_SCHEMA
from reference_evaluate import ReferenceProcess
from reference_recover import CACHE, ROOT
from residual import row as old_row, batch as old_batch

HERE = Path(__file__).resolve().parent
PROTOCOL = json.loads((HERE / 'stress-protocol-v1.json').read_text())
_FROZEN_PROTOCOL = copy.deepcopy(PROTOCOL)
NAMESPACE = 'pg-multimap-stress-20261103-v1'
MAPS = ('Germany', 'USA', 'France', 'UK & Ireland')
POLICIES = ('expert24', 'ppo2')
MODELS = ('expert24', 'ppo0', 'ppo1', 'ppo2')
FROZEN = ('ppo0', 'ppo1', 'ppo2')
PANELS = ('strong', 'mixed')
PHASES = ('Auction', 'Resources', 'Building', 'Bureaucracy')
LEARNED_PHASES = ('Auction', 'Building')
CONTROLLERS = (*MODELS, 'reference', 'teacherV2', 'fixedV2', 'fixedV1')
SPEC_FIELDS = {'map', 'players', 'variant', 'fastBid', 'cell', 'seed', 'smoke',
               'deal', 'focalSeat', 'panel', 'policy', 'controllers', 'maxSteps'}
OBSERVATION_FIELDS = {'schema', 'global', 'players', 'nodes', 'relations',
                      'actions', 'actionCity', 'prior'}
CHECK_FIELDS = {'hiddenInvariant', 'referenceAtomicLegal', 'fullMenuPrior', 'expertAtomicLegal'}
DEFAULT_ARTIFACT = CACHE / 'artifact'
DEFAULT_REFERENCE_PYTHON = ROOT / 'ai/.venv-reference/bin/python'
CHECKPOINT_MAX_BYTES = 16 * 1024**2


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def _protocol():
    if (_canonical(PROTOCOL) != _canonical(_FROZEN_PROTOCOL) or
            _canonical(json.loads((HERE / 'stress-protocol-v1.json').read_text())) != _canonical(_FROZEN_PROTOCOL)):
        raise ValueError('Stress protocol is frozen; overrides are forbidden')
    # Independent literals also reject edits made before this module is imported.
    # Compare nested JSON (not Python's False == 0); methodological prose is not
    # hashed here and may be clarified before a new process begins.
    expected = dict(schema='multimap-population-stress-v1', seedNamespace=NAMESPACE,
        maps=list(MAPS), excludedMaps=['Italy', 'Benelux'], players=list(range(2, 7)),
        variants=['original', 'recharged'], fastBids=[False, True], panels=list(PANELS),
        policies=list(POLICIES), dealsPerCell=4, smokeDealsPerCell=1, allFocalSeats=True,
        cellsPerPanel=80, independentDealsPerPanel=320, gamesPerPanel=2560, games=5120,
        maxSteps=4000, workers=6, inferenceThreads=1, uploadEveryBatches=16,
        studyArtifactMaxBytes=64 * 1024**2, referenceCacheMaxBytes=512 * 1024**2,
        referenceVenvMaxBytes=256 * 1024**2, modelRepo='coyotte508/powergrid-ai-multimap-v1',
        selected=dict(name='expert24', repo='coyotte508/powergrid-ai-multimap-v1',
            revision='39976d5e864638fe73d241061bc4dfd4b46ce0a4',
            path='runs/multimap-expert-ppo-20261102-v2-r1/expert/best.pt',
            sha256='1377fc2112c3b9ff3c2a20078ed341305b2a9006a4f7a1df413eeb0b509e6fbd', update=24),
        oldPool='candidate-pool-v1.json',
        oldPoolSha256='a4f5d80966d9dd5b7af712459dffea255590eeb158b3a8e73cb66b0045d29a4b',
        expertProtocol='expert-protocol-v2.json', expertSourceGit='db144fc87d6745fe595ec7e28afc68de496b7966',
        fitting=False, selection=False, qualificationEligible=False, reservedFinalSeedsUsed=False)
    if any(_canonical(_FROZEN_PROTOCOL.get(key)) != _canonical(value) for key, value in expected.items()):
        raise ValueError('Unexpected frozen stress protocol')
    return _FROZEN_PROTOCOL


def _controllers(spec, ci):
    weak = [*FROZEN, 'teacherV2'] + (['reference'] if spec['map'] == 'Germany' else [])
    result = []
    for seat in range(spec['players']):
        if seat == spec['focalSeat']:
            controller = spec['policy']
        elif spec['panel'] == 'strong':
            controller = 'reference' if spec['map'] == 'Germany' else 'expert24'
        else:
            ordinal = (seat - spec['focalSeat'] + spec['players']) % spec['players'] - 1
            index = ci + spec['deal'] + ordinal
            controller = 'expert24' if index % 2 == 0 else weak[(index // 2) % len(weak)]
        result.append(controller)
    return result


def plans(smoke=False):
    """All 80 cells, two panels, paired policies and every actual focal seat.

    Smoke changes only the namespace and deals per cell, never the 80-cell
    ordinal used to assign opponents. A runner may choose a canonical subset.
    """
    protocol = _protocol()
    if type(smoke) is not bool:
        raise ValueError('Stress smoke flag must be boolean; no training split')
    tasks = []
    cells = itertools.product(MAPS, range(2, 7), ('original', 'recharged'), (False, True))
    namespace = NAMESPACE + (':smoke' if smoke else '')
    for ci, (map_name, players, variant, fast) in enumerate(cells):
        cell = f'{map_name}|{players}|{variant}|{int(fast)}'
        for panel in PANELS:
            for deal in range(1 if smoke else 4):
                for focal in range(players):
                    for policy in POLICIES:
                        spec = dict(map=map_name, players=players, variant=variant, fastBid=fast,
                            cell=cell, seed=f'{namespace}:{panel}:{cell}:{deal}', smoke=smoke,
                            deal=deal, focalSeat=focal, panel=panel, policy=policy,
                            maxSteps=protocol['maxSteps'])
                        spec['controllers'] = _controllers(spec, ci)
                        tasks.append(spec)
    return tasks


def task_key(spec):
    return spec['seed'], spec['focalSeat'], spec['policy']


def _validate_spec(spec):
    if not isinstance(spec, dict) or set(spec) != SPEC_FIELDS:
        raise ValueError('Stress tasks forbid training, labels, heldout and custom fields')
    if (type(spec['smoke']) is not bool or type(spec['fastBid']) is not bool or
            type(spec['players']) is not int or spec['players'] not in range(2, 7) or
            spec['map'] not in MAPS or spec['variant'] not in ('original', 'recharged') or
            spec['panel'] not in PANELS or spec['policy'] not in POLICIES or
            type(spec['deal']) is not int or not 0 <= spec['deal'] < (1 if spec['smoke'] else 4) or
            type(spec['focalSeat']) is not int or not 0 <= spec['focalSeat'] < spec['players'] or
            type(spec['maxSteps']) is not int or spec['maxSteps'] != 4000):
        raise ValueError('Noncanonical stress spec/scope')
    cell = f"{spec['map']}|{spec['players']}|{spec['variant']}|{int(spec['fastBid'])}"
    ci = (MAPS.index(spec['map']) * 20 + (spec['players'] - 2) * 4 +
          ('original', 'recharged').index(spec['variant']) * 2 + int(spec['fastBid']))
    namespace = NAMESPACE + (':smoke' if spec['smoke'] else '')
    if (spec['cell'] != cell or spec['seed'] != f"{namespace}:{spec['panel']}:{cell}:{spec['deal']}" or
            not isinstance(spec['controllers'], list) or spec['controllers'] != _controllers(spec, ci)):
        raise ValueError('Noncanonical stress seed/cell/controller assignment')


def validate_tasks(tasks):
    """Independently reconstruct canonical specs; never grant arbitrary seeds."""
    _protocol()
    if not tasks:
        raise ValueError('Empty stress collection')
    seen, smoke = set(), None
    for spec in tasks:
        _validate_spec(spec)
        if smoke is None:
            smoke = spec['smoke']
        if spec['smoke'] is not smoke:
            raise ValueError('Mixed smoke/production namespaces')
        key = task_key(spec)
        if key in seen:
            raise ValueError('Duplicate stress seed/focal/policy')
        seen.add(key)


def load_models(artifact=DEFAULT_ARTIFACT, reference_python=DEFAULT_REFERENCE_PYTHON):
    """Load the immutable four-policy population, never an arbitrary checkpoint.

    All four checkpoints are metadata-budgeted before any transfer. Legacy
    candidates then use their original downloader and source/hash verifier, with
    no redundant prefetch. The expert's saved training identity must exactly match
    the unchanged production config, including six workers. The job must set
    HF_HUB_CACHE before importing this module (or huggingface_hub).
    """
    protocol = _protocol()
    pool_path = HERE / protocol['oldPool']
    if (digest(pool_path) != protocol['oldPoolSha256'] or
            _canonical(POOL) != _canonical(json.loads(pool_path.read_text()))):
        raise ValueError('Frozen legacy candidate pool changed')
    pins = [protocol['selected'], *(pin for pin in POOL['members'] if pin['name'] in FROZEN)]
    if [pin['name'] for pin in pins] != list(MODELS):
        raise ValueError('Exact canonical checkpoint population required')
    metadata_by_name = {}
    for pin in pins:
        metadata = get_hf_file_metadata(hf_hub_url(pin['repo'], pin['path'],
            repo_type=pin.get('repo_type', 'model'), revision=pin['revision']))
        if (metadata.commit_hash != pin['revision'] or type(metadata.size) is not int or
                not 0 < metadata.size <= CHECKPOINT_MAX_BYTES):
            raise ValueError(f"{pin['name']} checkpoint metadata exceeds 16 MiB or immutable revision differs")
        metadata_by_name[pin['name']] = metadata
    pin, metadata = protocol['selected'], metadata_by_name['expert24']
    path = Path(hf_hub_download(pin['repo'], pin['path'],
        repo_type=pin.get('repo_type', 'model'), revision=pin['revision']))
    if path.stat().st_size != metadata.size or digest(path) != pin['sha256']:
        raise ValueError('Expert checkpoint size/hash mismatch')
    expert, saved = load_expert(path)
    # Import lazily: expert_ppo itself imports the original rollout, unchanged.
    from expert_ppo import config
    expected = config(False, artifact=artifact, reference_python=reference_python, workers=6)
    if (saved.get('schema') != EXPERT_SCHEMA or type(saved.get('update')) is not int or
            saved['update'] != 24 or pin['update'] != 24 or saved.get('stage') != 'train' or
            _canonical(saved.get('config')) != _canonical(expected)):
        raise ValueError('Expert checkpoint schema/update/production config mismatch')
    population = load_candidates(list(FROZEN))
    if not isinstance(population, dict) or set(population) != set(FROZEN):
        raise ValueError('Exact canonical legacy candidate population required')
    models = {'expert24': expert, **population}
    for model in models.values():
        model.eval()
        model.requires_grad_(False)
    return models


def prefetch(artifact=DEFAULT_ARTIFACT, reference_python=DEFAULT_REFERENCE_PYTHON):
    """Harmless explicit preload; no games, training, labels, or subprocess slots."""
    return load_models(artifact, reference_python)


def _phase_counts():
    return dict.fromkeys(PHASES, 0)


def _counts():
    return {name: _phase_counts() for name in CONTROLLERS}


def _valid_counter(counter, fields):
    return (isinstance(counter, dict) and set(counter) == set(fields) and
            all(type(value) is int and value >= 0 for value in counter.values()))


def _terminal(state, spec):
    if set(state) != {'terminal', 'credit', 'steps', 'rounds', 'counts', 'seatCounts', 'publicChecks'}:
        raise ValueError('Terminal may contain only compact outcomes, never labels/traces')
    credit = state.get('credit')
    if (state.get('terminal') is not True or not isinstance(credit, list) or len(credit) != spec['players'] or
            any(type(x) not in (int, float) or not math.isfinite(x) or not 0 <= x <= 1 for x in credit) or
            not math.isclose(sum(credit), 1., rel_tol=0., abs_tol=1e-9) or
            type(state.get('steps')) is not int or not 0 < state['steps'] <= spec['maxSteps'] or
            type(state.get('rounds')) is not int or not 0 < state['rounds'] <= state['steps']):
        raise ValueError('Invalid terminal credit/cap; no fabricated losses')
    winners = sum(x > 0 for x in credit)
    if any(x > 0 and x != 1 / winners for x in credit):
        raise ValueError('Terminal winners must share credit equally')
    counts, seats, checks = (state.get(key) for key in ('counts', 'seatCounts', 'publicChecks'))
    if (not isinstance(counts, dict) or set(counts) != set(CONTROLLERS) or
            any(not _valid_counter(c, PHASES) for c in counts.values()) or
            not isinstance(seats, list) or len(seats) != spec['players'] or
            any(not _valid_counter(c, PHASES) for c in seats) or not _valid_counter(checks, CHECK_FIELDS)):
        raise ValueError('Invalid controller/seat/public nonnegative integer counters')
    totals = {name: sum(c.values()) for name, c in counts.items()}
    if sum(totals.values()) != state['steps'] or sum(sum(c.values()) for c in seats) != state['steps']:
        raise ValueError('Controller/seat counts must cover every step')
    for phase in PHASES:
        if sum(c[phase] for c in counts.values()) != sum(c[phase] for c in seats):
            raise ValueError('Seat/controller phase counts differ')
    assigned = spec['controllers']
    if spec['map'] != 'Germany' and totals['reference']:
        raise ValueError('Reference is Germany-only')
    for name in (*MODELS, 'reference', 'teacherV2'):
        if name not in assigned and totals[name]:
            raise ValueError('Unexpected controller for assigned seats')
    for name in MODELS:
        if any(counts[name][phase] for phase in ('Resources', 'Bureaucracy')):
            raise ValueError('Learned controller escaped Auction/Building')
    for phase in PHASES:
        for name in ('reference', 'teacherV2'):
            expected = sum(seats[s][phase] for s, c in enumerate(assigned) if c == name)
            if counts[name][phase] != expected:
                raise ValueError('Reference/teacher actual-seat routing mismatch')
        for name in MODELS:
            maximum = sum(seats[s][phase] for s, c in enumerate(assigned) if c == name)
            if counts[name][phase] > maximum:
                raise ValueError('Policy counts exceed assigned actual seats')
        for names, fixed in ((('expert24',), 'fixedV2'), (FROZEN, 'fixedV1')):
            expected = sum(seats[s][phase] for s, c in enumerate(assigned) if c in names)
            expected -= sum(counts[name][phase] for name in names)
            if counts[fixed][phase] != expected:
                raise ValueError('Fixed-phase controller/actual-seat routing mismatch')
    expected_checks = dict(hiddenInvariant=totals['reference'], referenceAtomicLegal=totals['reference'],
        fullMenuPrior=sum(totals[name] for name in MODELS), expertAtomicLegal=0)
    if checks != expected_checks:
        raise ValueError('Missing public/full-menu checks or leaked expert labels')
    return credit[spec['focalSeat']]


def validate_outcome(outcome, spec):
    """Validate a compact persisted outcome against its exact canonical task.

    Returns the focal credit. _terminal(state, spec) is the engine-terminal
    validator; this wrapper also checks collector counters, timing, and schema.
    """
    _validate_spec(spec)
    fields = {'spec', 'terminal', 'credit', 'allSeatCredit', 'steps', 'rounds', 'counts',
              'seatCounts', 'publicChecks', 'policyRequests', 'referenceRequests',
              'featureMs', 'inferenceMs', 'referenceMs', 'seconds'}
    if not isinstance(outcome, dict) or set(outcome) != fields or _canonical(outcome['spec']) != _canonical(spec):
        raise ValueError('Persisted outcome must match exact compact schema/canonical task')
    state = {key: outcome[key] for key in ('terminal', 'steps', 'rounds', 'counts', 'seatCounts', 'publicChecks')}
    state['credit'] = outcome['allSeatCredit']
    credit = _terminal(state, spec)
    if type(outcome['credit']) not in (int, float) or outcome['credit'] != credit:
        raise ValueError('Persisted focal credit differs from complete terminal vector')
    if (not _valid_counter(outcome['policyRequests'], MODELS) or
            any(outcome['policyRequests'][name] != sum(outcome['counts'][name].values()) for name in MODELS) or
            type(outcome['referenceRequests']) is not int or
            outcome['referenceRequests'] != sum(outcome['counts']['reference'].values())):
        raise ValueError('Persisted collector/engine request counters disagree')
    if any(not _finite_ms(outcome[key]) for key in ('featureMs', 'inferenceMs', 'referenceMs', 'seconds')):
        raise ValueError('Invalid persisted timing')
    return credit


def _finite_ms(value):
    return type(value) in (int, float) and math.isfinite(value) and value >= 0


def _observation(observation, name, spec):
    if not isinstance(observation, dict) or set(observation) != OBSERVATION_FIELDS:
        raise ValueError('Neural observations may contain only public tensor fields')
    if observation['schema'] != OBSERVATION_SCHEMA:
        raise ValueError('Unexpected observation schema')
    if not isinstance(observation['actions'], list) or len(observation['actions']) < 2:
        raise ValueError('Forced decision or empty full menu')
    # Do not let tensor conversion silently truncate noninteger city indices.
    cities = observation['actionCity']
    if not isinstance(cities, list) or any(type(index) is not int for index in cities):
        raise ValueError('Action city indices must be integers')
    try:
        result = (row if name == 'expert24' else old_row)(observation)
    except (AssertionError, IndexError, TypeError, RuntimeError, KeyError) as error:
        raise ValueError('Invalid public observation tensors') from error
    if result['global'].shape != (DIMS['global'],):
        raise ValueError('Invalid global tensor shape')
    for key in ('players', 'nodes', 'actions'):
        if result[key].ndim != 2 or result[key].shape[0] == 0:
            raise ValueError('Invalid full public tensor shape')
    if result['players'].shape[0] != spec['players']:
        raise ValueError('Wrong actual-player tensor count')
    nodes = result['nodes'].shape[0]
    if (result['relations'].shape != (4, nodes, nodes) or
            not torch.isfinite(result['relations']).all() or
            result['actionCity'].shape != (len(result['actions']),) or
            not torch.isfinite(result['prior']).all()):
        raise ValueError('Invalid relation/full-menu tensor')
    return result


def _close_all(processes):
    first = None
    for process in processes:
        if process is not None:
            try:
                process.close()
            except Exception as error:
                first = first or error
    return first


def collect(tasks, workers=6, *, artifact=DEFAULT_ARTIFACT,
            reference_python=DEFAULT_REFERENCE_PYTHON, models=None):
    """Return compact outcomes in task order; any failure aborts the entire call.

    A supplied population is an offline-test seam or the once-loaded result of
    load_models. The production runner loads strict pins once and passes it here.
    Inference never samples, creates a generator, optimizes, or requests labels.
    """
    tasks = copy.deepcopy(list(tasks))
    validate_tasks(tasks)
    protocol = _protocol()
    if type(workers) is not int or not 1 <= workers <= 6:
        raise ValueError('Stress collection requires 1..6 workers')
    population = load_models(artifact, reference_python) if models is None else models
    if not isinstance(population, dict) or set(population) != set(MODELS):
        raise ValueError('Exact expert24/ppo0/ppo1/ppo2 model population required')
    if any(not isinstance(model, torch.nn.Module) for model in population.values()):
        raise ValueError('Invalid frozen inference model')
    unique = list({id(m): m for m in population.values()}.values())
    # Preserve mixed submodule modes, rather than recursively changing them back.
    modes = [(module, module.training) for m in unique for module in m.modules()]
    old_threads = torch.get_num_threads()
    bridges, references = [], []
    live, requests, finished = {}, {}, {}
    closing = threading.Event()
    pending = iter(enumerate(tasks))
    pool = None

    def assign(slot):
        item = next(pending, None)
        if item is None:
            live.pop(slot, None)
            return
        number, spec = item
        live[slot] = dict(number=number, spec=spec, start=time.monotonic(), exchanges=0, revision=-1,
            featureMs=0., inferenceMs=0., referenceMs=0., policyRequests=dict.fromkeys(MODELS, 0),
            referenceRequests=0, observed=_counts(), observedSeats=[_phase_counts() for _ in range(spec['players'])])
        requests[slot] = dict(op='start', spec=spec)

    def bridge_call(slot, request):
        ep = live[slot]
        ep['exchanges'] += 1
        if ep['exchanges'] > ep['spec']['maxSteps'] + 1:
            raise RuntimeError('Stress transport decision cap exceeded')
        state = bridges[slot].call(request)
        if not isinstance(state, dict) or 'error' in state:
            raise RuntimeError('Stress bridge failure/cap')
        return state

    def decision(slot, state):
        ep, spec = live[slot], live[slot]['spec']
        kind = state.get('kind')
        required = {'terminal', 'kind', 'controller', 'seat', 'phase', 'revision'}
        required |= {'request'} if kind == 'reference' else {'observation', 'featureMs'}
        if state.get('terminal') is not False or kind not in ('policy', 'reference') or set(state) != required:
            raise ValueError('Unexpected decision fields/kind; expert labels are forbidden')
        seat, phase, revision = (state.get(key) for key in ('seat', 'phase', 'revision'))
        if (type(seat) is not int or not 0 <= seat < spec['players'] or phase not in PHASES or
                type(revision) is not int or not ep['revision'] < revision < spec['maxSteps']):
            raise ValueError('Invalid decision actual-seat/phase/revision')
        name = spec['controllers'][seat]
        if state['controller'] != name or (kind == 'reference') != (name == 'reference'):
            raise ValueError('Decision controller differs from actual-seat assignment')
        if kind == 'policy' and (name not in MODELS or phase not in LEARNED_PHASES):
            raise ValueError('Policy escaped frozen population/learned phases')
        ep['revision'] = revision
        return name, seat, phase

    def reference_call(slot, state):
        ep, spec = live[slot], live[slot]['spec']
        request = state['request']
        if spec['map'] != 'Germany' or not isinstance(request, dict) or set(request) != {'requestId', 'revision', 'player', 'state'}:
            raise ValueError('Reference request outside Germany/public API')
        public = request['state']
        if (type(request['player']) is not int or request['player'] != state['seat'] or
                type(request['revision']) is not int or request['revision'] != state['revision'] or
                not isinstance(request['requestId'], str) or not request['requestId'] or
                not isinstance(public, dict) or public.get('seed') != 'secret' or
                public.get('powerPlantsDeck') != [] or public.get('hiddenLog') != [] or
                'powerPlantDeckAfterStep3' in public or 'automation' in public):
            raise ValueError('Unbound/unredacted public reference request')
        options, players = public.get('options'), public.get('players')
        if (not isinstance(options, dict) or options.get('map') != 'Germany' or
                options.get('variant') != spec['variant'] or options.get('fastBid') is not spec['fastBid'] or
                not isinstance(players, list) or len(players) != spec['players'] or
                any(not isinstance(p, dict) or p.get('lastMove') is not None for p in players) or
                public.get('phase') != state['phase'] or not isinstance(public.get('currentPlayers'), list) or
                not public['currentPlayers'] or public['currentPlayers'][0] != state['seat']):
            raise ValueError('Public Germany decision/actual-seat/options mismatch')
        if options['fastBid'] and (public.get('currentBid') != 0 or any(p.get('bid') != 0 for p in players)):
            raise ValueError('Submitted sealed bids must be hidden')
        began = time.perf_counter()
        if closing.is_set():
            raise RuntimeError('Stress collector closing')
        if references[slot] is None:
            references[slot] = ReferenceProcess(artifact, reference_python)
        # A constructor may return after another worker triggered cleanup.
        if closing.is_set():
            references[slot].close()
            raise RuntimeError('Stress collector closed during reference creation')
        response = references[slot].decide(request)
        if (not isinstance(response, dict) or 'index' in response or 'move' not in response or
                response.get('requestId') != request['requestId'] or response.get('revision') != request['revision']):
            raise ValueError('Unbound reference atomic response')
        ep['referenceMs'] += 1000 * (time.perf_counter() - began)
        ep['referenceRequests'] += 1
        return response

    def call(item):
        slot, request = item
        state = bridge_call(slot, request)
        while state.get('terminal') is False:
            name, seat, phase = decision(slot, state)
            if state['kind'] == 'policy':
                break
            response = reference_call(slot, state)
            live[slot]['observed'][name][phase] += 1
            live[slot]['observedSeats'][seat][phase] += 1
            state = bridge_call(slot, dict(op='step', response=response))
        return slot, state

    try:
        torch.set_num_threads(protocol['inferenceThreads'])
        for model in unique:
            model.eval()
        for _ in range(min(workers, len(tasks))):
            bridges.append(LineProcess(['node', HERE / 'stress_game.cjs']))
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
                        if state['steps'] <= ep['revision']:
                            raise ValueError('Terminal did not advance past the pending decision')
                        observed = ep['observed']
                        if any(state['counts'][name] != observed[name] for name in (*MODELS, 'reference')):
                            raise ValueError('Collector/engine policy/reference request counters disagree')
                        reconstructed = copy.deepcopy(observed)
                        for seat, name in enumerate(spec['controllers']):
                            fixed = 'fixedV2' if name == 'expert24' else 'fixedV1' if name in FROZEN else name
                            for phase in PHASES:
                                remaining = state['seatCounts'][seat][phase] - ep['observedSeats'][seat][phase]
                                if remaining < 0 or (name == 'reference' and remaining):
                                    raise ValueError('Collector/engine actual-seat request counters disagree')
                                reconstructed[fixed][phase] += remaining
                        if reconstructed != state['counts']:
                            raise ValueError('Collector/engine fixed-phase routing disagrees')
                        result = dict(spec=spec, terminal=True, credit=credit, allSeatCredit=state['credit'],
                            steps=state['steps'], rounds=state['rounds'], counts=state['counts'],
                            seatCounts=state['seatCounts'], publicChecks=state['publicChecks'],
                            policyRequests=ep['policyRequests'], referenceRequests=ep['referenceRequests'],
                            featureMs=ep['featureMs'], inferenceMs=ep['inferenceMs'], referenceMs=ep['referenceMs'],
                            seconds=time.monotonic() - ep['start'])
                        finished[ep['number']] = result
                        assign(slot)
                        continue
                    if state.get('terminal') is not False:
                        raise ValueError('Missing strict terminal flag')
                    name = state['controller']
                    tensors = _observation(state['observation'], name, spec)
                    if not _finite_ms(state['featureMs']):
                        raise ValueError('Invalid feature timing')
                    ep['featureMs'] += state['featureMs']
                    groups.setdefault(name, []).append((slot, tensors, state))
                for name in sorted(groups):
                    items = groups[name]
                    began = time.perf_counter()
                    tensors = (batch if name == 'expert24' else old_batch)([r for _, r, _ in items])
                    mask = tensors['actionMask']
                    expected_mask = torch.arange(mask.shape[1])[None, :] < torch.tensor(
                        [len(r['actions']) for _, r, _ in items])[:, None]
                    if mask.dtype != torch.bool or not torch.equal(mask, expected_mask):
                        raise ValueError('Incomplete authoritative full-menu action mask')
                    logits, values = population[name](tensors)
                    if logits.shape != mask.shape or values.shape != (len(items),):
                        raise ValueError('Inference shape mismatch')
                    # Only valid logits must be finite. Padding may be -inf or
                    # huge finite numbers; explicitly masking prevents selection
                    # even when every real score is below the legacy -1e9 floor.
                    if not torch.isfinite(logits[mask]).all() or not torch.isfinite(values).all():
                        raise ValueError('Nonfinite policy output')
                    logits = logits.masked_fill(~mask, -torch.inf)
                    actions = logits.argmax(-1).tolist()
                    elapsed = 1000 * (time.perf_counter() - began) / len(items)
                    for action, (slot, r, state) in zip(actions, items):
                        if not 0 <= action < len(r['actions']):
                            raise ValueError('Greedy action outside authoritative full menu')
                        ep = live[slot]
                        ep['policyRequests'][name] += 1
                        ep['observed'][name][state['phase']] += 1
                        ep['observedSeats'][state['seat']][state['phase']] += 1
                        ep['inferenceMs'] += elapsed
                        requests[slot] = dict(op='step', index=action)
        if len(finished) != len(tasks):
            raise RuntimeError('Incomplete stress collection')
        return [finished[number] for number in range(len(tasks))]
    finally:
        closing.set()
        close_error = _close_all(bridges + references)
        try:
            if pool is not None:
                pool.shutdown(wait=True, cancel_futures=True)
        finally:
            # Late lazy construction cannot strand an orphan service.
            late_error = _close_all(references)
            for module, training in modes:
                module.training = training
            torch.set_num_threads(old_threads)
        if (close_error or late_error) is not None and len(finished) == len(tasks):
            raise RuntimeError('Stress process cleanup failed') from (close_error or late_error)
