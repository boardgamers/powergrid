"""Pinned final-checkpoint development evaluation; no training or candidate selection."""
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
import torch
from huggingface_hub import HfApi, hf_hub_download
from model import policy_from_checkpoint

ROOT = Path(__file__).resolve().parents[2]
REPO = 'coyotte508/powergrid-ai-germany-v1'
FIXTURE_SHA = 'f1c97bf909e38e5df372a89d169d80f5a6f24c00dccefacd60b10b767f1fcfa0'
COUNTS = {'2': 349, '3': 427, '4': 527, '5': 609, '6': 641}
PARENT_ONNX = '2f1dd42625ea86404155e63124e55d95d07016027a0ceda4e08164357b554927'


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def write(path, value):
    Path(path).write_text(json.dumps(value, indent=2) + '\n')


def load_module(name, filename):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(filename))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def validate_training(directory, protocol, key):
    """Independently inspect tensors, all batches and pinned provenance, not just job status."""
    report = read(directory / 'ablation-check.json')
    source = read(ROOT / 'ai/strong/five-plant-ablation-source-v1.json')
    run = protocol['runs'][key]
    env = {**protocol['common_env'], **run['env']}
    expected = {'key': key, 'status': 'complete', 'games': 4800, 'update': 19,
                'protocol_sha256': digest(ROOT / 'ai/strong/five-plant-ablation-protocol-v1.json'),
                'source_revision': source['revision'], 'source_sha256': source['sha256'],
                'settings': env, 'tf32': False, 'qualification_eligible': False}
    for name, value in expected.items():
        if report.get(name) != value:
            raise ValueError('Training report mismatch: ' + name)
    for name, sha in report['artifact_sha256'].items():
        if Path(name).name != name or digest(directory / name) != sha:
            raise ValueError('Training artifact hash mismatch: ' + name)
    cp = torch.load(directory / 'latest.pt', map_location='cpu', weights_only=True)
    expected = {'update': 19, 'architecture': 'multiplayer_ordered_plants',
                'feature_revision': run['feature_revision'], 'state_dim': 1215, 'action_dim': 100,
                'mixed_player_counts': True, 'training_device': 'cuda', 'async_rollout': True,
                'snapshot_admission': 'periodic_anchor', 'snapshot_interval': 5,
                'snapshot_updates': [-1, 14, 19], 'opponent_mode': env['OPPONENT_MODE'],
                'initial_checkpoint': env['INIT_CHECKPOINT'], 'initial_revision': env['INIT_REVISION'],
                'initial_sha256': env['INIT_SHA256'], 'initial_feature_revision': run['feature_revision'],
                'frozen_opponents': read(ROOT / 'ai/strong/population-opponents-v1.json')}
    for name, value in expected.items():
        if cp.get(name) != value:
            raise ValueError('Checkpoint provenance mismatch: ' + name)
    assert cp['initial_transfer']['trained'] is False
    net = policy_from_checkpoint(cp).eval()
    assert sum(p.numel() for p in net.parameters()) == 985346
    assert all(torch.isfinite(v).all().item() for v in net.state_dict().values())
    norms = {k: cp['state_dict'][k].norm().item() for k in ['extra_player.weight', 'extra_action.weight']}
    assert norms == report['new_parameter_norms']
    assert all(v == 0 if run['condition'] == 'control' else v > 0 for v in norms.values())
    rows = [r for r in read(directory / 'metrics.json') if r.get('stage') == 'train']
    assert [r['update'] for r in rows] == list(range(20))
    roles = set()
    search_rollouts = 0
    for r in rows:
        assert r['episodes'] == 240 and r['truncated'] == 0
        assert set(r['by_player_count']) == set('23456')
        assert all(v['episodes'] == 48 and v['truncated'] == 0 for v in r['by_player_count'].values())
        assert sum(r['opponent_seats'].values()) == 960
        assert r['search_rollouts_reported'] and r['search_stats']
        assert all(v['truncated'] == 0 for v in r['search_stats'].values())
        search_rollouts += sum(v['evaluations'] for v in r['search_stats'].values())
        roles.update(r['opponent_seats'])
    assert {'frozen0', 'frozen1', 'frozen2', 'learner', 'search_geo'} <= roles
    assert any(k.startswith('mixed:') for r in rows for k in r['training_opponents'])
    return {'games': 4800, 'game_truncations': 0, 'search_truncations': 0,
            'search_rollouts': search_rollouts, 'new_parameter_norms': norms}


