"""Two frozen expert replicas, with a durable four-slot (12 job-hour) budget.

New: --group multimap-expert-replicas-YYYYMMDD-v1 [--output ai/runs/GROUP].
Recovery: --continue-launch FIRST/launch.json --run-id GROUP-continuation-r1
          --resume-revision IMMUTABLE_MODEL_COMMIT
Missing peer: --continue-launch FIRST/launch.json --run-id GROUP-r2 --missing-replica 2
A source.json receipt also permits explicit missing-peer recovery after a source
upload and before any job submission. Neither recovery path ever repackages.

Keep the entire ignored ai/runs/GROUP directory, not just a copied receipt.
Exclusive, fsynced slot intents are NEVER removed or retried, including when the
API times out. Uncertain uploads/submissions require inspection, not an override.
The remote group inventory is bounded and fail-closed. This is a single durable
coordinator, not a distributed lock: do not copy its ledger to another machine
and submit concurrently. No counter supplied by a caller authorizes a segment.
"""
import argparse
import ast
from contextlib import contextmanager
import copy
import fcntl
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import random
import re
import shlex
import shutil
import subprocess
import tarfile
import tempfile

from huggingface_hub import HfApi, get_token, hf_hub_download
from huggingface_hub.errors import EntryNotFoundError
from data import ROOT, atomic_json, digest
from launch import package, check_local_storage as inherited_storage_check, tree_bytes, DATASET, MODEL, IMAGE
from job_neural import safe_run, immutable_revision, remote_size
from expert_replicas_v1 import Replica, STUDY, PROTOCOL_PATH
from expert_ppo import DEFAULT_ARTIFACT, DEFAULT_REFERENCE_PYTHON
from gap_study import THREAD_ENV

PREFLIGHT_NAME = 'ai/multimap/expert-replicas-preflight-v1.json'
LAUNCHER_NAME = 'ai/multimap/launch_expert_replicas_v1.py'
LIMIT = 128 * 1024**2
NAMESPACE = MODEL.split('/')[0]
STAGE = 'expert-replicas-v1'
SCHEMA = 'multimap-expert-replicas-launch-v1'

# Strict stress bootstrap, with additional member-type/path/commit guards.
BOOTSTRAP = r'''
import os,subprocess,tarfile,hashlib,json,re
from pathlib import Path,PurePosixPath
from huggingface_hub import hf_hub_download,get_hf_file_metadata,hf_hub_url,get_token
rev=os.environ['SOURCE_REVISION'];name=os.environ['SOURCE_PATH'];repo=os.environ['DATASET_REPO']
assert re.fullmatch('[0-9a-f]{40}',rev),'Immutable source revision required'
meta=get_hf_file_metadata(hf_hub_url(repo,name,repo_type='dataset',revision=rev),token=get_token())
assert meta.commit_hash==rev and type(meta.size) is int and 0<meta.size<128*1024**2,'Source metadata rejected'
p=hf_hub_download(repo,name,repo_type='dataset',revision=rev)
assert Path(p).stat().st_size==meta.size and hashlib.sha256(Path(p).read_bytes()).hexdigest()==os.environ['SOURCE_SHA256'],'Source hash mismatch'
root=Path('/tmp/multimap-source');root.mkdir(exist_ok=False)
with tarfile.open(p) as t:
    members=t.getmembers()
    assert sum(m.size for m in members)<256*1024**2 and len(members)<20000,'Expanded source budget'
    assert len({m.name for m in members})==len(members),'Duplicate source members'
    for m in members:
        n=PurePosixPath(m.name)
        assert (m.isfile() or m.isdir()) and not n.is_absolute() and '..' not in n.parts and n.as_posix()==m.name,'Unsafe source member'
    t.extractall(root,filter='data')
manifest=json.loads((root/'source-manifest.json').read_text())
assert manifest['gitCommit']==os.environ['SOURCE_COMMIT'],'Source commit mismatch'
assert {p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file()}==set(manifest['files'])|{'source-manifest.json'},'Source member coverage'
for name,sha in manifest['files'].items():
    file=root/name
    assert not file.is_symlink() and file.is_relative_to(root) and hashlib.sha256(file.read_bytes()).hexdigest()==sha,'Source member hash'
os.chdir(root);os.environ['PATH']=str(root/'runtime')+':'+os.environ['PATH'];os.environ['PYTHONPATH']=str(root/'ai/multimap')
subprocess.run(['python','-m','pip','install','--no-cache-dir','--disable-pip-version-check','--extra-index-url','https://download.pytorch.org/whl/cpu','-r','ai/multimap/requirements-cpu.txt'],check=True)
os.execvp('python',['python','-u','-B','ai/multimap/job_expert_replicas_v1.py'])
'''


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read(path):
    path = Path(path)
    require(not path.is_symlink() and path.stat().st_size <= 4 * 1024**2, 'Unsafe/oversize receipt')
    return json.loads(path.read_text())


