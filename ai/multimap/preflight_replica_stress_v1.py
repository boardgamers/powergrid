"""Real pinned-policy engineering smoke, never production stress or paid jobs.

Two panels, eight fixed scopes, three arms, every seat: 198 games per execution.
Uninterrupted versus first-batch interruption/resume: 396 terminal executions and
198 exact matches. No publication, training, selection or strength conclusion.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import subprocess
import time
import types

import torch
from data import ROOT, atomic_json, digest
import replica_stress_rollout_v1 as rollout
import replica_stress_study_v1 as study

BASE_GIT = '6a7cdc6b46d497065a0f73aaf9ca465ce0d2a874'
TIMINGS = frozenset({'featureMs', 'inferenceMs', 'referenceMs', 'seconds'})
PANELS = ('strong', 'mixed')
GAMES_PER_PANEL = 99
BATCHES_PER_PANEL = 8


def require(condition, message):
    if not condition:
        raise ValueError(message)


def bind(function, **overrides):
    """Private function globals; never patch the original or frozen serving modules."""
    namespace = dict(function.__globals__)
    namespace.update(overrides)
    result = types.FunctionType(function.__code__, namespace, function.__name__,
                                function.__defaults__, function.__closure__)
    result.__kwdefaults__ = dict(function.__kwdefaults__ or {})
    return result


def exact(left, right, label):
    require(study.canonical(left) == study.canonical(right), label)


def model_state(models):
    """Hash all tensors and inference flags, not a sample or aggregate norm."""
    require(isinstance(models, dict) and set(models) == set(rollout.MODELS), 'Exact six model roles required')
    require(len({id(model) for model in models.values()}) == 6, 'Model roles must not alias')
    result = {}
    for name in rollout.MODELS:
        model = models[name]
        require(isinstance(model, torch.nn.Module) and getattr(model, '_replica_stress_role', None) == name,
                'Incorrect model role')
        require(all(not module.training for module in model.modules()) and
                all(not p.requires_grad for p in model.parameters()), 'Frozen inference models required')
        sha = hashlib.sha256()
        for key, tensor in sorted(model.state_dict().items()):
            require(torch.isfinite(tensor).all().item(), 'Nonfinite model tensor')
            data = tensor.detach().cpu().contiguous()
            sha.update(study.canonical([key, str(data.dtype), list(data.shape)]).encode())
            sha.update(data.reshape(-1).view(torch.uint8).numpy().tobytes())
        result[name] = dict(stateSha256=sha.hexdigest(), training=model.training,
                            moduleTraining={n: module.training for n, module in model.named_modules()},
                            parametersRequireGrad=[p.requires_grad for p in model.parameters()])
    return result


def retained_checkpoints():
    """Explicit audited copies, not an assumption about the default HF cache."""
    paths = {}
    for pin in rollout.model_pins():
        if pin['name'] not in rollout.EXPERT_MODELS:
            continue
        parts = pin['path'].split('/')
        require(len(parts) == 4 and parts[0] == 'runs' and parts[1].startswith('multimap-') and
                parts[2:] == ['expert', 'best.pt'],
                'Unexpected frozen expert checkpoint path')
        path = ROOT / 'ai/runs' / parts[1] / 'audit/restored/expert/best.pt'
        require(path.is_file() and not path.is_symlink() and
                0 < path.stat().st_size <= rollout.CHECKPOINT_MAX_BYTES and digest(path) == pin['sha256'],
                'Retained checkpoint missing or changed; do not silently replace it')
        paths[pin['name']] = path
    require(set(paths) == set(rollout.EXPERT_MODELS), 'Three retained expert-family copies required')
    return paths


def verify_old_source(identities):
    """Complete model configs verify reference/runtime; independently bind old source to Git."""
    hashes = {}
    for identity in identities.values():
        for name, sha in identity['frozenSources'].items():
            path = 'ai/multimap/' + name
            require(path not in hashes or hashes[path] == sha, 'Conflicting frozen source identities')
            hashes[path] = sha
        for provenance in identity['modelProvenance'].values():
            for name, sha in provenance['config']['sourceFiles'].items():
                name = name if '/' in name else 'ai/multimap/' + name
                if name.startswith('engine/dist/'):
                    # Generated engine modules are fully hashed in saved/current config.
                    require(digest(ROOT / name) == sha, 'Compiled authoritative engine changed')
                    continue
                require(name not in hashes or hashes[name] == sha, 'Conflicting model source identities')
                hashes[name] = sha
    for name, sha in hashes.items():
        require(digest(ROOT / name) == sha, 'Current frozen source changed')
        old = subprocess.check_output(['git', 'show', BASE_GIT + ':' + name], cwd=ROOT)
        require(hashlib.sha256(old).hexdigest() == sha, 'Old serving source differs from frozen Git')
    return hashes


def verify_historical_ppo0(identities):
    """The two historical trainer differences are authenticated, not waived."""
    historical = rollout._protocol()['ppo0HistoricalTraining']
    require(historical['nonservingDifferences'] == ['ppo.py', 'rollout.py'] and
            len(historical['sourceFiles']) == 11, 'Exact historical PPO0 source scope required')
    for identity in identities.values():
        provenance = identity['modelProvenance']['ppo0']
        exact(provenance['historicalTrainingSource'], historical, 'Historical training pin changed')
        expected = dict(provenance['config'], sourceFiles=historical['sourceFiles'])
        exact(provenance['checkpointConfig'], expected, 'Historical complete checkpoint config changed')
        current = provenance['config']['sourceFiles']
        require(set(current) == set(historical['sourceFiles']) and
                sorted(n for n, sha in current.items() if sha != historical['sourceFiles'][n]) ==
                historical['nonservingDifferences'], 'Unexpected current/historical source difference')
    for name, sha in historical['sourceFiles'].items():
        old = subprocess.check_output(['git', 'show', historical['sourceGit'] + ':ai/multimap/' + name], cwd=ROOT)
        require(hashlib.sha256(old).hexdigest() == sha, 'Historical PPO0 source differs from original Git')
    return historical


def compare_execution(one, two, identity):
    """Exact plans/summary/batches; only the four declared per-game timings may differ."""
    one, two = Path(one), Path(two)
    require(identity.get('smoke') is True and identity.get('panel') in PANELS, 'Smoke identity required')
    tasks = study.plan(identity['panel'], True)
    exact(identity['tasks'], tasks, 'Frozen smoke tasks changed')
    groups = study.batches(tasks)
    require(len(tasks) == GAMES_PER_PANEL and len(groups) == BATCHES_PER_PANEL, 'Exact smoke coverage')
    expected = {'plan.json', 'summary.json'} | {f'batch-{i:03}.json' for i in range(BATCHES_PER_PANEL)}
    for path in (one, two):
        study.artifact_budget(path)
        require({p.name for p in path.iterdir()} == expected and all(p.is_file() for p in path.iterdir()),
                'Complete compact smoke inventory required')
        exact(study.read(path / 'plan.json'), identity, 'Smoke identity drift')
    controllers, public = Counter(), Counter()
    outcomes = [[], []]
    matches = 0
    for index, tasks in enumerate(groups):
        left, right = (study.read(path / f'batch-{index:03}.json') for path in (one, two))
        games = [study.verify_batch(record, index, tasks) for record in (left, right)]
        exact({k: v for k, v in left.items() if k != 'games'},
              {k: v for k, v in right.items() if k != 'games'}, 'Batch metadata drift')
        for a, b in zip(*games):
            exact({k: v for k, v in a.items() if k not in TIMINGS},
                  {k: v for k, v in b.items() if k not in TIMINGS}, 'Non-timing replay mismatch')
            matches += 1
            controllers.update({k: sum(v.values()) for k, v in a['counts'].items()})
            public.update(a['publicChecks'])
        for combined, batch in zip(outcomes, games):
            combined.extend(batch)
    for path, games in zip((one, two), outcomes):
        expected_summary = study.analyze(games, identity['panel'], True)
        require(expected_summary['descriptiveOnly'] is True, 'Smoke must not claim strength')
        exact(study.read(path / 'summary.json'), expected_summary, 'Smoke summary drift')
    exact(study.read(one / 'summary.json'), study.read(two / 'summary.json'), 'Resumed summary differs')
    require(matches == GAMES_PER_PANEL, 'Smoke matches must cover every scheduled game')
    return dict(matches=matches, controllers=dict(controllers), publicChecks=dict(public))


def completed_resume(output, panel, expected):
    def forbidden(*args, **kwargs):
        raise AssertionError('Completed resume attempted model loading or collection')
    runner = bind(study.run, load_models=forbidden, collect=forbidden)
    exact(runner(output, panel, smoke=True), expected, 'Completed resume result drift')


def output_directory(output):
    path = Path(output).absolute()
    parent = ROOT / 'ai/runs'
    require(path.parent == parent and path.name.startswith('multimap-replica-stress-') and
            not parent.is_symlink() and not path.is_symlink(), 'Use a dedicated ignored replica-stress directory')
    require(not path.exists(), 'Preflight exists; inspect failure, never overwrite evidence')
    return path


def preflight(output):
    output = output_directory(output)
    # The unchanged storage helper includes the original decimal ceiling, 2 GiB
    # minimum free space and 1 GiB additional staging/recovery allowance.
    from launch_expert_replicas_v1 import check_local_storage
    from huggingface_hub import HfApi
    check_local_storage(output)
    rollout._protocol()
    api = HfApi()
    require(api.model_info(rollout.PROTOCOL['modelRepo']).private is True, 'Existing private model repository required')
    paths = retained_checkpoints()
    retained_hashes = {name: digest(path) for name, path in paths.items()}
    identities = {panel: study.identity(panel, True, 6, study.ARTIFACT, study.REFERENCE_PYTHON) for panel in PANELS}
    old_hashes = verify_old_source(identities)
    historical_ppo0 = verify_historical_ppo0(identities)
    output.mkdir(exist_ok=False)
    began = time.monotonic()
    loads = []
    states = {}
    def loader(**kwargs):
        models = rollout.load_models(**kwargs, local_checkpoints=paths)
        state = model_state(models)
        if loads:
            exact(state, loads[0]['state'], 'Reloaded model tensor/flags changed')
        loads.append(dict(state=state, models=models))
        states[id(models)] = state
        return models
    def collector(tasks, *args, **kwargs):
        require(all(s['smoke'] is True and ':smoke:' in s['seed'] for s in tasks), 'Production collection forbidden')
        models = kwargs['models']
        require(id(models) in states, 'Only verified preflight-loaded models allowed')
        exact(model_state(models), states[id(models)], 'Model changed before collection')
        result = rollout.collect(tasks, *args, **kwargs)
        exact(model_state(models), states[id(models)], 'Model changed during inference')
        return result
    runner = bind(study.run, load_models=loader, collect=collector)
    controllers, public = Counter(), Counter()
    matches = 0
    manifests = {}
    committed_proofs = {}
    for panel in PANELS:
        one, two = (output / (panel + '-' + mode) for mode in ('uninterrupted', 'resumed'))
        first = runner(one, panel, smoke=True)
        require(runner(two, panel, smoke=True, stop_after_batches=1) is None, 'Interruption boundary not honored')
        committed = {p.name: digest(p) for p in two.glob('batch-*.json')}
        require(set(committed) == {'batch-000.json'}, 'Exactly one whole batch must precede interruption')
        committed_proofs[panel] = committed
        (two / 'batch-001.json.tmp').write_text('{malformed uncommitted engineering temporary file')
        second = runner(two, panel, smoke=True)
        require(all(digest(two / n) == sha for n, sha in committed.items()), 'Committed batch changed on resume')
        exact(first, second, 'Interrupted versus uninterrupted summary drift')
        proof = compare_execution(one, two, identities[panel])
        matches += proof['matches']; controllers.update(proof['controllers']); public.update(proof['publicChecks'])
        completed_resume(two, panel, second)
        exact(study.identity(panel, True, 6, study.ARTIFACT, study.REFERENCE_PYTHON), identities[panel],
              'Source/runtime/full-model/reference identity changed')
        for path in (one, two):
            manifests[path.name] = {p.name: digest(p) for p in sorted(path.iterdir())}
    require(len(loads) == 6 and matches == 198 and all(controllers[k] > 0 for k in rollout.CONTROLLERS),
            'All six cold model sets / ten controllers / 198 comparisons required')
    require(public['expertAtomicLegal'] == 0 and public['referenceAtomicLegal'] > 0, 'Reference/label scope violation')
    for loaded in loads:
        exact(model_state(loaded['models']), loaded['state'], 'Previously loaded model changed')
    require({name: digest(path) for name, path in paths.items()} == retained_hashes, 'Retained checkpoint bytes changed')
    exact(verify_old_source(identities), old_hashes, 'Frozen source changed during preflight')
    exact(verify_historical_ppo0(identities), historical_ppo0, 'Historical PPO0 provenance changed')
    for panel in PANELS:
        exact(study.identity(panel, True, 6, study.ARTIFACT, study.REFERENCE_PYTHON), identities[panel],
              'Final source/runtime/reference identity changed')
    study.artifact_budget(output)
    report = dict(schema='multimap-replica-stress-real-preflight-v1', allChecksPassed=True,
        smokeIdentities=identities, protocolSha256=digest(study.HERE / 'replica-stress-protocol-v1.json'),
        totalTerminalGames=396, exactTerminalAndCounterReplayMatches=198, failures=0,
        interruptedAfterBatches=1, completedBatchesPreserved=True, interruptedTemporaryBatchIgnored=True,
        completedResumePerformsNoCollection=True, committedBeforeInterruption=committed_proofs,
        bothPanels=True, allThreeFocalArms=True, allSixPinnedModels=True, modelLoads=6,
        allFourMaps=True, allFivePlayerCounts=True, allFourRules=True,
        modelTensorAndInferenceFlagsUnchanged=True, modelStateFingerprints=loads[0]['state'],
        metadataBeforeAllTransfers=True, explicitRetainedExpertCheckpoints=retained_hashes,
        controllersPerExecution=dict(controllers), publicChecksPerExecution=dict(public),
        legacyServingBaseGit=BASE_GIT, legacyServingGitHashesVerified=True, legacySourceFiles=old_hashes,
        historicalPpo0TrainingSource=historical_ppo0, historicalPpo0GitHashesVerified=True,
        reusedReferenceArtifact=True, reusedPythonEnvironments=True, onlySmokeRoots=True, productionGamesExecuted=0,
        manifests=manifests, seconds=time.monotonic()-began,
        fitting=False, selection=False, qualified=False, qualificationEligible=False, reservedFinalSeedsUsed=False,
        note='Real pinned policies/reference; repeated engineering smoke only, no independent strength observations. '
             'Only the four declared per-game timings may differ. No production jobs, training, selection or publication.')
    atomic_json(output / 'report.json', report)
    study.artifact_budget(output)
    print(json.dumps({k: report[k] for k in ('schema', 'totalTerminalGames', 'exactTerminalAndCounterReplayMatches',
                      'failures', 'modelLoads', 'seconds', 'qualified')}, indent=2), flush=True)
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    preflight(args.output)
