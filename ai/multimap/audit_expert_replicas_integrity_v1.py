"""Independent external integrity evidence for the TWO authorized expert replicas.

No import-time Torch, network, model loads, launches or games. Only this module
and its new tests are implementation changes; historical guards remain intact.
The default audit reuses local payloads and performs read-only HF metadata/job
requests. ``fetch`` explicitly authorizes bounded compact snapshot downloads.
``replay`` explicitly authorizes 16 evaluation replays, never training or labels.

API::
    fetch(replica, revision, output, api=None)  # output/restored
    audit_integrity(replica, revision, root, output, *, auditGitReceiptCommit,
                    original_root=None, selection_checkpoint=None, api=None)
    replay(replica, root, output, *, allow_games=False)

Run in the existing ai/.venv (with PYTHONPATH=ai/multimap). auditGitReceiptCommit
must really contain expert-replicas-continuations-v1.json, byte-identical locally.
All external checks are earned before a receipt is written. Checkpoint projections
come from weights_only=True tensors/metadata, NEVER expectedCheckpointProjection.
A failed/incomplete audit emits no external receipt. This auditor deliberately
supports only the actual two confirmation-only continuations, not arbitrary runs.

Limits: gradients and RAM-only training trajectories are unavailable; this is not
an optimization replay. Historical reference archive metadata + the entire pinned
1467-file recovered artifact are verified without re-downloading the 451 MB cache.
Principal runtime versions are exact, not a claim of fully pinned Python transitives.
Group inventory proves the four authorized labeled jobs, not absence of unrelated
jobs outside that group. HF inspection does not expose the actual timeout setting;
the three-hour creation cap is authenticated via the Git-anchored launch receipts.
"""
import argparse
import ast
from collections import Counter
import copy
from datetime import datetime
import hashlib
import importlib
import io
import json
from pathlib import Path, PurePosixPath
import random
import re
import shlex
import shutil
import subprocess
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
GROUP = 'multimap-expert-replicas-20261109-v1'
REPO = 'coyotte508/powergrid-ai-multimap-v1'
DATASET = 'coyotte508/powergrid-ai-training-v1'
SOURCE = 'a75b787f38a833a8736ab6b84c7a2019f3773a55'
LAUNCH_COMMIT = '9204f5f999f5b897af2ad71ee468cf9071b4a48c'
SOURCE_REVISION = 'dd2cc82ce85066101ff27d40680fb5939c0d9e68'
SOURCE_SHA = 'f4b30e8afaf0f3e9c17c04bcaae77e3e0368eb01faee77a8825f0ed5790daa16'
SOURCE_PATH = 'multimap/' + GROUP + '/source.tgz'
IMAGE = 'python:3.12.8-slim-bookworm@sha256:2199a62885a12290dc9c5be3ca0681d367576ab7bf037da120e564723292a2f0'
PINS = {
    1: dict(originalJob='6af2014f9737d9a9e08cea58', job='6af22c909737d9a9e08d6193',
            original='96c7c45c90304904fb12f199fa97b2fd7de2328f',
            selection='852dda11fd3762b6345a1096de1f86178125bb69', bestUpdate=24,
            bestSha256='7918c5ceec29ee181721eaaa3a38f63fd94cf0248c34d192e0b3f65960c729e5'),
    2: dict(originalJob='6af20150ab34849891a86aea', job='6af22cd59737d9a9e08d62a8',
            original='2ccf69640d16d59bc87564bc2c8fc919fe2cd906',
            selection='7be7a2560f208058c283d09703419db1416eec1e', bestUpdate=32,
            bestSha256='89d03f5b23fd6d088e175d32ff9c90ff88bd947f7e8b17d508b1b2f641a037fa'),
}
HELPERS = {
    'audit_expert_replicas_v1.py': 'a64b0c049e47303969cc394a04edde5ce5cccbceac7e92be0f3e19ba398109af',
    'audit_expert.py': '0755762b04c6d74b26a3e277780ef46a5be73b8c1407437fb3f8f385ef8d0f8e',
    'audit_gap.py': 'e764383ae7e0e82a065e24d14de06d31d498aab1cabf16f764c66b4dc8ef3522',
    'audit_neural.py': 'e5202371d7357e9929697eb77309533d0f7ec11ce8e54eab9c6048927f25e2bb',
    'audit_stress_integrity.py': 'c79e87b01f5f2b958c1242489fa345671279d46117684874760ad6bbf1703e17',
}
LIMIT = 128 * 1024**2
FILE_LIMIT = 16 * 1024**2
MANIFEST_LIMIT = 64 * 1024
LOG_LIMIT = 2 * 1024**2
TIMINGS = {'featureMs', 'inferenceMs', 'referenceMs', 'seconds'}
MODEL_KEYS = {'schema', 'width', 'bound', 'priorAsActionFeature', 'state_dict', 'stage', 'update', 'config'}
TRANSACTION_KEYS = MODEL_KEYS | {'optimizer', 'torchRng', 'pythonRng', 'history', 'bestUpdate',
    'bestStage', 'bestScore', 'baseline', 'bestArtifact', 'bestSha256', 'confirmations', 'result'}
PROJECTION_KEYS = ('stage', 'update', 'bestStage', 'bestUpdate', 'bestScore', 'baseline', 'history',
                   'result', 'config', 'width', 'bound', 'priorAsActionFeature', 'bestSha256', 'confirmations')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def exact(actual, expected, label):
    require(canonical(actual) == canonical(expected), label)


def immutable(value, size=40):
    require(type(value) is str and re.fullmatch('[0-9a-f]{' + str(size) + '}', value), 'Immutable hash required')
    return value


def replica_id(replica):
    require(type(replica) is int and replica in PINS, 'Exactly replica 1 or 2 required')
    return replica


def run_name(replica, original=False):
    return GROUP + ('' if original else '-continuation') + '-r' + str(replica_id(replica))


def safe_name(name):
    require(type(name) is str and name and '\\' not in name, 'Unsafe member name')
    p = PurePosixPath(name)
    require(not p.is_absolute() and '..' not in p.parts and p.as_posix() == name and name != '.', 'Unsafe member path')


def no_links(path):
    path = Path(path).absolute()
    require(not any(p.is_symlink() for p in (path, *path.parents)), 'Symlink/ancestor forbidden')
    return path


def read(path, limit=LIMIT):
    path = no_links(path)
    require(path.is_file() and 0 < path.stat().st_size <= limit, 'Missing/oversized regular JSON')
    def pairs(items):
        result = {}
        for k, v in items:
            require(k not in result, 'Duplicate JSON key')
            result[k] = v
        return result
    value = json.loads(path.read_text(), object_pairs_hook=pairs,
                       parse_constant=lambda _: require(False, 'Nonfinite JSON'))
    canonical(value)  # also rejects overflowing JSON exponents
    return value


