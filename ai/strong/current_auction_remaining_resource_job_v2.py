"""Unadmitted remaining-grid worker; exact first-recovery audit is mandatory.

Default only validates. No job submission API. All game/policy execution remains
in the byte-identical original source, with the previously tested retention core.
"""
import argparse
import importlib.util
import json
from pathlib import Path
import re
import shutil
import sys

import current_auction_resource_job_v2 as base

ENTRY='current_auction_remaining_resource_job_v2.py'
BASE_SHA='3b0c5f6d764969056a99791f679ab9baecc585daa2f1d99841ab40b2004468d5'
FIRST_SOURCE_SHA='ee8e98a7f1cb3c0f0cb7f30527ab4c259aa4b0219e121bef98df0cd79096f840'
FIRST_HANDLE='6ae3083f3fb22a235dd56000'
FIRST_COLLECTOR_SHA='c7394e741f6fd9f52b03a9d787f97ffd508e416be466bda3518c9237073ded74'
FIRST_MANAGER_SHA='81fb84a584a4efefe01627d85b62adee541489a806e6e2ccdd9d97a5db6d49cf'
require,read,digest,save=base.require,base.read,base.digest,base.save


def remaining_row(original,decision,name):
    rows=[r for r in original['rows'] if r['name']==name]
    fixed=[r for r in decision['fixed_recovery_rows'] if r['name']==name]
    require(len(rows)==len(fixed)==1,'Row absent/duplicated in fixed remaining plan')
    row,record=rows[0],fixed[0]
    require(name!=base.FAILED_NAME and record['reason']=='never_submitted' and record['original_handle'] is None,
        'Remaining worker cannot replay a submitted original or first recovery')
    require(base.object_hash(row)==record['original_row_sha256'] and row['shard']['games']==record['games'],
        'Fixed remaining row changed')
    n=row['players'];shard=row['shard']
    require(n in (2,3,5,6) and shard['players']==n and shard['name']==name
        and shard['seed']==f'current-auction-confirmation-v1-{n}p', 'Wrong remaining count/seed/canonical name')
    require(row['arm']=='conservative_population' and row['identity']['settings']['workers']==4
        and row['identity']['settings']['threads']==1,'Frozen remaining policy/workers changed')
    require(shard['games'] in (16,20,24) and shard['games']==shard['deals']*4*n
        and 0<=shard['start']<shard['start']+shard['deals']<=32,'Wrong fixed game interval')
    require(name.startswith('pg-current-confirm-v1-'),'Noncanonical source job name')
    return row


def attempt_name(name):
    require(name.startswith('pg-current-confirm-v1-'),'Noncanonical source job name')
    value=name.replace('pg-current-confirm-v1-','pg-current-retained-v2-',1)
    require(re.fullmatch('[a-z0-9][a-z0-9_-]{1,62}',value),'Unsafe attempt name')
    # The tested retention core's namespace deliberately contains only hyphens.
    return value.replace('_','-')


