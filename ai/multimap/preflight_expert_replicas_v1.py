"""Real-service smoke and exact interrupted training replay for both replicas.

Never runs production roots, submits jobs, publishes, selects between replicas,
or changes serving source. Retains bounded compact outcomes/checkpoints only.
"""
import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time
from unittest.mock import patch

import torch
from data import ROOT, atomic_json, digest
from expert_ppo import DEFAULT_ARTIFACT, DEFAULT_REFERENCE_PYTHON, artifact_budget
from expert_policy import load
from expert_replicas_v1 import Replica, PROTOCOL_PATH

TIMINGS = {'featureMs', 'inferenceMs', 'referenceMs', 'seconds'}
SMOKE_GAMES = 66


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read(path):
    path = Path(path)
    require(not path.is_symlink() and path.stat().st_size <= 128*1024**2, 'Unsafe smoke artifact')
    return json.loads(path.read_text())


def exact(left, right, label='transaction'):
    """Bit-exact tensors and strict structures; no numerical tolerances."""
    if isinstance(left, torch.Tensor):
        require(isinstance(right, torch.Tensor) and left.dtype == right.dtype and
                left.shape == right.shape and torch.equal(left, right), label + ': tensor')
    elif isinstance(left, dict):
        require(isinstance(right, dict) and left.keys() == right.keys(), label + ': keys')
        for key in left:
            exact(left[key], right[key], label + '.' + str(key))
    elif isinstance(left, (list, tuple)):
        require(type(left) is type(right) and len(left) == len(right), label + ': sequence')
        for i, (a, b) in enumerate(zip(left, right)):
            exact(a, b, label + '.' + str(i))
    else:
        require(type(left) is type(right) and left == right, label + ': value')


def validate_outcome(record, spec):
    from expert_rollout import _terminal
    require(record['spec'] == spec and record['terminal'] is True, 'Noncanonical/nonterminal smoke outcome')
    # The existing low-level validator does not authorize new roots; callers
    # reconstruct exact expected smoke tasks before calling this validator.
    state = dict(record, credit=record['allSeatCredit'])
    require(_terminal(state, spec) == record['credit'], 'Focal credit mismatch')
    require(spec['smoke'] is True and ':smoke:' in spec['seed'], 'Production root forbidden in preflight')
    require(all(type(record[k]) in (float, int) and record[k] >= 0 and
                __import__('math').isfinite(record[k]) for k in TIMINGS), 'Invalid timings')
    expert = sum(record['expertCounts'].values())
    require(expert == record['expertRequests'], 'Expert counter mismatch')
    if spec['split'] in ('selection', 'confirmation'):
        require(expert == 0, 'Evaluation expert labels forbidden')


def game_files(replica):
    p = replica.protocol
    def tasks(split, update=0, teacher=False):
        rows = replica.plans(split, update, smoke=True, protocol=p)
        return [dict(s, focalTeacher=True) for s in rows] if teacher else rows
    result = {'warmup.json': tasks('warmup')}
    for update in (1, 2):
        result[f'train-{update}.json'] = tasks('train', update)
    for name in ('0', 'teacher', 'warmup', '1', '2'):
        result[f'selection-{name}.json'] = tasks('selection', teacher=name == 'teacher')
    for name in ('selected', 'teacher'):
        result[f'confirmation-{name}.json'] = tasks('confirmation', teacher=name == 'teacher')
    require(sum(map(len, result.values())) == SMOKE_GAMES, 'Exact smoke schedule changed')
    return result


