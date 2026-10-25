"""Paired, fixed-action continuation records; no action selection or training."""
from datetime import datetime, timezone
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path
import re
import time

from strategic_collection import ROOT, read, write, digest
from hybrid_search import predict_batch
from surrogate_continuation_roots_v1 import PROTOCOL, candidate, contract, object_hash
from surrogate_opponent_continuations_v1 import MODES, SurrogateContinuationProbe

STRONG = ROOT/'ai/strong'
SAMPLES = 8
MAX_STEPS = 2400


def policy_digest(policy):
    # Match the repository's canonical write() representation, including newline.
    return hashlib.sha256((json.dumps(policy, indent=2)+'\n').encode()).hexdigest()


def code_hashes():
    names = ['surrogate_continuation_study_v1.py', 'surrogate_continuation_roots_v1.py',
             'surrogate_opponent_continuations_v1.py', 'surrogate-opponent-continuations-v1.cjs',
             'reference-opponent-continuations-v2.cjs', 'reference-search-public-balances-v1.cjs',
             'analysis-public-balances-v1.cjs', 'hybrid_search.py', 'opponent_surrogate_policy_v1.py',
             'opponent_surrogate_training_v1.py', 'strategic_collection.py', PROTOCOL.name]
    return {str(p.relative_to(ROOT)): digest(p) for p in [*[STRONG/n for n in names], ROOT/'ai/infer.py', ROOT/'ai/pool.py']}


def check_root(root, probe):
    """Re-encode and rerun the focal model; provenance never enters inference."""
    q = root['identity']
    assert q == contract(q['players'], q['deal'], q['seat'], q['rule'], q['mode'])
    assert set(root['request']) == {'state', 'player'}
    prepared = probe.node.call({**root['request'], 'op': 'prepare', 'featureRevision': '4.3-strategic-correction'})
    proposal = predict_batch(probe.focal, [prepared['observation']])[0]
    index = prepared['lossFilter']['passIndex'] if proposal in prepared['lossFilter']['forbidden'] else proposal
    receipt = {'arm': 'filter', 'search': None, 'modelSha256': probe.focal.sha256,
               'index': index, 'modelProposal': proposal, 'move': prepared['moves'][index]}
    expected = candidate(root['request'], prepared, receipt, q, root['decision'])
    assert expected is not None and all(root[k] == v for k, v in expected.items())
    assert set(root) <= set(expected) | {'root_id', 'case'}
    if 'root_id' in root: assert root['root_id'] == f'{q["players"]}:{q["episode"]}:{root["phase"]}'
    assert root['public_root_sha256'] == object_hash(root['request'])
    return prepared


def exact_credit(terminal, seat, players):
    assert isinstance(terminal, list) and len(terminal) == players
    scores = []
    for row in terminal:
        assert set(row) == {'powered', 'money', 'cities'}
        score = tuple(row[k] for k in ('powered', 'money', 'cities'))
        assert all(type(v) is int and v >= 0 for v in score)
        scores.append(score)
    top = max(scores)
    return Fraction(1, scores.count(top)) if scores[seat] == top else Fraction(0)


