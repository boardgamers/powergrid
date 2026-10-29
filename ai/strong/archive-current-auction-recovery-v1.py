"""Archive admitted recovery metadata, referring to unchanged original HF data.

Does not collect jobs, simulate games, train, launch, change policies or inspect
partial win rates. A prior intent or outcome requires manual inspection.
"""
from collections import Counter
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path

from huggingface_hub import HfApi
from policy_iteration_evidence_archive import upload_evidence
from public_policy_development_job_v1 import digest, read

ROOT = Path(__file__).resolve().parents[2]
NAME = 'current-auction-confirmation-recovery-evidence-v1'
OUT = ROOT/'ai/runs'/NAME
RESULT = ROOT/'ai/strong'/(NAME+'.json')
SNAPSHOT = ROOT/'ai/runs/current-auction-confirmation-recovery-launch-v1.json'


def save(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2, allow_nan=False); stream.write('\n')


def main():
    for path in (OUT, OUT.with_suffix('.tgz'), OUT.with_suffix('.intent.json'), RESULT):
        assert not path.exists(), 'Inspect previous archive intent/outcome; never blindly retry'
    spec = importlib.util.spec_from_file_location('recovery_manager',
        Path(__file__).with_name('manage-current-auction-confirmation-recovery-v1.py'))
    manager = importlib.util.module_from_spec(spec); spec.loader.exec_module(manager)
    admission = manager.admitted(); source = manager.source_checked()
    initial = read(ROOT/admission['initial_collection']); ready = read(manager.READINESS)
    snapshot = read(SNAPSHOT)
    assert snapshot['original_handles_preserved'] and snapshot['source_sha256'] == digest(manager.SOURCE)
    assert snapshot['admission_sha256'] == digest(manager.ADMISSION)
    sources = {ROOT/n for n in ready['input_hashes']}
    sources.update((Path(__file__).resolve(), manager.READINESS, manager.ADMISSION,
        ROOT/admission['initial_collection'], SNAPSHOT))
    sources.update(ROOT/n for n in (
        'ai/CURRENT-AUCTION-RECOVERY-2026-10-29.md',
        'ai/CURRENT-AUCTION-CONFIRMATION-2026-10-28.md',
        'ai/strong/policy_iteration_evidence_archive.py',
        'ai/strong/strategic_collection.py',
        'ai/strong/admit-current-auction-recovery-v1.py',
        'ai/runs/current-auction-recovery-admission-v1-first.log',
        'ai/strong/current-auction-recovery-storage-review-v1.json',
        'ai/runs/current-auction-recovery-initial-collection-v1-first.log',
        'ai/runs/current-auction-recovery-manager-tests-v1-first.log'))
    sources.update(p for p in (ROOT/'ai/runs/current-auction-recovery-before-startup-fix-v1').iterdir() if p.is_file())
    archives = []
    for job in initial['jobs']:
        folder = manager.OUT/job['name']; receipt = manager.verified_path(folder)
        assert read(receipt) == job
        assert digest(folder/'launch.json') == job['guard_sha256']
        assert digest(folder/'artifacts/manifest.json') == job['evidence']['manifest_sha256']
        sources.update((receipt, folder/'launch.json', folder/'artifacts/manifest.json'))
        if job['stage'] == 'ERROR':
            sources.add(folder/'preserved-terminal-error-v1.json')
            sources.update(folder/'terminal-recovery-v1'/n for n in ('intent.json','review.json','evaluation/evaluation.json'))
            sources.update(folder/'artifacts'/n for n in ('measurement.json','job/job-status.json','job/evaluation/evaluation.json'))
            sources.add(folder/'original-recovery-collection.log')
        archives.append({'name':job['name'],'job_id':job['job_id'],'original_hf_stage':job['stage'],
            'games':job['review']['games'],'evidence':job['evidence'],
            'verification_file':str(receipt.relative_to(ROOT)),'verification_sha256':digest(receipt),
            'recovery':job['review'].get('recovery')})
    for name, sha in snapshot['guard_hashes'].items():
        assert digest(ROOT/name) == sha; sources.add(ROOT/name)
    assert all(p.is_file() and not p.is_symlink() for p in sources)
    api = HfApi(); repo = 'coyotte508/powergrid-ai-germany-v1'
    assert api.model_info(repo).private and not api.file_exists(repo,'archives/'+NAME+'.tgz')
    OUT.mkdir(); manifest = {}
    for path in sorted(sources):
        name = str(path.relative_to(ROOT)); expected = digest(path)
        target = OUT/name; target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes(path.read_bytes())
        assert digest(target) == expected == digest(path), 'Source changed during snapshot'
        manifest[name] = expected
    recovery = {'source':{k:source[k] for k in ('repo','revision','archive','sha256','source_manifest_sha256')},
        'source_repo_type':'dataset','initial_original_archives':archives,
        'recovery_rule':manager.recovery.RULE,'original_source_and_policies_unchanged':True,
        'game_reruns':0,'new_inference':0,'new_gradients':0,
        'recovery_instructions':'Restore the immutable source and each original archive by revision/hash. Restore original guards, readiness pins, receipts, failed report and recovery intent. Rebuild only the derived report using original terminal files; never replay games. Run the read-only audit before admitting data. Inspect actual live state before any owner action; do not restart from a stale snapshot.',
        'original_error_preserved':True,'qualified':False,'reserved_final_seeds_used':False}
    save(OUT/'original-archive-references.json',recovery)
    manifest['original-archive-references.json'] = digest(OUT/'original-archive-references.json')
    save(OUT/'manifest.json',manifest)
    intent = {'created_at':datetime.now(timezone.utc).isoformat(),'stage':'prepared_for_upload',
        'manifest_sha256':digest(OUT/'manifest.json')}
    save(OUT.with_suffix('.intent.json'),intent)
    print(json.dumps({'stage':'uploading','files':len(manifest)+1}),flush=True)
    archive = upload_evidence(OUT)
    save(RESULT,{'status':'original_terminal_recovery_admitted_and_remaining_confirmation_started',
        'initial_jobs':len(archives),'initial_games':sum(j['games'] for j in archives),
        'original_hf_stages':dict(Counter(j['original_hf_stage'] for j in archives)),
        'original_error_preserved':True,'game_reruns':0,'recovery_rule':manager.recovery.RULE,
        'admission_sha256':digest(manager.ADMISSION),'launch_snapshot_sha256':digest(SNAPSHOT),
        'source_sha256':digest(manager.SOURCE),'archive':archive,
        'qualified':False,'reserved_final_seeds_used':False})
    OUT.with_suffix('.intent.json').write_text(json.dumps({**intent,'stage':'uploaded_download_verified',
        'archive':archive,'descriptor_sha256':digest(RESULT)},indent=2)+'\n')
    print(json.dumps(archive),flush=True)


if __name__ == '__main__': main()
