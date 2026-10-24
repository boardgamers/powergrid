"""Frozen-action holdout-world diagnostic; not a fresh game-strength evaluation."""
import argparse
import json
from pathlib import Path
import shutil
import time

import numpy as np

from strategic_collection import ROOT, read, write, digest
from hybrid_search import Model
from population_hybrid_policy import PopulationPolicy
from policy_iteration_evidence_archive import upload_evidence

STRONG = ROOT / 'ai/strong'
REPLAY = ROOT / 'ai/runs/population-auction-regression-replays-v1'
OUT = ROOT / 'ai/runs/auction-world-generalization-v1'
EVIDENCE = ROOT / 'ai/runs/auction-world-generalization-evidence-v1'
DESCRIPTOR = STRONG / 'auction-world-generalization-evidence-v1.json'
DEPENDENCIES = ['ai/strong/population_hybrid_policy.py', 'ai/strong/hybrid_search.py',
                'ai/infer.py', 'ai/pool.py', 'ai/strong/feature_contract.py']


def prepare():
    assert not OUT.exists()
    replay = read(STRONG / 'population-auction-regression-replays-evidence-v1.json')
    assert replay['remote_archive_verified'] and replay['exact_replays'] == 14
    assert replay['analysis_sha256'] == digest(REPLAY / 'analysis.json')
    analysis, selection = read(REPLAY / 'analysis.json'), read(REPLAY / 'selection.json')
    roots = []
    for pair in analysis['pairs']:
        first = pair['first_divergence']
        key = pair['cases'][1]
        rows = [json.loads(line) for line in (REPLAY / key / 'decisions.jsonl').read_text().splitlines()]
        reference = rows[first['decision'] - 1]
        assert reference['search'] == first['auction_search']
        assert reference['move'] == first['auction'] and first['shared_state_verified']
        assert reference['index'] != reference['modelProposal']
        roots.append({'label': pair['label'], 'case': key, 'direction': pair['direction'],
                      'request': first['public_root']['request'], 'original_decision': reference})
    assert len(roots) == 7
    runtime = REPLAY / 'runtime'
    assert all(digest(runtime / file) == sha for file, sha in selection['runtime_hashes'].items())
    assert all(digest(ROOT / file) == digest(runtime / file) for file in DEPENDENCIES)
    protocol = {
        'purpose': 'Test whether the original selected action beats its original model baseline on new sampled worlds, conditional on these seven public roots and unchanged continuation policies.',
        'selection': 'All seven first-divergence roots from the fixed exact replay set. Outcome-selected diagnostics, never strength estimates.',
        'replay_evidence': replay, 'replay_selection_sha256': digest(REPLAY / 'selection.json'),
        'roots': roots, 'runtime': str(runtime), 'runtime_hashes': selection['runtime_hashes'],
        'python_dependencies': {file: digest(ROOT / file) for file in DEPENDENCIES},
        'runner_sha256': digest(__file__), 'model_path': selection['model_path'],
        'model_sha256': selection['model_sha256'], 'samples': 64, 'search_workers': 4,
        'max_steps': 2400, 'original_worlds': list(range(8)), 'heldout_worlds': list(range(8, 64)),
        'preserve': 'Same public seed, candidates, model, roles, prior-bid inference, engine and model-only future continuations. First eight worlds must reproduce every original candidate outcome and role/belief exactly.',
        'primary': 'Mean paired terminal-credit difference on worlds 8..63, original selected action minus original model action. Actions are fixed before holdout outcomes; do not reselect on these outcomes.',
        'uncertainty': '10,000 bootstrap samples of the 14 consecutive four-world balanced-role blocks, seed 12343. Exploratory conditional simulation interval, not game strength or multiplicity-adjusted.',
        'failure': 'Any cap, missing root or original-prefix mismatch invalidates the diagnostic. No automatic retries or scoring incomplete data.',
        'planned_rollouts': sum(len(r['original_decision']['search']['options']) * 64 for r in roots),
        'new_hf_jobs': 0, 'gradients': False, 'new_strength_games': 0,
        'qualification_eligible': False, 'reserved_final_seeds_used': False,
    }
    assert protocol['planned_rollouts'] == 2304
    OUT.mkdir()
    write(OUT / 'protocol.json', protocol)
    print(json.dumps({'prepared': True, 'roots': 7, 'rollouts': 2304,
                      'protocol_sha256': digest(OUT / 'protocol.json')}), flush=True)


