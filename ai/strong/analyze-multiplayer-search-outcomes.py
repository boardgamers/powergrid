"""Describe the already completed 3–6p paired hybrid experiment; no new games."""
import argparse
from pathlib import Path

import numpy as np

from search_transfer import ROOT, read, write, digest, module

manager = module('multiplayer_outcome_verification', 'manage-multiplayer-search-transfer.py')
terminal = module('paired_terminal_metrics', 'analyze-search-transfer-outcomes.py')


def analyze(output):
    assert not output.exists(), 'Preserve previous diagnostic outputs'
    protocol = read(manager.PROTOCOL)
    source = read(manager.SOURCE)
    comparison = read(ROOT/'ai/strong/multiplayer-search-transfer-results-v1.json')
    assert comparison['all_counts_verified'] and comparison['verified_players'] == [3, 4, 5, 6]
    assert comparison['protocol_sha256'] == digest(manager.PROTOCOL)
    models, provenance = {}, {}
    for key in protocol['models']:
        models[key], provenance[key] = {}, {}
        for n in [3, 4, 5, 6]:
            directory = manager.FULL_ROOT/f'{key}-{n}p'
            verified = read(directory/'verified.json')
            assert verified['verified'] and verified['key'] == key and verified['players'] == n
            assert verified['smoke'] is False and verified['qualification_eligible'] is False
            assert verified['source_revision'] == source['revision']
            assert verified['source_sha256'] == source['sha256']
            assert verified['protocol_sha256'] == digest(manager.PROTOCOL)
            for name, sha in verified['artifacts'].items():
                assert Path(name).name == name and digest(directory/name) == sha
            checked = manager.verify_local(directory, key, n, False)
            manager.checks.same_summary(checked, verified['summary'])
            manager.checks.same_summary(checked, comparison['summaries'][key][str(n)])
            previous = comparison['provenance'][key][str(n)]
            assert previous['verified_sha256'] == digest(directory/'verified.json')
            assert previous['revision'] == verified['revision'] and previous['prefix'] == verified['prefix']
            guided, raw = [read(directory/(name+'.json'))['results'] for name in ['search', 'baseline']]

            def describe(a, b):
                result = terminal.paired_changes(a, b, protocol)
                result['means'] = {arm: {name: float(np.mean([terminal.metrics(row)[name] for row in rows]))
                    for name in terminal.metrics(rows[0])} for arm, rows in [('raw', b), ('search', a)]}
                return result

            result = {'overall': describe(guided, raw), 'rules': {}}
            for variant in ['original', 'recharged']:
                for sealed in [False, True]:
                    select = lambda rows: [r for r in rows if r['variant'] == variant and r['sealed'] == sealed]
                    rule = variant+('/sealed' if sealed else '/open')
                    result['rules'][rule] = describe(select(guided), select(raw))
            for label, view in [('overall', result['overall']), *result['rules'].items()]:
                existing = checked['search_minus_raw']['overall' if label == 'overall' else 'rules']
                if label != 'overall':
                    existing = existing[label]
                assert abs(view['terminal_changes']['win_credit']['mean_search_minus_raw']-
                           existing['win_share_difference']) < 1e-12
                assert view['games_per_arm'] == existing['games_per_model']
                assert view['independent_deals'] == existing['independent_deals'] == 8
            models[key][str(n)] = result
            provenance[key][str(n)] = {**previous, 'guided_sha256': digest(directory/'search.json'),
                                       'raw_sha256': digest(directory/'baseline.json')}
            print({'model': key, 'players': n, 'games_per_arm': len(guided),
                   'paired_win_change': result['overall']['terminal_changes']['win_credit']}, flush=True)
    result = {'players': [3,4,5,6], 'models': models, 'provenance': provenance,
        'protocol_sha256': digest(manager.PROTOCOL), 'source': source,
        'comparison_sha256': digest(ROOT/'ai/strong/multiplayer-search-transfer-results-v1.json'),
        'analysis_code': {str(path.relative_to(ROOT)): digest(path) for path in [Path(__file__),
            ROOT/'ai/strong/analyze-search-transfer-outcomes.py', ROOT/'ai/strong/manage-multiplayer-search-transfer.py']},
        'new_games': 0, 'gradients': False, 'qualification_eligible': False,
        'reserved_final_seeds_used': False,
        'scope': ('Descriptive paired terminal outcomes on all completed older hybrid development cells. '
                  'Eight independent deals per cell; whole-deal marginal bootstrap intervals, no multiplicity correction. '
                  'Failure categories overlap. Terminal differences do not establish the causal phase or decision. '
                  'No new model, games, selection or qualification; not comparable directly with newer development seeds.')}
    write(output, result)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--output', type=Path, required=True)
    analyze(parser.parse_args().output)
