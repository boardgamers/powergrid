"""Isolate one fixed search-selected action, followed by the filtered model."""
import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
import gzip
import json
import os
from pathlib import Path
import shutil
import time

from strategic_collection import ROOT, read, write, digest
from hybrid_search import Model, Node
from population_hybrid_policy import PopulationPolicy
from policy_iteration_evidence_archive import upload_evidence

STRONG = ROOT / 'ai/strong'
REPLAY = ROOT / 'ai/runs/population-auction-regression-replays-v1'
OUT = ROOT / 'ai/runs/auction-first-action-counterfactual-v1'
EVIDENCE = ROOT / 'ai/runs/auction-first-action-counterfactual-evidence-v1'
DESCRIPTOR = STRONG / 'auction-first-action-counterfactual-evidence-v1.json'
OBSERVER = STRONG / 'trace-public-economy.cjs'


def validate_runtime(protocol):
    assert protocol['runner_sha256'] == digest(__file__)
    assert protocol['observer_sha256'] == digest(OBSERVER)
    assert digest(protocol['model_path']) == protocol['model_sha256']
    assert all(digest(Path(protocol['runtime']) / file) == sha for file, sha in protocol['runtime_hashes'].items())
    assert all(digest(ROOT / file) == sha for file, sha in protocol['python_dependencies'].items())


def prepare():
    assert not OUT.exists()
    evidence = read(STRONG / 'population-auction-regression-replays-evidence-v1.json')
    assert evidence['remote_archive_verified'] and evidence['exact_replays'] == 14
    assert evidence['analysis_sha256'] == digest(REPLAY / 'analysis.json')
    analysis, selection = read(REPLAY / 'analysis.json'), read(REPLAY / 'selection.json')
    holdout = read(ROOT / 'ai/runs/auction-world-generalization-v1/protocol.json')
    cases = []
    for pair in analysis['pairs']:
        first = pair['first_divergence']
        reference = selection['requested'][pair['cases'][0]]
        assert first['shared_state_verified'] and reference['arm'] == 'filter'
        assert first['filter'] != first['auction']
        cases.append({'label': pair['label'], 'direction': pair['direction'],
                      'first': first, 'reference': reference,
                      'reference_folder': str(REPLAY / pair['cases'][0])})
    assert len(cases) == 7
    protocol = {'purpose': 'Change exactly the first differing learner action, then use the original filtered model. Isolate its effect on the fixed known deal, not fresh strength.',
                'selection': 'All seven first-divergence pairs from the existing outcome-selected replay set; no further selection by holdout-world results.',
                'cases': cases, 'branches': ['control', 'one_action'],
                'source': selection['source'], 'replay_evidence': evidence,
                'holdout_evidence': read(STRONG / 'auction-world-generalization-evidence-v1.json'),
                'runtime': str(REPLAY / 'runtime'), 'runtime_hashes': selection['runtime_hashes'],
                'model_path': selection['model_path'], 'model_sha256': selection['model_sha256'],
                'feature_revision': selection['feature_revision'],
                'python_dependencies': holdout['python_dependencies'],
                'runner_sha256': digest(__file__), 'observer_sha256': digest(OBSERVER),
                'execution': 'Original seed/rules/seat and frozen actual arena opponents. Reconstruct from setup; no hidden engine fields passed to the policy. Four concurrent CPU processes, no gradients.',
                'checks': 'All control decisions/public roots and full terminal reports must reproduce the original filtered model. Branches match through the first public root, inject exactly its saved auction move once, and use the filtered model thereafter. All legal/public/root trace checks and zero caps required.',
                'limits': 'Known-deal counterfactuals on outcome-selected examples. Opponent responses can change after the intervention. The treatment is one action plus filtered-model continuation; it is not the full auction-search policy.',
                'automatic_retries': False, 'new_hf_jobs': 0, 'new_strength_games': 0,
                'qualification_eligible': False, 'reserved_final_seeds_used': False}
    validate_runtime(protocol)
    OUT.mkdir()
    for case in cases:
        folder = OUT / case['label']
        folder.mkdir()
        source = Path(case['reference_folder'])
        for name in ['decisions.jsonl', 'public-roots.jsonl.gz']:
            shutil.copy2(source / name, folder / ('reference-' + name))
            assert digest(source / name) == digest(folder / ('reference-' + name))
        for branch in protocol['branches']:
            (folder / branch).mkdir()
    write(OUT / 'protocol.json', protocol)
    print(json.dumps({'prepared': True, 'pairs': 7, 'games': 14,
                      'protocol_sha256': digest(OUT / 'protocol.json')}), flush=True)


