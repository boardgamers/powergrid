"""Fixed-action opponent-model diagnostic. No training, selection or job submission."""
import argparse
from copy import deepcopy
import json
import os
from pathlib import Path
import threading
import time

from strategic_collection import ROOT, read, write, digest
from hybrid_search import Model, Node, EnginePool, predict_batch, public_seed, model_revision

STRONG = ROOT / 'ai/strong'
OLD = ROOT / 'ai/runs/auction-world-generalization-v1'
OUT = ROOT / 'ai/runs/reference-opponent-diagnostic-v2'
WORKER = STRONG / 'reference-opponent-continuations-v2.cjs'
TEST = STRONG / 'test-reference-opponent-continuations-v2.cjs'


def validate(p):
    assert p['runner_sha256'] == digest(__file__)
    assert p['worker_sha256'] == digest(WORKER) and p['test_sha256'] == digest(TEST)
    assert digest(p['model_path']) == p['model_sha256']
    assert all(digest(Path(p['runtime']) / f) == h for f, h in p['runtime_hashes'].items())
    assert all(digest(ROOT / f) == h for f, h in p['python_dependencies'].items())
    assert all(digest(OLD / f) == h for f, h in p['mixture_files'].items())
    assert all(digest(ROOT / f) == h for f, h in p['repair_dependencies'].items())
    assert all(digest(ROOT / f) == h for f, h in p['previous_pilot_files'].items())


def prepare():
    assert not OUT.exists()
    old = read(OLD / 'protocol.json')
    assert read(OLD / 'assessment.json')['all_complete']
    roots = []
    for i, root in enumerate(old['roots']):
        decision = root['original_decision']
        roots.append({**root, 'opponent': 'heuristic' if i == 2 else 'search_geo',
                      'options': [decision['modelProposal'], decision['index']]})
    p = {key: old[key] for key in ('runtime', 'runtime_hashes', 'python_dependencies',
                                  'model_path', 'model_sha256')}
    p.update(purpose='Hold the original candidate pair, public roots, sampled decks, focal model and full horizons fixed. Change opponent continuations and their inferred prior sealed bids together.',
             roots=roots, feature_revision='4.3-strategic-correction', samples=64, workers=4,
             max_steps=2400, runner_sha256=digest(__file__), worker_sha256=digest(WORKER),
             test_sha256=digest(TEST), mixture_files={f.name: digest(f) for f in OLD.glob('*.json')},
             controls='All seven roots, both fixed actions and all 64 original worlds must exactly reproduce saved mixture credits, roles and prior beliefs.',
             pilot_roots=[0, 2, 5, 6], pilot_worlds=[0, 1],
             pilot_purpose='Complete 2p/4p/6p search-opponent rollouts plus the 3p heuristic case, for correctness and CPU/RAM/time admission only. Do not interpret their scores as strength.',
             reference_opponents='Frozen public-arena-bridge behavior: search_geo16 strategic moves with six candidates and 2400-step inner horizons; economic nonstrategic moves; heuristic in the 3p case.',
             prior_beliefs='Reconstruct prior eligible public prompts, use the same reference role with seed <public world>:committed-bid:<actor>. This approximates prior actions without knowing the actual private arena RNG or submissions.',
             primary='For each of seven roots, original selected action minus original baseline on the same worlds 8..63; compare with the existing mixture margin. Keep original worlds 0..7 secondary. No new action selection.',
             uncertainty='Exploratory conditional simulation; retain paired world differences. Resample 14 consecutive four-world blocks jointly across policies, 10000 draws with seed 12347. Not fresh game win rates.',
             limitations=['Outcome-selected public roots, not a representative strength sample.',
                          'Known arena opponent identity is diagnostic knowledge, unavailable in deployment.',
                          'Prior bid inference and future opponent continuation change together; effects are not separately identified.',
                          'Search opponents retain their own historical internal rollout assumptions; only the outer opponent behavior changes.'],
             failure='Any outer or nested search cap, parity failure, missing result or invalid score rejects the diagnostic. Never score incomplete rollouts or retry automatically.',
             automatic_retries=False, new_hf_jobs=0, gradients=False, new_strength_games=0,
             qualification_eligible=False, reserved_final_seeds_used=False)
    failure = read(STRONG/'reference-opponent-pilot-failure-evidence-v1.json')
    assert failure['remote_archive_verified'] and failure['status']=='pilot_failed_no_admission'
    p.update(replaces_failed_pilot=failure,
             repair_dependencies={str(path.relative_to(ROOT)):digest(path) for path in [
                 STRONG/'analysis-public-balances-v1.cjs',STRONG/'reference-search-public-balances-v1.cjs']},
             repair_scope='Only the reference opponent nested search uses the isolated sampler; all public roots, outer world sampling, model inference and control continuations retain the frozen source. Known balances skip unused history replay; unknown balances still replay.',
             error_handling='JSONL failures exit nonzero immediately, including with stdin open.',
             previous_completed_pilot_roots=[0,2,5],
             previous_pilot_files={f'ai/runs/reference-opponent-diagnostic-v1/pilot-{i}.json':
                 digest(ROOT/f'ai/runs/reference-opponent-diagnostic-v1/pilot-{i}.json') for i in [0,2,5]},
             previous_pilot_checks='All terminal rows of the three previously completed v1 pilot cases must reproduce exactly under v2. The failed 6p root requires four new complete continuations.')
    validate(p)
    OUT.mkdir()
    write(OUT / 'protocol.json', p)
    print(json.dumps({'prepared': True, 'protocol_sha256': digest(OUT/'protocol.json'),
                      'controls': 896, 'pilot_rollouts': 16}), flush=True)


