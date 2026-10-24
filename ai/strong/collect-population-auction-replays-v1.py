"""Archive exact replay evidence and descriptive analysis, without strength claims."""
import gzip
import json
from pathlib import Path
import shutil

from strategic_collection import ROOT, read, write, digest
from policy_iteration_evidence_archive import upload_evidence

BASE = ROOT / 'ai/runs/population-auction-regression-replays-v1'
OUT = ROOT / 'ai/runs/population-auction-regression-replays-evidence-v1'
STRONG = ROOT / 'ai/strong'
DESCRIPTOR = STRONG / 'population-auction-regression-replays-evidence-v1.json'


def collect():
    assessment, selection, analysis = (read(BASE / name) for name in ['assessment.json', 'selection.json', 'analysis.json'])
    assert not OUT.exists() and not OUT.with_suffix('.tgz').exists() and not DESCRIPTOR.exists()
    assert assessment['replays'] == 14 and assessment['all_terminal_replays_match']
    assert analysis['assessment_sha256'] == digest(BASE / 'assessment.json')
    assert assessment['selection_sha256'] == analysis['selection_sha256'] == digest(BASE / 'selection.json')
    assert selection['runner_sha256'] == digest(STRONG / 'replay-population-auction-regressions-v1.py')
    assert selection['observer_sha256'] == digest(STRONG / 'trace-public-economy.cjs')
    assert analysis['analyzer_sha256'] == digest(STRONG / 'analyze-population-auction-replays-v1.py')
    assert selection['comparison_sha256'] == digest(STRONG / 'population-hybrid-development-comparison-v1.json')
    assert selection['archive'] == read(STRONG / 'population-hybrid-development-complete-evidence-v1.json')
    assert all(digest(BASE / 'runtime' / file) == sha for file, sha in selection['runtime_hashes'].items())
    plan = read(STRONG / 'population-hybrid-development-plan-v1.json')
    assert all(digest(ROOT / file) == sha for file, sha in plan['dependency_hashes'].items())
    learner_moves = root_moves = 0
    for key, request in selection['requested'].items():
        folder, result = BASE / key, assessment['results'][key]
        assert result == read(folder / 'result.json') and result['completed'] and result['exact_terminal_replay']
        assert digest(folder / 'economy.jsonl') == result['trace_sha256']
        assert digest(folder / 'public-roots.jsonl.gz') == result['public_roots_sha256']
        assert digest(folder / 'decisions.jsonl') == request['reference']['decision_receipt_sha256']
        trace = [json.loads(line) for line in (folder / 'economy.jsonl').read_text().splitlines()]
        decisions = [json.loads(line) for line in (folder / 'decisions.jsonl').read_text().splitlines()]
        with gzip.open(folder / 'public-roots.jsonl.gz', 'rt') as handle:
            roots = [json.loads(line) for line in handle]
        seat = request['reference']['terminal']['seat']
        focal = [move for move in trace if move['seat'] == seat]
        assert len(roots) == len(decisions) == len(focal) == result['learner_decisions']
        assert len(trace) == result['moves_logged'] == request['reference']['terminal']['steps']
        assert all(left['after'] == right['before'] for left, right in zip(trace, trace[1:])), 'Broken root trace chain'
        for decision, root, move in zip(decisions, roots, focal):
            assert decision['move'] == move['action'] == root['moves'][decision['index']]
            assert decision['round'] == move['before']['round'] == root['request']['state']['round']
            assert root['modelProposal'] == decision['modelProposal']
            state = root['request']['state']
            assert state['seed'] == 'secret' and state['powerPlantsDeck'] == []
            assert not state.get('hiddenLog') and 'powerPlantDeckAfterStep3' not in state
            if state['options']['fastBid']:
                assert all(p['bid'] == 0 for p in state['players'])
            for public, observed in zip(state['players'], move['before']['players']):
                assert public['money'] == observed['money']
                assert [c['name'] for c in public['cities']] == observed['cities']
                assert [p['number'] for p in public['powerPlants']] == [p['number'] for p in observed['plants']]
        root_moves += len(trace)
        learner_moves += len(decisions)
    assert len(analysis['pairs']) == 7 and all(p['first_divergence']['shared_state_verified'] for p in analysis['pairs'])
    OUT.mkdir()
    sources = [p for p in BASE.rglob('*') if p.is_file() and 'runtime' not in p.relative_to(BASE).parts]
    sources += [STRONG / name for name in ['replay-population-auction-regressions-v1.py',
                'analyze-population-auction-replays-v1.py', 'collect-population-auction-replays-v1.py',
                'trace-public-economy.cjs', 'population-hybrid-development-source-v1.json',
                'population-hybrid-development-complete-evidence-v1.json',
                'population-hybrid-development-review-v1.json']]
    for source in sources:
        destination = OUT / source.relative_to(ROOT)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        assert digest(source) == digest(destination)
    summary = {'exact_replays': 14, 'paired_cases': 7, 'root_moves_checked': root_moves,
               'learner_moves_checked': learner_moves, 'all_model_proposals_match': True,
               'all_legal_moves_match': True, 'all_search_seeds_match': True,
               'all_root_trace_chains_match': True, 'all_public_roots_checked': True,
               'shared_first_divergence_roots_verified': 7, 'frozen_runtime_files': 1463,
               'selection_sha256': digest(BASE / 'selection.json'),
               'assessment_sha256': digest(BASE / 'assessment.json'),
               'analysis_sha256': digest(BASE / 'analysis.json'),
               'collector_sha256': digest(__file__), 'limits': analysis['limitations'],
               'new_hf_jobs': 0, 'new_strength_games': 0, 'gradients': False,
               'qualification_eligible': False, 'reserved_final_seeds_used': False}
    write(OUT / 'assessment.json', summary)
    write(OUT / 'manifest.json', {str(p.relative_to(OUT)): digest(p) for p in sorted(OUT.rglob('*')) if p.is_file()})
    descriptor = {**summary, **upload_evidence(OUT)}
    write(DESCRIPTOR, descriptor)
    print(json.dumps(descriptor, indent=2))


if __name__ == '__main__':
    collect()
