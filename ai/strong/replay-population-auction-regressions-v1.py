"""Replay fixed adverse/improved pairs from the complete screen, never new games."""
import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
import gzip
import json
import os
from pathlib import Path
import shutil
import sys
import tarfile
import time

from strategic_collection import ROOT, read, write, digest
from hybrid_search import Model, Node, public_seed

STRONG = ROOT / 'ai/strong'
OUTPUT = ROOT / 'ai/runs/population-auction-regression-replays-v1'
SOURCE = STRONG / 'population-hybrid-development-source-v1.json'
COMPARISON = STRONG / 'population-hybrid-development-comparison-v1.json'
ARCHIVE = STRONG / 'population-hybrid-development-complete-evidence-v1.json'
COLLECTED = ROOT / 'ai/runs/population-hybrid-development-collected-v1'
MODEL = ROOT / 'ai/runs/policy-iteration-trained-8840u-prepared-v2/local-package-frozen-1/policy.onnx'
OBSERVER = STRONG / 'trace-public-economy.cjs'
SPEC = [
    (4, 'search_geo', 'original', False, 'worse'),
    (5, 'search_geo', 'recharged', False, 'worse'),
    (3, 'heuristic', None, None, 'worse'),
    (4, 'search_geo', 'recharged', True, 'better'),
    (4, 'search_geo', 'original', True, 'better'),
    (2, 'search_geo', 'recharged', True, 'better'),
    (6, 'search_geo', 'recharged', True, 'better'),
]


def prepare():
    assert not OUTPUT.exists(), 'Inspect an existing replay outcome; never restart automatically'
    comparison, archive, source = read(COMPARISON), read(ARCHIVE), read(SOURCE)
    assert comparison['complete'] and archive['remote_archive_verified']
    assert archive['comparison_sha256'] == digest(COMPARISON)
    assert comparison['source'] == source and comparison['games'] == 8400
    plan = read(STRONG / 'population-hybrid-development-plan-v1.json')
    assert all(digest(ROOT / file) == sha for file, sha in plan['dependency_hashes'].items())
    protocol = read(STRONG / 'population-hybrid-development-protocol-v1.json')
    assert digest(MODEL) == protocol['model_pin']['files']['inference64.onnx']
    requests, pairs = {}, []
    for n, opponent, variant, sealed, direction in SPEC:
        reports = {}
        provenance = {}
        for arm in ['filter', 'auction']:
            case = f'population-hybrid-development-v1-{arm}-{n}p-{opponent}-0-4'
            base = COLLECTED / case
            proof = comparison['provenance'][case]
            assert digest(base / 'verified.json') == proof['verified_sha256']
            receipt = read(base / 'verified.json')
            assert receipt['evidence'] == proof['evidence']
            evaluation = base / 'artifacts/evaluation/evaluation.json'
            assert digest(evaluation) == receipt['summary']['report_sha256']
            report = read(evaluation)
            assert report['all_complete'] and report['errors'] == []
            assert report['game_caps'] == report['rollout_caps'] == 0
            reports[arm] = {r['episode']: r for r in report['results']}
            provenance[arm] = {'case': case, 'report_sha256': digest(evaluation), **proof}
        eligible = []
        for episode, result in reports['filter'].items():
            terminal = result['terminal']
            if variant is not None and (terminal['variant'] != variant or terminal['sealed'] != sealed):
                continue
            difference = reports['auction'][episode]['terminal']['win'] - terminal['win']
            if (difference < 0) if direction == 'worse' else (difference > 0):
                eligible.append(episode)
        assert eligible
        episode = min(eligible)
        label = f'{n}p-{opponent}-{variant or "all"}-{sealed}-{direction}-{episode}'
        labels = []
        for arm in ['filter', 'auction']:
            key = label + '-' + arm
            reference = reports[arm][episode]
            path = COLLECTED / provenance[arm]['case'] / 'artifacts/evaluation' / f'decisions-{episode}.jsonl'
            assert digest(path) == reference['decision_receipt_sha256']
            requests[key] = {'players': n, 'opponent': opponent, 'arm': arm, 'episode': episode,
                             'reference': reference, 'receipt': str(path.relative_to(ROOT)),
                             'provenance': provenance[arm]}
            labels.append(key)
        pairs.append({'label': label, 'selection': 'Lowest episode satisfying the fixed outcome direction.',
                      'eligible_episodes': sorted(eligible), 'selected_episode': episode,
                      'direction': direction, 'cases': labels})
    assert len(requests) == 14 and len(pairs) == 7
    bundle = ROOT / 'ai/runs' / source['archive']
    assert digest(bundle) == source['sha256']
    OUTPUT.mkdir()
    runtime = OUTPUT / 'runtime'
    runtime.mkdir()
    with tarfile.open(bundle) as archive_file:
        members = archive_file.getmembers()
        assert len(members) == 1463 and all(m.isfile() for m in members)
        assert all(not Path(m.name).is_absolute() and '..' not in Path(m.name).parts for m in members)
        archive_file.extractall(runtime, filter='data')
    hashes = {str(p.relative_to(runtime)): digest(p) for p in runtime.rglob('*') if p.is_file()}
    assert len(hashes) == 1463
    assert all(hashes[file] == sha for file, sha in source['overlays'].items())
    for key, request in requests.items():
        folder = OUTPUT / key
        folder.mkdir()
        shutil.copy2(ROOT / request['receipt'], folder / 'decisions.jsonl')
        assert digest(folder / 'decisions.jsonl') == request['reference']['decision_receipt_sha256']
    selection = {'source': source, 'comparison_sha256': digest(COMPARISON), 'archive': read(ARCHIVE),
                 'model_sha256': digest(MODEL), 'model_path': str(MODEL),
                 'feature_revision': protocol['model_pin']['feature_revision'],
                 'requested': requests, 'pairs': pairs, 'runtime_hashes': hashes,
                 'observer_sha256': digest(OBSERVER), 'runner_sha256': digest(__file__),
                 'scope': 'Outcome-selected diagnostic replays. No fresh strength results or causal interventions.',
                 'new_hf_jobs': 0, 'gradients': False, 'qualification_eligible': False,
                 'reserved_final_seeds_used': False}
    write(OUTPUT / 'selection.json', selection)
    print(json.dumps({'prepared': True, 'replays': 14, 'selection_sha256': digest(OUTPUT / 'selection.json'),
                      'runtime_files': len(hashes), 'pairs': pairs}), flush=True)