class MemorySampler:
    """Sample summed resident memory; this is an observed peak, not a hard bound."""
    def __init__(self, pids):
        self.pids = pids
        self.peak = 0
        self.stop = threading.Event()
        self.thread = threading.Thread(target=self.run, daemon=True)

    def run(self):
        while not self.stop.is_set():
            total = 0
            for pid in self.pids:
                try:
                    total += int(Path(f'/proc/{pid}/statm').read_text().split()[1]) * os.sysconf('SC_PAGE_SIZE')
                except FileNotFoundError:
                    pass
            self.peak = max(total, self.peak)
            self.stop.wait(.1)


def verify_rows(p, root_index, mode, begin, count, rows):
    root = p['roots'][root_index]
    options, seat = root['options'], root['request']['player']
    old = read(OLD / f'root-{root_index}-result.json')['search']
    control_path = OUT / f'control-{root_index}.json'
    control_worlds = {} if mode == 'neural_population' else {
        r['sample']: r['diagnostic']['sampledWorldSha256'] for r in read(control_path)['rows']}
    assert len(rows) == count * 2 and [r['env'] for r in rows] == list(range(count * 2))
    worlds, decisions, nested, prior = {}, 0, 0, 0
    for i, row in enumerate(rows):
        sample, action_index = begin+i//2, options[i%2]
        assert row['sample'] == sample and row['actionIndex'] == action_index
        assert not row['truncated'] and 0 <= row['steps'] <= 2400
        assert row['searchStats']['truncated'] == row['diagnostic']['priorSearchStats']['truncated'] == 0
        terminal = row['diagnostic']['terminal']
        assert len(terminal) == len(root['request']['state']['players'])
        scores = [(r['powered'], r['money'], r['cities']) for r in terminal]
        assert all(all(type(v) is int and v >= 0 for v in s) for s in scores)
        top = max(scores)
        expected = (1 / scores.count(top)) if scores[seat] == top else 0
        assert row['value'] == expected
        assert sum(row['policyDecisions'].values()) == row['steps']
        assert type(row['filterOverrides']) is int and row['filterOverrides'] >= 0
        world = {k: row[k] for k in ('roles', 'initialBelief')}
        signature = row['diagnostic']['sampledWorldSha256']
        assert len(signature) == 64
        combined = {**world, 'sampledWorldSha256': signature}
        assert worlds.setdefault(sample, combined) == combined
        if mode == 'neural_population':
            assert row['value'] == old['sampleOutcomes'][str(action_index)][sample]
            assert world == old['worlds'][str(sample)]
            assert row['searchStats'] == row['diagnostic']['priorSearchStats'] == dict(decisions=0, evaluations=0, truncated=0)
        else:
            assert signature == control_worlds[sample]
            assert row['roles'] == ['neural' if i == seat else root['opponent'] for i in range(len(terminal))]
            assert row['initialBelief']['kind'] == 'reference_opponent_v1'
            bids = row['initialBelief']['committed']
            assert [b['actor'] for b in bids] == [b['actor'] for b in old['worlds'][str(sample)]['initialBelief']['committed']]
            assert all(b['role'] == root['opponent'] and b['searchStats']['truncated'] == 0 for b in bids)
            assert row['diagnostic']['priorSearchStats'] == {
                key: sum(b['searchStats'][key] for b in bids) for key in ('decisions','evaluations','truncated')}
            assert row['searchStats']['decisions'] == row['policyDecisions']['search_geo']
        decisions += row['policyDecisions']['neural']
        nested += row['searchStats']['evaluations']
        prior += row['diagnostic']['priorSearchStats']['evaluations']
    return {'complete': True, 'rollouts': len(rows), 'neural_decisions': decisions,
            'outer_steps': sum(r['steps'] for r in rows), 'nested_evaluations': nested,
            'prior_bid_evaluations_per_candidate': prior, 'caps': 0,
            'terminal_scores_verified': True, 'shared_sampled_worlds_verified': True}


