"""Unadmitted bucket-backed worker around the unchanged original evaluator.

Default validates only. Execution needs an explicitly prepared decision/control
and admission bundle. No job dispatch, implicit replacement or Git commit API.
"""
import argparse
import json
from pathlib import Path
import re
import shutil
import sys

import current_auction_resource_job_v2 as base
import current_auction_bucket_checkpoints_v3 as retention
import checkpoint_bucket_archives_v3 as archives
import checkpoint_bucket_transport_v3 as transport

require, read, digest, save = base.require, base.read, base.digest, base.save
CODE = {Path(module.__file__).name: module for module in (base, base.retention, retention, archives, transport)}
ENTRY = Path(__file__).name
BASE_SHA = '3b0c5f6d764969056a99791f679ab9baecc585daa2f1d99841ab40b2004468d5'
ALLOCATION = dict(base.ALLOCATION)
TRANSPORT = {'bucket': archives.BUCKET, 'upload_attempts': 3, 'read_attempts': 3,
    'hf_hub_version': '2.0.0', 'final_archive_by': 'independent_collector', 'job_retries': 0}


def inspect(bundle, bundle_sha, source, output, *, execute=False):
    bundle, source, output = (Path(p).resolve() for p in (bundle, source, output))
    pins = base.tree(bundle, 'manifest.json', bundle_sha)
    required = {ENTRY, *CODE, 'original-source.json', 'decision.json', 'control.json'}
    require(required <= set(pins) <= required|{'admission.json'}, 'Unexpected bucket worker bundle')
    require(pins[ENTRY] == digest(__file__) and all(pins[n] == digest(m.__file__) for n,m in CODE.items()),
        'Worker code differs from prepared bundle')
    require(digest(base.__file__) == BASE_SHA and digest(base.retention.__file__) == base.RETENTION_SHA,
        'Frozen v2 source helpers changed')
    require(pins['original-source.json'] == base.SOURCE_SHA, 'Original evaluator source changed')
    original, decision, control = (read(bundle/name) for name in ('original-source.json', 'decision.json', 'control.json'))
    fields = {'version', 'scope', 'attempt_id', 'original_name', 'original_row_sha256', 'prior_failed_attempts',
        'reason', 'allocation', 'transport', 'decision_sha256', 'source_descriptor_sha256'}
    require(set(control) == fields and control['version'] == 3 and control['scope'] == 'fixed_confirmation_bucket_retention',
        'Wrong bucket worker control')
    require(control['decision_sha256'] == pins['decision.json']
        and control['source_descriptor_sha256'] == base.SOURCE_SHA, 'Control decision/source pins differ')
    require(control['allocation'] == ALLOCATION and control['transport'] == TRANSPORT,
        'Execution/transport settings changed')
    require(decision['status'] == 'transport_recovery_recorded_execution_not_admitted'
        and decision['strength_outcomes_used_for_decision'] is False
        and decision['reserved_final_seeds_used'] is False and decision['source_descriptor_sha256'] == base.SOURCE_SHA,
        'Wrong transport decision purpose')
    require(decision['allocation'] == ALLOCATION and decision['transport'] == TRANSPORT, 'Decision settings differ')
    name = control['original_name']
    rows = [row for row in original['rows'] if row['name'] == name]
    records = [record for record in decision['rows'] if record['name'] == name]
    require(len(rows) == len(records) == 1, 'Missing/duplicate frozen row')
    row, record = rows[0], records[0]
    require(record == {k: control[k] for k in ('original_row_sha256', 'reason', 'prior_failed_attempts', 'attempt_id')}|{'name': name},
        'Attempt is not the explicitly recorded recovery')
    attempt = control['attempt_id']
    require(attempt == name.replace('pg-current-confirm-v1-', 'pg-current-bucket-v3-', 1).replace('_','-')
        and name.startswith('pg-current-confirm-v1-'), 'Foreign canonical attempt')
    require(control['original_row_sha256'] == base.object_hash(row), 'Original game row changed')
    prior = control['prior_failed_attempts']
    require(control['reason'] in ('never_submitted', 'failed_transport_recovery'), 'Unsupported recovery reason')
    require((not prior) == (control['reason'] == 'never_submitted'), 'Recovery history missing/unexpected')
    require(len({p['job_id'] for p in prior}) == len(prior), 'Duplicate prior attempt')
    for previous in prior:
        require(set(previous) == {'job_id', 'attempt_id', 'stage', 'terminal_sha256', 'log_sha256'}
            and previous['stage'] == 'ERROR' and re.fullmatch('[a-f0-9]{24}', previous['job_id'])
            and all(re.fullmatch('[a-f0-9]{64}',previous[k]) for k in ('terminal_sha256','log_sha256')),
            'Failed attempt must remain explicitly bound')
    n = row['players']; shard = row['shard']
    require(n in range(2,7) and shard['players'] == n and shard['name'] == name
        and shard['seed'] == f'current-auction-confirmation-v1-{n}p'
        and shard['games'] == shard['deals']*4*n and 0 <= shard['start'] < shard['start']+shard['deals'] <= 32,
        'Frozen confirmation scope differs')
    source_pins = base.tree(source, 'source-manifest.json', original['source_manifest_sha256'])
    spec = read(base.checked(source, row['job']))
    require(digest(source/row['job']) == row['job_spec_sha256'] and spec['workers'] == 4
        and row['identity']['settings']['workers'] == 4 and row['identity']['settings']['threads'] == 1,
        'Original execution settings changed')
    for key in ('candidate', 'contract'):
        require(digest(base.checked(source, spec[key])) == row[key+'_sha256'], 'Original policy/contract changed')
    require(source_pins['public_policy_measured_job_v1.py'] == original['measured_entry_sha256']
        and source_pins['public_policy_development_job_v1.py'] == original['entry_sha256'], 'Original evaluator changed')
    require(not output.exists(), 'Inspect previous attempt; never rerun')
    require(all(not output.is_relative_to(p) and not p.is_relative_to(output) for p in (bundle, source)), 'Output overlaps source')
    core_hash = base.object_hash({k:v for k,v in pins.items() if k != 'admission.json'})
    if execute:
        require('admission.json' in pins, 'Actual prepared bucket worker admission required')
        admission = read(bundle/'admission.json')
        require(admission['passed'] is True and admission['scope'] == control['scope']
            and admission['core_files_sha256'] == core_hash and admission['control_sha256'] == pins['control.json']
            and admission['decision_sha256'] == pins['decision.json'] and admission['source_descriptor_sha256'] == base.SOURCE_SHA,
            'Prepared execution admission differs')
        require(admission['new_jobs'] == admission['new_games'] == 0 and admission['qualified'] is False
            and admission['reserved_final_seeds_used'] is False, 'Admission cannot claim execution or strength')
        for field in ('preflight_sha256', 'test_log_sha256', 'preparation_archive_sha256'):
            require(re.fullmatch('[a-f0-9]{64}', admission[field]), 'Missing prepared evidence')
    raw = output/'original-output'/name
    command = [sys.executable, '-u', '-B', str(source/'public_policy_measured_job_v1.py'),
        '--source', str(source), '--manifest-sha256', original['source_manifest_sha256'], '--job', row['job'],
        '--output', str(raw), '--source-revision', original['revision'], '--source-archive-sha256', original['sha256'],
        '--protocol-sha256', original['protocol_sha256'], '--scope', 'development']
    context = {'attempt_id': attempt, 'decision_sha256': pins['decision.json'], 'source_descriptor_sha256': base.SOURCE_SHA,
        'original_row_sha256': base.object_hash(row), 'original_row': row}
    return {'control': control, 'row': row, 'original_source': original, 'context': context, 'attempt_id': attempt,
        'command': command, 'raw_output': str(raw), 'output': str(output), 'bundle_manifest_sha256': bundle_sha,
        'core_files_sha256': core_hash, 'admission_sha256': pins.get('admission.json')}


