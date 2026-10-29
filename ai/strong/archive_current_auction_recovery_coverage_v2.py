"""Archive coverage engineering and actual metadata proof, without execution."""
import json
from pathlib import Path
import shutil

from huggingface_hub import HfApi
from policy_iteration_evidence_archive import upload_evidence
import current_auction_recovery_coverage_v2 as c
import manage_current_auction_resource_recovery_v2 as first

OUT=c.ROOT/'ai/runs/current-auction-recovery-coverage-evidence-v2'
REPORT=c.ROOT/'ai/strong/current-auction-recovery-coverage-preflight-v2.json'
DESCRIPTOR=c.ROOT/'ai/strong/current-auction-recovery-coverage-evidence-v2.json'
PLAN=c.ROOT/'ai/runs/current-auction-recovery-coverage-preflight-v2/plan.json'


def main():
    intent=OUT.with_suffix('.intent.json');outcome=OUT.with_suffix('.outcome.json')
    c.require(not any(p.exists() for p in (OUT,intent,outcome,OUT.with_suffix('.tgz'),DESCRIPTOR)),
        'Inspect previous archive outcome before retrying')
    report=c.read(REPORT);first.prepared()
    c.require(report['passed'] and report['tests']==12 and report['plan_sha256']==c.digest(PLAN)
        and report['review_loader_calls']==report['game_outcome_files_read']==0,'Coverage report differs')
    c.require(all(c.digest(c.ROOT/p)==sha for p,sha in report['input_hashes'].items()),'Coverage inputs changed')
    paths={Path(__file__),REPORT,PLAN,c.ROOT/'ai/RESUME.md',
        c.ROOT/'ai/CURRENT-AUCTION-RECOVERY-COVERAGE-2026-10-29.md',c.ROOT/'ai/strong/experiments.json',
        c.ROOT/'ai/strong/current-auction-first-recovery-evidence-v2.json',
        c.ROOT/'ai/runs/current-auction-recovery-coverage-tests-v2-first.log'}
    paths.update(c.ROOT/p for p in report['input_hashes'])
    prior=c.ROOT/'ai/runs/current-auction-recovery-coverage-preflight-v2-before-handle-pin'
    paths.update(p for p in prior.rglob('*') if p.is_file())
    paths.update((first.OUT/'checks').glob('*.json'))
    api=HfApi();c.require(api.model_info(c.worker.retention.REPO).private,'Evidence repo must remain private')
    c.require(not api.file_exists(c.worker.retention.REPO,'archives/'+OUT.name+'.tgz'),'Inspect prior remote archive')
    OUT.mkdir()
    for path in sorted(paths):
        c.require(path.is_file() and not path.is_symlink(),'Expected regular coverage input')
        target=OUT/path.relative_to(c.ROOT);target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(path,target);c.require(c.digest(path)==c.digest(target),'Snapshot changed')
    c.worker.save(OUT/'manifest.json',{str(p.relative_to(OUT)):c.digest(p) for p in sorted(OUT.rglob('*')) if p.is_file()})
    c.worker.save(intent,{'report_sha256':c.digest(REPORT),'manifest_sha256':c.digest(OUT/'manifest.json'),'automatic_retries':False})
    evidence=upload_evidence(OUT)
    c.worker.save(DESCRIPTOR,{'archive':evidence,'report_sha256':c.digest(REPORT),'plan_sha256':c.digest(PLAN),
        'first_recovery_job_id':report['current_attempt_handle'],'tests':12,
        'new_hf_jobs':0,'new_games':0,'statistics_admitted':False,'qualified':False,'reserved_final_seeds_used':False})
    c.worker.save(outcome,{'archive':evidence,'descriptor_sha256':c.digest(DESCRIPTOR)})
    print(json.dumps({'archive':evidence,'tests':12,'new_hf_jobs':0,'statistics_admitted':False}),flush=True)


if __name__=='__main__':main()