def first_recovery_gate(result,original,first_source):
    require(result['verified'] is True and result['games']==16
        and result['original_name']==base.FAILED_NAME and result['original_failed_handle']==base.FAILED_HANDLE
        and result['attempt_id']==base.ATTEMPT and result['job_id']==FIRST_HANDLE,'Wrong/incomplete first recovery audit')
    require(result['original_failure_preserved'] is True and result['remaining_rows_admitted'] is False
        and result['qualification_eligible'] is False and result['qualified'] is False
        and result['reserved_final_seeds_used'] is False,'First recovery has wrong purpose')
    require(result['source_descriptor_sha256']==FIRST_SOURCE_SHA
        and result['collector_sha256']==FIRST_COLLECTOR_SHA and result['manager_sha256']==FIRST_MANAGER_SHA,
        'First recovery was not audited by the admitted collector')
    require(first_source['remote_archive_verified'] is True
        and result['bundle_manifest_sha256']==first_source['manifest_sha256'],'First supervisor differs')
    terminal=result['terminal']
    require(terminal['job_id']==FIRST_HANDLE and terminal['stage']=='COMPLETED'
        and terminal['timeout_seconds']==86400 and terminal['flavor']=='cpu-upgrade'
        and terminal['public_configuration_verified'] is True,'First HF attempt did not complete with verified controls')
    first=next(r for r in original['rows'] if r['name']==base.FAILED_NAME)
    audit=result['review']['audit']
    require(result['review']['games']==16 and audit['identity']==first['identity']
        and audit['all_receipts_verified'] is True and audit['counts']['rollout_caps']==0
        and audit['reserved_final_seeds_used'] is False,'First raw audit is incomplete/capped or changed policy')
    eps=list(range(first['shard']['start']*16,(first['shard']['start']+first['shard']['deals'])*16))
    require(result['retained_episodes']==eps,'First retention coverage differs')
    archived=[];names=set()
    for checkpoint in result['checkpoint_archives']:
        evidence=checkpoint['evidence'];path=evidence['archive_path']
        require(path not in names and re.fullmatch('archives/'+re.escape(base.ATTEMPT)+r'-checkpoint-[0-9]{4}\.tgz',path),
            'First checkpoint repeated or foreign')
        require(evidence['repo']==base.retention.REPO and evidence['remote_archive_verified'] is True
            and re.fullmatch('[a-f0-9]{40}',evidence['revision'])
            and re.fullmatch('[a-f0-9]{64}',evidence['archive_sha256']),'First checkpoint is not immutable verified evidence')
        names.add(path);archived.extend(checkpoint['episodes'])
    require(sorted(archived)==eps,'First checkpoint pairs omitted/duplicated')
    evidence=result['envelope_evidence']
    require(evidence['repo']==base.retention.REPO and evidence['archive_path']=='archives/'+base.ATTEMPT+'-final.tgz'
        and evidence['remote_archive_verified'] is True and re.fullmatch('[a-f0-9]{40}',evidence['revision'])
        and re.fullmatch('[a-f0-9]{64}',evidence['archive_sha256']),'First final evidence is not immutable')
    return True


def original_job_controls(source,original,row,pins):
    spec=read(base.checked(source,row['job']))
    require(digest(source/row['job'])==row['job_spec_sha256'] and spec['workers']==4,'Original job changed')
    for key in ('candidate','contract'):
        require(digest(base.checked(source,spec[key]))==row[key+'_sha256'],'Original policy/contract changed')
    require(pins['public_policy_measured_job_v1.py']==original['measured_entry_sha256']
        and pins['public_policy_development_job_v1.py']==original['entry_sha256'],'Original entry changed')


