"""External integrity and the 48 FIXED evaluation replays for replica stress v1.

Import is standard-library only. No launch, training, selection, optimizer, cache
repair, or implicit payload download API exists here. ``fetch`` requires
--allow-download. ``verify`` uses retained payloads and read-only authenticated
metadata/jobs. ``replay`` repeats verification, requires --allow-games, and emits
BOTH receipts only after all 48 comparisons succeed. A verification JSON file is
not a resumable capability: finalization requires the live verified session.
Authority lives in a closure-owned registry, not in mutable session fields.
The public session's ``models`` contains detached metadata, never live policies.
Paid-job proofs use only ROOT/ai/runs/GROUP; --ledger cannot relocate that ledger.
Replay intents/results use the fixed study-wide integrity-attempts-v1 directory;
failed/unknown attempts cannot be retried by changing output, session or process.

Run with ai/.venv/bin/python -B and PYTHONPATH=ai/multimap. Explicit immutable
revisions are mandatory; there is no default/latest final snapshot. Reference
and expert caches are reused, never deleted. Failed runs retain fixed-code
operational evidence and never release finished-subset strength conclusions.
"""
import argparse
import ast
import copy
from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import importlib
import importlib.util
import json
import marshal
import os
import sys
from pathlib import Path, PurePosixPath
import random
import re
import shutil
import subprocess
import tarfile
from types import CodeType, FunctionType, ModuleType

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
GROUP = 'multimap-replica-stress-20261109-v1'
ATTEMPT_ROOT = ROOT / 'ai/runs' / (GROUP + '-integrity-attempts-v1')
PANELS = ('strong', 'mixed')
MODELS = ('expert24', 'replica1', 'replica2', 'ppo0', 'ppo1', 'ppo2')
EXPERTS = MODELS[:3]
MODEL_CLASSES = {name: 'expert_policy.ExpertPolicy' if name in EXPERTS else 'residual.ResidualPolicy'
                 for name in MODELS}
SOURCE = '7bab96167ee32d691b2ccc450c50162283b0a473'
SOURCE_REVISION = '6eec23b7c0b07c2ae3514f46d1e9b5157f79c969'
SOURCE_SHA = 'ccf09e2cb52e30ec1c96008c6bf9bd5e7ee80291742dd220d5c9d0681c0f3c08'
DECODER_GIT = '4dceb9c16a9690d3e22fcedb9fed64043d66e505'
DECODER_SHA = '55d66336acc4d35a081fdf766132551ec6efbc912e584144baba608251b17ce0'
PEER_GIT = '0f9848da243157fc3139b284a8e449c3df8b9b9a'
LAUNCH_GIT = 'f1903aa078e581a3030ee0c5703786f7047eec38'
REPO = 'coyotte508/powergrid-ai-multimap-v1'
DATASET = 'coyotte508/powergrid-ai-training-v1'
SOURCE_PATH = 'multimap/' + GROUP + '/source.tgz'
INITIAL_IDS = dict(strong='6af24e8a9737d9a9e08ddd53', mixed='6af2549c9737d9a9e08df3e7')
HOURS = dict(strong=6, mixed=3, recovery=3)
LIMIT = 64 * 1024**2
SOURCE_LIMIT = 256 * 1024**2 - 1
FILE_LIMIT = 16 * 1024**2
MANIFEST_LIMIT = 64 * 1024
LOG_LIMIT = 2 * 1024**2
TIMINGS = frozenset(('featureMs', 'inferenceMs', 'referenceMs', 'seconds'))
SOURCE_NAMES = (
    'replica-stress-protocol-v1.json', 'replica_stress_game_v1.cjs',
    'replica_stress_rollout_v1.py', 'replica_stress_study_v1.py', 'job_replica_stress_v1.py',
    'launch_replica_stress_v1.py', 'preflight_replica_stress_v1.py', 'test_replica_stress_v1.cjs',
    'test_replica_stress_rollout_v1.py', 'test_replica_stress_study_v1.py',
    'test_job_replica_stress_v1.py', 'test_launch_replica_stress_v1.py', 'test_preflight_replica_stress_v1.py',
)
REPLAY_SCOPES = (
    ('Germany', 2, 'recharged', True, 0, 0),
    ('Germany', 6, 'recharged', True, 7, 5),
    ('USA', 3, 'recharged', True, 2, 1),
    ('USA', 5, 'original', True, 5, 4),
    ('France', 4, 'recharged', False, 4, 2),
    ('France', 2, 'original', True, 1, 1),
    ('UK & Ireland', 5, 'recharged', True, 6, 3),
    ('UK & Ireland', 6, 'original', False, 3, 0),
)
FLAGS = dict(fitting=False, selection=False, qualified=False,
             qualificationEligible=False, reservedFinalSeedsUsed=False)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def object_sha(value):
    return sha(canonical(value).encode())


def exact(actual, expected, message):
    require(canonical(actual) == canonical(expected), message)


def immutable(value, length=40):
    require(type(value) is str and re.fullmatch('[0-9a-f]{' + str(length) + '}', value), 'Immutable hash required')
    return value


def safe_name(name):
    require(type(name) is str and name and '\\' not in name, 'Unsafe member name')
    p = PurePosixPath(name)
    require(not p.is_absolute() and '..' not in p.parts and p.as_posix() == name and name != '.', 'Unsafe member path')
    return name


def lexical_path(path):
    # Path.absolute() does NOT remove '..'. Reject before any filesystem access
    # or resolution, including on non-existent output/cache/input paths.
    path = Path(path)
    require('..' not in path.parts, 'Parent traversal forbidden')
    return path.absolute()


def no_links(path):
    path = lexical_path(path)
    require(not any(p.is_symlink() for p in (path, *path.parents)), 'Symlink/ancestor forbidden')
    return path.resolve()


def canonical_ledger(directory=None):
    """The original paid-job ledger is fixed, never a relocatable proof input.

    Coordinator device/inode checks still authenticate this directory separately;
    rebinding a copy's coordinator cannot make omitted unknown slots disappear.
    """
    expected = no_links(ROOT / 'ai/runs' / GROUP)
    actual = expected if directory is None else no_links(directory)
    require(actual == expected, 'Canonical original paid-job ledger required; relocation forbidden')
    return expected


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def decode_json(raw):
    def pairs(items):
        result = {}
        for k, v in items:
            require(k not in result, 'Duplicate JSON key')
            result[k] = v
        return result
    value = json.loads(raw, object_pairs_hook=pairs,
                       parse_constant=lambda _: require(False, 'Nonfinite JSON'))
    canonical(value)
    return value


def read(path, limit=LIMIT):
    path = no_links(path)
    require(path.is_file() and 0 < path.stat().st_size <= limit, 'Missing/oversized regular file')
    return decode_json(path.read_bytes())


def write_new(path, value):
    path = no_links(path)
    raw = (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + '\n').encode()
    if path.exists():
        require(path.is_file() and path.read_bytes() == raw, 'Different retained evidence must not be overwritten')
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('xb') as stream:
            stream.write(raw)
    return digest(path)


def bind(function, **overrides):
    """No mutation of old guards, even for the expanded source-only limit."""
    namespace = dict(function.__globals__)
    namespace.update(overrides)
    result = FunctionType(function.__code__, namespace, function.__name__, function.__defaults__, function.__closure__)
    result.__kwdefaults__ = copy.copy(function.__kwdefaults__)
    return result


def git_bytes(name, revision=SOURCE):
    safe_name(name)
    immutable(revision)
    return subprocess.check_output(['git', 'show', revision + ':' + name], cwd=ROOT, stderr=subprocess.DEVNULL)


def authenticate_bytecode(path, raw):
    """-B prevents writes, NOT reads. Authenticate any applicable cached code.

    No cache is deleted and no import hook/global loader is patched. Marshal
    deserializes code but never executes it; comparison is to a fresh compile of
    the already Git-authenticated source, including every nested code object.
    """
    cache = Path(importlib.util.cache_from_source(str(path)))
    if cache.exists():
        no_links(cache)
        require(cache.is_file() and 16 < cache.stat().st_size <= FILE_LIMIT, 'Bounded regular Python cache')
        cached = cache.read_bytes()
        if cached[:4] != importlib.util.MAGIC_NUMBER:
            return  # CPython ignores a cache for a different interpreter.
        flags = int.from_bytes(cached[4:8], 'little')
        require(flags in (0, 1, 3), 'Unknown Python cache flags')
        if flags == 0:
            stat = Path(path).stat()
            if (int.from_bytes(cached[8:12], 'little') != int(stat.st_mtime) & 0xffffffff or
                    int.from_bytes(cached[12:16], 'little') != len(raw) & 0xffffffff):
                return  # Timestamp/size-stale code is not executed by Python.
        elif flags == 3 and cached[8:16] != importlib.util.source_hash(raw):
            return  # Checked-hash-stale code is not executed by Python.
        code = marshal.loads(cached[16:])
        require(isinstance(code, CodeType), 'Python cache must contain code')
        expected = compile(raw, code.co_filename, 'exec', dont_inherit=True, optimize=sys.flags.optimize)
        require(code == expected, 'Cached Python bytecode differs from authenticated source')


def authenticate_file(name, revision=SOURCE, checksum=None):
    raw = git_bytes('ai/multimap/' + name, revision)
    require(no_links(HERE / name).read_bytes() == raw, 'Helper/source differs from immutable Git: ' + name)
    require(checksum is None or sha(raw) == checksum, 'Helper hash mismatch')
    if name.endswith('.py'):
        authenticate_bytecode(HERE / name, raw)
    return raw


def helpers():
    # Authenticate ALL bytes before executing even the first helper import.
    names = ('audit_replica_stress_v1', 'audit_neural', 'audit_gap')
    sources = {name: authenticate_file(name + '.py') for name in names}
    result = {}
    for name, raw in sources.items():
        module = ModuleType(name)
        module.__file__ = str(HERE / (name + '.py'))
        # Private modules bypass cached/preloaded helper namespaces altogether.
        exec(compile(raw, module.__file__, 'exec', dont_inherit=True), module.__dict__)
        result[name] = module
    return result


def authenticated_decoder():
    """Execute the pinned adapter bytes privately, never sys.modules' decoder.

    Its frozen launcher dependency is authenticated by runtime_import_guard before
    this is called. Retain this same private namespace for final revalidation.
    """
    name = 'reconcile_replica_stress_jobs_v1'
    raw = authenticate_file(name + '.py', DECODER_GIT, DECODER_SHA)
    module = ModuleType(name)
    module.__file__ = str(HERE / (name + '.py'))
    exec(compile(raw, module.__file__, 'exec', dont_inherit=True), module.__dict__)
    return module


def local_source_difference(name, archived, local):
    if archived == local:
        return None
    require(name in {'ai/multimap/README.md', 'ai/multimap/runs.json',
                     'ai/multimap/replica-stress-v1-design.md'}, 'Frozen serving/source drift: ' + name)
    return dict(sourceSha256=archived, localSha256=local, note='Nonserving bookkeeping only')


def source_verifier(neural, config):
    # Explicit revision in the replacement also avoids the old default-argument trap.
    return bind(neural.verify_source, ROOT=ROOT, HERE=HERE, SOURCE=SOURCE,
                SOURCE_NAMES=set(config['sourceFiles']), LIMIT=SOURCE_LIMIT,
                git_bytes=lambda name: git_bytes(name, SOURCE),
                local_source_difference=local_source_difference)


def cache_file(path, cache_root=None):
    """Only HF snapshots -> blobs links within the declared repository cache."""
    path = lexical_path(path)
    if cache_root is not None:
        cache_root = no_links(cache_root)
    if not any(p.is_symlink() for p in (path, *path.parents)):
        require(path.is_file(), 'Missing retained payload; explicit fetch required')
        return path
    require(cache_root is not None, 'Unscoped cache symlink')
    root = no_links(cache_root)
    resolved = path.resolve(strict=True)
    require(path.is_relative_to(root) and resolved.is_relative_to(root) and
            path.is_relative_to(root / 'snapshots') and resolved.is_relative_to(root / 'blobs') and
            not any(p.is_symlink() for p in path.parents) and resolved.is_file(), 'Escaping/non-HF cache link')
    return no_links(resolved)