def worker(key):
    selection = read(OUTPUT / 'selection.json')
    assert digest(__file__) == selection['runner_sha256'] and digest(OBSERVER) == selection['observer_sha256']
    assert digest(MODEL) == selection['model_sha256']
    runtime, folder = OUTPUT / 'runtime', OUTPUT / key
    assert all(digest(runtime / name) == sha for name, sha in selection['runtime_hashes'].items())
    entry = selection['requested'][key]
    reference = entry['reference']
    expected = reference['terminal']
    assert digest(folder / 'decisions.jsonl') == reference['decision_receipt_sha256']
    decisions = [json.loads(line) for line in (folder / 'decisions.jsonl').read_text().splitlines()]
    assert len(decisions) == reference['decisions']
    assert not os.environ.get('NODE_OPTIONS') and not os.environ.get('PG_TRACE_PATH')
    trace = folder / 'economy.jsonl'
    trace.touch(exist_ok=False)
    model = Model(MODEL, threads=1)
    prepare_node = Node(str(runtime / 'ai/strong/population-hybrid-policy.cjs'))
    os.environ.update(NODE_OPTIONS='--require ' + str(OBSERVER), PG_TRACE_PATH=str(trace),
                      PG_DIAGNOSTIC_RUNTIME=str(runtime))
    try:
        bridge = Node(str(runtime / 'ai/strong/public-arena-bridge.cjs'))
    finally:
        for name in ['NODE_OPTIONS', 'PG_TRACE_PATH', 'PG_DIAGNOSTIC_RUNTIME']:
            os.environ.pop(name)
    write(folder / 'process.json', {'pid': os.getpid(), 'node_pid': bridge.proc.pid,
                                  'prepare_pid': prepare_node.proc.pid, 'started_at_unix': time.time()})
    started = time.perf_counter()
    result = {'case': key, 'completed': False, 'exact_terminal_replay': False,
              'selection_sha256': digest(OUTPUT / 'selection.json')}
    roots = folder / 'public-roots.jsonl.gz'
    try:
        seed = expected['gameSeed'].rsplit('-', 1)[0]
        assert seed == f"population-hybrid-development-v1-{entry['players']}p"
        response = bridge.call({'op': 'reset', 'n': 1, 'offset': entry['episode'],
                                'arenaSeed': seed, 'playerCount': entry['players'],
                                'mode': entry['opponent'],
                                'featureRevisions': {'learner': selection['feature_revision']}})
        assert response['ended'] == []
        with gzip.open(roots, 'xt') as saved:
            for number, decision in enumerate(decisions, 1):
                row = response['observations'][0]
                assert row is not None and row['roles'][row['seat']] == 'learner'
                assert decision['decision'] == number and decision['round'] == row['round']
                q = row['request']
                assert q['player'] == expected['seat']
                assert q['state']['seed'] == 'secret' and q['state']['powerPlantsDeck'] == []
                assert not q['state'].get('hiddenLog') and 'powerPlantDeckAfterStep3' not in q['state']
                if q['state']['options']['fastBid']:
                    assert all(p['bid'] == 0 for p in q['state']['players'])
                prepared = prepare_node.call({**q, 'featureRevision': selection['feature_revision'], 'op': 'prepare'})
                assert prepared['observation']['state'] == row['state']
                assert prepared['observation']['actions'] == row['actions']
                assert prepared['moves'][decision['index']] == decision['move']
                proposal = model.predict(row['state'], row['actions'])[0]
                assert proposal == decision['modelProposal']
                if decision['search']:
                    assert public_seed(prepared) == decision['search']['seed']
                saved.write(json.dumps({'decision': number, 'request': q, 'moves': prepared['moves'],
                                        'modelProposal': proposal}, allow_nan=False) + '\n')
                response = bridge.call({'op': 'step', 'actions': [decision['index']]})
                if number % 25 == 0:
                    write(folder / 'progress.json', {'case': key, 'decision': number,
                                                     'round': row['round'], 'seconds': time.perf_counter()-started})
                assert bool(response['ended']) == (number == len(decisions))
        assert response['observations'] == [None] and len(response['ended']) == 1
        actual = response['ended'][0]
        fields = [name for name in expected if name not in ['seat', 'win']]
        differences = [name for name in fields if actual[name] != expected[name]]
        assert not differences, differences
        moves_logged = sum(1 for _ in trace.open())
        assert moves_logged == expected['steps'], 'Missing root moves or observed simulation moves'
        result.update(completed=True, exact_terminal_replay=True, differences=differences,
                      actual=actual, learner_decisions=len(decisions), moves_logged=moves_logged,
                      trace_sha256=digest(trace), public_roots_sha256=digest(roots),
                      all_public_roots_checked=True, all_model_proposals_match=True,
                      all_search_seeds_match=True, all_legal_moves_match=True)
    except BaseException as error:
        result['error'] = type(error).__name__ + ': ' + str(error)
        raise
    finally:
        bridge.close()
        prepare_node.close()
        result['seconds'] = time.perf_counter() - started
        write(folder / 'result.json', result)
    return result


