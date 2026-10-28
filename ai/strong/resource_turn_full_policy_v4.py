"""Pinned research policy: complete resource turns, filtered-model other phases.

The six modes are execution controls, not selected or qualified candidates.
This service receives only public JSON. It cannot submit jobs or mutate an arena.
"""
import argparse
import importlib
import json
import math
from pathlib import Path
import sys

from resource_turn_public_policy_v2 import (
    ResourceTurnProducer, checked_path, digest, encode,
)

MODES = ('filter', 'model-turn', 'search-turn', 'atomic-search', 'atomic-search-corrected', 'atomic-search-anchored')
DESCRIPTOR = 'resource-full-descriptor.json'


def load_artifact(root):
    root = Path(root).resolve()
    descriptor_path = checked_path(root, DESCRIPTOR)
    spec = json.loads(descriptor_path.read_text())
    if (spec['revision'] != 'resource-turn-full-artifact-v4'
            or spec['qualification_eligible'] is not False
            or spec['reserved_final_seeds_used'] is not False
            or spec['settings']['max_steps'] != 2400):
        raise ValueError('Invalid research artifact contract')
    manifest_path = checked_path(root, spec['manifest']['path'])
    if digest(manifest_path) != spec['manifest']['sha256']:
        raise ValueError('Artifact manifest changed')
    hashes = json.loads(manifest_path.read_text())
    for name, expected in hashes.items():
        if digest(checked_path(root, name)) != expected:
            raise ValueError('Artifact file changed: '+name)
    local = Path(__file__).resolve()
    if local != checked_path(root, 'policy/'+local.name):
        raise ValueError('Run the full policy from its pinned artifact')
    for key in ('runtime', 'model'):
        item = spec[key]
        if digest(checked_path(root, item['path'])) != item['sha256']:
            raise ValueError('Frozen '+key+' identity changed')
    return root, spec, hashes


