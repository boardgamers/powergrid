"""Fresh-root expert warmup + game-balanced PPO, with atomic stage transactions.

Only the current rollout lives in RAM. ``last.pt`` is the commit record, including
optimizer/RNG state and the *bytes* of the committed best checkpoint. Evaluation
never asks for labels, and confirmation starts only after checkpoint selection.
The module-level collect/config/warm_start functions are offline-test seams.
"""
import argparse
import copy
import hashlib
import json
import math
import os
from pathlib import Path
import random
import subprocess
import time

import torch

from data import ROOT, atomic_json, digest, generator_digest
from expert_policy import PROTOCOL, batch, load, save, warm_start
from expert_rollout import collect, plans, summary
from candidates import load_candidates
from neural_study import runtime_versions
from reference_recover import CACHE, DESCRIPTOR_SHA, MANIFEST_SHA, PINS, verify_artifact
from candidates import POOL as CANDIDATE_POOL

HERE = Path(__file__).resolve().parent
DEFAULT_ARTIFACT = CACHE / 'artifact'
DEFAULT_REFERENCE_PYTHON = ROOT / 'ai/.venv-reference/bin/python'
_FROZEN_PROTOCOL = json.loads((HERE / 'expert-protocol-v2.json').read_text())


def make_protocol():
    return copy.deepcopy(_FROZEN_PROTOCOL)


def artifact_budget(directory, additional=0):
    directory = Path(directory)
    if directory.is_symlink():
        raise ValueError('Artifact directory symlink forbidden')
    total = additional
    for path in directory.rglob('*'):
        if path.is_symlink():
            raise ValueError('Artifact symlinks forbidden')
        if path.is_file():
            total += path.stat().st_size
    if total > _FROZEN_PROTOCOL['studyArtifactMaxBytes']:
        raise ValueError('Expert artifact budget exceeded 128 MiB')
    return total


def engine_dependencies():
    """Hash installed serving JS, not host-specific paths or mutable documentation."""
    code = '''const {createRequire}=require('module');const path=require('path');
const req=createRequire(path.resolve('engine/dist/index.js'));
const seen={};function visit(name,from){const p=from.resolve(name+'/package.json');
const meta=require(p);if(seen[meta.name])return;seen[meta.name]=path.dirname(p);
const sub=createRequire(p);for(const child of Object.keys(meta.dependencies||{}))visit(child,sub);}
for(const name of Object.keys(require('./engine/package.json').dependencies))visit(name,req);
console.log(JSON.stringify(seen));'''
    roots = json.loads(subprocess.check_output(['node', '-e', code], cwd=ROOT, text=True, timeout=30))
    answer = {}
    for name, directory in sorted(roots.items()):
        directory = Path(directory)
        files = {p.relative_to(directory).as_posix(): digest(p)
                 for p in sorted(directory.rglob('*')) if p.is_file()
                 and p.suffix in ('.js', '.cjs', '.mjs', '.json')
                 and not {'test', 'tests', 'coverage', 'node_modules'} & set(p.relative_to(directory).parts)}
        if 'package.json' not in files:
            raise ValueError('Missing engine serving dependency identity')
        # A small digest per dependency, rather than thousands of lodash filenames.
        answer[name] = dict(files=len(files), sha256=hashlib.sha256(
            json.dumps(files, sort_keys=True, separators=(',', ':')).encode()).hexdigest())
    return answer


