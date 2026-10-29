"""Collect original confirmation evidence after an inspected incomplete timeout.

Never launches jobs, changes the frozen grid, fills missing games, selects a
policy, or writes a complete-grid result. Failed originals remain explicit.
"""
import argparse
from contextlib import ExitStack
import fcntl
import importlib.util
import json
import os
from pathlib import Path
import re

from huggingface_hub import HfApi, hf_hub_download
from public_policy_development_job_v1 import digest, read, write
from public_policy_final_contract_v1 import object_hash
from population_policy_verification import extract_verified

spec = importlib.util.spec_from_file_location('original_confirmation_collector',
    Path(__file__).with_name('manage-current-auction-confirmation-recovery-v1.py'))
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
ROOT = m.ROOT
OWNER = ROOT / 'ai/runs/current-auction-network-resume-v1'
OLD_OWNER = ROOT / 'ai/runs/current-auction-confirmation-recovery-v1'
OUT = ROOT / 'ai/runs/current-auction-timeout-collection-v1'
KNOWN_FAILURE = 'pg-current-confirm-v1-pop-search_geo-4p-05'
KNOWN_HANDLE = '6ae2c32f3fb22a235dd50586'
DIAGNOSTIC = ROOT / 'ai/runs/current-auction-archive-receipt-inspection-v1/original-failure-check.json'


def admission():
    stopped = read(OWNER / 'state.json')
    assert stopped['stage'] == 'stopped_for_inspection'
    assert stopped['failure_type'] == 'AssertionError'
    assert stopped['failure'] == 'Preserve missing/ambiguous original archive; never resubmit'
    assert not Path(f"/proc/{stopped['pid']}").exists(), 'Original owner must have exited'
    assert not any((p / 'STOP').exists() for p in (OWNER, OLD_OWNER, OUT)), 'Respect explicit stop'
    assert all(digest(ROOT / p) == sha for p, sha in stopped['code_hashes'].items())
    m.admitted()
    source = m.source_checked()
    assert len(source['rows']) == 944 and source['games'] == 26880
    rows = {r['name']: r for r in source['rows']}
    guards = {}
    handles = []
    for p in m.OUT.glob('*/launch.json'):
        g = read(p)
        assert p.parent.name in rows and g['row'] == rows[p.parent.name]
        assert g['stage'] == 'launched' and g['source_fingerprint'] == object_hash(source)
        guards[str(p.relative_to(ROOT))] = digest(p)
        handles.append(g['job_id'])
    assert len(guards) == len(set(handles)) == stopped['submitted_jobs'] == 621
    assert read(m.OUT / KNOWN_FAILURE / 'launch.json')['job_id'] == KNOWN_HANDLE
    observed = read(DIAGNOSTIC)
    assert observed['job_id'] == KNOWN_HANDLE and observed['name'] == KNOWN_FAILURE
    assert observed['status']['stage'] == 'ERROR' and observed['status']['message'] == 'Job timeout'
    assert observed['refetched_log']['matching_receipts'] == 0
    assert observed['refetched_log']['unchanged_from_preserved'] is True
    assert observed['remote_archive']['exists'] is False
    assert digest(m.OUT / KNOWN_FAILURE / 'original-recovery-collection.log') == observed['refetched_log']['sha256']
    return source, {'owner_state_sha256': digest(OWNER / 'state.json'),
        'source_sha256': digest(m.SOURCE), 'guard_hashes': guards,
        'collector_sha256': digest(__file__), 'original_submitted_jobs': 621,
        'diagnostic_sha256': digest(DIAGNOSTIC),
        'owner_pins': stopped['code_hashes']}


def check_context(context):
    assert digest(OWNER / 'state.json') == context['owner_state_sha256']
    assert digest(m.SOURCE) == context['source_sha256']
    assert digest(__file__) == context['collector_sha256']
    assert digest(DIAGNOSTIC) == context['diagnostic_sha256']
    for p, sha in {**context['owner_pins'], **context['guard_hashes']}.items():
        assert digest(ROOT / p) == sha, 'Frozen input changed during collection'
    assert not any((p / 'STOP').exists() for p in (OWNER, OLD_OWNER, OUT))