def verify_root(root, result):
    old, new = root['original_decision'], result['search']
    before = old['search']
    assert result['modelProposal'] == old['modelProposal'] and not result['filterApplied']
    assert new['options'] == before['options'] and new['seed'] == before['seed']
    assert new['samples'] == 64 and new['maxSteps'] == before['maxSteps'] == 2400
    assert new['mode'] == before['mode'] and new['usable'] and new['truncated'] == 0
    assert new['evaluations'] == len(new['options']) * 64
    assert {key: value[:8] for key, value in new['sampleOutcomes'].items()} == before['sampleOutcomes']
    assert {str(i): new['worlds'][str(i)] for i in range(8)} == before['worlds']
    for key, outcomes in new['sampleOutcomes'].items():
        assert len(outcomes) == 64 and all(0 <= v <= 1 for v in outcomes)
        assert abs(float(np.mean(outcomes)) - new['meanCredits'][key]) < 1e-12
    chosen, baseline = str(old['index']), str(old['modelProposal'])
    differences = np.array(new['sampleOutcomes'][chosen]) - np.array(new['sampleOutcomes'][baseline])
    heldout = differences[8:]
    blocks = heldout.reshape(14, 4).mean(axis=1)
    rng = np.random.default_rng(12343)
    bootstrap = blocks[rng.integers(14, size=(10000, 14))].mean(axis=1)
    return {'label': root['label'], 'direction': root['direction'], 'original_selected_action': old['move'],
            'original_selected_index': old['index'], 'model_baseline_index': old['modelProposal'],
            'original_eight_world_margin': float(differences[:8].mean()),
            'heldout_56_world_margin': float(heldout.mean()),
            'heldout_block_bootstrap_95_interval': np.quantile(bootstrap, [.025, .975]).tolist(),
            'heldout_better_worlds': int((heldout > 0).sum()), 'heldout_worse_worlds': int((heldout < 0).sum()),
            'heldout_equal_worlds': int((heldout == 0).sum()), 'heldout_block_means': blocks.tolist(),
            'all_original_candidate_outcomes_match': True, 'all_original_roles_beliefs_match': True,
            'rollouts': new['evaluations'], 'caps': 0}


def run():
    protocol = read(OUT / 'protocol.json')
    assert protocol['runner_sha256'] == digest(__file__)
    assert digest(Path(protocol['model_path'])) == protocol['model_sha256']
    runtime = Path(protocol['runtime'])
    assert all(digest(runtime / name) == sha for name, sha in protocol['runtime_hashes'].items())
    assert all(digest(ROOT / name) == sha for name, sha in protocol['python_dependencies'].items())
    with (OUT / 'run-intent.json').open('x') as handle:
        json.dump({'started_at_unix': time.time(), 'automatic_retries': False}, handle)
    model = Model(protocol['model_path'], threads=1)
    policy = PopulationPolicy(model, runtime / 'ai/strong/population-hybrid-policy.cjs',
                              arm='auction', samples=64, workers=4, max_steps=2400)
    checks = []
    try:
        for i, root in enumerate(protocol['roots']):
            result = policy.choose(root['request'])
            # JSON-normalize world keys exactly as saved original receipts.
            result = json.loads(json.dumps(result, allow_nan=False))
            write(OUT / f'root-{i}-result.json', result)
            check = verify_root(root, result)
            write(OUT / f'root-{i}-check.json', check)
            checks.append(check)
            print(json.dumps({'completed': len(checks), 'label': root['label'],
                              'seconds': result['elapsedMs']/1000, 'prefix_exact': True}), flush=True)
    finally:
        policy.close()
    assert len(checks) == 7 and sum(c['rollouts'] for c in checks) == 2304
    write(OUT / 'assessment.json', {'protocol_sha256': digest(OUT / 'protocol.json'),
                                  'all_complete': True, 'checks': checks, 'rollouts': 2304,
                                  'caps': 0, 'new_hf_jobs': 0, 'gradients': False,
                                  'new_strength_games': 0, 'qualification_eligible': False,
                                  'reserved_final_seeds_used': False})


def archive():
    assert not EVIDENCE.exists() and not EVIDENCE.with_suffix('.tgz').exists() and not DESCRIPTOR.exists()
    protocol, assessment = read(OUT / 'protocol.json'), read(OUT / 'assessment.json')
    assert assessment['all_complete'] and assessment['protocol_sha256'] == digest(OUT / 'protocol.json')
    assert protocol['runner_sha256'] == digest(__file__)
    checks = [verify_root(root, read(OUT / f'root-{i}-result.json')) for i, root in enumerate(protocol['roots'])]
    assert checks == assessment['checks']
    assert all(digest(Path(protocol['runtime']) / name) == sha for name, sha in protocol['runtime_hashes'].items())
    assert all(digest(ROOT / name) == sha for name, sha in protocol['python_dependencies'].items())
    EVIDENCE.mkdir()
    sources = list(OUT.glob('*.json')) + [Path(__file__), STRONG / 'population-auction-regression-replays-evidence-v1.json']
    for source in sources:
        target = EVIDENCE / source.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        assert digest(source) == digest(target)
    write(EVIDENCE / 'manifest.json', {str(p.relative_to(EVIDENCE)): digest(p) for p in sorted(EVIDENCE.rglob('*')) if p.is_file()})
    result = {**assessment, 'scope': protocol['purpose'], 'limitations': [protocol['selection'], protocol['uncertainty']],
              'runner_sha256': digest(__file__), **upload_evidence(EVIDENCE)}
    write(DESCRIPTOR, result)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('stage', choices=['prepare', 'run', 'archive'])
    globals()[parser.parse_args().stage]()
