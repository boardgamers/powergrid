"""Save canonical metadata and demonstrate incomplete-study rejection.

Does not read game outcomes, submit jobs, modify the running recovery or admit
the remaining grid. No real positive complete-coverage claim is made.
"""
import json
from pathlib import Path

import current_auction_recovery_coverage_v2 as coverage
import manage_current_auction_resource_recovery_v2 as first

OUT=coverage.ROOT/'ai/runs/current-auction-recovery-coverage-preflight-v2'
REPORT=coverage.ROOT/'ai/strong/current-auction-recovery-coverage-preflight-v2.json'


def main():
    require=coverage.require
    require(not OUT.exists() and not REPORT.exists(),'Inspect prior coverage preflight')
    first.prepared()  # Recheck the live attempt's controls and all original pins.
    plan=coverage.actual_plan()
    expected={'preserved_original':19764,'failed_original_recovery':16,'first_execution':7100}
    require(plan['games_by_disposition']==expected,'Unexpected real game partition')
    require(plan['original_hf_status_counts']=={'COMPLETED':617,'ERROR':4},'Original failures were lost')
    load_calls=[]
    def must_not_load(value):
        load_calls.append(value);raise AssertionError('Incomplete coverage must reject before review/outcome access')
    try:coverage.require_complete_assignments(plan,[],must_not_load)
    except ValueError as error:rejection=str(error)
    else:raise AssertionError('Incomplete real study admitted')
    require(rejection=='Incomplete recovery coverage; do not read outcomes' and not load_calls,
        'Incomplete actual confirmation was not rejected before reads')
    guard=first.read(first.OUT/'launch.json')
    source=first.read(first.PRE/'bundle/original-source.json')
    row=next(r for r in source['rows'] if r['name']==first.worker.FAILED_NAME)
    assignment={'name':row['name'],'original_row_sha256':coverage.object_hash(row),
        'job_id':guard['job_id'],'attempt_id':guard['attempt_id'],'original_failed_handle':guard['original_failed_handle'],
        'stage':'RUNNING','verified':False,'review_sha256':None}
    try:coverage.require_complete_assignments(plan,[assignment],must_not_load)
    except ValueError as error:live_rejection=str(error)
    else:raise AssertionError('One live attempt was treated as full coverage')
    require(live_rejection==rejection and not load_calls,'Live attempt bypassed whole-study gate')
    log=coverage.ROOT/'ai/runs/current-auction-recovery-coverage-tests-v2-handle-pin.log'
    require('Ran 12 tests' in log.read_text() and log.read_text().rstrip().endswith('OK'),'Coverage tests incomplete')
    OUT.mkdir();coverage.worker.save(OUT/'plan.json',plan)
    report={'passed':True,'tests':12,'positive_controls':'small synthetic coverage; review loader mocked',
        'actual_canonical_shards':plan['canonical_shards'],'actual_canonical_games':plan['canonical_games'],
        'actual_shards_by_disposition':plan['shards_by_disposition'],'actual_games_by_disposition':plan['games_by_disposition'],
        'original_hf_status_counts':plan['original_hf_status_counts'],'original_failed_handle':first.worker.FAILED_HANDLE,
        'current_attempt_handle':guard['job_id'],'actual_incomplete_study_rejected':rejection,
        'actual_live_attempt_insufficient':live_rejection,'review_loader_calls':0,'game_outcome_files_read':0,
        'plan_sha256':coverage.digest(OUT/'plan.json'),'canonical_game_keys_sha256':plan['game_keys_sha256'],
        'input_hashes':{**plan['input_hashes'],str(Path(__file__).relative_to(coverage.ROOT)):coverage.digest(__file__),
            str(log.relative_to(coverage.ROOT)):coverage.digest(log),
            'ai/strong/test_current_auction_recovery_coverage_v2.py':coverage.digest(coverage.ROOT/'ai/strong/test_current_auction_recovery_coverage_v2.py')},
        'new_hf_jobs':0,'new_games':0,'new_inference':0,'remaining_grid_admitted':False,
        'actual_complete_coverage_verified':False,'statistics_admitted':False,'qualified':False,'reserved_final_seeds_used':False,
        'previous_goal_turn_classification':'progress','current_goal_turn_classification':'progress','goal_status':'active'}
    coverage.worker.save(REPORT,report)
    print(json.dumps({k:report[k] for k in ('passed','tests','actual_canonical_shards','actual_canonical_games',
        'actual_games_by_disposition','actual_incomplete_study_rejected','review_loader_calls','new_hf_jobs')}),flush=True)


if __name__=='__main__':main()