def write_new(path, value):
    """Never silently replace retained evidence, even after a failed audit."""
    path = no_links(path)
    raw = (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + '\n').encode()
    if path.exists():
        require(path.is_file() and path.read_bytes() == raw, 'Existing different evidence: ' + path.name)
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('xb') as stream:
            stream.write(raw)
    return digest(path)


def git_bytes(name, revision=SOURCE):
    safe_name(name)
    immutable(revision)
    return subprocess.check_output(['git', 'show', revision + ':' + name], cwd=ROOT)


def authenticate_helpers():
    for name, checksum in HELPERS.items():
        require(sha(git_bytes('ai/multimap/' + name)) == checksum == digest(no_links(HERE / name)),
                'Frozen helper differs from Git/hash: ' + name)
    # Modules with import-time serving dependencies (stress) are authenticated but
    # not imported. No old module global is ever assigned to or monkeypatched.
    return {name: importlib.import_module(name) for name in
            ('audit_expert_replicas_v1', 'audit_expert', 'audit_neural', 'audit_gap')}


def complete_names():
    # Independent whitelist, not an arbitrary manifest supplied by a caller.
    names = {'protocol.json', 'status.json', 'environment.json', 'recovery.json'}
    names |= {'expert/' + n for n in ('config.json', 'history.json', 'result.json', 'initial.pt',
        'warmup.pt', 'best.pt', 'last.pt', 'warmup-plan.json', 'selection-plan.json',
        'confirmation-plan.json', 'warmup.json', 'confirmation-selected.json', 'confirmation-teacher.json')}
    names |= {f'expert/selection-{s}.json' for s in ('0', 'teacher', 'warmup', '8', '16', '24', '32')}
    names |= {f'expert/{p}-{u}.json' for p in ('train', 'train-plan') for u in range(1, 33)}
    return names


def snapshot_names(original=False):
    return complete_names() - ({'expert/result.json', 'expert/confirmation-teacher.json'} if original else set())


def restore_safety(base, allowed):
    base = no_links(base)
    if not base.exists():
        return
    require(base.is_dir(), 'Restore root must be a directory')
    for p in base.rglob('*'):
        require(not p.is_symlink(), 'Nested restore symlink')
        name = p.relative_to(base).as_posix()
        require((p.is_file() and name in allowed) or (p.is_dir() and name == 'expert'),
                'Unexpected restore descendant')


def snapshot_metadata(manifest, entries, prefix, original=False):
    expected = snapshot_names(original)
    require(type(manifest) is dict and set(manifest) == expected, 'Exact snapshot whitelist required')
    for h in manifest.values():
        immutable(h, 64)
    require(len(entries) == len(expected) + 1 and len({e.path for e in entries}) == len(entries), 'Remote file count/duplicates')
    byname = {e.path[len(prefix):]: e for e in entries if e.path.startswith(prefix)}
    require(set(byname) == expected | {'artifacts.json'}, 'Remote tree exact file coverage')
    require(all(type(e.size) is int and 0 < e.size <= FILE_LIMIT for e in entries), 'Remote individual size budget')
    require(byname['artifacts.json'].size <= MANIFEST_LIMIT and sum(e.size for e in entries) <= LIMIT,
            'Remote aggregate budget BEFORE payloads')
    from audit_neural import git_blob
    for name, entry in byname.items():
        immutable(entry.blob_id)
        if entry.lfs:
            immutable(entry.lfs.sha256, 64)
            require(entry.lfs.size == entry.size and (name == 'artifacts.json' or entry.lfs.sha256 == manifest[name]),
                    'Remote LFS size/content pin')
            pointer = (f'version https://git-lfs.github.com/spec/v1\noid sha256:{entry.lfs.sha256}'
                       f'\nsize {entry.size}\n').encode()
            require(git_blob(pointer) == entry.blob_id, 'Remote LFS Git pointer')
    return byname


def authenticate_snapshot(replica, revision, base, remote, *, original=False, download=False):
    immutable(revision)
    base = Path(base)
    allowed = snapshot_names(original) | {'artifacts.json'}
    restore_safety(base, allowed)
    prefix = 'runs/' + run_name(replica, original) + '/'
    pin = dict(repo=REPO, revision=revision, path=prefix + 'artifacts.json')
    meta = remote.describe(pin)
    require(type(meta.size) is int and 0 < meta.size <= MANIFEST_LIMIT, 'Manifest metadata bound')
    local = base / 'artifacts.json'
    require(download or local.is_file(), 'Local manifest required (use explicit fetch first)')
    source = remote.get(pin, metadata=meta, cached=local if local.exists() else None)
    # RemoteFiles authenticates snapshot->blob cache links; JSON reads use the
    # resolved regular file, never copy the symlink into a restored directory.
    manifest = read(Path(source).resolve(strict=True), MANIFEST_LIMIT)
    entries = []
    for entry in remote.api.list_repo_tree(REPO, path_in_repo=prefix.rstrip('/'), revision=revision, recursive=True):
        if hasattr(entry, 'blob_id'):
            entries.append(entry)
        else:
            require(entry.path == prefix + 'expert', 'Unexpected remote directory')
        require(len(entries) <= len(allowed), 'Remote tree enumeration budget')
    byname = snapshot_metadata(manifest, entries, prefix, original)
    require(meta.blob_id == byname['artifacts.json'].blob_id and meta.size == byname['artifacts.json'].size,
            'Manifest metadata/tree disagree')
    checksums = dict(manifest, **{'artifacts.json': digest(source)})
    for name, checksum in sorted(checksums.items()):
        destination = no_links(base / name)
        require(download or destination.is_file(), 'Missing local artifact (explicit fetch required)')
        e = byname[name]
        payload = remote.get(dict(repo=REPO, revision=revision, path=prefix + name, sha256=checksum),
                             metadata=e, cached=destination if destination.exists() else None)
        if not destination.exists():
            destination.parent.mkdir(parents=True, exist_ok=True)
            no_links(destination)
            with destination.open('xb') as target, Path(payload).open('rb') as source_stream:
                shutil.copyfileobj(source_stream, target)
        require(digest(destination) == checksum, 'Restored hash mismatch')
        if name.endswith('.json'):
            # Reuse only authenticated compact validator; no model tensor JSON.
            import audit_expert_replicas_v1 as audit
            audit.compact_json(read(destination))
    restore_safety(base, allowed)
    require({p.relative_to(base).as_posix() for p in base.rglob('*') if p.is_file()} == allowed, 'Local file coverage')
    return dict(replica=replica, run=run_name(replica, original), repo=REPO, revision=revision,
        files=len(allowed), bytes=sum(e.size for e in entries), manifestSha256=checksums['artifacts.json'],
        manifest=manifest, metadataFirst=True, remoteEvidence=list(remote.evidence))


