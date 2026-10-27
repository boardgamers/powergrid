"""Actual-model complete resource-turn producer for isolated research experiments.

Only the Resources phase is supported. It returns a whole-turn response plus
separate research diagnostics; callers must execute the entire response through
the independently checked arena. It never launches jobs or chooses a candidate.
"""
import argparse
import hashlib
import importlib
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
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def checked_hash(value):
    if not isinstance(value, str) or not re.fullmatch('[a-f0-9]{64}', value):
        raise ValueError('Expected a SHA256 digest')
    return value


def checked_path(root, name):
    if not isinstance(name, str) or not name or Path(name).is_absolute() or '..' in Path(name).parts:
        raise ValueError('Runtime paths must remain inside the verified directory')
    result = (root/name).resolve()
    if not result.is_relative_to(root) or not result.is_file():
        raise ValueError('Missing runtime file or escaped runtime path')
    return result


class ResourceTurnProducer:
    def __init__(self, *, runtime, manifest, manifest_sha256, model, model_sha256,
                 mode, samples=8, workers=1, threads=1, max_steps=2400):
        self.search = self.exchange = None
        self.runtime = Path(runtime).resolve()
        if mode not in ('model', 'search'):
            raise ValueError('Unknown resource producer mode')
        bounds = {'samples': range(4,65,4), 'workers': range(1,33),
                  'threads': range(1,9), 'max_steps': range(1,2401)}
        settings = dict(samples=samples, workers=workers, threads=threads, max_steps=max_steps)
        if any(type(settings[k]) is not int or settings[k] not in values for k, values in bounds.items()):
            raise ValueError('Invalid fixed resource producer setting')
        if os.environ.get('NODE_OPTIONS'):
            raise ValueError('NODE_OPTIONS would change the engine runtime')
        manifest_path = checked_path(self.runtime, manifest)
        if digest(manifest_path) != checked_hash(manifest_sha256):
            raise ValueError('Runtime manifest hash mismatch')
        hashes = json.loads(manifest_path.read_text())
        if not isinstance(hashes, dict) or not hashes:
            raise ValueError('Missing runtime hashes')
        for name, expected in hashes.items():
            if digest(checked_path(self.runtime,name)) != checked_hash(expected):
                raise ValueError('Runtime file changed: '+name)
        model_path = Path(model).resolve()
        if digest(model_path) != checked_hash(model_sha256):
            raise ValueError('Model hash mismatch')
        sys.path.insert(0,str(self.runtime/'ai/strong'))
        resource = importlib.import_module('resource_turn_search_v1')
        hybrid = importlib.import_module('hybrid_search')
        for name in ('resource_turn_search_v1','hybrid_search','infer','pool','feature_contract'):
            module = importlib.import_module(name)
            origin = Path(module.__file__).resolve()
            if not origin.is_relative_to(self.runtime) or hashes.get(str(origin.relative_to(self.runtime))) != digest(origin):
                raise ValueError('Imported module differs from the verified runtime: '+name)
        self.mode = mode
        self.model = hybrid.Model(model_path, threads=threads)
        if self.model.sha256 != model_sha256 or hybrid.model_revision(self.model) != '4.3-strategic-correction':
            raise ValueError('Unsupported model identity or feature revision')
        local = Path(__file__).resolve().parent
        adapter_hashes = {name:digest(local/name) for name in (
            'resource_turn_public_policy_v1.py','resource-turn-exchange-worker-v1.cjs',
            'resource-turn-exchange-v1.cjs','resource-turn-transaction-v1.cjs')}
        self.specification = {'revision':'resource-turn-public-policy-v1','mode':mode,
            'featureRevision':'4.3-strategic-correction','settings':settings,
            'modelSha256':model_sha256,'runtimeManifestSha256':manifest_sha256,
            'adapterHashes':adapter_hashes,'qualification_eligible':False}
        self.identity = {'policySha256':hashlib.sha256(encode(self.specification).encode()).hexdigest(),
            'modelSha256':model_sha256,'runtimeManifestSha256':manifest_sha256}
        self.search = resource.ResourceTurnSearch(self.model,self.runtime/'ai/strong/resource-turn-search-v1.cjs',
            samples=samples, workers=workers, max_steps=max_steps)
        try:
            self.exchange = hybrid.Node(str(local/'resource-turn-exchange-worker-v1.cjs'))
        except BaseException:
            self.close()
            raise

    def close(self):
        if self.search is not None:
            search,self.search = self.search,None
            search.close()
        if self.exchange is not None:
            exchange,self.exchange = self.exchange,None
            exchange.close()

    def decide(self, request):
        if not isinstance(request,dict) or not isinstance(request.get('state'),dict):
            raise ValueError('Expected an object containing a public state')
        state,seat = request['state'],request.get('player')
        if state.get('phase') != 'Resources':
            raise ValueError('The whole-resource producer supports only Resources')
        if not isinstance(state.get('players'),list) or not 2 <= len(state['players']) <= 6:
            raise ValueError('Expected two to six players')
        if type(seat) is not int or not 0 <= seat < len(state['players']) or state.get('currentPlayers') != [seat]:
            raise ValueError('Expected the sole current resource buyer')
        if not isinstance(request.get('requestId'),str) or not request['requestId']:
            raise ValueError('Missing request ID')
        if type(request.get('revision')) is not int or not 0 <= request['revision'] <= 2**53-1:
            raise ValueError('Invalid request revision')
        before = encode(request)
        began = time.perf_counter()
        if self.mode == 'search':
            result = self.search.choose(request)
            actions = result['actions']
            if actions != result['bundles'][result['selected']]['actions']:
                raise ValueError('Selected whole plan differs from its evaluated bundle')
            trace = result['baselineDecisions']
        else:
            baseline,trace = self.search.baseline(request)
            actions = baseline['baselineActions']
            result = None
        response = self.exchange.call({'op':'respond','runtime':str(self.runtime),
            'request':request,'actions':actions,'identity':self.identity})
        if 'error' in response:
            raise ValueError('Resource response rejected: '+response['error'])
        if response['transaction']['actions'] != actions or encode(request) != before:
            raise ValueError('Resource response changed the chosen plan or public input')
        return {'response':response,'diagnostics':{'specification':self.specification,
            'baselineDecisions':trace,'searchResult':result,
            'elapsedMs':1000*(time.perf_counter()-began),'qualification_eligible':False}}


