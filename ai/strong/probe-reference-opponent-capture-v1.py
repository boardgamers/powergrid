"""Exact twin-game capture probe; no training, HF jobs or opponent replacement."""
import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import tarfile
import time

from strategic_collection import ROOT, read, write, digest
from hybrid_search import Model, Node
from population_hybrid_policy import PopulationPolicy

STRONG = ROOT / 'ai/strong'
RUNTIME = ROOT / 'ai/runs/population-auction-regression-replays-v1/runtime'
SOURCE = STRONG / 'population-hybrid-development-source-v1.json'
MODEL = ROOT / 'ai/runs/policy-iteration-trained-8840u-prepared-v2/local-package-frozen-1/policy.onnx'
OUT = ROOT / 'ai/runs/reference-opponent-capture-probe-v1'
FILES = [Path(__file__), STRONG / 'capture-reference-opponent-v1.cjs',
         STRONG / 'verify-reference-opponent-capture-v1.cjs', STRONG / 'test-reference-opponent-capture-v1.cjs']


def source_files():
    source = read(SOURCE)
    archive = ROOT / 'ai/runs' / source['archive']
    assert digest(archive) == source['sha256']
    import hashlib
    with tarfile.open(archive) as bundle:
        members = bundle.getmembers()
        assert all(m.isfile() and not Path(m.name).is_absolute() and '..' not in Path(m.name).parts for m in members)
        files = {m.name: hashlib.sha256(bundle.extractfile(m).read()).hexdigest() for m in members}
        assert len(files) == len(members) == 1463
    assert {str(p.relative_to(RUNTIME)) for p in RUNTIME.rglob('*') if p.is_file()} == set(files)
    assert all(digest(RUNTIME / name) == sha for name, sha in files.items())
    return files


def one_game(n, rule):
    episode = 4 * (n - 1) + rule  # Last focal seat, all four rules at each count.
    folder = OUT / f'{n}p-{rule}'
    folder.mkdir(exist_ok=False)
    capture = folder / 'opponent-decisions.jsonl'
    plain = Node(str(RUNTIME / 'ai/strong/public-arena-bridge.cjs'))
    old_env = {key: os.environ.get(key) for key in ('PG_OPPONENT_CAPTURE_RUNTIME', 'PG_OPPONENT_CAPTURE_OUTPUT')}
    try:
        os.environ['PG_OPPONENT_CAPTURE_RUNTIME'] = str(RUNTIME)
        os.environ['PG_OPPONENT_CAPTURE_OUTPUT'] = str(capture)
        recorded = Node(str(STRONG / 'capture-reference-opponent-v1.cjs'))
    finally:
        for key, value in old_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
    model = Model(MODEL)
    policy = PopulationPolicy(model, RUNTIME / 'ai/strong/population-hybrid-policy.cjs', arm='filter')
    started = time.perf_counter()
    decisions, steps = 0, 0
    import hashlib
    transcript = hashlib.sha256()
    try:
        reset = {'op':'reset', 'n':1, 'offset':episode, 'playerCount':n, 'mode':'search_geo',
                 'arenaSeed':f'opponent-surrogate-capture-runtime-v1-{n}p',
                 'featureRevisions':{'learner':'4.3-strategic-correction'}}
        left, right = plain.call(reset), recorded.call(reset)
        while True:
            assert left == right, 'Capture changed a public observation, receipt, or terminal'
            transcript.update(json.dumps(left, sort_keys=True).encode())
            if left['ended']:
                assert len(left['ended']) == 1 and left['observations'] == [None]
                terminal = left['ended'][0]
                assert not terminal['truncated']
                assert terminal['playerCount'] == n and terminal['episode'] == episode
                assert terminal['searchStats']['search_geo']['truncated'] == 0
                break
            row = left['observations'][0]
            assert row is not None and row['request']['player'] == n - 1
            decision = policy.choose(row['request'])
            assert decision['modelProposal'] == model.predict(row['state'], row['actions'])[0]
            query = {'op':'step', 'actions':[decision['index']]}
            transcript.update(json.dumps(query, sort_keys=True).encode())
            left, right = plain.call(query), recorded.call(query)
            decisions += 1
            steps += 1
            assert steps <= 1600
        write(folder / 'terminal.json', terminal)
    finally:
        policy.close()
        plain.close()
        recorded.close()
    # All captured records are checked; first/last calls of each strategic kind
    # are also recomputed from public state with the original teacher and seed.
    with (folder / 'replay.log').open('x') as log:
        subprocess.run(['node', str(STRONG / 'verify-reference-opponent-capture-v1.cjs'),
                        str(RUNTIME), str(capture), str(folder / 'verification.json')],
                       stdout=log, stderr=subprocess.STDOUT, check=True, cwd=ROOT)
    verification = read(folder / 'verification.json')
    assert verification['totals'] == terminal['searchStats']['search_geo']
    result = {'players':n, 'episode':episode, 'rule':rule, 'learner_decisions':decisions,
              'teacher_rows':verification['rows'], 'public_replays':len(verification['public_replays']),
              'teacher_rollouts':verification['totals']['evaluations'], 'caps':0,
              'exact_twin_trajectory_sha256':transcript.hexdigest(),
              'capture_sha256':digest(capture), 'terminal_sha256':digest(folder / 'terminal.json'),
              'verification_sha256':digest(folder / 'verification.json'),
              'seconds':time.perf_counter()-started, 'training_eligible':False, 'qualification_eligible':False}
    write(folder / 'verified.json', result)
    return result