def downloaded_file(path, cache, size):
    """Allow HF snapshot-to-blob links only within this dedicated audit cache."""
    cache = Path(cache).resolve(strict=True)
    path = Path(path).resolve(strict=True)
    require(path.is_relative_to(cache) and path.is_file(),
            'Downloaded file escapes cache or is not a regular file')
    require(type(size) is int and size > 0 and path.stat().st_size == size,
            'Downloaded file metadata size mismatch')
    return path


def sha_bytes(value):
    return hashlib.sha256(value).hexdigest()


def command_for(bootstrap):
    return ['bash', '-lc', 'python -m pip install --no-cache-dir --disable-pip-version-check '
            'huggingface_hub==1.29.0 && python -c ' + shlex.quote(bootstrap)]


def original_command(commit):
    immutable_revision(commit)
    text = subprocess.check_output(['git', 'show', commit + ':' + LAUNCHER_NAME], cwd=ROOT, text=True)
    nodes = [n.value for n in ast.parse(text).body if isinstance(n, ast.Assign) and
             any(isinstance(t, ast.Name) and t.id == 'BOOTSTRAP' for t in n.targets)]
    require(len(nodes) == 1, 'Original bootstrap constant missing')
    bootstrap = ast.literal_eval(nodes[0])
    require(isinstance(bootstrap, str), 'Original bootstrap must be literal text')
    return command_for(bootstrap), text.encode()


def group_directory(group):
    safe_run(group)
    require(re.fullmatch(r'multimap-expert-replicas-\d{8}-v1', group), 'Use multimap-expert-replicas-YYYYMMDD-v1')
    runs = ROOT / 'ai/runs'
    require(not runs.is_symlink(), 'Run root symlink forbidden')
    directory = runs / group
    require(not directory.is_symlink(), 'Group symlink forbidden')
    return directory


def output_directory(run):
    safe_run(run)
    out = ROOT / 'ai/runs' / run
    require(not out.exists() and not out.is_symlink(), 'Existing intent/output; inspect uncertain submission')
    return out


