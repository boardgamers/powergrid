"""Re-evaluate every fixed final checkpoint after an explicit numerical repair."""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys

import torch
from huggingface_hub import HfApi, hf_hub_download
from five_plant_screen import ROOT, REPO, COUNTS, digest, read, write, load_module, collect

PROTOCOL = ROOT / 'ai/strong/inference64-screen-protocol-v1.json'


def config(cohort, key):
    protocol = read(PROTOCOL)
    cfg = protocol['cohorts'][cohort]
    assert digest(ROOT / cfg['original_protocol']) == cfg['original_protocol_sha256']
    original = read(ROOT / cfg['original_protocol'])
    assert cfg['evaluation'] == original['evaluation']
    assert key in cfg['models']
    return protocol, cfg, original


def fetch(prefix, revision, name, out, sha=None):
    assert Path(name).name == name
    target = out / name
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(hf_hub_download(REPO, prefix + '/' + name, revision=revision), target)
    if sha:
        assert digest(target) == sha, name
    return target


def prepare(cohort, key, out):
    torch.set_num_threads(1)
    _, cfg, original_protocol = config(cohort, key)
    pin = cfg['models'][key]
    src = out / 'original'
    src.mkdir(parents=True, exist_ok=True)
    if cohort == 'five-plant':
        origin = load_module('five_plant_prepare', 'five_plant_screen.py').prepare(
            key, pin['original']['revision'], src, original_protocol)
    else:
        for name, sha in pin['original']['hashes'].items():
            fetch(pin['original']['path'], pin['original']['revision'], name, src, sha)
        checkpoint = torch.load(src / 'latest.pt', map_location='cpu', weights_only=True)
        if key == 'parent':
            assert digest(src / 'latest.pt') == original_protocol['initial']['sha256']
            assert checkpoint['update'] == 79
        else:
            validator = load_module('population_prepare', 'prepare-population-screen.py')
            validator.validate_training(checkpoint, read(src / 'metrics.json'), original_protocol, key, 19)
        origin = pin['original']
    for name, sha in pin['original']['hashes'].items():
        assert digest(src / name) == sha
    model = out / 'derivative'
    derivative = pin['derivative']
    for name, sha in derivative['files'].items():
        fetch(derivative['prefix'], derivative['revision'], name, model, sha)
    cp = torch.load(model / 'inference64.pt', map_location='cpu', weights_only=True)
    source_cp = torch.load(src / 'latest.pt', map_location='cpu', weights_only=True)
    assert cp['inference_precision'] == 'float64' and cp['inference_only'] is True
    assert cp['inference_transform'] == 'float64-exp-div-silu-v1'
    assert cp['numerical_derivative']['source_checkpoint_sha256'] == digest(src / 'latest.pt')
    assert cp['feature_revision'] == source_cp['feature_revision'] == pin['feature_revision']
    assert cp['state_dict'].keys() == source_cp['state_dict'].keys()
    assert all(torch.equal(v, source_cp['state_dict'][k]) for k, v in cp['state_dict'].items())
    manifest = {'key': key, 'cohort': cohort, 'original_checkpoint': origin,
        'derivative': derivative, 'feature_revision': pin['feature_revision'],
        'hashes': {'latest.onnx': digest(model / 'inference64.onnx')},
        'inference_precision': 'float64', 'inference_transform': cp['inference_transform'],
        'qualification_eligible': False}
    write(out / 'evaluated-model.json', manifest)
    return manifest


def check_validation(out, manifest, protocol):
    parity, serving, audit = [read(out / f'{name}.json') for name in ['parity', 'serving', 'precision-audit']]
    sha = manifest['hashes']['latest.onnx']
    assert parity['positions'] == serving['positions'] == audit['positions'] == 2553
    assert parity['by_player_count'] == audit['by_player_count'] == COUNTS
    assert {k: v['positions'] for k, v in serving['by_player_count'].items()} == COUNTS
    assert parity['all_actions_match'] and parity['inactive_values_zero'] and serving['all_moves_legal']
    assert parity['feature_revision'] == audit['feature_revision'] == manifest['feature_revision']
    assert parity['model_sha256'] == serving['model_sha256'] == audit['derivative_onnx_sha256'] == sha
    assert audit['fixture_sha256'] == protocol['fixture_sha256']
    assert audit['source_checkpoint_sha256'] == digest(out / 'original/latest.pt')
    assert audit['source_onnx_sha256'] == digest(out / 'original/latest.onnx')
    assert audit['derivative_checkpoint_sha256'] == digest(out / 'derivative/inference64.pt')
    assert audit['native64_strict_pass'] and audit['stored_weights_identical']
    assert audit['rtol'] == 1e-4 and audit['atol'] == 1e-5
    assert audit['action_change_counts'] == {k: len(v) for k, v in audit['action_changes'].items()}