class RetainedRemote:
    """Compose the frozen <=128 MiB RemoteFiles collector, never raise its limit.

    Separate instances bound panel/source/preflight/models; their accounted byte
    totals are retained in the common report. No fallback from a cache miss.
    """
    def __init__(self, api, neural, *, download=False):
        require(type(download) is bool, 'Boolean download permission required')
        self.inner = neural.RemoteFiles(api)
        self.api, self.download = api, download

    @property
    def evidence(self):
        return self.inner.evidence

    def describe(self, pin):
        immutable(pin['revision'])
        safe_name(pin['path'])
        return self.inner.describe(pin)

    def get(self, pin, metadata=None, cached=None):
        if cached is None:
            from huggingface_hub import try_to_load_from_cache
            from huggingface_hub.constants import HF_HUB_CACHE
            candidate = try_to_load_from_cache(pin['repo'], pin['path'], revision=pin['revision'],
                                               repo_type=pin.get('repo_type', 'model'))
            if isinstance(candidate, str):
                kind = 'datasets' if pin.get('repo_type') == 'dataset' else 'models'
                root = Path(HF_HUB_CACHE) / (kind + '--' + pin['repo'].replace('/', '--'))
                cached = cache_file(candidate, root)
            else:
                require(self.download, 'Missing retained payload; no implicit download fallback')
        else:
            cached = cache_file(cached)
        result = self.inner.get(pin, metadata=metadata, cached=cached)
        if cached is None:
            from huggingface_hub.constants import HF_HUB_CACHE
            kind = 'datasets' if pin.get('repo_type') == 'dataset' else 'models'
            root = Path(HF_HUB_CACHE) / (kind + '--' + pin['repo'].replace('/', '--'))
            result = cache_file(result, root)
        return Path(result)


def manifest_names(manifest):
    required = {'protocol.json', 'status.json', 'environment.json', 'recovery.json', 'study/plan.json'}
    require(type(manifest) is dict and required <= set(manifest), 'Missing snapshot metadata')
    batches = sorted(n for n in manifest if n.startswith('study/batch-'))
    require(len(batches) <= 640 and batches == [f'study/batch-{i:03}.json' for i in range(len(batches))],
            'Noncontiguous/invalid whole batch prefix')
    allowed = required | set(batches) | ({'study/summary.json'} if len(batches) == 640 else set())
    require(set(manifest) <= allowed, 'Unknown/temporary snapshot member or premature summary')
    for name, checksum in manifest.items():
        safe_name(name)
        immutable(checksum, 64)
    return batches


def restore_safety(base, allowed):
    base = no_links(base)
    if not base.exists():
        return
    require(base.is_dir(), 'Restore root must be a directory')
    dirs = {str(p) for n in allowed for p in PurePosixPath(n).parents if str(p) != '.'}
    for p in base.rglob('*'):
        name = p.relative_to(base).as_posix()
        require(not p.is_symlink() and ((p.is_file() and name in allowed) or (p.is_dir() and name in dirs)),
                'Unexpected/linked restored member')


def metadata_tree(remote, repo, revision, prefix, *, maximum=LIMIT, count=647):
    """Enumerate and describe EVERY member before reading even the manifest."""
    immutable(revision)
    safe_name(prefix.rstrip('/'))
    entries = {}
    dirs = set()
    for entry in remote.api.list_repo_tree(repo, path_in_repo=prefix.rstrip('/'), revision=revision, recursive=True):
        require(entry.path.startswith(prefix), 'Remote prefix escape')
        name = entry.path[len(prefix):]
        safe_name(name)
        if not hasattr(entry, 'blob_id'):
            require(name not in dirs and len(dirs) < count, 'Remote directory overflow/duplicate')
            dirs.add(name)
            continue
        require(name not in entries and len(entries) < count, 'Remote member overflow/duplicate')
        require(type(entry.size) is int and 0 < entry.size <= FILE_LIMIT, 'Remote member size bound')
        entries[name] = entry
    require(entries and sum(e.size for e in entries.values()) <= maximum, 'Aggregate metadata bound before transfer')
    require(dirs <= {str(p) for n in entries for p in PurePosixPath(n).parents if str(p) != '.'}, 'Unexpected remote directory')
    for name, entry in entries.items():
        immutable(entry.blob_id)
        if entry.lfs:
            immutable(entry.lfs.sha256, 64)
            require(type(entry.lfs.size) is int and entry.lfs.size == entry.size, 'LFS size')
            pointer = (f'version https://git-lfs.github.com/spec/v1\noid sha256:{entry.lfs.sha256}\nsize {entry.size}\n').encode()
            require(hashlib.sha1(b'blob ' + str(len(pointer)).encode() + b'\0' + pointer).hexdigest() == entry.blob_id,
                    'LFS pointer Git blob')
        meta = remote.describe(dict(repo=repo, revision=revision, path=prefix + name))
        require(meta.size == entry.size and meta.blob_id == entry.blob_id and
                (meta.lfs.sha256 if meta.lfs else None) == (entry.lfs.sha256 if entry.lfs else None), 'Remote tree/HEAD metadata disagreement')
    return entries


def authenticate_snapshot(panel, revision, base, remote, *, segment=1, download=False):
    require(panel in PANELS and type(segment) is int and segment in (1, 2), 'Fixed panel/segment required')
    immutable(revision)
    run = GROUP + ('-' if segment == 1 else '-recovery-') + panel
    prefix = 'runs/' + run + '/'
    entries = metadata_tree(remote, REPO, revision, prefix)
    require('artifacts.json' in entries and entries['artifacts.json'].size <= MANIFEST_LIMIT, 'Manifest bound')
    base = no_links(base)
    # Inspect local tree before get/copy; never write through unexpected links.
    restore_safety(base, set(entries))
    def get(name, checksum=None):
        local = base / name
        require(download or local.is_file(), 'Local panel incomplete; explicit fetch required')
        pin = dict(repo=REPO, revision=revision, path=prefix + name)
        if checksum:
            pin['sha256'] = checksum
        return remote.get(pin, metadata=entries[name], cached=local if local.exists() else None)
    manifest_path = get('artifacts.json')
    manifest = read(manifest_path, MANIFEST_LIMIT)
    batches = manifest_names(manifest)
    require(set(entries) == set(manifest) | {'artifacts.json'}, 'Exact remote inventory required')
    for name, checksum in manifest.items():
        entry = entries[name]
        require(not entry.lfs or entry.lfs.sha256 == checksum, 'Manifest/LFS disagreement')
    hashes = dict(manifest, **{'artifacts.json': digest(manifest_path)})
    for name, checksum in sorted(hashes.items()):
        src = manifest_path if name == 'artifacts.json' else get(name, checksum)
        require(digest(src) == checksum, 'Panel member hash mismatch')
        dst = no_links(base / name)
        if not dst.exists():
            require(download, 'No implicit restore')
            dst.parent.mkdir(parents=True, exist_ok=True)
            with dst.open('xb') as out, src.open('rb') as stream:
                shutil.copyfileobj(stream, out)
        require(digest(dst) == checksum, 'Restored content mismatch')
    restore_safety(base, set(hashes))
    require({p.relative_to(base).as_posix() for p in base.rglob('*') if p.is_file()} == set(hashes), 'Exact local inventory')
    return dict(panel=panel, revision=revision, run=run, segment=segment, manifestSha256=hashes['artifacts.json'],
                files=hashes, bytes=sum(e.size for e in entries.values()), batches=len(batches),
                complete=len(batches) == 640 and 'study/summary.json' in manifest,
                remoteEvidence=copy.deepcopy(remote.evidence))


def retained_experts():
    return {
        'expert24': ROOT / 'ai/runs/multimap-expert-ppo-20261102-v2-r1/audit/restored/expert/best.pt',
        'replica1': ROOT / 'ai/runs/multimap-expert-replicas-20261109-v1-continuation-r1/audit/restored/expert/best.pt',
        'replica2': ROOT / 'ai/runs/multimap-expert-replicas-20261109-v1-continuation-r2/audit/restored/expert/best.pt',
    }


def protect_output(output, *inputs):
    output = no_links(output)
    home = Path(os.environ.get('HF_HOME', str(Path(os.environ.get('XDG_CACHE_HOME', str(Path.home() / '.cache'))) / 'huggingface')))
    cache = Path(os.environ.get('HF_HUB_CACHE', os.environ.get('HUGGINGFACE_HUB_CACHE', str(home / 'hub'))))
    protected = [ROOT / 'ai/runs/multimap-reference-preflight-v1', ROOT / 'ai/.venv-reference', ROOT / 'ai/.venv',
                 ROOT / 'ai/runs' / GROUP, ROOT / 'ai/runs' / (GROUP + '-preflight'), ATTEMPT_ROOT, cache,
                 *(p.parent for p in retained_experts().values()), *inputs]
    for path in protected:
        if path is None:
            continue
        retained = no_links(path)
        require(output != retained and output not in retained.parents and retained not in output.parents,
                'Output must not overlap retained caches/reference/preflight/ledger/inputs')
    return output


def storage_budget():
    used = sum(p.stat().st_size for root in (ROOT / 'ai/runs').glob('multimap-*')
               for p in root.rglob('*') if p.is_file())
    reserve = 1024**3
    free = shutil.disk_usage(ROOT).free
    require(used + reserve <= 8_000_000_000 and free >= 2 * 1024**3 + reserve,
            'Existing 8 GB ceiling / 2 GiB free + 1 GiB reserve; never delete retained evidence')
    return dict(localRunCacheBytes=used, freeBytes=free, reservedBytes=reserve, limitBytes=8_000_000_000)


def fetch_panel(panel, immutable_revision, output, *, allow_download=False, segment=1, api=None):
    require(allow_download is True, 'Explicit --allow-download required')
    output = protect_output(output)
    storage_budget()
    h = helpers()
    if api is None:
        from huggingface_hub import HfApi
        api = HfApi()
    remote = RetainedRemote(api, h['audit_neural'], download=True)
    result = authenticate_snapshot(panel, immutable_revision, Path(output) / 'restored', remote,
                                   segment=segment, download=True)
    write_new(Path(output) / 'fetch-evidence.json', result)
    return result


def fetch_preflight(output, *, allow_download=False, api=None):
    """Optional explicit bounded recovery of the 58 preflight evidence files."""
    require(allow_download is True, 'Explicit --allow-download required')
    output = protect_output(output)
    storage_budget()
    h = helpers()
    preflight = decode_json(authenticate_file('replica-stress-preflight-v1.json'))
    pin = preflight['privateEvidence']
    if api is None:
        from huggingface_hub import HfApi
        api = HfApi()
    remote = RetainedRemote(api, h['audit_neural'], download=True)
    entries = metadata_tree(remote, REPO, pin['revision'], pin['prefix'] + '/', count=58)
    require(set(entries) == set(pin['files']) and sum(e.size for e in entries.values()) == pin['bytes'] == 5804466,
            'Exact preflight metadata inventory/budget')
    base = output / 'restored'
    restore_safety(base, set(pin['files']))
    for name, checksum in pin['files'].items():
        destination = no_links(base / name)
        source = remote.get(dict(repo=REPO, revision=pin['revision'], path=pin['prefix'] + '/' + name, sha256=checksum),
                            metadata=entries[name], cached=destination if destination.exists() else None)
        if not destination.exists():
            destination.parent.mkdir(parents=True, exist_ok=True)
            with destination.open('xb') as out, source.open('rb') as stream:
                shutil.copyfileobj(stream, out)
        require(digest(destination) == checksum, 'Restored preflight payload hash')
    result = dict(revision=pin['revision'], files=pin['files'], bytes=pin['bytes'], remoteEvidence=remote.evidence)
    write_new(output / 'fetch-evidence.json', result)
    return result


