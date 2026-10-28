"""Archive the complete development comparison and a compact, lossless statistics view.

Raw game archives remain at their existing immutable revisions. This operation
does not submit, simulate, infer, select a policy, or rerun the comparison.
"""
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path

from huggingface_hub import HfApi
from policy_iteration_evidence_archive import upload_evidence
from public_policy_development_job_v1 import digest, read

ROOT = Path(__file__).resolve().parents[2]
NAME = 'conservative-auction-comparison-evidence-v2'
OUT = ROOT / 'ai/runs' / NAME
RESULT = ROOT / 'ai/strong' / (NAME + '.json')
COMPARISON = ROOT / 'ai/strong/conservative-auction-development-comparison-with-attempts-v1.json'
SUMMARY = ROOT / 'ai/strong/conservative-auction-development-summary-v2.json'
DOCUMENT = ROOT / 'ai/CONSERVATIVE-AUCTION-COMPARISON-2026-10-28.md'


def save(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write('\n')


def main():
    for p in (OUT, OUT.with_suffix('.tgz'), OUT.with_suffix('.intent.json'), RESULT, SUMMARY):
        assert not p.exists(), 'Inspect prior archive intent/outcome before retrying'
    assert DOCUMENT.is_file(), 'Finish the full-result interpretation before archiving'
    spec = importlib.util.spec_from_file_location('manager', Path(__file__).with_name('manage-conservative-auction-attempts-v1.py'))
    manager = importlib.util.module_from_spec(spec); spec.loader.exec_module(manager)
    source = read(manager.SOURCE); owner = read(manager.OWNER / 'state.json')
    report = read(COMPARISON); collected = read(manager.RESULT)
    assert owner['stage'] == 'complete' and owner['completed_games'] == 10080
    process = Path('/proc') / str(owner['pid']) / 'cmdline'
    assert not process.exists() or not any(part.rsplit(b'/', 1)[-1] == b'coordinate-conservative-auction-attempts-v1.py'
        for part in process.read_bytes().split(b'\0'))
    assert report['complete'] and report['raw_receipts_reaudited'] and report['games'] == 10080
    assert report['games_per_arm'] == 3360 and report['cells_per_arm'] == 27
    assert report['independent_deals_per_count'] == 8
    assert report['candidate_selected'] is report['qualification_eligible'] is report['reserved_final_seeds_used'] is False
    assert collected['complete'] and collected['verified_jobs'] == collected['expected_jobs'] == 648
    assert owner['result_sha256'] == digest(manager.RESULT)
    assert len(report['provenance']) == report['execution']['selected_jobs'] == 648
    assert report['execution']['total_hf_attempts'] == 650
    assert len(report['execution']['failed_original_attempts']) == 2
    assert set(report['provenance']) == {row['name'] for row in source['rows']}
    sources = {Path(__file__).resolve(), COMPARISON, COMPARISON.with_suffix('.intent.json'), DOCUMENT}
    for name, sha in report['input_hashes'].items():
        assert digest(ROOT / name) == sha
        sources.add(ROOT / name)
    for name, evidence in report['provenance'].items():
        folder = manager.execution_folder(name)
        for filename, key in (('launch.json', 'launch_sha256'), ('verified.json', 'verified_sha256')):
            assert digest(folder / filename) == evidence[key]
            sources.add(folder / filename)
        assert evidence['evidence']['remote_archive_verified']
    approval = read(manager.recovery.APPROVAL)
    assert approval['allowed_retries'] == report['execution']['failed_original_attempts']
    for name, failure in approval['allowed_retries'].items():
        log = ROOT / failure['log']
        guard = manager.original.OUT / name / 'launch.json'
        assert digest(log) == failure['log_sha256'] and digest(guard) == failure['original_guard_sha256']
        sources.update((log, guard))
    # Keep every computed statistic and adverse cell. Only bulky raw provenance
    # and individual job measurements move to the archived full comparison.
    summary = {k: v for k, v in report.items() if k not in ('provenance', 'costs', 'execution')}
    summary['costs'] = {arm: {k: v for k, v in cost.items() if k != 'per_job'} for arm, cost in report['costs'].items()}
    summary['execution'] = {k: v for k, v in report['execution'].items() if k != 'execution_index'}
    summary['full_comparison'] = {'path': str(COMPARISON.relative_to(ROOT)), 'sha256': digest(COMPARISON),
        'raw_archives': 648, 'recovery': str(RESULT.relative_to(ROOT)),
        'omitted_from_compact_view': ['provenance', 'costs.*.per_job', 'execution.execution_index']}
    assert all(cost['counts']['rollout_caps'] == 0 for cost in summary['costs'].values())
    save(SUMMARY, summary); sources.add(SUMMARY)
    sources.update(ROOT / name for name in (
        'ai/RESUME.md', 'ai/CONSERVATIVE-AUCTION-DEVELOPMENT-2026-10-27.md',
        'ai/strong/conservative-auction-bootstrap-recovery-evidence-v1.json',
        'ai/strong/conservative-auction-cpu-results-evidence-v2.json',
        'ai/strong/conservative-auction-8840u-cost-review-v2.json',
        'ai/strong/policy_iteration_evidence_archive.py', 'ai/strong/strategic_collection.py',
        'ai/runs/conservative-auction-development-comparison-with-attempts-v1-first.log',
        'ai/runs/conservative-auction-development-attempts-coordinator-v1.log',
        'ai/runs/conservative-auction-development-attempts-coordinator-v1/predecessor.json'))
    assert all(p.is_file() and not p.is_symlink() for p in sources)
    api = HfApi(); repo = 'coyotte508/powergrid-ai-germany-v1'
    assert api.model_info(repo).private and not api.file_exists(repo, 'archives/' + NAME + '.tgz')
    OUT.mkdir(); manifest = {}
    for p in sorted(sources):
        name = str(p.relative_to(ROOT)); target = OUT / name
        target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(p.read_bytes())
        manifest[name] = digest(target)
    save(OUT / 'manifest.json', manifest)
    intent = {'created_at': datetime.now(timezone.utc).isoformat(), 'stage': 'prepared_for_upload',
        'manifest_sha256': digest(OUT / 'manifest.json')}
    save(OUT.with_suffix('.intent.json'), intent)
    archive = upload_evidence(OUT)
    save(RESULT, {'status': 'complete_development_comparison_independently_reaudited',
        'comparison_sha256': digest(COMPARISON), 'summary_sha256': digest(SUMMARY),
        'collected_result_sha256': digest(manager.RESULT), 'source_sha256': digest(manager.SOURCE),
        'protocol_sha256': report['protocol_sha256'], 'games': 10080, 'selected_jobs': 648,
        'total_hf_attempts': 650, 'failed_original_attempts_preserved': 2, 'raw_archives': 648,
        'new_hf_jobs': 0, 'new_games': 0, 'new_inference': 0, 'new_gradient_updates': 0,
        'candidate_selected': False, 'qualification_eligible': False, 'reserved_final_seeds_used': False,
        'archive': archive})
    OUT.with_suffix('.intent.json').write_text(json.dumps({**intent, 'stage': 'uploaded_download_verified',
        'archive': archive, 'descriptor_sha256': digest(RESULT)}, indent=2) + '\n')
    print(json.dumps(archive), flush=True)


if __name__ == '__main__': main()
