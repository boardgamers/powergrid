"""Read-only independent original-job audit suitable for isolated worker processes.

No HF requests, artifact extraction, receipt writes, collection operations, game
execution or policy calls. Uses the same frozen full verifiers as collection.
"""
import importlib.util
from pathlib import Path
import resource
import time

from public_policy_development_job_v1 import read,digest
from public_policy_final_contract_v1 import object_hash

ROOT=Path(__file__).resolve().parents[2]
MODULES={}


def manager(kind):
    assert kind in ('confirmation','runtime')
    if kind not in MODULES:
        filename='manage-current-auction-confirmation-recovery-v1.py' if kind=='confirmation' else 'manage-current-auction-runtime-v1.py'
        spec=importlib.util.spec_from_file_location('readonly_audit_'+kind,Path(__file__).with_name(filename))
        value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);MODULES[kind]=value
    return MODULES[kind]


def audit_original(case):
    """Reject changed source/guard/receipt before and after the full raw audit."""
    m=manager(case['kind']);folder=m.OUT/case['name']
    assert folder.resolve().parent==m.OUT.resolve()
    assert digest(m.SOURCE)==case['source_sha256']
    source=read(m.SOURCE);row=next(r for r in source['rows'] if r['name']==case['name'])
    receipt=m.verified_path(folder) if case['kind']=='confirmation' else folder/'verified.json'
    assert digest(receipt)==case['verified_sha256'] and digest(folder/'launch.json')==case['guard_sha256']
    saved=read(receipt);guard=read(folder/'launch.json')
    assert saved['job_id']==case['job_id']==guard['job_id'] and saved['row']==row==guard['row']
    assert guard['stage']=='launched' and saved['verified']
    if case['kind']=='confirmation':
        assert guard['source_fingerprint']==object_hash(source)
        assert saved['source_sha256']==case['source_sha256'] and m.recovery.complete_data(saved)
    else:
        assert guard['source']==source and saved['stage']=='COMPLETED'
    before=resource.getrusage(resource.RUSAGE_SELF);started=time.perf_counter()
    review=(m.verify_result(folder,source,row,saved) if case['kind']=='confirmation'
            else m.previous.verify_artifacts(folder/'artifacts',source,row,saved['evidence']))
    assert review==saved['review'], 'Independent verifier differs from original receipt'
    after=resource.getrusage(resource.RUSAGE_SELF)
    assert digest(m.SOURCE)==case['source_sha256'] and digest(receipt)==case['verified_sha256']
    assert digest(folder/'launch.json')==case['guard_sha256']
    return {'name':case['name'],'kind':case['kind'],'job_id':saved['job_id'],'original_hf_stage':saved['stage'],
        'games':review['games'],'review_sha256':object_hash(review),'counts':review['audit']['counts'],
        'seconds':time.perf_counter()-started,
        'cpu_seconds':after.ru_utime+after.ru_stime-before.ru_utime-before.ru_stime,
        'process_lifetime_peak_rss_bytes':after.ru_maxrss*1024}
