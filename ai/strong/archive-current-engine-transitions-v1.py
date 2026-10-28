"""Archive fixed historical transition checks without duplicating engine/game archives."""
from datetime import datetime, timezone
import json
from pathlib import Path

from huggingface_hub import HfApi
from policy_iteration_evidence_archive import upload_evidence
from public_policy_development_job_v1 import digest, read

ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT / 'ai/runs/current-engine-transitions-v1'
NAME = 'current-engine-transitions-evidence-v1'
OUT = ROOT / 'ai/runs' / NAME
RESULT = ROOT / 'ai/strong' / (NAME + '.json')


def save(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write('\n')


def main():
    for path in (OUT, OUT.with_suffix('.tgz'), OUT.with_suffix('.intent.json'), RESULT):
        assert not path.exists(), 'Inspect existing archive intent/outcome before retrying'
    report_path = ROOT / 'ai/strong/current-engine-transitions-results-v1.json'
    report = read(report_path)
    design = read(RUN / 'design.json')
    assert report['passed'] and report['recorded_games'] == report['terminal_economies_exact'] == 33
    assert report['transitions'] == 16330 and report['original_requests_exact'] == 3443
    assert report['learner_moves'] == 4720 and report['opponent_moves'] == 11610
    assert report['changed_economic_transitions'] == report['changed_legal_menus'] == report['changed_hidden_log_transitions'] == 0
    assert report['current_action_rejections'] == report['new_inference'] == report['new_search_rollouts'] == report['new_hf_jobs'] == 0
    assert report['qualification_eligible'] is report['reserved_final_seeds_used'] is False
    assert report['design_sha256'] == digest(RUN / 'design.json')
    assert report['assessment_sha256'] == digest(RUN / 'assessment.json')
    assert report['differences_sha256'] == digest(RUN / 'differences.jsonl')
    assert all(digest(ROOT / name) == sha for name, sha in design['recorded_inputs'].items())
    assert design['python_checker_sha256'] == digest(ROOT / 'ai/strong/replay-current-engine-transitions-v1.py')
    assert design['node_checker_sha256'] == digest(ROOT / 'ai/strong/replay-current-engine-transitions-v1.cjs')
    differences = [json.loads(line) for line in (RUN / 'differences.jsonl').read_text().splitlines()]
    assert len(differences) == report['changed_log_transitions'] == 15
    assert all(row['kind'] == 'log' and row['current'] == row['old'] +
               [{'type': 'event', 'event': 'Starting Step 3.'}] for row in differences)
    sources = {Path(__file__).resolve(), report_path}
    for directory in (RUN, RUN.with_name(RUN.name + '-initial'), RUN.with_name(RUN.name + '-second')):
        sources.update(p for p in directory.rglob('*') if p.is_file())
    sources.update(ROOT / name for name in (
        'ai/strong/replay-current-engine-transitions-v1.py', 'ai/strong/replay-current-engine-transitions-v1.cjs',
        'ai/strong/current-engine-compatibility-evidence-v1.json',
        'ai/strong/current-engine-policy-evidence-v1.json',
        'ai/strong/resource-turn-full-integration-evidence-v2.json',
        'ai/strong/policy_iteration_evidence_archive.py', 'ai/strong/strategic_collection.py',
        'ai/runs/current-engine-transitions-v1-third.log',
        'ai/CURRENT-ENGINE-TRANSITIONS-2026-10-28.md', 'ai/RESUME.md',
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
    intent = {'created_at': datetime.now(timezone.utc).isoformat(), 'stage': 'prepared_for_upload',
              'manifest_sha256': digest(OUT / 'manifest.json')}
    save(OUT.with_suffix('.intent.json'), intent)
    archive = upload_evidence(OUT)
    save(RESULT, {'status': 'fixed_recorded_transitions_match_current_engine_not_strength_validation',
                 'report_sha256': digest(report_path), 'design_sha256': report['design_sha256'],
                 'assessment_sha256': report['assessment_sha256'], 'differences_sha256': report['differences_sha256'],
                 'recorded_games': 33, 'transitions': 16330, 'original_requests_exact': 3443,
                 'terminal_economies_exact': 33, 'log_differences': 15,
                 'log_difference_classification': 'Only one appended Starting Step 3 event in each affected transition.',
                 'preserved_initial_harness_failures': 2, 'new_hf_jobs': 0, 'new_inference': 0,
                 'new_full_game_trajectories': 0, 'new_gradients': 0,
                 'qualification_eligible': False, 'reserved_final_seeds_used': False, 'archive': archive})
    OUT.with_suffix('.intent.json').write_text(json.dumps({**intent, 'stage': 'uploaded_download_verified',
        'archive': archive, 'descriptor_sha256': digest(RESULT)}, indent=2) + '\n')
    print(json.dumps(archive), flush=True)


if __name__ == '__main__':
    main()