def inspect(bundle,bundle_sha,source,output,name,*,execute=False):
    bundle,source,output=(Path(p).resolve() for p in (bundle,source,output))
    pins=base.tree(bundle,'manifest.json',bundle_sha)
    required={ENTRY,base.ENTRY,base.CORE,'original-source.json','decision.json','first-recovery-source.json'}
    require(required<=set(pins)<=required|{'first-recovery-result.json','admission.json'},'Unexpected remaining worker inputs')
    require(pins[ENTRY]==digest(__file__) and pins[base.ENTRY]==digest(base.__file__)==BASE_SHA
        and pins[base.CORE]==digest(base.retention.__file__)==base.RETENTION_SHA,'Unpinned worker/retention code')
    require(pins['original-source.json']==base.SOURCE_SHA and pins['decision.json']==base.DECISION_SHA
        and pins['first-recovery-source.json']==FIRST_SOURCE_SHA,'Original source/decision/first attempt changed')
    original,decision,first_source=(read(bundle/p) for p in ('original-source.json','decision.json','first-recovery-source.json'))
    row=remaining_row(original,decision,name);attempt=attempt_name(name)
    first_passed=False
    if 'first-recovery-result.json' in pins:
        first_passed=first_recovery_gate(read(bundle/'first-recovery-result.json'),original,first_source)
    core_hash=base.object_hash({k:v for k,v in pins.items() if k!='admission.json'})
    if execute:
        require(first_passed,'Complete independently audited first recovery is required before any remaining game')
        require('admission.json' in pins,'Actual reviewed remaining-grid preparation required')
        admission=read(bundle/'admission.json')
        require(admission['passed'] is True and admission['scope']=='remaining_fixed_confirmation_first_executions'
            and admission['core_files_sha256']==core_hash and admission['first_recovery_result_sha256']==pins['first-recovery-result.json']
            and admission['decision_sha256']==base.DECISION_SHA and admission['source_descriptor_sha256']==base.SOURCE_SHA
            and admission['allocation']==base.ALLOCATION and admission['jobs']==323 and admission['games']==7100,
            'Remaining admission does not bind actual inputs/resources')
        require(admission['new_hf_jobs']==admission['new_games']==0 and admission['qualified'] is False
            and admission['reserved_final_seeds_used'] is False,'Preparation cannot claim execution/strength')
        for key in ('preflight_sha256','test_log_sha256','preparation_archive_sha256'):
            require(re.fullmatch('[a-f0-9]{64}',admission[key]),'Missing real prepared evidence')
    source_pins=base.tree(source,'source-manifest.json',original['source_manifest_sha256'])
    original_job_controls(source,original,row,source_pins)
    require(not output.exists(),'Inspect existing attempt; never rerun')
    require(all(not output.is_relative_to(p) and not p.is_relative_to(output) for p in (bundle,source)), 'Output overlaps immutable inputs')
    raw=output/'original-output'/name
    common=['--source',str(source),'--manifest-sha256',original['source_manifest_sha256'],'--job',row['job'],
        '--output',str(raw),'--source-revision',original['revision'],'--source-archive-sha256',original['sha256']]
    command=[sys.executable,'-u','-B',str(source/'public_policy_measured_job_v1.py'),*common,
        '--protocol-sha256',original['protocol_sha256'],'--scope','development']
    context={'attempt_id':attempt,'decision_sha256':base.DECISION_SHA,'source_descriptor_sha256':base.SOURCE_SHA,
        'original_row_sha256':base.object_hash(row),'original_row':row}
    return {'scope':'remaining_fixed_confirmation_first_execution','attempt_id':attempt,'original_name':name,
        'original_failed_handle':None,'original_source':original,'row':row,'context':context,'allocation':base.ALLOCATION,
        'bundle_manifest_sha256':bundle_sha,'core_files_sha256':core_hash,'admission_sha256':pins.get('admission.json'),
        'first_recovery_result_sha256':pins.get('first-recovery-result.json'),'first_recovery_gate_verified':first_passed,
        'command':command,'raw_output':str(raw),'output':str(output)}