def run():
    selection = read(OUTPUT / 'selection.json')
    assert digest(__file__) == selection['runner_sha256']
    intent = OUTPUT / 'run-intent.json'
    with intent.open('x') as stream:
        json.dump({'pid': os.getpid(), 'started_at_unix': time.time(), 'automatic_retries': False}, stream)
    results, errors = {}, {}
    with ProcessPoolExecutor(max_workers=4) as pool:
        futures = {pool.submit(worker, key): key for key in selection['requested']}
        for future in as_completed(futures):
            key = futures[future]
            try:
                results[key] = future.result()
                print(json.dumps({'completed': len(results), 'case': key,
                                  'seconds': round(results[key]['seconds'], 2)}), flush=True)
            except Exception as error:
                errors[key] = type(error).__name__ + ': ' + str(error)
                print(json.dumps({'failed': key, 'error': errors[key]}), flush=True)
            write(OUTPUT / 'status.json', {'completed': len(results), 'errors': errors,
                                           'expected': 14, 'updated_at_unix': time.time()})
    assert not errors, errors
    assert len(results) == 14 and all(r['completed'] and r['exact_terminal_replay'] for r in results.values())
    assert all(digest(OUTPUT / 'runtime' / name) == sha for name, sha in selection['runtime_hashes'].items())
    write(OUTPUT / 'assessment.json', {'replays': 14, 'pairs': 7, 'results': results,
                                      'selection_sha256': digest(OUTPUT / 'selection.json'),
                                      'all_terminal_replays_match': True, 'all_runtime_hashes_match': True,
                                      'new_strength_games': 0, 'new_hf_jobs': 0, 'gradients': False,
                                      'qualification_eligible': False, 'reserved_final_seeds_used': False})


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('stage', choices=['prepare', 'run'])
    globals()[parser.parse_args().stage]()
