"""Offline, explicitly selected expert replica inference; JSONL on stdin/stdout.

Run with the pinned CPU Python environment and explicit --replica/--checkpoint.
No environment, reference policy, game, training or network loader is invoked.
The versioned manifest is a local trust anchor, not a downloaded credential.
"""
# Frozen tensor helpers contain assertions: reject -O before importing anything.
if not __debug__:
    print('{"schema":"pg-replica-serving-error-v1","code":"startup-failed"}', flush=True)
    raise SystemExit(1)

import _imp
import argparse
from collections import OrderedDict
import contextlib
import hashlib
import importlib
import importlib.util
import io
import json
import marshal
import math
import os
from pathlib import Path
import re
import stat
import sys
from types import CodeType

ROOT = Path(__file__).absolute().parents[2]
MANIFEST = ROOT / 'ai/serving_v1/manifest.json'
MAX_LINE_BYTES = 4 * 1024**2  # Includes the terminating LF (CRLF is also accepted).
CACHE_SIZE = 64
FLOAT32_MAX = 3.4028234663852886e38
HEX64 = re.compile(r'[0-9a-f]{64}\Z')
RUNTIMES = dict(python='3.12.8', torch='2.10.0+cpu', numpy='2.2.6', node='v24.20.0', engine='2.0.22')
REPLICAS = {
    'replica1': dict(sha256='7918c5ceec29ee181721eaaa3a38f63fd94cf0248c34d192e0b3f65960c729e5',
                     configSha256='60e7a5c2d17290c76ed63fcc366448e4eec499079bf97edf242cff945f0b73b9', update=24),
    'replica2': dict(sha256='89d03f5b23fd6d088e175d32ff9c90ff88bd947f7e8b17d508b1b2f641a037fa',
                     configSha256='95727038dae650a1ab01482f427c4c831ea8a4c82c3db7632ec4d541853a10a6', update=32),
}
ARCHITECTURE = dict(schema='multimap-expert-ppo-v2', width=64, bound=16,
                    stage='train', priorAsActionFeature=True)
PYTHON_MODULES = ('data', 'model', 'residual', 'expert_policy')
FROZEN_FILES = (
    'ai/core.cjs', 'ai/strong/economics.cjs', 'engine/package.json', 'engine/wrapper.ts',
    *(f'ai/multimap/{name}.py' for name in PYTHON_MODULES),
    *(f'ai/multimap/{name}' for name in (
        'protocol.json', 'ppo-protocol-v1.json', 'expert-protocol-v2.json',
        'features.cjs', 'economics_v2.cjs', 'teacher_v2.cjs', 'teacher.cjs',
        'game.cjs', 'game_rl.cjs', 'expert_game.cjs', 'reference_game.cjs')),
)
OBSERVATION_FIELDS = {'schema', 'global', 'players', 'nodes', 'relations', 'actions', 'actionCity', 'prior'}
_FROZEN = None


def require(condition):
    if not condition:
        raise ValueError('Invalid serving input or identity')


def sha256(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    # Python-only serialization (config, retry cache, normalized offline fixtures).
    # Not a cross-language canonical JSON standard; use raw input-file hashes for
    # Node/Python fixture binding. Serving request IDs remain opaque.
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')


def strict_json(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result)
            result[key] = value
        return result

    def number(text):
        result = float(text)
        require(math.isfinite(result))
        return result

    def invalid(_):
        raise ValueError('Invalid JSON')

    require(type(raw) is bytes)
    return json.loads(raw.decode('utf-8'), object_pairs_hook=pairs,
                      parse_float=number, parse_constant=invalid)


def safe_read(path, limit, *, size=None):
    """Bounded regular-file read with no symlink in ANY path component.

    Walk directory descriptors with O_NOFOLLOW, rather than checking a path and
    then reopening it. Hash/load consume the very same checkpoint bytes.
    """
    path = Path(path)
    require('..' not in path.parts)
    path = path.absolute()
    directory = os.open(path.anchor, os.O_RDONLY | os.O_DIRECTORY)
    try:
        for part in path.parts[1:-1]:
            next_directory = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=directory)
            os.close(directory)
            directory = next_directory
        descriptor = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
        with os.fdopen(descriptor, 'rb') as stream:
            info = os.fstat(stream.fileno())
            require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1 and 0 < info.st_size <= limit)
            require(size is None or info.st_size == size)
            raw = stream.read(limit + 1)
            require(len(raw) == info.st_size and len(raw) <= limit)
            return raw
    finally:
        os.close(directory)