class ResourceTurnService:
    def __init__(self, factory):
        self.factory,self.producer = factory,None

    def close(self):
        if self.producer is not None:
            producer,self.producer = self.producer,None
            producer.close()

    def handle_line(self, line):
        request = {}
        try:
            def nonfinite(value):
                raise ValueError('Non-finite JSON number: '+value)
            def finite_float(value):
                number = float(value)
                if not math.isfinite(number):return nonfinite(value)
                return number
            parsed = json.loads(line,parse_constant=nonfinite,parse_float=finite_float)
            if not isinstance(parsed,dict):raise ValueError('Expected a JSON object')
            request = parsed
            if self.producer is None:self.producer = self.factory()
            return self.producer.decide(request)
        except Exception as error:
            self.close()
            return {'requestId':request.get('requestId'),'revision':request.get('revision'),
                    'error':type(error).__name__+': '+str(error)}


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--runtime',required=True,type=Path)
    parser.add_argument('--manifest',required=True)
    parser.add_argument('--manifest-sha256',required=True)
    parser.add_argument('--model',required=True,type=Path)
    parser.add_argument('--model-sha256',required=True)
    parser.add_argument('--mode',choices=['model','search'],required=True)
    parser.add_argument('--samples',type=int,default=8)
    parser.add_argument('--workers',type=int,default=1)
    parser.add_argument('--threads',type=int,default=1)
    parser.add_argument('--max-steps',type=int,default=2400)
    settings=vars(parser.parse_args())
    service = ResourceTurnService(lambda:ResourceTurnProducer(**settings))
    try:
        for line in sys.stdin:
            print(encode(service.handle_line(line)),flush=True)
    finally:service.close()


if __name__ == '__main__':
    main()