def prepare(key, revision, directory, protocol):
    if not re.fullmatch('[a-f0-9]{40}', revision):
        raise ValueError('Immutable model revision required')
    directory.mkdir(parents=True, exist_ok=True)
    parent = key == 'parent'
    if parent:
        init = protocol['initial']['validation']
        assert revision == init['parent_revision']
        prefix, feature = 'runs/multiplayer-refine-hard-v1', '4.0-multiplayer'
        names = ['latest.pt', 'latest.onnx', 'metrics.json', 'schema.json']
    else:
        run = protocol['runs'][key]
        prefix, feature = 'runs/' + run['env']['RUN_NAME'], run['feature_revision']
        raw = Path(hf_hub_download(REPO, prefix + '/ablation-check.json', revision=revision)).read_bytes()
        (directory / 'ablation-check.json').write_bytes(raw)
        report = json.loads(raw)
        assert report['status'] == 'complete', 'Final completed artifact required'
        names = list(report['artifact_sha256'])
        assert {'latest.pt', 'latest.onnx', 'metrics.json', 'schema.json'} <= set(names)
    hashes = {}
    for name in names:
        assert Path(name).name == name
        data = Path(hf_hub_download(REPO, prefix + '/' + name, revision=revision)).read_bytes()
        (directory / name).write_bytes(data)
        hashes[name] = hashlib.sha256(data).hexdigest()
    if parent:
        assert hashes['latest.pt'] == init['parent_sha256'] and hashes['latest.onnx'] == PARENT_ONNX
        cp = torch.load(directory / 'latest.pt', map_location='cpu', weights_only=True)
        assert cp['update'] == 79 and cp['feature_revision'] == feature
        validation = {'scope': 'Frozen original parent; not trained in this experiment'}
    else:
        validation = validate_training(directory, protocol, key)
    manifest = {'key': key, 'revision': revision, 'path': prefix, 'feature_revision': feature,
                'hashes': hashes, 'training': validation, 'qualification_eligible': False}
    write(directory / 'checkpoint.json', manifest)
    return manifest


def summarize(rows, evaluation):
    groups = {}
    for row in rows:
        groups.setdefault(row['gameSeed'], []).append(float(row['win']))
    assert len({len(v) for v in groups.values()}) == 1
    means = np.array([np.mean(groups[k]) for k in sorted(groups)])
    rng = np.random.default_rng(evaluation['bootstrap_seed'])
    samples = means[rng.integers(len(means), size=(evaluation['bootstrap_replicates'], len(means)))].mean(1)
    return {'games': len(rows), 'independent_deals': len(means), 'win_rate': float(means.mean()),
            'deal_bootstrap_95_interval': np.quantile(samples, [.025, .975]).tolist()}


def collect(directory, protocol, manifest):
    verifier = load_module('population_screen_verifier', 'collect-population-screen.py')
    ev, cells = protocol['evaluation'], {}
    for screen in ev['screens']:
        n, opponent = screen['players'], screen['opponent']
        file = directory / f'{opponent}-{n}p.json'
        report = read(file)
        verifier.verify_report(report, screen, manifest, ev, manifest['feature_revision'])
        rows = report['results']
        cells[f'{opponent}/{n}p'] = {**summarize(rows, ev), 'artifact_sha256': digest(file),
            'truncations': 0, 'by_rules': {v + ('/sealed' if s else '/open'): summarize(
                [r for r in rows if r['variant'] == v and r['sealed'] == s], ev)
                for v in ['original', 'recharged'] for s in [False, True]}}
    return {'checkpoint': manifest, 'cells': cells, 'qualification_eligible': False,
            'scope': 'Predeclared development seeds; no final qualification',
            'bootstrap_replicates': ev['bootstrap_replicates'], 'bootstrap_seed': ev['bootstrap_seed']}