def fetch(replica, revision, output, api=None):
    """Explicit bounded compact download, never source/models/reference or jobs."""
    helpers = authenticate_helpers()
    if api is None:
        from huggingface_hub import HfApi
        api = HfApi()
    output = no_links(output)
    remote = helpers['audit_neural'].RemoteFiles(api)
    report = authenticate_snapshot(replica, revision, output / 'restored', remote, download=True)
    write_new(output / 'download-verification.json', report)
    return report


def expected_environment(replica, segment):
    replica_id(replica)
    require(type(segment) is int and segment in (1, 2), 'Exactly two segments')
    env = dict(RUN_ID=run_name(replica, segment == 1), MODEL_REPO=REPO, DATASET_REPO=DATASET,
        SOURCE_PATH=SOURCE_PATH, SOURCE_REVISION=SOURCE_REVISION, SOURCE_SHA256=SOURCE_SHA, SOURCE_COMMIT=SOURCE,
        EXPERT_REPLICA=str(replica), EXPERT_WORKERS='6', EXPERT_SMOKE='0', REPLICA_SEGMENT=str(segment),
        PYTHONUNBUFFERED='1', PYTHONDONTWRITEBYTECODE='1', HF_HUB_DISABLE_PROGRESS_BARS='1', HF_HUB_DISABLE_XET='1')
    env.update(dict.fromkeys(('OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'OPENBLAS_NUM_THREADS',
                             'NUMEXPR_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS'), '1'))
    if segment == 2:
        env.update(RESUME_RUN=run_name(replica, True), RESUME_REVISION=PINS[replica]['original'])
    return env


def expected_labels(replica, segment):
    return dict(project='powergrid-multimap', stage='expert-replicas-v1', group=GROUP,
                replica=str(replica), segment=str(segment))


def frozen_command():
    tree = ast.parse(git_bytes('ai/multimap/launch_expert_replicas_v1.py'))
    values = [ast.literal_eval(n.value) for n in tree.body if isinstance(n, ast.Assign)
              and any(isinstance(t, ast.Name) and t.id == 'BOOTSTRAP' for t in n.targets)]
    require(len(values) == 1 and type(values[0]) is str, 'Single original literal bootstrap')
    return ['bash', '-lc', 'python -m pip install --no-cache-dir --disable-pip-version-check '
            'huggingface_hub==1.29.0 && python -c ' + shlex.quote(values[0])]


def launch_receipts(auditGitReceiptCommit):
    immutable(auditGitReceiptCommit)
    require(subprocess.run(['git', 'merge-base', '--is-ancestor', LAUNCH_COMMIT, auditGitReceiptCommit],
                           cwd=ROOT, capture_output=True).returncode == 0, 'Continuation receipt Git ancestry')
    receipts = []
    for name, commit in (('expert-replicas-launch-v1.json', LAUNCH_COMMIT),
                         ('expert-replicas-continuations-v1.json', auditGitReceiptCommit)):
        path = no_links(HERE / name)
        require(path.read_bytes() == git_bytes('ai/multimap/' + name, commit), 'Receipt differs from anchored Git: ' + name)
        receipts.append(read(path))
    first, continuation = receipts
    exact(continuation['originalLaunchReceiptGitCommit'], LAUNCH_COMMIT, 'Original receipt Git anchor')
    exact(continuation['originalLaunchReceiptSha256'], digest(HERE / 'expert-replicas-launch-v1.json'), 'Original receipt SHA')
    source = first['source']
    exact(continuation['source'], source, 'Continuation unchanged source')
    for k, v in dict(sourceCommit=SOURCE, sourceRevision=SOURCE_REVISION, sourceSha256=SOURCE_SHA,
                     sourcePath=SOURCE_PATH, sourceBytes=49280401, group=GROUP).items():
        exact(source[k], v, 'Literal source pin: ' + k)
    require(first['sourceDatasetRepo'] == DATASET and first['modelRepo'] == REPO, 'Pinned repositories')
    exact(source['protocolSha256'], digest(HERE / 'expert-replicas-protocol-v1.json'), 'Protocol receipt SHA')
    exact(source['preflightSha256'], digest(HERE / 'expert-replicas-preflight-v1.json'), 'Preflight receipt SHA')
    jobs = {}
    for segment, receipt in enumerate(receipts, 1):
        require(receipt['group'] == GROUP and len(receipt['jobs']) == 2, 'Both replicas must be reported')
        require({r['replica'] for r in receipt['jobs']} == {1, 2}, 'Receipt replica coverage')
        for record in receipt['jobs']:
            replica = replica_id(record['replica'])
            exact(record['env'], expected_environment(replica, segment), 'Expected nonsecret job environment')
            require(record['segment'] == segment and record['source'] == source and record['sourceCommit'] == SOURCE
                    and record['run'] == run_name(replica, segment == 1) and record['group'] == GROUP,
                    'Receipt run/segment/source identity')
            require(record['jobId'] == PINS[replica]['originalJob' if segment == 1 else 'job'] and
                    record['image'] == IMAGE and record['flavor'] == 'cpu-upgrade' and record['timeout'] == '3h',
                    'Receipt literal job/image/budget')
            require(record['maxSegmentsPerReplica'] == 2 and record['maxTotalJobHours'] == 12 and
                    record['plannedGames'] == 6240 and record['groupPlannedGames'] == 12480,
                    'Preregistered group game/hour budget')
            if segment == 2:
                require(record['resumeRevision'] == PINS[replica]['original'] and
                        record['recoveryFromJob'] == PINS[replica]['originalJob'], 'Same-replica original-only recovery')
            jobs[replica, segment] = record
    return jobs, dict(source=source, auditGitReceiptCommit=auditGitReceiptCommit, originalReceiptGit=LAUNCH_COMMIT,
        originalReceiptSha256=digest(HERE / 'expert-replicas-launch-v1.json'),
        continuationReceiptSha256=digest(HERE / 'expert-replicas-continuations-v1.json'))


def verify_job_config(job, receipt, command):
    r, s = receipt['replica'], receipt['segment']
    require(job.id == receipt['jobId'] and job.environment == expected_environment(r, s) and
            job.docker_image == IMAGE and job.flavor == 'cpu-upgrade' and job.command == command and
            not job.arguments and not getattr(job, 'volumes', None) and not getattr(job, 'space_id', None),
            'Actual HF job config differs (details suppressed to avoid secrets)')
    require(all((job.labels or {}).get(k) == v for k, v in expected_labels(r, s).items()), 'HF job labels differ')


def bounded_log(lines):
    parts, size = [], 0
    for line in lines:
        require(type(line) is str, 'Unexpected job log packet')
        size += len(line.encode()) + 1
        require(size <= LOG_LIMIT, 'Job log byte budget')
        parts.append(line)
    return '\n'.join(parts)


