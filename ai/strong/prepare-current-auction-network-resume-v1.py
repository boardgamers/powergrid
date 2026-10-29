"""Preserve original DNS-stop evidence and admit one deliberate owner resumption.

Only status inspection and evidence archival; no launch, collection or policy calls.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
import shutil

from huggingface_hub import HfApi
from policy_iteration_evidence_archive import upload_evidence
from public_policy_development_job_v1 import digest, read

ROOT = Path(__file__).resolve().parents[2]
STRONG = ROOT / 'ai/strong'
RUNS = ROOT / 'ai/runs'
NAME = 'current-auction-network-resume-evidence-v1'
OUT = RUNS / NAME
DESCRIPTOR = STRONG / (NAME + '.json')


def save(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write('\n')


def main():
    spec = importlib.util.spec_from_file_location('reviewed_network_owner', STRONG / 'coordinate-current-auction-network-resume-v1.py')
    resume = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(resume)
    snapshot = RUNS / 'current-auction-network-resume-initial-collection-v1.json'
    assert all(not p.exists() for p in (OUT, OUT.with_suffix('.tgz'), OUT.with_suffix('.intent.json'), DESCRIPTOR, resume.REVIEW, snapshot))
    assert not (resume.OUT / 'state.json').exists()
    old_state = resume.OLD_OUT / 'state.json'
    old_log = RUNS / 'current-auction-confirmation-recovery-v1-first.log'
    old = read(old_state)
    assert not Path(f"/proc/{old['pid']}").exists()
    assert old['stage'] == 'stopped_for_inspection' and old['failure_type'] == 'ConnectError'
    assert old['failure'] == '[Errno -2] Name or service not known'
    assert all(digest(ROOT / n) == sha for n, sha in old['code_hashes'].items())
    test_log = RUNS / 'current-auction-network-resume-tests-v1-fixture-fixed.log'
    assert 'Ran 10 tests' in test_log.read_text() and test_log.read_text().rstrip().endswith('OK')
    manager = resume.original_owner().manager_module()
    with manager.base.exclusive_operation():
        manager.admitted()
        source = manager.source_checked()
        previous = read(STRONG / 'current-auction-confirmation-recovery-progress-v1.json')
        guards = {str(p.relative_to(ROOT)): digest(p) for p in manager.OUT.glob('*/launch.json')}
        assert guards == {str((manager.OUT / g['name'] / 'launch.json').relative_to(ROOT)): g['guard_sha256'] for g in previous['original_guards']}
        assert len(guards) == 403 and all(read(ROOT / n)['stage'] == 'launched' for n in guards)
        handles = [read(ROOT / n)['job_id'] for n in guards]
        assert len(set(handles)) == 403
        collection = read(manager.OUT / 'collection-state-recovered-v1.json')
        assert collection['source_sha256'] == digest(manager.SOURCE)
        assert collection['verified_jobs'] == len(collection['jobs']) >= 339
        assert all(manager.recovery.complete_data(j) for j in collection['jobs'])
        assert {j['job_id'] for j in collection['jobs']} <= set(handles)
        # Recheck unchanged cached receipts and their manifest bindings, without
        # running independent game audits or any new policy simulation.
        cached = [manager.cached(manager.OUT / row['name'], source, row) for row in source['rows'] if (manager.OUT / row['name'] / 'launch.json').exists()]
        assert {j['job_id'] for j in cached if j is not None} == {j['job_id'] for j in collection['jobs']}
        audited = {j['job_id'] for j in collection['jobs']}
        unresolved = [g for g in previous['original_guards'] if g['job_id'] not in audited]
        api = HfApi()

        def inspect(g):
            return {'name': g['name'], 'job_id': g['job_id'],
                    'stage': api.inspect_job(job_id=g['job_id'], namespace='coyotte508').status.stage}

        with ThreadPoolExecutor(max_workers=8) as pool:
            statuses = list(pool.map(inspect, unresolved))
        assert all(s['stage'] in ('RUNNING', 'SCHEDULING', 'COMPLETED') for s in statuses), 'Inspect new terminal failure before resuming'
        save(snapshot, collection)
        sources = {Path(__file__).resolve(), STRONG / 'coordinate-current-auction-network-resume-v1.py',
                   STRONG / 'test_current_auction_network_resume_v1.py', old_state, old_log, snapshot,
                   test_log, RUNS / 'current-auction-network-resume-tests-v1-first.log',
                   RUNS / 'test-current-auction-network-resume-before-fixture-path-fix-v1.py',
                   RUNS / 'current-auction-network-stop-original-collection-v1-first.log',
                   STRONG / 'current-auction-confirmation-recovery-progress-v1.json',
                   STRONG / 'current-auction-confirmation-recovery-evidence-v1.json',
                   STRONG / 'current-auction-grid-source-v1.json',
                   STRONG / 'policy_iteration_evidence_archive.py'}
        review = {'ready_for_deliberate_resume': True, 'original_jobs_only': True,
                  'checked_at': datetime.now(timezone.utc).isoformat(),
                  'previous_owner_pid': old['pid'], 'previous_owner_stopped_at': old['updated_at'],
                  'failure_scope': 'DNS failure during read-only whoami/status inspection; no ambiguous submission',
                  'original_guard_hashes': guards, 'original_handles': handles,
                  'submitted_jobs': 403, 'audited_jobs': collection['verified_jobs'],
                  'audited_games': sum(j['review']['games'] for j in collection['jobs']),
                  'initial_collection': str(snapshot.relative_to(ROOT)),
                  'uncollected_original_statuses': statuses, 'unchanged_execution_pins': len(old['code_hashes']),
                  'input_hashes': {str(p.relative_to(ROOT)): digest(p) for p in sorted(sources)},
                  'tests': 10, 'test_fixture_import_failure_preserved': True,
                  'max_active_jobs': 64, 'planned_jobs': 944, 'planned_games': 26880,
                  'new_jobs_by_review': 0, 'new_games_by_review': 0,
                  'automatic_restarts': False, 'candidate_selected': False,
                  'qualified': False, 'reserved_final_seeds_used': False}
        save(resume.REVIEW, review)
        resume.checked_review(manager)
        sources.add(resume.REVIEW)
        sources.update(ROOT / name for name in guards)
        assert api.model_info('coyotte508/powergrid-ai-germany-v1').private
        assert not api.file_exists('coyotte508/powergrid-ai-germany-v1', 'archives/' + NAME + '.tgz')
        OUT.mkdir()
        manifest = {}
        for p in sorted(sources):
            assert p.is_file() and not p.is_symlink()
            name = str(p.relative_to(ROOT))
            target = OUT / name
            target.parent.mkdir(parents=True, exist_ok=True)
            with p.open('rb') as src, target.open('xb') as dst:
                shutil.copyfileobj(src, dst)
            assert digest(target) == digest(p)
            manifest[name] = digest(p)
        save(OUT / 'manifest.json', manifest)
        save(OUT.with_suffix('.intent.json'), {'stage': 'upload_intent', 'review_sha256': digest(resume.REVIEW)})
        archive = upload_evidence(OUT)
        save(DESCRIPTOR, {'complete': True, 'review_sha256': digest(resume.REVIEW),
                         'archive': archive, 'submitted_jobs': 403,
                         'audited_jobs': review['audited_jobs'], 'audited_games': review['audited_games'],
                         'candidate_selected': False, 'qualified': False, 'reserved_final_seeds_used': False})
        OUT.with_suffix('.intent.json').write_text(json.dumps({'stage': 'uploaded_download_verified',
            'archive': archive, 'descriptor_sha256': digest(DESCRIPTOR)}, indent=2) + '\n')
        print(json.dumps({'reviewed': True, 'audited_jobs': review['audited_jobs'],
                          'audited_games': review['audited_games'], 'archive': archive}), flush=True)


if __name__ == '__main__':
    main()