def run(args):
    protocol = read(ROOT / 'ai/strong/five-plant-ablation-protocol-v1.json')
    assert args.key in ['parent', *protocol['runs']]
    out = args.output.resolve()
    fixtures = args.fixtures.resolve()
    assert digest(fixtures) == FIXTURE_SHA
    out.mkdir(parents=True, exist_ok=True)
    status = {'key': args.key, 'model_revision': args.revision, 'status': 'running',
              'protocol_sha256': digest(ROOT / 'ai/strong/five-plant-ablation-protocol-v1.json'),
              'source_revision': os.environ.get('SOURCE_REVISION'),
              'source_sha256': os.environ.get('SOURCE_SHA256'), 'qualification_eligible': False}

    def execute(command, log):
        with (out / log).open('w') as file:
            subprocess.run(command, cwd=ROOT, stdout=file, stderr=subprocess.STDOUT, check=True)

    try:
        manifest = prepare(args.key, args.revision, out, protocol)
        for script, filename in [('check-export.py', 'parity.json'), ('benchmark-serving.py', 'serving.json')]:
            command = [sys.executable, str(ROOT / 'ai/strong' / script)]
            if script == 'check-export.py':
                command.append(str(out / 'latest.pt'))
            command += [str(out / 'latest.onnx'), str(fixtures), '--output', str(out / filename)]
            execute(command, filename + '.log')
        parity, serving = read(out / 'parity.json'), read(out / 'serving.json')
        assert parity['positions'] == serving['positions'] == 2553
        assert parity['by_player_count'] == COUNTS
        assert {k: v['positions'] for k, v in serving['by_player_count'].items()} == COUNTS
        assert parity['all_actions_match'] and parity['inactive_values_zero'] and serving['all_moves_legal']
        assert parity['feature_revision'] == manifest['feature_revision']
        assert parity['model_sha256'] == serving['model_sha256'] == manifest['hashes']['latest.onnx']
        print(json.dumps({'stage': 'parity_and_serving_passed', 'key': args.key, 'positions': 2553}), flush=True)
        for screen in protocol['evaluation']['screens']:
            n, opponent = screen['players'], screen['opponent']
            filename = f'{opponent}-{n}p.json'
            command = [sys.executable, str(ROOT / 'ai/strong/evaluate.py'), str(out / 'latest.onnx'),
                       '--players', str(n), '--games', str(screen['games']), '--workers', str(args.workers),
                       '--seed', protocol['evaluation']['seed_template'].format(players=n),
                       '--opponent', 'economic' if opponent == 'a260' else opponent,
                       '--output', str(out / filename)]
            if opponent == 'a260':
                path = hf_hub_download(REPO, screen['model_path'], revision=screen['revision'])
                assert digest(path) == screen['sha256']
                command += ['--opponent-model', path]
            execute(command, filename + '.log')
            print(json.dumps({'stage': 'cell_complete', 'key': args.key, 'cell': filename}), flush=True)
        summary = collect(out, protocol, manifest)
        write(out / 'summary.json', summary)
        status.update(status='complete', games=sum(x['games'] for x in summary['cells'].values()),
                      cells=len(summary['cells']), truncations=0)
        assert status['games'] == 4000 and status['cells'] == 7
    except BaseException as error:
        status.update(status='failed', error=type(error).__name__ + ': ' + str(error))
        raise
    finally:
        status['artifact_sha256'] = {p.name: digest(p) for p in out.iterdir()
                                    if p.is_file() and p.name != 'screen-check.json'}
        write(out / 'screen-check.json', status)
        if args.upload:
            HfApi().upload_folder(repo_id=REPO, folder_path=out, path_in_repo='runs/five-plant-screen-v1-' + args.key)
        print(json.dumps({k: v for k, v in status.items() if k != 'artifact_sha256'}), flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser(__doc__)
    p.add_argument('key')
    p.add_argument('revision')
    p.add_argument('output', type=Path)
    p.add_argument('--fixtures', type=Path, default=ROOT / 'ai/strong/fixtures/multiplayer-serving-v1.jsonl')
    p.add_argument('--workers', type=int, default=24)
    p.add_argument('--upload', action='store_true')
    run(p.parse_args())
