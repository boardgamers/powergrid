"""Zero-head plumbing check: every player count must reproduce parent games."""
import argparse
from pathlib import Path
import subprocess
import sys
from huggingface_hub import hf_hub_download
from strategic_collection import ROOT, read, write, digest
from arena_statistics import validate_pairs


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('zero_model', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    zero = args.zero_model.resolve()
    protocol = read(ROOT/'ai/strong/strategic-teacher-training-protocol-v1.json')
    pin = protocol['model']
    parent = Path(hf_hub_download(protocol['repo'], pin['path'], revision=pin['revision']))
    assert digest(parent) == pin['sha256']
    results = {}
    for n in range(2, 7):
        reports = {}
        for key, model, revision in [('parent', parent, pin['feature_revision']),
                                     ('zero', zero, '4.3-strategic-correction')]:
            name = f'{key}-{n}p'
            with (out/(name+'.log')).open('w') as log:
                subprocess.run([sys.executable, str(ROOT/'ai/strong/evaluate.py'), str(model),
                    '--players', str(n), '--games', str(4*n), '--workers', '4',
                    '--seed', f'strategic-correction-plumbing-v1-{n}p', '--opponent', 'economic',
                    '--output', str(out/(name+'.json'))], cwd=ROOT,
                    stdout=log, stderr=subprocess.STDOUT, check=True)
            report = read(out/(name+'.json'))
            assert report['model_feature_revision'] == report['encoder_feature_revision'] == revision
            assert report['games'] == 4*n and report['truncated'] == 0
            validate_pairs(report['results'], n)
            reports[key] = sorted(report['results'], key=lambda row: row['episode'])
        assert reports['zero'] == reports['parent'], f'Zero head changed complete-game records at {n}p'
        results[str(n)] = {'games_per_model': 4*n, 'complete_game_records_identical': True}
        print({'players': n, **results[str(n)]}, flush=True)
    write(out/'check.json', {'passed': True, 'by_player_count': results,
        'total_games': 160, 'game_truncations': 0, 'parent_sha256': digest(parent),
        'zero_model_sha256': digest(zero), 'gradients': 0, 'qualification_eligible': False,
        'scope': 'Untrained arena compatibility only. Disjoint plumbing seeds; not strength evidence.'})


if __name__ == '__main__':
    main()
