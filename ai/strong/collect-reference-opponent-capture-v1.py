"""Audit/archive all twenty passive-capture twin cases, never training labels."""
import argparse
from collections import Counter
import importlib.util
import json
import math
from pathlib import Path
import re
import shutil

import numpy as np
from strategic_collection import ROOT, read, write, digest
from policy_iteration_evidence_archive import upload_evidence

STRONG = ROOT / 'ai/strong'
RUN = ROOT / 'ai/runs/reference-opponent-capture-probe-v1'
OUT = ROOT / 'ai/runs/reference-opponent-capture-evidence-v1'
DESCRIPTOR = STRONG / 'reference-opponent-capture-evidence-v1.json'
HOST_DEPENDENCIES = ['ai/strong/population_hybrid_policy.py', 'ai/strong/hybrid_search.py',
                     'ai/infer.py', 'ai/pool.py', 'ai/strong/feature_contract.py',
                     'ai/strong/strategic_collection.py', 'ai/strong/arena_statistics.py']


def verify_row(row, ordinal, players, rule):
    assert row['ordinal'] == ordinal and row['qualification_eligible'] is False
    assert row['playerCount'] == players and type(row['seat']) is int and 0 <= row['seat'] < players - 1
    assert row['variant'] == ('recharged' if rule % 2 else 'original')
    assert row['sealed'] is (rule < 2)
    request = row['request']
    assert request['player'] == row['seat']
    state = request['state']
    assert state['options']['showMoney'] is True and state['options']['map'] == 'Germany'
    assert state['seed'] == 'secret' and state['powerPlantsDeck'] == state['hiddenLog'] == []
    assert 'powerPlantDeckAfterStep3' not in state and 'automation' not in state
    assert len(state['players']) == players
    assert all(p['lastMove'] is None and type(p['money']) is int and p['money'] >= 0 for p in state['players'])
    if row['sealed']:
        assert state['currentBid'] == 0 and all(p['bid'] == 0 for p in state['players'])
    assert re.fullmatch('[a-f0-9]{64}', row['publicRootSha256'])
    observation = row['observation']
    assert observation['featureRevision'] == '4.3-strategic-correction'
    assert len(observation['state']) == 1217 and np.isfinite(observation['state']).all()
    assert len(observation['actions']) == len(observation['moves']) > 1
    assert all(len(a) == 101 and np.isfinite(a).all() for a in observation['actions'])
    assert observation['playerOrder'][0] == row['seat'] and set(observation['playerOrder']) == set(range(players))
    assert observation['playerMask'] == [1] * players + [0] * (6 - players)
    target = row['target']
    assert type(target) is int and 0 <= target < len(observation['moves'])
    options, result = row['teacher']['options'], row['teacher']['result']
    assert options['samples'] == 16 and options['candidates'] == 6 and options['geography'] is True
    assert options.get('maxSteps', 2400) == 2400 and options.get('continuation', 'mixed') == 'mixed'
    assert isinstance(options['seed'], str) and options['seed'].startswith('arena-search-')
    assert result['index'] == target and result['action'] == observation['moves'][target]
    assert result.get('truncated', 0) == 0
    evaluations = result['evaluations']
    assert type(evaluations) is int and evaluations >= 0
    if evaluations:
        values = result['values']
        assert values and evaluations == 16 * len(values)
        assert all(str(int(k)) == k and 0 <= int(k) < len(observation['moves']) for k in values)
        assert all(math.isfinite(v) and 0 <= v <= 16 for v in values.values())
        assert values[str(target)] == max(values.values())
        assert result['winEstimate'] == values[str(target)] / 16
    assert math.isfinite(row['teacher']['elapsedMs']) and row['teacher']['elapsedMs'] >= 0
    kind = 'building' if any(m['name'] == 'Build' for m in observation['moves']) else \
           'bid' if any(m['name'] == 'Bid' for m in observation['moves']) else 'plant'
    assert any(m['name'] in ('Build', 'Bid', 'ChoosePowerPlant') for m in observation['moves'])
    return kind, evaluations


