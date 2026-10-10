"""Frozen two-seed input ablation. Training is permitted on HF Jobs only."""
import hashlib
import json
import os
from pathlib import Path
import runpy
import torch
from huggingface_hub import HfApi


def main():
    if os.environ.get('POWERGRID_TRAINING_PLATFORM') != 'hf-job':
        raise ValueError('Run gradients on HF Jobs only')
    path = Path('ai/strong/five-plant-ablation-protocol-v1.json')
    protocol = json.loads(path.read_text())
    key = os.environ['ABLATION_KEY']
    settings = {**protocol['common_env'], **protocol['runs'][key]['env']}
    for name, expected in settings.items():
        if os.environ.get(name) != expected:
            raise ValueError('Frozen ablation configuration mismatch: ' + name)
    for name, digest in protocol['runtime_sha256'].items():
        if hashlib.sha256(Path(name).read_bytes()).hexdigest() != digest:
            raise ValueError('Runtime hash mismatch: ' + name)
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    out = Path('ai/runs') / os.environ['RUN_NAME']
    out.mkdir(parents=True, exist_ok=True)
    report = {'key': key, 'qualification_eligible': False, 'protocol_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
              'source_revision': os.environ['SOURCE_REVISION'], 'source_sha256': os.environ['SOURCE_SHA256'],
              'settings': settings, 'tf32': False}
    try:
        runpy.run_path('ai/strong/train.py', run_name='__main__')
        metrics = json.loads((out / 'metrics.json').read_text())
        rows = [r for r in metrics if r.get('stage') == 'train']
        assert [r['update'] for r in rows] == list(range(20))
        for row in rows:
            assert row['episodes'] == 240 and row['truncated'] == 0
            assert set(row['by_player_count']) == set('23456')
            assert all(x['episodes'] == 48 and x['truncated'] == 0 for x in row['by_player_count'].values())
            assert sum(row['opponent_seats'].values()) == 960
            assert row['search_rollouts_reported'] and row['search_stats']
            assert all(x['truncated'] == 0 for x in row['search_stats'].values())
        checkpoint = torch.load(out / 'latest.pt', map_location='cpu', weights_only=True)
        assert checkpoint['update'] == 19 and checkpoint['snapshot_updates'] == [-1, 14, 19]
        assert checkpoint['initial_sha256'] == settings['INIT_SHA256']
        assert checkpoint['initial_revision'] == settings['INIT_REVISION']
        expected_revision = '4.1-five-plants-zero-inputs' if settings['ZERO_NEW_PLANT_INPUTS'] == '1' else '4.1-five-plants'
        assert checkpoint['feature_revision'] == expected_revision
        assert checkpoint['architecture'] == 'multiplayer_ordered_plants'
        assert checkpoint['state_dim'] == 1215 and checkpoint['action_dim'] == 100
        norms = {k: checkpoint['state_dict'][k].norm().item() for k in ['extra_player.weight', 'extra_action.weight']}
        if settings['ZERO_NEW_PLANT_INPUTS'] == '1':
            assert all(value == 0 for value in norms.values())
        else:
            assert all(value > 0 for value in norms.values())
        assert all(torch.isfinite(value).all().item() for value in checkpoint['state_dict'].values())
        report.update(status='complete', games=4800, update=19, new_parameter_norms=norms)
    except BaseException as error:
        report.update(status='failed', error=type(error).__name__ + ': ' + str(error))
        raise
    finally:
        report['artifact_sha256'] = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in out.iterdir()
                                    if p.is_file() and p.name != 'ablation-check.json'}
        (out / 'ablation-check.json').write_text(json.dumps(report, indent=2) + '\n')
        HfApi().upload_folder(repo_id=os.environ['HF_MODEL_REPO'], folder_path=out, path_in_repo='runs/' + os.environ['RUN_NAME'])
        print(json.dumps({'stage': 'five_plant_ablation', **report}), flush=True)


if __name__ == '__main__':
    main()
