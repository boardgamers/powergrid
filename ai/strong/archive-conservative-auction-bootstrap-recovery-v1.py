"""One-shot evidence archive for the reviewed infrastructure recovery.

Copies immutable admission evidence and cached archive references. It neither
collects live jobs nor submits them. Inspect any existing intent before retrying.
"""
from datetime import datetime,timezone
import importlib.util
import json
from pathlib import Path
import shutil

from huggingface_hub import HfApi
from policy_iteration_evidence_archive import upload_evidence
from public_policy_development_job_v1 import read,digest

ROOT=Path(__file__).resolve().parents[2]
NAME='conservative-auction-bootstrap-recovery-evidence-v1'
OUT=ROOT/'ai/runs'/NAME
DESCRIPTOR=ROOT/'ai/strong'/(NAME+'.json')
SNAPSHOT=ROOT/'ai/strong/conservative-auction-attempts-recovery-state-v1.json'


def save(path,data):
    with path.open('x') as stream:json.dump(data,stream,indent=2,allow_nan=False);stream.write('\n')


def main():
    for path in (OUT,OUT.with_suffix('.tgz'),OUT.with_suffix('.intent.json'),DESCRIPTOR,SNAPSHOT):
        assert not path.exists(),'Inspect previous archive outcome before retry: '+str(path)
    spec=importlib.util.spec_from_file_location('archive_attempt_manager',Path(__file__).with_name('manage-conservative-auction-attempts-v1.py'))
    manager=importlib.util.module_from_spec(spec);spec.loader.exec_module(manager)
    source=manager.source_checked();manager.tests_checked()
    predecessor=read(manager.OWNER/'predecessor.json');state=read(manager.OWNER/'state.json')
    assert digest(manager.OWNER/'predecessor.json')==state['predecessor_sha256']
    assert all(digest(ROOT/name)==sha for name,sha in state['code_hashes'].items())
    proc=Path('/proc')/str(state['pid'])/'cmdline'
    live=proc.exists() and b'coordinate-conservative-auction-attempts-v1.py' in proc.read_bytes()
    assert live and state['stage']!='stopped_for_inspection','Inspect changed owner before creating archive'
    assert HfApi().model_info('coyotte508/powergrid-ai-germany-v1').private
    sources={Path(__file__).resolve(),manager.OWNER/'predecessor.json',manager.TEST_RESULT,
        manager.recovery.APPROVAL,manager.recovery.CACHE,manager.SOURCE,
        ROOT/'ai/runs/conservative-auction-attempts-tests-v1.log',
        ROOT/'ai/runs/conservative-auction-bootstrap-review-v1.log',
        ROOT/'ai/runs/conservative-auction-bootstrap-retry-v1.log'}
    sources.update(ROOT/name for name in state['code_hashes'])
    sources.update(ROOT/'ai/strong'/name for name in ('prepare-node-runtime-cache-v1.py',
        'policy_iteration_evidence_archive.py','strategic_collection.py',
        'conservative-auction-development-owner-recovery-evidence-v3.json',
        'conservative-auction-development-owner-recovery-state-v3.json'))
    for folder in ('conservative-auction-bootstrap-recovery-v1','node-runtime-cache-v1'):
        sources.update(p for p in (ROOT/'ai/runs'/folder).glob('*') if p.is_file() and p.suffix in ('.json','.sh'))
    sources.update(ROOT/'ai'/name for name in ('RESUME.md','CONSERVATIVE-AUCTION-RUNTIME-2026-10-27.md',
        'CONSERVATIVE-AUCTION-BOOTSTRAP-RECOVERY-2026-10-28.md'))
    recovered={}
    for name,target in manager.recovery.TARGETS.items():
        original=manager.original.OUT/name;selected=manager.execution_folder(name)
        sources.add(original/'launch.json');sources.add(ROOT/target['log'])
        sources.update(p for p in (original/'failure.json',original/'job.log') if p.exists())
        guard=read(selected/'launch.json');manager.guard_checked(source,guard['row'],guard)
        recovered[name]={'original_job_id':target['job_id'],'attempt_job_id':guard['job_id'],
            'original_guard_sha256':digest(original/'launch.json'),'attempt_guard_sha256':digest(selected/'launch.json')}
    for item in predecessor['selected_guards']:
        folder=ROOT/item['directory'];assert digest(folder/'launch.json')==item['guard_sha256']
        sources.add(folder/'launch.json')
        if 'verified_sha256' in item:
            assert digest(folder/'verified.json')==item['verified_sha256']
            sources.update((folder/'verified.json',folder/'artifacts/manifest.json'))
    snapshot={'captured_at':datetime.now(timezone.utc).isoformat(),'owner_live_at_capture':live,
        'owner_state':state,'predecessor_sha256':state['predecessor_sha256'],
        'admission_selected_jobs':len(predecessor['selected_guards']),
        'admission_cached_audits':sum('verified_sha256' in g for g in predecessor['selected_guards']),
        'reviewed_attempts':recovered,'new_gradients':0,'qualified':False,'reserved_final_seeds_used':False,
        'scope':'Immutable admission and a live-owner snapshot, not the final result. Raw completed-job archives are referenced by cached receipts. Source and Node cache use their included immutable HF descriptors.'}
    save(SNAPSHOT,snapshot);sources.add(SNAPSHOT)
    OUT.mkdir();manifest={}
    log=OUT/'owner-log-at-capture.log';log.write_text(manager.OWNER.with_suffix('.log').read_text())
    manifest[log.name]=digest(log)
    for source_file in sorted(sources):
        assert source_file.is_file() and not source_file.is_symlink()
        name=str(source_file.relative_to(ROOT));target=OUT/name;target.parent.mkdir(parents=True,exist_ok=True)
        before=digest(source_file);shutil.copy2(source_file,target)
        assert digest(target)==before;manifest[name]=before
    note=OUT/'README.md'
    note.write_text('''# Reviewed Node bootstrap recovery

Two original jobs failed before source extraction/evaluation. Their exact original
guards, logs and reviewed failure proof are preserved. The explicit replacement
guards live in separate attempt-1 folders. New unsubmitted rows use the same Node
release from the immutable, official-checksum-verified HF archive. Models, engine,
source, seeds, schedule and statistical arithmetic remain frozen.

The immutable predecessor captures 424 selected rows and 360 cached raw audits;
the state/log snapshot may show later progress. This is recovery provenance, not
a completed study or strength claim. Inspect actual owner state and job handles
before acting. No automatic retry/restart or final qualification is authorized by
this snapshot. Original v3 recovery/source archives and completed raw job archives
are referenced by their included immutable descriptors rather than duplicated.
''')
    manifest[note.name]=digest(note);save(OUT/'manifest.json',manifest)
    intent={'created_at':datetime.now(timezone.utc).isoformat(),'stage':'prepared_for_upload',
        'repo':'coyotte508/powergrid-ai-germany-v1','archive_path':'archives/'+NAME+'.tgz',
        'manifest_sha256':digest(OUT/'manifest.json')}
    save(OUT.with_suffix('.intent.json'),intent)
    print(json.dumps({'stage':'uploading','files':len(manifest)+1}),flush=True)
    archive=upload_evidence(OUT)
    descriptor={'status':'reviewed_infrastructure_recovery_active_not_strength_result',
        'reviewed_attempts':recovered,'snapshot_sha256':digest(SNAPSHOT),
        'bootstrap_recovery_sha256':digest(manager.recovery.APPROVAL),'node_cache':read(manager.recovery.CACHE),
        'admission_selected_jobs':424,'admission_cached_audits':360,'preserved_failed_originals':2,
        'planned_selected_jobs':648,'planned_games':10080,'source_sha256':digest(manager.SOURCE),
        'new_gradients':0,'qualification_eligible':False,'reserved_final_seeds_used':False,'archive':archive}
    save(DESCRIPTOR,descriptor)
    OUT.with_suffix('.intent.json').write_text(json.dumps({**intent,'stage':'uploaded_download_verified',
        'archive':archive,'descriptor_sha256':digest(DESCRIPTOR)},indent=2)+'\n')
    print(json.dumps(archive),flush=True)


if __name__=='__main__':main()
