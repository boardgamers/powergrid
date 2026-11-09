"""Continuation-only control-plane adapter for the frozen replica-stress launch.

The request's timeoutSeconds and the current response's timeout are different
API contracts. Decode *actual* response metadata; a receipt is never a fallback.
Only disabled expose/SSH configurations are normalized. Nothing here changes the
worker, source archive, canonical receipts, requested-hour accounting or guards.
The failed strong admission already consumed its 6h slot; it must not be retried.

This file and its test are deliberately NOT members of the 13 frozen SOURCES.
The original archive is pinned below; HEAD may advance for bookkeeping/this
adapter, but all 13 files and the preflight must still match SOURCE_GIT exactly.
No initial-launch API or CLI is provided. Missing-peer continuation is mixed only;
recovery retains the original terminal/timeout/latest-authority/priority checks.
"""
import argparse
import hashlib
from pathlib import Path
import re
import subprocess
from types import FunctionType, SimpleNamespace

from huggingface_hub.utils import get_session, hf_raise_for_status
import launch_replica_stress_v1 as original

SOURCE_GIT = '7bab96167ee32d691b2ccc450c50162283b0a473'
SOURCE_REVISION = '6eec23b7c0b07c2ae3514f46d1e9b5157f79c969'
SOURCE_SHA256 = 'ccf09e2cb52e30ec1c96008c6bf9bd5e7ee80291742dd220d5c9d0681c0f3c08'
FROZEN_SOURCE_NAMES = (
    'replica-stress-protocol-v1.json', 'replica_stress_game_v1.cjs',
    'replica_stress_rollout_v1.py', 'replica_stress_study_v1.py', 'job_replica_stress_v1.py',
    'launch_replica_stress_v1.py', 'preflight_replica_stress_v1.py', 'test_replica_stress_v1.cjs',
    'test_replica_stress_rollout_v1.py', 'test_replica_stress_study_v1.py',
    'test_job_replica_stress_v1.py', 'test_launch_replica_stress_v1.py', 'test_preflight_replica_stress_v1.py',
)
FROZEN_PREFLIGHT_NAME = 'ai/multimap/replica-stress-preflight-v1.json'


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _disabled_expose(value):
    if value is None or value is False or type(value) is list and not value:
        return False
    _require(type(value) is dict and set(value) == {'ports'} and
             type(value['ports']) is list and not value['ports'],
             'Actual expose configuration is not explicitly disabled')
    return False


def _disabled_ssh(value):
    if value is None or value is False:
        return False
    _require(type(value) is dict and set(value) == {'enabled'} and value['enabled'] is False,
             'Actual SSH configuration is not explicitly disabled')
    return False


def decode_actual(raw):
    """Return only the old inspector's allowlisted fields, never the raw body.

    Both timeout aliases, when present, must be positive *integers* and equal.
    Unknown exposure shapes fail closed, including false-like numeric values.
    Status endpoints are retained for the unchanged validate_job to reject;
    normalizing disabled configuration must never erase active-endpoint evidence.
    Unknown response/status fields (notably secrets) are not retained or logged.
    """
    _require(type(raw) is dict, 'Actual job metadata must be an object')
    timeouts = [raw[name] for name in ('timeoutSeconds', 'timeout') if name in raw]
    _require(timeouts and all(type(value) is int and value > 0 for value in timeouts),
             'Actual job timeout missing or invalid')
    _require(all(value == timeouts[0] for value in timeouts), 'Actual job timeout aliases conflict')
    status = raw.get('status', {})
    _require(type(status) is dict, 'Actual job status must be an object')
    expose, ssh = _disabled_expose(raw.get('expose')), _disabled_ssh(raw.get('ssh'))
    return SimpleNamespace(
        id=raw.get('id'), environment=raw.get('environment'), docker_image=raw.get('dockerImage'),
        flavor=raw.get('flavor'), command=raw.get('command'), arguments=raw.get('arguments'),
        labels=raw.get('labels'), volumes=raw.get('volumes'), space_id=raw.get('spaceId'),
        timeout_seconds=timeouts[0], expose=expose, ssh=ssh,
        status=SimpleNamespace(stage=status.get('stage'), message=status.get('message'),
                               expose_urls=status.get('exposeUrls'), ssh_url=status.get('sshUrl')),
    )


def inspect_actual(api, job_id):
    """One authenticated raw GET, no retry/JobInfo lookup/receipt fallback.

    Do not print or serialize HTTP exceptions: they can contain private bodies.
    Callers may validate the returned allowlist with original.validate_job.
    """
    _require(isinstance(job_id, str) and re.fullmatch('[A-Za-z0-9_-]+', job_id), 'Unsafe job ID')
    try:
        response = get_session().get(f'{api.endpoint}/api/jobs/{original.NAMESPACE}/{job_id}',
                                     headers=api._build_hf_headers(), timeout=30)
        hf_raise_for_status(response)
        raw = response.json()
    except Exception:
        raise ValueError('Actual HF job metadata request failed; inspect durable ledger') from None
    return decode_actual(raw)


