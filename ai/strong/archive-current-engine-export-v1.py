"""Archive completed current-engine parity and independent raw-output audit."""
from datetime import datetime,timezone
import json
from pathlib import Path

from huggingface_hub import HfApi
from policy_iteration_evidence_archive import upload_evidence
from public_policy_development_job_v1 import read,digest

ROOT=Path(__file__).resolve().parents[2]
NAME='current-engine-export-evidence-v1'
OUT=ROOT/'ai/runs'/NAME
RESULT=ROOT/'ai/strong'/(NAME+'.json')


def save(p,x):
    with p.open('x') as f:json.dump(x,f,indent=2,allow_nan=False);f.write('\n')


def main():
    assert all(not p.exists() for p in (OUT,OUT.with_suffix('.tgz'),OUT.with_suffix('.intent.json'),RESULT)), 'Inspect existing archive outcome'
    report_path=ROOT/'ai/strong/current-engine-export-parity-v1.json';report=read(report_path)
    audit_path=ROOT/'ai/strong/current-engine-export-audit-v1.json';audit=read(audit_path)
    assert report['complete'] and audit['complete'] and report['positions']==audit['positions']==2553
    assert audit['report_sha256']==digest(report_path) and audit['receipts_sha256']==report['receipts_sha256']
    assert audit['all_input_tensor_hashes_match'] and audit['all_native_onnx_actions_equal']
    assert all(digest(ROOT/n)==h for n,h in report['input_hashes'].items())
    source=ROOT/'ai/runs/current-engine-export-parity-v1'
    assert digest(source/'receipts.jsonl')==report['receipts_sha256']
    assert digest(ROOT/'ai/strong/audit_current_engine_export_v1.py')==audit['auditor_sha256']
    sources={ROOT/n for n in report['input_hashes']}
    cases=ROOT/'ai/runs/current-full-serving-8840u-prepared-v1/package/cases.jsonl';sources.remove(cases)
    sources.update((Path(__file__).resolve(),report_path,audit_path,
        ROOT/'ai/CURRENT-ENGINE-EXPORT-2026-10-29.md',
        ROOT/'ai/strong/audit_current_engine_export_v1.py',ROOT/'ai/strong/test_current_export_serving_binding_v1.py',
        ROOT/'ai/strong/current-full-serving-launch-evidence-v1.json',
        ROOT/'ai/strong/policy_iteration_evidence_archive.py',ROOT/'ai/strong/strategic_collection.py'))
    sources.update(p for p in source.rglob('*') if p.is_file())
    for n in ('current-engine-export-parity-v1-first.log','current-engine-export-parity-v1-native-source-fixed.log',
              'current-engine-export-parity-v1-before-native-source-fix.py','current-engine-export-native-source-v1-first.log',
              'current-engine-export-independent-audit-v1-first.log','current-export-serving-binding-tests-v1-first.log'):
        sources.add(ROOT/'ai/runs'/n)
    for name,count in (('current-engine-export-parity-tests-v1-first.log',4),('current-export-serving-binding-tests-v1-first.log',2)):
        log=(ROOT/'ai/runs'/name).read_text();assert f'Ran {count} tests' in log and log.rstrip().endswith('OK')
    package_archive=read(ROOT/'ai/strong/current-full-serving-launch-evidence-v1.json')['archive']
    assert package_archive['remote_archive_verified']
    api=HfApi();repo='coyotte508/powergrid-ai-germany-v1'
    assert api.model_info(repo).private and not api.file_exists(repo,'archives/'+NAME+'.tgz')
    OUT.mkdir();manifest={}
    for p in sorted(sources):
        assert p.is_file() and not p.is_symlink()
        n=str(p.relative_to(ROOT));before=digest(p);target=OUT/n;target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes(p.read_bytes());assert digest(target)==before==digest(p);manifest[n]=before
    save(OUT/'recovery.json',{'current_runtime_and_cases_archive':package_archive,
        'cases_sha256':digest(cases),'native_training_source':report['native_source'],'model_pin':report['model_pin'],
        'instructions':'Restore exact current runtime/public fixtures from the referenced full-serving package and verify all hashes. This archive includes native definitions, original checkpoint and complete raw parity outputs. Do not repeat completed forward passes or the completed feature audit. Inspect the existing target run and collect/audit it only after completion; then bind saved model proposals without new inference. No selection or final seeds are authorized by technical proof.'})
    manifest['recovery.json']=digest(OUT/'recovery.json');save(OUT/'manifest.json',manifest)
    intent={'created_at':datetime.now(timezone.utc).isoformat(),'stage':'prepared_for_upload','manifest_sha256':digest(OUT/'manifest.json')}
    save(OUT.with_suffix('.intent.json'),intent);archive=upload_evidence(OUT)
    save(RESULT,{'complete':True,'positions':2553,'tests':6,'all_native_onnx_actions_equal':True,
        'independent_input_and_output_audit':True,'report_sha256':digest(report_path),'audit_sha256':digest(audit_path),
        'model_sha256':report['model_sha256'],'checkpoint_sha256':report['checkpoint_sha256'],
        'runtime_manifest_sha256':report['runtime_manifest_sha256'],'preserved_first_setup_failure':True,
        'candidate_selected':False,'qualified':False,'reserved_final_seeds_used':False,'archive':archive})
    OUT.with_suffix('.intent.json').write_text(json.dumps({**intent,'stage':'uploaded_download_verified',
        'archive':archive,'descriptor_sha256':digest(RESULT)},indent=2)+'\n')
    print(json.dumps(archive),flush=True)


if __name__=='__main__':main()