def runtime_import_guard(*, reject_preloaded=True):
    names = subprocess.check_output(['git', 'ls-tree', '-r', '--name-only', SOURCE, 'ai/multimap'],
                                    cwd=ROOT, text=True).splitlines()
    for name in names:
        if not name.endswith('.py'):
            continue
        path = ROOT / name
        raw = no_links(path).read_bytes()
        require(raw == git_bytes(name, SOURCE), 'Runtime Python source differs before import')
        authenticate_bytecode(path, raw)
        module_name = path.stem
        if reject_preloaded and not module_name.startswith(('audit_', 'test_', 'preflight_')):
            require(module_name not in sys.modules, 'Use a fresh auditor process; preloaded serving module forbidden: ' + module_name)


def authenticate_source(archive, preflight, remote, neural):
    archive = no_links(archive)
    require(archive.is_file() and archive.stat().st_size == 49988970 and digest(archive) == SOURCE_SHA,
            'Original compressed source pin')
    pin = dict(repo=DATASET, repo_type='dataset', revision=SOURCE_REVISION, path=SOURCE_PATH, sha256=SOURCE_SHA)
    metadata = remote.describe(pin)
    require(metadata.size == 49988970 and metadata.size < 128 * 1024**2, 'Source compressed metadata limit')
    remote.get(pin, metadata=metadata, cached=archive)
    # Bound before getmembers/full verification. This archive is already hash pinned.
    with tarfile.open(archive, 'r:gz') as tf:
        members = tf.getmembers()
        require(len(members) == 1428 and sum(m.size for m in members) == 137556136 <= SOURCE_LIMIT,
                'Exact original expanded archive size/member count')
    config = preflight['smokeIdentities']['strong']['modelProvenance']['expert24']['config']
    report = source_verifier(neural, config)(archive, config)
    require(report['manifestFiles'] == 1404, 'Complete original manifest')
    for name in (*SOURCE_NAMES, 'replica-stress-preflight-v1.json'):
        authenticate_file(name)
    require(digest(HERE / 'replica-stress-preflight-v1.json') ==
            '780d8ee78fca181318b0eab45e361d2b55e5d9db9e525276c357c241d5e7d192', 'Frozen preflight bytes')
    return dict(report, compressedBytes=49988970, expandedBytes=137556136, members=1428,
                sourceGit=SOURCE, sourceRevision=SOURCE_REVISION, sourceSha256=SOURCE_SHA,
                remoteEvidence=copy.deepcopy(remote.evidence))


def verify_preflight(preflight, root, remote, audit, study):
    pin = preflight['privateEvidence']
    require(pin['repo'] == REPO and pin['revision'] == '1d859ae85fb8a9ac1dbe4dd68d1df9efdd741e14' and
            pin['prefix'] == 'diagnostics/replica-stress-v1-preflight' and pin['bytes'] == 5804466,
            'Private preflight immutable pin')
    names = pin['files']
    require(len(names) == 58, 'Complete private preflight')
    entries = metadata_tree(remote, REPO, pin['revision'], pin['prefix'] + '/', count=58)
    require(set(entries) == set(names) and sum(e.size for e in entries.values()) == pin['bytes'], 'Exact preflight inventory/size')
    root = no_links(root)
    paths = {}
    for name, checksum in names.items():
        safe_name(name)
        local = HERE / name.removeprefix('source/') if name.startswith('source/') else root / name
        paths[name] = remote.get(dict(repo=REPO, revision=pin['revision'], path=pin['prefix'] + '/' + name,
                                      sha256=checksum), metadata=entries[name], cached=local if local.is_file() else None)
    archived = read(paths['report.json'])
    require('privateEvidence' not in archived and all(preflight.get(k) == v for k, v in archived.items()), 'Archived preflight report')
    for name in SOURCE_NAMES:
        require(digest(paths['source/' + name]) == sha(git_bytes('ai/multimap/' + name, SOURCE)), 'Preflight source hash')
    matches = 0
    for panel in PANELS:
        outcomes = []
        for mode in ('uninterrupted', 'resumed'):
            prefix = panel + '-' + mode + '/'
            plan = read(paths[prefix + 'plan.json'])
            exact(plan, preflight['smokeIdentities'][panel], 'Preflight full identity')
            exact(plan['tasks'], audit.expected_tasks(panel, smoke=True), 'Independent preflight tasks')
            games = []
            for i, tasks in enumerate(audit.expected_batches(panel, smoke=True)):
                games.extend(audit.verify_batch(read(paths[prefix + f'batch-{i:03}.json']), i, tasks))
            require(len(games) == 99, 'Preflight terminal count')
            exact(read(paths[prefix + 'summary.json']), study.analyze(games, panel, True), 'Preflight summary')
            outcomes.append([{k: v for k, v in g.items() if k not in TIMINGS} for g in games])
        exact(outcomes[0], outcomes[1], 'Actual preflight replay outcomes')
        matches += len(outcomes[0])
    require(matches == 198, 'Preflight comparison count')
    return dict(revision=pin['revision'], files=58, bytes=pin['bytes'], terminals=396, exactMatches=matches,
                privateReportSha256=digest(paths['report.json']), remoteEvidence=copy.deepcopy(remote.evidence),
                note='Preflight suites are separate evidence, NOT worker startup tests.')


def checkpoint_projection(saved, pin, config, *, expert):
    """Projection is extracted from DECODED fields after independent validation."""
    keys = {'schema', 'width', 'bound', 'state_dict', 'update', 'config'}
    if expert:
        keys |= {'stage', 'priorAsActionFeature'}
    require(type(saved) is dict and set(saved) == keys, 'Exact checkpoint schema/keys')
    expected = dict(schema='multimap-expert-ppo-v2' if expert else 'multimap-residual-ppo-v1',
                    width=64, bound=16 if expert else 8, update=pin['update'])
    if expert:
        expected.update(stage='train', priorAsActionFeature=True)
    for name, value in expected.items():
        require(type(saved[name]) is type(value) and saved[name] == value, 'Decoded architecture/update: ' + name)
    exact(saved['config'], config, 'Complete actual saved config')
    return dict(pin=copy.deepcopy(pin), configSha256=object_sha(saved['config']),
                **{name: saved[name] for name in expected})


def verify_historical(audit, provenance):
    historical = audit.PPO0_HISTORICAL_TRAINING
    # The frozen protocol really uses a 40-character Git SHA (do not guess a suffix).
    for name, checksum in historical['sourceFiles'].items():
        require(sha(git_bytes('ai/multimap/' + name, historical['sourceGit'])) == checksum, 'Historical PPO0 Git object')
    current = provenance['ppo0']['config']
    saved = provenance['ppo0']['checkpointConfig']
    exact(provenance['ppo0']['historicalTrainingSource'], historical, 'PPO0 historical source provenance')
    exact(saved, dict(current, sourceFiles=historical['sourceFiles']), 'Only pinned historical sourceFiles exception')
    differences = []
    for name, checksum in current['sourceFiles'].items():
        require(digest(no_links(HERE / name)) == checksum, 'Current PPO0 source hash')
        if historical['sourceFiles'][name] != checksum:
            differences.append(name)
    exact(sorted(differences), ['ppo.py', 'rollout.py'], 'Exactly two historical training-only differences')
    return dict(sourceGit=historical['sourceGit'], files=11, differingNonservingSources=sorted(differences))


def model_fingerprint(models, *, validate=True):
    """All tensors, modes, grad flags, roles and root serving width/bound/class.

    The explicit configuration is not in state_dict: a changed bound alters the
    policy even when every tensor and mode is identical. Authenticated source and
    these frozen root attributes are the boundary, not hostile Python patching.
    """
    result = {}
    for name, model in models.items():
        tensors = {}
        for key, tensor in model.state_dict().items():
            t = tensor.detach().cpu().contiguous()
            tensors[key] = dict(shape=list(t.shape), dtype=str(t.dtype), sha256=sha(t.numpy().tobytes()))
        configuration = dict(width=getattr(model, 'width', None), bound=getattr(model, 'bound', None),
                             modelClass=type(model).__module__ + '.' + type(model).__qualname__)
        result[name] = dict(tensors=tensors, modules={k: m.training for k, m in model.named_modules()},
                            requiresGrad={k: p.requires_grad for k, p in model.named_parameters()},
                            role=getattr(model, '_replica_stress_role', None), servingConfiguration=configuration)
        if validate:
            require(type(configuration['width']) is int and configuration['width'] == 64 and
                    type(configuration['bound']) is int and configuration['bound'] == (16 if name in EXPERTS else 8) and
                    configuration['modelClass'] == MODEL_CLASSES.get(name), 'Frozen root serving configuration width/bound/class')
            require(not any(result[name]['modules'].values()) and not any(result[name]['requiresGrad'].values()) and
                    result[name]['role'] == name, 'Evaluation-only distinct model roles')
    if validate:
        require(set(models) == set(MODELS) and len({id(m) for m in models.values()}) == 6, 'Six nonaliased models')
    return result


def validate_tensor_state(state, expected, torch_api):
    require(isinstance(state, dict) and state.keys() == expected.keys(), 'Full tensor key coverage')
    for key, template in expected.items():
        tensor = state[key]
        require(isinstance(tensor, torch_api.Tensor) and tensor.device.type == 'cpu' and
                tensor.dtype == template.dtype and tensor.shape == template.shape and
                torch_api.isfinite(tensor).all().item(), 'Finite CPU tensor shape/dtype: ' + key)


def decode_models(remote, audit, provenance, local_checkpoints=None):
    local_checkpoints = {} if local_checkpoints is None else local_checkpoints
    require(type(local_checkpoints) is dict and set(local_checkpoints) <= set(EXPERTS), 'Explicit copies are expert-family only')
    local_checkpoints = dict(retained_experts(), **local_checkpoints)
    require(all(no_links(p).is_file() for p in local_checkpoints.values()), 'Required retained expert-family copies missing')
    # All six remote metadata checks must finish BEFORE any get or torch.load.
    metadata = {name: remote.describe(audit.MODEL_PINS[name]) for name in MODELS}
    require(all(type(m.size) is int and 0 < m.size <= FILE_LIMIT for m in metadata.values()) and
            sum(m.size for m in metadata.values()) <= 96 * 1024**2, 'Six-model metadata byte limits')
    paths = {name: remote.get(audit.MODEL_PINS[name], metadata=metadata[name], cached=local_checkpoints.get(name))
             for name in MODELS}
    import torch
    from expert_policy import ExpertPolicy
    from residual import ResidualPolicy
    models, projections = {}, {}
    python_rng = random.getstate()
    try:
        with torch.random.fork_rng(devices=[]):
            for name in MODELS:
                path, expert = paths[name], name in EXPERTS
                require(digest(path) == audit.MODEL_PINS[name]['sha256'], 'Immutable checkpoint bytes')
                saved = torch.load(path, weights_only=True, map_location='cpu')
                config = provenance[name]['checkpointConfig' if name == 'ppo0' else 'config']
                projections[name] = checkpoint_projection(saved, audit.MODEL_PINS[name], config, expert=expert)
                model = ExpertPolicy(64, 16) if expert else ResidualPolicy(64, 8)
                state, expected = saved['state_dict'], model.state_dict()
                validate_tensor_state(state, expected, torch)
                model.load_state_dict(state, strict=True)
                model.eval().requires_grad_(False)
                model._replica_stress_role = name
                models[name] = model
    finally:
        random.setstate(python_rng)
    fingerprint = model_fingerprint(models)
    return models, dict(projection=projections, fingerprint=fingerprint,
                        paths={n: str(p) for n, p in paths.items()},
                        metadataBytes=sum(m.size for m in metadata.values()), remoteEvidence=copy.deepcopy(remote.evidence))


