"""Merge disjoint arena shards without averaging confidence intervals or percentiles.

Input paths/hashes and run names remain in the output. This assembles evidence;
only verify-final.py can apply the frozen qualification protocol.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path

from arena_statistics import search_summary, validate_pairs, win_summary

IDENTITY = (
    'player_count', 'model_sha256', 'model_feature_revision', 'encoder_feature_revision',
    'opponent_sha256', 'opponent_feature_revision', 'paired_seats', 'async_rollout',
    'candidate_search_samples', 'search_max_steps', 'candidate_search_scope',
    'candidate_geographic_search', 'candidate_search_model_proposal', 'seed',
    'source', 'arena_runner_sha256', 'model_repository_revision', 'opponent_repository_revision',
)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def merge(paths):
    require(bool(paths), 'No arena shards')
    inputs = [(Path(p), json.loads(Path(p).read_text())) for p in paths]
    inputs.sort(key=lambda item: item[1]['deal_offset'])
    first = inputs[0][1]
    require(all(k in first for k in IDENTITY), 'Missing arena identity/provenance')
    require(all(first['source'].get(k) for k in ['archive', 'revision', 'sha256']), 'Missing source pin')
    require(first['arena_runner_sha256'] and first['model_repository_revision'], 'Missing runtime/model pin')
    n = first['player_count']; paired = 4*n
    offset = 0; rows = []; shards = []; run_names = set()
    for path, report in inputs:
        require(all(k in report and report[k] == first[k] for k in IDENTITY), 'Mixed arena identity/provenance')
        # Download cache paths may differ for a frozen opponent. Its bytes and
        # repository revision above are the identity; heuristic names are exact.
        if not first['opponent_sha256']:
            require(report['opponent'] == first['opponent'], 'Mixed opponent')
        require(report['paired_seats'] is True and report['async_rollout'] is False, 'Wrong arena scheduling')
        require(report['deal_offset'] == offset, 'Duplicate, missing or overlapping shard deals')
        games = report['games']; actual = report['results']
        require(type(games) is int and games > 0 and games % paired == 0 and len(actual) == games,
                'Incomplete shard game count')
        validate_pairs(actual, n)
        require({r['episode'] for r in actual} == set(range(offset*paired, offset*paired+games)),
                'Wrong shard episode set')
        require({r['gameSeed'] for r in actual} == {f"{first['seed']}-{i}" for i in range(offset, offset+games//paired)},
                'Wrong shard deal set')
        role = 'snapshot0' if first['opponent_sha256'] else first['opponent']
        for row in actual:
            e = row['episode']
            require(row['gameSeed'] == f"{first['seed']}-{e//paired}"
                    and row['seat'] == (e//4) % n
                    and row['variant'] == ('recharged' if e % 2 else 'original')
                    and row['sealed'] == (e % 4 < 2), 'Episode pairing metadata mismatch')
            require(not row['truncated'], 'Truncated game')
            require(all(r in ['learner', role] for r in row['roles']), 'Wrong opponent roles')
        search = search_summary(actual)
        require(search['search_rollouts_reported'], 'Missing search diagnostics')
        require(all(s['truncated'] == 0 for s in search['search_stats'].values()), 'Truncated search rollouts')
        expected_roles = ({'learner'} if first['candidate_search_samples'] else set()) | ({role} if role in ['search', 'search_geo'] else set())
        require(set(search['search_stats']) == expected_roles
                and all(s['evaluations'] > 0 for s in search['search_stats'].values()), 'Missing or unexpected search execution')
        summary = win_summary(actual)
        require(abs(report['win_rate']-summary['win_rate']) < 1e-12 and report['truncated'] == 0,
                'Stored summary disagrees with raw games')
        require(math.isfinite(report['seconds']) and report['seconds'] > 0, 'Invalid runtime')
        require(report['run_name'] not in run_names, 'Duplicate run name')
        run_names.add(report['run_name'])
        shards.append({'path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                       'run_name': report['run_name'], 'deal_offset': offset, 'games': games,
                       'seconds': report['seconds'], 'inference_p95_ms': report['inference_p95_ms'],
                       'engine_workers': report['engine_workers']})
        rows.extend(actual); offset += games//paired
    rows.sort(key=lambda row: row['episode'])
    result = {k: first[k] for k in IDENTITY}
    result.update(opponent=first['opponent'], model=first['model'], chance_win_rate=1/n, deal_offset=0,
                  results=rows, shards=shards, shard_seconds_sum=sum(x['seconds'] for x in shards),
                  qualification_checked=False)
    result.update(win_summary(rows)); result.update(search_summary(rows))
    result['by_rules'] = [{'variant': v, 'sealed': s,
                          **win_summary([r for r in rows if r['variant'] == v and r['sealed'] == s])}
                         for v in ['original', 'recharged'] for s in [False, True]]
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('reports', nargs='+', type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    result = merge(args.reports)
    with args.output.open('x') as handle:
        json.dump(result, handle, indent=2); handle.write('\n')
    print(json.dumps({k: result[k] for k in ['games', 'independent_seeds', 'win_rate', 'qualification_checked']}))