def verify_result(root, result, mode, begin, count):
    """Independent checks also accept and retain explicit caps as unusable data."""
    assert mode in MODES and type(begin) is type(count) is int and 0 <= begin < SAMPLES and 0 < count <= SAMPLES-begin
    assert result['mode'] == mode and result['options'] == root['options'] and len(root['options']) == 2
    assert len(set(root['options'])) == 2
    assert result['samples'] == SAMPLES and result['begin'] == begin and result['count'] == count
    assert result['worker_sha256'] == digest(STRONG/'surrogate-opponent-continuations-v1.cjs')
    assert result['qualification_eligible'] is False
    assert type(result['seconds']) in (int, float) and math.isfinite(result['seconds']) and result['seconds'] >= 0
    rows = result['rows']; assert len(rows) == count*2
    n, seat = root['identity']['players'], root['identity']['seat']
    outer = nested = 0; decisions = {'neural': 0, 'surrogate': 0}; worlds = {}; credits = {}
    for i, row in enumerate(rows):
        sample = begin + i//2
        assert row['env'] == i and row['sample'] == sample and row['actionIndex'] == root['options'][i % 2]
        assert type(row['steps']) is int and 0 <= row['steps'] <= MAX_STEPS
        assert type(row['truncated']) is bool and row['truncated'] is (row['diagnostic']['terminal'] is None)
        if row['truncated']: assert row['steps'] == MAX_STEPS
        assert len(row['roles']) == n and row['roles'][seat] == 'neural'
        if mode != 'neural_population':
            other = 'surrogate' if mode == 'surrogate_opponent_v1' else 'search_geo'
            assert row['roles'] == ['neural' if p == seat else other for p in range(n)]
        else: assert set(row['roles']) <= {'neural', 'economic', 'legacy', 'rush'}
        assert all(type(v) is int and v >= 0 for v in row['policyDecisions'].values())
        assert sum(row['policyDecisions'].values()) == row['steps']
        for role in decisions: decisions[role] += row['policyDecisions'].get(role, 0)
        for stats in (row['searchStats'], row['diagnostic']['priorSearchStats']):
            assert set(stats) == {'decisions', 'evaluations', 'truncated'}
            assert all(type(v) is int and v >= 0 for v in stats.values())
            assert stats['truncated'] <= stats['evaluations']
            nested += stats['truncated']
            if mode != 'reference_opponent_v1': assert set(stats.values()) == {0}
        diagnostic = row['diagnostic']; sha = diagnostic['sampledWorldSha256']
        assert re.fullmatch('[a-f0-9]{64}', sha)
        actors = [item['actor'] for item in row['initialBelief']['committed']]
        assert actors == root['prior_actors']
        for item in row['initialBelief']['committed']:
            assert item['action']['name'] in ('Bid', 'Pass') and item['actor'] != seat
        world = {k: row[k] for k in ('roles', 'initialBelief')}; world['sha256'] = sha
        assert worlds.setdefault(sample, world) == world, 'Action pair used different sampled worlds or prior beliefs'
        outer += row['truncated']
        if row['truncated']:
            assert row['value'] is None; credits[(sample, i % 2)] = None
        else:
            credit = exact_credit(diagnostic['terminal'], seat, n)
            assert type(row['value']) in (int, float) and row['value'] == float(credit)
            credits[(sample, i % 2)] = credit
    assert result['inference_decisions'] == decisions
    assert result['outer_caps'] == outer and result['nested_caps'] == nested and result['caps'] == outer+nested
    assert result['usable'] is (outer+nested == 0)
    return {'worlds': worlds, 'credits': credits, 'caps': outer+nested, 'outer_caps': outer, 'nested_caps': nested}


def run_chunk(root, mode, begin, count, focal, surrogate, output, *, workers=8, surrogate_sha256=None):
    """One immutable execution. An interrupted output is never silently rerun."""
    assert focal.sha256 == read(PROTOCOL)['focal_model_sha256']
    assert mode in MODES and type(begin) is type(count) is int and 0 <= begin < SAMPLES and 0 < count <= SAMPLES-begin
    if mode == 'surrogate_opponent_v1':
        assert surrogate is not None and re.fullmatch('[a-f0-9]{64}', surrogate_sha256 or '')
        assert policy_digest(surrogate.policy) == surrogate_sha256, 'Loaded opponent policy differs from the frozen descriptor'
    else: assert surrogate is None and surrogate_sha256 is None
    output = Path(output); output.mkdir(parents=True, exist_ok=False)
    hashes = code_hashes(); start = time.perf_counter()
    intent = {'root_sha256': object_hash(root), 'public_root_sha256': root['public_root_sha256'],
              'mode': mode, 'begin': begin, 'count': count, 'samples': SAMPLES, 'max_steps': MAX_STEPS,
              'focal_model_sha256': focal.sha256, 'surrogate_policy_sha256': surrogate_sha256,
              'protocol_sha256': digest(PROTOCOL), 'code_hashes': hashes,
              'started_at': datetime.now(timezone.utc).isoformat(), 'workers': workers,
              'gradients': False, 'qualification_eligible': False, 'reserved_final_seeds_used': False}
    write(output/'intent.json', intent); write(output/'root.json', root)
    if surrogate is not None:
        write(output/'policy.json', surrogate.policy)
        assert digest(output/'policy.json') == surrogate_sha256
    status = {**intent, 'stage': 'running'}; write(output/'status.json', status)
    probe = None
    try:
        probe = SurrogateContinuationProbe(focal, surrogate, workers=workers); check_root(root, probe)
        result = probe.run(root['request'], root['options'], mode=mode, samples=SAMPLES,
                           begin=begin, count=count, max_steps=MAX_STEPS)
        write(output/'result.json', result)
        checked = verify_result(root, result, mode, begin, count)
        assert hashes == code_hashes()
        status.update(stage='complete' if result['usable'] else 'capped', caps=checked['caps'],
                      result_sha256=digest(output/'result.json'), rows=len(result['rows']))
    except BaseException as error:
        status.update(stage='failed', error=type(error).__name__+': '+str(error)); raise
    finally:
        if probe: probe.close()
        status['wall_seconds'] = time.perf_counter()-start; write(output/'status.json', status)
    return status