def verify_runtime(panel, root, preflight, study, gap, reference_remote):
    artifact = no_links(ROOT / 'ai/runs/multimap-reference-preflight-v1/artifact')
    reference_python = ROOT / 'ai/.venv-reference/bin/python'
    rebuilt = study.identity(panel, False, 6, artifact, reference_python)
    expected = copy.deepcopy(preflight['smokeIdentities'][panel])
    expected.update(smoke=False, tasks=study.plan(panel, False))
    exact(rebuilt, expected, 'Full current identity vs frozen preflight')
    exact(read(root / 'study/plan.json'), rebuilt, 'Full committed runtime identity')
    environment, recovery = read(root / 'environment.json'), read(root / 'recovery.json')
    config = rebuilt['modelProvenance']['expert24']['config']
    protocol = config['protocol']
    exact(environment['versions'], config['runtimeVersions'], 'Actual principal runtime versions')
    require(environment['requirementsSha256'] == protocol['referenceRequirementsSha256'] and
            type(environment['referenceVenvBytes']) is int and 0 < environment['referenceVenvBytes'] <= protocol['referenceVenvMaxBytes'],
            'Recorded reference requirements/budget')
    reference = gap.verify_reference(dict(protocol, compressedArchiveRamMaxBytes=128 * 1024**2), recovery, reference_remote)
    venv_bytes = sum(p.stat().st_size for p in reference_python.parent.parent.rglob('*') if p.is_file())
    require(venv_bytes <= protocol['referenceVenvMaxBytes'], 'Retained reference venv size')
    return rebuilt, dict(environment=environment, reference=reference, referenceVenvBytes=venv_bytes,
                         note='Principal versions and complete packaged bytes; not a full transitive Python dependency lock.')


def timestamp(value):
    require(isinstance(value, (str, datetime)), 'Authenticated chronology timestamp required')
    value = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
    require(value.tzinfo is not None, 'Timezone-aware chronology required')
    return value.astimezone(timezone.utc)


def chronology(raw):
    # This is separate from the frozen decoder, not a raw JobInfo serialization.
    result = {}
    for key in ('createdAt', 'startedAt', 'finishedAt'):
        value = raw.get(key)
        result[key] = timestamp(value).isoformat() if value is not None else None
    require(result['createdAt'] is not None, 'Actual createdAt required')
    if result['startedAt']:
        require(timestamp(result['createdAt']) <= timestamp(result['startedAt']), 'Created/start chronology')
    if result['finishedAt']:
        require(result['startedAt'] is not None and timestamp(result['startedAt']) <= timestamp(result['finishedAt']), 'Start/finish chronology')
    return result


def inspect_with_chronology(api, job_id, decoder):
    require(type(job_id) is str and re.fullmatch('[A-Za-z0-9_-]+', job_id), 'Unsafe job ID')
    from huggingface_hub.utils import get_session, hf_raise_for_status
    try:
        response = get_session().get(f'{api.endpoint}/api/jobs/coyotte508/{job_id}',
                                     headers=api._build_hf_headers(), timeout=30)
        hf_raise_for_status(response)
        raw = response.json()
    except Exception:
        raise ValueError('Authenticated actual job metadata unavailable') from None
    return decoder.decode_actual(raw), chronology(raw)


def ledger_attempts(directory):
    """Unknown slots consume hours, even if inventory is empty. Never free one."""
    directory = no_links(directory)
    intents, receipts, hashes = {}, {}, {}
    for kind, target in (('intents', intents), ('receipts', receipts)):
        root = no_links(directory / kind)
        if not root.exists():
            continue
        for p in root.iterdir():
            require(p.name in {n + '.json' for n in HOURS} and p.is_file() and not p.is_symlink(), 'Unexpected ledger entry')
            target[p.stem] = read(p, 4 * 1024**2)
            hashes[kind + '/' + p.name] = digest(p)
    require(set(receipts) <= set(intents), 'Receipt without intent')
    return dict(attemptedSlots=[n for n in HOURS if n in intents], requestedHours=sum(HOURS[n] for n in intents),
                unknownSlots=[n for n in HOURS if n in intents and n not in receipts],
                hashes=hashes), intents, receipts


def production_events(log, *, startup_suite=None):
    """Generic legacy fixture support needs a REAL successful suite boundary.

    Production replica-stress always passes None: its authenticated bootstrap
    contains no startup suites. Never invent an old 34/7 or 45/10 boundary.
    """
    require(type(log) is str and 0 < len(log.encode()) <= LOG_LIMIT, 'Bounded nonempty logs')
    if startup_suite is not None:
        require(type(startup_suite) is dict and set(startup_suite) == {'python', 'node'} and
                all(type(v) is int and v > 0 for v in startup_suite.values()), 'Explicit legacy startup suite')
        matches = list(re.finditer(r'^Ran ' + str(startup_suite['python']) + r' tests in [^\n]+\n\s*\n?OK(?:\n|$)', log, re.M))
        require(len(matches) == 1, 'Unique successful Python startup boundary')
        before = log[:matches[0].end()]
        require(re.search(r'(?:#|ℹ) tests ' + str(startup_suite['node']) + r'\b', before) and
                re.search(r'(?:#|ℹ) pass ' + str(startup_suite['node']) + r'\b', before) and
                re.search(r'(?:#|ℹ) fail 0\b', before), 'Successful Node startup suite')
        log = log[matches[0].end():]
    else:
        require(not re.search(r'^Ran \d+ tests in |(?:#|ℹ) tests \d+', log, re.M), 'Unexpected startup test boundary in new worker')
    events = []
    for line in log.splitlines():
        if line.lstrip().startswith('{'):
            event = decode_json(line)
            require(type(event) is dict and 'stage' in event, 'Unrecognized structured production event')
            events.append(event)
    require(events, 'Production events missing')
    return events


def startup_source_proof():
    launcher = authenticate_file('launch_replica_stress_v1.py')
    worker = authenticate_file('job_replica_stress_v1.py')
    tree = ast.parse(launcher)
    bootstraps = [ast.literal_eval(node.value) for node in tree.body if isinstance(node, ast.Assign) and
                  any(isinstance(t, ast.Name) and t.id == 'BOOTSTRAP' for t in node.targets)]
    require(len(bootstraps) == 1, 'Literal frozen bootstrap required')
    require('unittest' not in bootstraps[0] and '--test' not in bootstraps[0] and
            'unittest' not in worker.decode() and '--test' not in worker.decode(), 'Unexpected frozen startup suite')
    return dict(launcherSha256=sha(launcher), workerSha256=sha(worker), startupTestsInvoked=False,
                boundary='unique production uploaded/runtime-ready; preflight suites are separate')


def verify_log(log, panel, status, revision, job_stage, audit):
    require(job_stage in ('COMPLETED', 'ERROR', 'CANCELED'), 'Unknown/nonterminal job cannot pass final audit')
    events = production_events(log)
    inherited = status.get('resume', {}).get('transaction', {}).get('committedBatches', 0)
    require(type(inherited) is int and 0 <= inherited < 640, 'Inherited batch boundary')
    groups = audit.expected_batches(panel)
    expected, cumulative = [], sum(len(b) for b in groups[:inherited])
    expected.append(('uploaded', 'runtime-ready'))
    for i in range(inherited, 640):
        cumulative += len(groups[i])
        if (i + 1) % 16 == 0:
            expected.append(('uploaded', 'batches-' + str(i + 1)))
        expected.append(('replica-stress-batch', i + 1))
    sequence, uploads = [], []
    for event in events:
        stage = event['stage']
        if stage == 'uploaded':
            require(set(event) == {'stage', 'label', 'revision'}, 'Upload schema')
            immutable(event['revision'])
            sequence.append((stage, event['label']))
            uploads.append(dict(stage=event['label'], revision=event['revision']))
        elif stage == 'replica-stress-batch':
            require(set(event) == {'stage', 'panel', 'batches', 'totalBatches', 'games'} and event['panel'] == panel and
                    type(event['batches']) is int and inherited < event['batches'] <= 640 and
                    type(event['games']) is int and event['games'] == sum(len(b) for b in groups[:event['batches']]) and
                    type(event['totalBatches']) is int and event['totalBatches'] == 640, 'Independent cumulative whole batch counts')
            sequence.append((stage, event['batches']))
        elif stage == 'complete':
            exact(event, dict(stage='complete', run=status['run'], panel=panel, games=7680, qualified=False), 'Worker complete event')
            sequence.append(('complete', None))
        else:
            raise ValueError('Unexpected optimization/selection/production event')
    exact(sequence[:len(expected)], expected, 'Exact ordered runtime-ready/batch/upload sequence')
    tail = sequence[len(expected):]
    normal = [('uploaded', 'complete'), ('uploaded', 'complete'), ('complete', None)]
    if job_stage == 'COMPLETED':
        exact(tail, normal, 'Normal completion has TWO complete uploads')
    else:
        allowed = ([('uploaded', 'complete')], [('uploaded', 'complete'), ('uploaded', 'complete')], normal)
        require(tail in allowed or tail[:-1] in allowed and tail[-1:] == [('uploaded', 'failed')],
                'Terminal failure requires genuinely complete outputs/upload, not assumed success')
    require(len({u['revision'] for u in uploads}) == len(uploads), 'Duplicate upload revisions')
    matches = [i for i, u in enumerate(uploads) if u['revision'] == revision]
    require(len(matches) == 1, 'Snapshot not in authenticated job upload chain')
    index = matches[0]
    chosen = uploads[index]
    require(chosen['stage'] == status['stage'], 'Snapshot stage/upload label mismatch')
    require(index == len(uploads)-1 or job_stage != 'COMPLETED' and chosen['stage'] == 'complete', 'Nonfinal snapshot requires honest terminal failure')
    exact(status['receipts'], uploads[:index], 'Status receipts lag their own immutable upload')
    return dict(jobStage=job_stage, logSha256=sha(log.encode()), logBytes=len(log.encode()),
                uploads=uploads, snapshotUploadIndex=index, inheritedBatches=inherited,
                generatedBatches=640-inherited, terminalFailure=job_stage != 'COMPLETED',
                startupTestsInvoked=False, independentNewObservations=0)


def verify_prefix_log(log, panel, status, revision, committed, audit):
    """Timeout-only original: whole uploaded prefix plus possibly killed work.

    Printing follows upload on multiples of 16, so termination between those
    lines is legitimate. Unuploaded printed work is not an independent sample.
    """
    require(type(committed) is int and 0 <= committed < 640, 'Incomplete original prefix required')
    events = production_events(log)
    groups = audit.expected_batches(panel)
    uploads, printed, position = [], 0, 0
    def upload(label):
        nonlocal position
        require(position < len(events), 'Missing original upload event')
        event = events[position]
        require(set(event) == {'stage', 'label', 'revision'} and event['stage'] == 'uploaded' and
                event['label'] == label, 'Original ordered publication boundary')
        uploads.append(dict(stage=label, revision=immutable(event['revision'])))
        position += 1
    upload('runtime-ready')
    for i, tasks in enumerate(groups):
        if position == len(events):
            break
        if (i+1) % 16 == 0:
            upload('batches-' + str(i+1))
            if position == len(events):
                break
        event = events[position]
        exact(event, dict(stage='replica-stress-batch', panel=panel, batches=i+1, totalBatches=640,
                          games=sum(len(b) for b in groups[:i+1])), 'Original printed whole-batch sequence')
        printed += 1
        position += 1
    require(position == len(events), 'Unexpected original optimization/completion event')
    require(len({u['revision'] for u in uploads}) == len(uploads), 'Duplicate original upload revision')
    require(uploads[-1]['revision'] == revision and uploads[-1]['stage'] == status['stage'],
            'Timeout snapshot must bind latest authenticated original upload')
    exact(status['receipts'], uploads[:-1], 'Original status receipt lag')
    boundary = 0 if uploads[-1]['stage'] == 'runtime-ready' else int(uploads[-1]['stage'].split('-')[1])
    require(boundary == committed and printed >= max(0, committed-1), 'Original committed boundary versus log')
    return dict(logSha256=sha(log.encode()), logBytes=len(log.encode()), uploads=uploads,
                committedBatches=committed, printedBatches=printed,
                unuploadedPrintedBatches=max(0, printed-committed), additionalStrengthObservations=0)


def bounded_log(lines):
    parts, size = [], 0
    for item in lines:
        line = item if isinstance(item, str) else getattr(item, 'log', None)
        require(type(line) is str, 'Unexpected job log API item')
        line = line if line.endswith('\n') else line + '\n'
        size += len(line.encode())
        require(size <= LOG_LIMIT, 'Job log byte budget')
        parts.append(line)
    return ''.join(parts)


