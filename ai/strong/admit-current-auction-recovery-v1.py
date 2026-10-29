"""Admit unchanged remaining games only after auditing all first 64 originals.

Reads the exact original HF handles; never submits or replays games. Admission
is explicit, exclusive and outcome-independent, with ERROR retained as ERROR.
"""
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path

from huggingface_hub import HfApi
from public_policy_development_job_v1 import digest, read

ROOT = Path(__file__).resolve().parents[2]
INITIAL = ROOT/'ai/runs/current-auction-confirmation-recovery-initial-collection-v1.json'


def main():
    spec = importlib.util.spec_from_file_location('recovery_manager',
        Path(__file__).with_name('manage-current-auction-confirmation-recovery-v1.py'))
    manager = importlib.util.module_from_spec(spec); spec.loader.exec_module(manager)
    assert not manager.ADMISSION.exists() and not INITIAL.exists(), 'Inspect existing admission outcome'
    assert not (ROOT/'ai/runs/current-auction-confirmation-recovery-v1/state.json').exists()
    old_path = ROOT/'ai/runs/current-auction-grid-coordinator-v1/state.json'; old = read(old_path)
    assert old['stage'] == 'stopped_for_inspection' and old['submitted_jobs'] == 64
    assert not Path(f"/proc/{old['pid']}/cmdline").exists(), 'Original owner is still present'
    with manager.base.exclusive_operation():
        source = manager.source_checked()
        report_path = manager.OUT/'collection-state-recovered-v1.json'
        report_sha256 = digest(report_path)
        report = read(report_path)
        assert report['verified_jobs'] == len(report['jobs']) == 64 and not report['complete']
        assert report['source_sha256'] == digest(manager.SOURCE)
        assert report['recovered_original_errors'] == 1
        guards = list(manager.OUT.glob('*/launch.json'))
        assert len(guards) == 64 and len({j['job_id'] for j in report['jobs']}) == 64
        planned = {r['name']:r for r in source['rows']}
        stages = Counter()
        for job in report['jobs']:
            folder = manager.OUT/job['name']; row = planned[job['name']]
            assert manager.cached(folder,source,row) == job and manager.recovery.complete_data(job)
            stages[job['stage']] += 1
        assert stages == {'COMPLETED':63,'ERROR':1}
        failed = next(j for j in report['jobs'] if j['stage']=='ERROR')
        assert failed['job_id'] == '6ae2847a41e90535df77edf5' and failed['review']['games'] == 48
        assert failed['review']['audit']['counts']['decisions'] == 6486
        assert failed['evidence'] == read(ROOT/'ai/strong/current-auction-recovery-preflight-v1.json')['original_archive']
        api = HfApi()
        def inspect(job):
            stage = api.inspect_job(job_id=job['job_id']).status.stage
            assert stage == job['stage'], 'Original HF status changed; inspect rather than resubmit'
            return {'job_id':job['job_id'],'name':job['name'],'stage':stage}
        with ThreadPoolExecutor(max_workers=8) as pool:
            statuses = list(pool.map(inspect,report['jobs']))
        assert digest(report_path) == report_sha256, 'Collection changed during admission'
        manager.write_new(INITIAL,report)
        admission = {'admitted':True,'created_at':datetime.now(timezone.utc).isoformat(),
            'rule':manager.recovery.RULE,'no_game_reruns':True,'source_sha256':digest(manager.SOURCE),
            'readiness_sha256':digest(manager.READINESS),'planned_games':26880,'planned_jobs':944,
            'max_active_jobs':64,'initial_collection':str(INITIAL.relative_to(ROOT)),
            'initial_collection_sha256':digest(INITIAL),'original_handles':sorted(j['job_id'] for j in report['jobs']),
            'original_guard_hashes':{str(p.relative_to(ROOT)):digest(p) for p in sorted(guards)},
            'stopped_owner_state':str(old_path.relative_to(ROOT)), 'stopped_owner_state_sha256':digest(old_path),
            'stopped_owner_pid':old['pid'],'fresh_original_hf_statuses':statuses,
            'initial_audited_games':sum(j['review']['games'] for j in report['jobs']),
            'original_hf_stage_counts':dict(stages),'original_error_retained':True,
            'admission_helper_sha256':digest(__file__),
            'rationale':'Complete original terminal data only; exact post-terminal shutdown timeout, all raw decisions and execution bindings audited. Every game retained and ERROR preserved. Apply this same data/error rule regardless of outcomes to future original jobs. No other failure admitted, no reruns or replacements. Frozen source, policies, statistical protocol, budget and seeds are unchanged.',
            'new_jobs':0,'new_games':0,'new_gradients':0,'qualified':False,'reserved_final_seeds_used':False}
        manager.write_new(manager.ADMISSION,admission)
        assert manager.admitted() == admission
    print(json.dumps({'admitted':True,'initial_verified_jobs':64,'initial_audited_games':admission['initial_audited_games'],
        'original_hf_stages':dict(stages),'remaining_never_submitted_jobs':len(source['rows'])-64,
        'admission_sha256':digest(manager.ADMISSION),'new_jobs':0}),flush=True)


if __name__ == '__main__': main()