def verify_chunk(folder, root, *, surrogate_sha256=None):
    folder = Path(folder); intent = read(folder/'intent.json'); status = read(folder/'status.json')
    assert status['stage'] in ('complete', 'capped') and all(status[k] == v for k, v in intent.items())
    assert intent['root_sha256'] == object_hash(root) and read(folder/'root.json') == root
    assert intent['public_root_sha256'] == root['public_root_sha256']
    assert intent['protocol_sha256'] == digest(PROTOCOL) and intent['code_hashes'] == code_hashes()
    assert intent['focal_model_sha256'] == read(PROTOCOL)['focal_model_sha256']
    assert intent['surrogate_policy_sha256'] == (surrogate_sha256 if intent['mode'] == 'surrogate_opponent_v1' else None)
    if intent['mode'] == 'surrogate_opponent_v1':
        assert re.fullmatch('[a-f0-9]{64}', surrogate_sha256 or '')
        assert digest(folder/'policy.json') == policy_digest(read(folder/'policy.json')) == surrogate_sha256
    else: assert not (folder/'policy.json').exists()
    assert intent['samples'] == SAMPLES and intent['max_steps'] == MAX_STEPS
    assert all(intent[k] is False for k in ('gradients', 'qualification_eligible', 'reserved_final_seeds_used'))
    assert digest(folder/'result.json') == status['result_sha256']
    result = read(folder/'result.json'); checked = verify_result(root, result, intent['mode'], intent['begin'], intent['count'])
    assert status['stage'] == ('complete' if checked['caps'] == 0 else 'capped')
    assert status['caps'] == checked['caps'] and status['rows'] == len(result['rows'])
    return result


def paired_root(root, results):
    """Join every fixed world/action/mode; refuse omitted or duplicated chunks."""
    assert set(results) == set(MODES)
    gathered = {}; all_worlds = {}; caps = 0
    for mode in MODES:
        credits = {}; worlds = {}
        for result in results[mode]:
            check = verify_result(root, result, mode, result['begin'], result['count'])
            assert not (set(worlds) & set(check['worlds'])), 'Duplicated continuation samples'
            worlds.update(check['worlds']); credits.update(check['credits']); caps += check['caps']
        assert set(worlds) == set(range(SAMPLES)), 'Missing continuation samples'
        for sample, world in worlds.items():
            assert all_worlds.setdefault(sample, world['sha256']) == world['sha256'], 'Modes used different sampled deck worlds'
        gathered[mode] = credits
    report = {'complete': caps == 0, 'caps': caps, 'identity': root['identity'], 'phase': root['phase'],
              'root_sha256': object_hash(root), 'public_root_sha256': root['public_root_sha256'],
              'options': root['options'], 'prior_bid_count': len(root['prior_actors']), 'world_sha256': all_worlds,
              'mode_credits': {}, 'margins': None, 'qualification_eligible': False,
              'scope': 'Paired diagnostic terminal credits; not optimal-action labels, calibrated win probabilities, or full-game strength.'}
    rational = lambda value: [value.numerator, value.denominator] if value is not None else None
    for mode, values in gathered.items():
        report['mode_credits'][mode] = [[rational(values[(sample, action)]) for action in range(2)] for sample in range(SAMPLES)]
    if caps == 0:
        report['margins'] = {mode: rational(sum((v[(s, 1)]-v[(s, 0)] for s in range(SAMPLES)), Fraction())/SAMPLES)
                             for mode, v in gathered.items()}
    return report