def run(bundle, bundle_sha, source, output, *, execute=False):
    expected = inspect(bundle, bundle_sha, source, output, execute=execute)
    if not execute: return {'valid': True, 'execute': False, 'attempt_id': expected['attempt_id'],
        'games': expected['row']['shard']['games'], 'core_files_sha256': expected['core_files_sha256']}
    import huggingface_hub
    require(huggingface_hub.__version__ == TRANSPORT['hf_hub_version'], 'Unpinned bucket SDK')
    api = huggingface_hub.HfApi(); transport.BucketTransport(api).private(archives.BUCKET)
    output = Path(output).resolve(); output.mkdir(); save(output/'attempt.json', expected)
    supervisor = output/'supervisor'; ledgers = output/'transport-ledgers'; observations = []
    def upload(folder):
        observation = {'started_at': base.now(), 'directory': folder.name,
            'child_live_before_upload': base.child_live(supervisor), 'manifest_sha256': digest(folder/'manifest.json')}
        receipt = archives.upload_directory(folder, ledgers, api)
        observation.update(finished_at=base.now(), evidence=receipt, child_live_after_upload=base.child_live(supervisor))
        observations.append(observation); save(output/(folder.name+'.transport.json'), observation)
        print(json.dumps({'bucket_checkpoint': receipt, 'attempt_id': expected['attempt_id']}), flush=True)
        return receipt
    status = {'stage': 'running', 'started_at': base.now(), 'attempt_id': expected['attempt_id'],
        'original_name': expected['row']['name'], 'prior_failed_attempts': expected['control']['prior_failed_attempts'],
        'qualified': False, 'reserved_final_seeds_used': False, 'automatic_job_retries': False}
    error = None
    try:
        result = retention.supervise(expected['command'], Path(expected['raw_output'])/'job/evaluation',
            supervisor, expected['context'], upload, ALLOCATION['checkpoint_period_seconds'])
        require(result['child_returncode'] == 0 and len(result['retained_episodes']) == result['expected_episodes']
            == expected['row']['shard']['games'], 'Incomplete or failed original evaluator')
        require(any(x['child_live_before_upload'] and x['child_live_after_upload'] for x in observations),
            'No checkpoint retained while child was live')
        base.tree(source, 'source-manifest.json', expected['original_source']['source_manifest_sha256'])
        base.tree(bundle, 'manifest.json', bundle_sha)
        status.update(stage='child_complete_pending_independent_audit', supervisor=result)
    except BaseException as caught:
        error = caught; status.update(stage='failed_preserved', failure_type=type(caught).__name__)
    finally:
        status['finished_at'] = base.now(); save(output/'run-status.json', status)
        envelope = output/(expected['attempt_id']+'-final'); envelope.mkdir()
        save(envelope/'attempt.json', expected); save(envelope/'run-status.json', status)
        save(envelope/'checkpoint-transports.json', observations)
        raw = Path(expected['raw_output'])
        if raw.exists(): base.snapshot_tree(raw, envelope/'raw')
        if supervisor.exists():
            (envelope/'supervisor').mkdir()
            for p in supervisor.iterdir():
                if p.is_file() and p.suffix in ('.json', '.log'):
                    require(not p.is_symlink(), 'Symlink in supervisor metadata')
                    shutil.copyfile(p, envelope/'supervisor'/p.name)
        if ledgers.exists(): base.snapshot_tree(ledgers, envelope/'transport-ledgers')
        save(envelope/'manifest.json', {str(p.relative_to(envelope)): digest(p) for p in sorted(envelope.rglob('*')) if p.is_file()})
        receipt = archives.upload_directory(envelope, output/'final-transport', api)
        save(output/'final-bucket-receipt.json', receipt)
        print(json.dumps({'bucket_final_evidence': receipt, 'attempt_id': expected['attempt_id'], 'status': status}), flush=True)
    if error is not None: raise error
    return {'status': status, 'bucket_evidence': receipt, 'versioned_archive_pending': True, 'qualified': False}


if __name__ == '__main__':
    p = argparse.ArgumentParser(__doc__)
    for name in ('bundle', 'source', 'output'): p.add_argument('--'+name, type=Path, required=True)
    p.add_argument('--bundle-manifest-sha256', required=True); p.add_argument('--execute', action='store_true')
    args = p.parse_args()
    print(json.dumps(run(args.bundle, args.bundle_manifest_sha256, args.source, args.output, execute=args.execute)), flush=True)