def audit_case(folder, players, rule, expected):
    result = read(folder / 'verified.json')
    assert result == expected and result['players'] == players and result['rule'] == rule
    assert result['episode'] == 4 * (players - 1) + rule and result['caps'] == 0
    assert result['training_eligible'] is result['qualification_eligible'] is False
    assert {p.name for p in folder.iterdir()} == {'verified.json', 'verification.json', 'replay.log', 'terminal.json', 'opponent-decisions.jsonl'}
    for field, name in [('capture_sha256', 'opponent-decisions.jsonl'), ('terminal_sha256', 'terminal.json'), ('verification_sha256', 'verification.json')]:
        assert digest(folder / name) == result[field]
    assert re.fullmatch('[a-f0-9]{64}', result['exact_twin_trajectory_sha256'])
    terminal, verification = read(folder / 'terminal.json'), read(folder / 'verification.json')
    assert read(folder / 'replay.log') == verification
    assert terminal['episode'] == result['episode'] and terminal['playerCount'] == players
    assert terminal['gameSeed'] == f'opponent-surrogate-capture-runtime-v1-{players}p-0'
    assert terminal['variant'] == ('recharged' if rule % 2 else 'original') and terminal['sealed'] is (rule < 2)
    assert terminal['roles'] == ['search_geo'] * (players - 1) + ['learner']
    assert terminal['truncated'] is False and 0 < terminal['steps'] <= 1600
    scores = [tuple(p[k] for k in ('powered', 'money', 'cities')) for p in terminal['final']['players']]
    assert len(scores) == players and all(type(x) is int and x >= 0 for s in scores for x in s)
    best = max(scores)
    assert terminal['value'] == [1 / scores.count(best) if s == best else 0 for s in scores]
    kinds, totals, latency = {}, Counter(), []
    with (folder / 'opponent-decisions.jsonl').open() as stream:
        for ordinal, line in enumerate(stream):
            row = json.loads(line)
            kind, evaluations = verify_row(row, ordinal, players, rule)
            kinds.setdefault(kind, []).append(ordinal)
            totals.update(decisions=1, evaluations=evaluations, truncated=0)
            latency.append(row['teacher']['elapsedMs'])
    assert totals == terminal['searchStats']['search_geo'] == verification['totals']
    assert totals['decisions'] == result['teacher_rows'] == verification['rows'] == verification['public_feature_and_menu_checks']
    assert totals['evaluations'] == result['teacher_rollouts']
    selected = sorted({i for indices in kinds.values() for i in (indices[0], indices[-1])})
    assert selected == verification['public_replays'] and len(selected) == result['public_replays']
    assert verification['all_targets_legal'] and verification['training_eligible'] is verification['qualification_eligible'] is False
    assert sum(latency) <= result['seconds'] * 1000
    return {'case': folder.name, 'players': players, 'rule': rule, 'teacher_rows': len(latency),
            'teacher_rollouts': totals['evaluations'], 'public_replays': len(selected),
            'learner_decisions': result['learner_decisions'], 'phase_rows': {k: len(v) for k,v in kinds.items()},
            'teacher_call_p50_ms': float(np.percentile(latency, 50)), 'teacher_call_p95_ms': float(np.percentile(latency, 95)),
            'paired_probe_seconds': result['seconds'], 'verified_sha256': digest(folder / 'verified.json')}


