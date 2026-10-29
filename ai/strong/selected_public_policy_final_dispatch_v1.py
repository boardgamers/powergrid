"""Durable original-only dispatch for a separately admitted final release.

This storage/transport layer does not establish selection, technical readiness,
resource sizing or admission. The final manager must verify those before calling
it. There is deliberately no CLI, credential lookup or automatic retry loop.
"""
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re

from public_policy_final_audit_v1 import PROTOCOL_SHA, require, same, schedule, validate_identity
from public_policy_final_contract_v1 import fingerprint, object_hash
from public_policy_runtime_v1 import sha256

SETUP_SHA256 = 'acaa414b8e917cbfd5642b28c45802c7673f18e1f08c1a6a33d02396bd435f68'


def final_bootstrap(reference):
    """Keep the exercised dependency/download checks; change only the job entry."""
    marker = 'python -u -B /workspace/source/public_policy_measured_job_v1.py'
    require(reference.count(marker) == 1, 'Unexpected reference bootstrap')
    setup = reference.split(marker)[0]
    require(hashlib.sha256(setup.encode()).hexdigest() == SETUP_SHA256, 'Reference setup changed')
    return setup + r'''python -u -B /workspace/source/public_policy_selected_final_job_v1.py \
  --source /workspace/source --manifest-sha256 "$SOURCE_MANIFEST_SHA256" \
  --job "$FINAL_JOB" --output "/workspace/output/$FINAL_NAME" \
  --source-revision "$SOURCE_REVISION" --source-archive-sha256 "$SOURCE_SHA256" \
  --execute --upload
'''


class SubmissionUncertain(RuntimeError):
    pass


def read(path):
    return json.loads(Path(path).read_text())


def directory_sync(path):
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def durable_write(path, value, *, exclusive=False):
    path = Path(path)
    temporary = path if exclusive else path.with_name(path.name+'.pending')
    with temporary.open('x') as stream:
        json.dump(value, stream, indent=2, allow_nan=False); stream.write('\n')
        stream.flush(); os.fsync(stream.fileno())
    if not exclusive:
        os.replace(temporary, path)
    directory_sync(path.parent)


def validate_release(release, bootstrap):
    require(set(release) == {'version', 'admission_sha256', 'source', 'plan', 'allocation', 'bootstrap_sha256'},
            'Incomplete final release')
    require(type(release['version']) is int and release['version'] == 1, 'Unknown release version')
    sha256(release['admission_sha256'])
    require(sha256(release['bootstrap_sha256']) == hashlib.sha256(bootstrap.encode()).hexdigest(), 'Bootstrap changed')
    source = release['source']
    require(set(source) == {'repo', 'revision', 'archive', 'sha256', 'source_manifest_sha256'}, 'Incomplete source pin')
    require(source['repo'] == 'coyotte508/powergrid-ai-training-v1'
            and re.fullmatch('[a-f0-9]{40}', source['revision']) is not None, 'Unpinned source revision')
    require(re.fullmatch('[a-z0-9-]+\.tgz', source['archive']) is not None, 'Invalid source archive name')
    sha256(source['sha256']); sha256(source['source_manifest_sha256'])
    plan = release['plan']; identity = validate_identity(plan['identity'])
    require(set(plan) == {'version', 'candidate_sha256', 'identity', 'protocol_sha256', 'run_fingerprint', 'rows', 'jobs', 'games'},
            'Unexpected final plan fields')
    require(type(plan['version']) is int and plan['version'] == 1 and plan['protocol_sha256'] == PROTOCOL_SHA,
            'Final protocol changed')
    require(plan['run_fingerprint'] == fingerprint(plan['candidate_sha256'], identity), 'Candidate fingerprint changed')
    shards = schedule(); rows = plan['rows']
    require(len(rows) == plan['jobs'] == 320 and plan['games'] == 20160, 'Incomplete final plan')
    require([row['shard'] for row in rows] == shards, 'Reserved schedule changed')
    require(set(release['allocation']) == {s['name'] for s in shards}, 'Incomplete resource allocation')
    for row in rows:
        name = row['shard']['name']
        require(set(row) == {'name', 'job', 'contract', 'shard', 'workers'}, 'Unexpected final row')
        require(row['name'] == name and row['job'] == f'controls/{name}.job.json'
                and row['contract'] == f'controls/{name}.contract.json', 'Wrong source control path')
        require(type(row['workers']) is int and 1 <= row['workers'] <= 32, 'Invalid game concurrency')
        allocation = release['allocation'][name]
        require(set(allocation) == {'flavor', 'timeout'}, 'Incomplete allocation')
        require(isinstance(allocation['flavor'], str) and re.fullmatch('[a-z0-9-]+', allocation['flavor']) is not None,
                'Invalid HF flavor')
        # Four-deal final shards can need 13h under the measured six-player
        # runtime allowance. Actual allocation remains a separate admission.
        require(re.fullmatch('(?:[1-9]|1[0-9]|2[0-4])h', allocation['timeout']) is not None, 'Invalid timeout')
    return {r['name']: r for r in rows}


