"""Check actual existing metadata and incomplete-grid refusal, without raw re-audit."""
import json
from pathlib import Path
from unittest.mock import patch

import current_auction_recovery_authentication_v2 as a

OUT = a.ROOT/'ai/runs/current-auction-recovery-authentication-preflight-v2'
REPORT = a.remaining.STRONG/'current-auction-recovery-authentication-preflight-v2.json'


def main():
    a.require(not OUT.exists() and not REPORT.exists(), 'Inspect existing authentication preflight')
    log = a.ROOT/'ai/runs/current-auction-recovery-authentication-tests-v2-first.log'
    a.require('Ran 16 tests' in log.read_text() and log.read_text().rstrip().endswith('OK'), 'Authentication tests incomplete')
    OUT.mkdir()
    a.remaining.save(OUT/'intent.json', {'purpose':'authenticate existing first audit and real incomplete-grid refusal',
        'new_jobs':0,'new_games':0,'new_inference':0,'raw_reaudit':False})
    with patch.object(a,'context',wraps=a.context) as context_spy, patch.object(a,'authenticate',wraps=a.authenticate) as review_spy:
        try: a.authenticate_complete()
        except ValueError as error: rejection = str(error)
        else: raise AssertionError('Current incomplete study unexpectedly admitted')
        a.require(rejection == 'Incomplete recovery coverage; do not read outcomes', 'Wrong complete-study rejection')
        a.require(context_spy.call_count == review_spy.call_count == 0, 'Incomplete study loaded comparison reviews')
    current = a.context(); inventory = a.inventory(current['plan'])
    reference = next(r for r in inventory['available'] if r['name'] == a.first.worker.FAILED_NAME)
    authenticated = a.authenticate(reference,current)
    a.require(authenticated['job_id'] == a.remaining.worker.FIRST_HANDLE and authenticated['games'] == 16,
        'Known completed first recovery did not authenticate')
    source = current['sources']['first_execution']; guards = {}; observations = {}
    for row in current['original_source']['rows']:
        if row['name'] not in current['plan']['fixed_recovery_order'] or row['name'] == a.first.worker.FAILED_NAME: continue
        folder = a.remaining.OUT/'jobs'/a.remaining.worker.attempt_name(row['name'])
        if not (folder/'launch.json').exists(): continue
        guard = a.remaining.checked_guard(folder,source,row)
        check_path = sorted(folder.joinpath('checks').glob('*.json'))[-1]; check = a.read(check_path)
        a.require(check['job_id'] == guard['job_id'] and check['attempt_id'] == guard['attempt_id']
            and check['original_name'] == row['name'] and check['public_configuration_verified'] is True
            and check['timeout_seconds'] == 86400 and check['flavor'] == 'cpu-upgrade' and check['image'] == a.first.IMAGE
            and check['bootstrap_sha256'] == a.first.sha_text(a.remaining.bootstrap())
            and check['environment_sha256'] == a.object_hash(a.remaining.public_environment(source,row)), 'Saved actual HF binding differs')
        guards[str((folder/'launch.json').relative_to(a.ROOT))] = a.digest(folder/'launch.json')
        observations[str(check_path.relative_to(a.ROOT))] = a.digest(check_path)
    a.require(len(guards) == 64, 'Expected original first batch; inspect changed coverage')
    paths = [Path(__file__),Path(a.__file__),a.remaining.STRONG/'test_current_auction_recovery_authentication_v2.py',log,
        a.first.RESULT,a.first.SOURCE,a.remaining.SOURCE,a.first.OUT/'launch.json',a.first.OUT/'launch-intent.json',
        a.first.OUT/'terminal.json',a.first.OUT/'original-recovery.log',
        a.first.OUT/'artifacts/manifest.json',a.first.OUT/'artifacts/attempt.json',a.first.OUT/'artifacts/run-status.json',
        a.first.OUT/'artifacts/raw/manifest.json']
    report = {'passed':True,'tests':16,'unit_positive_controls':'synthetic metadata; no games or remote APIs',
        'actual_first_receipt_authenticated':True,'first_job_id':authenticated['job_id'],
        'first_review_sha256':reference['review_sha256'],'first_raw_games_previously_audited':16,
        'raw_audit_repeated':False,'known_original_failure_preserved':a.first.worker.FAILED_HANDLE,
        'actual_remaining_launch_bindings_checked':len(guards),'live_status_refetched':False,
        'actual_incomplete_comparison_rejection':rejection,'comparison_context_calls_before_rejection':0,
        'comparison_review_loader_calls_before_rejection':0,'inventory':a.current_inventory_summary(current),
        'input_hashes':{**{str(p.relative_to(a.ROOT)):a.digest(p) for p in paths},**guards,**observations},
        'coverage_plan_input_hashes':current['plan']['input_hashes'],
        'new_jobs':0,'new_games':0,'new_inference':0,'statistics_computed':False,'candidate_selected':False,
        'qualified':False,'reserved_final_seeds_used':False,'goal_status':'active'}
    a.remaining.save(REPORT,report)
    print(json.dumps({k:report[k] for k in ('passed','tests','actual_first_receipt_authenticated',
        'actual_remaining_launch_bindings_checked','actual_incomplete_comparison_rejection','inventory','new_games')}),flush=True)


if __name__=='__main__':main()
