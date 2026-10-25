"""Archive completed original wrapper engineering evidence, never rerun games."""
import argparse
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
import shutil

from policy_iteration_evidence_archive import upload_evidence
from public_policy_final_audit_v1 import read, digest

ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT/'ai/runs/public-policy-final-runner-preflight-v1'
OUT = ROOT/'ai/runs/public-policy-final-runner-evidence-v1'
DESCRIPTOR = ROOT/'ai/strong/public-policy-final-runner-evidence-v1.json'


def write_new(path, value):
    with path.open('x') as stream:
        stream.write(json.dumps(value, indent=2)+'\n')


def main():
    parser = argparse.ArgumentParser(__doc__); parser.add_argument('--archive', action='store_true', required=True)
    parser.parse_args()
    assert not OUT.exists() and not OUT.with_suffix('.tgz').exists() and not DESCRIPTOR.exists()
    result = read(RUN/'result.json'); prepared = read(RUN/'prepared.json'); state = read(RUN/'state.json')
    assert result['complete'] and result['all_game_terminals_exact'] and result['caps'] == 0
    assert result['games'] == 96 and result['offset_reference_games'] == 8 and result['exact_continuations'] == 22048
    assert result['prepared_sha256'] == digest(RUN/'prepared.json') and state['stage'] == 'complete'
    spec = importlib.util.spec_from_file_location('final_runner_engineering_check', ROOT/'ai/strong/check-public-policy-final-runner-v1.py')
    checker = importlib.util.module_from_spec(spec); spec.loader.exec_module(checker); checker.pinned(prepared)
    for name, summary in result['cases'].items():
        folder = RUN/name
        assert digest(folder/'evaluation.json') == summary['evaluation_sha256']
        assert digest(folder/'audit.json') == summary['audit_sha256']
        for filename, sha in read(folder/'audit.json')['input_hashes'].items():
            assert digest(folder/filename) == sha
    for record in read(RUN/'reference-offset/evaluation.json')['results']:
        assert read(RUN/'reference-offset'/f'game-{record["episode"]}.json') == record
        assert digest(RUN/'reference-offset'/f'decisions-{record["episode"]}.jsonl') == record['decision_receipt_sha256']
    study = read(ROOT/'ai/runs/surrogate-continuation-study-coordinator-v1/state.json')
    assert all(digest(ROOT/name) == sha for name, sha in study['code_hashes'].items())
    process = Path('/proc')/str(study['pid'])/'cmdline'
    study_live = process.exists() and b'coordinate-surrogate-continuation-study-v1.py' in process.read_bytes()
    assert study_live or study['stage'] in ('complete', 'complete_with_caps')
    original = read(ROOT/'ai/runs/public-policy-final-runner-launch-v1.json')
    wrapper_process = Path('/proc')/str(original['pid'])/'cmdline'
    assert not wrapper_process.exists() or b'check-public-policy-final-runner-v1.py' not in wrapper_process.read_bytes(), 'Original controller has not exited'
    assert read(ROOT/'ai/strong/experiments.json')['final_seed_prefix_used'] is False
    checkpoint = {'checked_at': datetime.now(timezone.utc).isoformat(),
                  'previous_goal_turn': 'progress: guarded runner prepared and original engineering games launched',
                  'current_goal_turn': 'progress: original wrapper whole-game parity verified and archived',
                  'wrapper_original_process_complete': True, 'wrapper_launch': original,
                  'original_study_owner_live': study_live, 'study_pinned_code_unchanged': True,
                  'study_state': study, 'reserved_final_seeds_used': False}
    checkpoint_path = ROOT/'ai/runs/public-policy-final-runner-completion-checkpoint-v1.json'
    write_new(checkpoint_path, checkpoint)
    paths = {p for p in RUN.rglob('*') if p.is_file() and p.name != '.owner.lock'}
    paths.update(ROOT/name for name in prepared['source_hashes'])
    paths.update({Path(__file__), checkpoint_path, ROOT/'ai/strong/policy_iteration_evidence_archive.py',
                  ROOT/'ai/strong/public-policy-final-runner-preparation-v1.json',
                  ROOT/'ai/runs/public-policy-final-runner-launch-v1.json',
                  ROOT/'ai/runs/public-policy-final-runner-execution-v1.log',
                  ROOT/'ai/runs/public-policy-final-runner-verification-v1.log'})
    OUT.mkdir(); hashes = {}
    for source in sorted(paths):
        name = str(source.relative_to(ROOT)); target = OUT/name
        target.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(source, target)
        hashes[name] = digest(source); assert digest(target) == hashes[name]
    note = OUT/'README.md'
    note.write_text('''# Guarded standalone final runner: engineering execution evidence

All 96 original wrapper games match the independent earlier runtime in every
public decision and complete terminal. This includes 80 filtered-model cases at
2–6 players, eight filtered nonzero-offset cases and eight auction-prototype
cases. Eight additional original-runtime games supply the offset reference.
All 22,048 auction continuations match exactly; timing fields are excluded.
Legacy wall-clock bookkeeping is normalized only in request comparisons.

The runtime preserves every original engine/policy file. The guarded runner
reuses arena.play and adds exact artifact/candidate/contract binding. Engineering
contracts reject reserved seed names; final contracts require selected status,
immutable selection-evidence pins and a prior matching launch intent. Eight
admission/lifecycle tests and all seven actual dry validations passed. No final
seeds, HF submissions, gradients or candidate selection occurred.

This is engineering evidence, not improved strength or AMD 8840U latency. The
HF source/launch admission and original-intent reconciliation still need to be
connected and verified before any actual reserved evaluation. Candidate selection,
fresh whole-game strength and exact complete-policy target/export/package proofs
remain mandatory. Complete package, contracts, original launch guard, raw games,
requests/responses, audit outputs, logs and checks are retained.
''')
    hashes['README.md'] = digest(note); write_new(OUT/'manifest.json', hashes)
    print(json.dumps({'stage': 'uploading', 'files': len(hashes)+1}), flush=True)
    archive = upload_evidence(OUT)
    write_new(DESCRIPTOR, {**result, 'archive': archive, 'original_launch': original,
                          'runtime_manifest_sha256': prepared['runtime_manifest_sha256'],
                          'unchanged_original_runtime_files': prepared['unchanged_original_runtime_files'],
                          'raw_result_sha256': digest(RUN/'result.json'), 'completion_checkpoint': checkpoint})
    print(json.dumps(archive), flush=True)


if __name__ == '__main__':
    main()
