"""Frozen three-arm replica stress-v1 collector (narrow 6a7cdc6 stress delta).

Independent namespace validation; greedy central inference; unchanged legacy
loaders and reference transport. Only compact terminal outcomes leave collect:
no observations, trajectories, labels, reference requests, or atomic moves.
"""
import copy
import hashlib
import types
from concurrent.futures import ThreadPoolExecutor
import itertools
import json
import math
from pathlib import Path
import threading
import time

import torch
from huggingface_hub import get_hf_file_metadata, hf_hub_download, hf_hub_url

from candidates import POOL
from data import digest
from expert_policy import load as load_expert, row, batch, SCHEMA as EXPERT_SCHEMA
from expert_rollout import LineProcess
from model import DIMS, SCHEMA as OBSERVATION_SCHEMA
from reference_evaluate import ReferenceProcess
from reference_recover import CACHE, ROOT
from residual import row as old_row, batch as old_batch, load as load_old

HERE = Path(__file__).resolve().parent
PROTOCOL = json.loads((HERE / 'replica-stress-protocol-v1.json').read_text())
NAMESPACE = 'pg-multimap-replica-stress-20261109-v1'
MAPS = ('Germany', 'USA', 'France', 'UK & Ireland')
POLICIES = ('replica1', 'replica2', 'ppo2')
EXPERT_MODELS = ('expert24', 'replica1', 'replica2')
MODELS = (*EXPERT_MODELS, 'ppo0', 'ppo1', 'ppo2')
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


PROTOCOL_SHA256 = '99d6e0e4eac7808f2de8c335361c5611ae4a93edfe8778b30dbe4139fb265d69'
FROZEN_SOURCES = {'stress_game.cjs': '7d3a6408f220bf228837e807ca5e3ed0c6c2f18069a11d0bb8d29f4531b28d47',
 'stress_rollout.py': 'fd1c861e96c42341994fb48fbde9885240ea9d3a3333f13f1297cacae9e7757e',
 'stress_study.py': '1014ed49dbb54d3b0faccf61d694847d8bf3f12967d0abdd44ec1af4e45c2d6f',
 'expert_policy.py': '5304112f56195eec7aa6f89967503e6d08768be7ffb4fc232a7fcfe3349b4213',
 'expert_game.cjs': '6d0580b5054e5fb18b5b872827796665125d9997dd31b720dfe2becb00369942',
 'expert_rollout.py': '3deb6af55d5210caa04d02210a14bd3ff9c7af413afa2b39ef72bb3e3ebfb77e',
 'expert_ppo.py': '4357357fde973deff89d9df908622297ccce6fb89446c6e4cf314f20a5383bd0',
 'expert-protocol-v2.json': 'd9180c76ce072fe03fb1c325466d8d768a919d040ffd27229d4f375f61065796',
 'expert_replicas_v1.py': '8250728734ade2014dff94eff6d1f857b674124f5aa142ccc24002f1aa730cb4',
 'expert-replicas-protocol-v1.json': '130bb9d99e050211c0aecf86b46a98bb8e2cba6fb44371674cd17447d9b7aa5f',
 'replica_game_v1.cjs': 'b6f40b2fcc640484b3c1843d572df377dad34eee2ee1aec2b57241b73c0bd7c1',
 'replica_protocol_v1.cjs': 'c39a6844aaa70d4ec3dde6ab02969afe9aae176417ca3ad315ad260dec692a8a',
 'job_expert_replicas_v1.py': '66163649e35c80377f50d50d0d84d11f98f74b3c6c2d6968e233cb1b4f4032fb',
 'test_expert_replicas_v1.py': 'ffb227869444051ab5373872364f4263016033c0dbb0ffde5538c6e9519e6b6d',
 'launch_expert_replicas_v1.py': '5e6126d482df3febc290a2de2b39777107b8fe33939662e00349a042e183423c',
 'test_launch_expert_replicas_v1.py': '2802ec781d84f0413619d32e502aeff669d525c1e5e9d73018e8eeeb7b7e5da5',
 'preflight_expert_replicas_v1.py': '91c5577472bfe4767f987ec7dae6d277b09bcfcb73443dd614feb3a31031d4f0',
 'test_preflight_expert_replicas_v1.py': '9748637b386321dff38b5f0584acceea33f0d7926c9605fb2f845a16b46b6a3c',
 'game_rl.cjs': 'b3e8996da51841340b6f4f77b803dcbf01e2f72938ee44b7ba66f593d8167157',
 'game.cjs': '3a36d6a74407d7a8454edba898fabf9848a4c0615e960bb94554ae363b5b1e2b',
 'features.cjs': '1ced47a4a5e65946a8fdb207f0d6f87d9b535c698729ec36e008d39e0914803b',
 'teacher.cjs': 'd741947ba120f56a17953b92dc553a30cd4476f9594b3161a8a0adb1af0e88cb',
 'teacher_v2.cjs': '89a5b6c9e8520224eeb1cb34d8543cfccb2d8313002626a50907d4fa996cbdf6',
 'economics_v2.cjs': 'dbb2216b3572e4afc882a3da11f683abd998a54b8672c7acda4843ee142d1897',
 'model.py': '4f790d8fc718ed63f4df1a34c4a71ce1815abfaff50171cb1f6f256fe2f62a3e',
 'residual.py': '83e8cac000a05b2a015fa4f6612e0e4193ecd134e72f79e77123a2a10346e480',
 'candidates.py': '1c839a805d7bbe7a58415c2cea2ae1e98685d6373f3ee9ebbace1e841914d5ed',
 'candidate-pool-v1.json': 'a4f5d80966d9dd5b7af712459dffea255590eeb158b3a8e73cb66b0045d29a4b',
 'ppo.py': 'ea911838c835fc31df2a2566f8ef97531248f43e3cbf6f8cfa4bce0d6d164bee',
 'ppo-protocol-v1.json': '51f86acbbd1a495213c40554b3cc0c7933c92a2fc1608690397fbee76dad3cfe',
 'data.py': '3a166d6baf8e294aff56ac13310867d34892347fc754493def1d347d65670492',
 'reference_evaluate.py': 'e22e7b6e9de687d1c903217c03735434622e22e951cfbf030827f430e757cab9',
 'reference_recover.py': '1d0b7f87fa22c8e5673152abc4496f0b62ce017c2bcdc8b39ae8658febd7fadc',
 'reference_game.cjs': 'cd4e87bc0754a67b3a9bfffba17ac37353c5f1c4391aacc2ae92e18ad2d71949',
 'reference_compatibility.cjs': 'b3e87335eb97bdc301f6eebdd8e3adcb2bcfd3737d8d6d0eca00ff9156a45694',
 'rollout.py': 'ec6bf43926c1ce884e91b402d1881c7eb0efe728b6230eec2ae2fbb209791300',
 'requirements-cpu.txt': '975c2199adeee3550ce7ca31644833fa3fe5605789e6067e86b48610acb8ecf4'}