def verify_inherited(original, final, old_manifest, final_manifest, transaction):
    names = manifest_names(old_manifest)
    count = len(names)
    require(count < 640 and 'study/summary.json' not in old_manifest, 'Complete original cannot be replayed after error')
    require(transaction['committedBatches'] == count and transaction['complete'] is False and
            transaction['planSha256'] == old_manifest['study/plan.json'], 'Inherited transaction boundary')
    files = ['study/plan.json', *names]
    for name in files:
        require(digest(no_links(Path(original) / name)) == old_manifest[name] ==
                final_manifest.get(name) == digest(no_links(Path(final) / name)), 'Inherited RAW bytes changed, including timings')
    return {name: old_manifest[name] for name in files}


def recovery_choice(initial, audits, created_at):
    for panel in PANELS:
        job = initial[panel]
        require(job['stage'] in ('COMPLETED', 'ERROR', 'CANCELED') and job['finishedAt'] is not None and
                timestamp(job['finishedAt']) < timestamp(created_at), 'Both originals must be terminal BEFORE recovery paid request')
    incomplete = [p for p in PANELS if not audits[p]['transaction']['complete']]
    require(incomplete, 'No recovery of complete outputs, including complete-after-error')
    for p in incomplete:
        require(initial[p]['stage'] == 'ERROR' and initial[p]['message'] == 'Job timeout', 'Actual ERROR/Job timeout required')
    return incomplete[0], incomplete[1:]


def commit_time(api, repo, revision, *, repo_type='model'):
    immutable(revision)
    commits = api.list_repo_commits(repo, repo_type=repo_type, revision=revision)
    require(commits and commits[0].commit_id == revision, 'Authenticated immutable commit chronology')
    return timestamp(commits[0].created_at).isoformat()


def verify_owner(api, remote, directory, source, launch):
    directory = canonical_ledger(directory)
    original = read(directory / 'intent.json', 4 * 1024**2)
    exact(original['coordinator'], launch.coordinator(directory), 'Original coordinator identity; copied ledger forbidden')
    for key in ('reservationOwner', 'reservationPath', 'sourceParentRevision'):
        require(original[key] == source[key], 'Original reservation coordinator')
    reservation = launch.reservation_for(source)
    exact(read(directory / 'reservation.json', MANIFEST_LIMIT), reservation, 'Canonical reservation')
    require(digest(directory / 'reservation.json') == source['reservationSha256'] ==
            '57829f7e0b846b3f01e4cc46d368a0b637e43714d3b93b35e78ad99cda68611f' and
            source['reservationOwner'] == 'a5f5b5bb15e747fbb37280d3d5e9f6ff' and
            source['sourceParentRevision'] == 'dd2cc82ce85066101ff27d40680fb5939c0d9e68', 'Original CAS owner pins')
    info = api.repo_info(DATASET, repo_type='dataset')
    require(info.private is True, 'Private dataset required')
    head = immutable(info.sha)
    for rev in dict.fromkeys((SOURCE_REVISION, head)):
        pin = dict(repo=DATASET, repo_type='dataset', revision=rev, path=source['reservationPath'], sha256=source['reservationSha256'])
        meta = remote.describe(pin)
        require(type(meta.size) is int and 0 < meta.size <= MANIFEST_LIMIT, 'Reservation metadata bound')
        remote.get(pin, metadata=meta, cached=directory / 'reservation.json')
    parent_paths = api.get_paths_info(DATASET, [source['sourcePath'], source['reservationPath']],
                                     repo_type='dataset', revision=source['sourceParentRevision'])
    require(parent_paths == [], 'Source/owner must be absent at original CAS parent')
    return dict(originalRevision=SOURCE_REVISION, currentRevision=head, reservation=reservation,
                reservationSha256=source['reservationSha256'], parentPathsAbsent=True,
                remoteEvidence=copy.deepcopy(remote.evidence))


def public_records():
    rows = {}
    for label, filename, rev in (
            ('launch', 'replica-stress-launch-v1.json', LAUNCH_GIT),
            ('reconciliation', 'replica-stress-reconciliation-v1.json', DECODER_GIT),
            ('peer', 'replica-stress-peer-v1.json', PEER_GIT)):
        raw = authenticate_file(filename, rev)
        rows[label] = dict(git=rev, path='ai/multimap/' + filename, sha256=sha(raw), record=decode_json(raw))
    authenticate_file('reconcile_replica_stress_jobs_v1.py', DECODER_GIT, DECODER_SHA)
    # All historic artifacts remain unchanged, not only current qualification flags.
    tracked = subprocess.check_output(['git', 'ls-tree', '-r', '--name-only', SOURCE, 'ai/multimap'], cwd=ROOT, text=True).splitlines()
    historical = {}
    for name in tracked:
        if name.endswith('.json') and name != 'ai/multimap/runs.json':
            require(digest(no_links(ROOT / name)) == sha(git_bytes(name, SOURCE)), 'Historical artifact/qualification JSON changed')
            historical[name] = digest(ROOT / name)
    return rows, historical


def verify_recovery(receipt, jobs, roots, originals, snapshots, api, remote_factory, audit, worker, preflight, source):
    panel = receipt['panel']
    audits = receipt['initialSnapshotAudits']
    require(set(audits) == set(PANELS) and set(originals) == set(PANELS), 'Both original snapshots required for recovery')
    chosen, others = recovery_choice(jobs, audits, jobs['recovery']['createdAt'])
    require(chosen == panel and others == receipt['otherIncompletePanels'] and receipt['furtherJobsAuthorized'] is False,
            'Fixed strong-first recovery; no further paid jobs')
    first, last = receipt['originalSnapshotAuthority'], receipt['lastSnapshotAuthority']
    exact(first['manifestSha256'], last['manifestSha256'], 'Stale authority between both recovery checks')
    require(set(first['manifestSha256']) == set(PANELS) and receipt['resumeRevision'] == first['revision'], 'Both-manifest authority')
    info = api.repo_info(REPO)
    require(info.private is True, 'Private original manifests')
    head = immutable(info.sha)
    reports = {}
    for p in PANELS:
        root = no_links(originals[p])
        remote = remote_factory()
        snapshot = authenticate_snapshot(p, first['revision'], root, remote)
        require(snapshot['manifestSha256'] == first['manifestSha256'][p], 'Original authoritative manifest mismatch')
        transaction = worker.validate_snapshot(root, source, p, GROUP + '-' + p,
            worker.production_identity(preflight, p), require_incomplete=False)
        # validate_snapshot returns the transaction itself, not a claimed flag.
        exact(transaction, audits[p]['transaction'], 'Independently validated original transaction')
        expected = dict(run=GROUP + '-' + p, revision=first['revision'], manifestSha256=snapshot['manifestSha256'],
                        files={n: h for n, h in snapshot['files'].items() if n.startswith('study/')},
                        allFileHashes={n: h for n, h in snapshot['files'].items() if n != 'artifacts.json'},
                        totalBytes=snapshot['bytes'], transaction=transaction)
        exact(audits[p], expected, 'Complete original snapshot audit, including raw timings')
        actual = jobs[p]
        exact(receipt['initialJobStates'][p], dict(jobId=actual['jobId'], stage=actual['stage'],
              jobTimeout=actual['stage'] == 'ERROR' and actual['message'] == 'Job timeout'), 'Recorded/actual initial job state')
        # Verify BOTH recorded immutable authority checks and latest unchanged originals.
        for rev in dict.fromkeys((first['revision'], last['revision'], receipt['requestedSnapshotRevisions'][p], head)):
            pin = dict(repo=REPO, revision=immutable(rev), path='runs/' + GROUP + '-' + p + '/artifacts.json',
                       sha256=snapshot['manifestSha256'])
            meta = remote.describe(pin)
            require(0 < meta.size <= MANIFEST_LIMIT, 'Recovery authority manifest bound')
            remote.get(pin, metadata=meta, cached=root / 'artifacts.json')
        log = bounded_log(api.fetch_job_logs(job_id=jobs[p]['jobId'], namespace='coyotte508', follow=False))
        original_status = read(root / 'status.json')
        # The model repository HEAD may contain unrelated commits. The final
        # original upload's own revision is in the authenticated job log.
        events = production_events(log)
        last_upload = [e for e in events if e['stage'] == 'uploaded'][-1]['revision']
        pin = dict(repo=REPO, revision=immutable(last_upload), path='runs/' + GROUP + '-' + p + '/artifacts.json',
                   sha256=snapshot['manifestSha256'])
        meta = remote.describe(pin)
        require(0 < meta.size <= MANIFEST_LIMIT, 'Original final upload manifest bound')
        remote.get(pin, metadata=meta, cached=root / 'artifacts.json')
        log_report = (verify_log(log, p, original_status, last_upload, jobs[p]['stage'], audit)
                      if transaction['complete'] else verify_prefix_log(log, p, original_status, last_upload,
                                                                        transaction['committedBatches'], audit))
        reports[p] = dict(snapshot, productionLog=log_report)
    for authority in (first, last):
        when = commit_time(api, REPO, authority['revision'])
        require(timestamp(when) < timestamp(jobs['recovery']['createdAt']), 'Recovery authority committed before paid task')
    exact(receipt['resumeAudit'], audits[panel], 'Chosen complete resume audit')
    require(receipt['recoveryFromJob'] == jobs[panel]['jobId'] and receipt['sourceArchiveReusedExactly'] is True,
            'Same original job/source recovery')
    final_status = read(Path(roots[panel]) / 'status.json')
    exact(final_status['resume'], audits[panel], 'Worker consumed the exact audited original')
    inherited = verify_inherited(originals[panel], roots[panel], read(Path(originals[panel]) / 'artifacts.json'),
                                 read(Path(roots[panel]) / 'artifacts.json'), audits[panel]['transaction'])
    require(snapshots[panel]['segment'] == 2 and snapshots[next(p for p in PANELS if p != panel)]['segment'] == 1,
            'Exactly one recovery panel')
    complete_errors = [p for p in PANELS if audits[p]['transaction']['complete'] and jobs[p]['stage'] != 'COMPLETED']
    exact(receipt['completeAfterErrorRequiresAudit'], complete_errors, 'Honest complete-after-error classification')
    return dict(exercised=True, selectedPanel=panel, authorityChecks=[first, last], currentOriginalHead=head,
                originals=reports, inheritedRawFiles=inherited, completeAfterError=complete_errors)