def config(smoke=False, protocol=PROTOCOL, *, artifact=DEFAULT_ARTIFACT,
           reference_python=DEFAULT_REFERENCE_PYTHON, workers=None):
    """Fail closed on all serving code, compiled engine, pins, and runtime drift.

    Auditors, docs, launch receipts, and other nonserving files intentionally do
    not affect this identity. Reference's COMPLETE manifest is verified, but no
    archived fixture/training root is consumed by optimization.
    """
    if protocol != _FROZEN_PROTOCOL or json.loads((HERE / 'expert-protocol-v2.json').read_text()) != protocol:
        raise ValueError('Frozen expert protocol changed')
    if (digest(HERE / 'candidate-pool-v1.json') != protocol['candidatePoolSha256'] or
        json.loads((HERE / 'candidate-pool-v1.json').read_text())['members'] != protocol['opponentPool'] or
        PINS['source'] != protocol['reference']['sourcePin'] or PINS['model'] != protocol['reference']['modelPin'] or
        MANIFEST_SHA != protocol['reference']['runtimeManifestSha256'] or DESCRIPTOR_SHA != protocol['reference']['policySha256']):
        raise ValueError('Frozen opponent/reference pins differ from serving helpers')
    workers = (2 if smoke else protocol['workers']) if workers is None else workers
    if type(workers) is not int or not 1 <= workers <= protocol['workers']:
        raise ValueError('Expert workers must be 1..6')
    if digest(ROOT / 'ai/requirements-serve.txt') != protocol['referenceRequirementsSha256']:
        raise ValueError('Reference environment requirements changed')
    if json.loads((ROOT / 'engine/package.json').read_text())['version'] != '2.0.22':
        raise ValueError('Authoritative engine release changed')
    engine = sorted((ROOT / 'engine/dist').rglob('*.js'))
    if len(engine) != 42:
        raise ValueError('Expected all 42 compiled authoritative engine modules')
    names = ('expert-protocol-v2.json', 'expert_policy.py', 'expert_rollout.py', 'expert_game.cjs',
             'expert_ppo.py', 'job_expert.py', 'job_gap.py', 'job_neural.py', 'job.py', 'gap_study.py', 'gap-protocol-v1.json', 'teacher_v2.cjs', 'economics_v2.cjs', 'teacher-repairs-v2.json',
             'features.cjs', 'teacher.cjs', 'game.cjs', 'game_rl.cjs', 'model.py', 'residual.py',
             'candidates.py', 'candidate-pool-v1.json', 'ppo-protocol-v1.json', 'data.py', 'protocol.json',
             'reference_evaluate.py', 'reference_recover.py', 'reference_game.cjs',
             'neural_study.py', 'neural-study-v1.json', 'requirements-cpu.txt')
    paths = [HERE / name for name in names]
    paths += [ROOT / name for name in ('ai/core.cjs', 'ai/strong/economics.cjs',
                                      'ai/requirements-serve.txt', 'engine/package.json', 'engine/pnpm-lock.yaml')]
    paths += engine
    checked = verify_artifact(Path(artifact))
    manifest = json.loads((Path(artifact) / 'manifest.json').read_text())
    # The exact manifest pin covers the entire frozen reference, including its
    # engine/dependencies. These explicit code hashes make the serving audit easy.
    reference_sources = {name: sha for name, sha in manifest.items()
                         if Path(name).suffix in ('.py', '.js', '.cjs', '.mjs')}
    return dict(schema='multimap-expert-training-identity-v2', protocol=copy.deepcopy(protocol), smoke=smoke,
                generatorDigest=generator_digest(), sourceFiles={p.relative_to(ROOT).as_posix(): digest(p) for p in paths},
                engineDependencies=engine_dependencies(), referenceSourceFiles=reference_sources,
                referenceManifestSha256=digest(Path(artifact) / 'manifest.json'), referenceFiles=checked['present'],
                runtimeVersions=runtime_versions(reference_python),
                execution=dict(workers=workers, collector='thread-pool-lockstep-central-torch-with-child-processes', inferenceThreads=protocol['inferenceThreads'],
                               optimizerThreads=protocol['optimizerThreads'], deterministicAlgorithms=True),
                sourcePins=dict(warmStart=protocol['warmStart'], opponents=protocol['opponentPool'], reference=protocol['reference']))


def objective_weights(rows):
    """Global mean-one weights; NEVER renormalize a minibatch's label subset.

    Rollout assigns 1/n_game to PPO rows and 1/(available_phases*n_phase)
    to expert rows. Therefore sum(expertWeight) equals the number of expert
    games, irrespective of how many labels or phases each game produced.
    """
    if not rows:
        raise ValueError('Empty optimization window')
    game = torch.tensor([r['weight'] for r in rows], dtype=torch.float32)
    expert = torch.tensor([r.get('expertWeight', 0.) for r in rows], dtype=torch.float32)
    labels = torch.tensor([r.get('expertIndex', -1) for r in rows], dtype=torch.long)
    if not torch.isfinite(game).all() or not (game > 0).all():
        raise ValueError('Invalid per-game PPO weights')
    if not torch.isfinite(expert).all() or (expert < 0).any():
        raise ValueError('Invalid expert weights')
    for row, label, weight in zip(rows, labels.tolist(), expert.tolist()):
        if (label < -1 or label >= len(row['prior']) or
                (label == -1 and weight != 0) or (label >= 0 and weight <= 0) or
                (label >= 0 and row.get('phase') not in ('Auction', 'Building'))):
            raise ValueError('Illegal expert label/phase/weight')
    return game / game.mean(), (expert / expert.mean() if float(expert.sum()) else expert)