def verify_log(log, replica, segment, final_revision=None):
    # Frozen startup tests themselves print mocked runtime-ready/complete events.
    # Only events after the successful Python suite belong to production; Node
    # startup checks must have succeeded before that boundary as well.
    boundaries = list(re.finditer(r'^Ran 34 tests in [^\n]+\n\s*\n?OK(?:\n|$)', log, re.MULTILINE))
    require(len(boundaries) == 1, 'Single successful frozen Python startup suite')
    boundary = boundaries[0].end()
    startup, production = log[:boundary], log[boundary:]
    require(re.search(r'(?:#|ℹ) tests 7', startup) and re.search(r'(?:#|ℹ) pass 7', startup) and
            re.search(r'(?:#|ℹ) fail 0', startup), 'Frozen 34 Python / 7 Node startup tests')
    events = [json.loads(line) for line in production.splitlines() if line.startswith('{"stage":')]
    ready = [e for e in events if e.get('stage') == 'uploaded' and e.get('label') == 'runtime-ready']
    require(len(ready) == 1 and events[0] == ready[0], 'Single production runtime-ready boundary')
    require(set(ready[0]) == {'stage', 'label', 'revision'}, 'Production runtime-ready schema')
    runtime_ready = dict(stage='runtime-ready', revision=immutable(ready[0]['revision']))
    events = events[1:]
    require(all(e['stage'] in ('uploaded', 'expert-ppo', 'complete') for e in events), 'Unexpected production event')
    updates = [e['update'] for e in events if e['stage'] == 'expert-ppo']
    exact(updates, list(range(1, 33)) if segment == 1 else [], 'No repeated/resumed optimization')
    uploads = [e for e in events if e['stage'] == 'uploaded']
    labels = (['initial', 'warmup', *('update-' + str(u) for u in range(1, 33)), 'confirmation-selected']
              if segment == 1 else ['confirmation-teacher', 'complete', 'complete'])
    exact([e['label'] for e in uploads], labels, 'Exact original/continuation publication sequence')
    sequence = [(e['stage'], e.get('label') if e['stage'] == 'uploaded' else e.get('update')) for e in events]
    expected_sequence = ([('uploaded', 'initial'), ('uploaded', 'warmup')] +
        [event for u in range(1, 33) for event in (('uploaded', 'update-' + str(u)), ('expert-ppo', u))] +
        [('uploaded', 'confirmation-selected')] if segment == 1 else
        [('uploaded', label) for label in labels] + [('complete', None)])
    exact(sequence, expected_sequence, 'Selection must be committed strictly before confirmation')
    for e in uploads:
        immutable(e['revision'])
    require(len({e['revision'] for e in uploads}) == len(uploads), 'Duplicate uploaded revision')
    if segment == 1:
        require(next(e['revision'] for e in uploads if e['label'] == 'update-32') == PINS[replica]['selection'] and
                uploads[-1]['revision'] == PINS[replica]['original'], 'Preconfirmation selection/original immutable revisions')
    else:
        require(uploads[-1]['revision'] == final_revision and events[-1]['stage'] == 'complete' and
                events[-1]['run'] == run_name(replica), 'Completed final revision/run')
    return dict(logSha256=sha(log.encode()), logBytes=len(log.encode()), optimizationUpdates=updates,
                runtimeReady=runtime_ready, uploads=[dict(stage=e['label'], revision=e['revision']) for e in uploads],
                completeResult=events[-1]['result'] if segment == 2 else None,
                pythonStartupTests=34, nodeStartupTests=7, startupIsNotProduction=True)


def verify_upload_receipts(status, job):
    # The currently uploaded snapshot cannot yet contain its own commit ID.
    exact(status['receipts'], [job['runtimeReady'], *job['uploads'][:-1]],
          'Entire ordered upload chain, including production runtime-ready')


def verify_jobs(api, receipts, replica, revision):
    command = frozen_command()
    inventory = []
    for item in api.list_jobs(namespace='coyotte508', labels={'group': GROUP}, timeout=30):
        inventory.append(item.id)
        require(len(inventory) <= 4, 'Group exceeds four-job budget')
    require(len(set(inventory)) == 4 and set(inventory) == {r['jobId'] for r in receipts.values()},
            'Missing/duplicate/unreceipted/replacement group job')
    reports, actual = [], {}
    for slot, record in sorted(receipts.items()):
        job = api.inspect_job(job_id=record['jobId'], namespace='coyotte508')
        verify_job_config(job, record, command)
        actual[slot] = job
        if slot[1] == 1:
            require(job.status.stage == 'ERROR' and job.status.message == 'Job timeout',
                    'Both original slots ended by timeout, not success-dependent replacement')
        if slot[0] != replica:
            continue
        segment = slot[1]
        require(job.status.stage == ('ERROR' if segment == 1 else 'COMPLETED'), 'Original timeout / completed continuation required')
        if segment == 1:
            require(job.status.message == 'Job timeout', 'Original must be operational timeout, not completed replacement')
        log = bounded_log(api.fetch_job_logs(job_id=job.id, namespace='coyotte508', follow=False))
        report = verify_log(log, replica, segment, revision)
        report.update(jobId=job.id, segment=segment, status=job.status.stage,
                      startedAt=str(job.started_at), finishedAt=str(job.finished_at),
                      frozenCommandSha256=sha(canonical(command).encode()), actualNonsecretConfigVerified=True)
        reports.append(report)  # no full JobInfo/environment/log dump
    for r in (1, 2):
        before, after = actual[r, 1], actual[r, 2]
        require(before.finished_at is not None and after.started_at is not None, 'Job chronology timestamps required')
        old_end = datetime.fromisoformat(str(before.finished_at).replace('Z', '+00:00'))
        new_start = datetime.fromisoformat(str(after.started_at).replace('Z', '+00:00'))
        require(old_end < new_start, 'Continuation cannot overlap original')
    return dict(groupJobIds=sorted(inventory), targetJobs=reports, maxSegmentsPerReplica=2,
                maxAuthorizedHours=12, timeoutEvidence='Git-pinned creation request; not exposed by HF inspection')


def local_source_difference(name, archived, local):
    if archived == local:
        return None
    require(name in {'ai/multimap/README.md', 'ai/multimap/runs.json', 'ai/multimap/expert-replicas-v1-design.md'},
            'Frozen source drift: ' + name)
    return dict(sourceSha256=archived, localSha256=local, note='Explicit nonserving documentation/bookkeeping only')


def cached_pin(remote, pin):
    """No model payload download fallback; existing HF snapshot links are supported."""
    from huggingface_hub import try_to_load_from_cache
    cached = try_to_load_from_cache(pin['repo'], pin['path'], revision=pin['revision'], repo_type=pin.get('repo_type', 'model'))
    require(isinstance(cached, str), 'Required immutable model is not cached; downloads need separate authorization')
    metadata = remote.describe(pin)
    require(type(metadata.size) is int and 0 < metadata.size <= FILE_LIMIT, 'Frozen model metadata byte budget')
    return remote.get(pin, metadata=metadata, cached=cached)