@contextmanager
def locked(directory):
    path = directory / '.launch-lock'
    require(not path.is_symlink(), 'Ledger lock symlink forbidden')
    with path.open('a') as handle:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def exclusive_json(path, value):
    """A torn file is deliberately a blocker too; never overwrite a slot intent."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    require(not path.parent.is_symlink(), 'Ledger directory symlink forbidden')
    with path.open('x') as handle:
        json.dump(value, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write('\n')
        handle.flush()
        os.fsync(handle.fileno())
    descriptor = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def slot(directory, replica, segment, kind='intents'):
    require(type(replica) is int and replica in (1, 2) and type(segment) is int and segment in (1, 2),
            'Only two replicas with two segments each are authorized')
    require(kind in ('intents', 'receipts') and not (directory / kind).is_symlink(), 'Unsafe ledger directory')
    return directory / kind / f'r{replica}-s{segment}.json'


def labels_for(group, replica, segment):
    return dict(project='powergrid-multimap', stage=STAGE, group=group,
                replica=str(replica), segment=str(segment))


def env_for(source, replica, segment, run, revision=None):
    env = dict(RUN_ID=run, MODEL_REPO=MODEL, DATASET_REPO=DATASET,
               SOURCE_PATH=source['sourcePath'], SOURCE_REVISION=source['sourceRevision'],
               SOURCE_SHA256=source['sourceSha256'], SOURCE_COMMIT=source['sourceCommit'],
               EXPERT_REPLICA=str(replica), EXPERT_WORKERS='6', EXPERT_SMOKE='0',
               REPLICA_SEGMENT=str(segment), PYTHONUNBUFFERED='1', PYTHONDONTWRITEBYTECODE='1',
               HF_HUB_DISABLE_PROGRESS_BARS='1', HF_HUB_DISABLE_XET='1')
    env.update({name: '1' for name in THREAD_ENV})
    if revision:
        env.update(RESUME_RUN=source['group'] + '-r' + str(replica), RESUME_REVISION=revision)
    return env


def check_local_storage(directory):
    # Retain the old stricter decimal 8 GB ceiling, with an additional 1 GiB
    # reservation for bounded source staging, four snapshots and recovery copies.
    # Reusable reference/environment bytes are not repeatedly downloaded here.
    inherited_storage_check(directory)
    reserved = 8 * LIMIT
    used = sum(tree_bytes(p) for p in (ROOT / 'ai/runs').glob('multimap-*'))
    require(used + reserved <= 8_000_000_000 and
            shutil.disk_usage(ROOT).free >= STUDY['budget']['minimumFreeBytes'] + reserved,
            'Insufficient bounded staging/recovery headroom')


def preflight_gate():
    require(not subprocess.check_output(['git', 'status', '--porcelain', '--untracked-files=normal'],
                                       cwd=ROOT, text=True).strip(), 'Commit all source/preflight before launch')
    preflight = read(ROOT / PREFLIGHT_NAME)
    require(preflight.get('schema') == 'multimap-expert-replicas-preflight-v1' and
            preflight.get('allChecksPassed') is True and
            preflight.get('protocolSha256') == digest(PROTOCOL_PATH), 'Pinned real-service preflight required')
    expected_checks = dict(totalTerminalGames=264, exactTerminalAndCounterReplayMatches=132,
        failures=0, interruptedAfterUpdate=1, completedCommittedWorkPreserved=True,
        deliberatelyCorruptedBestRepaired=True, completedResumePerformsNoCollection=True,
        onlySmokeRoots=True, reusedReferenceArtifact=True, productionGamesExecuted=0,
        qualified=False, qualificationEligible=False, reservedFinalSeedsUsed=False)
    require(json.dumps({k: preflight.get(k) for k in expected_checks}, sort_keys=True) ==
            json.dumps(expected_checks, sort_keys=True), 'Incomplete real-service preflight evidence')
    results = preflight.get('results')
    require(isinstance(results, dict), 'Both replica replays required')
    for number in (1, 2):
        checked = results.get(str(number))
        require(isinstance(checked, dict) and
                type(checked.get('exactTerminalAndCounterReplayMatches')) is int and
                checked['exactTerminalAndCounterReplayMatches'] == 66 and
                checked.get('exactModelOptimizerRngAndHistory') is True, 'Both replica replays required')
        replica = Replica(number)
        current = replica.config(True, replica.protocol, artifact=DEFAULT_ARTIFACT,
                                 reference_python=DEFAULT_REFERENCE_PYTHON, workers=6)
        require(current == preflight['smokeIdentities'][str(number)], 'Preflight source/runtime identity changed')
    require(STUDY['budget'] == dict(replicas=2, workers=6, flavor='cpu-upgrade', timeout='3h',
            maxSegmentsPerReplica=2, maxTotalJobHours=12, studyArtifactMaxBytes=LIMIT,
            localStorageMaxBytes=8 * 1024**3, minimumFreeBytes=2 * 1024**3), 'Budget protocol changed')
    return preflight


def private_api():
    token = get_token()
    require(bool(token), 'Existing credentials required')
    api = HfApi()
    require(api.model_info(MODEL).private is True and api.dataset_info(DATASET).private is True,
            'Existing private repositories required')
    return api, token


def remote_path_absent(api, run):
    try:
        entries = iter(api.list_repo_tree(MODEL, path_in_repo='runs/' + run, recursive=False))
        # Even an empty remote directory is not ours to overwrite.
        next(entries, None)
    except EntryNotFoundError:
        return
    raise ValueError('Remote run path already exists')


def inventory(api, group):
    """All states, not just running: completed/uncertain slots also consume budget."""
    jobs = []
    for summary in api.list_jobs(namespace=NAMESPACE, labels={'group': group}, timeout=30):
        require(len(jobs) < 4, 'Remote group exceeds four-job budget')
        job = api.inspect_job(job_id=summary.id, namespace=NAMESPACE)
        labels = job.labels or {}
        require(labels.get('group') == group and labels.get('project') == 'powergrid-multimap' and
                labels.get('stage') == STAGE and labels.get('replica') in ('1', '2') and
                labels.get('segment') in ('1', '2'), 'Remote group identity/labels invalid')
        key = labels['replica'], labels['segment']
        require(all((j.labels['replica'], j.labels['segment']) != key for j in jobs), 'Duplicate remote budget slot')
        jobs.append(job)
    return jobs


def validate_job(job, receipt, command):
    require(job.id == receipt['jobId'] and job.environment == receipt['env'] and
            job.docker_image == IMAGE == receipt['image'] and
            job.flavor == 'cpu-upgrade' == receipt['flavor'] and receipt['timeout'] == '3h' and
            job.command == command and not job.arguments and not getattr(job, 'volumes', None) and
            not getattr(job, 'space_id', None), 'Original HF job execution differs from pinned receipt')
    expected = labels_for(receipt['group'], receipt['replica'], receipt['segment'])
    require(all((job.labels or {}).get(k) == v for k, v in expected.items()), 'Original HF labels differ')


def validate_inventory(jobs, directory, source, command):
    for job in jobs:
        replica, segment = int(job.labels['replica']), int(job.labels['segment'])
        receipt_path = slot(directory, replica, segment, 'receipts')
        require(receipt_path.is_file(), 'Remote submission without durable receipt; inspect, never retry')
        receipt = read(receipt_path)
        require(receipt['source'] == source and receipt['replica'] == replica and receipt['segment'] == segment,
                'Remote receipt/source/slot mismatch')
        require(receipt['env'] == env_for(source, replica, segment, receipt['run'], receipt.get('resumeRevision')),
                'Remote receipt environment mismatch')
        require(read(slot(directory, replica, segment)) == {k: v for k, v in receipt.items() if k not in ('jobId', 'url')},
                'Durable intent/receipt mismatch')
        validate_job(job, receipt, command)


def verify_archive(archive, source, preflight, launcher_bytes):
    require(0 < Path(archive).stat().st_size < LIMIT and Path(archive).stat().st_size == source['sourceBytes'] and
            digest(archive) == source['sourceSha256'], 'Original source archive hash/size mismatch')
    with tarfile.open(archive) as tar:
        members = tar.getmembers()
        require(len(members) < 20000 and sum(m.size for m in members) < 2 * LIMIT, 'Expanded source budget')
        require(len({m.name for m in members}) == len(members), 'Duplicate archive member')
        for member in members:
            path = PurePosixPath(member.name)
            require((member.isfile() or member.isdir()) and not path.is_absolute() and
                    '..' not in path.parts and path.as_posix() == member.name, 'Unsafe archive member')
        manifest_member = tar.getmember('source-manifest.json')
        require(manifest_member.size <= 4 * 1024**2, 'Oversize source manifest')
        manifest = json.load(tar.extractfile(manifest_member))
        require(manifest['gitCommit'] == source['sourceCommit'], 'Original source Git commit mismatch')
        files = {m.name for m in members if m.isfile()}
        require(files == set(manifest['files']) | {'source-manifest.json'}, 'Source manifest coverage mismatch')
        for name, expected in manifest['files'].items():
            with tar.extractfile(name) as handle:
                actual = hashlib.file_digest(handle, 'sha256').hexdigest()
            require(actual == expected, 'Source member hash mismatch')
        require(manifest['files'][LAUNCHER_NAME] == sha_bytes(launcher_bytes), 'Archive/committed launcher drift')
        require(manifest['files'][PREFLIGHT_NAME] == source['preflightSha256'] and
                json.load(tar.extractfile(PREFLIGHT_NAME)) == preflight, 'Archived preflight differs')
        for identity in preflight['smokeIdentities'].values():
            require(all(manifest['files'].get(n) == h for n, h in identity['sourceFiles'].items()),
                    'Preflight source files differ from packaged source')
    return manifest


def intent_for(source, replica, segment, run, **extra):
    return dict(schema=SCHEMA, group=source['group'], run=run, replica=replica, segment=segment,
                source=source, sourceCommit=source['sourceCommit'],
                env=env_for(source, replica, segment, run, extra.get('resumeRevision')),
                image=IMAGE, flavor='cpu-upgrade', timeout='3h',
                preflightSha256=source['preflightSha256'], plannedGames=6240,
                plannedTrainingGames=2720, plannedSelectionGames=2240,
                plannedConfirmationGames=1280, plannedConfirmationDealRoots=160,
                groupPlannedGames=12480, maxSegmentsPerReplica=2, maxTotalJobHours=12,
                historicalCandidateDeployed=False, qualified=False,
                qualificationEligible=False, reservedFinalSeedsUsed=False, **extra)


def submit(api, token, directory, intent, command):
    """Do not add retry here. A failed request permanently consumes its slot."""
    replica, segment, run = intent['replica'], intent['segment'], intent['run']
    path = slot(directory, replica, segment)
    require(not path.exists() and not path.is_symlink(), 'Budget slot already attempted; uncertain submissions count')
    out = output_directory(run)
    remote_path_absent(api, run)
    # Reserve fixed group slot BEFORE per-run output or any paid API call.
    exclusive_json(path, intent)
    out.mkdir(exist_ok=False)
    exclusive_json(out / 'intent.json', intent)
    job = api.run_job(image=IMAGE, command=command, env=intent['env'], secrets={'HF_TOKEN': token},
                      flavor='cpu-upgrade', timeout='3h', name=run, namespace=NAMESPACE,
                      labels=labels_for(intent['group'], replica, segment))
    record = dict(intent, jobId=job.id, url=f'https://huggingface.co/jobs/{NAMESPACE}/{job.id}')
    exclusive_json(slot(directory, replica, segment, 'receipts'), record)
    exclusive_json(out / 'launch.json', record)
    records = [read(p) for p in sorted((directory / 'receipts').glob('r*-s*.json'))]
    atomic_json(directory / 'launches.json', records)
    print(json.dumps(record, indent=2), flush=True)
    return record


def launch(group, directory):
    expected = group_directory(group)
    require(Path(directory).absolute() == expected.absolute(), 'Use the dedicated ai/runs/GROUP directory')
    require(not expected.exists(), 'Existing group/intent: explicit recovery only')
    preflight = preflight_gate()
    check_local_storage(expected)
    api, token = private_api()
    require(not inventory(api, group), 'Remote group already has jobs')
    source_path = f'multimap/{group}/source.tgz'
    require(not api.file_exists(DATASET, source_path, repo_type='dataset'), 'Group source already published')
    for number in (1, 2):
        output_directory(group + '-r' + str(number))
        remote_path_absent(api, group + '-r' + str(number))
    expected.mkdir(parents=True, exist_ok=False)
    with locked(expected):
        exclusive_json(expected / 'intent.json', dict(schema=SCHEMA, group=group, sourcePath=source_path,
                       preflightSha256=digest(ROOT / PREFLIGHT_NAME), maxSegmentsPerReplica=2, maxTotalJobHours=12))
        archive, commit = package(expected)
        immutable_revision(commit)
        require(commit == subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                'Source HEAD changed while packaging')
        command, original = original_command(commit)
        require(command == command_for(BOOTSTRAP), 'Committed bootstrap differs from running launcher')
        source = dict(schema=SCHEMA, group=group, sourceCommit=commit, sourcePath=source_path,
                      sourceSha256=digest(archive), sourceBytes=Path(archive).stat().st_size,
                      protocolSha256=digest(PROTOCOL_PATH), preflightSha256=digest(ROOT / PREFLIGHT_NAME))
        verify_archive(archive, source, preflight, original)
        # Recheck the clean gate after package: no concurrent source/preflight edits.
        require(preflight_gate() == preflight, 'Preflight changed while packaging')
        upload = api.upload_file(repo_id=DATASET, repo_type='dataset', path_or_fileobj=archive,
                                 path_in_repo=source_path, commit_message=f'{group}: frozen expert replica source {commit}')
        source['sourceRevision'] = immutable_revision(upload.oid)
        exclusive_json(expected / 'source.json', source)
        records = []
        for number in (1, 2):
            jobs = inventory(api, group)
            validate_inventory(jobs, expected, source, command)
            require(not any(j.labels['replica'] == str(number) for j in jobs), 'Replica already remotely submitted')
            records.append(submit(api, token, expected, intent_for(source, number, 1, group + '-r' + str(number)), command))
        return records


def validate_transaction(base, identity):
    """Audit the actual immutable commit without collecting/fitting or changing RNG."""
    import torch
    with torch.random.fork_rng(devices=[]):
        return _validate_transaction(base, identity)


def _validate_transaction(base, identity):
    import math
    import torch
    from expert_policy import load
    base = Path(base)
    require(read(base / 'expert/config.json') == identity, 'Resume replica/config/source/workers mismatch')
    model, saved = load(base / 'expert/last.pt')
    _, initial = load(base / 'expert/initial.pt')
    require(saved['config'] == identity == initial['config'] and initial['stage'] == 'initial' and
            initial['update'] == 0 and saved['width'] == initial['width'] == identity['protocol']['width'],
            'Checkpoint replica/config/source identity mismatch')
    stage, update = saved['stage'], saved['update']
    require(stage in ('initial', 'warmup', 'train') and type(update) is int and
            0 <= update <= identity['protocol']['updates'] and (stage == 'train' or update == 0),
            'Invalid committed training stage')
    require(saved.get('result') is None, 'Already complete transaction cannot consume a continuation')
    require(isinstance(saved['bestArtifact'], bytes) and sha_bytes(saved['bestArtifact']) == saved['bestSha256'],
            'Committed best checkpoint hash mismatch')
    _, best = load(io.BytesIO(saved['bestArtifact']))
    require(best['config'] == identity and best['stage'] == saved['bestStage'] and
            best['update'] == saved['bestUpdate'] and type(saved['bestUpdate']) is int and
            0 <= saved['bestUpdate'] <= update and math.isfinite(saved['bestScore']) and
            best['width'] == identity['protocol']['width'] and saved['bestStage'] in ('initial', 'warmup', 'train') and
            (saved['bestStage'] == 'train' or saved['bestUpdate'] == 0), 'Committed selection identity mismatch')
    protocol = identity['protocol']
    optimizer = torch.optim.AdamW(model.parameters(), lr=protocol['warmupLearningRate' if stage != 'train' else 'learningRate'],
                                  weight_decay=protocol['weightDecay'])
    require(saved['optimizer']['param_groups'] == optimizer.state_dict()['param_groups'],
            'Committed optimizer recipe/parameter groups mismatch')
    optimizer.load_state_dict(saved['optimizer'])
    for parameter, state in optimizer.state.items():
        require(set(state) == {'step', 'exp_avg', 'exp_avg_sq'}, 'Invalid optimizer state fields')
        require(state['exp_avg'].shape == parameter.shape and state['exp_avg_sq'].shape == parameter.shape and
                state['step'].numel() == 1 and all(torch.isfinite(v).all() for v in state.values()),
                'Invalid/nonfinite optimizer transaction')
    # Uploaded best/history can be ahead of last.pt following a crash. Check
    # checkpoint identities/finite tensors, NEVER compare them to committed
    # selection or overwrite the downloaded evidence. Embedded best is authority.
    for name in ('best.pt', 'warmup.pt'):
        path = base / 'expert' / name
        if path.exists():
            _, candidate = load(path)
            require(candidate['config'] == identity and candidate['width'] == identity['protocol']['width'],
                    'Uploaded checkpoint config mismatch')
    torch.Generator().set_state(saved['torchRng'])
    random.Random().setstate(saved['pythonRng'])
    require(isinstance(saved['history'], list) and isinstance(saved['baseline'], dict), 'Invalid transaction history/baseline')
    expected_history = [] if stage == 'initial' else [('warmup', 0)] + [('train', i) for i in range(1, update + 1)]
    require([(row['stage'], row['update']) for row in saved['history']] == expected_history,
            'Invalid committed transaction history')
    for label, record in saved.get('confirmations', {}).items():
        require(label in ('selected', 'teacher') and
                digest(base / f'expert/confirmation-{label}.json') == record['sha256'], 'Committed confirmation mismatch')
    return dict(stage=stage, update=update, configSha256=digest(base / 'expert/config.json'),
                lastSha256=digest(base / 'expert/last.pt'), bestSha256=saved['bestSha256'])


def verify_resume(source, receipt, revision, directory, preflight):
    """Check ALL manifest metadata before downloading any payload, then all hashes."""
    from job_expert import validate_manifest
    from job_expert_replicas_v1 import _compact_training_json
    immutable_revision(revision)
    prefix = 'runs/' + receipt['run'] + '/'
    with tempfile.TemporaryDirectory(prefix='.resume-audit-', dir=directory) as temp:
        temp = Path(temp)
        cache, base = temp / 'download', temp / 'verified'
        size = remote_size(MODEL, prefix + 'artifacts.json', revision, maximum=64 * 1024)
        manifest_path = downloaded_file(
            hf_hub_download(MODEL, prefix + 'artifacts.json', revision=revision, cache_dir=cache), cache, size)
        manifest = read(manifest_path)
        inherited = validate_manifest(manifest)
        require({'status.json', 'protocol.json', 'environment.json', 'recovery.json'} <= set(manifest),
                'Resume missing source/runtime metadata')
        sizes = {name: remote_size(MODEL, prefix + name, revision, maximum=LIMIT) for name in manifest}
        require(size + sum(sizes.values()) <= LIMIT, 'Aggregate resume metadata/artifact budget exceeded')
        for name, sha in manifest.items():
            path = downloaded_file(
                hf_hub_download(MODEL, prefix + name, revision=revision, cache_dir=cache), cache, sizes[name])
            require(digest(path) == sha, 'Resume artifact hash/size mismatch')
            destination = base / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(path.read_bytes())
            if name.endswith('.json'):
                _compact_training_json(json.loads(destination.read_text()))
        status = read(base / 'status.json')
        identity = copy.deepcopy(preflight['smokeIdentities'][str(receipt['replica'])])
        identity['smoke'] = False
        require(status['run'] == receipt['run'] and status['protocol'] == identity['protocol'] and
                status['workers'] == 6 and status['smoke'] is False and
                status['sourceRepo'] == DATASET and status['sourcePath'] == source['sourcePath'] and
                status['sourceRevision'] == source['sourceRevision'] and status['sourceSha256'] == source['sourceSha256'],
                'Resume snapshot source/replica/workers identity mismatch')
        require(read(base / 'protocol.json') == identity['protocol'], 'Resume protocol mismatch')
        environment = read(base / 'environment.json')
        # Version structure is validated by full config; these files must also be
        # present, hash-checked and bound to the retained exact reference.
        require(environment['requirementsSha256'] == identity['protocol']['referenceRequirementsSha256'] and
                environment['versions'] == identity['runtimeVersions'], 'Resume reference requirements/runtime mismatch')
        recovery = read(base / 'recovery.json')
        reference = identity['protocol']['reference']
        require(recovery.get('exactServiceReady') is True and
                recovery.get('runtimeManifestSha256') == identity['referenceManifestSha256'] and
                recovery.get('policySha256') == reference['policySha256'] and
                recovery.get('pins') == dict(source=reference['sourcePin'], model=reference['modelPin']) and
                recovery.get('omitted') == [], 'Resume reference recovery mismatch')
        transaction = validate_transaction(base, identity)
        return dict(revision=revision, manifestSha256=digest(manifest_path), files=inherited,
                    allFileHashes=manifest, totalBytes=size + sum(sizes.values()), transaction=transaction)


def continue_replica(receipt_path, new_run, *, revision=None, missing_replica=None):
    """One immutable continuation OR explicit unsubmitted peer using original source."""
    require((revision is not None) != (missing_replica is not None), 'Choose immutable resume OR missing replica')
    anchor = read(receipt_path)
    group = anchor['group']
    directory = group_directory(group)
    require(directory.is_dir(), 'Original durable group ledger required')
    source = read(directory / 'source.json')
    require(source['schema'] == SCHEMA and source['group'] == group and
            source['sourcePath'] == f'multimap/{group}/source.tgz', 'Invalid original source receipt')
    immutable_revision(source['sourceCommit']); immutable_revision(source['sourceRevision'])
    require(re.fullmatch('[0-9a-f]{64}', source['sourceSha256']), 'Invalid source hash')
    with locked(directory):
        preflight = preflight_gate()
        require(source['preflightSha256'] == digest(ROOT / PREFLIGHT_NAME) and
                source['protocolSha256'] == digest(PROTOCOL_PATH), 'Recovery must use original preflight/source identity')
        check_local_storage(directory)
        command, original = original_command(source['sourceCommit'])
        api, token = private_api()
        jobs = inventory(api, group)
        validate_inventory(jobs, directory, source, command)
        first = None
        if 'jobId' in anchor:
            number = anchor['replica']
            canonical_path = slot(directory, number, 1, 'receipts')
            first = read(canonical_path)
            require(anchor == first and first['segment'] == 1 and first['run'] == group + '-r' + str(number) and
                    first['source'] == source and first['env'] == env_for(source, number, 1, first['run']),
                    'Only the pinned first launch receipt can authorize recovery')
            require(read(slot(directory, number, 1)) == {k: v for k, v in first.items() if k not in ('jobId', 'url')},
                    'Pinned first receipt differs from durable intent')
            old = api.inspect_job(job_id=first['jobId'], namespace=NAMESPACE)
            validate_job(old, first, command)
            require(any(j.id == old.id for j in jobs), 'Original job missing from authoritative group inventory')
        else:
            require(anchor == source and revision is None, 'Resume requires the pinned first job receipt')
        if revision is not None:
            immutable_revision(revision)
            replica, segment = first['replica'], 2
            require(old.status.stage in ('ERROR', 'CANCELED'), 'Only ERROR/CANCELED original jobs may continue')
            require(new_run == group + '-continuation-r' + str(replica), 'Use the fixed GROUP-continuation-rN run ID')
            require(not any(j.labels['replica'] == str(replica) and j.id != first['jobId'] for j in jobs),
                    'Replica already consumed its continuation')
        else:
            require(type(missing_replica) is int and missing_replica in (1, 2), 'Missing replica must be integer 1 or 2')
            replica, segment = missing_replica, 1
            require(first is None or replica != first['replica'], 'Missing replica must be the other peer')
            require(new_run == group + '-r' + str(replica), 'Missing peer must retain original GROUP-rN ID')
            require(not any(j.labels['replica'] == str(replica) for j in jobs), 'Missing peer already exists remotely')
        require(not slot(directory, replica, segment).exists(), 'Budget slot already attempted; uncertain submissions count')
        output_directory(new_run)
        remote_path_absent(api, new_run)
        with tempfile.TemporaryDirectory(prefix='.source-audit-', dir=directory) as cache:
            advertised = remote_size(DATASET, source['sourcePath'], source['sourceRevision'], repo_type='dataset', maximum=LIMIT - 1)
            require(advertised == source['sourceBytes'], 'Original source metadata differs')
            archive = downloaded_file(
                hf_hub_download(DATASET, source['sourcePath'], revision=source['sourceRevision'],
                                repo_type='dataset', cache_dir=cache), cache, advertised)
            verify_archive(archive, source, preflight, original)
        extra = dict(sourceArchiveReusedExactly=True)
        if revision is not None:
            extra.update(firstReceiptSha256=digest(canonical_path), recoveryFromJob=first['jobId'],
                         resumeRevision=revision, resumeAudit=verify_resume(source, first, revision, directory, preflight))
        elif first:
            extra.update(firstReceiptSha256=digest(canonical_path), recoveryFromJob=first['jobId'])
        # Recheck immediately before reserving the one-shot slot.
        jobs = inventory(api, group)
        validate_inventory(jobs, directory, source, command)
        require(not any(j.labels['replica'] == str(replica) and j.labels['segment'] == str(segment) for j in jobs),
                'Remote budget slot already exists')
        if revision is not None:
            require(api.inspect_job(job_id=first['jobId'], namespace=NAMESPACE).status.stage in ('ERROR', 'CANCELED'),
                    'Original job no longer stopped')
        return submit(api, token, directory, intent_for(source, replica, segment, new_run, **extra), command)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--group')
    parser.add_argument('--output')
    parser.add_argument('--continue-launch')
    parser.add_argument('--run-id')
    parser.add_argument('--resume-revision')
    parser.add_argument('--missing-replica', type=int, choices=(1, 2))
    args = parser.parse_args()
    if args.continue_launch:
        if args.group or args.output or not args.run_id:
            parser.error('Recovery requires --run-id, not --group/--output')
        continue_replica(args.continue_launch, args.run_id, revision=args.resume_revision, missing_replica=args.missing_replica)
    else:
        if not args.group or args.run_id or args.resume_revision or args.missing_replica:
            parser.error('New launch requires --group [--output] only')
        launch(args.group, args.output or group_directory(args.group))
