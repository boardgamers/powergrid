"""One HF-only training update to validate new inputs, mixed opponents and export."""
import hashlib
import json
import os
from pathlib import Path
import runpy
import subprocess
import sys
import torch
from huggingface_hub import HfApi


def main():
    if os.environ.get('POWERGRID_TRAINING_PLATFORM') != 'hf-job':
        raise ValueError('Gradient smoke check runs only on HF Jobs')
    protocol = json.loads(Path('ai/strong/five-plant-smoke-protocol-v1.json').read_text())
    for key, value in protocol['env'].items():
        if os.environ.get(key) != value:
            raise ValueError('Configuration mismatch: ' + key)
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    out = Path('ai/runs') / os.environ['RUN_NAME']
    out.mkdir(parents=True, exist_ok=True)
    report = dict(qualification_eligible=False, protocol_sha256=hashlib.sha256(
        Path('ai/strong/five-plant-smoke-protocol-v1.json').read_bytes()).hexdigest(),
        source_archive=os.environ['SOURCE_ARCHIVE'], source_revision=os.environ['SOURCE_REVISION'],
        source_sha256=os.environ['SOURCE_SHA256'])
    try:
        runpy.run_path('ai/strong/train.py', run_name='__main__')
        metrics = json.loads((out / 'metrics.json').read_text())
        training = [r for r in metrics if r.get('stage') == 'train']
        assert len(training) == 1 and training[0]['update'] == 0
        row = training[0]
        assert row['episodes'] == 80 and row['truncated'] == 0
        assert set(row['by_player_count']) == set('23456')
        assert all(x['episodes'] == 16 and x['truncated'] == 0 for x in row['by_player_count'].values())
        assert row['search_rollouts_reported'] and row['search_stats']
        assert all(x['truncated'] == 0 for x in row['search_stats'].values())
        assert sum(row['opponent_seats'].values()) == 320
        assert all(row['opponent_seats'].get(f'frozen{i}', 0) > 0 for i in range(3))
        checkpoint = torch.load(out / 'latest.pt', map_location='cpu', weights_only=True)
        assert checkpoint['architecture'] == 'multiplayer_ordered_plants'
        assert checkpoint['feature_revision'] == '4.1-five-plants'
        assert checkpoint['state_dim'] == 1215 and checkpoint['action_dim'] == 100
        assert checkpoint['initial_sha256'] == protocol['env']['INIT_SHA256']
        assert checkpoint['initial_transfer']['trained'] is False
        norms = {key: checkpoint['state_dict'][key].norm().item()
                 for key in ['extra_player.weight', 'extra_action.weight']}
        assert all(value > 0 for value in norms.values()), norms
        assert all(torch.isfinite(value).all().item() for value in checkpoint['state_dict'].values())
        subprocess.run([sys.executable, 'ai/strong/check-export.py', str(out / 'latest.pt'),
                        str(out / 'latest.onnx'), 'ai/strong/fixtures/multiplayer-serving-v1.jsonl',
                        '--output', str(out / 'export-check.json')], check=True)
        report.update(status='complete', training=row, new_parameter_norms=norms,
                      export=json.loads((out / 'export-check.json').read_text()))
    except BaseException as error:
        report.update(status='failed', error=type(error).__name__ + ': ' + str(error))
        raise
    finally:
        report['artifact_sha256'] = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                                    for p in out.iterdir() if p.is_file() and p.name != 'smoke-check.json'}
        (out / 'smoke-check.json').write_text(json.dumps(report, indent=2) + '\n')
        HfApi().upload_folder(repo_id=os.environ['HF_MODEL_REPO'], folder_path=out,
                             path_in_repo='runs/' + os.environ['RUN_NAME'])
        print(json.dumps({'stage': 'five_plant_smoke', **report}), flush=True)


if __name__ == '__main__':
    main()