def authenticate_bytecode(path, raw):
    """Authenticate applicable pyc against a fresh compile; -B alone is not enough.

    Equivalent to the completed study's stdlib-only bytecode guard, without
    importing its audit workflow. Nothing is deleted or patched.
    """
    cache = Path(importlib.util.cache_from_source(str(path)))
    if cache.exists() or cache.is_symlink():
        cached = safe_read(cache, 16 * 1024**2)
        require(len(cached) > 16)
        if cached[:4] != importlib.util.MAGIC_NUMBER:
            return
        flags = int.from_bytes(cached[4:8], 'little')
        require(flags in (0, 1, 3))
        if flags == 0:
            info = Path(path).stat()
            if (int.from_bytes(cached[8:12], 'little') != int(info.st_mtime) & 0xffffffff or
                    int.from_bytes(cached[12:16], 'little') != len(raw) & 0xffffffff):
                return
        elif (flags == 3 and _imp.check_hash_based_pycs != 'never'
              and cached[8:16] != importlib.util.source_hash(raw)):
            return
        code = marshal.loads(cached[16:])
        require(isinstance(code, CodeType))
        require(code == compile(raw, code.co_filename, 'exec', dont_inherit=True, optimize=0))


def load_manifest(path=MANIFEST):
    raw = safe_read(path, 128 * 1024)
    manifest = strict_json(raw)
    require(type(manifest) is dict and set(manifest) == {'schema', 'replicas', 'sourceFiles', 'runtimes'})
    require(manifest['schema'] == 'pg-replica-serving-manifest-v1')
    require(canonical(manifest['runtimes']) == canonical(RUNTIMES))
    require(type(manifest['replicas']) is dict and set(manifest['replicas']) == set(REPLICAS))
    for replica, pin in REPLICAS.items():
        expected = dict(pin, bytes=793281, **ARCHITECTURE)
        require(canonical(manifest['replicas'][replica]) == canonical(expected))
    return manifest, sha256(raw)


def verify_sources(manifest, root=ROOT):
    files = manifest['sourceFiles']
    require(type(files) is dict)
    engine = {p.relative_to(root).as_posix() for p in (root / 'engine/dist').rglob('*.js')}
    require(len(engine) == 42 and set(files) == set(FROZEN_FILES) | engine)
    sources = {}
    for name, checksum in files.items():
        require(type(checksum) is str and HEX64.fullmatch(checksum))
        raw = safe_read(root / name, 16 * 1024**2)
        require(sha256(raw) == checksum)
        if name.endswith('.py'):
            authenticate_bytecode(root / name, raw)
            sources[Path(name).stem] = raw
    package = strict_json(safe_read(root / 'engine/package.json', 64 * 1024))
    require(package['version'] == RUNTIMES['engine'])
    return sources


def frozen_runtime():
    """Import only the four authenticated inference dependencies, never a loader."""
    global _FROZEN
    if _FROZEN is not None:
        require(all(sys.modules.get(name) is module for name, module in _FROZEN.items()))
        return _FROZEN['expert_policy']
    require(not any(name in sys.modules for name in PYTHON_MODULES))
    original_path = sys.path[:]
    original_bytecode = sys.dont_write_bytecode
    try:
        sys.dont_write_bytecode = True
        sys.path.insert(0, str(ROOT / 'ai/multimap'))
        modules = {name: importlib.import_module(name) for name in PYTHON_MODULES}
        require(all(Path(module.__file__).absolute() == ROOT / f'ai/multimap/{name}.py'
                    for name, module in modules.items()))
        _FROZEN = modules
    finally:
        sys.path[:] = original_path
        sys.dont_write_bytecode = original_bytecode
    return _FROZEN['expert_policy']


def validate_saved(saved, pin):
    require(type(saved) is dict and set(saved) == {
        'schema', 'width', 'bound', 'stage', 'priorAsActionFeature', 'state_dict', 'config', 'update'})
    for key, value in dict(ARCHITECTURE, update=pin['update']).items():
        require(type(saved[key]) is type(value) and saved[key] == value)
    require(type(saved['config']) is dict and sha256(canonical(saved['config'])) == pin['configSha256'])