def finite_state(state, expected):
    import torch
    require(isinstance(state, dict) and state.keys() == expected.keys(), 'Complete model tensor keys')
    for name, tensor in state.items():
        template = expected[name]
        require(isinstance(tensor, torch.Tensor) and tensor.dtype == template.dtype and tensor.shape == template.shape
                and tensor.device.type == 'cpu' and torch.isfinite(tensor).all().item(), 'Model tensor dtype/shape/finite: ' + name)


def frozen_models(protocol, config, remote, helpers):
    import torch
    from model import GraphPolicy, SCHEMA
    from residual import ResidualPolicy
    paths = [cached_pin(remote, pin) for pin in [protocol['warmStart'], *protocol['opponentPool']]]
    warm = torch.load(paths[0], map_location='cpu', weights_only=True)
    require(warm['schema'] == SCHEMA and warm['width'] == 64, 'Frozen representation schema/width')
    finite_state(warm['state_dict'], GraphPolicy(64).state_dict())
    # Immutable warmStart digest/revision authenticates the entire original model;
    # source provenance for PPO checkpoints is additionally compared to old Git.
    old_source = '4ca026e34b7ba9743cfa4d4811277a8ac31258ba'
    class CachedRemote:
        def get(self, pin):
            return cached_pin(remote, pin)
    reports = helpers['audit_expert'].reuse(helpers['audit_neural'].verify_candidates,
        SOURCE=old_source, NAMESPACE=protocol['seedNamespace'], git_bytes=git_bytes)(
            dict(members=protocol['opponentPool']), config, CachedRemote())
    for pin, path in zip(protocol['opponentPool'], paths[1:]):
        saved = torch.load(path, map_location='cpu', weights_only=True)
        require(saved['schema'] == 'multimap-residual-ppo-v1' and saved['width'] == 64 and saved['bound'] == 8,
                'Frozen opponent model identity')
        finite_state(saved['state_dict'], ResidualPolicy(64, 8).state_dict())
        require(digest(path) == pin['sha256'], 'Frozen model content')
    return paths, dict(warmStart=protocol['warmStart'], opponents=reports, allModelTensorsFinite=True)


def verify_runtime_source(replica, base, remote, helpers):
    audit = helpers['audit_expert_replicas_v1']
    config = read(Path(base) / 'expert/config.json')
    source = no_links(ROOT / 'ai/runs' / GROUP / 'source.tgz')
    require(source.is_file() and source.stat().st_size == 49280401 and digest(source) == SOURCE_SHA, 'Local source archive pin')
    source = remote.get(dict(repo=DATASET, repo_type='dataset', revision=SOURCE_REVISION,
                             path=SOURCE_PATH, sha256=SOURCE_SHA), cached=source)
    report = helpers['audit_expert'].reuse(helpers['audit_neural'].verify_source, ROOT=ROOT, HERE=HERE,
        SOURCE=SOURCE, SOURCE_NAMES=set(config['sourceFiles']), git_bytes=git_bytes,
        local_source_difference=local_source_difference)(source, config)
    require(report['manifestFiles'] == 1381, 'Complete 1381-file source archive')
    # Only import serving dependencies after their archive/Git/local hashes match.
    from expert_replicas_v1 import Replica
    artifact = ROOT / 'ai/runs/multimap-reference-preflight-v1/artifact'
    no_links(artifact)
    reference_python = ROOT / 'ai/.venv-reference/bin/python'
    runner = Replica(replica)
    rebuilt = runner.config(False, runner.protocol, workers=6, artifact=artifact, reference_python=reference_python)
    exact(config, rebuilt, 'Full 42-module/dependencies/reference/runtime/serving identity')
    environment = helpers['audit_neural'].verify_environment(runner.protocol, read(Path(base) / 'environment.json'), config)
    reference = helpers['audit_gap'].verify_reference(dict(runner.protocol, compressedArchiveRamMaxBytes=LIMIT),
                                                     read(Path(base) / 'recovery.json'), remote)
    require(sum(p.stat().st_size for p in reference_python.parent.parent.rglob('*') if p.is_file()) <=
            runner.protocol['referenceVenvMaxBytes'], 'Reused reference venv budget')
    with __import__('torch').random.fork_rng(devices=[]):
        paths, models = frozen_models(runner.protocol, config, remote, helpers)
    audit.exact(config['protocol'], audit.protocol_for(replica), 'Independent replica scope')
    return dict(source=report, environment=environment, reference=reference, frozenModels=models,
                fullConfigSha256=digest(Path(base) / 'expert/config.json')), paths


def load_checkpoint(path, config, *, transaction=False):
    import torch
    from expert_policy import ExpertPolicy
    path = no_links(path)
    require(path.is_file() and 0 < path.stat().st_size <= FILE_LIMIT, 'Bounded regular checkpoint')
    saved = torch.load(path, map_location='cpu', weights_only=True)
    require(type(saved) is dict and set(saved) == (TRANSACTION_KEYS if transaction else MODEL_KEYS), 'Exact checkpoint keys')
    exact(saved['config'], config, 'Checkpoint complete config')
    require(saved['schema'] == 'multimap-expert-ppo-v2' and type(saved['width']) is int and saved['width'] == 64 and
            type(saved['bound']) is int and saved['bound'] == 16 and saved['priorAsActionFeature'] is True, 'Checkpoint architecture metadata')
    require(saved['stage'] in ('initial', 'warmup', 'train') and type(saved['update']) is int and
            0 <= saved['update'] <= 32 and (saved['stage'] == 'train' or saved['update'] == 0), 'Checkpoint stage/update')
    with torch.random.fork_rng(devices=[]):
        model = ExpertPolicy(64, 16)
        finite_state(saved['state_dict'], model.state_dict())
        model.load_state_dict(saved['state_dict'], strict=True)
        if transaction:
            verify_optimizer(saved, model, config['protocol'])
    return saved