def receipts(logs, name):
    found = []
    for line in logs.splitlines():
        if not line.startswith('{'):
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict) and set(value) == {'case', 'status', 'evidence'} and value['case'] == name:
            found.append(value)
    return found


def failure(folder, row, status, category, **details):
    record = {**status, 'row': row, 'category': category,
        'source_sha256': digest(m.SOURCE), 'guard_sha256': digest(folder / 'launch.json'),
        'verified': False, 'qualified': False, 'new_jobs': 0, 'new_games': 0, **details}
    path = OUT / 'failures' / (row['name'] + '.json')
    assert not path.exists(), 'Inspect the existing failure; never overwrite it'
    m.write_new(path, record)
    return record


def collect_terminal(api, source, row, status):
    folder = m.OUT / row['name']
    logs = '\n'.join(str(x) for x in api.fetch_job_logs(job_id=status['job_id'], follow=False))
    log = folder / 'original-recovery-collection.log'
    if log.exists() and log.read_text() != logs:
        changed = OUT / 'failures' / (row['name'] + '.changed.log')
        with changed.open('x') as stream:
            stream.write(logs)
        return None, failure(folder, row, status, 'changed_original_log',
            original_log_sha256=digest(log), changed_log_sha256=digest(changed))
    if not log.exists():
        with log.open('x') as stream:
            stream.write(logs)
    found = receipts(logs, row['name'])
    if len(found) != 1:
        return None, failure(folder, row, status, 'missing_or_ambiguous_original_archive_receipt',
            receipt_count=len(found), original_log_sha256=digest(log))
    evidence = found[0]['evidence']
    try:
        assert evidence['repo'] == 'coyotte508/powergrid-ai-germany-v1'
        assert evidence['archive_path'] == 'archives/' + row['name'] + '.tgz'
        assert evidence['remote_archive_verified']
        assert re.fullmatch('[a-f0-9]{40}', evidence['revision'])
        archive = Path(hf_hub_download(evidence['repo'], evidence['archive_path'], revision=evidence['revision']))
        assert digest(archive) == evidence['archive_sha256']
        if not (folder / 'artifacts').exists():
            extract_verified(archive, folder / 'artifacts')
        extra = {}
        if status['stage'] == 'COMPLETED':
            review = m.base.verify_artifacts(folder / 'artifacts', source, row, evidence)
            destination = folder / 'verified.json'
        elif status['stage'] == 'ERROR':
            original_failure = folder / 'preserved-terminal-error-v1.json'
            if not original_failure.exists():
                m.write_new(original_failure, {**status, 'evidence': evidence, 'original_failed': True})
            review = m.recovery.prepare(folder / 'artifacts', m.LOCAL / 'source/artifact',
                source, row, evidence, folder / 'terminal-recovery-v1')
            extra = {'recovery_validator_sha256': digest(m.recovery.__file__),
                'recovery_audit_sha256': digest(folder / 'terminal-recovery-v1/review.json')}
            destination = folder / 'verified-terminal-recovery-v1.json'
        else:
            raise ValueError('Unadmitted original terminal status')
        saved = {**status, 'row': row, 'verified': True, 'review': review, 'evidence': evidence,
            'source_sha256': digest(m.SOURCE), 'guard_sha256': digest(folder / 'launch.json'), **extra}
        assert m.recovery.complete_data(saved)
        m.write_new(destination, saved)
        return saved, None
    except (AssertionError, ValueError, KeyError) as error:
        return None, failure(folder, row, status, 'original_archive_or_audit_rejected',
            failure_type=type(error).__name__, original_log_sha256=digest(log))