def run(args):
    protocol, cfg, _ = config(args.cohort, args.key)
    assert digest(args.fixtures) == protocol['fixture_sha256']
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=True)
    assert not (out / 'screen-check.json').exists(), 'Use a new documented run for retries'
    status = {'cohort': args.cohort, 'key': args.key, 'status': 'running',
        'protocol_sha256': digest(PROTOCOL), 'source_revision': os.environ.get('SOURCE_REVISION'),
        'source_sha256': os.environ.get('SOURCE_SHA256'), 'qualification_eligible': False}

    def execute(command, log):
        with (out / log).open('w') as file:
            subprocess.run(command, cwd=ROOT, stdout=file, stderr=subprocess.STDOUT, check=True)

    try:
        manifest = prepare(args.cohort, args.key, out)
        pt, onnx = [str(out / 'derivative' / name) for name in ['inference64.pt', 'inference64.onnx']]
        commands = {
            'parity': ['check-export.py', pt, onnx, str(args.fixtures.resolve())],
            'serving': ['benchmark-serving.py', onnx, str(args.fixtures.resolve())],
            'precision-audit': ['audit-inference64.py', str(out / 'original/latest.pt'),
                str(out / 'original/latest.onnx'), pt, onnx, str(args.fixtures.resolve())]}
        for label, command in commands.items():
            execute([sys.executable, str(ROOT / 'ai/strong' / command[0]), *command[1:],
                     '--output', str(out / (label + '.json'))], label + '.log')
        check_validation(out, manifest, protocol)
        print({'stage': 'validation_passed', 'cohort': args.cohort, 'key': args.key}, flush=True)
        for screen in cfg['evaluation']['screens']:
            n, opponent = screen['players'], screen['opponent']
            filename = f'{opponent}-{n}p.json'
            command = [sys.executable, str(ROOT / 'ai/strong/evaluate.py'), onnx,
                '--players', str(n), '--games', str(screen['games']), '--workers', '24',
                '--seed', cfg['evaluation']['seed_template'].format(players=n),
                '--opponent', 'economic' if opponent == 'a260' else opponent,
                '--output', str(out / filename)]
            if opponent == 'a260':
                path = hf_hub_download(REPO, screen['model_path'], revision=screen['revision'])
                assert digest(path) == screen['sha256']
                command += ['--opponent-model', path]
            execute(command, filename + '.log')
            print({'stage': 'cell_complete', 'cohort': args.cohort, 'key': args.key, 'cell': filename}, flush=True)
        summary = collect(out, cfg, manifest)
        write(out / 'summary.json', summary)
        status.update(status='complete', games=sum(x['games'] for x in summary['cells'].values()),
                      cells=len(summary['cells']), truncations=0)
        assert status['games'] == cfg['evaluation']['games_per_candidate']
    except BaseException as error:
        status.update(status='failed', error=type(error).__name__ + ': ' + str(error))
        raise
    finally:
        status['artifact_sha256'] = {str(p.relative_to(out)): digest(p) for p in out.rglob('*')
                                    if p.is_file() and p.name != 'screen-check.json'}
        write(out / 'screen-check.json', status)
        if args.upload:
            HfApi().upload_folder(repo_id=REPO, folder_path=out,
                path_in_repo=f'runs/inference64-screen-v1-{args.cohort}-{args.key}')
        print({k: v for k, v in status.items() if k != 'artifact_sha256'}, flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser(__doc__)
    p.add_argument('cohort', choices=['five-plant', 'population'])
    p.add_argument('key')
    p.add_argument('output', type=Path)
    p.add_argument('--fixtures', type=Path, default=ROOT / 'ai/strong/fixtures/multiplayer-serving-v1.jsonl')
    p.add_argument('--upload', action='store_true')
    run(p.parse_args())