def audit():
    state = read(RUN / 'status.json')
    assert state['stage'] == 'complete', 'Wait for all twenty existing twin cases'
    assert not state['errors'] and state['exact_twin_games'] == 20
    expected = {f'{n}p-{r}' for n in range(2,7) for r in range(4)}
    assert set(state['cases']) == expected
    intent = read(RUN / 'intent.json')
    for key in ('source', 'runtime_file_hashes', 'probe_code_hashes', 'model_sha256', 'workers'):
        assert state[key] == intent[key]
    for key in ('training_eligible', 'gradients', 'qualification_eligible', 'reserved_final_seeds_used'):
        assert state[key] is False
    assert all(digest(ROOT / name) == sha for name,sha in state['probe_code_hashes'].items())
    spec = importlib.util.spec_from_file_location('opponent_capture_probe', STRONG / 'probe-reference-opponent-capture-v1.py')
    probe = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(probe)
    assert probe.source_files() == state['runtime_file_hashes']
    assert digest(probe.MODEL) == state['model_sha256']
    host_hashes = {name: digest(ROOT / name) for name in HOST_DEPENDENCIES}
    assert all(sha == state['runtime_file_hashes'][name] for name,sha in host_hashes.items())
    canonical = read(RUN / 'canonical.log')
    assert canonical['positions'] == canonical['hidden_field_mutations'] == 2553
    assert canonical['public_features_exact'] and canonical['game_states_unchanged'] and canonical['real_teacher_calls'] == 0
    assert canonical['counts'] == {'2':349, '3':427, '4':527, '5':609, '6':641}
    cells = [audit_case(RUN / f'{n}p-{r}', n, r, state['cases'][f'{n}p-{r}']) for n in range(2,7) for r in range(4)]
    assert sum(c['teacher_rows'] for c in cells) == state['teacher_rows']
    assert sum(c['public_replays'] for c in cells) == state['public_replays']
    return {'complete':True, 'exact_twin_games':20, 'game_executions':40,
            'canonical_positions':2553, 'source':state['source'], 'source_files_unchanged':1463,
            'model_sha256':state['model_sha256'], 'probe_code_hashes':state['probe_code_hashes'],
            'host_dependencies_match_frozen_source':host_hashes, 'collector_sha256':digest(__file__),
            'cells':cells, 'teacher_rows':state['teacher_rows'], 'public_teacher_replays':state['public_replays'],
            'teacher_rollouts':sum(c['teacher_rollouts'] for c in cells), 'caps':0,
            'training_eligible':False, 'gradients':False, 'new_hf_jobs':0,
            'qualification_eligible':False, 'reserved_final_seeds_used':False,
            'scope':'Passive capture engineering proof, all counts and rules at the last focal seat. Raw probe records are excluded from training/strength. Same-source paired games and public teacher replays support capture correctness; they do not validate a trained surrogate or representative latency.'}


def main(archive):
    review = audit()
    if not archive:
        print(json.dumps(review, indent=2))
        return
    assert not OUT.exists() and not OUT.with_suffix('.tgz').exists() and not DESCRIPTOR.exists(), 'Inspect previous archive attempts before retrying'
    files = [p for p in RUN.rglob('*') if p.is_file()]
    files += [ROOT / name for name in review['probe_code_hashes']]
    files += [ROOT / name for name in HOST_DEPENDENCIES]
    files += [Path(__file__), STRONG / 'test_reference_opponent_capture_collection_v1.py',
              STRONG / 'population-hybrid-development-source-v1.json', STRONG / 'population-hybrid-development-protocol-v1.json',
              STRONG / 'policy_iteration_evidence_archive.py', ROOT / 'ai/runs/reference-opponent-capture-probe-v1.log',
              ROOT / 'ai/runs/reference-opponent-capture-collector-preflight-v1.json',
              ROOT / 'ai/runs/reference-opponent-capture-collector-tests-v1.log']
    OUT.mkdir()
    for source in sorted(set(files)):
        assert source.is_file() and not source.is_symlink()
        dest = OUT / source.relative_to(ROOT)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, dest)
        assert digest(source) == digest(dest)
    write(OUT / 'review.json', review)
    write(OUT / 'manifest.json', {str(p.relative_to(OUT)):digest(p) for p in sorted(OUT.rglob('*')) if p.is_file()})
    write(DESCRIPTOR, {**review, **upload_evidence(OUT)})
    print({k:read(DESCRIPTOR)[k] for k in ('revision','archive_sha256','archived_files','remote_archive_verified')})


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--archive', action='store_true')
    main(parser.parse_args().archive)
