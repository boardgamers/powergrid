"""Isolated expert-v2 replicas: unchanged algorithms, separately guarded scopes.

No frozen module globals/defaults are mutated. Original config guards still run
against the original protocol; replica identity additionally pins this adapter.
"""
import copy
import json
from pathlib import Path
import types

import expert_ppo as trainer
import expert_rollout as rollout
from data import digest

HERE = Path(__file__).resolve().parent
PROTOCOL_PATH = HERE / 'expert-replicas-protocol-v1.json'
# Independent literals, NOT values learned from the editable study JSON at
# import. The JS boundary independently carries the same critical pins.
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
CRITICAL_PROTOCOL = {
    'schema': 'multimap-expert-replicas-v1',
    'baseProtocol': 'expert-protocol-v2.json',
    'frozenSources': FROZEN_SOURCES,
    'replicas': [
        {'id': 1, 'seed': 190731, 'seedNamespace': 'pg-multimap-expert-replicas-v1-r1'},
        {'id': 2, 'seed': 827119, 'seedNamespace': 'pg-multimap-expert-replicas-v1-r2'},
    ],
    'transferMaps': [],
    'qualificationEligible': False,
    'reservedFinalSeedsUsed': False,
    'counts': {
        'trainingGamesPerReplica': 2720, 'selectionGamesPerReplica': 2240,
        'confirmationGamesPerArmPerReplica': 640, 'confirmationDealRootsPerReplica': 160,
        'totalGamesPerReplica': 6240, 'totalGames': 12480,
    },
    'analysis': {
        'primary': 'selected-minus-teacher-v2', 'unit': 'paired-all-seat-deal',
        'weighting': 'equal-80-map-count-rule-cells', 'dealsPerCell': 2,
        'normal95Z': 1.96, 'pooledInference': False, 'winnerSelection': False,
        'betweenReplicaSpread': 'descriptive-includes-evaluation-noise',
    },
    'budget': {
        'replicas': 2, 'workers': 6, 'flavor': 'cpu-upgrade', 'timeout': '3h',
        'maxSegmentsPerReplica': 2, 'maxTotalJobHours': 12,
        'studyArtifactMaxBytes': 134217728, 'localStorageMaxBytes': 8589934592,
        'minimumFreeBytes': 2147483648,
    },
}
SOURCES = (
    'expert-replicas-protocol-v1.json', 'expert_replicas_v1.py',
    'replica_game_v1.cjs', 'replica_protocol_v1.cjs', 'job_expert_replicas_v1.py',
    'test_expert_replicas_v1.py', 'launch_expert_replicas_v1.py',
    'test_launch_expert_replicas_v1.py', 'preflight_expert_replicas_v1.py',
    'test_preflight_expert_replicas_v1.py',
)


def _canonical(value):
    # JSON canonicalization is type-sensitive: False != 0 and True != 1.
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def _read_study():
    study = json.loads(PROTOCOL_PATH.read_text())
    if not isinstance(study, dict) or any(key not in study for key in CRITICAL_PROTOCOL):
        raise ValueError('Missing critical replica protocol fields')
    if _canonical({key: study[key] for key in CRITICAL_PROTOCOL}) != _canonical(CRITICAL_PROTOCOL):
        raise ValueError('Frozen replica protocol scope/pins/budget changed')
    return study


STUDY = _read_study()
BASE = copy.deepcopy(trainer.PROTOCOL)


def bind(function, **overrides):
    namespace = dict(function.__globals__)
    namespace.update(overrides)
    result = types.FunctionType(function.__code__, namespace, function.__name__,
                                function.__defaults__, function.__closure__)
    result.__kwdefaults__ = function.__kwdefaults__
    return result


def protocol_for(replica):
    if type(replica) is not int or replica not in (1, 2):
        raise ValueError('Replica must be integer 1 or 2')
    if _canonical(_read_study()) != _canonical(STUDY):
        raise ValueError('Replica protocol changed during execution')
    for name, sha in FROZEN_SOURCES.items():
        if digest(HERE / name) != sha:
            raise ValueError('Frozen expert source changed')
    if _canonical(BASE) != _canonical(json.loads((HERE / 'expert-protocol-v2.json').read_text())):
        raise ValueError('Frozen base protocol changed')
    expected_bridge = (HERE / 'expert_game.cjs').read_bytes().replace(
        b"const protocol = require('./expert-protocol-v2.json');",
        b"const protocol = require('./replica_protocol_v1.cjs')(process.argv[2]);")
    if (HERE / 'replica_game_v1.cjs').read_bytes() != expected_bridge:
        raise ValueError('Replica bridge differs beyond explicit protocol binding')
    entry = CRITICAL_PROTOCOL['replicas'][replica - 1]
    return dict(copy.deepcopy(BASE), seed=entry['seed'], seedNamespace=entry['seedNamespace'], transferMaps=[])


class Replica:
    def __init__(self, replica):
        self.replica = replica
        self.protocol = protocol_for(replica)

        def guard(protocol):
            if rollout._canonical(protocol) != rollout._canonical(protocol_for(replica)):
                raise ValueError('Replica recipe/scope overrides forbidden')

        self.plans = bind(rollout.plans, _protocol=guard)
        self.validate_tasks = bind(rollout.validate_tasks, _protocol=guard, plans=self.plans)
        # Private bridge argv, not process-global environment or legacy mutation.
        class Bridge(rollout.LineProcess):
            def __init__(self, argv, **kwargs):
                if argv != ['node', HERE / 'expert_game.cjs']:
                    raise ValueError('Unexpected bridge command')
                super().__init__(['node', HERE / 'replica_game_v1.cjs', str(replica)], **kwargs)
        self.collect = bind(rollout.collect, validate_tasks=self.validate_tasks, LineProcess=Bridge)

    def config(self, smoke=False, protocol=None, **kwargs):
        if rollout._canonical(protocol) != rollout._canonical(protocol_for(self.replica)):
            raise ValueError('Wrong replica protocol')
        # Retain every original engine/reference/model/config check unchanged.
        result = trainer.config(smoke, BASE, **kwargs)
        result.update(schema='multimap-expert-replica-identity-v1', replica=self.replica,
                      protocol=copy.deepcopy(protocol), replicaStudy=copy.deepcopy(STUDY))
        result['sourceFiles'].update({'ai/multimap/' + n: digest(HERE / n) for n in SOURCES})
        return result

    def run(self, checkpoint, output, smoke=False, stop_after=None, callback=None, **kwargs):
        # Bind per call, retaining exact checkpoint transaction/RNG/optimizer code.
        run = bind(trainer.run, make_protocol=lambda: protocol_for(self.replica),
                   config=self.config, collect=self.collect, plans=self.plans)
        return run(checkpoint, output, smoke, stop_after, callback, **kwargs)