def verify_jobs(api, directory, roots, snapshots, source, launch, decoder, audit, output,
                remote_factory, *, originals=None, recovery_anchor=None, preflight=None, worker=None):
    directory = canonical_ledger(directory)
    attempts, intents, receipts = ledger_attempts(directory)
    write_new(output / 'attempted-slots.json', attempts)  # also retained on unknown/failure
    actual, dates = {}, {}
    def inspect(_api, job_id):
        job, date = inspect_with_chronology(_api, job_id, decoder)
        actual[job_id], dates[job_id] = job, date
        return job
    inventory = bind(launch.inventory, inspect_actual=inspect)(api, GROUP)
    write_new(output / 'observed-inventory.json', dict(jobIds=sorted(actual), attemptedSlots=attempts['attemptedSlots'],
               requestedHours=attempts['requestedHours'], unknownSlots=attempts['unknownSlots']))
    require(not attempts['unknownSlots'], 'Unknown attempts consume their slot; no final attestation')
    command, launcher_bytes = launch.original_command(SOURCE)
    launch.validate_inventory(inventory, directory, source, command)
    require(set(PANELS) <= set(receipts), 'Both initial submissions mandatory')
    public, historical = public_records()
    peer = public['peer']['record']
    for p in PANELS:
        require(receipts[p]['jobId'] == INITIAL_IDS[p], 'No replacement initial job')
        exact(receipts[p], peer['records'][p], 'Pinned initial canonical receipt')
        require(digest(directory / 'receipts' / (p + '.json')) == peer['durableReceiptSha256'][p], 'Initial receipt byte hash')
    require(digest(directory / 'receipts/strong.json') == 'adca66e5372792048b471e55c0db8b7ec0be1b74b47730b5078989774e3d7dba', 'Strong admission failure never frees its slot')
    exact(source, peer['source'], 'Pinned original source/owner')
    exact(public['launch']['record']['records'][0], receipts['strong'], 'Original successful strong ID before admission failure')
    for slot, r in receipts.items():
        require(r['url'] == 'https://huggingface.co/jobs/coyotte508/' + r['jobId'], 'Canonical job URL')
        base = launch.intent_for(source, r['panel'], r['segment'], r['run'])
        for key in base:
            if key != 'env':
                exact(r[key], base[key], 'Full frozen receipt field ' + key)
        for filename, ledger in (('intent.json', 'intents'), ('launch.json', 'receipts')):
            require(digest(no_links(ROOT / 'ai/runs' / r['run'] / filename)) == digest(directory / ledger / (slot + '.json')),
                    'Per-run/canonical ledger bytes')
    owner = verify_owner(api, remote_factory(), directory, source, launch)
    source_time = commit_time(api, DATASET, SOURCE_REVISION, repo_type='dataset')
    git_dates = {rev: timestamp(subprocess.check_output(['git', 'show', '-s', '--format=%cI', rev], cwd=ROOT, text=True).strip()).isoformat()
                 for rev in (SOURCE, LAUNCH_GIT, DECODER_GIT, PEER_GIT)}
    jobs = {}
    for slot, r in receipts.items():
        job = actual[r['jobId']]
        date = dates[job.id]
        require(timestamp(git_dates[SOURCE]) < timestamp(source_time) < timestamp(date['createdAt']), 'Actual source committed/published before paid task')
        require(job.status.stage in ('COMPLETED', 'ERROR', 'CANCELED') and date['finishedAt'], 'Final audit requires terminal actual jobs')
        jobs[slot] = dict(jobId=job.id, stage=job.status.stage,
                          message='Job timeout' if job.status.message == 'Job timeout' else 'other-or-absent',
                          actualTimeoutSeconds=job.timeout_seconds, **date,
                          commandSha256=object_sha(job.command), environmentSha256=object_sha(job.environment),
                          labels=job.labels, image=job.docker_image, flavor=job.flavor,
                          expose=False, ssh=False, noActiveEndpoints=True)
    require(timestamp(jobs['strong']['createdAt']) < timestamp(git_dates[LAUNCH_GIT]) < timestamp(git_dates[DECODER_GIT]) <
            timestamp(jobs['mixed']['createdAt']), 'Original strong / adapter / mixed chronology')
    recovery = dict(exercised=False, reason='Authoritative group inventory and all three exclusive slots inspected; recovery unattempted',
                    inventorySlots=attempts['attemptedSlots'])
    if 'recovery' in receipts:
        require(recovery_anchor is not None, 'Recovery requires an explicit immutable public bookkeeping anchor')
        rev, path = recovery_anchor
        immutable(rev); safe_name(path)
        raw = git_bytes(path, rev)
        anchor = decode_json(raw)
        exact(anchor, dict(group=GROUP, receipt=receipts['recovery'],
                           receiptSha256=digest(directory / 'receipts/recovery.json'),
                           intentSha256=digest(directory / 'intents/recovery.json')), 'Recovery public canonical bookkeeping anchor')
        require(receipts['recovery']['firstReceiptSha256'] == digest(directory / 'receipts' / (receipts['recovery']['panel'] + '.json')),
                'Recovery original receipt pin')
        recovery = verify_recovery(receipts['recovery'], jobs, roots, originals or {}, snapshots, api, remote_factory,
                                   audit, worker, preflight, source)
        recovery['publicAnchor'] = dict(git=rev, path=path, sha256=sha(raw))
    else:
        require(recovery_anchor is None and all(s['segment'] == 1 for s in snapshots.values()), 'Unsubmitted recovery cannot supply output')
    logs = {}
    proof = startup_source_proof()
    for panel in PANELS:
        status = read(roots[panel] / 'status.json')
        slot = status['slot']
        require(status['run'] == receipts[slot]['run'] and status['panel'] == receipts[slot]['panel'], 'Panel/job/run ownership')
        for key in ('sourceRepo', 'sourceRevision', 'sourcePath', 'sourceCommit', 'sourceSha256'):
            require(status[key] == source[key], 'Job/panel original source binding')
        log = bounded_log(api.fetch_job_logs(job_id=receipts[slot]['jobId'], namespace='coyotte508', follow=False))
        logs[panel] = verify_log(log, panel, status, snapshots[panel]['revision'], jobs[slot]['stage'], audit)
        logs[panel]['jobId'] = receipts[slot]['jobId']
    return dict(schema='multimap-replica-stress-common-budget-evidence-v1', attempts=attempts,
                actualJobs=jobs, groupInventoryIds=sorted(actual), owner=owner, recovery=recovery,
                logs=logs, startupSourceProof=proof, sourcePublishedAt=source_time, gitCommitTimes=git_dates,
                publicRecords=public, historicalArtifactHashes=historical,
                actualRequestedHours=sum(j['actualTimeoutSeconds'] for j in jobs.values()) / 3600,
                originalAdmissionFailure='Strong ID/receipt persisted; old timeoutSeconds/truthy expose/ssh validator failed. No strong retry. New decoder preceded missing mixed submission.',
                chronologyLimits='Immutable HF source publication and actual job timestamps authenticated. Local Git objects and pinned public bookkeeping authenticate the recorded Git sequence; historical push wall-clock time is not independently exposed.',
                inventoryScope='All jobs returned by authenticated group-label inventory; not an account-wide assertion.', **FLAGS)


@dataclass
class _Session:
    roots: dict
    output: Path
    audit: object
    models: dict
    model_evidence: dict
    panels: dict
    budget: dict
    budget_sha: str
    reports: dict
    seals: dict
    witnesses: dict
    revalidate: object
    replays: dict = field(default_factory=dict)
    replay_attempts: set = field(default_factory=set)
    failed: bool = False
    ledger: object = None


def _check_evidence(session):
    require(session.failed is False, 'Failed replay permanently invalidates this audit session')
    if session.ledger is not None:
        current, _, _ = ledger_attempts(canonical_ledger(session.ledger))
        exact(current, session.budget['attempts'], 'Complete ledger inventory changed since verification')
    for path, checksum in session.seals.items():
        require(digest(no_links(path)) == checksum, 'Retained evidence changed after authentication')
    for panel in PANELS:
        manifest = read(session.roots[panel] / 'artifacts.json', MANIFEST_LIMIT)
        exact(dict(manifest, **{'artifacts.json': digest(session.roots[panel] / 'artifacts.json')}),
              session.panels[panel]['snapshot']['files'], 'Snapshot changed since authentication')
        restore_safety(session.roots[panel], set(manifest) | {'artifacts.json'})
        for name, checksum in manifest.items():
            require(digest(no_links(session.roots[panel] / name)) == checksum, 'Committed panel bytes changed')
    exact(model_fingerprint(session.models), session.model_evidence['fingerprint'],
          'All six model tensors/modes/grad flags/root serving configurations unchanged')


def _verify_integrity(roots, revisions, output, *, segments=None, ledger=None, preflight_root=None,
                     local_checkpoints=None, original_roots=None, recovery_anchor=None, api=None):
    """Read-only remote metadata, real CPU decode, NO games or payload downloads.

    Returns a live session, never an external receipt. Both complete panels are
    required; an independent joint operational report is retained on incomplete
    output. Unknown intent slots are counted and prevent success.
    """
    require(type(roots) is dict and type(revisions) is dict and set(roots) == set(revisions) == set(PANELS), 'Both panels and immutable revisions required')
    ledger = canonical_ledger(ledger)  # before output writes, helpers, network or models
    segments = dict.fromkeys(PANELS, 1) if segments is None else segments
    require(set(segments) == set(PANELS), 'Both segment selectors required')
    roots = {p: no_links(roots[p]) for p in PANELS}
    local_checkpoints = {p: lexical_path(path) for p, path in (local_checkpoints or {}).items()}
    original_roots = {p: no_links(path) for p, path in (original_roots or {}).items()}
    output = protect_output(output, *roots.values(), ledger, preflight_root,
                            *(Path(p).parent for p in (local_checkpoints or {}).values()),
                            *(original_roots or {}).values())
    paths = [*roots.values(), output]
    require(all(a != b and a not in b.parents and b not in a.parents for i, a in enumerate(paths) for b in paths[i+1:]), 'Nonnested distinct input/output roots')
    for rev in revisions.values():
        immutable(rev)
    h = helpers()
    audit, neural, gap = (h[n] for n in ('audit_replica_stress_v1', 'audit_neural', 'audit_gap'))
    output.mkdir(parents=True, exist_ok=True)
    # Preserve incomplete/failed operational data; no successful subset statistics.
    operational = audit.report_all(roots)
    write_new(output / 'operational-json-audit.json', operational)
    require(operational['bothPanelsComplete'], 'Both panels must be JSON-complete; operational evidence retained, no receipt')
    if api is None:
        from huggingface_hub import HfApi
        api = HfApi()
    collectors = []
    def remote_factory():
        remote = RetainedRemote(api, neural)
        collectors.append(remote)
        return remote
    snapshots = {p: authenticate_snapshot(p, revisions[p], roots[p], remote_factory(), segment=segments[p]) for p in PANELS}
    preflight = read(HERE / 'replica-stress-preflight-v1.json', 4 * 1024**2)
    source = read(ledger / 'source.json', 4 * 1024**2)
    require(source['sourceCommit'] == SOURCE and source['sourceRevision'] == SOURCE_REVISION and source['sourceSha256'] == SOURCE_SHA,
            'Frozen original source only')
    source_report = authenticate_source(ledger / 'source.tgz', preflight, remote_factory(), neural)
    # Source/Git/dependency/Node authentication precedes ANY serving imports.
    runtime_import_guard()
    import replica_stress_study_v1 as study
    import launch_replica_stress_v1 as launch
    import job_replica_stress_v1 as worker
    decoder = authenticated_decoder()
    launch.verify_archive(ledger / 'source.tgz', source, preflight, git_bytes('ai/multimap/launch_replica_stress_v1.py', SOURCE))
    decoder.verify_frozen_source(source)
    launch.check_local_storage(output)
    preflight_report = verify_preflight(preflight, preflight_root or ROOT / 'ai/runs' / (GROUP + '-preflight'), remote_factory(), audit, study)
    identities, runtimes = {}, {}
    for p in PANELS:
        identities[p], runtimes[p] = verify_runtime(p, roots[p], preflight, study, gap, remote_factory())
        exact(identities[p]['tasks'], audit.expected_tasks(p), 'Independently reconstructed production task identity')
    exact(identities['strong']['modelProvenance'], identities['mixed']['modelProvenance'], 'Same six policies across both panels')
    historical = verify_historical(audit, identities['strong']['modelProvenance'])
    models, model_evidence = decode_models(remote_factory(), audit, identities['strong']['modelProvenance'], local_checkpoints)
    budget = verify_jobs(api, ledger, roots, snapshots, source, launch, decoder, audit, output, remote_factory,
                         originals=original_roots, recovery_anchor=recovery_anchor, preflight=preflight, worker=worker)
    budget['boundedCollectors'] = [dict(accountedBytes=r.inner.bounded_bytes, artifacts=len(r.inner.accounted)) for r in collectors]
    budget['aggregateAccountedBytes'] = sum(r.inner.bounded_bytes for r in collectors)
    require(all(r.inner.bounded_bytes <= 128 * 1024**2 for r in collectors), 'Frozen old collector limit unchanged')
    # Explicit aggregate proof, not an unbounded succession of 128 MiB overrides.
    require(budget['aggregateAccountedBytes'] <= 448 * 1024**2, 'Overall source/preflight/two panels/six models/optional originals budget')
    budget_sha = write_new(output / 'job-budget-evidence.json', budget)
    reports, panels, seals = {}, {}, {str(output / 'job-budget-evidence.json'): budget_sha}
    for p in PANELS:
        reports[p] = audit.audit_panel(roots[p], p)
        require(reports[p]['jsonComplete'], 'Complete independently validated JSON required')
        panels[p] = dict(schema='multimap-replica-stress-retained-integrity-v1', panel=p,
            snapshot=snapshots[p], source=source_report, runtime=runtimes[p], preflight=preflight_report,
            historicalTraining=historical, decodedModels=model_evidence,
            jobBudgetEvidenceSha256=budget_sha, independentJson=reports[p], **FLAGS)
        path = output / ('integrity-' + p + '.json')
        seals[str(path)] = write_new(path, panels[p])
    for name, path in model_evidence['paths'].items():
        seals[path] = audit.MODEL_PINS[name]['sha256']
    for kind in ('source.json', 'intent.json', 'reservation.json', 'source.tgz'):
        seals[str(ledger / kind)] = digest(ledger / kind)
    for name, checksum in budget['attempts']['hashes'].items():
        seals[str(ledger / name)] = checksum
    # Explicit proof dependencies. The replay witness is deliberately ABSENT.
    witnesses = {
        'immutableRemoteManifestAndSource': ['snapshot', 'source'],
        'completeServingConfigAndRuntime': ['runtime', 'source'],
        'decodedSixCheckpointTensorsAndFullConfigs': ['decodedModels'],
        'referenceAndModelProvenance': ['runtime', 'decodedModels', 'historicalTraining'],
        'sourceCommittedBeforeTasks': ['budget.sourcePublishedAt', 'budget.actualJobs'],
        'allSubmissionsIncludingUnknownCounted': ['budget.attempts', 'budget.groupInventoryIds'],
        'sixPlusThreePlusSharedThreeHourBudget': ['budget.actualRequestedHours', 'budget.actualJobs'],
        'recoveryOnlyAfterBothOriginalsTerminalActualJobTimeout': ['budget.recovery'],
        'fixedStrongPriorityIfBothIncomplete': ['budget.recovery'],
        'inheritedCommittedBatchesUnchanged': ['budget.recovery', 'snapshot'],
        'sameSourceRuntimeTasksOnContinuation': ['budget.recovery', 'source', 'runtime'],
        'noOutcomeDependentReplacement': ['budget.actualJobs', 'budget.recovery', 'budget.publicRecords'],
        'historicalArtifactsAndQualificationUnchanged': ['budget.historicalArtifactHashes'],
    }
    require(set(witnesses) == set(audit.EXTERNAL_CHECKS) - {'exactEngineReplayAndGreedyRouting'}, 'External witness coverage')
    def revalidate():
        # Read-only metadata and rehashes; no model reload/download/game.
        runtime_import_guard(reject_preloaded=False)
        current_attempts, _, _ = ledger_attempts(canonical_ledger(ledger))
        exact(current_attempts, budget['attempts'], 'Complete ledger inventory changed since verification')
        current_jobs = bind(launch.inventory, inspect_actual=decoder.inspect_actual)(api, GROUP)
        launch.validate_inventory(current_jobs, ledger, source, launch.original_command(SOURCE)[0])
        exact(sorted(j.id for j in current_jobs), budget['groupInventoryIds'], 'Authoritative group inventory changed')
        for job in current_jobs:
            prior = budget['actualJobs'][job.labels['slot']]
            require(job.status.stage == prior['stage'] and job.timeout_seconds == prior['actualTimeoutSeconds'] and
                    ('Job timeout' if job.status.message == 'Job timeout' else 'other-or-absent') == prior['message'],
                    'Terminal job metadata changed during audit')
        source_verifier(neural, identities['strong']['modelProvenance']['expert24']['config'])(ledger / 'source.tgz',
                              identities['strong']['modelProvenance']['expert24']['config'])
        public_records()
        for p in PANELS:
            identity, _ = verify_runtime(p, roots[p], preflight, study, gap, remote_factory())
            exact(identity, identities[p], 'Runtime changed during replay')
    session = _Session(roots, output, audit, models, model_evidence, panels, budget, budget_sha,
                       reports, seals, witnesses, revalidate, ledger=ledger)
    _check_evidence(session)
    return session


