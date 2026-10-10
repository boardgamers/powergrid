"""Pinned frozen-weight action-menu experiment; no optimizer or model selection."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import torch
from huggingface_hub import HfApi, hf_hub_download
from five_plant_screen import ROOT, REPO, COUNTS, read, write, digest, collect


def prepare(key, directory, protocol):
    pin = protocol['conditions'][key]
    directory.mkdir(parents=True, exist_ok=True)
    hashes = {}
    for local, remote, expected in [('latest.pt', pin['checkpoint'], pin['checkpoint_sha256']),
                                    ('latest.onnx', pin['model'], pin['model_sha256'])]:
        raw = Path(hf_hub_download(REPO, pin['prefix'] + '/' + remote, revision=pin['revision'])).read_bytes()
        (directory / local).write_bytes(raw)
        hashes[local] = digest(directory / local)
        assert hashes[local] == expected
    cp = torch.load(directory / 'latest.pt', map_location='cpu', weights_only=True)
    assert cp['architecture'] == 'multiplayer_ordered' and cp['update'] == 79
    assert cp['feature_revision'] == pin['feature_revision']
    assert (cp['state_dim'], cp['action_dim']) == (1149, 98)
    if key == 'expanded':
        assert cp['transfer']['trained'] is False and cp['transfer']['kind'] == 'sealed-bid-menu-only'
        parent = protocol['conditions']['control']
        file = hf_hub_download(REPO, parent['prefix'] + '/' + parent['checkpoint'], revision=parent['revision'])
        assert digest(file) == parent['checkpoint_sha256']
        original = torch.load(file, map_location='cpu', weights_only=True)
        assert cp['state_dict'].keys() == original['state_dict'].keys()
        assert all(torch.equal(v, original['state_dict'][k]) for k, v in cp['state_dict'].items())
    manifest = {'key': key, 'revision': pin['revision'], 'path': pin['prefix'],
                'feature_revision': pin['feature_revision'], 'hashes': hashes,
                'trained': False, 'qualification_eligible': False}
    write(directory / 'checkpoint.json', manifest)
    return manifest


def validate_checks(directory, manifest):
    parity, serving = read(directory / 'parity.json'), read(directory / 'serving.json')
    assert parity['positions'] == serving['positions'] == 2553
    assert parity['by_player_count'] == COUNTS
    assert {k: v['positions'] for k, v in serving['by_player_count'].items()} == COUNTS
    assert parity['all_actions_match'] and parity['inactive_values_zero'] and serving['all_moves_legal']
    assert parity['feature_revision'] == manifest['feature_revision']
    assert parity['model_sha256'] == serving['model_sha256'] == manifest['hashes']['latest.onnx']
    assert serving['search_samples'] == 0 and serving['search_truncated_rollouts'] == 0


def main():
    p = argparse.ArgumentParser(__doc__)
    p.add_argument('key', choices=['control', 'expanded'])
    p.add_argument('output', type=Path)
    p.add_argument('--upload', action='store_true')
    args = p.parse_args()
    protocol_file = ROOT / 'ai/strong/sealed-menu-protocol-v1.json'
    protocol = read(protocol_file)
    fixtures = ROOT / protocol['fixture_path']
    assert digest(fixtures) == protocol['fixture_sha256']
    out = args.output.resolve(); out.mkdir(parents=True, exist_ok=True)
    status = {'key': args.key, 'status': 'running', 'protocol_sha256': digest(protocol_file),
              'source_revision': os.environ.get('SOURCE_REVISION'), 'source_sha256': os.environ.get('SOURCE_SHA256'),
              'fixture_sha256': digest(fixtures), 'trained': False, 'qualification_eligible': False}

    def execute(command, log):
        with (out / log).open('w') as file:
            subprocess.run(command, cwd=ROOT, stdout=file, stderr=subprocess.STDOUT, check=True)

    try:
        manifest = prepare(args.key, out, protocol)
        for script, filename in [('check-export.py', 'parity.json'), ('benchmark-serving.py', 'serving.json')]:
            command = [sys.executable, str(ROOT / 'ai/strong' / script)]
            if script == 'check-export.py': command.append(str(out / 'latest.pt'))
            command += [str(out / 'latest.onnx'), str(fixtures), '--output', str(out / filename)]
            execute(command, filename + '.log')
        validate_checks(out, manifest)
        print(json.dumps({'stage': 'parity_and_serving_passed', 'key': args.key, 'positions': 2553}), flush=True)
        for screen in protocol['evaluation']['screens']:
            n, opponent = screen['players'], screen['opponent']
            filename = f'{opponent}-{n}p.json'
            command = [sys.executable, 'ai/strong/evaluate.py', str(out / 'latest.onnx'),
                       '--players', str(n), '--games', str(screen['games']), '--workers', '24',
                       '--seed', protocol['evaluation']['seed_template'].format(players=n),
                       '--opponent', 'economic' if opponent == 'a260' else opponent,
                       '--output', str(out / filename)]
            if opponent == 'a260':
                model = hf_hub_download(REPO, screen['model_path'], revision=screen['revision'])
                assert digest(model) == screen['sha256']
                command += ['--opponent-model', model]
            execute(command, filename + '.log')
            print(json.dumps({'stage': 'cell_complete', 'key': args.key, 'cell': filename}), flush=True)
        summary = collect(out, protocol, manifest)
        write(out / 'summary.json', summary)
        status.update(status='complete', games=sum(s['games'] for s in summary['cells'].values()),
                      cells=len(summary['cells']), truncations=0)
        assert status['games'] == 7520 and status['cells'] == 13
    except BaseException as error:
        status.update(status='failed', error=type(error).__name__ + ': ' + str(error))
        raise
    finally:
        status['artifact_sha256'] = {p.name: digest(p) for p in out.iterdir()
                                    if p.is_file() and p.name != 'screen-check.json'}
        write(out / 'screen-check.json', status)
        if args.upload:
            HfApi().upload_folder(repo_id=REPO, folder_path=out, path_in_repo='runs/sealed-menu-screen-v1-' + args.key)
        print(json.dumps({k: v for k, v in status.items() if k != 'artifact_sha256'}), flush=True)


if __name__ == '__main__':
    main()