def dispatch_once(api, directory, release, name, token, bootstrap):
    """Return the original handle or attempt one submission after durable intent.

    Caller owns batch admission/concurrency and independent completed-job audit.
    Any unresolved intent blocks all further submissions in this release.
    """
    rows = validate_release(release, bootstrap)
    require(name in rows, 'Unknown final shard')
    require(isinstance(token, str) and bool(token), 'Missing job credential')
    directory = Path(directory)
    require(not directory.is_symlink(), 'Ledger cannot be a symlink')
    directory.mkdir(parents=True, exist_ok=True)
    with (directory/'.dispatch.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        pin = object_hash(release); plan_path = directory/'release.json'
        if plan_path.exists():
            require(same(read(plan_path), release), 'Reserved namespace already belongs to another release')
        else:
            require(not (directory/'jobs').exists(), 'Existing job ledger has no release pin')
            durable_write(plan_path, release, exclusive=True)
        jobs = directory/'jobs'; jobs.mkdir(exist_ok=True); directory_sync(directory)
        require(not jobs.is_symlink(), 'Job ledger cannot be a symlink')
        require(not list(jobs.glob('*.pending')), 'Unfinished receipt write; reconcile original handles')
        originals = {}
        for path in sorted(jobs.glob('*.json')):
            require(not path.is_symlink(), 'Job receipt cannot be a symlink')
            saved = read(path); original_name = path.stem
            require(original_name in rows and saved['name'] == original_name
                    and saved['release_sha256'] == pin and same(saved['row'], rows[original_name]),
                    'Original launch receipt changed')
            require(saved['stage'] == 'launched' and re.fullmatch('[a-f0-9]{24}', saved.get('job_id', '')) is not None,
                    'Unresolved original submission; reconcile it before continuing')
            originals[original_name] = saved
        if name in originals:
            return originals[name]
        row = rows[name]; path = jobs/(name+'.json')
        guard = {'stage': 'launch_intent', 'created_at': datetime.now(timezone.utc).isoformat(),
            'name': name, 'release_sha256': pin, 'row': row}
        durable_write(path, guard, exclusive=True)
        source = release['source']; allocation = release['allocation'][name]
        try:
            job = api.run_job(image='python:3.11-slim-bookworm', command=['bash', '-lc', bootstrap],
                name=name, flavor=allocation['flavor'], timeout=allocation['timeout'],
                env={'SOURCE_ARCHIVE': source['archive'], 'SOURCE_REVISION': source['revision'],
                    'SOURCE_SHA256': source['sha256'], 'SOURCE_MANIFEST_SHA256': source['source_manifest_sha256'],
                    'FINAL_JOB': row['job'], 'FINAL_NAME': name, 'HF_HUB_DISABLE_PROGRESS_BARS': '1',
                    'PYTHONDONTWRITEBYTECODE': '1'}, secrets={'HF_TOKEN': token},
                labels={'project': 'powergrid-ai', 'stage': 'selected-public-policy-final-v1'})
            require(isinstance(job.id, str) and re.fullmatch('[a-f0-9]{24}', job.id) is not None, 'Ambiguous job handle')
            guard.update(stage='launched', job_id=job.id)
        except BaseException as error:
            guard.update(stage='launch_unknown', failure_type=type(error).__name__)
            durable_write(path, guard)
            # Error strings and complete API responses can contain credentials.
            raise SubmissionUncertain('Reconcile the original submission for '+name+'; do not retry') from None
        durable_write(path, guard)
        return guard
