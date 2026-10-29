"""First resource-recovery job around the byte-identical original evaluator.

Default validates only. Actual execution requires the independently prepared
admission in the immutable supervisor bundle. No HF job submission API here.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import sys

import current_auction_recovery_checkpoints_v2 as retention

ENTRY = 'current_auction_resource_job_v2.py'
CORE = 'current_auction_recovery_checkpoints_v2.py'
DECISION_SHA = '4d23adb861704dc2ec3e8e3d358024e026175ccce13dc2efb768742c00a348fb'
SOURCE_SHA = 'a4384b10eb8a4381423731bc0c315673f9214d91c1fb336aa81ef4a7102d1c5a'
RETENTION_SHA = 'fe1edbf68b2cfda8786d9e68b133db20f4335fedd72816374db486571e37f3fe'
FAILED_NAME = 'pg-current-confirm-v1-pop-search_geo-4p-05'
FAILED_HANDLE = '6ae2c32f3fb22a235dd50586'
ATTEMPT = 'pg-current-recover-v2-pop-search-4p-05'
ALLOCATION = {'timeout': '24h', 'flavor': 'cpu-upgrade', 'game_workers': 4,
    'search_workers': 4, 'inference_threads': 1, 'checkpoint_period_seconds': 30}
require, digest, save = retention.require, retention.digest, retention.save


def read(path): return json.loads(Path(path).read_text())
def now(): return datetime.now(timezone.utc).isoformat()
def object_hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest()


def checked(root, name):
    require(isinstance(name, str) and name and not Path(name).is_absolute()
        and all(p not in ('', '.', '..') for p in name.split('/')), 'Noncanonical bundle path')
    path = root/name
    require(path.resolve().is_relative_to(root) and path.is_file(), 'Missing/escaped bundle file')
    require(not any(p.is_symlink() for p in (path, *path.parents) if p != root.parent), 'Symlink in bundle')
    return path


def tree(root, manifest_name, sha):
    root = Path(root).resolve(); path = checked(root, manifest_name)
    require(digest(path) == sha, 'Manifest differs from immutable pin')
    pins = read(path)
    require(isinstance(pins, dict) and pins and manifest_name not in pins, 'Invalid manifest')
    require(set(pins)|{manifest_name} == {str(p.relative_to(root)) for p in root.rglob('*') if p.is_file()}, 'Bundle file set changed')
    for name, value in pins.items():
        require(re.fullmatch('[a-f0-9]{64}', value) is not None and digest(checked(root, name)) == value, 'Pinned file changed: '+name)
    return pins


def inspect(bundle, bundle_sha, source, output, *, execute=False):
    bundle, source, output = Path(bundle).resolve(), Path(source).resolve(), Path(output).resolve()
    pins = tree(bundle, 'manifest.json', bundle_sha)
    require(digest(__file__) == pins[ENTRY] and digest(retention.__file__) == pins[CORE] == RETENTION_SHA, 'Supervisor code differs')
    require(set(pins) in ({ENTRY, CORE, 'original-source.json', 'decision.json', 'control.json'},
        {ENTRY, CORE, 'original-source.json', 'decision.json', 'control.json', 'admission.json'}), 'Unexpected supervisor inputs')
    require(pins['decision.json'] == DECISION_SHA and pins['original-source.json'] == SOURCE_SHA, 'Wrong frozen decision/source')
    decision, original, control = (read(bundle/name) for name in ('decision.json', 'original-source.json', 'control.json'))
    require(decision['original_failed_handle'] == FAILED_HANDLE and decision['original_audited_shards'] == 620
        and decision['original_audited_games'] == 19764 and decision['never_submitted_rows'] == 323, 'Wrong original terminal accounting')
    require(decision['status'] == 'resource_recovery_design_recorded_execution_not_admitted'
        and decision['strength_outcomes_used_for_decision'] is False, 'Wrong recovery decision')
    require(set(control) == {'version', 'scope', 'attempt_id', 'original_name', 'original_failed_handle',
        'original_row_sha256', 'allocation', 'decision_sha256', 'source_descriptor_sha256'}, 'Unexpected attempt control')
    require(type(control['version']) is int and control['version'] == 2
        and control['scope'] == 'single_original_failed_shard_technical_recovery', 'Wrong recovery scope')
    require(control['attempt_id'] == ATTEMPT and control['original_name'] == FAILED_NAME
        and control['original_failed_handle'] == FAILED_HANDLE, 'Only the one exact failed original is admitted')
    require(control['decision_sha256'] == DECISION_SHA and control['source_descriptor_sha256'] == SOURCE_SHA, 'Control pins differ')
    require(control['allocation'] == ALLOCATION, 'Effective resource controls changed')
    rows = [r for r in original['rows'] if r['name'] == FAILED_NAME]
    require(len(rows) == 1, 'Missing/duplicate original row'); row = rows[0]
    require(control['original_row_sha256'] == object_hash(row) == decision['fixed_recovery_rows'][0]['original_row_sha256'], 'Original row changed')
    require(decision['fixed_recovery_rows'][0]['name'] == FAILED_NAME and row['shard']['games'] == 16, 'Not the failed sixteen games')
    source_pins = tree(source, 'source-manifest.json', original['source_manifest_sha256'])
    spec = read(checked(source, row['job']))
    require(digest(source/row['job']) == row['job_spec_sha256'] and spec['workers'] == 4, 'Original game workers/job changed')
    require(row['identity']['settings']['workers'] == 4 and row['identity']['settings']['threads'] == 1, 'Original search/inference workers changed')
    for key in ('candidate', 'contract'):
        require(digest(checked(source, spec[key])) == row[key+'_sha256'], 'Original execution binding changed')
    require(source_pins['public_policy_measured_job_v1.py'] == original['measured_entry_sha256']
        and source_pins['public_policy_development_job_v1.py'] == original['entry_sha256'], 'Original entry changed')
    require(not output.exists(), 'Inspect any prior attempt; never rerun')
    require(all(not output.is_relative_to(root) and not root.is_relative_to(output) for root in (bundle, source)), 'Output overlaps immutable inputs')
    core_hash = object_hash({k: v for k, v in pins.items() if k != 'admission.json'})
    if execute:
        require('admission.json' in pins, 'Real prepared-control admission required before execution')
        admission = read(bundle/'admission.json')
        require(admission['passed'] is True and admission['scope'] == control['scope']
            and admission['core_files_sha256'] == core_hash
            and admission['control_sha256'] == pins['control.json']
            and admission['decision_sha256'] == DECISION_SHA
            and admission['source_descriptor_sha256'] == SOURCE_SHA,
            'Prepared-control admission does not bind this execution')
        require(admission['new_hf_jobs'] == admission['new_games'] == 0
            and admission['qualified'] is False and admission['reserved_final_seeds_used'] is False,
            'Admission must precede execution and cannot qualify strength')
        for field in ('preflight_sha256', 'test_log_sha256', 'preparation_archive_sha256'):
            require(re.fullmatch('[a-f0-9]{64}', admission[field]) is not None, 'Missing admission evidence')
    raw = output/'original-output'/FAILED_NAME
    common = ['--source', str(source), '--manifest-sha256', original['source_manifest_sha256'],
        '--job', row['job'], '--output', str(raw), '--source-revision', original['revision'],
        '--source-archive-sha256', original['sha256']]
    command = [sys.executable, '-u', '-B', str(source/'public_policy_measured_job_v1.py'),
        *common, '--protocol-sha256', original['protocol_sha256'], '--scope', 'development']
    # The measured entry executes by design; never run it for a validation-only probe.
    dry_command = [sys.executable, '-u', '-B', str(source/'public_policy_development_job_v1.py'),
        *[str(raw/'job') if value == str(raw) else value for value in common]]
    context = {'attempt_id': ATTEMPT, 'decision_sha256': DECISION_SHA, 'source_descriptor_sha256': SOURCE_SHA,
        'original_row_sha256': object_hash(row), 'original_row': row}
    return {'control': control, 'original_source': original, 'row': row, 'context': context,
        'bundle_manifest_sha256': bundle_sha, 'core_files_sha256': core_hash,
        'admission_sha256': pins.get('admission.json'), 'command': command,
        'dry_command': dry_command, 'raw_output': str(raw), 'output': str(output)}


def snapshot_tree(source, target):
    """Copy immutable final raw bytes without changing the original manifest."""
    target.mkdir(parents=True, exist_ok=False)
    paths = sorted(source.rglob('*'))
    require(not any(p.is_symlink() for p in paths), 'Symlink in raw output')
    for path in paths:
        if not path.is_file(): continue
        destination = target/path.relative_to(source); destination.parent.mkdir(parents=True, exist_ok=True)
        require(retention.copy_stable(path, destination)['stable'], 'Raw output changed during final snapshot')


def child_live(supervisor):
    start = supervisor/'child-started.json'
    if not start.exists(): return False
    pid = read(start)['pid']; status = Path(f'/proc/{pid}/stat')
    try: return status.read_text().rsplit(')', 1)[1].split()[0] != 'Z'
    except FileNotFoundError: return False


def run(bundle, bundle_sha, source, output, *, execute=False, upload=False):
    config = inspect(bundle, bundle_sha, source, output, execute=execute)
    if not execute: return {'valid': True, 'execute': False, 'core_files_sha256': config['core_files_sha256'], 'control': config['control']}
    require(upload is True, 'Recovery execution requires durable private retention')
    source, output = Path(source).resolve(), Path(output).resolve()
    # Use the original source's verified archive helper and its original dependency
    # context, not a different implementation or unpinned installed module.
    helper_path = source/'artifact/ai/strong/policy_iteration_evidence_archive.py'
    sys.path.insert(0, str(helper_path.parent))
    spec = importlib.util.spec_from_file_location('frozen_recovery_evidence_uploader', helper_path)
    helper = importlib.util.module_from_spec(spec); spec.loader.exec_module(helper)
    from huggingface_hub import HfApi
    api = HfApi(); require(api.model_info(retention.REPO).private, 'Evidence repo must remain private')
    output.mkdir(); save(output/'attempt.json', config)
    supervisor = output/'supervisor'; observations = []
    def uploader(folder):
        require(not api.file_exists(retention.REPO, 'archives/'+folder.name+'.tgz'), 'Existing evidence requires inspection')
        observation = {'started_at': now(), 'child_live_before_upload': child_live(supervisor),
            'directory': folder.name, 'manifest_sha256': digest(folder/'manifest.json')}
        evidence = helper.upload_evidence(folder)
        observation.update(finished_at=now(), evidence=evidence,
            child_live_after_upload=child_live(supervisor)); observations.append(observation)
        save(output/(folder.name+'.transport.json'), observation)
        print(json.dumps({'checkpoint_evidence': evidence, 'attempt_id': ATTEMPT}), flush=True)
        return evidence
    raw = Path(config['raw_output']); status = {'stage': 'running', 'started_at': now(),
        'attempt_id': ATTEMPT, 'original_name': FAILED_NAME, 'original_failed_handle': FAILED_HANDLE,
        'qualified': False, 'reserved_final_seeds_used': False, 'automatic_retries': False}
    caught = None
    try:
        result = retention.supervise(config['command'], raw/'job/evaluation', supervisor,
            config['context'], uploader, ALLOCATION['checkpoint_period_seconds'])
        require(result['child_returncode'] == 0, 'Original child failed; preserve evidence without retry')
        require(len(result['retained_episodes']) == result['expected_episodes'] == 16, 'Incomplete retained original episodes')
        require(any(o['child_live_before_upload'] and o['child_live_after_upload'] for o in observations), 'No verified retention while original child remained live')
        tree(source, 'source-manifest.json', config['original_source']['source_manifest_sha256'])
        tree(Path(bundle).resolve(), 'manifest.json', bundle_sha)
        status.update(stage='child_complete_pending_independent_audit', supervisor=result)
    except BaseException as error:
        caught = error; status.update(stage='failed_preserved', failure_type=type(error).__name__)
    finally:
        status['finished_at'] = now(); save(output/'run-status.json', status)
        envelope = output/(ATTEMPT+'-final'); envelope.mkdir()
        save(envelope/'attempt.json', config); save(envelope/'run-status.json', status)
        save(envelope/'checkpoint-transports.json', observations)
        if raw.exists(): snapshot_tree(raw, envelope/'raw')
        if supervisor.exists():
            meta = envelope/'supervisor'; meta.mkdir()
            for path in sorted(supervisor.iterdir()):
                if path.is_file() and path.suffix in ('.json', '.log'):
                    require(not path.is_symlink(), 'Symlink in supervisor output')
                    shutil.copyfile(path, meta/path.name)
        save(envelope/'manifest.json', {str(p.relative_to(envelope)): digest(p)
            for p in sorted(envelope.rglob('*')) if p.is_file()})
        save(output/'final-upload-intent.json', {'manifest_sha256': digest(envelope/'manifest.json'), 'automatic_retries': False})
        require(not api.file_exists(retention.REPO, 'archives/'+envelope.name+'.tgz'), 'Existing final archive requires inspection')
        final = helper.upload_evidence(envelope)
        save(output/'final-upload-receipt.json', final)
        print(json.dumps({'recovery_final_evidence': final, 'attempt_id': ATTEMPT, 'status': status}), flush=True)
    if caught is not None: raise caught
    return {'status': status, 'evidence': final, 'qualified': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--bundle', type=Path, required=True)
    parser.add_argument('--bundle-manifest-sha256', required=True)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--execute', action='store_true'); parser.add_argument('--upload', action='store_true')
    args = parser.parse_args()
    print(json.dumps(run(args.bundle, args.bundle_manifest_sha256, args.source, args.output,
        execute=args.execute, upload=args.upload)), flush=True)
