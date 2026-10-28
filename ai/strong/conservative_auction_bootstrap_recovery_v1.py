"""Reviewed pre-evaluation infrastructure recovery; never launches a job itself."""
import argparse
from datetime import datetime,timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import re

from huggingface_hub import HfApi
from public_policy_development_job_v1 import read,digest
from public_policy_final_contract_v1 import object_hash

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'ai/runs/conservative-auction-bootstrap-recovery-v1'
APPROVAL=ROOT/'ai/strong/conservative-auction-bootstrap-recovery-v1.json'
CACHE=ROOT/'ai/strong/node-runtime-cache-v1.json'
SOURCE_SHA='351fc4626837c2b7a9d1374e575852abd4fbf4e3d036fbbf406d9fedfb5acafa'
NODE_SHA='41cd79bb7877c81605a9e68ec4c91547774f46a40c67a17e34d7179ef11729df'
NAME='node-v24.14.0-linux-x64.tar.xz'
TARGETS={
 'pg-conservative-dev-v2-pop-heuristic-5p-02':{
  'job_id':'6ae1dca83fb22a235dd3e7c7','error_kind':'HTTP502',
  'log':'ai/runs/conservative-auction-development-hf-v2/pg-conservative-dev-v2-pop-heuristic-5p-02/job.log',
  'log_sha256':'792f3c25a65262e4225f9a45048cb50d7acc02a2756f35795acb80ba1cd0aa9f'},
 'pg-conservative-dev-v2-pop-legacy-6p-00':{
  'job_id':'6ae1dcb03fb22a235dd3e7eb','error_kind':'short_download',
  'log':'ai/runs/conservative-auction-failure-inspection-v1/pg-conservative-dev-v2-pop-legacy-6p-00.log',
  'log_sha256':'40bb0a3afee295dc11f07aef8ec7c29e16919ed5433168165eeccb9a32d1dd68'}}


def manager():
    path=Path(__file__).with_name('manage-conservative-auction-development-v2.py')
    spec=importlib.util.spec_from_file_location('unchanged_original_manager',path)
    value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value


def sha_text(value):return hashlib.sha256(value.encode()).hexdigest()


def cached_bootstrap(original,cache):
    assert cache['version']=='v24.14.0' and cache['sha256']==NODE_SHA and cache['remote_archive_verified'] is True
    assert cache['repo']=='coyotte508/powergrid-ai-training-v1' and cache['repo_type']=='dataset'
    assert cache['path']=='bootstrap/'+NAME and re.fullmatch('[a-f0-9]{40}',cache['revision'])
    needle="urllib.request.urlretrieve('https://nodejs.org/dist/v24.14.0/node-v24.14.0-linux-x64.tar.xz','/tmp/node.tar.xz')"
    assert original.count(needle)==1,'Unexpected original setup; review changes before replacing it'
    replacement=(f"node_archive=hf_hub_download({cache['repo']!r},{cache['path']!r},repo_type='dataset',revision={cache['revision']!r})\n"
        f"assert hashlib.sha256(Path(node_archive).read_bytes()).hexdigest()=={cache['sha256']!r}\n"
        "Path('/tmp/node.tar.xz').write_bytes(Path(node_archive).read_bytes())")
    return original.replace(needle,replacement,1)


def preevaluation_failure(log,kind):
    assert '"game_progress"' not in log and '"case"' not in log and '"evidence"' not in log
    assert log.count('Traceback (most recent call last):')==1
    tail=log.split('Traceback (most recent call last):')[1]
    assert 'File "<stdin>", line 4, in <module>' in tail
    if kind=='HTTP502':
        assert tail.rstrip().endswith('urllib.error.HTTPError: HTTP Error 502: Bad Gateway')
        assert 'in urlretrieve' in tail and 'in urlopen' in tail
    elif kind=='short_download':
        assert tail.rstrip().endswith('urllib.error.ContentTooShortError: <urlopen error retrieval incomplete: got only 6717440 out of 31039304 bytes>')
        assert 'in urlretrieve' in tail
    else:raise AssertionError('Unreviewed failure type')


def checked_approval(source):
    approval=read(APPROVAL);m=manager();cache=read(CACHE)
    assert digest(m.SOURCE)==approval['source_sha256']==SOURCE_SHA
    assert approval['source_fingerprint']==object_hash(source)
    assert approval['reviewer_sha256']==digest(Path(__file__)) and approval['node_cache_descriptor_sha256']==digest(CACHE)
    assert approval['original_bootstrap_sha256']==sha_text(m.BOOTSTRAP)
    bootstrap=cached_bootstrap(m.BOOTSTRAP,cache)
    assert approval['cached_bootstrap_sha256']==sha_text(bootstrap)
    assert set(approval['allowed_retries'])==set(TARGETS) and approval['retry_limit_per_row']==1
    assert approval['new_policy_or_seed_selection'] is False and approval['qualification_eligible'] is False
    by_name={r['name']:r for r in source['rows']}
    for name,target in TARGETS.items():
        proof=approval['allowed_retries'][name];path=m.OUT/name/'launch.json';guard=read(path)
        assert proof['job_id']==guard['job_id']==target['job_id'] and proof['original_guard_sha256']==digest(path)
        assert guard['stage']=='launched' and guard['row']==by_name[name] and guard['source_fingerprint']==object_hash(source)
        assert proof['log_sha256']==target['log_sha256']==digest(ROOT/target['log'])
        assert proof['error_kind']==target['error_kind'] and proof['original_status']=='ERROR'
        assert proof['evaluation_started'] is False and proof['original_output_archive_exists'] is False
        preevaluation_failure((ROOT/target['log']).read_text(),target['error_kind'])
    return approval,bootstrap