def compare_execution(one, two, replica):
    """Compare complete resumed tensors plus every compact scheduled outcome."""
    one, two = Path(one), Path(two)
    names = [set(p.name for p in path.iterdir()) for path in (one, two)]
    require(names[0] == names[1] and not any(n.endswith('.tmp') for n in names[0]), 'Full preflight file coverage')
    models = {}
    for name in ('initial.pt', 'warmup.pt', 'best.pt', 'last.pt'):
        _, left = load(one/name); _, right = load(two/name)
        if name == 'last.pt':
            for checkpoint, folder in ((left, one), (right, two)):
                require(checkpoint['optimizer']['state'], 'Optimizer must be populated')
                require(set(checkpoint['confirmations']) == {'selected', 'teacher'}, 'Completed confirmation transaction')
                for label, saved in checkpoint['confirmations'].items():
                    require(saved['sha256'] == digest(folder/f'confirmation-{label}.json'), 'Confirmation transaction hash')
                require(hashlib.sha256(checkpoint['bestArtifact']).hexdigest() == checkpoint['bestSha256'] ==
                        digest(folder/'best.pt'), 'Embedded committed best bytes')
            # Only confirmation file hashes differ because those JSON files
            # contain machine timings. Summary and all other metadata stay exact.
            for saved in (left, right):
                saved['confirmations'] = {k: v['summary'] for k, v in saved['confirmations'].items()}
        exact(left, right, name)
        models[name] = dict(exactStateAndMetadata=True, bytes=(one/name).stat().st_size)
    counters, public, experts = Counter(), Counter(), Counter()
    matched = 0
    file_tasks = game_files(replica)
    for name, tasks in file_tasks.items():
        left, right = read(one/name), read(two/name)
        require(len(left['games']) == len(right['games']) == len(tasks), 'Smoke game coverage')
        exact({k: v for k, v in left.items() if k != 'games'},
              {k: v for k, v in right.items() if k != 'games'}, name)
        for a, b, spec in zip(left['games'], right['games'], tasks):
            validate_outcome(a, spec); validate_outcome(b, spec)
            exact({k: v for k, v in a.items() if k not in TIMINGS},
                  {k: v for k, v in b.items() if k not in TIMINGS}, name)
            matched += 1
            counters.update({k: sum(v.values()) for k, v in a['counts'].items()})
            public.update(a['publicChecks']); experts[a['spec']['split']] += a['expertRequests']
    for name in names[0] - set(file_tasks) - set(models):
        require(name.endswith('.json'), 'Unexpected preflight file')
        exact(read(one/name), read(two/name), name)
    require(matched == SMOKE_GAMES and experts['warmup'] > 0 and experts['train'] > 0 and
            experts['selection'] == experts['confirmation'] == 0, 'Expert routing/exact game coverage')
    require(all(counters[c] > 0 for c in ('learner', 'warmupExpert', 'reference', 'self',
                                        'ppo0', 'ppo1', 'ppo2', 'fixedV1', 'fixedV2', 'focalTeacher')),
            'All controllers must execute in real smoke')
    return dict(exactTerminalAndCounterReplayMatches=matched, exactModelOptimizerRngAndHistory=True,
                models=models, controllersPerExecution=dict(counters), publicChecksPerExecution=dict(public),
                expertRequestsPerExecution=dict(experts))


def checkpoint_metadata():
    """All four principal model sizes are checked before any download."""
    from huggingface_hub import HfApi, get_hf_file_metadata, hf_hub_url, get_token, hf_hub_download
    replica = Replica(1); p = replica.protocol
    pins = [p['warmStart'], *p['opponentPool']]; api = HfApi(); metadata = []
    for pin in pins:
        require(api.model_info(pin['repo'], revision=pin['revision']).private, 'Private frozen models required')
        m = get_hf_file_metadata(hf_hub_url(pin['repo'], pin['path'], revision=pin['revision']), token=get_token())
        require(m.commit_hash == pin['revision'] and type(m.size) is int and 0 < m.size <= 16*1024**2,
                'Frozen model size/revision rejected')
        metadata.append(dict(pin=pin, bytes=m.size))
    warm = pins[0]
    path = Path(hf_hub_download(warm['repo'], warm['path'], revision=warm['revision']))
    require(path.stat().st_size == metadata[0]['bytes'] and digest(path) == warm['sha256'], 'Warm-start bytes')
    return path, metadata