def validate_observation(observation):
    """Validate all dimensions/numbers BEFORE frozen row() allocates tensors."""
    require(type(observation) is dict and set(observation) == OBSERVATION_FIELDS)
    require(observation['schema'] == 'multimap-graph-v1')

    def vector(values, length):
        require(type(values) is list and len(values) == length)
        for value in values:
            require(type(value) in (int, float) and -FLOAT32_MAX <= value <= FLOAT32_MAX and math.isfinite(value))

    def matrix(values, low, high, width):
        require(type(values) is list and low <= len(values) <= high)
        for values_row in values:
            vector(values_row, width)
        return len(values)

    vector(observation['global'], 273)
    matrix(observation['players'], 2, 6, 80)
    nodes = matrix(observation['nodes'], 1, 64, 36)
    actions = matrix(observation['actions'], 2, 4096, 34)
    relations = observation['relations']
    require(type(relations) is list and len(relations) == 4)
    for relation in relations:
        matrix(relation, nodes, nodes, nodes)
    cities = observation['actionCity']
    require(type(cities) is list and len(cities) == actions)
    require(all(type(city) is int and -1 <= city < nodes for city in cities))
    prior = observation['prior']
    vector(prior, actions)
    require(all(-20 <= value <= 0 for value in prior) and max(prior) == 0)
    return actions


class ReplicaPolicy:
    """One explicit, pinned replica. choose(public_observation) returns an int."""

    def __init__(self, replica, checkpoint):
        require(type(replica) is str and replica in REPLICAS)
        manifest, self.manifest_sha256 = load_manifest()
        verify_sources(manifest)
        self.replica = replica
        pin = manifest['replicas'][replica]
        raw = safe_read(checkpoint, pin['bytes'], size=pin['bytes'])
        require(sha256(raw) == pin['sha256'])
        self.checkpoint_sha256 = pin['sha256']
        require('.'.join(map(str, sys.version_info[:3])) == RUNTIMES['python'])
        import torch
        import numpy
        require(torch.__version__ == RUNTIMES['torch'] and numpy.__version__ == RUNTIMES['numpy'])
        require(torch.get_default_dtype() == torch.float32 and torch.get_default_device().type == 'cpu')
        torch.set_num_threads(1)
        self._torch = torch
        self._expert = frozen_runtime()
        self.model, saved = self._expert.load(io.BytesIO(raw))  # Frozen load uses weights_only=True.
        validate_saved(saved, pin)
        require(type(self.model) is self._expert.ExpertPolicy and self.model.width == 64 and self.model.bound == 16)
        self.model.eval()
        self.model.requires_grad_(False)
        require(all(p.device.type == 'cpu' and p.dtype == torch.float32 and torch.isfinite(p).all()
                    for p in self.model.parameters()))
        # Capture only after authenticated loading and the one-time eval/freeze.
        self._loaded_fingerprint = self._model_fingerprint()

    def _model_fingerprint(self):
        """Retain tensor bytes/metadata and inference-relevant module state.

        This detects accidental in-process changes, not malicious Python code
        deliberately replacing private fields or methods. It never repairs state.
        """
        torch = self._torch

        def tensors(items):
            result = []
            for name, value in items:
                require(value.device.type == 'cpu' and value.layout == torch.strided)
                raw = value.detach().contiguous().reshape(-1).view(torch.uint8).numpy().tobytes()
                result.append((name, tuple(value.shape), value.dtype, value.device, sha256(raw)))
            return tuple(result)

        modules = tuple(
            (name, type(module), type(module.training), module.training,
             tuple((key, type(getattr(module, key)), getattr(module, key))
                   for key in ('width', 'bound') if hasattr(module, key)))
            for name, module in self.model.named_modules())
        gradients = tuple((name, value.requires_grad, value.grad is None)
                          for name, value in self.model.named_parameters())
        return (modules, gradients, tensors(self.model.state_dict().items()),
                tensors(self.model.named_buffers()))  # Includes nonpersistent buffers.

    def assert_unchanged(self):
        """Fail closed if the authenticated model has changed since loading."""
        require(self._model_fingerprint() == self._loaded_fingerprint)

    def choose(self, observation):
        count = validate_observation(observation)
        self.assert_unchanged()
        torch = self._torch
        require(torch.get_num_threads() == 1 and torch.get_default_dtype() == torch.float32
                and torch.get_default_device().type == 'cpu')
        require(all(not module.training for module in self.model.modules()))
        with torch.inference_mode():
            inputs = self._expert.batch([self._expert.row(observation)])
            mask = inputs['actionMask']
            require(mask.dtype == torch.bool and tuple(mask.shape) == (1, count) and bool(mask.all()))
            logits, _ = self.model(inputs)  # The uncalibrated value head is deliberately discarded.
            require(isinstance(logits, torch.Tensor) and logits.dtype == torch.float32
                    and logits.device.type == 'cpu' and tuple(logits.shape) == (1, count)
                    and bool(torch.isfinite(logits).all()))
            index = int(torch.argmax(logits[0]).item())  # First maximum, no sampling/reranking.
            require(0 <= index < count and bool(mask[0, index]))
        self.assert_unchanged()
        return index

    def ready(self):
        return dict(schema='pg-replica-serving-ready-v1', replica=self.replica,
                    checkpointSha256=self.checkpoint_sha256, manifestSha256=self.manifest_sha256)


