"""Verify actual admitted failure routing without gameplay or repeated raw audits."""
from collections import Counter
from pathlib import Path
import json
from unittest.mock import patch

import current_auction_attempt_authentication_v4 as a
import current_auction_attempt_comparison_v4 as c

OUT = a.ROOT/'ai/runs/current-auction-failure-routing-preflight-v4'
REPORT = a.ROOT/'ai/strong/current-auction-attempt-authentication-preflight-v4.json'


def main():
    a.require(not OUT.exists() and not REPORT.exists(), 'Inspect prior routing preflight')
    plan = a.coverage.actual_plan(); routes = a.actual_routes(plan); found = a.inventory(plan, routes)
    a.require(not found['complete'], 'Incomplete preflight requires missing coverage')
    original = a.prior_routing.actual_routes(plan)
    changed = {name for name in routes if routes[name] != original[name]}
    a.require(changed == set(a.failed.failed_records()) and len(changed) == 10, 'Unrelated original route changed')
    with patch.object(c, 'check_inputs') as inputs, patch.object(c, 'make_cases') as cases, \
         patch.object(c, 'parallel_audit') as audits, patch.object(c.statistics, 'analyze') as stats:
        try: c.compare(OUT/'forbidden-comparison.json')
        except ValueError as error:
            a.require(str(error) == 'Incomplete recovery coverage; do not read outcomes', 'Unexpected refusal')
        else: raise ValueError('Incomplete failure recovery admitted')
        for fn in (inputs, cases, audits, stats): fn.assert_not_called()
    current = a.context(plan, routes)
    reference = next(r for r in found['available'] if r['backend'] == 'bucket_remaining_v3')
    checked = a.authenticate(reference, current)
    a.require(checked['review']['audit']['all_receipts_verified'], 'Existing bucket binding incomplete')
    log = a.ROOT/'ai/runs/current-auction-failure-routing-tests-v4-first.log'
    a.require('Ran 44 tests' in log.read_text() and log.read_text().rstrip().endswith('OK'), 'Tests incomplete')
    prior = a.read(a.ROOT/'ai/strong/current-auction-attempt-authentication-preflight-v3.json')
    pins = {**prior['frozen_input_hashes'], **plan['input_hashes']}
    paths = [Path(a.__file__), Path(c.__file__), Path(__file__), Path(a.prior_routing.__file__),
        Path(a.failed.__file__), Path(a.failed.packer.__file__), a.failed.SOURCE, a.failed.DECISION,
        a.failed.PRE/'prepared.json', a.failed.PREFLIGHT, a.failed.PREP_EVIDENCE, a.failed.FAILURES,
        a.ROOT/'ai/strong/test_current_auction_attempt_authentication_v4.py',
        a.ROOT/'ai/strong/test_current_auction_attempt_comparison_v4.py', log]
    pins.update({str(p.relative_to(a.ROOT)): a.digest(p) for p in paths})
    a.require(all(a.digest(a.ROOT/p) == sha for p, sha in pins.items()), 'Frozen routing inputs changed')
    OUT.mkdir();a.failed.save(OUT/'intent.json', {'input_hashes': pins, 'new_jobs': 0, 'new_games': 0})
    a.failed.save(OUT/'routes.json', routes);a.failed.save(OUT/'inventory.json', found)
    report = {'passed': True, 'checked_at': a.failed.now(), 'code_sha256': a.digest(a.__file__),
        'comparison_sha256': a.digest(c.__file__), 'frozen_input_hashes': pins, 'tests_passed': 44,
        'canonical_shards': plan['canonical_shards'], 'canonical_games': plan['canonical_games'],
        'routes_by_backend': dict(Counter(routes.values())), 'changed_routes': sorted(changed),
        'unchanged_other_routes': len(routes)-len(changed), 'previous_failed_attempts': a.failed.failed_records(),
        'actual_existing_bucket_reference': reference, 'actual_existing_bucket_binding_passed': True,
        'incomplete_comparison_rejected_before_context_reviews_audits_statistics': True,
        'inventory': a.inventory_summary(found), 'failure_backend_real_completion_pending': True,
        'raw_reaudits': 0, 'new_jobs': 0, 'new_games': 0, 'inference_requests': 0,
        'statistics_admitted': False, 'candidate_selected': False, 'qualified': False, 'reserved_final_seeds_used': False}
    a.failed.save(REPORT, report)
    _, _, _, comparison_pins = c.check_inputs(plan)
    a.failed.save(OUT/'comparison-input-check.json', {'passed': True, 'pins': comparison_pins, 'new_games': 0})
    print(json.dumps({'passed': True, 'routes': report['routes_by_backend'], 'preserved_failures': len(changed),
        'comparison_input_pins': len(comparison_pins), 'raw_reaudits': 0, 'new_games': 0}), flush=True)


if __name__ == '__main__': main()