def preflight(output):
    output = Path(output)
    require(not output.is_symlink() and output.resolve().parent == (ROOT/'ai/runs').resolve() and
            output.name.startswith('multimap-') and not output.exists(), 'Fresh ignored multimap output required')
    from launch_expert_replicas_v1 import check_local_storage
    check_local_storage(output)
    checkpoint, models = checkpoint_metadata()
    output.mkdir(parents=True)
    began = time.monotonic(); identities = {}; results = {}; manifests = {}; production_hashes = {}
    kwargs = dict(artifact=DEFAULT_ARTIFACT, reference_python=DEFAULT_REFERENCE_PYTHON)
    for replica_id in (1, 2):
        replica = Replica(replica_id)
        expected = replica.config(True, replica.protocol, workers=6, **kwargs)
        one = output/f'r{replica_id}-uninterrupted'/'expert'
        two = output/f'r{replica_id}-resumed'/'expert'
        with patch.dict(os.environ, {'EXPERT_WORKERS': '6'}):
            first = replica.run(checkpoint, one, smoke=True, **kwargs)
            require(replica.run(checkpoint, two, smoke=True, stop_after=1, **kwargs) is None, 'Interrupted boundary')
            before = {p.name: digest(p) for p in two.iterdir() if p.is_file()}
            # This is intentionally uncommitted damage, not a serving alteration.
            (two/'best.pt').write_bytes(b'uncommitted preflight damage')
            second = replica.run(checkpoint, two, smoke=True, **kwargs)
            exact(first, second, 'Completed resumed result')
            require(all(digest(two/n) == h for n, h in before.items() if n not in ('best.pt', 'last.pt', 'history.json')),
                    'Committed completed artifacts changed on resume')
            with patch.object(replica, 'collect', side_effect=AssertionError('Completed resume repeated games')):
                exact(replica.run(checkpoint, two, smoke=True, **kwargs), second, 'Completed resume')
        result = compare_execution(one, two, replica)
        for path in (one, two):
            artifact_budget(path)
            require(read(path/'config.json') == expected, 'Preflight source/runtime drift')
            manifests[path.parent.name] = {p.name: digest(p) for p in path.iterdir() if p.is_file()}
        require(replica.config(True, replica.protocol, workers=6, **kwargs) == expected, 'Source/runtime changed during preflight')
        identities[str(replica_id)] = expected; results[str(replica_id)] = result
        production_hashes[str(replica_id)] = {}
        for split, update in [('warmup', 0), ('selection', 0), ('confirmation', 0)] + [('train', i) for i in range(1, 33)]:
            planned = replica.plans(split, update, protocol=replica.protocol)
            encoded = json.dumps(planned, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
            production_hashes[str(replica_id)][f'{split}-{update}'] = hashlib.sha256(encoded).hexdigest()
    report = dict(schema='multimap-expert-replicas-preflight-v1', allChecksPassed=True,
        protocolSha256=digest(PROTOCOL_PATH), smokeIdentities=identities, results=results, manifests=manifests,
        modelMetadata=models, productionPlanHashes=production_hashes,
        totalTerminalGames=264, exactTerminalAndCounterReplayMatches=132,
        failures=0, interruptedAfterUpdate=1, completedCommittedWorkPreserved=True,
        deliberatelyCorruptedBestRepaired=True, completedResumePerformsNoCollection=True,
        exactRngRecoveryScope='Interruption after update 1, before remaining optimization and confirmation. Not an arbitrary-boundary RNG claim.',
        inheritedConfirmationResume='The unchanged trainer loads the selected model anew on a confirmation-only continuation, consuming initialization RNG. Tests separately verify that narrow constructor-only advance; final model/optimizer/outcomes are unchanged and no optimization repeats.',
        maps=Replica(1).protocol['trainMaps'], smokePlayers=[2], smokeRules=[dict(variant='original',fastBid=False)],
        additionalCountsAndRules='Production planners exhaustively checked in Python/JS tests; existing unchanged mechanics suite covers all 120 cells. This training smoke is deliberately the frozen two-player original/open smoke schedule, not every production rule.',
        onlySmokeRoots=True, reusedReferenceArtifact=True, productionGamesExecuted=0,
        seconds=time.monotonic()-began, qualified=False, qualificationEligible=False, reservedFinalSeedsUsed=False,
        note='Engineering smoke with real pinned policies and exact reference. Deliberate exact repeats test optimizer/RNG recovery, not independent strength or training-replication evidence.')
    atomic_json(output/'report.json', report)
    print(json.dumps({k:v for k,v in report.items() if k not in ('smokeIdentities','results','manifests','modelMetadata')}, indent=2))
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    preflight(args.output)