def run_root(p, model, root_index, mode, begin, count, output):
    assert not output.exists()
    intent = output.with_suffix('.intent.json')
    with intent.open('x') as f:
        json.dump({'started': time.time(), 'automatic_retries': False}, f)
    root = p['roots'][root_index]
    q = {**root['request'], 'featureRevision': p['feature_revision']}
    node = Node(str(WORKER))
    try:
        prepared = node.call({**q, 'op': 'prepare'})
    finally:
        node.close()
    assert public_seed(prepared) == root['original_decision']['search']['seed']
    assert predict_batch(model, [prepared['observation']])[0] == root['options'][0]
    assert not prepared['lossFilter']['forbidden']
    neural = {}
    if mode == 'neural_population':
        choices = predict_batch(model, [r['encoded'] for r in prepared['prior']])
        neural = {str(r['actor']): r['encoded']['moves'][a] for r, a in zip(prepared['prior'], choices)}
    start, cpu0 = time.perf_counter(), os.times()
    pool = EnginePool(min(p['workers'], count*2), script=str(WORKER))
    memory = MemorySampler([os.getpid(), *[process.pid for process in pool.processes]])
    memory.thread.start()
    rows, decisions, last_progress = [], 0, time.monotonic()
    try:
        response = pool.call({**q, 'op':'reset', 'n':count*2, 'offset':begin*2,
                              'options':root['options'], 'mode':mode, 'samples':p['samples'],
                              'maxSteps':p['max_steps'], 'belief':'policy', 'endgameFilter':True,
                              'seed':public_seed(prepared), 'referenceOpponent':root['opponent'],
                              'neuralBeliefs':neural})
        while True:
            rows.extend(response['ended'])
            live = [i for i, r in enumerate(response['observations']) if r is not None]
            if not live:
                break
            observations = [response['observations'][i] for i in live]
            assert all(r['roles'][r['actor']] == 'neural' for r in observations)
            if mode != 'neural_population':
                assert all(r['actor'] == q['player'] for r in observations)
            actions = [None] * (count*2)
            for i, a in zip(live, predict_batch(model, observations)):
                actions[i] = a
            decisions += len(live)
            response = pool.call({'op':'step', 'actions':actions})
            if time.monotonic()-last_progress > 45:
                print(json.dumps({'root':root_index, 'mode':mode, 'completed':len(rows),
                                  'neural_decisions':decisions, 'seconds':time.perf_counter()-start}), flush=True)
                last_progress = time.monotonic()
    finally:
        memory.stop.set(); memory.thread.join(); pool.close()
    cpu1 = os.times()
    rows.sort(key=lambda row: row['env'])
    result = {'root':root_index, 'label':root['label'], 'mode':mode, 'begin':begin, 'count':count,
              'options':root['options'], 'rows':rows, 'seconds':time.perf_counter()-start,
              'cpu_seconds':sum(cpu1[:4])-sum(cpu0[:4]), 'sampled_peak_total_rss_bytes':memory.peak,
              'memory_sampling_period_seconds':.1, 'protocol_sha256':digest(OUT/'protocol.json')}
    # Save raw evidence before rejecting any invalid execution; never silently discard failed work.
    write(output, result)
    checks = verify_rows(p, root_index, mode, begin, count, rows)
    assert decisions == checks['neural_decisions']
    write(output.with_suffix('.check.json'), checks)
    print(json.dumps({k:v for k,v in result.items() if k!='rows'} | {'checks':checks}), flush=True)