def worker(label, branch):
    protocol = read(OUT / 'protocol.json')
    validate_runtime(protocol)
    case = next(c for c in protocol['cases'] if c['label'] == label)
    folder = OUT / label / branch
    entry, first = case['reference'], case['first']
    expected = entry['reference']['terminal']
    old_decisions = [json.loads(line) for line in (folder.parent / 'reference-decisions.jsonl').read_text().splitlines()]
    with gzip.open(folder.parent / 'reference-public-roots.jsonl.gz', 'rt') as handle:
        old_roots = [json.loads(line) for line in handle]
    assert digest(folder.parent / 'reference-decisions.jsonl') == entry['reference']['decision_receipt_sha256']
    assert len(old_roots) == len(old_decisions) == entry['reference']['decisions']
    runtime = Path(protocol['runtime'])
    model = Model(protocol['model_path'], threads=1)
    policy = PopulationPolicy(model, runtime / 'ai/strong/population-hybrid-policy.cjs',
                              arm='filter', samples=8, workers=1, max_steps=2400)
    assert not os.environ.get('NODE_OPTIONS') and not os.environ.get('PG_TRACE_PATH')
    trace = folder / 'economy.jsonl'
    trace.touch(exist_ok=False)
    os.environ.update(NODE_OPTIONS='--require ' + str(OBSERVER), PG_TRACE_PATH=str(trace),
                      PG_DIAGNOSTIC_RUNTIME=str(runtime))
    try:
        bridge = Node(str(runtime / 'ai/strong/public-arena-bridge.cjs'))
    finally:
        for name in ['NODE_OPTIONS', 'PG_TRACE_PATH', 'PG_DIAGNOSTIC_RUNTIME']:
            os.environ.pop(name)
    write(folder / 'process.json', {'pid': os.getpid(), 'node_pid': bridge.proc.pid,
                                  'policy_pid': policy.node.proc.pid, 'started_at_unix': time.time()})
    started, count, changed = time.perf_counter(), 0, 0
    result = {'label': label, 'branch': branch, 'completed': False,
              'protocol_sha256': digest(OUT / 'protocol.json')}
    try:
        seed = expected['gameSeed'].rsplit('-', 1)[0]
        assert seed == f"population-hybrid-development-v1-{entry['players']}p"
        response = bridge.call({'op': 'reset', 'n': 1, 'offset': entry['episode'], 'arenaSeed': seed,
                                'playerCount': entry['players'], 'mode': entry['opponent'],
                                'featureRevisions': {'learner': protocol['feature_revision']}})
        assert not response['ended']
        with (folder / 'decisions.jsonl').open('x') as receipts, gzip.open(folder / 'public-roots.jsonl.gz', 'xt') as saved:
            while response['observations'][0] is not None:
                row = response['observations'][0]
                assert row['roles'][row['seat']] == 'learner'
                count += 1
                q = row['request']
                assert q['player'] == expected['seat']
                state = q['state']
                assert state['seed'] == 'secret' and state['powerPlantsDeck'] == []
                assert not state.get('hiddenLog') and 'powerPlantDeckAfterStep3' not in state
                if state['options']['fastBid']:
                    assert all(p['bid'] == 0 for p in state['players'])
                decision = policy.choose(q)
                assert decision['search'] is None and decision['modelProposal'] == model.predict(row['state'], row['actions'])[0]
                if branch == 'control' or count <= first['decision']:
                    reference = old_decisions[count-1]
                    assert old_roots[count-1]['request'] == q
                    assert decision['index'] == reference['index'] and decision['move'] == reference['move']
                    assert decision['modelProposal'] == reference['modelProposal'] and row['round'] == reference['round']
                intervention = count == first['decision'] and branch == 'one_action'
                if count == first['decision']:
                    assert q == first['public_root']['request']
                    assert decision['move'] == first['filter']
                    assert decision['index'] == first['public_root']['modelProposal']
                if intervention:
                    move = first['auction']
                    index = first['public_root']['moves'].index(move)
                    assert index != decision['index']
                    changed += 1
                else:
                    index, move = decision['index'], decision['move']
                receipts.write(json.dumps({'decision': count, 'round': row['round'], 'filtered_policy': decision,
                                           'intervention': intervention, 'executed_index': index, 'executed_move': move})+'\n')
                saved.write(json.dumps({'decision': count, 'request': q})+'\n')
                response = bridge.call({'op': 'step', 'actions': [index]})
                if count % 25 == 0:
                    write(folder / 'progress.json', {'decision': count, 'round': row['round'],
                                                     'seconds': time.perf_counter()-started})
        assert response['observations'] == [None] and len(response['ended']) == 1
        terminal = response['ended'][0]
        assert not terminal['truncated'] and all(s['truncated'] == 0 for s in terminal['searchStats'].values())
        assert count >= first['decision'] and changed == (1 if branch == 'one_action' else 0)
        if branch == 'control':
            assert count == len(old_decisions)
            assert all(terminal[name] == value for name, value in expected.items() if name not in ['seat', 'win'])
        trace_rows = [json.loads(line) for line in trace.read_text().splitlines()]
        assert len(trace_rows) == terminal['steps']
        assert all(left['after'] == right['before'] for left, right in zip(trace_rows, trace_rows[1:]))
        focal = [r for r in trace_rows if r['seat'] == expected['seat']]
        receipts = [json.loads(line) for line in (folder / 'decisions.jsonl').read_text().splitlines()]
        assert len(focal) == len(receipts) == count
        assert all(move['action'] == receipt['executed_move'] for move, receipt in zip(focal, receipts))
        result.update(completed=True, terminal=terminal, win=terminal['value'][expected['seat']],
                      learner_decisions=count, interventions=changed, all_public_roots_checked=True,
                      original_prefix_matched=True, control_exact=branch == 'control',
                      root_moves_checked=len(trace_rows), final_economy=trace_rows[-1]['after']['players'][expected['seat']],
                      artifacts={name: digest(folder / name) for name in ['economy.jsonl', 'decisions.jsonl', 'public-roots.jsonl.gz']})
    except BaseException as error:
        result['error'] = type(error).__name__ + ': ' + str(error)
        raise
    finally:
        bridge.close()
        policy.close()
        result['seconds'] = time.perf_counter()-started
        write(folder / 'result.json', result)
    return result