PROTOCOL_FILE_SHA256 = '1ca5a8fd0979f785cec0656a8738fbc7d5b92f9eb70a9729e0c26ec7916477d3'

def _check_protocol():
    if digest(HERE / 'replica-stress-protocol-v1.json') != PROTOCOL_FILE_SHA256:
        raise ValueError('Frozen replica stress protocol bytes changed')
    for value in (PROTOCOL, json.loads((HERE / 'replica-stress-protocol-v1.json').read_text())):
        if hashlib.sha256(_canonical(value).encode()).hexdigest() != PROTOCOL_SHA256:
            raise ValueError('Frozen replica stress protocol changed')


def _protocol():
    _check_protocol()
    for name, sha in FROZEN_SOURCES.items():
        if digest(HERE / name) != sha:
            raise ValueError('Frozen old source changed: ' + name)
    return copy.deepcopy(PROTOCOL)


_protocol()  # Reject altered protocol/source before any public API can run.
SMOKE_SCOPES = tuple(tuple(scope) for scope in PROTOCOL['smokeScopes'])


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
    """80 production cells or eight fixed smoke scopes, three arms, all focal seats.

    Smoke preserves the 80-cell ordinal used to assign opponents.
    """
    protocol = _protocol()
    if type(smoke) is not bool:
        raise ValueError('Stress smoke flag must be boolean; no training split')
    tasks = []
    cells = itertools.product(MAPS, range(2, 7), ('original', 'recharged'), (False, True))
    namespace = NAMESPACE + (':smoke' if smoke else '')
    for ci, (map_name, players, variant, fast) in enumerate(cells):
        if smoke and (map_name, players, variant, fast) not in SMOKE_SCOPES:
            continue
        cell = f'{map_name}|{players}|{variant}|{int(fast)}'
        for panel in PANELS:
            for deal in range(1 if smoke else 8):
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
            type(spec['deal']) is not int or not 0 <= spec['deal'] < (1 if spec['smoke'] else 8) or
            type(spec['focalSeat']) is not int or not 0 <= spec['focalSeat'] < spec['players'] or
            type(spec['maxSteps']) is not int or spec['maxSteps'] != 4000):
        raise ValueError('Noncanonical stress spec/scope')
    if spec['smoke'] and (spec['map'], spec['players'], spec['variant'], spec['fastBid']) not in SMOKE_SCOPES:
        raise ValueError('Outside frozen eight-scope smoke')
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


