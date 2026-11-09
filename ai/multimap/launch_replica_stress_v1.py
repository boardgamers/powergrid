"""Single durable coordinator: 6h strong + 3h mixed + ONE shared 3h recovery.

No caller counter can grant more jobs. Every submitted or uncertain API attempt
consumes an exclusive fsynced slot BEFORE the paid request. Recovery requires
both initial jobs terminal, actual ERROR / "Job timeout", an incomplete valid
immutable original snapshot, and fixed strong-first priority. Retain the entire
original ai/runs/GROUP directory; copied ledgers and blind retries are rejected.
A conditional dataset commit atomically reserves remote source+owner against an
observed immutable parent, preventing independent hosts from launching twice.
Recovery audits current original-run manifests at MODEL HEAD after both initials
terminate, and rechecks that authority immediately before reserving a paid slot.

Private preflight evidence follows the existing privateEvidence contract:
repo/revision/prefix/files(SHA256 map)/bytes. Every file is remotely size/hash
verified, archived report/identities and both exact smoke replays are checked.
JobInfo drops timeoutSeconds in hub 1.29.0: inspect_actual reads that field from
the authenticated raw response, but never returns/serializes its secrets.
"""
import argparse
import ast
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shlex
import shutil
import subprocess
import tarfile
import tempfile
import threading
import uuid
from types import SimpleNamespace

from huggingface_hub import HfApi, CommitOperationAdd, get_token, hf_hub_download
from huggingface_hub.errors import EntryNotFoundError
from huggingface_hub.utils import get_session, hf_raise_for_status
from data import ROOT, atomic_json, digest
from launch import package, check_local_storage as inherited_storage_check, tree_bytes, DATASET, MODEL, IMAGE
from job_neural import safe_run, immutable_revision, remote_size
from replica_stress_study_v1 import PROTOCOL, identity, plan, ARTIFACT, REFERENCE_PYTHON, batches, verify_batch, analyze
from gap_study import THREAD_ENV
from job_replica_stress_v1 import (canonical, read, no_links, downloaded_file, fetch_snapshot,
                                   validate_snapshot, validate_manifest, production_identity)

PREFLIGHT_NAME = 'ai/multimap/replica-stress-preflight-v1.json'
LAUNCHER_NAME = 'ai/multimap/launch_replica_stress_v1.py'
PROTOCOL_PATH = ROOT / 'ai/multimap/replica-stress-protocol-v1.json'
SOURCE_NAMES = ('replica-stress-protocol-v1.json', 'replica_stress_game_v1.cjs',
                'replica_stress_rollout_v1.py', 'replica_stress_study_v1.py', 'job_replica_stress_v1.py',
                'launch_replica_stress_v1.py', 'preflight_replica_stress_v1.py', 'test_replica_stress_v1.cjs',
                'test_replica_stress_rollout_v1.py', 'test_replica_stress_study_v1.py',
                'test_job_replica_stress_v1.py', 'test_launch_replica_stress_v1.py', 'test_preflight_replica_stress_v1.py')
LIMIT = 128 * 1024**2
NAMESPACE = MODEL.split('/')[0]  # HF account namespace, not the frozen seed namespace.
SEED_NAMESPACE = 'pg-multimap-replica-stress-20261109-v1'
GROUP = 'multimap-replica-stress-20261109-v1'
STAGE = 'replica-stress-v1'
SCHEMA = 'multimap-replica-stress-launch-v1'
PANELS = ('strong', 'mixed')
HOURS = {'strong': 6, 'mixed': 3, 'recovery': 3}
BUDGET = dict(initialHours={'strong': 6, 'mixed': 3}, recoveryHours=3,
              maxRecoveryJobs=1, maxJobs=3, maxTotalJobHours=12)
_HELD_LOCKS = set()

BOOTSTRAP = r'''
import os,subprocess,tarfile,hashlib,json,re
from pathlib import Path,PurePosixPath
from huggingface_hub import hf_hub_download,get_hf_file_metadata,hf_hub_url,get_token
rev=os.environ['SOURCE_REVISION'];name=os.environ['SOURCE_PATH'];repo=os.environ['DATASET_REPO']
assert re.fullmatch('[0-9a-f]{40}',os.environ['SOURCE_COMMIT']),'Full source Git commit required'
assert re.fullmatch('[0-9a-f]{64}',os.environ['SOURCE_SHA256']),'Full source hash required'
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
os.execvp('python',['python','-u','-B','ai/multimap/job_replica_stress_v1.py'])
'''


def require(condition, message):
    if not condition:
        raise ValueError(message)


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


def group_directory(group=GROUP):
    require(group == GROUP, 'Only the single authorized replica-stress group is allowed')
    return no_links(ROOT / 'ai/runs' / group)


def output_directory(run):
    safe_run(run)
    require(run in {GROUP + '-' + p for p in PANELS} | {GROUP + '-recovery-' + p for p in PANELS},
            'Only fixed original/recovery run IDs are allowed')
    out = no_links(ROOT / 'ai/runs' / run)
    require(not out.exists(), 'Existing intent/output; inspect uncertain submission')
    return out


def coordinator(directory):
    directory = no_links(directory)
    info = directory.stat()
    return dict(path=str(directory.absolute()), device=info.st_dev, inode=info.st_ino)