def expert_loss(logps, selected, weights):
    labels = torch.tensor([r.get('expertIndex', -1) for r in selected], dtype=torch.long)
    valid = labels >= 0
    # Safe gather plus a zero coefficient keeps a differentiable exact zero in
    # entirely unlabelled batches, with finite gradients and no empty mean.
    losses = -logps.gather(1, labels.clamp_min(0)[:, None]).squeeze(1)
    return (losses * weights * valid).mean()


def _step(model, optimizer, loss, protocol):
    if not torch.isfinite(loss):
        raise FloatingPointError('Nonfinite expert/PPO objective')
    optimizer.zero_grad(set_to_none=True)
    loss.backward()
    norm = torch.nn.utils.clip_grad_norm_(model.parameters(), protocol['maxGradNorm'], error_if_nonfinite=True)
    optimizer.step()
    return float(norm)


def _metrics(rows, stats, **extra):
    if not stats:
        raise RuntimeError('Optimization made no steps')
    return dict(rows=len(rows), expertRows=sum(r.get('expertIndex', -1) >= 0 for r in rows),
                optimizerSteps=len(stats), **extra,
                **{key: sum(s[key] for s in stats) / len(stats) for key in stats[0]})


def warmup_optimize(model, optimizer, rows, protocol=PROTOCOL, *, epochs=None):
    torch.set_num_threads(protocol['optimizerThreads'])
    model.train()
    weights, expert_weights = objective_weights(rows)
    if not bool((expert_weights > 0).any()):
        raise ValueError('Warmup needs expert games')
    returns = torch.tensor([r['return'] for r in rows], dtype=torch.float32)
    generator = torch.Generator().manual_seed(protocol['seed'] + 313)
    stats = []
    for _ in range(protocol['warmupEpochs'] if epochs is None else epochs):
        for indices in torch.randperm(len(rows), generator=generator).split(protocol['batchSize']):
            selected = [rows[int(i)] for i in indices]
            logits, values = model(batch(selected))
            ce = expert_loss(logits.log_softmax(-1), selected, expert_weights[indices])
            value = (weights[indices] * (values - returns[indices]).square()).mean()
            loss = ce + protocol['warmupValueCoefficient'] * value
            norm = _step(model, optimizer, loss, protocol)
            stats.append(dict(loss=float(loss.detach()), expertCE=float(ce.detach()),
                              value=float(value.detach()), gradNorm=norm))
    return _metrics(rows, stats, epochs=protocol['warmupEpochs'] if epochs is None else epochs)


def optimize(model, optimizer, rows, update, protocol=PROTOCOL):
    torch.set_num_threads(protocol['optimizerThreads'])
    model.train()
    weights, expert_weights = objective_weights(rows)
    returns = torch.tensor([r['return'] for r in rows], dtype=torch.float32)
    advantages = returns - torch.tensor([r['oldValue'] for r in rows], dtype=torch.float32)
    center = (weights * advantages).mean()
    scale = (weights * (advantages - center).square()).mean().sqrt().clamp_min(1e-6)
    advantages = (advantages - center) / scale
    coefficient = protocol['expertCoefficient'] * protocol['expertDecay'] ** (update - 1)
    generator = torch.Generator().manual_seed(protocol['seed'] + update * 1009)
    stats, stopped = [], False
    for _ in range(protocol['epochsPerUpdate']):
        for indices in torch.randperm(len(rows), generator=generator).split(protocol['batchSize']):
            selected = [rows[int(i)] for i in indices]
            logits, values = model(batch(selected))
            logps = logits.log_softmax(-1)
            probability = logps.exp()
            action = torch.tensor([r['chosen'] for r in selected], dtype=torch.long)
            chosen = logps.gather(1, action[:, None]).squeeze(1)
            old = torch.tensor([r['oldLog'] for r in selected], dtype=torch.float32)
            delta = chosen - old
            ratio = delta.exp()
            w, adv = weights[indices], advantages[indices]
            kl = (w * ((ratio - 1) - delta)).mean()
            if not torch.isfinite(kl):
                raise FloatingPointError('Nonfinite PPO KL')
            if float(kl.detach()) > protocol['targetKl']:
                stopped = True
                break
            actor = -(w * torch.minimum(ratio * adv, ratio.clamp(1 - protocol['clip'], 1 + protocol['clip']) * adv)).mean()
            value = (w * (values - returns[indices]).square()).mean()
            entropy = -(w * (probability * logps).sum(-1)).mean()
            ce = expert_loss(logps, selected, expert_weights[indices])
            # Deliberately no heuristic-prior KL: disagreement with the old prior
            # is precisely the expert supervision this recipe must learn.
            loss = actor + protocol['valueCoefficient'] * value - protocol['entropyCoefficient'] * entropy + coefficient * ce
            norm = _step(model, optimizer, loss, protocol)
            stats.append(dict(loss=float(loss.detach()), actor=float(actor.detach()), value=float(value.detach()),
                              entropy=float(entropy.detach()), expertCE=float(ce.detach()),
                              approxKl=float(kl.detach()), gradNorm=norm))
        if stopped:
            break
    return _metrics(rows, stats, earlyStopped=stopped, expertCoefficient=coefficient)