def verify_optimizer(saved, model, protocol):
    import torch
    stage = saved['stage']
    optimizer = torch.optim.AdamW(model.parameters(), lr=protocol['learningRate' if stage == 'train' else 'warmupLearningRate'],
                                  weight_decay=protocol['weightDecay'])
    state = saved['optimizer']
    require(type(state) is dict and set(state) == {'state', 'param_groups'}, 'Exact optimizer schema')
    expected = optimizer.state_dict()
    # Tensor_equal, not tolerant metrics: all booleans/types/groups/order are fixed.
    from audit_expert import tensor_equal
    tensor_equal(state['param_groups'], expected['param_groups'], 'Optimizer parameter groups/recipe')
    parameters = list(model.parameters())
    ids = expected['param_groups'][0]['params']
    expected_history = [] if stage == 'initial' else [('warmup', 0)] + [('train', u) for u in range(1, saved['update'] + 1)]
    require(type(saved['history']) is list and [(h['stage'], h['update']) for h in saved['history']] == expected_history,
            'Committed ordered history')
    steps = sum(h['optimization']['optimizerSteps'] for h in saved['history']
                if (h['stage'] == 'train') == (stage == 'train'))
    require(type(steps) is int and steps >= 0 and (stage == 'initial' or steps > 0), 'Optimizer committed step sum')
    require(type(state['state']) is dict and all(type(k) is int for k in state['state']) and
            set(state['state']) == (set(ids) if steps else set()), 'Complete optimizer state coverage')
    for index, parameter in zip(ids, parameters):
        if not steps:
            continue
        item = state['state'][index]
        require(type(item) is dict and set(item) == {'step', 'exp_avg', 'exp_avg_sq'}, 'Optimizer state keys')
        for key, value in item.items():
            require(isinstance(value, torch.Tensor) and value.device.type == 'cpu' and torch.isfinite(value).all().item(),
                    'Finite CPU optimizer tensor')
            if key == 'step':
                require(value.shape == torch.Size([]) and value.dtype == torch.float32 and value.item() == steps, 'Optimizer exact step count')
            else:
                require(value.shape == parameter.shape and value.dtype == parameter.dtype, 'Optimizer moment shape/dtype')
        require((item['exp_avg_sq'] >= 0).all().item(), 'Nonnegative second moments')
    optimizer.load_state_dict(state)
    rng = saved['torchRng']
    require(isinstance(rng, torch.Tensor) and rng.dtype == torch.uint8 and rng.dim() == 1, 'Torch RNG encoding')
    torch.Generator().set_state(rng)
    random.Random().setstate(saved['pythonRng'])


def checkpoint_projection(saved, path):
    """Actual decoded checkpoint values only; no expected-JSON argument exists."""
    projected = {k: copy.deepcopy(saved[k]) for k in PROJECTION_KEYS}
    projected['lastSha256'] = digest(path)
    canonical(projected)
    return projected


def committed_names(saved):
    """Derive immutable output boundary from last.pt, NOT uploaded manifest keys.

    best.pt/history.json are handled separately: uploads can precede last.pt.
    Uncommitted plan/outcome files are deliberately excluded.
    """
    stage, update = saved['stage'], saved['update']
    require(stage in ('initial', 'warmup', 'train') and type(update) is int and 0 <= update <= 32 and
            (stage == 'train' or update == 0), 'Invalid committed boundary')
    names = {'expert/config.json', 'expert/initial.pt', 'expert/selection-plan.json',
             'expert/selection-0.json', 'expert/selection-teacher.json'}
    if stage != 'initial':
        names |= {'expert/warmup-plan.json', 'expert/warmup.json', 'expert/warmup.pt', 'expert/selection-warmup.json'}
    if stage == 'train':
        names |= {f'expert/{p}-{u}.json' for u in range(1, update + 1) for p in ('train', 'train-plan')}
        names |= {f'expert/selection-{u}.json' for u in range(8, update + 1, 8)}
    confirmations = saved['confirmations']
    require(type(confirmations) is dict and set(confirmations) <= {'selected', 'teacher'} and
            ('teacher' not in confirmations or 'selected' in confirmations), 'Confirmation committed order')
    if confirmations:
        require(stage == 'train' and update == 32, 'Confirmation before selection completed')
        names.add('expert/confirmation-plan.json')
        names |= {f'expert/confirmation-{label}.json' for label in confirmations}
    if saved['result'] is not None:
        require(set(confirmations) == {'selected', 'teacher'}, 'Result before both confirmations')
        names.add('expert/result.json')
    return names


def verify_inherited(original, final, saved, old_manifest, final_manifest):
    original, final = Path(original), Path(final)
    names = committed_names(saved)
    # Uploaded best/history may be ahead; only count them if they agree with the
    # authenticated transaction. Embedded best itself is always checked in chain.
    if old_manifest.get('expert/best.pt') == saved['bestSha256']:
        names.add('expert/best.pt')
    if read(original / 'expert/history.json') == saved['history']:
        names.add('expert/history.json')
    for label, record in saved['confirmations'].items():
        require(old_manifest[f'expert/confirmation-{label}.json'] == record['sha256'], 'Original committed confirmation hash')
    for name in sorted(names):
        require(name in old_manifest and name in final_manifest and old_manifest[name] == final_manifest[name] ==
                digest(original / name) == digest(final / name), 'Inherited committed output changed: ' + name)
    return dict(boundary=dict(stage=saved['stage'], update=saved['update'], confirmations=sorted(saved['confirmations'])),
                files={name: old_manifest[name] for name in sorted(names)},
                excludedUploadedFiles=sorted(set(old_manifest) - names))


def unchanged_transaction(before, after, best_path):
    import torch
    from expert_policy import load
    from audit_expert import tensor_equal
    require(before.keys() == after.keys(), 'Transaction schema changed')
    allowed = {'confirmations', 'result', 'torchRng'}
    for key in before.keys() - allowed:
        tensor_equal(before[key], after[key], 'No optimization/reselection transaction change: ' + key)
    with torch.random.fork_rng(devices=[]):
        torch.set_rng_state(before['torchRng'])
        load(best_path)  # exactly ONE frozen constructor (no optimizer/forward)
        tensor_equal(torch.get_rng_state(), after['torchRng'], 'Exactly one selected-model constructor RNG advance')
    for label, record in before['confirmations'].items():
        tensor_equal(record, after['confirmations'].get(label), 'Previously committed confirmation unchanged')
    return sorted(before.keys() - allowed)