class RequestSession:
    """Bounded 64-entry LRU retry cache; an ID/payload conflict fails closed."""

    def __init__(self, policy):
        self.policy = policy
        self.cache = OrderedDict()

    def handle(self, request):
        require(type(request) is dict and set(request) == {'schema', 'requestId', 'replica', 'observation'})
        require(request['schema'] == 'pg-replica-serving-request-v1' and request['replica'] == self.policy.replica)
        request_id = request['requestId']
        require(type(request_id) is str and HEX64.fullmatch(request_id))
        count = validate_observation(request['observation'])
        payload = sha256(canonical(request))
        if request_id in self.cache:
            previous, response = self.cache[request_id]
            require(previous == payload)
            self.cache.move_to_end(request_id)
            return dict(response)
        index = self.policy.choose(request['observation'])
        require(type(index) is int and 0 <= index < count)
        response = dict(schema='pg-replica-serving-response-v1', requestId=request_id,
                        replica=self.policy.replica, checkpointSha256=self.policy.checkpoint_sha256,
                        index=index, actionCount=count)
        self.cache[request_id] = payload, response
        if len(self.cache) > CACHE_SIZE:
            self.cache.popitem(last=False)
        return dict(response)


def emit(output, message):
    output.write(json.dumps(message, separators=(',', ':'), allow_nan=False) + '\n')
    output.flush()


def error(output, code):
    try:
        emit(output, dict(schema='pg-replica-serving-error-v1', code=code))
    except (OSError, ValueError):
        pass
    return 1


def serve(policy, source, output):
    """Binary bounded-read JSONL; clean EOF is success, unterminated JSON is not."""
    try:
        emit(output, policy.ready())
        session = RequestSession(policy)
        while True:
            line = source.readline(MAX_LINE_BYTES + 1)
            if line == b'':
                return 0
            require(type(line) is bytes and len(line) <= MAX_LINE_BYTES and line.endswith(b'\n'))
            emit(output, session.handle(strict_json(line)))
    except (Exception, KeyboardInterrupt):
        return error(output, 'invalid-request')


class _Arguments(argparse.ArgumentParser):
    def error(self, message):
        raise ValueError('Invalid arguments')


def main(argv=None):
    output = sys.stdout
    try:
        # Never forward dependency chatter, raw input, model contents or traceback.
        with open(os.devnull, 'w') as quiet, contextlib.redirect_stdout(quiet), contextlib.redirect_stderr(quiet):
            parser = _Arguments(add_help=False, allow_abbrev=False)
            parser.add_argument('--replica', choices=tuple(REPLICAS), required=True)
            parser.add_argument('--checkpoint', required=True)
            args = parser.parse_args(argv)
            policy = ReplicaPolicy(args.replica, args.checkpoint)
            return serve(policy, sys.stdin.buffer, output)
    except (Exception, KeyboardInterrupt):
        return error(output, 'startup-failed')


if __name__ == '__main__':
    raise SystemExit(main())