def pilot():
    p = read(OUT/'protocol.json'); validate(p)
    assert not os.environ.get('NODE_OPTIONS')
    os.environ['PG_REFERENCE_RUNTIME'] = p['runtime']
    model = Model(p['model_path'], threads=1)
    assert model_revision(model) == p['feature_revision']
    with (OUT/'pilot-intent.json').open('x') as f:
        json.dump({'started':time.time(), 'automatic_retries':False}, f)
    for i in range(7):
        run_root(p, model, i, 'neural_population', 0, 64, OUT/f'control-{i}.json')
    for i in p['pilot_roots']:
        run_root(p, model, i, 'reference_opponent_v1', 0, 2, OUT/f'pilot-{i}.json')
        if i in p['previous_completed_pilot_roots']:
            previous = read(ROOT/f'ai/runs/reference-opponent-diagnostic-v1/pilot-{i}.json')
            assert read(OUT/f'pilot-{i}.json')['rows'] == previous['rows'], 'Previous complete pilot changed'
    rejection_checks = []
    original = read(OUT/'pilot-6.json')['rows']
    corruptions = {
        'outer_cap': lambda rows: rows[0].update(truncated=True),
        'nested_cap': lambda rows: rows[0]['searchStats'].update(truncated=1),
        'prior_bid_cap': lambda rows: rows[0]['diagnostic']['priorSearchStats'].update(truncated=1),
        'invalid_score': lambda rows: rows[0].update(value=1.1),
        'wrong_world': lambda rows: rows[0]['diagnostic'].update(sampledWorldSha256='0'*64),
        'wrong_action': lambda rows: rows[0].update(actionIndex=rows[1]['actionIndex']),
        'missing_result': lambda rows: rows.pop(),
    }
    for name, corrupt in corruptions.items():
        rows = deepcopy(original); corrupt(rows)
        try:
            verify_rows(p, 6, 'reference_opponent_v1', 0, 2, rows)
        except AssertionError:
            rejection_checks.append(name)
        else:
            raise AssertionError(f'Corrupted evidence accepted: {name}')
    validate(p)
    write(OUT/'pilot-complete.json', {'complete':True, 'controls':896, 'reference_rollouts':16,
                                     'protocol_sha256':digest(OUT/'protocol.json'),
                                     'caps':0, 'new_hf_jobs':0, 'strength_claim':False,
                                     'previous_completed_pilot_roots_exact':p['previous_completed_pilot_roots'],
                                     'six_player_sealed_failure_complete':True,
                                     'rejection_checks':rejection_checks})


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('stage', choices=['prepare','pilot'])
    globals()[parser.parse_args().stage]()