def verify_checkpoint_chain(replica, base, original, selection_path, warm_path, helpers):
    import torch
    from expert_policy import warm_start, load
    from audit_expert import tensor_equal
    audit = helpers['audit_expert_replicas_v1']
    base, original, selection_path = Path(base), Path(original), Path(selection_path)
    config = read(base / 'expert/config.json')
    with torch.random.fork_rng(devices=[]):
        stages = {name: load_checkpoint(base / f'expert/{name}.pt', config, transaction=name == 'last')
                  for name in ('initial', 'warmup', 'best', 'last')}
        old = load_checkpoint(original / 'expert/last.pt', config, transaction=True)
        selection = load_checkpoint(selection_path, config, transaction=True)
        # All original checkpoint files, not only last.pt, must be finite/valid.
        for name in ('initial', 'warmup', 'best'):
            load_checkpoint(original / f'expert/{name}.pt', config)
        initial_model = helpers['audit_expert'].reuse(warm_start, PROTOCOL=config['protocol'])(warm_path)
        tensor_equal(stages['initial']['state_dict'], initial_model.state_dict(), 'Original warm-start representation/zero head')
        for name in ('network.action.2.weight', 'network.action.2.bias'):
            require(torch.count_nonzero(stages['initial']['state_dict'][name]).item() == 0, 'Initial zero actor')
        for name, stage, update in (('initial', 'initial', 0), ('warmup', 'warmup', 0),
                                   ('best', 'train', PINS[replica]['bestUpdate'])):
            require(stages[name]['stage'] == stage and stages[name]['update'] == update, 'Stage checkpoint metadata')
        final = stages['last']
        for record in (selection, old, final):
            require(record['stage'] == 'train' and record['update'] == 32 and record['bestStage'] == 'train' and
                    record['bestUpdate'] == PINS[replica]['bestUpdate'], 'Completed training/immutable selected checkpoint')
            require(isinstance(record['bestArtifact'], bytes) and sha(record['bestArtifact']) == record['bestSha256'] ==
                    digest(base / 'expert/best.pt') == PINS[replica]['bestSha256'], 'Embedded best bytes/hash')
            _, embedded = load(io.BytesIO(record['bestArtifact']))
            tensor_equal(embedded, stages['best'], 'Embedded best metadata/tensors')
        require(selection['confirmations'] == {} and selection['result'] is None and
                set(old['confirmations']) == {'selected'} and old['result'] is None and
                set(final['confirmations']) == {'selected', 'teacher'} and final['result'] is not None,
                'Exact selection/original/final confirmation chronology')
        unchanged = unchanged_transaction(selection, old, base / 'expert/best.pt')
        unchanged_transaction(old, final, base / 'expert/best.pt')
        # For replica 2 selected update32 is also the final trained model.
        if final['bestUpdate'] == 32:
            tensor_equal(stages['best']['state_dict'], final['state_dict'], 'Selected final-update model tensor identity')
        for root, record in ((base, final), (original, old)):
            exact(read(root / 'expert/history.json'), record['history'], 'History committed bytes/metadata')
            for label, committed in record['confirmations'].items():
                path = root / f'expert/confirmation-{label}.json'
                saved_json = read(path)
                audit.equal_summary(committed, dict(summary=audit.summary(saved_json['games']), sha256=digest(path)),
                                    'Actual committed confirmation summary/hash')
        exact(read(base / 'expert/result.json'), final['result'], 'Committed result')
        inherited = verify_inherited(original, base, old, read(original / 'artifacts.json'), read(base / 'artifacts.json'))
        report = dict(finalCheckpoint=checkpoint_projection(final, base / 'expert/last.pt'),
            selectionCommit=dict(revision=PINS[replica]['selection'], checkpointSha256=digest(selection_path),
                                 projection=checkpoint_projection(selection, selection_path)),
            originalCheckpointSha256=digest(original / 'expert/last.pt'), inherited=inherited,
            unchangedKeys=unchanged, constructorAdvances={'selectionToOriginal': 1, 'originalToContinuation': 1},
            finiteModelCheckpoints=9, allOptimizerParametersAndExactStepsVerified=True,
            initialZeroHeadAndWarmStartVerified=True, embeddedBestBytesVerified=True)
    return report


def audit_integrity(replica, revision, root, output, *, auditGitReceiptCommit,
                    original_root=None, selection_checkpoint=None, api=None):
    """Read-only remote authentication + local integrity; no games or downloads.

    Writes separate evidence.json and external-integrity.json ONLY after success.
    The latter is the exact schema consumed by audit_expert_replicas_v1.py.
    """
    replica_id(replica)
    immutable(revision)
    helpers = authenticate_helpers()
    audit = helpers['audit_expert_replicas_v1']
    root, output = no_links(root), no_links(output)
    require(not output.is_relative_to(root), 'Evidence must be separate from snapshot')
    receipts, launch = launch_receipts(auditGitReceiptCommit)
    if api is None:
        from huggingface_hub import HfApi
        api = HfApi()
    remote = helpers['audit_neural'].RemoteFiles(api)
    recovery = ROOT / 'ai/runs' / run_name(replica, True) / 'recovery'
    original_root = no_links(original_root or recovery / 'restored')
    selection_checkpoint = no_links(selection_checkpoint or recovery / 'selection-last.pt')
    final = authenticate_snapshot(replica, revision, root, remote)
    original = authenticate_snapshot(replica, PINS[replica]['original'], original_root, remote, original=True)
    pin = dict(repo=REPO, revision=PINS[replica]['selection'], path='runs/' + run_name(replica, True) + '/expert/last.pt')
    meta = remote.describe(pin)
    require(type(meta.size) is int and 0 < meta.size <= FILE_LIMIT, 'Selection transaction metadata bound')
    remote.get(pin, metadata=meta, cached=selection_checkpoint)
    pending = audit.audit_complete(root, replica)  # independently validates EVERY saved plan/outcome/selector
    jobs = verify_jobs(api, receipts, replica, revision)
    status, old_status = read(root / 'status.json'), read(original_root / 'status.json')
    exact(status['resume'], dict(run=run_name(replica, True), revision=PINS[replica]['original'],
          files={n: h for n, h in original['manifest'].items() if n.startswith('expert/')}), 'Exact inherited snapshot identity')
    for actual, is_original in ((status, False), (old_status, True)):
        for key, expected in dict(sourceRevision=SOURCE_REVISION, sourceSha256=SOURCE_SHA,
                sourceRepo=DATASET, sourcePath=SOURCE_PATH, run=run_name(replica, is_original)).items():
            exact(actual[key], expected, 'Snapshot/job source binding: ' + key)
    require(old_status['stage'] == 'confirmation-selected', 'Original committed upload stage')
    exact(jobs['targetJobs'][1]['completeResult'], status['result'], 'Actual HF completion result equals committed result')
    exact(read(original_root / 'protocol.json'), read(root / 'protocol.json'), 'Original/continuation protocol identity')
    old_environment = read(original_root / 'environment.json')
    exact(old_environment['versions'], read(root / 'expert/config.json')['runtimeVersions'], 'Original runtime versions')
    protocol = audit.protocol_for(replica)
    require(old_environment['requirementsSha256'] == protocol['referenceRequirementsSha256'] and
            type(old_environment['referenceVenvBytes']) is int and
            0 < old_environment['referenceVenvBytes'] <= protocol['referenceVenvMaxBytes'], 'Original environment pins/budget')
    verify_upload_receipts(old_status, jobs['targetJobs'][0])
    verify_upload_receipts(status, jobs['targetJobs'][1])
    provenance, model_paths = verify_runtime_source(replica, root, remote, helpers)
    tensors = verify_checkpoint_chain(replica, root, original_root, selection_checkpoint, model_paths[0], helpers)
    # Gate compares independently decoded actual projections to independent JSON
    # expectations. No expected projection is ever used to construct the receipt.
    evidence = dict(schema='multimap-expert-replica-integrity-evidence-v1', replica=replica, revision=revision,
        auditorSha256=digest(Path(__file__)), testsSha256=digest(HERE / 'test_audit_expert_replicas_integrity_v1.py'),
        sourceGit=SOURCE, helperSha256=HELPERS, launch=launch, jobs=jobs, finalSnapshot=final,
        originalSnapshot=original, provenance=provenance, checkpoints=tensors,
        verifiedRemoteFiles=list(remote.evidence), boundedAuthenticatedBytes=remote.bounded_bytes,
        jsonManifestSha256=pending['manifestSha256'], savedTerminalOutcomes=pending['coverage']['savedTerminalOutcomes'],
        replay=dict(status='not-requested', newIndependentObservations=0),
        limitations=[__doc__.split('Limits: ', 1)[1].strip()], qualified=False, qualificationEligible=False,
        reservedFinalSeedsUsed=False, promoted=False, deployed=False)
    evidence_raw = (json.dumps(evidence, indent=2, sort_keys=True, allow_nan=False) + '\n').encode()
    receipt = dict(schema='multimap-expert-replica-external-integrity-v1', replica=replica,
        manifestSha256=final['manifestSha256'], evidenceSha256=sha(evidence_raw),
        checks=dict.fromkeys(audit.EXTERNAL_CHECKS, True), finalCheckpoint=tensors['finalCheckpoint'],
        selectionCommit=tensors['selectionCommit'])
    audit.audit_complete(root, replica, integrity=receipt)  # fails closed before any success receipt write
    write_new(output / 'evidence.json', evidence)
    write_new(output / 'external-integrity.json', receipt)
    return receipt


