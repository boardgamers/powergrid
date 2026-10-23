"""Complete paired development deals with immutable, independently pinned models."""
import argparse
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

PROTOCOL = ROOT/'ai/strong/strategic-correction-screen-protocol-v1.json'
SOURCE = ROOT/'ai/strong/strategic-correction-screen-source-v1.json'


def module(name, file):
    spec = importlib.util.spec_from_file_location(name, ROOT/'ai/strong'/file)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


verifier = module('strategic_screen_verifier', 'collect-population-screen.py')
pairs = module('strategic_screen_pairs', 'compare-population-screens.py')


def cell_for(protocol, n, opponent):
    return next(row for row in protocol['screens'] if row['players'] == n and row['opponent'] == opponent)


def case_key(key, n, opponent, start, end, smoke=False):
    return ('smoke-' if smoke else '')+f'{key}-{n}p-{opponent}-{start}-{end}'


def prefix(*args):
    return 'runs/strategic-correction-screen-v1-'+case_key(*args)


def pin_hash(pin):
    import hashlib
    return hashlib.sha256(json.dumps(pin, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def validate_pin(pin, key, protocol):
    assert key in protocol['models'] and pin['key'] == key
    assert pin['repo'] == protocol['repo'] and re.fullmatch('[0-9a-f]{40}', pin['revision'])
    assert re.fullmatch('[0-9a-f]{64}', pin['files']['inference64.onnx'])
    assert re.fullmatch('[0-9a-f]{64}', pin['files']['inference64.pt'])
    assert pin['feature_revision'] == ('4.2-discard-correction' if key == 'parent' else '4.3-strategic-correction')
    if key == 'parent':
        parent = read(ROOT/'ai/strong/strategic-teacher-training-protocol-v1.json')['model']
        assert pin['revision'] == parent['revision']
        assert pin['prefix']+'/inference64.onnx' == parent['path']
        assert pin['files']['inference64.onnx'] == parent['sha256']
    else:
        assert pin['training_verified'] and pin['parent_frozen'] and pin['seed'] == int(key)
        assert pin['strict_parity_positions'] == 2553
        assert re.fullmatch('[0-9a-f]{64}', pin['training_verified_sha256'])


def contract(protocol, n, opponent, start, end, smoke=False):
    cell = cell_for(protocol, n, opponent)
    if smoke:
        assert start == 0 and end == 1
    else:
        assert start in range(0, cell['deals'], 4) and end == start+4 <= cell['deals']
    screen = {**cell, 'games': (end-start)*4*n, 'deal_offset': start}
    evaluation = {**protocol, 'deal_offsets': list(range(start, end)),
        'seed_template': protocol['smoke_seed_template' if smoke else 'seed_template']}
    return screen, evaluation


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


def verify_report(report, protocol, pin, n, opponent, start, end, smoke=False):
    screen, evaluation = contract(protocol, n, opponent, start, end, smoke)
    checks = verifier.verify_report(report, screen,
        {'hashes': {'latest.onnx': pin['files']['inference64.onnx']}}, evaluation, pin['feature_revision'])
    rows = report['results']
    assert {r['episode'] for r in rows} == set(range(start*4*n, end*4*n))
    assert all(r['seat'] == r['episode']//4 % n and r['variant'] == ('recharged' if r['episode']%2 else 'original')
        and r['sealed'] == (r['episode']%4 < 2) for r in rows)
    if opponent == 'search_geo':
        stats = checks['search_stats']['search_geo']
        assert stats['evaluations'] > 0 and stats['decisions'] > 0
    return {**summarize(rows, evaluation), 'seconds': report['seconds'],
        'search_stats': checks['search_stats'], 'game_truncations': 0, 'search_truncations': 0,
        'by_rules': {v+('/sealed' if s else '/open'): summarize(
            [r for r in rows if r['variant'] == v and r['sealed'] == s], evaluation)
            for v in ['original', 'recharged'] for s in [False, True]}}


def same(actual, stored):
    if isinstance(actual, dict):
        assert actual.keys() == stored.keys()
        for key, value in actual.items(): same(value, stored[key])
    elif isinstance(actual, list):
        assert len(actual) == len(stored)
        for a, b in zip(actual, stored): same(a, b)
    elif isinstance(actual, float):
        assert np.isfinite(actual) and np.isfinite(stored) and abs(actual-stored) < 1e-12
    else:
        assert actual == stored


def verify_serving(serving, pin):
    assert serving['positions'] == 2553 and serving['all_moves_legal']
    assert serving['model_sha256'] == pin['files']['inference64.onnx'] and serving['search_samples'] == 0
    assert {n: x['positions'] for n, x in serving['by_player_count'].items()} == {'2':349,'3':427,'4':527,'5':609,'6':641}


def verify_local(out, key, n, opponent, start, end, smoke, pin, source=None):
    protocol = read(PROTOCOL)
    validate_pin(pin, key, protocol)
    screen, _ = contract(protocol, n, opponent, start, end, smoke)
    status = read(out/'screen-check.json')
    expected = {'status': 'complete', 'key': key, 'players': n, 'opponent': opponent,
        'start': start, 'end': end, 'smoke': smoke, 'protocol_sha256': digest(PROTOCOL),
        'model_pin_sha256': pin_hash(pin), 'games': screen['games'],
        'game_truncations': 0, 'search_truncations': 0, 'qualification_eligible': False}
    if source:
        expected.update(source_revision=source['revision'], source_sha256=source['sha256'])
    for name, value in expected.items(): assert status[name] == value, name
    assert {'checkpoint.json', 'serving.json', 'evaluation.json', 'summary.json'} <= set(status['artifacts'])
    for name, sha in status['artifacts'].items():
        assert Path(name).name == name and digest(out/name) == sha
    assert read(out/'checkpoint.json') == pin
    verify_serving(read(out/'serving.json'), pin)
    summary = verify_report(read(out/'evaluation.json'), protocol, pin, n, opponent, start, end, smoke)
    same(summary, read(out/'summary.json'))
    return summary


def run(args):
    protocol = read(PROTOCOL)
    pin = read(args.pin) if args.pin else json.loads(os.environ['MODEL_PIN'])
    validate_pin(pin, args.key, protocol)
    if not args.pin:
        assert pin_hash(pin) == os.environ['MODEL_PIN_SHA256']
    if args.upload:
        assert not args.pin and os.environ.get('SOURCE_REVISION') and os.environ.get('SOURCE_SHA256')
    screen, evaluation = contract(protocol, args.players, args.opponent, args.start, args.end, args.smoke)
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    status = {'status': 'running', 'key': args.key, 'players': args.players, 'opponent': args.opponent,
        'start': args.start, 'end': args.end, 'smoke': args.smoke, 'protocol_sha256': digest(PROTOCOL),
        'model_pin_sha256': pin_hash(pin), 'source_revision': os.environ.get('SOURCE_REVISION'),
        'source_sha256': os.environ.get('SOURCE_SHA256'), 'qualification_eligible': False}
    def execute(label, arguments):
        with (out/(label+'.log')).open('w') as log:
            subprocess.run([sys.executable, *map(str, arguments)], cwd=ROOT,
                stdout=log, stderr=subprocess.STDOUT, check=True)
    try:
        model = hf_hub_download(pin['repo'], pin['prefix']+'/inference64.onnx', revision=pin['revision'])
        assert digest(model) == pin['files']['inference64.onnx']
        write(out/'checkpoint.json', pin)
        execute('serving', [ROOT/'ai/strong/benchmark-serving.py', model,
            ROOT/'ai/strong/fixtures/multiplayer-serving-v1.jsonl', '--output', out/'serving.json'])
        verify_serving(read(out/'serving.json'), pin)
        command = [ROOT/'ai/strong/evaluate.py', model, '--players', args.players, '--games', screen['games'],
            '--deal-offset', args.start, '--workers', protocol['workers'],
            '--seed', evaluation['seed_template'].format(players=args.players),
            '--opponent', 'economic' if args.opponent == 'a260' else args.opponent,
            '--output', out/'evaluation.json']
        if args.opponent == 'a260':
            other = hf_hub_download(protocol['repo'], screen['model_path'], revision=screen['revision'])
            assert digest(other) == screen['sha256']
            command += ['--opponent-model', other]
        execute('evaluation', command)
        summary = verify_report(read(out/'evaluation.json'), protocol, pin,
            args.players, args.opponent, args.start, args.end, args.smoke)
        write(out/'summary.json', summary)
        status.update(status='complete', games=summary['games'], game_truncations=0, search_truncations=0)
    except BaseException as error:
        status.update(status='failed', error=type(error).__name__+': '+str(error))
        raise
    finally:
        status['artifacts'] = {p.name:digest(p) for p in out.iterdir() if p.is_file()}
        write(out/'screen-check.json', status)
        if args.upload:
            HfApi().upload_folder(repo_id=protocol['repo'], folder_path=out,
                path_in_repo=prefix(args.key, args.players, args.opponent, args.start, args.end, args.smoke))
        print(status, flush=True)
    verify_local(out, args.key, args.players, args.opponent, args.start, args.end, args.smoke, pin)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('key', choices=['parent', '11101', '11102'])
    parser.add_argument('players', type=int, choices=range(2, 7))
    parser.add_argument('opponent')
    parser.add_argument('start', type=int)
    parser.add_argument('end', type=int)
    parser.add_argument('output', type=Path)
    parser.add_argument('--pin', type=Path, help='Local preflight only; HF jobs use the pinned environment')
    parser.add_argument('--smoke', action='store_true')
    parser.add_argument('--upload', action='store_true')
    run(parser.parse_args())