def run():
    protocol = read(OUT / 'protocol.json')
    validate_runtime(protocol)
    with (OUT / 'run-intent.json').open('x') as handle:
        json.dump({'pid': os.getpid(), 'started_at_unix': time.time(), 'automatic_retries': False}, handle)
    results, errors = {}, {}
    with ProcessPoolExecutor(max_workers=4) as pool:
        futures = {pool.submit(worker, c['label'], b): c['label']+'/'+b for c in protocol['cases'] for b in protocol['branches']}
        for future in as_completed(futures):
            key = futures[future]
            try:
                results[key] = future.result()
                print(json.dumps({'completed': len(results), 'case': key,
                                  'seconds': round(results[key]['seconds'], 2)}), flush=True)
            except Exception as error:
                errors[key] = type(error).__name__+': '+str(error)
                print(json.dumps({'failed': key, 'error': errors[key]}), flush=True)
            write(OUT / 'status.json', {'completed': len(results), 'expected': 14, 'errors': errors})
    assert not errors and len(results) == 14, errors
    pairs = []
    for c in protocol['cases']:
        control, branch = (results[c['label']+'/'+b] for b in protocol['branches'])
        assert control['control_exact'] and control['interventions'] == 0 and branch['interventions'] == 1
        pairs.append({'label': c['label'], 'full_hybrid_direction': c['direction'],
                      'control_win': control['win'], 'one_action_win': branch['win'],
                      'difference': branch['win']-control['win'],
                      'control_final': control['terminal']['final'], 'one_action_final': branch['terminal']['final']})
    validate_runtime(protocol)
    write(OUT / 'assessment.json', {'all_complete': True, 'protocol_sha256': digest(OUT / 'protocol.json'),
                                  'pairs': pairs, 'results': results, 'exact_controls': 7,
                                  'single_action_branches': 7, 'new_strength_games': 0,
                                  'new_hf_jobs': 0, 'gradients': False, 'qualification_eligible': False,
                                  'reserved_final_seeds_used': False})