@contextmanager
def locked(directory):
    import fcntl
    directory = no_links(directory)
    path = no_links(directory / '.launch-lock')
    descriptor = os.open(path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    key = (str(directory), os.getpid(), threading.get_ident())
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        _HELD_LOCKS.add(key)
        try:
            yield
        finally:
            _HELD_LOCKS.remove(key)
            fcntl.flock(descriptor, fcntl.LOCK_UN)
    finally:
        os.close(descriptor)


def exclusive_json(path, value):
    path = no_links(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, 'w') as handle:
        handle.write(canonical(value) + '\n')
        handle.flush()
        os.fsync(handle.fileno())
    # Also persist a newly-created intents/receipts/output directory entry.
    for directory in (path.parent, path.parent.parent):
        descriptor = os.open(directory, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)


def slot(directory, name, kind='intents'):
    require(name in HOURS and kind in ('intents', 'receipts'), 'Only three authorized budget slots')
    return no_links(Path(directory) / kind / (name + '.json'))


def labels_for(group, panel, segment, name):
    require(group == GROUP and panel in PANELS and type(segment) is int and segment in (1, 2) and
            name == (panel if segment == 1 else 'recovery'), 'Invalid fixed budget labels')
    return dict(project='powergrid-multimap', stage=STAGE, group=group, panel=panel,
                segment=str(segment), slot=name, hours=str(HOURS[name]))


def env_for(source, panel, segment, run, revision=None):
    name = panel if segment == 1 else 'recovery'
    env = dict(RUN_ID=run, MODEL_REPO=MODEL, DATASET_REPO=DATASET,
               SOURCE_PATH=source['sourcePath'], SOURCE_REVISION=source['sourceRevision'],
               SOURCE_SHA256=source['sourceSha256'], SOURCE_COMMIT=source['sourceCommit'],
               REPLICA_STRESS_GROUP=source['group'], REPLICA_STRESS_PANEL=panel,
               REPLICA_STRESS_SEGMENT=str(segment), REPLICA_STRESS_SLOT=name,
               REPLICA_STRESS_WORKERS='6', REPLICA_STRESS_SMOKE='0',
               PYTHONUNBUFFERED='1', PYTHONDONTWRITEBYTECODE='1',
               HF_HUB_DISABLE_PROGRESS_BARS='1', HF_HUB_DISABLE_XET='1')
    env.update({key: '1' for key in THREAD_ENV})
    if revision is not None:
        immutable_revision(revision)
        env.update(RESUME_RUN=source['group'] + '-' + panel, RESUME_REVISION=revision)
    return env


def check_local_storage(directory):
    inherited_storage_check(directory)
    reserved = 1024**3
    used = sum(tree_bytes(path) for path in (ROOT / 'ai/runs').glob('multimap-*'))
    require(used + reserved <= 8_000_000_000 and shutil.disk_usage(ROOT).free >= 2 * 1024**3 + reserved,
            'Insufficient bounded staging/recovery headroom')


def preflight_gate():
    require(not subprocess.check_output(['git', 'status', '--porcelain', '--untracked-files=normal'],
                                       cwd=ROOT, text=True).strip(), 'Commit all source/preflight before launch')
    preflight = read(ROOT / PREFLIGHT_NAME, 4 * 1024**2)
    expected = dict(schema='multimap-replica-stress-real-preflight-v1', allChecksPassed=True,
                    protocolSha256=digest(PROTOCOL_PATH), totalTerminalGames=396,
                    exactTerminalAndCounterReplayMatches=198, failures=0, interruptedAfterBatches=1,
                    completedBatchesPreserved=True, interruptedTemporaryBatchIgnored=True,
                    completedResumePerformsNoCollection=True, bothPanels=True,
                    allThreeFocalArms=True, allSixPinnedModels=True, modelLoads=6,
                    allFourMaps=True, allFivePlayerCounts=True, allFourRules=True,
                    modelTensorAndInferenceFlagsUnchanged=True, metadataBeforeAllTransfers=True,
                    legacyServingGitHashesVerified=True, reusedPythonEnvironments=True, onlySmokeRoots=True,
                    reusedReferenceArtifact=True, productionGamesExecuted=0, fitting=False, selection=False,
                    qualified=False, qualificationEligible=False, reservedFinalSeedsUsed=False)
    require(canonical({k: preflight.get(k) for k in expected}) == canonical(expected),
            'Incomplete real-service preflight evidence')
    require(canonical(PROTOCOL.get('jobBudget')) == canonical(BUDGET) and
            PROTOCOL.get('seedNamespace') == SEED_NAMESPACE and PROTOCOL.get('workers') == 6 and
            PROTOCOL.get('uploadEveryBatches') == 16 and PROTOCOL.get('studyArtifactMaxBytes') == 64 * 1024**2,
            'Frozen budget/protocol changed')
    require(set(preflight.get('smokeIdentities', {})) == set(PANELS), 'Both panel identities required')
    for panel in PANELS:
        current = identity(panel, True, 6, ARTIFACT, REFERENCE_PYTHON)
        require(canonical(current) == canonical(preflight['smokeIdentities'][panel]),
                'Preflight source/runtime identity changed')
        require(len(current['tasks']) == 99 and len(batches(current['tasks'])) == 8,
                'Frozen smoke coverage changed')
    commit = immutable_revision(subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip())
    for name in (PREFLIGHT_NAME, *('ai/multimap/' + n for n in SOURCE_NAMES)):
        committed = subprocess.check_output(['git', 'show', commit + ':' + name], cwd=ROOT)
        require(sha_bytes(committed) == digest(ROOT / name), 'Preflight/source differs from committed Git')
    evidence = preflight.get('privateEvidence', {})
    require(evidence.get('repo') == MODEL and isinstance(evidence.get('files'), dict) and
            evidence.get('prefix') == 'diagnostics/replica-stress-v1-preflight', 'Private archived preflight required')
    immutable_revision(evidence.get('revision'))
    return preflight


def private_api():
    token = get_token()
    require(bool(token), 'Existing credentials required')
    api = HfApi()
    require(api.model_info(MODEL).private is True and api.dataset_info(DATASET).private is True,
            'Existing private repositories required')
    return api, token


def verify_preflight_archive(api, preflight, directory):
    """Actual private remote evidence, not remoteVerified/allChecksPassed booleans."""
    evidence = preflight['privateEvidence']
    require(api.model_info(evidence['repo']).private is True, 'Private preflight archive required')
    immutable_revision(evidence['revision'])
    files = evidence['files']
    smoke_names = {f'{p}-{mode}/{n}' for p in PANELS for mode in ('uninterrupted', 'resumed')
                   for n in ('plan.json', 'summary.json', *(f'batch-{i:03}.json' for i in range(8)))}
    source_names = {'source/' + n for n in SOURCE_NAMES}
    required = {'report.json'} | smoke_names | source_names
    optional = {'python-checks.log', 'node-checks.log', 'engine-checks.log', 'smoke.log'}
    require(required <= set(files) <= required | optional and
            all(isinstance(h, str) and re.fullmatch('[0-9a-f]{64}', h) for h in files.values()),
            'Archived preflight coverage/hash invalid')
    with tempfile.TemporaryDirectory(prefix='.preflight-audit-', dir=directory) as temp:
        cache = Path(temp) / 'download'
        prefix = evidence['prefix'] + '/'
        sizes = {n: remote_size(MODEL, prefix + n, evidence['revision'], maximum=64 * 1024**2) for n in files}
        require(all(type(n) is int and n > 0 for n in sizes.values()) and
                type(evidence.get('bytes')) is int and sum(sizes.values()) == evidence['bytes'] and
                0 < sum(sizes.values()) <= 64 * 1024**2, 'Preflight aggregate metadata budget exceeded')
        paths = {}
        for name, sha in files.items():
            path = downloaded_file(hf_hub_download(MODEL, prefix + name, revision=evidence['revision'], cache_dir=cache),
                                   cache, sizes[name])
            require(digest(path) == sha, 'Archived preflight hash mismatch')
            paths[name] = path
        report = read(paths['report.json'], 4 * 1024**2)
        # The uploaded report precedes its own archive receipt; all report fields
        # must survive exactly in the generated local launch-gating receipt.
        require('privateEvidence' not in report and all(canonical(preflight.get(k)) == canonical(v)
                                                       for k, v in report.items()), 'Archived preflight report differs')
        required_fields = {'schema', 'allChecksPassed', 'smokeIdentities', 'protocolSha256', 'totalTerminalGames',
                           'exactTerminalAndCounterReplayMatches', 'failures', 'interruptedAfterBatches',
                           'completedBatchesPreserved', 'interruptedTemporaryBatchIgnored',
                           'completedResumePerformsNoCollection', 'productionGamesExecuted'}
        require(required_fields <= set(report), 'Incomplete archived real preflight report')
        for name in SOURCE_NAMES:
            require(digest(paths['source/' + name]) == digest(ROOT / 'ai/multimap' / name),
                    'Archived preflight source differs')
        timings = {'featureMs', 'inferenceMs', 'referenceMs', 'seconds'}
        matches = 0
        for panel in PANELS:
            results = []
            current = preflight['smokeIdentities'][panel]
            groups = batches(current['tasks'])
            for mode in ('uninterrupted', 'resumed'):
                prefix = panel + '-' + mode + '/'
                require(canonical(read(paths[prefix + 'plan.json'])) == canonical(current), 'Archived smoke identity differs')
                games = []
                for index, tasks in enumerate(groups):
                    games.extend(verify_batch(read(paths[prefix + f'batch-{index:03}.json']), index, tasks))
                require(len(games) == 99 and canonical(read(paths[prefix + 'summary.json'])) ==
                        canonical(analyze(games, panel, True)), 'Archived smoke summary differs')
                results.append([{k: v for k, v in game.items() if k not in timings} for game in games])
            require(canonical(results[0]) == canonical(results[1]), 'Archived exact replay mismatch')
            matches += len(results[0])
        require(matches == 198, 'Archived replay count changed')
    return dict(revision=evidence['revision'], files=len(files), bytes=evidence['bytes'], exactReplayMatches=matches)


def remote_path_absent(api, run):
    try:
        next(iter(api.list_repo_tree(MODEL, path_in_repo='runs/' + run, recursive=False)), None)
    except EntryNotFoundError:
        return
    raise ValueError('Remote run path already exists')


def inspect_actual(api, job_id):
    """Hub's JobInfo silently discards timeoutSeconds. Read canonical actual metadata.

    Raw response (which can include secrets) never leaves this function and is
    never logged. Missing timeout is an admission failure, not a receipt fallback.
    """
    require(isinstance(job_id, str) and re.fullmatch('[A-Za-z0-9_-]+', job_id), 'Unsafe job ID')
    response = get_session().get(f'{api.endpoint}/api/jobs/{NAMESPACE}/{job_id}',
                                 headers=api._build_hf_headers(), timeout=30)
    hf_raise_for_status(response)
    value = response.json()
    status = value.get('status', {})
    return SimpleNamespace(id=value.get('id'), environment=value.get('environment'),
        docker_image=value.get('dockerImage'), flavor=value.get('flavor'), command=value.get('command'),
        arguments=value.get('arguments'), labels=value.get('labels'), volumes=value.get('volumes'),
        space_id=value.get('spaceId'), timeout_seconds=value.get('timeoutSeconds'),
        status=SimpleNamespace(stage=status.get('stage'), message=status.get('message'),
                               expose_urls=status.get('exposeUrls'), ssh_url=status.get('sshUrl')),
        expose=value.get('expose'), ssh=value.get('ssh'))


def inventory(api, group):
    jobs = []
    for summary in api.list_jobs(namespace=NAMESPACE, labels={'group': group}, timeout=30):
        require(len(jobs) < 3, 'Remote group exceeds three-job budget')
        job = inspect_actual(api, summary.id)
        labels = job.labels or {}
        require(labels.get('group') == group and labels.get('stage') == STAGE and
                labels.get('project') == 'powergrid-multimap' and labels.get('panel') in PANELS and
                labels.get('segment') in ('1', '2') and labels.get('slot') in HOURS,
                'Remote group identity/labels invalid')
        require(labels['slot'] == (labels['panel'] if labels['segment'] == '1' else 'recovery'), 'Remote slot mismatch')
        require(all(j.labels['slot'] != labels['slot'] and j.id != job.id for j in jobs), 'Duplicate remote budget slot')
        jobs.append(job)
    return jobs


def validate_job(job, receipt, command):
    require(job.id == receipt['jobId'] and canonical(job.environment) == canonical(receipt['env']) and
            job.docker_image == IMAGE == receipt['image'] and job.flavor == 'cpu-upgrade' == receipt['flavor'] and
            receipt['timeout'] == str(HOURS[receipt['slot']]) + 'h' and
            type(job.timeout_seconds) is int and job.timeout_seconds == HOURS[receipt['slot']] * 3600 and
            job.command == command and not job.arguments and not job.volumes and not job.space_id and
            not job.expose and not job.ssh and not getattr(job.status, 'expose_urls', None) and
            not getattr(job.status, 'ssh_url', None), 'Actual HF job config/hours differ from pinned receipt')
    labels = dict(labels_for(receipt['group'], receipt['panel'], receipt['segment'], receipt['slot']), name=receipt['run'])
    require(job.labels == labels, 'Actual HF job labels differ')


def validate_inventory(jobs, directory, source, command):
    names = set()
    for kind in ('intents', 'receipts'):
        root = no_links(directory / kind)
        if root.exists():
            require(all(p.name in {n + '.json' for n in HOURS} and p.is_file() and not p.is_symlink()
                        for p in root.iterdir()), 'Unexpected durable budget ledger entry')
    for name in HOURS:
        intent_path, receipt_path = slot(directory, name), slot(directory, name, 'receipts')
        if not intent_path.exists():
            require(not receipt_path.exists(), 'Receipt without durable slot intent')
            continue
        names.add(name)
        require(receipt_path.is_file(), 'Uncertain intent without receipt; inspect, never retry')
        receipt = read(receipt_path, 4 * 1024**2)
        require(receipt['source'] == source and receipt['slot'] == name and receipt['requestedHours'] == HOURS[name],
                'Durable receipt/source/slot mismatch')
        require(read(intent_path, 4 * 1024**2) == {k: v for k, v in receipt.items() if k not in ('jobId', 'url')},
                'Durable intent/receipt mismatch')
        require(receipt['env'] == env_for(source, receipt['panel'], receipt['segment'], receipt['run'], receipt.get('resumeRevision')),
                'Durable receipt environment mismatch')
        expected_run = GROUP + ('-' if receipt['segment'] == 1 else '-recovery-') + receipt['panel']
        require(receipt['run'] == expected_run and receipt['group'] == GROUP,
                'Durable receipt run/group mismatch')
        matched = [j for j in jobs if j.id == receipt['jobId']]
        require(len(matched) == 1, 'Durable job absent from authoritative inventory; inspect, never retry')
        validate_job(matched[0], receipt, command)
    require(len(names) <= 3 and sum(HOURS[n] for n in names) <= 12 and len(jobs) == len(names),
            'Remote submission without durable receipt or budget exceeded')
    require({j.labels['slot'] for j in jobs} == names, 'Remote slot inventory differs from ledger')

def verify_archive(archive, source, preflight, launcher_bytes):
    require(0 < Path(archive).stat().st_size < LIMIT and Path(archive).stat().st_size == source['sourceBytes'] and
            digest(archive) == source['sourceSha256'], 'Original source archive hash/size mismatch')
    immutable_revision(source['sourceCommit'])
    with tarfile.open(archive) as tar:
        members = tar.getmembers()
        require(len(members) < 20000 and sum(m.size for m in members) < 2 * LIMIT, 'Expanded source budget')
        require(len({m.name for m in members}) == len(members), 'Duplicate archive member')
        for member in members:
            path = PurePosixPath(member.name)
            require((member.isfile() or member.isdir()) and not path.is_absolute() and '..' not in path.parts and
                    path.as_posix() == member.name and member.name != '.', 'Unsafe archive member')
        member = tar.getmember('source-manifest.json')
        require(member.isfile() and member.size <= 4 * 1024**2, 'Oversize source manifest')
        manifest = json.load(tar.extractfile(member))
        require(manifest['gitCommit'] == source['sourceCommit'], 'Original source Git commit mismatch')
        files = {m.name for m in members if m.isfile()}
        require(files == set(manifest['files']) | {'source-manifest.json'}, 'Source manifest coverage mismatch')
        for name, expected in manifest['files'].items():
            require(isinstance(expected, str) and re.fullmatch('[0-9a-f]{64}', expected), 'Invalid source manifest hash')
            with tar.extractfile(name) as handle:
                actual = hashlib.file_digest(handle, 'sha256').hexdigest()
            require(actual == expected, 'Source member hash mismatch')
        require(manifest['files'][LAUNCHER_NAME] == sha_bytes(launcher_bytes), 'Archive/committed launcher drift')
        require(manifest['files'][PREFLIGHT_NAME] == source['preflightSha256'] and
                canonical(json.load(tar.extractfile(PREFLIGHT_NAME))) == canonical(preflight), 'Archived preflight differs')
        for current in preflight['smokeIdentities'].values():
            for name, sha in current['sourceFiles'].items():
                require(manifest['files'].get(name if '/' in name else 'ai/multimap/' + name) == sha,
                        'Preflight source differs from packaged source')
            for role, provenance in current['modelProvenance'].items():
                # PPO0's checkpoint predates replica-aware training helpers.
                # The complete historical saved config remains pinned, but it
                # is not a false claim that those old training files are served.
                serving = provenance['config']
                require('servingConfig' not in provenance, 'Unexpected model provenance schema')
                if 'checkpointConfig' in provenance:
                    historical = PROTOCOL['ppo0HistoricalTraining']
                    require(role == 'ppo0' and provenance.get('historicalTrainingSource') == historical and
                            provenance['checkpointConfig']['sourceFiles'] == historical['sourceFiles'],
                            'Unexpected historical checkpoint/source exception')
                for name, sha in serving['sourceFiles'].items():
                    require(manifest['files'].get(name if '/' in name else 'ai/multimap/' + name) == sha,
                            'Frozen serving source differs from package')
            for name, sha in current['frozenSources'].items():
                require(manifest['files'].get('ai/multimap/' + name) == sha, 'Frozen original source differs from package')
        require({'ai/multimap/' + n for n in SOURCE_NAMES} <= set(manifest['files']), 'Missing frozen source/test files')
    return manifest


def intent_for(source, panel, segment, run, **extra):
    name = panel if segment == 1 else 'recovery'
    labels_for(source['group'], panel, segment, name)
    return dict(schema=SCHEMA, group=source['group'], run=run, panel=panel, segment=segment, slot=name,
                source=source, sourceCommit=source['sourceCommit'], requestedHours=HOURS[name],
                env=env_for(source, panel, segment, run, extra.get('resumeRevision')),
                image=IMAGE, flavor='cpu-upgrade', timeout=str(HOURS[name]) + 'h',
                preflightSha256=source['preflightSha256'], plannedGames=7680, plannedDealRoots=640,
                groupPlannedGames=15360, groupPlannedDealRoots=1280, jobBudget=BUDGET,
                qualified=False, qualificationEligible=False, reservedFinalSeedsUsed=False, **extra)


def submit(api, token, directory, intent, command):
    """One request, never retry; unknown responses still burn the fixed slot."""
    require((str(Path(directory).absolute()), os.getpid(), threading.get_ident()) in _HELD_LOCKS,
            'Submission requires original exclusive coordinator lock')
    name, run = intent['slot'], intent['run']
    path = slot(directory, name)
    require(not path.exists(), 'Budget slot already attempted; uncertain submissions count')
    existing = [n for n in HOURS if slot(directory, n).exists()]
    require(len(existing) + 1 <= 3 and sum(HOURS[n] for n in existing) + HOURS[name] <= 12,
            'Maximum three attempts / twelve requested job-hours exhausted')
    out = output_directory(run)
    remote_path_absent(api, run)
    verify_remote_reservation(api, intent['source'], directory)
    if intent['segment'] == 2:
        intent['lastSnapshotAuthority'] = snapshot_authority(api, directory, expected=intent['originalSnapshotAuthority'])
    exclusive_json(path, intent)
    out.mkdir(exist_ok=False)
    exclusive_json(out / 'intent.json', intent)
    job = api.run_job(image=IMAGE, command=command, env=intent['env'], secrets={'HF_TOKEN': token},
                      flavor='cpu-upgrade', timeout=intent['timeout'], name=run, namespace=NAMESPACE,
                      labels=labels_for(GROUP, intent['panel'], intent['segment'], name))
    # Persist the returned id before validation; failed inspection is not permission
    # to submit again. Never serialize JobInfo or any raw response.
    require(isinstance(job.id, str) and re.fullmatch('[A-Za-z0-9_-]+', job.id), 'Invalid returned job identity')
    record = dict(intent, jobId=job.id, url=f'https://huggingface.co/jobs/{NAMESPACE}/{job.id}')
    exclusive_json(slot(directory, name, 'receipts'), record)
    exclusive_json(out / 'launch.json', record)
    records = [read(slot(directory, n, 'receipts'), 4 * 1024**2) for n in HOURS
               if slot(directory, n, 'receipts').exists()]
    atomic_json(directory / 'launches.json', records)
    validate_job(inspect_actual(api, job.id), record, command)
    print(json.dumps(dict(run=run, jobId=job.id, slot=name, requestedHours=HOURS[name], url=record['url'])), flush=True)
    return record


def repository_head(api, repo, *, dataset=False):
    info = api.dataset_info(repo) if dataset else api.model_info(repo)
    require(info.private is True, 'Private authoritative repository required')
    return immutable_revision(info.sha)


def reservation_for(source):
    require(source['group'] == GROUP and source['reservationPath'] == f'multimap/{GROUP}/reservation.json' and
            isinstance(source['reservationOwner'], str) and re.fullmatch('[0-9a-f]{32}', source['reservationOwner']),
            'Invalid exclusive remote group owner')
    immutable_revision(source['sourceParentRevision'])
    return dict(schema='multimap-replica-stress-reservation-v1', group=GROUP,
                owner=source['reservationOwner'], observedParent=source['sourceParentRevision'], jobBudget=BUDGET,
                sourceCommit=source['sourceCommit'], sourcePath=source['sourcePath'],
                sourceSha256=source['sourceSha256'], sourceBytes=source['sourceBytes'],
                protocolSha256=source['protocolSha256'], preflightSha256=source['preflightSha256'])


def reserve_source(api, directory, source, archive):
    """One remote compare-and-swap, never retried, atomically creates source+owner.

    The absence checks were made AT sourceParentRevision, not mutable HEAD.
    Independent worktrees/hosts with that same observed parent cannot both win.
    A lost response or CAS conflict leaves the durable local intent in place.
    """
    reservation = reservation_for(source)
    payload = (canonical(reservation) + '\n').encode()
    source['reservationSha256'] = sha_bytes(payload)
    exclusive_json(directory / 'reservation.json', reservation)
    result = api.create_commit(repo_id=DATASET, repo_type='dataset',
        parent_commit=source['sourceParentRevision'],
        operations=[CommitOperationAdd(path_in_repo=source['sourcePath'], path_or_fileobj=archive),
                    CommitOperationAdd(path_in_repo=source['reservationPath'], path_or_fileobj=payload)],
        commit_message=f'{GROUP}: exclusive source/owner reservation {source["sourceCommit"]}')
    return immutable_revision(result.oid)


def verify_remote_reservation(api, source, directory):
    """Bind immutable AND current owner marker to the one original local ledger."""
    intent = read(directory / 'intent.json', 4 * 1024**2)
    require(intent['coordinator'] == coordinator(directory) and
            intent['reservationOwner'] == source['reservationOwner'] and
            intent['reservationPath'] == source['reservationPath'] and
            intent['sourceParentRevision'] == source['sourceParentRevision'],
            'Remote owner differs from original durable coordinator')
    expected = reservation_for(source)
    local = directory / 'reservation.json'
    require(read(local, 64 * 1024) == expected and digest(local) == source['reservationSha256'],
            'Local owner reservation changed')
    head = repository_head(api, DATASET, dataset=True)
    revisions = tuple(dict.fromkeys((source['sourceRevision'], head)))
    with tempfile.TemporaryDirectory(prefix='.owner-audit-', dir=directory) as temp:
        sizes = {rev: remote_size(DATASET, source['reservationPath'], rev, repo_type='dataset', maximum=64 * 1024)
                 for rev in revisions}
        for index, rev in enumerate(revisions):
            cache = Path(temp) / str(index)
            path = downloaded_file(hf_hub_download(DATASET, source['reservationPath'], revision=rev,
                                                   repo_type='dataset', cache_dir=cache), cache, sizes[rev])
            require(digest(path) == source['reservationSha256'] and read(path, 64 * 1024) == expected,
                    'Remote group reservation changed; no submission authorized')
    return head


def snapshot_authority(api, directory, revisions=None, expected=None):
    """Current original-run manifests at one immutable MODEL HEAD, not caller choice.

    Called only after both original jobs are terminal. Supplied old revisions
    are accepted only when BOTH original manifests still equal authoritative
    HEAD, including status/failure/summary hashes. Payload audits use HEAD itself.
    A second invocation immediately before reservation rejects changed evidence.
    """
    head = repository_head(api, MODEL)
    pins = {(panel, 'current'): head for panel in PANELS}
    if revisions is not None:
        for panel in PANELS:
            immutable_revision(revisions[panel])
            if revisions[panel] != head:
                pins[panel, 'requested'] = revisions[panel]
    with tempfile.TemporaryDirectory(prefix='.authority-audit-', dir=directory) as temp:
        names = {key: f'runs/{GROUP}-{key[0]}/artifacts.json' for key in pins}
        sizes = {key: remote_size(MODEL, names[key], rev, maximum=64 * 1024) for key, rev in pins.items()}
        hashes = {}
        for (panel, kind), rev in pins.items():
            key = panel, kind
            cache = Path(temp) / panel / kind
            path = downloaded_file(hf_hub_download(MODEL, names[key], revision=rev, cache_dir=cache), cache, sizes[key])
            validate_manifest(read(path, 64 * 1024))
            hashes[key] = digest(path)
        current = {panel: hashes[panel, 'current'] for panel in PANELS}
        if revisions is not None:
            require(all(hashes.get((p, 'requested'), current[p]) == current[p] for p in PANELS),
                    'Stale original snapshot differs from authoritative latest manifest')
        if expected is not None:
            require(current == expected['manifestSha256'], 'Authoritative original output changed during recovery audit')
    return dict(revision=head, manifestSha256=current)


def verify_source_remote(api, source, preflight, original, directory):
    require(api.dataset_info(DATASET).private is True, 'Private original source required')
    with tempfile.TemporaryDirectory(prefix='.source-audit-', dir=directory) as cache:
        size = remote_size(DATASET, source['sourcePath'], source['sourceRevision'], repo_type='dataset', maximum=LIMIT - 1)
        require(size == source['sourceBytes'], 'Original source metadata differs')
        archive = downloaded_file(hf_hub_download(DATASET, source['sourcePath'], revision=source['sourceRevision'],
                                                repo_type='dataset', cache_dir=cache), cache, size)
        verify_archive(archive, source, preflight, original)


def launch(group=GROUP, directory=None):
    expected = group_directory(group)
    require(directory is None or Path(directory).absolute() == expected, 'Use dedicated ai/runs/GROUP directory')
    require(not expected.exists(), 'Existing group/intent: explicit original-ledger recovery only')
    preflight = preflight_gate()
    check_local_storage(expected)
    api, token = private_api()
    require(not inventory(api, group), 'Remote group already has jobs')
    source_path = f'multimap/{group}/source.tgz'
    reservation_path = f'multimap/{group}/reservation.json'
    source_parent = repository_head(api, DATASET, dataset=True)
    require(not api.file_exists(DATASET, source_path, repo_type='dataset', revision=source_parent) and
            not api.file_exists(DATASET, reservation_path, repo_type='dataset', revision=source_parent),
            'Group source/owner already reserved at observed immutable parent')
    for panel in PANELS:
        output_directory(group + '-' + panel)
        remote_path_absent(api, group + '-' + panel)
    expected.mkdir(parents=True, exist_ok=False)
    with locked(expected):
        owner = uuid.uuid4().hex
        exclusive_json(expected / 'intent.json', dict(schema=SCHEMA, group=group, sourcePath=source_path,
                       reservationOwner=owner, reservationPath=reservation_path, sourceParentRevision=source_parent,
                       coordinator=coordinator(expected), preflightSha256=digest(ROOT / PREFLIGHT_NAME), jobBudget=BUDGET))
        verify_preflight_archive(api, preflight, expected)
        archive, commit = package(expected)
        immutable_revision(commit)
        require(commit == subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                'Source HEAD changed while packaging')
        command, original = original_command(commit)
        require(command == command_for(BOOTSTRAP), 'Committed bootstrap differs from running launcher')
        source = dict(schema=SCHEMA, group=group, sourceCommit=commit, sourcePath=source_path, sourceRepo=DATASET,
                      reservationOwner=owner, reservationPath=reservation_path, sourceParentRevision=source_parent,
                      sourceSha256=digest(archive), sourceBytes=Path(archive).stat().st_size,
                      protocolSha256=digest(PROTOCOL_PATH), preflightSha256=digest(ROOT / PREFLIGHT_NAME))
        verify_archive(archive, source, preflight, original)
        require(preflight_gate() == preflight, 'Preflight changed while packaging')
        source['sourceRevision'] = reserve_source(api, expected, source, archive)
        exclusive_json(expected / 'source.json', source)
        verify_source_remote(api, source, preflight, original, expected)
        records = []
        for panel in PANELS:
            jobs = inventory(api, group)
            validate_inventory(jobs, expected, source, command)
            records.append(submit(api, token, expected, intent_for(source, panel, 1, group + '-' + panel), command))
        return records


def verify_resume(source, receipt, revision, directory, preflight, *, require_incomplete=True):
    immutable_revision(revision)
    with tempfile.TemporaryDirectory(prefix='.resume-audit-', dir=directory) as temp:
        temp = Path(temp)
        checked = fetch_snapshot(MODEL, receipt['run'], revision, temp / 'verified', temp / 'download')
        checked['transaction'] = validate_snapshot(temp / 'verified', source, receipt['panel'], receipt['run'],
            production_identity(preflight, receipt['panel']), require_incomplete=require_incomplete)
        return checked


def terminal_initials(jobs):
    initial = {j.labels['panel']: j for j in jobs if j.labels['segment'] == '1'}
    require(set(initial) == set(PANELS), 'Both original initial jobs required before recovery')
    require(all(j.status.stage in ('COMPLETED', 'ERROR', 'CANCELED') for j in initial.values()),
            'Both initial jobs must be terminal before recovery')
    return initial


def choose_recovery(initial, audits):
    incomplete = [p for p in PANELS if not audits[p]['transaction']['complete']]
    for panel in incomplete:
        status = initial[panel].status
        require(status.stage == 'ERROR' and status.message == 'Job timeout',
                'Incomplete original must be actual ERROR / Job timeout; other failures require audit')
    require(incomplete, 'Both outputs complete; audit instead of recovery')
    return incomplete[0], incomplete[1:]  # fixed strong priority, never strength-based


def continue_panel(receipt_path, new_run, *, revision=None, missing_panel=None, peer_revision=None):
    """Explicit missing initial peer OR single shared recovery of original work.

    For recovery, revision pins the anchor panel and peer_revision pins the other
    original panel, including completed peers. Both supplied manifests must equal
    authoritative MODEL HEAD after both jobs terminate; that HEAD is fully audited
    before selecting the fixed-priority incomplete panel. A complete errored original
    can be audited but never replayed. A second recovery is never authorized.
    """
    require((revision is not None) != (missing_panel is not None), 'Choose immutable recovery OR missing initial peer')
    require((revision is not None) == (peer_revision is not None), 'Recovery requires immutable snapshots for both initials')
    anchor = read(receipt_path, 4 * 1024**2)
    group = anchor['group']
    directory = group_directory(group)
    require(directory.is_dir(), 'Original durable group coordinator required')
    with locked(directory):
        original_intent = read(directory / 'intent.json', 4 * 1024**2)
        require(original_intent['coordinator'] == coordinator(directory) and
                canonical(original_intent['jobBudget']) == canonical(BUDGET), 'Copied/changed coordinator ledger forbidden')
        source = read(directory / 'source.json', 4 * 1024**2)
        require(source['schema'] == SCHEMA and source['group'] == group and source['sourceRepo'] == DATASET and
                source['sourcePath'] == f'multimap/{group}/source.tgz', 'Invalid original source receipt')
        immutable_revision(source['sourceCommit']); immutable_revision(source['sourceRevision'])
        require(isinstance(source['sourceSha256'], str) and re.fullmatch('[0-9a-f]{64}', source['sourceSha256']),
                'Invalid source hash')
        preflight = preflight_gate()
        require(source['preflightSha256'] == original_intent['preflightSha256'] == digest(ROOT / PREFLIGHT_NAME) and
                source['protocolSha256'] == digest(PROTOCOL_PATH), 'Original source/preflight identity changed')
        check_local_storage(directory)
        command, original = original_command(source['sourceCommit'])
        api, token = private_api()
        jobs = inventory(api, group)
        validate_inventory(jobs, directory, source, command)
        verify_remote_reservation(api, source, directory)
        if 'jobId' in anchor:
            require(anchor.get('segment') == 1 and anchor.get('slot') in PANELS and
                    anchor == read(slot(directory, anchor['slot'], 'receipts'), 4 * 1024**2),
                    'Only canonical first launch receipt can authorize recovery')
        else:
            require(anchor == source and missing_panel is not None, 'Recovery requires pinned original job receipt')
        if missing_panel is not None:
            require(missing_panel in PANELS and ('panel' not in anchor or anchor['panel'] != missing_panel),
                    'Missing initial must be the unsubmitted peer')
            panel, segment, name = missing_panel, 1, missing_panel
            require(new_run == group + '-' + panel, 'Missing peer retains original fixed run ID')
        else:
            immutable_revision(revision); immutable_revision(peer_revision)
            require(not slot(directory, 'recovery').exists(), 'Shared recovery slot already attempted; budget exhausted')
            initial = terminal_initials(jobs)
            revisions = {anchor['panel']: revision, next(p for p in PANELS if p != anchor['panel']): peer_revision}
            authority = snapshot_authority(api, directory, revisions=revisions)
            audits = {p: verify_resume(source, read(slot(directory, p, 'receipts'), 4 * 1024**2), authority['revision'],
                                      directory, preflight, require_incomplete=False) for p in PANELS}
            require(all(audits[p]['manifestSha256'] == authority['manifestSha256'][p] for p in PANELS),
                    'Audited snapshot differs from authoritative manifest')
            panel, other_incomplete = choose_recovery(initial, audits)
            require(panel == anchor['panel'], 'Fixed strong-priority recovery requires that original panel receipt')
            segment, name = 2, 'recovery'
            require(new_run == group + '-recovery-' + panel, 'Recovery requires fixed GROUP-recovery-PANEL ID')
        require(not slot(directory, name).exists(), 'Budget slot already attempted; uncertain submissions count')
        output_directory(new_run)
        remote_path_absent(api, new_run)
        verify_preflight_archive(api, preflight, directory)
        verify_source_remote(api, source, preflight, original, directory)
        extra = dict(sourceArchiveReusedExactly=True)
        if revision is not None:
            extra.update(firstReceiptSha256=digest(slot(directory, panel, 'receipts')), recoveryFromJob=anchor['jobId'],
                         resumeRevision=authority['revision'], resumeAudit=audits[panel], initialSnapshotAudits=audits,
                         requestedSnapshotRevisions=revisions, originalSnapshotAuthority=authority,
                         otherIncompletePanels=other_incomplete, furtherJobsAuthorized=False,
                         completeAfterErrorRequiresAudit=[p for p in PANELS if audits[p]['transaction']['complete'] and
                                                        initial[p].status.stage != 'COMPLETED'],
                         initialJobStates={p: dict(jobId=initial[p].id, stage=initial[p].status.stage,
                             jobTimeout=initial[p].status.stage == 'ERROR' and initial[p].status.message == 'Job timeout')
                             for p in PANELS})
        # Recheck immediately before reserving; a nonterminal peer or newly
        # visible uncertain submission never gets ignored by a stale audit.
        jobs = inventory(api, group)
        validate_inventory(jobs, directory, source, command)
        if revision is not None:
            chosen, remaining = choose_recovery(terminal_initials(jobs), audits)
            require((chosen, remaining) == (panel, other_incomplete), 'Initial recovery eligibility changed')
        return submit(api, token, directory, intent_for(source, panel, segment, new_run, **extra), command)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--group', default=None)
    parser.add_argument('--output')
    parser.add_argument('--continue-launch')
    parser.add_argument('--run-id')
    parser.add_argument('--resume-revision')
    parser.add_argument('--peer-revision')
    parser.add_argument('--missing-panel', choices=PANELS)
    args = parser.parse_args()
    if args.continue_launch:
        if args.group or args.output or not args.run_id:
            parser.error('Explicit recovery uses --continue-launch --run-id, not --group/--output')
        continue_panel(args.continue_launch, args.run_id, revision=args.resume_revision,
                       peer_revision=args.peer_revision, missing_panel=args.missing_panel)
    else:
        if args.run_id or args.resume_revision or args.peer_revision or args.missing_panel:
            parser.error('Initial launch accepts only --group and --output')
        launch(args.group or GROUP, args.output)


if __name__ == '__main__':
    try:
        main()
    except Exception:
        # HTTP errors may contain private payloads; retain receipts, not traceback.
        print('Replica stress launch stopped; inspect durable ledger; never blindly retry', file=__import__('sys').stderr)
        raise SystemExit(1) from None
