"""Preserve the admitted first recovery and exact handle, without executing it."""
from pathlib import Path
import json
import shutil

from huggingface_hub import HfApi
import manage_current_auction_resource_recovery_v2 as m
from policy_iteration_evidence_archive import upload_evidence

OUT=m.ROOT/'ai/runs/current-auction-first-recovery-evidence-v2'
DESCRIPTOR=m.STRONG/'current-auction-first-recovery-evidence-v2.json'
REPORT=m.STRONG/'current-auction-first-recovery-status-v2.json'


def main():
    intent=OUT.with_suffix('.intent.json');outcome=OUT.with_suffix('.outcome.json')
    m.require(not any(p.exists() for p in (OUT,OUT.with_suffix('.tgz'),intent,outcome,DESCRIPTOR)),
        'Inspect previous evidence upload outcome before retrying')
    prepared=m.prepared();source=m.source_checked();guard=m.read(m.OUT/'launch.json');report=m.read(REPORT)
    m.require(guard['source']==source and report['actual_hf']['job_id']==guard['job_id']
        and report['actual_hf']['public_configuration_verified'] is True,'Recovery handle changed')
    m.require(report['prepared_sha256']==m.digest(m.PRE/'prepared.json')
        and report['launch_sha256']==m.digest(m.OUT/'launch.json'),'Recovery state changed')
    api=HfApi();m.require(api.model_info(m.worker.retention.REPO).private,'Evidence must stay private')
    m.require(not api.file_exists(m.worker.retention.REPO,'archives/'+OUT.name+'.tgz'),'Inspect existing remote archive')
    paths={Path(__file__),REPORT,m.SOURCE,m.PREP_EVIDENCE,m.PREFLIGHT,m.OWNER_CONTEXT,
        m.ROOT/'ai/RESUME.md',m.ROOT/'ai/CURRENT-AUCTION-FIRST-RECOVERY-2026-10-29.md',m.STRONG/'experiments.json',
        m.STRONG/'current-auction-resource-recovery-decision-v2.json',
        m.STRONG/'current-auction-original-terminal-evidence-v1.json',
        m.STRONG/'current-auction-recovery-retention-evidence-v2.json',
        m.PRE/'prepared.json',m.PRE/'evidence-upload-intent.json',
        m.PRE/'source-upload-intent.json',m.PRE/'source-upload-receipt.json',
        m.OUT/'launch-intent.json',m.OUT/'launch.json'}
    paths.update(m.ROOT/p for p in prepared['code_hashes'])
    paths.update((m.PRE/'bundle').iterdir());paths.update((m.OUT/'checks').glob('*.json'))
    OUT.mkdir()
    for path in sorted(paths):
        m.require(path.is_file() and not path.is_symlink(),'Expected regular recovery input')
        target=OUT/path.relative_to(m.ROOT);target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(path,target);m.require(m.digest(path)==m.digest(target),'Recovery snapshot differs')
    m.save(OUT/'manifest.json',{str(p.relative_to(OUT)):m.digest(p) for p in sorted(OUT.rglob('*')) if p.is_file()})
    m.save(intent,{'created_at':m.now(),'report_sha256':m.digest(REPORT),
        'manifest_sha256':m.digest(OUT/'manifest.json'),'automatic_retries':False})
    evidence=upload_evidence(OUT)
    m.save(DESCRIPTOR,{'archive':evidence,'report_sha256':m.digest(REPORT),'job_id':guard['job_id'],
        'original_failed_handle':m.worker.FAILED_HANDLE,'supervisor_source':source,
        'preparation_evidence':prepared['preparation_evidence'],'archiving_new_jobs':0,'archiving_new_games':0,
        'attempt_games_audited':0,'remaining_rows_admitted':False,'qualified':False,'reserved_final_seeds_used':False})
    m.save(outcome,{'archive':evidence,'descriptor_sha256':m.digest(DESCRIPTOR)})
    print(json.dumps({'archive':evidence,'job_id':guard['job_id'],'new_jobs_from_archiving':0}),flush=True)


if __name__=='__main__':main()