class FullResourcePolicy:
    def __init__(self, root, mode):
        if mode not in MODES:
            raise ValueError('Unknown execution control')
        self.producer = self.atomic = None
        self.root, self.artifact, hashes = load_artifact(root)
        self.mode = mode
        spec = self.artifact
        runtime = (self.root/spec['runtime']['directory']).resolve()
        if not runtime.is_relative_to(self.root):
            raise ValueError('Runtime escaped artifact')
        self.producer = ResourceTurnProducer(runtime=runtime,
            manifest=spec['runtime']['manifest'], manifest_sha256=spec['runtime']['sha256'],
            model=checked_path(self.root, spec['model']['path']), model_sha256=spec['model']['sha256'],
            mode='search' if mode in ('search-turn', 'atomic-search', 'atomic-search-corrected', 'atomic-search-anchored') else 'model',
            **spec['settings'])
        try:
            module_name = 'resource_replanning_policy_v1' if mode in ('atomic-search','atomic-search-corrected', 'atomic-search-anchored') else 'population_hybrid_policy'
            module = importlib.import_module(module_name)
            origin = Path(module.__file__).resolve()
            if not origin.is_relative_to(self.root) or hashes.get(str(origin.relative_to(self.root))) != digest(origin):
                raise ValueError('Atomic policy imported outside pinned artifact')
            policy_class = module.ResourceReplanningPolicy if mode in ('atomic-search','atomic-search-corrected', 'atomic-search-anchored') else module.PopulationPolicy
            self.atomic = policy_class(self.producer.model,
                runtime/'ai/strong/population-hybrid-policy.cjs',
                arm='resource-filter' if mode in ('atomic-search','atomic-search-corrected', 'atomic-search-anchored') else 'filter',
                **{k:v for k,v in spec['settings'].items() if k != 'threads'})
            if mode == 'atomic-search-corrected':
                from resource_turn_search_v1 import ResourceTurnSearch
                self.atomic.resource = ResourceTurnSearch(self.producer.model,
                    self.root/'policy/resource-turn-search-worker-v2.cjs',
                    **{k:v for k,v in spec['settings'].items() if k != 'threads'})
            if mode == 'atomic-search-anchored':
                from resource_turn_anchored_search_v2 import AnchoredResourceTurnSearch
                self.atomic.resource = AnchoredResourceTurnSearch(self.producer.model,
                    self.root/'policy/resource-turn-search-worker-v4.cjs',
                    **{k:v for k,v in spec['settings'].items() if k != 'threads'})
            self.specification = {'revision':'resource-turn-full-policy-v4', 'mode':mode,
                'resourceSampling':('turn-start-public-history-v2' if mode == 'atomic-search-anchored'
                    else 'current-public-state-v1' if mode in ('search-turn','atomic-search','atomic-search-corrected')
                    else 'not-used'),
                'resourceBaseline':('historical-public-deck-v1' if mode == 'atomic-search'
                    else 'atomic-public-observation' if mode == 'filter' else 'public-deck-metadata-v2'),
                'artifactDescriptorSha256':digest(self.root/DESCRIPTOR),
                'resourcePolicy':self.producer.specification,
                'otherPhases':'frozen-filtered-model', 'qualification_eligible':False}
            import hashlib
            self.identity = {'policySha256':hashlib.sha256(encode(self.specification).encode()).hexdigest(),
                'modelSha256':spec['model']['sha256'],
                'runtimeManifestSha256':spec['runtime']['sha256']}
        except BaseException:
            self.close()
            raise

    def describe(self):
        return {'identity':self.identity, 'resourceIdentity':self.producer.identity,
                'specification':self.specification, 'qualification_eligible':False}

    def close(self):
        if self.atomic is not None:
            atomic, self.atomic = self.atomic, None
            atomic.close()
        if self.producer is not None:
            producer, self.producer = self.producer, None
            producer.close()

    def decide(self, request):
        if (not isinstance(request, dict) or not isinstance(request.get('state'), dict)
                or not isinstance(request.get('requestId'), str) or not request['requestId']
                or type(request.get('revision')) is not int or not 0 <= request['revision'] <= 2**53-1):
            raise ValueError('Invalid public request or revision')
        state, seat = request['state'], request.get('player')
        if (not isinstance(state.get('players'), list) or not 2 <= len(state['players']) <= 6
                or type(seat) is not int or not 0 <= seat < len(state['players'])
                or state.get('currentPlayers', [None])[0] != seat):
            raise ValueError('Invalid acting player')
        before = encode(request)
        result = {'requestId':request['requestId'], 'revision':request['revision'],
                  'identity':self.identity, 'qualification_eligible':False}
        if state['phase'] == 'Resources' and self.mode in ('model-turn', 'search-turn'):
            chosen = self.producer.decide(request)
            result.update(kind='resource-turn', resource=chosen['response'], diagnostics=chosen['diagnostics'])
        else:
            chosen = self.atomic.choose(request)
            result.update(kind='atomic', move=chosen['move'], decision=chosen)
        if encode(request) != before:
            raise ValueError('Policy mutated its public input')
        return result


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--artifact', type=Path, required=True)
    parser.add_argument('--mode', choices=MODES, required=True)
    args = parser.parse_args()
    policy = None
    def finite(value):
        number = float(value)
        if not math.isfinite(number):
            raise ValueError('Non-finite JSON')
        return number
    try:
        for line in sys.stdin:
            try:
                q = json.loads(line, parse_float=finite,
                    parse_constant=lambda value: (_ for _ in ()).throw(ValueError('Non-finite JSON')))
                if not isinstance(q, dict) or q.get('op') not in ('describe', 'decide'):
                    raise ValueError('Unknown public operation')
                if policy is None:
                    policy = FullResourcePolicy(args.artifact, args.mode)
                result = policy.describe() if q['op'] == 'describe' else policy.decide(q['request'])
            except Exception as error:
                if policy is not None:
                    policy.close(); policy = None
                result = {'error':type(error).__name__+': '+str(error)}
            print(encode(result), flush=True)
    finally:
        if policy is not None:
            policy.close()


if __name__ == '__main__':
    main()
