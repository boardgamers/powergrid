"""Preserve original terminal audits and the separately admitted v4 launch."""
import importlib.util
import json
from pathlib import Path

from huggingface_hub import HfApi
from policy_iteration_evidence_archive import upload_evidence
from public_policy_development_job_v1 import digest, read

ROOT = Path(__file__).resolve().parents[2]
NAME = 'resource-runtime-terminal-evidence-v1'
OUT = ROOT / 'ai/runs' / NAME
RESULT = ROOT / 'ai/strong' / (NAME + '.json')


def save(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write('\n')


def main():
    for path in (OUT, OUT.with_suffix('.tgz'), OUT.with_suffix('.intent.json'), RESULT):
        assert not path.exists(), 'Inspect existing archive intent/outcome before retrying'
    spec = importlib.util.spec_from_file_location('launcher', Path(__file__).with_name('launch-resource-turn-runtime-v2.py'))
    launcher = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(launcher)
    source, report, _ = launcher.source_checked()
    assert report['verified_successful_jobs'] == 5 and report['verified_successful_games'] == 88
    assert report['failed_jobs_preserved'] == 1 and not report['success_gate_passed']
    sources = {Path(__file__).resolve(), launcher.SOURCE, launcher.ADMISSION, launcher.collector.RESULT}
    originals = []
    for record in report['jobs']:
        originals.append({'name': record['name'], 'job_id': record['job_id'],
                          'outcome': record['outcome'], 'archive': record['evidence']})
        if record['verified']:
            receipt = ROOT / record['verified_receipt']
            assert digest(receipt) == record['verified_receipt_sha256']
            audit = receipt.parent / 'independent-audit/result.json'
            assert digest(audit) == record['review']['independent_audit_sha256']
            sources.update((receipt, audit))
    launches = []
    for row in source['rows']:
        path = launcher.OUT / row['job']['name'] / 'launch.json'
        guard = read(path)
        assert guard['stage'] == 'launched' and guard['source'] == source and guard['row'] == row
        sources.add(path)
        launches.append({'name': row['job']['name'], 'job_id': guard['job_id'], 'launch_sha256': digest(path)})
    assert len({row['job_id'] for row in launches}) == 2
    sources.update(ROOT / name for name in (
        'ai/RESUME.md', 'ai/RESOURCE-TURN-RUNTIME-2026-10-28.md',
        'ai/RESOURCE-RUNTIME-LAUNCHER-2026-10-28.md', 'ai/RESOURCE-RUNTIME-COLLECTION-2026-10-28.md',
        'ai/RESOURCE-RUNTIME-ADMISSION-2026-10-28.md',
        'ai/strong/launch-resource-turn-runtime-v2.py', 'ai/strong/collect-resource-turn-runtime-v2.py',
        'ai/strong/collect-resource-runtime-outcomes-v2.py', 'ai/strong/resource-turn-runtime-source-v1.json',
        'ai/strong/resource-runtime-launcher-evidence-v2.json', 'ai/strong/resource-runtime-collector-evidence-v2.json',
        'ai/strong/resource-runtime-preflight-evidence-v2.json',
        'ai/strong/resource-turn-runtime-corrected-six-result-v1.json',
        'ai/strong/policy_iteration_evidence_archive.py', 'ai/strong/strategic_collection.py',
        'ai/runs/resource-turn-runtime-outcomes-v2-eleventh.log',
        'ai/runs/resource-turn-runtime-collected-v2-first.log',
        'ai/runs/resource-turn-runtime-collected-v2/state.json',
        'ai/runs/resource-turn-runtime-hf-v2/prepared.json',
        'ai/runs/resource-turn-runtime-hf-v2/upload-intent.json',
        'ai/runs/resource-turn-runtime-hf-v2/upload-receipt.json',
        'ai/runs/conservative-auction-development-attempts-coordinator-v1/state.json'))
    api = HfApi()
    repo = 'coyotte508/powergrid-ai-germany-v1'
    assert api.model_info(repo).private and not api.file_exists(repo, 'archives/' + NAME + '.tgz')
    OUT.mkdir()
    hashes = {}
    for path in sorted(sources):
        assert path.is_file() and not path.is_symlink()
        name = str(path.relative_to(ROOT))
        target = OUT / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(path.read_bytes())
        hashes[name] = digest(target)
    save(OUT / 'manifest.json', hashes)
    intent = {'created_at': launcher.now(), 'stage': 'prepared_for_upload',
              'manifest_sha256': digest(OUT / 'manifest.json')}
    save(OUT.with_suffix('.intent.json'), intent)
    archive = upload_evidence(OUT)
    save(RESULT, {'status': 'originals_terminal_failure_preserved_corrected_runtime_launched',
                 'original_outcomes_sha256': digest(launcher.collector.RESULT),
                 'originals': originals, 'verified_successful_games': 88,
                 'failed_jobs_preserved': 1, 'original_success_gate_passed': False,
                 'admission_sha256': digest(launcher.ADMISSION),
                 'corrected_source_sha256': digest(launcher.SOURCE),
                 'corrected_launches': launches, 'new_hf_jobs': 2, 'planned_runtime_games': 32,
                 'new_strength_games': 0, 'new_gradients': 0, 'automatic_retries': False,
                 'qualification_eligible': False, 'reserved_final_seeds_used': False, 'archive': archive})
    OUT.with_suffix('.intent.json').write_text(json.dumps({**intent, 'stage': 'uploaded_download_verified',
        'archive': archive, 'descriptor_sha256': digest(RESULT)}, indent=2) + '\n')
    print(json.dumps(archive), flush=True)


if __name__ == '__main__':
    main()