def replay_tasks(panel, audit=None):
    require(panel in PANELS, 'Fixed panel required')
    if audit is None:
        audit = helpers()['audit_replica_stress_v1']
    protocol = audit.protocol()
    keys = ('map', 'players', 'variant', 'fastBid', 'deal', 'focalSeat')
    exact(protocol['postRunReplayScopes'], [dict(zip(keys, s)) for s in REPLAY_SCOPES], 'Eight literal replay scopes')
    require(protocol['postRunReplayGames'] == 48 and set(protocol['replayTimingExceptions']) == TIMINGS, 'Fixed replay budget/timing exclusions')
    by_scope = {}
    for task in audit.expected_tasks(panel):
        scope = tuple(task[k] for k in keys)
        if scope in REPLAY_SCOPES:
            by_scope[scope, task['policy']] = task
    tasks = [by_scope[scope, policy] for scope in REPLAY_SCOPES for policy in ('replica1', 'replica2', 'ppo2')]
    require(len(tasks) == 24 and len({canonical(t) for t in tasks}) == 24, '24 fixed panel tasks')
    return tasks


def compare_replays(tasks, outcomes, stored, audit):
    require(type(outcomes) is list and len(outcomes) == len(tasks) == 24, 'Exactly 24 replay terminals per panel')
    checks = []
    for task, actual in zip(tasks, outcomes):
        audit.validate_outcome(actual, task)
        original = stored[canonical(task)]
        audit.validate_outcome(original, task)
        left = {k: v for k, v in actual.items() if k not in TIMINGS}
        right = {k: v for k, v in original.items() if k not in TIMINGS}
        exact(left, right, 'Full canonical terminal/routing/public/request replay mismatch')
        checks.append(dict(spec=task, canonicalOutcomeSha256=object_sha(left),
                           storedRawOutcomeSha256=object_sha(original), replayRawOutcomeSha256=object_sha(actual)))
    return checks


def _replay_panel(session, panel, *, allow_games=False):
    require(allow_games is True, 'Explicit --allow-games required; no arbitrary seeds')
    require(panel in PANELS, 'Fixed panel required')
    _session_check(session)
    require(panel not in session.replay_attempts and not (session.output / ('replay-attempt-' + panel + '.json')).exists(),
            'Replay slot already attempted; failed/unknown evaluation attempts cannot be retried')
    session.revalidate()
    tasks = replay_tasks(panel, session.audit)
    wanted = {canonical(t) for t in tasks}
    stored = {}
    for i, batch in enumerate(session.audit.expected_batches(panel)):
        if any(canonical(t) in wanted for t in batch):
            record = read(session.roots[panel] / f'study/batch-{i:03}.json')
            for game in session.audit.verify_batch(record, i, batch):
                if canonical(game['spec']) in wanted:
                    stored[canonical(game['spec'])] = game
    require(set(stored) == wanted, 'Replay observations must already be in committed panel')
    torch, collect = _replay_services()
    before = model_fingerprint(session.models)
    python_rng, deterministic = random.getstate(), torch.are_deterministic_algorithms_enabled()
    checks, failure, outcomes = [], None, None
    # Closure-owned authority consumes the fixed durable slot, independent of
    # output/session/process, with O_EXCL + fsync BEFORE any evaluation game.
    durable_attempt_sha = _begin_replay(session, panel, tasks)
    attempt_path = session.output / ('replay-attempt-' + panel + '.json')
    session.seals[str(attempt_path)] = write_new(attempt_path, dict(panel=panel, taskSha256=object_sha(tasks),
        gamesRequested=24, manifestSha256=session.panels[panel]['snapshot']['manifestSha256'], **FLAGS))
    session.replay_attempts.add(panel)
    try:
        with torch.random.fork_rng(devices=[]):
            torch.use_deterministic_algorithms(True)
            outcomes = collect(tasks, workers=6, artifact=ROOT / 'ai/runs/multimap-reference-preflight-v1/artifact',
                               reference_python=ROOT / 'ai/.venv-reference/bin/python', models=session.models)
            checks = compare_replays(tasks, outcomes, stored, session.audit)
    except BaseException:
        failure = 'fixed-replay-failed'  # never retain exception/private payload text
        session.failed = True
        raise
    finally:
        torch.use_deterministic_algorithms(deterministic)
        random.setstate(python_rng)
        after = model_fingerprint(session.models, validate=False)
        if failure is not None or before != after:
            session.failed = True
            write_new(session.output / ('replay-failure-' + panel + '.json'), dict(panel=panel,
                code=failure or 'model-state-changed', attemptedTaskSha256=object_sha(tasks),
                completedExactMatches=len(checks), before=before, after=after,
                manifestSha256=session.panels[panel]['snapshot']['manifestSha256'], **FLAGS))
        exact(after, before, 'Replay changed a model tensor/submodule mode/grad flag/root serving configuration')
    _session_check(session)
    report = dict(schema='multimap-replica-stress-fixed-replay-v1', panel=panel,
        durableAttemptSha256=durable_attempt_sha, manifestSha256=session.panels[panel]['snapshot']['manifestSha256'], taskSha256=object_sha(tasks),
        tasks=tasks, outcomes=outcomes, checks=checks, games=24, exactMatches=len(checks),
        modelBefore=before, modelAfter=after, expertLabels=0, independentStrengthObservations=0,
        excludedTimingFields=sorted(TIMINGS), **FLAGS)
    path = session.output / ('replay-' + panel + '.json')
    session.seals[str(path)] = write_new(path, report)
    session.replays[panel] = report
    return report


def _finalize_receipts(session):
    """Authenticate retained actual evidence, then release BOTH attestations.

    Calling this on verify-only reports or one replay never writes a receipt.
    No receipt field is copied from expectedModelProjection/_model_projection.
    """
    _session_check(session)
    require(set(session.replays) == session.replay_attempts == set(PANELS), 'All 48 actual replays required before either receipt')
    require(not any(session.output.glob('replay-failure-*.json')), 'Retained failed replay cannot be hidden by successful retries')
    session.revalidate()
    _session_check(session)
    exact(read(session.output / 'job-budget-evidence.json'), session.budget, 'Actual common budget evidence binding')
    receipts = {}
    for p in PANELS:
        integrity = read(session.output / ('integrity-' + p + '.json'))
        exact(integrity, session.panels[p], 'Retained integrity evidence object')
        replay = read(session.output / ('replay-' + p + '.json'))
        exact(replay, session.replays[p], 'Actual retained replay proof')
        tasks = replay_tasks(p, session.audit)
        exact(replay['tasks'], tasks, 'Fixed replay spec set')
        require(replay['games'] == replay['exactMatches'] == len(replay['checks']) == 24 and
                replay['expertLabels'] == replay['independentStrengthObservations'] == 0, 'Actual 48 replay/zero-label evidence')
        stored = {}
        for i, batch in enumerate(session.audit.expected_batches(p)):
            for g in session.audit.verify_batch(read(session.roots[p] / f'study/batch-{i:03}.json'), i, batch):
                stored[canonical(g['spec'])] = g
        exact(compare_replays(tasks, replay['outcomes'], stored, session.audit), replay['checks'], 'Reauthenticated actual replay comparisons')
        exact(replay['modelBefore'], session.model_evidence['fingerprint'], 'Initial model fingerprint')
        exact(replay['modelAfter'], replay['modelBefore'], 'Unchanged full model fingerprint')
        witnesses = dict(session.witnesses, exactEngineReplayAndGreedyRouting=['replay.checks', 'replay.modelBefore', 'replay.modelAfter'])
        require(set(witnesses) == set(session.audit.EXTERNAL_CHECKS) and all(witnesses.values()), 'All fourteen earned proof dependencies')
        evidence = dict(integrity=integrity, replay=replay, witnesses=witnesses,
                        jobBudgetEvidenceSha256=session.budget_sha, **FLAGS)
        evidence_sha = write_new(session.output / ('evidence-' + p + '.json'), evidence)
        # Independent binding is recomputed from source/runtime/manifest JSON;
        # actual decoded model projection comes only from weights_only payloads.
        report = session.audit.audit_panel(session.roots[p], p)
        binding = report['integrityBinding']
        receipt = dict(schema='multimap-replica-stress-external-integrity-v1', **binding,
            evidenceSha256=evidence_sha, checks={k: bool(witnesses[k]) for k in session.audit.EXTERNAL_CHECKS},
            modelProjection=session.model_evidence['projection'], jobBudgetEvidenceSha256=session.budget_sha)
        session.audit.validate_integrity(receipt, report)
        receipts[p] = receipt
    statuses = {p: session.budget['logs'][p]['jobStage'] for p in PANELS}
    joint = session.audit.report_all(session.roots, statuses=statuses, integrity=receipts)
    require(joint['strengthStatisticsReleased'] is True, 'Independent BOTH-panel JSON release gate failed')
    # Recheck all inputs immediately before the only attestation write.
    _session_check(session)
    write_new(session.output / 'independent-joint-audit.json', joint)
    write_new(session.output / 'external-integrity.json', receipts)
    return receipts, joint