def verify_frozen_source(source):
    """Offline pin check, in addition to (never instead of) original preflight.

    sourceCommit is the canonical ledger's Git field. An optional sourceGit
    alias cannot contradict it. Revision/hash pins prohibit repackaging even at
    the same Git commit. No ledger or source file is written by this check.
    """
    _require(type(source) is dict and source.get('sourceCommit') == SOURCE_GIT and
             source.get('sourceGit', SOURCE_GIT) == SOURCE_GIT and
             source.get('sourceRevision') == SOURCE_REVISION and source.get('sourceSha256') == SOURCE_SHA256,
             'Only the frozen original source archive is authorized')
    _require(original.SOURCE_NAMES == FROZEN_SOURCE_NAMES and original.PREFLIGHT_NAME == FROZEN_PREFLIGHT_NAME,
             'Frozen source/preflight membership changed')
    names = (FROZEN_PREFLIGHT_NAME, *('ai/multimap/' + name for name in FROZEN_SOURCE_NAMES))
    for name in names:
        committed = subprocess.check_output(['git', 'show', SOURCE_GIT + ':' + name],
                                            cwd=original.ROOT, stderr=subprocess.DEVNULL)
        current = original.no_links(Path(original.ROOT) / name).read_bytes()
        _require(hashlib.sha256(committed).digest() == hashlib.sha256(current).digest(),
                 'Frozen original source/preflight differs from SOURCE_GIT')


def _preflight_gate():
    # The unchanged continuation calls this under its original coordinator lock,
    # before private_api/inventory or any paid request. Its own HEAD/current-file,
    # real 396/198 preflight, budget and serving identity checks still run in full.
    source = original.read(original.group_directory() / 'source.json', 4 * 1024**2)
    verify_frozen_source(source)
    return original.preflight_gate()


def _bind(function, **replacements):
    """Clone a function's globals privately; never assign to the old module."""
    namespace = dict(function.__globals__)
    namespace.update(replacements)
    bound = FunctionType(function.__code__, namespace, function.__name__, function.__defaults__, function.__closure__)
    bound.__kwdefaults__ = function.__kwdefaults__
    bound.__doc__ = function.__doc__
    return bound


def _bound_functions():
    inventory = _bind(original.inventory, inspect_actual=inspect_actual)
    submit = _bind(original.submit, inspect_actual=inspect_actual)
    continuation = _bind(original.continue_panel, inventory=inventory, submit=submit, preflight_gate=_preflight_gate)
    return SimpleNamespace(inventory=inventory, submit=submit, continue_panel=continuation)


def continue_panel(receipt_path, new_run, *, revision=None, missing_panel=None, peer_revision=None):
    """Explicit canonical initial-receipt continuation, never a fresh launch.

    Only the missing mixed peer is permitted in missing-panel mode. The original
    strong 6h receipt remains consumed even though its post-submit admission
    failed. Recovery uses both immutable revisions and all unchanged old guards.
    """
    _require((revision is not None) != (missing_panel is not None),
             'Choose immutable recovery OR missing mixed peer')
    _require((revision is not None) == (peer_revision is not None),
             'Recovery requires immutable snapshots for both initials')
    _require(missing_panel is None or missing_panel == 'mixed', 'Only the missing mixed peer is authorized')
    anchor = original.read(receipt_path, 4 * 1024**2)
    _require(type(anchor) is dict and 'jobId' in anchor and anchor.get('segment') == 1 and
             anchor.get('slot') in original.PANELS,
             'Canonical original initial-job receipt required; no source-only initial launch')
    return _bound_functions().continue_panel(receipt_path, new_run, revision=revision,
                                             missing_panel=missing_panel, peer_revision=peer_revision)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--continue-launch', required=True, help='Canonical original initial-job receipt')
    parser.add_argument('--run-id', required=True)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--missing-panel', choices=('mixed',))
    mode.add_argument('--resume-revision')
    parser.add_argument('--peer-revision')
    args = parser.parse_args(argv)
    if (args.resume_revision is not None) != (args.peer_revision is not None):
        parser.error('Recovery requires --resume-revision AND --peer-revision; missing-peer mode accepts neither')
    return continue_panel(args.continue_launch, args.run_id, revision=args.resume_revision,
                          missing_panel=args.missing_panel, peer_revision=args.peer_revision)


if __name__ == '__main__':
    try:
        main()
    except Exception:
        # Never disclose raw HTTP payloads, credentials or response exceptions.
        print('Replica stress reconciliation stopped; retain original ledger; never blindly retry',
              file=__import__('sys').stderr)
        raise SystemExit(1) from None
