"""Fresh paired whole-game evaluation; synthetic models are plumbing-only."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys

import numpy as np
from huggingface_hub import HfApi, hf_hub_download
from strategic_collection import ROOT, read, write, digest
from arena_statistics import validate_pairs, search_summary, win_summary

PROTOCOL = ROOT/'ai/strong/policy-iteration-development-protocol-v2.json'
SOURCE = ROOT/'ai/strong/policy-iteration-development-source-v2.json'


def module(name, file):
    spec = importlib.util.spec_from_file_location(name, ROOT/'ai/strong'/file)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


pairs = module('policy_iteration_pairs', 'compare-population-screens.py')


def pin_hash(pin):
    return hashlib.sha256(json.dumps(pin, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def validate_pin(pin, key, protocol, *, plumbing=False):
    assert key in protocol['models'] and pin['key'] == key
    assert pin['repo'] == protocol['repo']
    for file in ['inference64.onnx', 'inference64.pt']:
        assert re.fullmatch('[a-f0-9]{64}', pin['files'][file])
    if key == 'parent':
        assert pin == protocol['parent_pin']
        return
    spec = protocol['candidate_heads'][key]
    assert pin['feature_revision'] == '4.3-strategic-correction'
    assert pin['model_args'] == {'head_type': spec['head_type'], 'heads': 4, 'margin': .025,
                                 'parent_margin': .025, 'disagreement_penalty': spec['penalty']}
    if plumbing:
        assert pin['synthetic_untrained'] and not pin['training_verified']
        return
    assert not pin.get('synthetic_untrained', False)
    assert re.fullmatch('[a-f0-9]{40}', pin['revision'])
    assert pin['prefix'] == 'runs/policy-iteration-training-v2-'+spec['head_type']+'/ensemble-'+str(int(spec['penalty']))+'/derivative'
    assert pin['training_verified'] and pin['parent_frozen']
    assert pin['seeds'] == protocol['candidate_seeds']
    assert pin['design_sha256'] == protocol['training_design_sha256']
    assert re.fullmatch('[a-f0-9]{64}', pin['training_verified_sha256'])
    assert re.fullmatch('[a-f0-9]{64}', pin['data_check_sha256'])
    assert pin['strict_parity_positions'] == 2553 and pin['cached_positions_checked'] == 17280


def contract(protocol, n, opponent, start, end, mode):
    assert mode in ['development', 'smoke', 'plumbing']
    cells = [r for r in protocol['screens'] if r['players'] == n and r['opponent'] == opponent]
    assert len(cells) == 1
    cell = cells[0]
    if mode == 'development':
        assert start in range(0, cell['deals'], 4) and end == start+4 <= cell['deals']
        seed = protocol['seed_template']
    elif mode == 'smoke':
        assert n in [2, 6] and opponent == 'search_geo' and start == 0 and end == 1
        seed = protocol['smoke_seed_template']
    else:
        assert n in [2, 6] and start == 4 and end == 5
        seed = protocol['plumbing_seed_template']
    assert 'reserved' not in seed and seed.startswith('policy-iteration-')
    return {**cell, 'games': (end-start)*4*n, 'deal_offset': start}, {
        **protocol, 'seed_template': seed, 'deal_offsets': list(range(start, end))}


def case_key(key, n, opponent, start, end, mode='development'):
    return f'{mode}-{key}-{n}p-{opponent}-{start}-{end}'


def prefix(*args):
    return 'runs/policy-iteration-development-v2-'+case_key(*args)


def summarize(rows, protocol):
    means = np.asarray([np.mean([r['win'] for r in rows if r['gameSeed'] == seed])
                        for seed in sorted({r['gameSeed'] for r in rows})])
    interval = None
    if len(means) > 1:
        rng = np.random.default_rng(protocol['bootstrap_seed'])
        draws = means[rng.integers(len(means), size=(protocol['bootstrap_replicates'], len(means)))].mean(1)
        interval = np.quantile(draws, [.025, .975]).tolist()
    return {'games': len(rows), 'independent_deals': len(means), 'win_rate': float(means.mean()),
            'deal_bootstrap_95_interval': interval}


def verify_report(report, protocol, pin, n, opponent, start, end, mode):
    screen, evaluation = contract(protocol, n, opponent, start, end, mode)
    seed = evaluation['seed_template'].format(players=n)
    expected = {'model_sha256': pin['files']['inference64.onnx'], 'model_feature_revision': pin['feature_revision'],
                'encoder_feature_revision': pin['feature_revision'], 'player_count': n, 'games': screen['games'],
                'paired_seats': True, 'candidate_search_samples': 0, 'candidate_geographic_search': False,
                'candidate_search_scope': 'all', 'candidate_search_model_proposal': True,
                'seed': seed, 'deal_offset': start, 'search_max_steps': 2400, 'opponent_sha256': screen.get('sha256')}
    for field, value in expected.items():
        assert report[field] == value, field
    if opponent != 'a260':
        assert report['opponent'] == opponent
    assert report['async_rollout'] is False and report['engine_workers'] == min(protocol['workers'], screen['games'])
    assert np.isfinite(report['seconds']) and report['seconds'] > 0
    rows = report['results']
    assert len(rows) == screen['games']
    validate_pairs(rows, n)
    assert {r['gameSeed'] for r in rows} == {seed+'-'+str(i) for i in range(start, end)}
    role = 'snapshot0' if opponent == 'a260' else opponent
    assert all(not r['truncated'] and all(actor in ['learner', role] for actor in r['roles']) for r in rows)
    checks = search_summary(rows)
    assert checks['search_rollouts_reported'] and all(stats['truncated'] == 0 for stats in checks['search_stats'].values())
    assert report['truncated'] == 0 and abs(win_summary(rows)['win_rate']-report['win_rate']) < 1e-12
    assert {r['episode'] for r in rows} == set(range(start*4*n, end*4*n))
    assert all(r['seat'] == r['episode']//4 % n and r['variant'] == ('recharged' if r['episode']%2 else 'original')
               and r['sealed'] == (r['episode']%4 < 2) for r in rows)
    if opponent == 'search_geo':
        stats = checks['search_stats']['search_geo']
        assert stats['evaluations'] > 0 and stats['decisions'] > 0
    return {**summarize(rows, evaluation), 'seconds': report['seconds'], 'search_stats': checks['search_stats'],
            'game_truncations': 0, 'search_truncations': 0,
            'by_rules': {v+('/sealed' if s else '/open'): summarize(
                [r for r in rows if r['variant'] == v and r['sealed'] == s], evaluation)
                for v in ['original', 'recharged'] for s in [False, True]}}


def verify_serving(report, pin):
    assert report['positions'] == 2553 and report['all_moves_legal'] and report['search_samples'] == 0
    assert report['model_sha256'] == pin['files']['inference64.onnx']
    assert {n: c['positions'] for n, c in report['by_player_count'].items()} == {'2': 349, '3': 427, '4': 527, '5': 609, '6': 641}


def same(actual, stored):
    if isinstance(actual, dict):
        assert actual.keys() == stored.keys()
        for key in actual:
            same(actual[key], stored[key])
    elif isinstance(actual, list):
        assert len(actual) == len(stored)
        for a, b in zip(actual, stored):
            same(a, b)
    elif isinstance(actual, float):
        assert np.isfinite(actual) and np.isfinite(stored) and abs(actual-stored) < 1e-12
    else:
        assert actual == stored


def verify_local(out, key, n, opponent, start, end, mode, pin, source=None):
    protocol = read(PROTOCOL)
    validate_pin(pin, key, protocol, plumbing=mode == 'plumbing')
    status = read(out/'development-check.json')
    expected = {'status': 'complete', 'key': key, 'players': n, 'opponent': opponent, 'start': start, 'end': end,
                'mode': mode, 'protocol_sha256': digest(PROTOCOL), 'model_pin_sha256': pin_hash(pin),
                'game_truncations': 0, 'search_truncations': 0, 'qualification_eligible': False}
    if source:
        expected.update(source_revision=source['revision'], source_sha256=source['sha256'])
    for name, value in expected.items():
        assert status[name] == value, name
    assert {'checkpoint.json', 'serving.json', 'evaluation.json', 'summary.json'} <= set(status['artifacts'])
    for file, sha in status['artifacts'].items():
        assert Path(file).name == file and digest(out/file) == sha
    assert read(out/'checkpoint.json') == pin
    verify_serving(read(out/'serving.json'), pin)
    summary = verify_report(read(out/'evaluation.json'), protocol, pin, n, opponent, start, end, mode)
    same(summary, read(out/'summary.json'))
    assert status['games'] == summary['games']
    return summary


def run(args):
    protocol = read(PROTOCOL)
    assert digest(ROOT/'ai/strong/policy-iteration-training-design-v2.json') == protocol['training_design_sha256']
    pin = read(args.pin) if args.pin else json.loads(os.environ['MODEL_PIN'])
    validate_pin(pin, args.key, protocol, plumbing=args.mode == 'plumbing')
    if not args.pin:
        assert pin_hash(pin) == os.environ['MODEL_PIN_SHA256']
    if args.mode == 'plumbing':
        assert args.pin and not args.upload
    if args.local_model:
        assert args.mode == 'plumbing' and args.key != 'parent' and not args.upload
    if args.upload:
        assert not args.pin and args.mode != 'plumbing'
        assert os.environ.get('SOURCE_REVISION') and os.environ.get('SOURCE_SHA256')
    screen, evaluation = contract(protocol, args.players, args.opponent, args.start, args.end, args.mode)
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    status = {'status': 'running', 'key': args.key, 'players': args.players, 'opponent': args.opponent,
              'start': args.start, 'end': args.end, 'mode': args.mode, 'protocol_sha256': digest(PROTOCOL),
              'model_pin_sha256': pin_hash(pin), 'source_revision': os.environ.get('SOURCE_REVISION'),
              'source_sha256': os.environ.get('SOURCE_SHA256'), 'qualification_eligible': False}
    def execute(name, command):
        with (out/(name+'.log')).open('w') as log:
            subprocess.run([sys.executable, *map(str, command)], cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, check=True)
    try:
        model = args.local_model or hf_hub_download(pin['repo'], pin['prefix']+'/inference64.onnx', revision=pin['revision'])
        assert digest(model) == pin['files']['inference64.onnx']
        write(out/'checkpoint.json', pin)
        execute('serving', [ROOT/'ai/strong/benchmark-serving.py', model,
            ROOT/'ai/strong/fixtures/multiplayer-serving-v1.jsonl', '--output', out/'serving.json'])
        verify_serving(read(out/'serving.json'), pin)
        command = [ROOT/'ai/strong/evaluate.py', model, '--players', args.players, '--games', screen['games'],
                   '--deal-offset', args.start, '--workers', protocol['workers'],
                   '--seed', evaluation['seed_template'].format(players=args.players),
                   '--opponent', 'economic' if args.opponent == 'a260' else args.opponent, '--output', out/'evaluation.json']
        if args.opponent == 'a260':
            other = hf_hub_download(protocol['repo'], screen['model_path'], revision=screen['revision'])
            assert digest(other) == screen['sha256']
            command += ['--opponent-model', other]
        execute('evaluation', command)
        summary = verify_report(read(out/'evaluation.json'), protocol, pin,
                                args.players, args.opponent, args.start, args.end, args.mode)
        write(out/'summary.json', summary)
        status.update(status='complete', games=summary['games'], game_truncations=0, search_truncations=0)
    except BaseException as error:
        status.update(status='failed', error=type(error).__name__+': '+str(error))
        raise
    finally:
        status['artifacts'] = {p.name: digest(p) for p in out.iterdir() if p.is_file()}
        write(out/'development-check.json', status)
        if args.upload:
            HfApi().upload_folder(repo_id=protocol['repo'], folder_path=out,
                path_in_repo=prefix(args.key, args.players, args.opponent, args.start, args.end, args.mode))
        print({k: v for k, v in status.items() if k != 'artifacts'}, flush=True)
    verify_local(out, args.key, args.players, args.opponent, args.start, args.end, args.mode, pin)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('key')
    parser.add_argument('players', type=int)
    parser.add_argument('opponent')
    parser.add_argument('start', type=int)
    parser.add_argument('end', type=int)
    parser.add_argument('output', type=Path)
    parser.add_argument('--mode', choices=['development', 'smoke', 'plumbing'], default='development')
    parser.add_argument('--pin', type=Path)
    parser.add_argument('--local-model', type=Path)
    parser.add_argument('--upload', action='store_true')
    run(parser.parse_args())