def model_pins():
    protocol = _protocol()
    pool_path = HERE / protocol['oldPool']
    if (digest(pool_path) != protocol['oldPoolSha256'] or
            _canonical(POOL) != _canonical(json.loads(pool_path.read_text()))):
        raise ValueError('Frozen legacy candidate pool changed')
    pins = [protocol['expertOpponent'], *protocol['replicas'], *POOL['members']]
    if [p['name'] for p in pins] != list(MODELS) or len({p['sha256'] for p in pins}) != 6:
        raise ValueError('Exact distinct six-checkpoint population required')
    return copy.deepcopy(pins)


def serving_configs(artifact=DEFAULT_ARTIFACT, reference_python=DEFAULT_REFERENCE_PYTHON):
    """Complete current serving identities, including unchanged a75 replica sources."""
    _protocol()
    from expert_ppo import config
    from expert_replicas_v1 import Replica
    from ppo import config as old_config, make_protocol
    kwargs = dict(artifact=artifact, reference_python=reference_python, workers=6)
    result = {'expert24': config(False, **kwargs)}
    for number in (1, 2):
        replica = Replica(number)
        result[f'replica{number}'] = replica.config(False, protocol=replica.protocol, **kwargs)
    result.update({f'ppo{i}': old_config(False, make_protocol(i)) for i in range(3)})
    return result


def _saved_configs(serving):
    """Independent historical PPO0 exception, never inferred from loaded weights.

    PPO0 predates replica-aware training helpers. Every saved config field still
    matches exactly; only its 11-file source map comes from the pinned original
    Git object. All current serving bytes remain separately pinned to 6a7cdc6.
    """
    _protocol()
    expected = copy.deepcopy(serving)
    historical = PROTOCOL['ppo0HistoricalTraining']
    current = serving['ppo0']['sourceFiles']
    if (set(current) != set(historical['sourceFiles']) or
            sorted(name for name, sha in current.items() if sha != historical['sourceFiles'][name]) !=
            historical['nonservingDifferences'] or
            any(sha != FROZEN_SOURCES[name] for name, sha in current.items())):
        raise ValueError('Unexpected PPO0 historical/current source differences')
    expected['ppo0']['sourceFiles'] = copy.deepcopy(historical['sourceFiles'])
    return expected


def model_configs(artifact=DEFAULT_ARTIFACT, reference_python=DEFAULT_REFERENCE_PYTHON):
    """Expected complete saved-checkpoint configs, not current serving provenance."""
    return _saved_configs(serving_configs(artifact, reference_python))


def model_provenance(artifact=DEFAULT_ARTIFACT, reference_python=DEFAULT_REFERENCE_PYTHON):
    serving = serving_configs(artifact, reference_python)
    configs = _saved_configs(serving)
    result = {pin['name']: dict(pin=pin, config=serving[pin['name']],
        role='opponent-only' if pin['name'] == 'expert24' else
             'focal-only' if pin['name'].startswith('replica') else
             'shared-focal-control-and-opponent' if pin['name'] == 'ppo2' else 'opponent-only')
        for pin in model_pins()}
    result['ppo0'].update(checkpointConfig=configs['ppo0'],
                          historicalTrainingSource=copy.deepcopy(PROTOCOL['ppo0HistoricalTraining']))
    return result


def _validate_saved(name, pin, model, saved, config):
    from residual import SCHEMA as OLD_SCHEMA
    expert = name in EXPERT_MODELS
    if (not isinstance(saved, dict) or saved.get('schema') != (EXPERT_SCHEMA if expert else OLD_SCHEMA) or
            type(saved.get('update')) is not int or saved['update'] != pin['update'] or
            type(saved.get('width')) is not int or saved['width'] != 64 or
            type(saved.get('bound')) is not int or saved['bound'] != (16 if expert else 8) or
            (expert and (saved.get('stage') != 'train' or saved.get('priorAsActionFeature') is not True)) or
            _canonical(saved.get('config')) != _canonical(config)):
        raise ValueError(name + ' checkpoint schema/update/full saved config mismatch')
    if not isinstance(model, torch.nn.Module) or not all(torch.isfinite(t).all() for t in model.state_dict().values()):
        raise ValueError(name + ' nonfinite/invalid model state')