def eligible(candidate, baseline, protocol=PROTOCOL):
    if candidate.get('failures') != 0 or set(candidate.get('maps', {})) != set(baseline['maps']):
        return False
    for name, credit in baseline['maps'].items():
        limit = 0 if name == 'Germany' and protocol['selectionGermanyNonregression'] else protocol['selectionMaxMapRegression']
        value = candidate['maps'][name]
        if not math.isfinite(value) or value < credit - limit - 1e-12:
            return False
    return math.isfinite(candidate['macroCredit'])


def assert_initial_parity(initial, teacher):
    """Compare every terminal field, not just focal win credit or macro means."""
    key = lambda r: (r['spec']['seed'], r['spec']['focalSeat'])
    reference = {key(r): r for r in teacher}
    if len(reference) != len(teacher) or len(initial) != len(teacher) or len({key(r) for r in initial}) != len(initial):
        raise RuntimeError('Initial teacher parity task mismatch')
    # Actor routing/request counts and timings necessarily differ; terminal game fields do not.
    for row in initial:
        other = reference.get(key(row))
        if other is None or not row.get('terminal') or not other.get('terminal'):
            raise RuntimeError('Initial teacher parity missing terminal game')
        for required in ('terminal', 'credit', 'steps', 'rounds', 'allSeatCredit'):
            if required not in row or required not in other:
                raise RuntimeError('Initial teacher parity missing terminal fields')
        left = {k: row[k] for k in ('terminal', 'credit', 'steps', 'rounds', 'allSeatCredit')}
        right = {k: other[k] for k in left}
        if left != right:
            raise RuntimeError('Initial teacher full terminal parity failed')
        specs = [{k: v for k, v in r['spec'].items() if k != 'focalTeacher'} for r in (row, other)]
        if specs[0] != specs[1]:
            raise RuntimeError('Initial teacher parity spec mismatch')


def _restore_best(output, saved):
    content = saved['bestArtifact']
    if not isinstance(content, bytes) or hashlib.sha256(content).hexdigest() != saved['bestSha256']:
        raise ValueError('Committed best checkpoint bytes/hash mismatch')
    path = output / 'best.pt'
    if not path.exists() or digest(path) != saved['bestSha256']:
        temp = output / 'best.pt.tmp'
        temp.write_bytes(content)
        temp.replace(path)