REPLAY_SCOPES = (
    ('Germany', 2, 'recharged', True, 0, 0),
    ('Germany', 6, 'recharged', True, 1, 5),
    ('USA', 3, 'recharged', True, 0, 1),
    ('USA', 5, 'original', True, 1, 4),
    ('France', 4, 'recharged', False, 0, 2),
    ('France', 2, 'original', True, 1, 1),
    ('UK & Ireland', 5, 'recharged', True, 0, 3),
    ('UK & Ireland', 6, 'original', False, 1, 0),
)


def replay_tasks(replica):
    """16 scope-only confirmation replays, fixed BEFORE final results.

    The eight registered (map,players,variant,fastBid,deal,focalSeat) tuples
    cover all four maps/five player counts/four rules, including the watched
    Germany2 and USA3 recharged/fast scopes. Both selected and teacher arms.
    Singleton collections preserve the exact immutable canonical full spec and
    fixed opponents. No stochastic training or selection replay is claimed.
    """
    import audit_expert_replicas_v1 as audit
    keys = ('map', 'players', 'variant', 'fastBid', 'deal', 'focalSeat')
    batches = []
    for label, teacher in (('confirmation-selected', False), ('confirmation-teacher', True)):
        plan = audit.expected_plan(replica_id(replica), 'confirmation', teacher=teacher)
        for scope in REPLAY_SCOPES:
            matches = [s for s in plan if tuple(s[k] for k in keys) == scope]
            require(len(matches) == 1, 'Unique preregistered replay scope')
            batches.append((label, matches))
    return batches


def replay(replica, root, output, *, allow_games=False):
    require(allow_games is True, 'Explicit allow_games=True required for real evaluation replays')
    helpers = authenticate_helpers()
    audit = helpers['audit_expert_replicas_v1']
    root, output = no_links(root), no_links(output)
    receipt = read(output / 'external-integrity.json')
    require(digest(output / 'evidence.json') == receipt['evidenceSha256'], 'Retained independent integrity evidence binding')
    audit.audit_complete(root, replica, integrity=receipt)
    # Re-authenticate current local serving runtime/reference before any game.
    from huggingface_hub import HfApi
    remote = helpers['audit_neural'].RemoteFiles(HfApi())
    _, paths = verify_runtime_source(replica, root, remote, helpers)
    import torch
    from expert_replicas_v1 import Replica
    from expert_policy import load
    from residual import load as load_opponent
    runner = Replica(replica)
    with torch.random.fork_rng(devices=[]):
        opponents = {pin['name']: load_opponent(path)[0].eval() for pin, path in zip(runner.protocol['opponentPool'], paths[1:])}
    checks, counts = [], Counter()
    began = time.monotonic()
    prior_deterministic = torch.are_deterministic_algorithms_enabled()
    try:
        torch.use_deterministic_algorithms(True)
        with torch.random.fork_rng(devices=[]):
            for label, tasks in replay_tasks(replica):
                stored = {canonical(r['spec']): r for r in read(root / f'expert/{label}.json')['games']}
                model, _ = load(root / 'expert/best.pt')
                rows, outcomes = runner.collect(model, tasks, workers=6, training=False, mode='evaluation',
                    seed=runner.protocol['seed'], protocol=runner.protocol, opponents=opponents,
                    artifact=ROOT / 'ai/runs/multimap-reference-preflight-v1/artifact',
                    reference_python=ROOT / 'ai/.venv-reference/bin/python')
                require(rows == [] and len(outcomes) == len(tasks), 'Evaluation replay must return no training/label rows')
                audit.verify_outcomes(outcomes, tasks)
                for r in outcomes:
                    left = {k: v for k, v in r.items() if k not in TIMINGS}
                    right = {k: v for k, v in stored[canonical(r['spec'])].items() if k not in TIMINGS}
                    exact(left, right, 'Exact replay terminal/controller/public/request counters')
                    require(r['expertRequests'] == 0, 'No replay expert labels')
                    checks.append(dict(stage=label, spec=r['spec'], terminalAndCountersSha256=sha(canonical(left).encode())))
                    counts.update({k: sum(v.values()) for k, v in r['counts'].items()})
    finally:
        torch.use_deterministic_algorithms(prior_deterministic)
    require(len(checks) == 16, 'Exact replay coverage')
    report = dict(replica=replica, manifestSha256=receipt['manifestSha256'], evidenceSha256=receipt['evidenceSha256'],
        games=16, exactMatches=16, newIndependentObservations=0, expertLabels=0, checks=checks,
        controllerCounts=dict(counts), excludedTimingFields=sorted(TIMINGS), seconds=time.monotonic() - began,
        note='Scope-selected deterministic evaluation only; no training/gradient replay or new strength observations.')
    write_new(output / 'replay-verification.json', report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('fetch', 'audit', 'replay'))
    parser.add_argument('--replica', type=int, choices=(1, 2), required=True)
    parser.add_argument('--revision')
    parser.add_argument('--root', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--audit-git-receipt-commit')
    parser.add_argument('--allow-games', action='store_true')
    args = parser.parse_args()
    if args.action == 'fetch':
        require(args.revision is not None, '--revision required')
        result = fetch(args.replica, args.revision, args.output)
    elif args.action == 'audit':
        require(args.revision is not None and args.audit_git_receipt_commit is not None, 'Revision and receipt Git commit required')
        result = audit_integrity(args.replica, args.revision, args.root or args.output / 'restored', args.output,
                                 auditGitReceiptCommit=args.audit_git_receipt_commit)
    else:
        result = replay(args.replica, args.root or args.output / 'restored', args.output, allow_games=args.allow_games)
    print(json.dumps({k: result[k] for k in ('replica', 'manifestSha256') if k in result}, indent=2))


if __name__ == '__main__':
    main()
