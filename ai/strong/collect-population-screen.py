"""Collect and independently verify one complete, pinned development screen."""
import argparse
import hashlib
import json
from pathlib import Path
import re

from huggingface_hub import hf_hub_download
from arena_statistics import validate_pairs, win_summary, search_summary

ROOT = Path(__file__).resolve().parents[2]


def verify_report(report, screen, checkpoint, evaluation, feature_revision='4.0-multiplayer'):
    n = screen['players']
    expected_seed = evaluation['seed_template'].format(players=n)
    expected = {
        'model_sha256': checkpoint['hashes']['latest.onnx'],
        'model_feature_revision': feature_revision,
        'encoder_feature_revision': feature_revision,
        'player_count': n, 'games': screen['games'], 'paired_seats': True,
        'candidate_search_samples': 0, 'candidate_geographic_search': False,
        'candidate_search_scope': 'all', 'candidate_search_model_proposal': True,
        'seed': expected_seed, 'deal_offset': 0, 'search_max_steps': 2400,
        'opponent_sha256': screen.get('sha256'),
    }
    for key, value in expected.items():
        if report.get(key) != value:
            raise ValueError('Wrong arena contract: ' + key)
    if screen['opponent'] != 'a260' and report['opponent'] != screen['opponent']:
        raise ValueError('Wrong heuristic opponent')
    rows = report['results']
    if len(rows) != screen['games']:
        raise ValueError('Wrong completed game count')
    validate_pairs(rows, n)
    if {r['gameSeed'] for r in rows} != {f'{expected_seed}-{i}' for i in evaluation['deal_offsets']}:
        raise ValueError('Wrong exact deal set')
    expected_role = 'snapshot0' if screen['opponent'] == 'a260' else screen['opponent']
    for r in rows:
        if r['truncated'] or any(role not in ['learner', expected_role] for role in r['roles']):
            raise ValueError('Truncated game or incorrect opposing role')
    stats = search_summary(rows)
    if not stats['search_rollouts_reported'] or any(v['truncated'] for v in stats['search_stats'].values()):
        raise ValueError('Missing or truncated search diagnostics')
    summary = win_summary(rows)
    if abs(summary['win_rate'] - report['win_rate']) > 1e-12 or report['truncated'] != 0:
        raise ValueError('Stored aggregate disagrees with raw outcomes')
    return {
        **summary, **stats,
        'by_rules': {f'{v}/{"sealed" if s else "open"}': win_summary(
            [r for r in rows if r['variant'] == v and r['sealed'] == s])
            for v in ['original', 'recharged'] for s in [False, True]},
    }


def collect(directory, revision):
    if not re.fullmatch('[0-9a-f]{40}', revision):
        raise ValueError('Pin immutable artifact revision')
    protocol = json.loads((ROOT / 'ai/strong/population-training-protocol-v1.json').read_text())
    evaluation = protocol['evaluation']
    checkpoint = json.loads((directory / 'checkpoint.json').read_text())
    if checkpoint['strict_parity'] != 'passed':
        raise ValueError('Require full export parity before collecting screen')
    result = {'checkpoint': checkpoint, 'artifact_revision': revision, 'cells': {},
              'qualification_eligible': False, 'scope': 'Fresh development deals; final test remains unused.'}
    for screen in evaluation['screens']:
        n, opponent = screen['players'], screen['opponent']
        run = f'population-v1-{checkpoint["arm"]}-u{checkpoint["update"]}-{opponent}-{n}p'
        data = Path(hf_hub_download('coyotte508/powergrid-ai-germany-v1',
            f'runs/{run}/evaluation.json', revision=revision)).read_bytes()
        report = json.loads(data)
        summary = verify_report(report, screen, checkpoint, evaluation)
        file = directory / f'{opponent}-{n}p.json'
        file.write_bytes(data)
        result['cells'][f'{opponent}/{n}p'] = {
            'artifact_sha256': hashlib.sha256(data).hexdigest(), 'run': run, **summary}
    (directory / 'summary.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({cell: {'games': s['games'], 'win_rate': s['win_rate']}
                      for cell, s in result['cells'].items()}))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('directory', type=Path)
    p.add_argument('revision')
    a = p.parse_args()
    collect(a.directory.resolve(), a.revision)
