"""Bounded full-game harness for the exact Germany public FILTER service.

No tournament/qualification. Authoritative game state lives only in Node.
The old service runs in its own Python environment and module namespace. A
runtime-only subset cannot satisfy its immutable load_artifact; complete recovery
uses bounded RAM for compressed source and preserves that loader and identity.

Reusable API: plans(), ReferenceProcess.decide(), evaluate(..., model=... or
checkpoint=...). Supplied models (including equal-logit ensembles) implement the
same batch -> (logits, value) interface as ResidualPolicy. They are never trained.
Focal modes: selected (PPO Auction/Building + geographic fixed phases), teacher
(geographic all phases), reference (the unchanged old service all phases).
"""
import argparse
import json
import os
from pathlib import Path
import queue
import signal
import subprocess
import sys
import threading
import time

from reference_recover import CACHE, ROOT, PINS, MANIFEST_SHA, DESCRIPTOR_SHA, budget, digest, verify_artifact

NAMESPACE = 'pg-multimap-reference-preflight-v1'
MAX_GAMES = 20


def plans(games=20, focal_policy='selected'):
    if type(games) is not int or not 1 <= games <= MAX_GAMES:
        raise ValueError('Preflight permits 1..20 games, not a tournament')
    if focal_policy not in ('selected', 'teacher', 'reference'):
        raise ValueError('Unknown focal policy')
    tasks = []
    for players in range(2, 7):
        for variant in ('original', 'recharged'):
            for fast in (False, True):
                cell = f'Germany|{players}|{variant}|{int(fast)}'
                tasks.append(dict(map='Germany', players=players, variant=variant, fastBid=fast,
                    cell=cell, seed=f'{NAMESPACE}:smoke:{cell}:0', focalSeat=len(tasks) % players,
                    focalPolicy=focal_policy, maxSteps=4000))
    return tasks[:games]


class LineProcess:
    """Persistent insertion-order JSON transport; bounded responses and timeouts."""
    def __init__(self, argv, *, cwd=ROOT, env=None, timeout=60):
        self.timeout = timeout
        self.process = subprocess.Popen([str(x) for x in argv], cwd=cwd, env=env,
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, bufsize=1,
            start_new_session=True)
        self.answers = queue.Queue(maxsize=2)
        self.reader = threading.Thread(target=self._read, daemon=True)
        self.reader.start()

    def _read(self):
        try:
            while True:
                line = self.process.stdout.readline(16 * 1024**2)
                if not line or not line.endswith('\n'):
                    self.answers.put(RuntimeError('Worker EOF or oversized/unterminated response'))
                    return
                self.answers.put(line)
        except (ValueError, OSError) as error:
            try:
                self.answers.put_nowait(error)
            except queue.Full:
                pass

    def call(self, request):
        # NEVER sort transport keys. The old policy's object iteration is semantic.
        self.process.stdin.write(json.dumps(request, separators=(',', ':'), allow_nan=False) + '\n')
        self.process.stdin.flush()
        try:
            line = self.answers.get(timeout=self.timeout)
        except queue.Empty:
            self.close()
            raise TimeoutError('Reference worker response deadline exceeded') from None
        if isinstance(line, BaseException):
            raise line
        answer = json.loads(line)
        if not isinstance(answer, dict):
            raise ValueError('Worker response is not an object')
        if 'error' in answer:
            raise RuntimeError(answer['error'])
        return answer

    def close(self):
        if self.process.poll() is None:
            try:
                os.killpg(self.process.pid, signal.SIGTERM)
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(self.process.pid, signal.SIGKILL)
                self.process.wait(timeout=5)
        if self.process.stdin:
            self.process.stdin.close()
        self.reader.join(timeout=2)
        if self.process.stdout:
            self.process.stdout.close()


class ReferenceProcess(LineProcess):
    def __init__(self, artifact, python=ROOT / 'ai/.venv-reference/bin/python', *, verify=True):
        artifact = Path(artifact).resolve()
        # verify=False is only for the explicit canonical-loader blocker probe.
        # evaluate() never disables this check.
        verify_artifact(artifact, require_complete=verify)
        env = dict(os.environ)
        for name in ('PYTHONPATH', 'PYTHONHOME', 'NODE_OPTIONS', 'NODE_PATH', 'PG_REFERENCE_RUNTIME'):
            env.pop(name, None)
        env['PYTHONDONTWRITEBYTECODE'] = '1'
        super().__init__([python, '-u', '-B', artifact / 'ai/strong/public_policy_runtime_v1.py',
                          artifact], cwd=artifact, env=env)

    def decide(self, request):
        if set(request) != {'requestId', 'revision', 'player', 'state'}:
            raise ValueError('Only public decision API requests may cross to reference')
        state = request['state']
        if (state.get('seed') != 'secret' or state.get('powerPlantsDeck') != [] or
            state.get('hiddenLog') != [] or 'powerPlantDeckAfterStep3' in state or 'automation' in state):
            raise ValueError('Unredacted public request')
        if state.get('options', {}).get('fastBid') and (
                state.get('currentBid') != 0 or any(p.get('bid') != 0 for p in state['players'])):
            raise ValueError('Submitted sealed bids must be hidden')
        response = self.call(request)
        expected = dict(policySha256=DESCRIPTOR_SHA, runtimeManifestSha256=MANIFEST_SHA,
            modelSha256=PINS['model']['sha256'], featureRevision='4.3-strategic-correction',
            backend='population-v1', settings=dict(arm='filter', max_steps=2400, samples=8, threads=1, workers=4))
        for key, value in expected.items():
            if response.get(key) != value:
                raise ValueError('Reference identity mismatch: ' + key)
        if any(response.get(k) != request[k] for k in ('requestId', 'revision')) or 'move' not in response:
            raise ValueError('Unbound reference response')
        return response