def load_models(artifact=DEFAULT_ARTIFACT, reference_python=DEFAULT_REFERENCE_PYTHON,
                local_checkpoints=None):
    """All six immutable metadata checks precede ANY download; local copies are pinned too.

    Explicit retained paths are allowed only for the three expert-family pins.
    No arbitrary checkpoint selection, local source edits or global monkeypatches.
    Cache placement outside output is enforced by the worker/run boundary.
    """
    pins = model_pins()
    if local_checkpoints is None:
        local_checkpoints = {}
    if (not isinstance(local_checkpoints, dict) or not set(local_checkpoints) <= set(EXPERT_MODELS) or
            any(not isinstance(p, (str, Path)) for p in local_checkpoints.values())):
        raise ValueError('Local checkpoints map may contain only pinned expert-family roles')
    metadata_by_name = {}
    for pin in pins:
        metadata = get_hf_file_metadata(hf_hub_url(pin['repo'], pin['path'], revision=pin['revision']))
        if (metadata.commit_hash != pin['revision'] or type(metadata.size) is not int or
                not 0 < metadata.size <= CHECKPOINT_MAX_BYTES):
            raise ValueError(pin['name'] + ' checkpoint metadata exceeds 16 MiB or immutable revision differs')
        metadata_by_name[pin['name']] = metadata
    if sum(m.size for m in metadata_by_name.values()) > PROTOCOL['checkpointAggregateMaxBytes']:
        raise ValueError('Aggregate six-checkpoint budget exceeded')
    configs = model_configs(artifact, reference_python)
    models = {}
    for pin in pins:
        name = pin['name']
        path = Path(local_checkpoints[name] if name in local_checkpoints else
                    hf_hub_download(pin['repo'], pin['path'], revision=pin['revision']))
        if not path.is_file() or path.stat().st_size != metadata_by_name[name].size or digest(path) != pin['sha256']:
            raise ValueError(name + ' checkpoint size/hash mismatch')
        model, saved = (load_expert if name in EXPERT_MODELS else load_old)(path)
        _validate_saved(name, pin, model, saved, configs[name])
        model.eval()
        model.requires_grad_(False)
        model._replica_stress_role = name
        models[name] = model
    if len({id(m) for m in models.values()}) != 6:
        raise ValueError('Checkpoint roles must not alias')
    return models


def prefetch(artifact=DEFAULT_ARTIFACT, reference_python=DEFAULT_REFERENCE_PYTHON,
             local_checkpoints=None):
    return load_models(artifact, reference_python, local_checkpoints=local_checkpoints)


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
        for names, fixed in ((EXPERT_MODELS, 'fixedV2'), (FROZEN, 'fixedV1')):
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
    _check_protocol()
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
        result = (row if name in EXPERT_MODELS else old_row)(observation)
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
        raise ValueError('Exact six-model replica stress population required')
    if any(not isinstance(model, torch.nn.Module) for model in population.values()):
        raise ValueError('Invalid frozen inference model')
    if any(getattr(model, '_replica_stress_role', name) != name for name, model in population.items()):
        raise ValueError('Frozen model roles swapped')
    if len({id(m) for m in population.values()}) != len(MODELS):
        raise ValueError('Distinct frozen models required; role aliases forbidden')
    unique = list(population.values())
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
            bridges.append(LineProcess(['node', HERE / 'replica_stress_game_v1.cjs']))
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
                            fixed = 'fixedV2' if name in EXPERT_MODELS else 'fixedV1' if name in FROZEN else name
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
                    tensors = (batch if name in EXPERT_MODELS else old_batch)([r for _, r, _ in items])
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


# Truly generic primitives retain original implementations via private namespaces.
# Family-hardcoded _terminal/_observation/collect are explicit versioned copies above.
import stress_rollout as _legacy

def _bind_generic(function):
    bound = types.FunctionType(function.__code__, globals(), function.__name__, function.__defaults__, function.__closure__)
    bound.__kwdefaults__ = function.__kwdefaults__
    return bound

for _name in ('_phase_counts', '_counts', '_valid_counter', '_finite_ms', '_close_all'):
    globals()[_name] = _bind_generic(getattr(_legacy, _name))
