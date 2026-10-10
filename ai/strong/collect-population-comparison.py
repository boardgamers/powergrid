"""Recheck all raw cells, training pins and paired contrasts from a coordinator snapshot."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import torch
from huggingface_hub import hf_hub_download

ROOT = Path(__file__).resolve().parents[2]
REPO = 'coyotte508/powergrid-ai-germany-v1'


def module(name, filename):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(filename))
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('revision')
    parser.add_argument('update', type=int, choices=[9, 19])
    parser.add_argument('output', type=Path)
    parser.add_argument('--parent', type=Path, default=ROOT / 'ai/runs/population-parent-screen-v1')
    args = parser.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=True)
    prefix = 'runs/population-coordinator-v1'
    protocol = json.loads((ROOT / 'ai/strong/population-training-protocol-v1.json').read_text())
    prepare = module('prepare_population', 'prepare-population-screen.py')
    collect = module('collect_population', 'collect-population-screen.py')

    def download(path, revision=args.revision):
        return Path(hf_hub_download(REPO, path, revision=revision)).read_bytes()

    state_bytes = download(prefix + '/state.json')
    state = json.loads(state_bytes)
    assert str(args.update) in state['comparisons'], 'Comparison not ready'
    assert state['protocol_sha256'] == hashlib.sha256((ROOT / 'ai/strong/population-training-protocol-v1.json').read_bytes()).hexdigest()
    (out / 'coordinator-state.json').write_bytes(state_bytes)
    manifests = {}
    for arm in protocol['arms']:
        key = f'{arm}-u{args.update}'
        entry = state['checkpoints'][key]
        assert entry['phase'] == 'collected'
        assert all(s['observed_stage'] == 'COMPLETED' for s in entry['screens'].values())
        directory = out / key
        directory.mkdir(exist_ok=True)
        for name in ['checkpoint.json', 'parity.json', 'summary.json']:
            (directory / name).write_bytes(download(f'{prefix}/{key}/{name}'))
        pin = json.loads((directory / 'checkpoint.json').read_text())
        assert pin['revision'] == entry['revision'] and pin['arm'] == arm and pin['update'] == args.update
        assert pin['strict_parity'] == 'passed'
        for name, digest in pin['hashes'].items():
            raw = download(f'runs/{pin["run"]}/{name}', pin['revision'])
            assert hashlib.sha256(raw).hexdigest() == digest
            (directory / name).write_bytes(raw)
        checkpoint = torch.load(directory / 'latest.pt', map_location='cpu', weights_only=True)
        prepare.validate_training(checkpoint, json.loads((directory / 'metrics.json').read_text()), protocol, arm, args.update)
        parity = json.loads((directory / 'parity.json').read_text())
        assert parity['positions'] == 2553 and parity['all_actions_match']
        assert parity['by_player_count'] == {'2': 349, '3': 427, '4': 527, '5': 609, '6': 641}
        assert parity['model_sha256'] == pin['hashes']['latest.onnx']
        assert parity['feature_revision'] == '4.0-multiplayer' and parity['inactive_values_zero']
        original = json.loads((directory / 'summary.json').read_text())
        collect.collect(directory, entry['result_revision'])
        assert json.loads((directory / 'summary.json').read_text()) == original
        manifests[arm] = {'checkpoint': pin, 'result_revision': entry['result_revision'],
                          'screen_jobs': {k: v['job_id'] for k, v in entry['screens'].items()}}
    comparison = out / f'comparison-u{args.update}.json'
    command = [sys.executable, str(ROOT / 'ai/strong/compare-population-screens.py'),
               '--parent', str(args.parent.resolve()), '--update', str(args.update), '--output', str(comparison)]
    for arm in protocol['arms']:
        command += ['--' + arm, str(out / f'{arm}-u{args.update}')]
    subprocess.run(command, check=True)
    remote = download(prefix + '/' + state['comparisons'][str(args.update)])
    assert json.loads(remote) == json.loads(comparison.read_text()), 'Paired contrasts do not reproduce'
    report = {'coordinator_revision': args.revision, 'update': args.update, 'verified': True,
              'qualification_eligible': False, 'primary': args.update == protocol['primary_checkpoint_update'],
              'candidate_games': 3 * sum(s['games'] for s in protocol['evaluation']['screens']),
              'parent_games': sum(s['games'] for s in protocol['evaluation']['screens']),
              'truncations': 0, 'comparisons_reproduced': True,
              'comparison_sha256': hashlib.sha256(comparison.read_bytes()).hexdigest(), 'arms': manifests}
    (out / 'verified.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k: v for k, v in report.items() if k != 'arms'}))


if __name__ == '__main__':
    main()