def archive():
    assert not EVIDENCE.exists() and not EVIDENCE.with_suffix('.tgz').exists() and not DESCRIPTOR.exists()
    protocol, assessment = read(OUT / 'protocol.json'), read(OUT / 'assessment.json')
    validate_runtime(protocol)
    assert assessment['all_complete'] and assessment['protocol_sha256'] == digest(OUT / 'protocol.json')
    for key, result in assessment['results'].items():
        folder = OUT / key
        assert result == read(folder / 'result.json') and result['completed']
        assert all(digest(folder / name) == sha for name, sha in result['artifacts'].items())
        receipts = [json.loads(line) for line in (folder / 'decisions.jsonl').read_text().splitlines()]
        case = next(c for c in protocol['cases'] if c['label'] == result['label'])
        changed = [r for r in receipts if r['intervention']]
        assert len(changed) == result['interventions'] == (0 if result['branch'] == 'control' else 1)
        assert all(r['executed_move'] == r['filtered_policy']['move'] and r['executed_index'] == r['filtered_policy']['index']
                   for r in receipts if not r['intervention'])
        if changed:
            assert changed[0]['decision'] == case['first']['decision']
            assert changed[0]['executed_move'] == case['first']['auction']
            assert changed[0]['filtered_policy']['move'] == case['first']['filter']
        assert all(r['filtered_policy']['arm'] == 'filter' and r['filtered_policy']['search'] is None for r in receipts)
    EVIDENCE.mkdir()
    sources = [p for p in OUT.rglob('*') if p.is_file()]
    sources += [Path(__file__), OBSERVER, STRONG / 'population-auction-regression-replays-evidence-v1.json']
    for source in sources:
        target = EVIDENCE / source.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        assert digest(source) == digest(target)
    write(EVIDENCE / 'manifest.json', {str(p.relative_to(EVIDENCE)): digest(p) for p in sorted(EVIDENCE.rglob('*')) if p.is_file()})
    summary = {k: v for k, v in assessment.items() if k != 'results'}
    summary.update(learner_decisions=sum(r['learner_decisions'] for r in assessment['results'].values()),
                   root_moves_checked=sum(r['root_moves_checked'] for r in assessment['results'].values()),
                   runner_sha256=digest(__file__), scope=protocol['purpose'], limitations=protocol['limits'])
    write(DESCRIPTOR, {**summary, **upload_evidence(EVIDENCE)})
    print(json.dumps(read(DESCRIPTOR), indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('stage', choices=['prepare', 'run', 'archive'])
    globals()[parser.parse_args().stage]()
