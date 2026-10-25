"""Shared public-request transport for pinned research policies.

Uses the same choose() implementation as the arena. This is an execution
contract, not candidate selection, strength qualification or deployment.
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import sys
import time


def encode(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def checked_path(root, name):
    if not isinstance(name, str) or not name or Path(name).is_absolute() or '..' in Path(name).parts:
        raise ValueError('Artifact path must stay inside its directory')
    path = (root/name).resolve()
    if not path.is_relative_to(root) or not path.is_file():
        raise ValueError('Missing artifact file or escaped artifact path')
    return path


def sha256(value):
    if not isinstance(value, str) or not re.fullmatch('[0-9a-f]{64}', value):
        raise ValueError('Expected a SHA256 digest')
    return value


class PopulationInstance:
    def __init__(self, policy, identity):
        self.policy, self.identity = policy, identity

    def prepare(self, request):
        return self.policy.node.call({'op': 'prepare', 'state': request['state'],
            'player': request['player'], 'featureRevision': self.identity['featureRevision']})

    def choose(self, request):
        return self.policy.choose(request)

    def close(self):
        self.policy.close()


def load_artifact(directory, descriptor='policy.json'):
    root = Path(directory).resolve()
    path = checked_path(root, descriptor)
    spec = json.loads(path.read_text())
    if set(spec) != {'version', 'backend', 'feature_revision', 'model', 'runtime_manifest', 'settings'}:
        raise ValueError('Unknown or missing policy descriptor fields')
    if type(spec['version']) is not int or spec['version'] != 1 or spec['backend'] != 'population-v1' or spec['feature_revision'] != '4.3-strategic-correction':
        raise ValueError('Unsupported public-policy contract')
    for key in ('model', 'runtime_manifest'):
        if set(spec[key]) != {'path', 'sha256'}:
            raise ValueError('Invalid artifact pin')
        target = checked_path(root, spec[key]['path'])
        if digest(target) != sha256(spec[key]['sha256']):
            raise ValueError('Artifact pin mismatch: '+key)
    manifest = json.loads(checked_path(root, spec['runtime_manifest']['path']).read_text())
    if not isinstance(manifest, dict) or not manifest:
        raise ValueError('Missing runtime manifest')
    for name, expected in manifest.items():
        if digest(checked_path(root, name)) != sha256(expected):
            raise ValueError('Runtime hash mismatch: '+name)
    entry = 'ai/strong/public_policy_runtime_v1.py'
    if checked_path(root, entry) != Path(__file__).resolve() or manifest.get(entry) != digest(__file__):
        raise ValueError('Transport must execute from its verified standalone artifact')
    if manifest.get(spec['model']['path']) != spec['model']['sha256']:
        raise ValueError('Model missing from runtime manifest')
    settings = spec['settings']
    if set(settings) != {'arm', 'samples', 'workers', 'threads', 'max_steps'}:
        raise ValueError('Unknown or missing execution settings')
    if settings['arm'] not in ('model', 'filter', 'auction', 'building', 'combined'):
        raise ValueError('Unsupported population policy arm')
    bounds = {'samples': range(4, 65, 4), 'workers': range(1, 33),
              'threads': range(1, 9), 'max_steps': range(1, 2401)}
    if any(type(settings[k]) is not int or settings[k] not in values for k, values in bounds.items()):
        raise ValueError('Invalid frozen execution setting')
    if os.environ.get('NODE_OPTIONS'):
        raise ValueError('NODE_OPTIONS would alter the frozen engine runtime')
    sys.path.insert(0, str(root/'ai/strong'))
    from hybrid_search import Model
    from population_hybrid_policy import PopulationPolicy
    import hybrid_search, population_hybrid_policy, infer, pool, feature_contract
    for module in (hybrid_search, population_hybrid_policy, infer, pool, feature_contract):
        origin = Path(module.__file__).resolve()
        if not origin.is_relative_to(root) or manifest.get(str(origin.relative_to(root))) != digest(origin):
            raise ValueError('Imported policy module differs from its frozen artifact')
    model = Model(checked_path(root, spec['model']['path']), threads=settings['threads'])
    if feature_contract.model_revision(model) != spec['feature_revision']:
        raise ValueError('Model feature revision differs from its policy descriptor')
    policy = PopulationPolicy(model, checked_path(root, 'ai/strong/population-hybrid-policy.cjs'),
        arm=settings['arm'], samples=settings['samples'], workers=settings['workers'], max_steps=settings['max_steps'])
    identity = {'policySha256': digest(path), 'runtimeManifestSha256': spec['runtime_manifest']['sha256'],
                'modelSha256': model.sha256, 'featureRevision': policy.revision,
                'backend': spec['backend'], 'settings': settings}
    return PopulationInstance(policy, identity)


class PublicPolicyService:
    """One stateless decision per request, with a reusable engine between requests."""
    def __init__(self, factory):
        self.factory, self.instance = factory, None

    def close(self):
        if self.instance is not None:
            instance, self.instance = self.instance, None
            instance.close()

    def decide(self, request, *, diagnostics=False):
        if not isinstance(request, dict) or not isinstance(request.get('state'), dict):
            raise ValueError('Expected an object containing state and player')
        players = request['state'].get('players')
        actor = request.get('player')
        if not isinstance(players, list) or not 2 <= len(players) <= 6:
            raise ValueError('Expected two to six players')
        if type(actor) is not int or not 0 <= actor < len(players):
            raise ValueError('Invalid acting player')
        before = encode(request)
        started = time.perf_counter()
        try:
            if self.instance is None:
                self.instance = self.factory()
            instance = self.instance
            prepared = instance.prepare(request)
            moves = prepared['moves']
            order = prepared['observation']['playerOrder']
            if (not isinstance(moves, list) or not moves or not isinstance(order, list)
                    or any(type(seat) is not int for seat in order)
                    or sorted(order) != list(range(len(players))) or order[0] != actor):
                raise ValueError('Invalid public legal menu or player ordering')
            decision = instance.choose(request)
            index = decision['index']
            if type(index) is not int or not 0 <= index < len(moves) or encode(decision['move']) != encode(moves[index]):
                raise ValueError('Policy returned a move outside the public legal menu')
            if (decision['modelSha256'] != instance.identity['modelSha256']
                    or decision['featureRevision'] != instance.identity['featureRevision']):
                raise ValueError('Policy identity changed during a decision')
            if encode(request) != before:
                raise ValueError('Policy mutated its public request')
            response = {'requestId': request.get('requestId'), 'revision': request.get('revision'),
                        'move': decision['move'], 'playerOrder': order, **instance.identity,
                        'elapsedMs': 1000*(time.perf_counter()-started), 'qualification_eligible': False}
            if diagnostics:
                response['decision'] = decision
            # Use the same JSON representation in the arena and standalone worker.
            return json.loads(encode(response))
        except BaseException:
            self.close()
            raise

    def handle_line(self, line, *, diagnostics=False):
        request = {}
        try:
            def nonfinite(value):
                raise ValueError('Non-finite JSON number: '+value)
            def finite_float(value):
                number = float(value)
                if not math.isfinite(number):
                    return nonfinite(value)
                return number
            parsed = json.loads(line, parse_constant=nonfinite, parse_float=finite_float)
            if not isinstance(parsed, dict):
                raise ValueError('Expected a JSON object')
            request = parsed
            return self.decide(request, diagnostics=diagnostics)
        except Exception as error:
            return {'requestId': request.get('requestId'), 'revision': request.get('revision'),
                    'error': type(error).__name__+': '+str(error)}


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('artifact', type=Path)
    parser.add_argument('--descriptor', default='policy.json')
    parser.add_argument('--diagnostics', action='store_true')
    args = parser.parse_args()
    service = PublicPolicyService(lambda: load_artifact(args.artifact, args.descriptor))
    try:
        for line in sys.stdin:
            print(encode(service.handle_line(line, diagnostics=args.diagnostics)), flush=True)
    finally:
        service.close()


if __name__ == '__main__':
    main()
