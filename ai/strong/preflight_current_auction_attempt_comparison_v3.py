"""Check mixed comparison plumbing on existing raw artifacts, never new games."""
from pathlib import Path
import json
import time
from unittest.mock import patch

import current_auction_attempt_comparison_v3 as c

OUT = c.ROOT/'ai/runs/current-auction-attempt-comparison-preflight-v3'
REPORT = c.ROOT/'ai/strong/current-auction-attempt-comparison-preflight-v3.json'


def main():
    c.require(not OUT.exists() and not REPORT.exists(), 'Inspect existing preflight intent/outcome')
    plan = c.auth.coverage.actual_plan(); routes = c.auth.actual_routes(plan)
    found = c.auth.inventory(plan, routes)
    c.require(not found['complete'], 'Incomplete-gate preflight requires actual missing coverage')
    with patch.object(c, 'check_inputs') as inputs, patch.object(c, 'make_cases') as cases, \
         patch.object(c, 'parallel_audit') as audit, patch.object(c.statistics, 'analyze') as stats:
        try:
            c.compare(OUT/'forbidden-comparison.json')
        except ValueError as error:
            c.require(str(error) == 'Incomplete recovery coverage; do not read outcomes', 'Unexpected refusal')
        else:
            raise ValueError('Incomplete study admitted')
        for fn in (inputs, cases, audit, stats): fn.assert_not_called()
    _, _, _, pins = c.check_inputs(plan)
    names = [next(s['name'] for s in plan['slots'] if s['kind'] == 'preserved_original'
                  and s['original']['stage'] == 'ERROR')]
    for backend in ('timeout_v2', 'retained_v2', 'bucket_first_v3', 'bucket_remaining_v3'):
        names.append(next(r['name'] for r in found['available'] if r['backend'] == backend))
    subset = {**plan, 'slots': [s for s in plan['slots'] if s['name'] in names]}
    refs = {r['name']: r for r in found['available']}
    cases, _ = c.make_cases(subset, routes, refs)
    test = c.ROOT/'ai/strong/test_current_auction_attempt_comparison_v3.py'
    log = c.ROOT/'ai/runs/current-auction-attempt-comparison-tests-v3-first.log'
    c.require('Ran 15 tests' in log.read_text() and log.read_text().rstrip().endswith('OK'), 'Tests incomplete')
    pins.update({str(p.relative_to(c.ROOT)): c.digest(p) for p in (test, Path(__file__), log)})
    OUT.mkdir()
    c.write_new(OUT/'intent.json', {'cases': cases, 'input_hashes': pins,
        'new_games': 0, 'inference_requests': 0, 'statistics_admitted': False})
    started = time.perf_counter()
    audited = c.match_audits(cases, c.parallel_audit(cases))
    c.require(all(c.digest(c.ROOT/p) == sha for p, sha in pins.items()), 'Preflight inputs changed')
    report = {'passed': True, 'checked_at': c.auth.remaining.now(),
        'complete_comparison_executed': False, 'incomplete_gate_rejected_before_context_and_reviews': True,
        'actual_backends_checked': [r['backend'] for r in cases], 'independent_audits': audited,
        'jobs_reaudited': len(audited), 'existing_games_reaudited': sum(r['games'] for r in audited.values()),
        'raw_audit_wall_seconds': time.perf_counter()-started,
        'all_saved_full_reviews_exact': True, 'workers': 4, 'tests_passed': 15,
        'input_hashes': pins, 'code_sha256': c.digest(c.__file__),
        'inventory': c.auth.inventory_summary(found), 'remaining_bucket_actual_authentication_verified': True,
        'new_jobs': 0, 'new_games': 0, 'inference_requests': 0, 'statistics_admitted': False,
        'candidate_selected': False, 'qualified': False, 'reserved_final_seeds_used': False}
    c.write_new(REPORT, report)
    print(json.dumps({k: report[k] for k in ('passed', 'actual_backends_checked', 'jobs_reaudited',
        'existing_games_reaudited', 'raw_audit_wall_seconds', 'new_games', 'statistics_admitted')}), flush=True)


if __name__ == '__main__': main()