def _replay_services():
    import torch
    from replica_stress_rollout_v1 import collect
    return torch, collect


def durable_new(path, value):
    """Exclusive, crash-durable evidence. Existing/partial files NEVER resume.

    A killed writer leaves a consumed unknown slot. Unlike write_new, even an
    identical existing intent is an error. No removal/overwrite API exists.
    """
    path = no_links(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    no_links(path)
    raw = (canonical(value) + '\n').encode()
    with path.open('xb') as stream:  # O_CREAT | O_EXCL, across processes
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    for directory in (path.parent, path.parent.parent):
        descriptor = os.open(no_links(directory), os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
    return digest(path)


def _make_workflow():
    """One isolated authority domain; no function accepts a session for issuance.

    Production captures the actual verifier here, once at module initialization.
    Constructor fields, copied handles and JSON are not authority. Test-only
    FunctionType bindings can build a DIFFERENT domain, never register with the
    production registry. Deliberate interpreter/closure monkeypatching is outside
    this boundary; ordinary mutable session fields are entirely untrusted.
    Public ``models`` entries are detached role/width/bound/modelClass descriptors,
    not policies or tensors. Changing even these metadata views rejects use.
    """
    verifier, evidence_check = _verify_integrity, _check_evidence
    attempt_root = ATTEMPT_ROOT  # fixed study-wide, no CLI override
    registry, owned = {}, {}
    reference_fields = {'audit', 'models', 'revalidate'}

    def model_descriptors(proof):
        return {name: dict(role=value['role'], **copy.deepcopy(value['servingConfiguration']))
                for name, value in proof.model_evidence['fingerprint'].items()}

    def copy_view(proof):
        values = {k: copy.deepcopy(v) for k, v in vars(proof).items() if k not in reference_fields}
        return _Session(**values, audit=proof.audit, models=model_descriptors(proof), revalidate=proof.revalidate)

    def synchronize(view, proof):
        view.__dict__.clear()
        view.__dict__.update(vars(copy_view(proof)))

    def durable_check(proof):
        state = owned[id(proof)]
        root = no_links(attempt_root)
        if root.exists():
            require(root.is_dir(), 'Durable replay authority must be a directory')
            allowed = {p + suffix for p in PANELS for suffix in ('.intent.json', '.result.json')}
            require(all(p.name in allowed and p.is_file() and not p.is_symlink() for p in root.iterdir()),
                    'Unexpected durable replay authority entry')
        for panel in PANELS:
            intent = no_links(root / (panel + '.intent.json'))
            result = no_links(root / (panel + '.result.json'))
            row = state['durable'].get(panel)
            if row is None:
                require(not intent.exists() and not result.exists(),
                        'Replay slot already attempted in another output/session/process; no retry or JSON resume')
            else:
                require(intent.is_file() and digest(intent) == row['intentSha256'], 'Durable replay intent changed')
                exact(read(intent), row['binding'], 'Durable replay authority binding changed')
                if row['status'] == 'success':
                    require(result.is_file() and digest(result) == row['resultSha256'], 'Durable replay result changed')
                    require(proof.replays[panel]['durableAttemptSha256'] == row['intentSha256'], 'Replay/intent binding changed')
                    exact(read(result), dict(panel=panel, status='success', intentSha256=row['intentSha256'],
                          replaySha256=object_sha(proof.replays[panel]), **FLAGS), 'Durable replay result binding changed')
                else:
                    require(row['status'] == 'active' and not result.exists(), 'Failed/unknown durable replay attempt')

    def check_owned(proof):
        require(id(proof) in owned and owned[id(proof)]['proof'] is proof, 'Live verified session required')
        evidence_check(proof)
        durable_check(proof)

    def checked(view):
        row = registry.get(id(view))
        require(row is not None and row[0] is view, 'Live verified session required; constructed/copy/JSON sessions have no authority')
        proof = row[1]
        require(set(vars(view)) == set(vars(proof)), 'Verified authority fields changed')
        for key, value in vars(proof).items():
            actual = getattr(view, key)
            if key == 'models':
                expected = model_descriptors(proof)
                message = 'Verified model metadata bindings changed'
                require(type(actual) is dict and actual == expected, message)
                exact(actual, expected, message)
            elif key in reference_fields:
                require(actual is value, 'Verified authority callable binding changed')
            else:
                message = 'Verified authority binding changed: ' + key
                require(type(actual) is type(value), message)
                if key in {'model_evidence', 'panels', 'budget', 'budget_sha', 'reports', 'seals', 'witnesses', 'replays'}:
                    exact(actual, value, message)
                else:
                    require(actual == value, message)
        check_owned(proof)
        return proof

    def begin(proof, panel, tasks):
        check_owned(proof)
        require(panel not in owned[id(proof)]['durable'], 'Replay already attempted')
        binding = dict(schema='multimap-replica-stress-durable-replay-attempt-v1', group=GROUP,
            sourceCommit=SOURCE, sourceRevision=SOURCE_REVISION, sourceSha256=SOURCE_SHA,
            panel=panel, taskSha256=object_sha(tasks), gamesRequested=24,
            snapshots={p: {k: proof.panels[p]['snapshot'][k] for k in ('revision', 'manifestSha256', 'segment')} for p in PANELS},
            modelEvidenceSha256=object_sha(proof.model_evidence), jobBudgetEvidenceSha256=proof.budget_sha,
            output=str(proof.output), **FLAGS)
        path = no_links(attempt_root) / (panel + '.intent.json')
        checksum = durable_new(path, binding)
        owned[id(proof)]['durable'][panel] = dict(binding=binding, intentSha256=checksum, status='active')
        return checksum

    # Only these private function copies receive internal authority operations.
    replay_impl = bind(_replay_panel, _session_check=check_owned, _begin_replay=begin)
    final_impl = bind(_finalize_receipts, _session_check=check_owned)

    def verify_integrity(*args, **kwargs):
        proof = verifier(*args, **kwargs)  # actual full verification, not a caller-supplied session
        owned[id(proof)] = dict(proof=proof, durable={})
        check_owned(proof)
        view = copy_view(proof)
        registry[id(view)] = (view, proof)
        return view

    def session_check(session):
        checked(session)  # deliberately never return closure-owned state

    def replay_panel(session, panel, *, allow_games=False):
        view = session
        require(allow_games is True, 'Explicit --allow-games required; no arbitrary seeds')
        require(panel in PANELS, 'Fixed panel required')
        proof = checked(view)
        try:
            report = replay_impl(proof, panel, allow_games=True)
            row = owned[id(proof)]['durable'][panel]
            result = dict(panel=panel, status='success', intentSha256=row['intentSha256'], replaySha256=object_sha(report), **FLAGS)
            row['resultSha256'] = durable_new(no_links(attempt_root) / (panel + '.result.json'), result)
            row['status'] = 'success'
            check_owned(proof)
            return copy.deepcopy(report)
        except BaseException:
            proof.failed = True
            row = owned[id(proof)]['durable'].get(panel)
            if row is not None and row['status'] == 'active':
                row['status'] = 'failed'
                # If writing fails, the durable intent still consumes the slot.
                durable_new(no_links(attempt_root) / (panel + '.result.json'),
                    dict(panel=panel, status='failed', code='fixed-replay-failed-or-interrupted',
                         intentSha256=row['intentSha256'], **FLAGS))
            raise
        finally:
            synchronize(view, proof)

    def finalize_receipts(session):
        proof = checked(session)
        state = owned[id(proof)]['durable']
        require(set(state) == set(PANELS) and all(r['status'] == 'success' for r in state.values()),
                'All 48 actual replays required before either receipt; no saved-JSON resume')
        result = final_impl(proof)
        return copy.deepcopy(result)

    return verify_integrity, replay_panel, finalize_receipts, session_check


verify_integrity, replay_panel, finalize_receipts, _session_check = _make_workflow()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    fetch = sub.add_parser('fetch', help='Explicit bounded panel-only downloads (no models/games)')
    fetch.add_argument('panel', choices=PANELS)
    fetch.add_argument('revision')
    fetch.add_argument('output', type=Path)
    fetch.add_argument('--segment', type=int, choices=(1, 2), default=1)
    fetch.add_argument('--allow-download', action='store_true')
    preflight_fetch = sub.add_parser('fetch-preflight', help='Explicit bounded private preflight evidence only')
    preflight_fetch.add_argument('output', type=Path)
    preflight_fetch.add_argument('--allow-download', action='store_true')
    for command in ('verify', 'replay'):
        p = sub.add_parser(command)
        for panel in PANELS:
            p.add_argument('--' + panel + '-root', type=Path, required=True)
            p.add_argument('--' + panel + '-revision', required=True)
            p.add_argument('--' + panel + '-segment', type=int, choices=(1, 2), default=1)
            p.add_argument('--original-' + panel + '-root', type=Path)
        p.add_argument('--output', type=Path, required=True)
        p.add_argument('--ledger', type=Path, help='Compatibility only: must equal the canonical ROOT/ai/runs/GROUP ledger')
        p.add_argument('--preflight-root', type=Path)
        for role in EXPERTS:
            p.add_argument('--' + role + '-checkpoint', type=Path)
        p.add_argument('--recovery-anchor-git')
        p.add_argument('--recovery-anchor-path')
        if command == 'replay':
            p.add_argument('--allow-games', action='store_true')
    args = parser.parse_args(argv)
    try:
        if args.command == 'fetch-preflight':
            result = fetch_preflight(args.output, allow_download=args.allow_download)
            print(canonical(dict(preflightRevision=result['revision'], files=len(result['files']))))
            return 0
        if args.command == 'fetch':
            result = fetch_panel(args.panel, args.revision, args.output, segment=args.segment, allow_download=args.allow_download)
            print(canonical(dict(panel=args.panel, complete=result['complete'], files=len(result['files']))))
            return 0
        if args.command == 'replay':
            require(args.allow_games is True, 'Explicit --allow-games required')
        require(bool(args.recovery_anchor_git) == bool(args.recovery_anchor_path), 'Both recovery anchor Git and path required')
        roots = {p: getattr(args, p + '_root') for p in PANELS}
        originals = {p: getattr(args, 'original_' + p + '_root') for p in PANELS if getattr(args, 'original_' + p + '_root') is not None}
        session = verify_integrity(roots, {p: getattr(args, p + '_revision') for p in PANELS}, args.output,
            segments={p: getattr(args, p + '_segment') for p in PANELS}, ledger=args.ledger, preflight_root=args.preflight_root,
            local_checkpoints={p: getattr(args, p + '_checkpoint') for p in EXPERTS if getattr(args, p + '_checkpoint') is not None},
            original_roots=originals, recovery_anchor=(args.recovery_anchor_git, args.recovery_anchor_path) if args.recovery_anchor_git else None)
        if args.command == 'replay':
            for p in PANELS:
                replay_panel(session, p, allow_games=True)
            finalize_receipts(session)
        print(canonical(dict(status='verified-without-attestation' if args.command == 'verify' else 'complete-integrity-verified',
                             replays=0 if args.command == 'verify' else 48, **FLAGS)))
        return 0
    except Exception:
        # Never print raw API/model exceptions. Preserve prior hashed operational evidence.
        print(canonical(dict(status='failed-or-incomplete', code='external-integrity-not-released', strengthStatisticsReleased=False)))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