def main(workers):
    assert type(workers) is int and 1 <= workers <= 8
    assert digest(MODEL) == '55331f43379e8fe89025d93b1a7a48c88e0ea39b4ebd3a7ef8240d4b62753530'
    hashes = source_files()
    source_hashes = {str(p.relative_to(ROOT)):digest(p) for p in FILES}
    OUT.mkdir(exist_ok=False)
    state = {'created_at':datetime.now(timezone.utc).isoformat(), 'pid':os.getpid(),
             'source':read(SOURCE), 'runtime_file_hashes':hashes, 'probe_code_hashes':source_hashes,
             'model_sha256':digest(MODEL), 'workers':workers, 'cases':{}, 'errors':[],
             'stage':'starting', 'new_games':20, 'paired_runs':40,
             'training_eligible':False, 'gradients':False, 'new_hf_jobs':0,
             'qualification_eligible':False, 'reserved_final_seeds_used':False,
             'purpose':'Engineering capture parity only, excluded from strength and future training. All 2–6 counts/four rules at the last focal seat. Other seats are covered by canonical input checks, not by these twin games.'}
    write(OUT / 'intent.json', state)
    started = time.perf_counter()
    try:
        with (OUT / 'canonical.log').open('x') as log:
            subprocess.run(['node', str(STRONG / 'test-reference-opponent-capture-v1.cjs'), str(RUNTIME)],
                           stdout=log, stderr=subprocess.STDOUT, check=True, cwd=ROOT)
        with ProcessPoolExecutor(max_workers=workers) as pool:
            futures = {pool.submit(one_game, n, rule):(n,rule) for n in range(2,7) for rule in range(4)}
            for future in as_completed(futures):
                n, rule = futures[future]
                try:
                    state['cases'][f'{n}p-{rule}'] = future.result()
                except Exception as error:
                    state['errors'].append({'players':n, 'rule':rule, 'error':type(error).__name__+': '+str(error)})
                state.update(stage='running', updated_at=datetime.now(timezone.utc).isoformat())
                write(OUT / 'status.json', state)
                print({'complete_cases':len(state['cases']), 'errors':state['errors'], 'seconds':time.perf_counter()-started}, flush=True)
        assert not state['errors'] and len(state['cases']) == 20
        assert source_files() == hashes
        assert all(digest(ROOT / name) == sha for name,sha in source_hashes.items())
        state.update(stage='complete', exact_twin_games=20,
                     teacher_rows=sum(r['teacher_rows'] for r in state['cases'].values()),
                     public_replays=sum(r['public_replays'] for r in state['cases'].values()))
    except BaseException as error:
        state.update(stage='stopped_with_error', error=type(error).__name__+': '+str(error))
        raise
    finally:
        state.update(seconds=time.perf_counter()-started, updated_at=datetime.now(timezone.utc).isoformat())
        write(OUT / 'status.json', state)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--workers', type=int, default=8)
    main(parser.parse_args().workers)
