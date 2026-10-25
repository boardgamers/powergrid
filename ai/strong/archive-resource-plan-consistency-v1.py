"""Archive the completed diagnostic, referencing the immutable original screen."""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import shutil

from policy_iteration_evidence_archive import upload_evidence

ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT / 'ai/runs/resource-plan-consistency-v1'
OUT = ROOT / 'ai/runs/resource-plan-consistency-evidence-v1'


def read(path):
    return json.loads(path.read_text())


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--archive', action='store_true', required=True)
    parser.parse_args()
    result = read(RUN / 'assessment.json')
    audit = read(RUN / 'independent-audit.json')
    replays = read(RUN / 'replays.json')
    assert result['complete'] and audit['complete'] and replays['complete']
    assert audit['assessment_sha256'] == replays['assessment_sha256'] == digest(RUN / 'assessment.json')
    assert audit['replays_sha256'] == digest(RUN / 'replays.json')
    assert result['analyzer_sha256'] == digest(ROOT / 'ai/strong/resource_plan_consistency_v1.py')
    assert result['design_sha256'] == digest(ROOT / 'ai/strong/resource-plan-consistency-design-v1.json')
    assert audit['source_sha256'] == digest(ROOT / 'ai/strong/audit-resource-plan-consistency-v1.py')
    assert replays['replay_code_sha256'] == digest(ROOT / 'ai/strong/replay-resource-plan-consistency-v1.cjs')
    assert result['totals']['games'] == 1680 and result['totals']['search_decisions'] == 69624
    sources = set(p for p in RUN.iterdir() if p.is_file())
    for name in ['resource_plan_consistency_v1.py', 'test_resource_plan_consistency_v1.py',
                 'resource-plan-consistency-design-v1.json', 'replay-resource-plan-consistency-v1.cjs',
                 'audit-resource-plan-consistency-v1.py', 'archive-resource-plan-consistency-v1.py',
                 'resource-replanning-development-complete-evidence-v1.json',
                 'resource-replanning-development-plan-v1.json']:
        sources.add(ROOT / 'ai/strong' / name)
    for name in ['resource-plan-consistency-v1.log', 'resource-plan-consistency-replays-v1.log',
                 'resource-plan-consistency-audit-v1.log',
                 'surrogate-study-live-observation-20261025-resource-audit.json']:
        sources.add(ROOT / 'ai/runs' / name)
    # Small reports and selected raw receipts are retained directly. The other
    # original receipts remain pinned by inputs.json to the complete old archive.
    inputs = read(RUN / 'inputs.json')
    selected = set()
    for example in result['examples'].values():
        prefix = (f"ai/runs/resource-replanning-development-collected-v1/"
                  f"resource-replanning-development-v1-resource-filter-{example['players']}p-"
                  f"{example['opponent']}-0-4/artifacts/evaluation/")
        selected.add(prefix + f"decisions-{example['episode']}.jsonl")
    for name, expected in inputs.items():
        if name.endswith('/evaluation.json') or name in selected:
            assert digest(ROOT / name) == expected
            sources.add(ROOT / name)
    runtime = ROOT / 'ai/runs/resource-replanning-job-source-prepared-v1/layout'
    sources.add(runtime / 'resource-job-manifest.json')
    sources.add(runtime / 'resource-runtime-manifest.json')
    state_path = ROOT / 'ai/runs/surrogate-continuation-study-coordinator-v1/state.json'
    state = read(state_path)
    command = Path('/proc') / str(state['pid']) / 'cmdline'
    assert command.exists() and b'coordinate-surrogate-continuation-study-v1.py' in command.read_bytes()
    assert all(digest(ROOT / name) == sha for name, sha in state['code_hashes'].items())
    checkpoint = {'checked_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                  'original_coordinator_live': True, 'pinned_code_unchanged': True,
                  'owner_state': state, 'previous_goal_turn': 'verified wait',
                  'current_goal_turn': 'progress: complete receipt audit, independent conservation check and exact original-game replays'}
    checkpoint_path = ROOT / 'ai/runs/resource-plan-consistency-completion-checkpoint-v1.json'
    assert not checkpoint_path.exists()
    checkpoint_path.write_text(json.dumps(checkpoint, indent=2) + '\n')
    sources.add(checkpoint_path)
    assert not OUT.exists() and not OUT.with_suffix('.tgz').exists()
    OUT.mkdir()
    manifest = {}
    for source in sorted(sources):
        name = str(source.relative_to(ROOT))
        target = OUT / name
        target.parent.mkdir(parents=True, exist_ok=True)
        before = digest(source)
        shutil.copy2(source, target)
        assert digest(target) == before
        manifest[name] = before
    readme = OUT / 'README.md'
    readme.write_text('''# Resource-plan consistency diagnostic

Descriptive audit of all 1,680 resource-filter games in the completed rejected
screen, using its paired filter terminals. This archive retains every derived
transition/turn, all game/cell summaries, independent conservation/aggregation
audit, code, 54 original reports, and the raw receipts for the three hash-selected
original games replayed exactly. The other original receipts are available in the
prior complete-screen archive pinned by assessment.json and inputs.json.

For reconstruction, restore that prior archive at its repository-relative paths
and the frozen job source identified by the original complete-evidence descriptor
into ai/runs/resource-replanning-job-source-prepared-v1/layout. Its exact manifests
are included here. Run resource_plan_consistency_v1.py into a fresh directory;
the replay and independent audit helpers use the documented default output path.
Six focused unit tests passed before the original audit. No gradients, new HF
jobs, fresh strength games, adoption, production changes or reserved seeds.

The selected within-turn alternatives are legal inventory comparisons only.
Their future outcomes were not simulated. Plan changes also occur in improved
games, so neither commitment nor stable sampling has been shown to improve play.
The separately running 480-position opponent-fidelity study remains untouched.
''')
    manifest['README.md'] = digest(readme)
    (OUT / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(json.dumps({'stage': 'uploading', 'files': len(manifest) + 1}), flush=True)
    archive = upload_evidence(OUT)
    descriptor = {'complete': True, 'assessment_sha256': digest(RUN / 'assessment.json'),
                  'independent_audit_sha256': digest(RUN / 'independent-audit.json'),
                  'replays_sha256': digest(RUN / 'replays.json'), 'totals': result['totals'],
                  'original_games_replayed': 3, 'exact_replayed_learner_moves': audit['replayed_learner_moves'],
                  'contract_tests_passed': 6, 'archive': archive, 'new_strength_games': 0,
                  'new_hf_jobs': 0, 'gradients': False, 'qualification_eligible': False,
                  'reserved_final_seeds_used': False,
                  'decision': 'Keep resource search rejected. This diagnostic supports testing execution-consistent planning, not adopting commitment or claiming causal harm. Continue the unchanged auction/opponent-fidelity priority.'}
    target = ROOT / 'ai/strong/resource-plan-consistency-evidence-v1.json'
    assert not target.exists()
    target.write_text(json.dumps(descriptor, indent=2) + '\n')
    print(json.dumps(archive), flush=True)


if __name__ == '__main__':
    main()