def run(checkpoint, output, smoke=False, stop_after=None, callback=None, *,
        artifact=DEFAULT_ARTIFACT, reference_python=DEFAULT_REFERENCE_PYTHON):
    if type(smoke) is not bool or (stop_after is not None and (type(stop_after) is not int or stop_after < 0)):
        raise ValueError('Invalid smoke/stop_after')
    protocol = make_protocol()
    workers = int(os.environ.get('EXPERT_WORKERS', 2 if smoke else protocol['workers']))
    if not 1 <= workers <= protocol['workers']:
        raise ValueError('EXPERT_WORKERS must be 1..6')
    updates = 2 if smoke else protocol['updates']
    every = 1 if smoke else protocol['selectionEvery']
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    artifact_budget(output)
    identity = config(smoke, protocol, artifact=artifact, reference_python=reference_python, workers=workers)
    identity_path = output / 'config.json'
    if identity_path.exists() and json.loads(identity_path.read_text()) != identity:
        raise RuntimeError('Existing run config/source/runtime mismatch')
    if (output / 'last.pt').exists() and not identity_path.exists():
        raise RuntimeError('Commit without immutable config')
    atomic_json(identity_path, identity)
    population = load_candidates(['ppo0', 'ppo1', 'ppo2'])
    torch.set_num_threads(protocol['optimizerThreads'])
    torch.use_deterministic_algorithms(True)
    random.seed(protocol['seed'])
    torch.manual_seed(protocol['seed'])
    selection_plan = plans('selection', smoke=smoke, protocol=protocol)
    atomic_json(output / 'selection-plan.json', selection_plan)
    history, confirmations, result = [], {}, None
    best_update, best_stage, update, stage = 0, 'initial', 0, 'initial'

    def optimizer_for(model, warm=False):
        return torch.optim.AdamW(model.parameters(), lr=protocol['warmupLearningRate' if warm else 'learningRate'],
                                 weight_decay=protocol['weightDecay'])

    def gather(model, tasks, *, mode='evaluation', seed=None):
        rows, outcomes = collect(model, tasks, workers, training=mode != 'evaluation',
            seed=protocol['seed'] if seed is None else seed, mode=mode, artifact=artifact,
            reference_python=reference_python, opponents=population, protocol=protocol)
        if len(outcomes) != len(tasks) or any(r.get('terminal') is not True for r in outcomes):
            raise RuntimeError('Incomplete/nonterminal collection; no synthetic rewards or game retries')
        if mode == 'evaluation' and rows:
            raise ValueError('Evaluation must not return expert/training rows')
        if len(rows) > protocol['maxRolloutRows']:
            raise MemoryError('Rollout RAM row budget exceeded')
        return rows, outcomes

    def commit(label):
        artifact_budget(output)
        best_bytes = (output / 'best.pt').read_bytes()
        save(output / 'last.pt', model, stage=stage, update=update, optimizer=optimizer.state_dict(),
             torchRng=torch.get_rng_state(), pythonRng=random.getstate(), config=identity,
             history=history, bestUpdate=best_update, bestStage=best_stage, bestScore=best_score,
             baseline=baseline, bestArtifact=best_bytes, bestSha256=hashlib.sha256(best_bytes).hexdigest(),
             confirmations=confirmations, result=result)
        atomic_json(output / 'history.json', history)
        artifact_budget(output)
        if callback:
            callback(label)

    def selection(model, label, candidate_update, candidate_stage):
        nonlocal best_score, best_update, best_stage
        _, games = gather(model, selection_plan)
        selected = summary(games)
        atomic_json(output / f'selection-{label}.json', dict(summary=selected, games=games))
        if eligible(selected, baseline, protocol) and selected['macroCredit'] > best_score + 1e-12:
            best_score, best_update, best_stage = selected['macroCredit'], candidate_update, candidate_stage
            save(output / 'best.pt', model, stage=best_stage, update=best_update, config=identity)
        return selected

    if (output / 'last.pt').exists():
        model, saved = load(output / 'last.pt')
        if saved['config'] != identity:
            raise RuntimeError('Checkpoint config/source/runtime mismatch')
        stage, update = saved['stage'], saved['update']
        if stage not in ('initial', 'warmup', 'train') or not 0 <= update <= updates or (stage != 'train' and update != 0):
            raise ValueError('Invalid committed training stage')
        _restore_best(output, saved)
        optimizer = optimizer_for(model, warm=stage in ('initial', 'warmup'))
        optimizer.load_state_dict(saved['optimizer'])
        torch.set_rng_state(saved['torchRng'])
        random.setstate(saved['pythonRng'])
        history, baseline = saved['history'], saved['baseline']
        best_score, best_update, best_stage = saved['bestScore'], saved['bestUpdate'], saved['bestStage']
        confirmations, result = saved.get('confirmations', {}), saved.get('result')
        atomic_json(output / 'history.json', history)
        for label, record in confirmations.items():
            path = output / f'confirmation-{label}.json'
            if not path.is_file() or digest(path) != record['sha256']:
                raise ValueError('Committed confirmation hash mismatch')
        if result is not None:
            atomic_json(output / 'result.json', result)
            return result
    else:
        model = warm_start(checkpoint)
        optimizer = optimizer_for(model, warm=True)
        _, initial = gather(model, selection_plan)
        _, teacher = gather(model, [dict(s, focalTeacher=True) for s in selection_plan])
        assert_initial_parity(initial, teacher)
        baseline = summary(initial)
        if baseline['failures']:
            raise RuntimeError('Initial selection has failures')
        best_score = baseline['macroCredit']
        atomic_json(output / 'selection-0.json', dict(summary=baseline, games=initial))
        atomic_json(output / 'selection-teacher.json', dict(summary=summary(teacher), games=teacher))
        save(output / 'initial.pt', model, stage='initial', update=0, config=identity)
        save(output / 'best.pt', model, stage='initial', update=0, config=identity)
        commit('initial')

    if stage == 'initial':
        warmup_plan = plans('warmup', smoke=smoke, protocol=protocol)
        atomic_json(output / 'warmup-plan.json', warmup_plan)
        rows, outcomes = gather(model, warmup_plan, mode='warmup', seed=protocol['seed'] + 313)
        metrics = warmup_optimize(model, optimizer, rows, protocol, epochs=2 if smoke else protocol['warmupEpochs'])
        del rows
        atomic_json(output / 'warmup.json', dict(games=outcomes, optimization=metrics))
        selected = selection(model, 'warmup', 0, 'warmup')
        history.append(dict(stage='warmup', update=0, training=summary(outcomes), optimization=metrics, selection=selected))
        save(output / 'warmup.pt', model, stage='warmup', update=0, config=identity)
        stage = 'warmup'
        commit('warmup')
    if stage == 'warmup':
        # Warmup Adam moments do NOT contaminate the fixed PPO optimizer.
        optimizer = optimizer_for(model)
    for current in range(update + 1, updates + 1):
        if stop_after is not None and current > stop_after:
            return None
        began = time.monotonic()
        train_plan = plans('train', current, smoke=smoke, protocol=protocol)
        atomic_json(output / f'train-plan-{current}.json', train_plan)
        rows, outcomes = gather(model, train_plan, mode='train', seed=protocol['seed'] + current * 7919)
        metrics = optimize(model, optimizer, rows, current, protocol)
        del rows
        record = dict(stage='train', update=current, training=summary(outcomes), optimization=metrics)
        atomic_json(output / f'train-{current}.json', dict(games=outcomes))
        if current % every == 0 or current == updates:
            record['selection'] = selection(model, str(current), current, 'train')
        history.append(record)
        stage, update = 'train', current
        commit(f'update-{current}')
        print(json.dumps(dict(stage='expert-ppo', update=current, bestStage=best_stage, bestUpdate=best_update,
                              trainCredit=record['training']['macroCredit'], rows=metrics['rows'],
                              seconds=time.monotonic() - began)), flush=True)
    if stop_after is not None:
        return None

    # No holdout/transfer collection happens until every optimization and the
    # last scheduled selection are committed. Paired teacher-v2 is a control,
    # never a way to choose between candidate checkpoints on confirmation.
    selected_model, _ = load(output / 'best.pt')
    confirmation_plan = plans('confirmation', smoke=smoke, protocol=protocol)
    atomic_json(output / 'confirmation-plan.json', confirmation_plan)
    for label, teacher in (('selected', False), ('teacher', True)):
        if label in confirmations:
            continue
        tasks = [dict(s, focalTeacher=True) for s in confirmation_plan] if teacher else confirmation_plan
        _, outcomes = gather(selected_model, tasks)
        scores = summary(outcomes)
        path = output / f'confirmation-{label}.json'
        atomic_json(path, dict(summary=scores, games=outcomes))
        confirmations[label] = dict(summary=scores, sha256=digest(path))
        commit(f'confirmation-{label}')
    result = dict(selectedUpdate=best_update, selectedStage=best_stage, selectionScore=best_score,
                  baselineSelectionScore=baseline['macroCredit'], confirmation={k: v['summary'] for k, v in confirmations.items()},
                  trainedUpdates=updates, warmupEpochs=2 if smoke else protocol['warmupEpochs'], smoke=smoke,
                  qualified=False, qualificationEligible=False, reservedFinalSeedsUsed=False,
                  note='Fresh-root expert/PPO experiment. Teacher-v2 baseline is an eligible fallback; confirmation never selects.')
    atomic_json(output / 'result.json', result)
    commit('complete')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--checkpoint', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--artifact', default=DEFAULT_ARTIFACT)
    parser.add_argument('--reference-python', default=DEFAULT_REFERENCE_PYTHON)
    parser.add_argument('--smoke', action='store_true')
    parser.add_argument('--stop-after', type=int)
    args = parser.parse_args()
    print(json.dumps(run(args.checkpoint, args.output, args.smoke, args.stop_after,
                         artifact=args.artifact, reference_python=args.reference_python), indent=2))
