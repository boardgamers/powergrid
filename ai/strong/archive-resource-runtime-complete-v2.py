"""Archive the two audited v4 pilots without rerunning or duplicating raw games."""
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path

from huggingface_hub import HfApi
from policy_iteration_evidence_archive import upload_evidence
from public_policy_development_job_v1 import digest, read

ROOT = Path(__file__).resolve().parents[2]
NAME = 'resource-runtime-complete-evidence-v2'
OUT = ROOT / 'ai/runs' / NAME
RESULT = ROOT / 'ai/strong' / (NAME + '.json')


def save(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write('\n')


def main():
    for p in (OUT, OUT.with_suffix('.tgz'), OUT.with_suffix('.intent.json'), RESULT):
        assert not p.exists(), 'Inspect previous archive intent/outcome before retrying'
    spec = importlib.util.spec_from_file_location('collector', Path(__file__).with_name('collect-resource-turn-runtime-v2.py'))
    collector = importlib.util.module_from_spec(spec); spec.loader.exec_module(collector)
    source, originals, _ = collector.launcher.source_checked()
    guards = collector.guards_checked(source)
    report = read(collector.RESULT)
    assert report == read(collector.TERMINAL) == read(collector.OUT / 'state.json')
    assert report['complete'] and report['all_terminal'] and report['verified_jobs'] == 2 and report['verified_games'] == 32
    assert report['scope'] == 'runtime-only' and report['qualification_eligible'] is report['reserved_final_seeds_used'] is False
    assert all(report[k] == 0 for k in ('failed_jobs_preserved', 'pending_jobs', 'unverified_jobs', 'new_hf_jobs', 'new_inference', 'new_full_games', 'new_strength_games'))
    assert report['collector_sha256'] == digest(Path(collector.__file__))
    assert report['source_sha256'] == digest(collector.launcher.SOURCE)
    assert originals['verified_successful_games'] == 88 and originals['failed_jobs_preserved'] == 1
    assert originals['success_gate_passed'] is False
    sources = {Path(__file__).resolve(), Path(collector.__file__), collector.RESULT, collector.TERMINAL,
        collector.OUT / 'state.json', collector.launcher.SOURCE, collector.launcher.ADMISSION, collector.TEST}
    rows = {row['job']['name']: row for row in source['rows']}
    jobs = []
    for item in report['jobs']:
        name = item['name']; row = rows[name]; folder = collector.OUT / name
        checked = collector.cached_checked(folder, source, row, guards[name])
        assert checked['review'] == item['review'] and checked['evidence'] == item['evidence']
        assert item['outcome'] == 'verified_success' and item['stage'] == 'COMPLETED'
        assert digest(folder / 'verified.json') == item['verified_receipt_sha256']
        assert item['review']['audit']['counts']['rollout_caps'] == 0
        sources.update((folder / 'verified.json', folder / 'status.json', folder / 'job.log',
            folder / 'independent-audit/result.json', folder / 'independent-audit/driver.log',
            collector.launcher.OUT / name / 'launch.json'))
        jobs.append({k: item[k] for k in ('name', 'job_id', 'verified_receipt_sha256', 'review', 'evidence')})
    assert {j['job_id'] for j in jobs} == {'6ae23f6e41e90535df779e68', '6ae23f6e3fb22a235dd467c4'}
    counts = {key: sum(j['review']['audit']['counts'][key] for j in jobs)
        for key in jobs[0]['review']['audit']['counts']}
    assert counts['atomic_moves'] == 4174 and counts['rollouts'] == 118392 and counts['neural_decisions'] == 8868511
    sources.update(ROOT / name for name in (
        'ai/RESOURCE-RUNTIME-COMPLETE-2026-10-28.md', 'ai/RESOURCE-RUNTIME-ADMISSION-2026-10-28.md', 'ai/RESUME.md',
        'ai/strong/launch-resource-turn-runtime-v2.py', 'ai/strong/resource-runtime-terminal-evidence-v1.json',
        'ai/strong/resource-runtime-collector-evidence-v2.json', 'ai/strong/resource-runtime-preflight-evidence-v2.json',
        'ai/strong/resource-turn-boundary-policy-evidence-v2.json',
        'ai/strong/policy_iteration_evidence_archive.py', 'ai/strong/strategic_collection.py',
        'ai/runs/resource-turn-runtime-collected-v2-sixth.log'))
    api = HfApi(); repo = 'coyotte508/powergrid-ai-germany-v1'
    assert api.model_info(repo).private and not api.file_exists(repo, 'archives/' + NAME + '.tgz')
    assert all(p.is_file() and not p.is_symlink() for p in sources)
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
    save(RESULT, {'status': 'corrected_v4_resource_runtime_complete_independently_verified',
        'report_sha256': digest(collector.RESULT), 'terminal_report_sha256': digest(collector.TERMINAL),
        'source_sha256': report['source_sha256'], 'admission_sha256': report['admission_sha256'],
        'verified_jobs': 2, 'verified_games': 32, 'counts': counts, 'jobs': jobs,
        'original_success_gate_passed': False, 'original_failed_jobs_preserved': 1,
        'scope': 'runtime-only', 'new_hf_jobs': 0, 'new_inference': 0, 'new_games': 0, 'new_gradients': 0,
        'qualification_eligible': False, 'reserved_final_seeds_used': False, 'archive': archive})
    OUT.with_suffix('.intent.json').write_text(json.dumps({**intent, 'stage': 'uploaded_download_verified',
        'archive': archive, 'descriptor_sha256': digest(RESULT)}, indent=2) + '\n')
    print(json.dumps(archive), flush=True)


if __name__ == '__main__': main()