def evaluate(tasks, *, artifact=CACHE / 'artifact', reference_python=ROOT / 'ai/.venv-reference/bin/python',
             model=None, checkpoint=None, model_label=None):
    """One selected focal vs reference opponents; max 20 games, fail whole batch.

    A supplied checkpoint is explicitly identified by its bytes, not silently
    substituted for PPO0. A supplied model requires a caller-provided label with
    its constituent immutable checkpoint hashes (e.g. an ensemble descriptor).
    """
    tasks = list(tasks)
    if not 1 <= len(tasks) <= MAX_GAMES:
        raise ValueError('Bounded preflight requires 1..20 games')
    if model is not None and checkpoint is not None:
        raise ValueError('Supply a model OR checkpoint, not both')
    if model is not None and not model_label:
        raise ValueError('Supplied model needs an explicit provenance label')
    for spec in tasks:
        if (not spec.get('seed', '').startswith(NAMESPACE + ':') or spec.get('map') != 'Germany' or
            spec.get('focalPolicy', 'selected') not in ('selected', 'teacher', 'reference')):
            raise ValueError('Unsupported preflight task or reserved seed namespace')
    # Preserve the exact immutable public loader. Do not weaken the descriptor to
    # work around unused training/fixture entries in its manifest.
    verify_artifact(Path(artifact))
    budget(CACHE)
    needs_model = any(s.get('focalPolicy', 'selected') == 'selected' for s in tasks)
    if needs_model:
        import torch
        from residual import load, row, batch
        torch.set_num_threads(1)
        if model is None:
            selected = Path(checkpoint) if checkpoint is not None else CACHE / 'ppo.pt'
            sha = digest(selected)
            if checkpoint is None and sha != PINS['ppo']['sha256']:
                raise ValueError('Wrong selected PPO0 checkpoint')
            model, _ = load(selected)
            model_label = model_label or dict(checkpointSha256=sha, selectedPPO0=sha == PINS['ppo']['sha256'])
        model.eval()
    reference = bridge = None
    outcomes = []
    try:
        reference = ReferenceProcess(artifact, reference_python)
        bridge = LineProcess(['node', ROOT / 'ai/multimap/reference_game.cjs'])
        for spec in tasks:
            started = time.monotonic()
            state = bridge.call(dict(op='start', spec=spec))
            repeated_phases = set()
            while not state['terminal']:
                if state['kind'] == 'reference':
                    response = reference.decide(state['request'])
                    # Each phase gets an actual deterministic service repeat. The
                    # bridge already compared hidden-poisoned public bytes.
                    if state['phase'] not in repeated_phases:
                        repeated = reference.decide(state['request'])
                        if repeated['move'] != response['move']:
                            raise ValueError('Repeated public reference decision changed')
                        repeated_phases.add(state['phase'])
                    state = bridge.call(dict(op='step', response=response))
                elif state['kind'] == 'ppo':
                    with torch.inference_mode():
                        logits, _ = model(batch([row(state['observation'])]))
                    index = int(logits[0].argmax())
                    state = bridge.call(dict(op='step', index=index))
                else:
                    raise ValueError('Unknown comparison actor')
            outcomes.append(dict(spec=spec, **state, seconds=time.monotonic() - started,
                                 repeatedReferencePhases=sorted(repeated_phases)))
    finally:
        if bridge:
            bridge.close()
        if reference:
            reference.close()
    return dict(games=len(outcomes), outcomes=outcomes, model=model_label,
                referencePolicySha256=DESCRIPTOR_SHA, runtimeManifestSha256=MANIFEST_SHA,
                qualification_eligible=False, reserved_final_seeds_used=False)


def probe_loader(artifact=CACHE / 'artifact', reference_python=ROOT / 'ai/.venv-reference/bin/python'):
    """One initial decision request, no game moves, unmodified archived loader."""
    bridge = reference = None
    try:
        bridge = LineProcess(['node', ROOT / 'ai/multimap/reference_game.cjs'])
        spec = plans(1, 'reference')[0]
        state = bridge.call(dict(op='start', spec=spec))
        reference = ReferenceProcess(artifact, reference_python, verify=False)
        reference.decide(state['request'])
        return dict(exactLoaderPassed=True, games=0)
    except Exception as error:
        return dict(exactLoaderPassed=False, error=str(error), games=0, neuralDecisions=0,
                    qualification_eligible=False, reserved_final_seeds_used=False)
    finally:
        if reference:
            reference.close()
        if bridge:
            bridge.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--games', type=int, default=20)
    parser.add_argument('--focal-policy', choices=('selected', 'teacher', 'reference'), default='selected')
    parser.add_argument('--checkpoint', type=Path)
    parser.add_argument('--artifact', type=Path, default=CACHE / 'artifact')
    parser.add_argument('--reference-python', type=Path, default=ROOT / 'ai/.venv-reference/bin/python')
    parser.add_argument('--probe-loader', action='store_true')
    args = parser.parse_args()
    try:
        result = probe_loader(args.artifact, args.reference_python) if args.probe_loader else evaluate(
            plans(args.games, args.focal_policy), artifact=args.artifact, reference_python=args.reference_python,
            checkpoint=args.checkpoint)
    except Exception as error:
        result = dict(blocked=True, error=str(error), games=0, qualification_eligible=False, reserved_final_seeds_used=False)
    print(json.dumps(result, indent=2))
    if result.get('blocked') or result.get('exactLoaderPassed') is False:
        sys.exit(2)