def run(bundle,bundle_sha,source,output,name,*,execute=False,upload=False):
    config=inspect(bundle,bundle_sha,source,output,name,execute=execute)
    if not execute:return {'valid':True,'execute':False,'name':name,'games':config['row']['shard']['games'],
        'first_recovery_gate_verified':config['first_recovery_gate_verified'],'core_files_sha256':config['core_files_sha256']}
    require(upload is True,'Execution requires durable private retention')
    source,output=Path(source).resolve(),Path(output).resolve();attempt=config['attempt_id']
    helper_path=source/'artifact/ai/strong/policy_iteration_evidence_archive.py';sys.path.insert(0,str(helper_path.parent))
    spec=importlib.util.spec_from_file_location('frozen_remaining_evidence_uploader',helper_path)
    helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
    from huggingface_hub import HfApi
    api=HfApi();require(api.model_info(base.retention.REPO).private,'Evidence repo must remain private')
    output.mkdir();save(output/'attempt.json',config);supervisor=output/'supervisor';observations=[]
    def uploader(folder):
        require(not api.file_exists(base.retention.REPO,'archives/'+folder.name+'.tgz'),'Inspect existing archive; never overwrite')
        observation={'started_at':base.now(),'child_live_before_upload':base.child_live(supervisor),
            'directory':folder.name,'manifest_sha256':digest(folder/'manifest.json')}
        evidence=helper.upload_evidence(folder)
        observation.update(finished_at=base.now(),evidence=evidence,child_live_after_upload=base.child_live(supervisor))
        observations.append(observation);save(output/(folder.name+'.transport.json'),observation)
        print(json.dumps({'checkpoint_evidence':evidence,'attempt_id':attempt}),flush=True);return evidence
    raw=Path(config['raw_output']);status={'stage':'running','started_at':base.now(),'attempt_id':attempt,
        'original_name':name,'original_failed_handle':None,'qualified':False,'reserved_final_seeds_used':False,'automatic_retries':False}
    caught=None
    try:
        result=base.retention.supervise(config['command'],raw/'job/evaluation',supervisor,
            config['context'],uploader,base.ALLOCATION['checkpoint_period_seconds'])
        require(result['child_returncode']==0,'Original child failed; preserve without retry')
        require(len(result['retained_episodes'])==result['expected_episodes']==config['row']['shard']['games'],
            'Incomplete retained original episodes')
        require(any(o['child_live_before_upload'] and o['child_live_after_upload'] for o in observations),
            'No verified retention while original child stayed live')
        base.tree(source,'source-manifest.json',config['original_source']['source_manifest_sha256'])
        base.tree(Path(bundle).resolve(),'manifest.json',bundle_sha)
        status.update(stage='child_complete_pending_independent_audit',supervisor=result)
    except BaseException as error:
        caught=error;status.update(stage='failed_preserved',failure_type=type(error).__name__)
    finally:
        status['finished_at']=base.now();save(output/'run-status.json',status)
        envelope=output/(attempt+'-final');envelope.mkdir()
        save(envelope/'attempt.json',config);save(envelope/'run-status.json',status)
        save(envelope/'checkpoint-transports.json',observations)
        if raw.exists():base.snapshot_tree(raw,envelope/'raw')
        if supervisor.exists():
            meta=envelope/'supervisor';meta.mkdir()
            for path in sorted(supervisor.iterdir()):
                if path.is_file() and path.suffix in ('.json','.log'):
                    require(not path.is_symlink(),'Symlink in supervisor output');shutil.copyfile(path,meta/path.name)
        save(envelope/'manifest.json',{str(p.relative_to(envelope)):digest(p) for p in sorted(envelope.rglob('*')) if p.is_file()})
        save(output/'final-upload-intent.json',{'manifest_sha256':digest(envelope/'manifest.json'),'automatic_retries':False})
        require(not api.file_exists(base.retention.REPO,'archives/'+envelope.name+'.tgz'),'Inspect existing final archive')
        final=helper.upload_evidence(envelope);save(output/'final-upload-receipt.json',final)
        print(json.dumps({'recovery_final_evidence':final,'attempt_id':attempt,'status':status}),flush=True)
    if caught is not None:raise caught
    return {'status':status,'evidence':final,'qualified':False}


if __name__=='__main__':
    parser=argparse.ArgumentParser(__doc__)
    for arg in ('bundle','source','output'):parser.add_argument('--'+arg,type=Path,required=True)
    parser.add_argument('--bundle-manifest-sha256',required=True);parser.add_argument('--name',required=True)
    parser.add_argument('--execute',action='store_true');parser.add_argument('--upload',action='store_true')
    args=parser.parse_args();print(json.dumps(run(args.bundle,args.bundle_manifest_sha256,args.source,args.output,args.name,
        execute=args.execute,upload=args.upload)),flush=True)