def cycle(api, source, limit):
    assert type(limit) is int and 1 <= limit <= 64
    audited, failed, active, deferred, unsubmitted = [], [], [], [], []
    attempted = 0
    for row in source['rows']:
        folder = m.OUT / row['name']
        if not (folder / 'launch.json').exists():
            unsubmitted.append(row['name'])
            continue
        cached = m.cached(folder, source, row)
        rejected = OUT / 'failures' / (row['name'] + '.json')
        assert not (cached is not None and rejected.exists()), 'Failure cannot silently become success'
        if cached is not None:
            audited.append(cached)
            continue
        if rejected.exists():
            saved = read(rejected)
            assert saved['guard_sha256'] == digest(folder / 'launch.json')
            assert saved['source_sha256'] == digest(m.SOURCE) and saved['row'] == row
            assert saved['job_id'] == read(folder / 'launch.json')['job_id'] and saved['verified'] is False
            assert digest(folder / 'original-recovery-collection.log') == saved['original_log_sha256']
            if 'changed_log_sha256' in saved:
                assert digest(OUT / 'failures' / (row['name'] + '.changed.log')) == saved['changed_log_sha256']
            failed.append(saved)
            continue
        status = m.base.original_status(api, source, row)
        if status['stage'] in ('RUNNING', 'SCHEDULING', 'PENDING', 'STARTING'):
            active.append(status)
            continue
        if attempted >= limit:
            deferred.append(status)
            continue
        attempted += 1
        saved, rejected = collect_terminal(api, source, row, status)
        if saved is not None:
            audited.append(saved)
            print(json.dumps({'audited': row['name'], 'original_hf_stage': status['stage'],
                'games': saved['review']['games']}), flush=True)
        else:
            failed.append(rejected)
            print(json.dumps({'preserved_failure': row['name'], 'original_hf_stage': status['stage'],
                'category': rejected['category']}), flush=True)
    return {'checked_at': m.now(), 'expected_jobs': len(source['rows']),
        'verified_jobs': len(audited), 'failed_originals': failed, 'active_originals': active,
        'deferred_terminals': deferred, 'unsubmitted_jobs': unsubmitted,
        'audited_originals': [{'name': j['row']['name'], 'job_id': j['job_id'],
            'stage': j['stage'], 'evidence': j['evidence']} for j in audited],
        'complete': False, 'qualified': False, 'reserved_final_seeds_used': False,
        'new_jobs': 0, 'new_games': 0,
        'interpretation': 'Evidence preservation only. Incomplete original shards remain failures; no survivor-only comparison or selection.'}


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--limit', type=int, default=8)
    args = parser.parse_args()
    with ExitStack() as stack:
        for owner in (OWNER, OLD_OWNER):
            lock = stack.enter_context((owner / '.owner.lock').open('a'))
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        stack.enter_context(m.base.exclusive_operation())
        source, context = admission()
        OUT.mkdir(exist_ok=True)
        (OUT / 'failures').mkdir(exist_ok=True)
        (OUT / 'cycles').mkdir(exist_ok=True)
        context_path = OUT / 'admitted-context.json'
        if context_path.exists():
            assert read(context_path) == context, 'Inspect changed collector/context'
        else:
            m.write_new(context_path, context)
        state = {'pid': os.getpid(), 'started_at': m.now(), 'stage': 'collecting_originals_only',
            'context_sha256': digest(context_path), 'new_jobs': 0, 'new_games': 0, 'qualified': False}
        write(OUT / 'state.json', state)
        try:
            report = cycle(HfApi(), source, args.limit)
            check_context(context)
            path = OUT / 'cycles' / (report['checked_at'].replace(':', '-') + '.json')
            m.write_new(path, report)
            state.update(stage='collection_cycle_complete', finished_at=m.now(),
                verified_jobs=report['verified_jobs'], failed_originals=len(report['failed_originals']),
                active_originals=len(report['active_originals']), deferred_terminals=len(report['deferred_terminals']),
                unsubmitted_jobs=len(report['unsubmitted_jobs']), report=str(path.relative_to(ROOT)),
                report_sha256=digest(path))
        except BaseException as error:
            state.update(stage='stopped_for_inspection', failure_type=type(error).__name__)
            raise
        finally:
            write(OUT / 'state.json', state)
        print(json.dumps(state), flush=True)


if __name__ == '__main__':
    main()