def review():
    assert not OUT.exists() and not APPROVAL.exists(),'Inspect previous review; never replace it silently'
    m=manager();source=m.source_checked();assert digest(m.SOURCE)==SOURCE_SHA
    cache=read(CACHE);bootstrap=cached_bootstrap(m.BOOTSTRAP,cache)
    old=read(ROOT/'ai/runs/conservative-auction-development-coordinator-recovery-v3/state.json')
    assert old['stage']=='stopped_for_inspection' and not (Path('/proc')/str(old['pid'])/'cmdline').exists()
    assert all(digest(ROOT/name)==sha for name,sha in old['code_hashes'].items())
    api=HfApi();proofs={}
    by_name={r['name']:r for r in source['rows']}
    for name,target in TARGETS.items():
        path=m.OUT/name/'launch.json';guard=read(path)
        assert guard['job_id']==target['job_id'] and guard['row']==by_name[name]
        assert guard['stage']=='launched' and guard['source_fingerprint']==object_hash(source)
        log=(ROOT/target['log']).read_text();assert sha_text(log)==target['log_sha256']
        preevaluation_failure(log,target['error_kind'])
        job=api.inspect_job(job_id=target['job_id'])
        assert job.status.stage=='ERROR' and job.command==['bash','-lc',m.BOOTSTRAP]
        assert job.docker_image=='python:3.11-slim-bookworm' and job.flavor==by_name[name]['flavor']
        expected={'SOURCE_ARCHIVE':source['archive'],'SOURCE_REVISION':source['revision'],'SOURCE_SHA256':source['sha256'],
            'SOURCE_MANIFEST_SHA256':source['source_manifest_sha256'],'PROTOCOL_SHA256':source['protocol_sha256'],
            'PILOT_JOB':by_name[name]['job'],'PILOT_NAME':name}
        assert all(job.environment.get(k)==v for k,v in expected.items())
        fresh='\n'.join(str(x) for x in api.fetch_job_logs(job_id=target['job_id'],follow=False))
        assert sha_text(fresh)==target['log_sha256']
        assert not api.file_exists('coyotte508/powergrid-ai-germany-v1','archives/'+name+'.tgz')
        assert not (m.OUT/name/'artifacts').exists() and not (m.OUT/name/'verified.json').exists()
        proofs[name]={**target,'original_guard_sha256':digest(path),'row_hash':object_hash(by_name[name]),
            'original_status':'ERROR','evaluation_started':False,'original_output_archive_exists':False,
            'exact_original_bootstrap_and_source_environment_verified':True,
            'created_at':str(job.created_at),'started_at':str(job.started_at),'finished_at':str(job.finished_at)}
    OUT.mkdir()
    (OUT/'original-bootstrap.sh').write_text(m.BOOTSTRAP)
    (OUT/'cached-node-bootstrap.sh').write_text(bootstrap)
    approval={'revision':'conservative-auction-bootstrap-recovery-v1','reviewed_at':datetime.now(timezone.utc).isoformat(),
        'source_sha256':SOURCE_SHA,'source_fingerprint':object_hash(source),'reviewer_sha256':digest(Path(__file__)),
        'node_cache_descriptor_sha256':digest(CACHE),'node_cache':cache,'original_bootstrap_sha256':sha_text(m.BOOTSTRAP),
        'cached_bootstrap_sha256':sha_text(bootstrap),'allowed_retries':proofs,'retry_limit_per_row':1,
        'remaining_unsubmitted_rows_use_cached_node':True,'original_failed_handles_preserved':True,
        'original_failed_guard_files_unchanged':True,'same_release_and_frozen_evaluation_source':True,
        'historical_binary_checksum_available':False,
        'setup_change':'Replace only the Node download with an immutable HF copy verified against official Node checksums. Historical source descriptor retains the original bootstrap hash; new guards must declare the actual cached-bootstrap hash.',
        'authorization':'Reviewed infrastructure recovery within active human-resumed research; explicit one-shot retry operation only, never automatic retries.',
        'new_hf_jobs':0,'new_policy_or_seed_selection':False,'qualification_eligible':False,'reserved_final_seeds_used':False}
    m.write_new(APPROVAL,approval);checked_approval(source)
    print(json.dumps({'reviewed_bootstrap_failures':len(proofs),'source_unchanged':True,'bootstrap_sha256':sha_text(bootstrap),'new_hf_jobs':0}),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(__doc__);parser.add_argument('operation',choices=['review'])
    globals()[parser.parse_args().operation]()
