"""Read-only routing/authentication of v2 and bucket-v3 confirmation attempts.

Incomplete coverage rejects before parsing reviews or analyzing outcomes. Failed
transport attempts remain missing until a separate explicit recovery is admitted.
This module never dispatches, collects, reruns games or qualifies a candidate.
"""
from collections import Counter
import json
from pathlib import Path
import re

import current_auction_recovery_authentication_v2 as previous
import manage_current_auction_bucket_remaining_v3 as remaining

coverage=previous.coverage
first=remaining.first
ROOT=remaining.ROOT
read,digest,require=remaining.read,remaining.digest,remaining.require
object_hash=remaining.worker.base.object_hash
BACKENDS={'timeout_v2','retained_v2','bucket_first_v3','bucket_remaining_v3'}


def routing(plan, retained_names, first_bucket_name, packed_names):
    """Partition canonical recovery slots without opening any outcome report."""
    required={s['name'] for s in plan['slots'] if s['kind']!='preserved_original'}
    groups={'timeout_v2':[previous.first.worker.FAILED_NAME], 'retained_v2':list(retained_names),
        'bucket_first_v3':[first_bucket_name], 'bucket_remaining_v3':list(packed_names)}
    routes={}
    for backend,names in groups.items():
        require(len(names)==len(set(names)),'Duplicate routing name')
        for name in names:
            require(name in required and name not in routes,'Foreign/overlapping attempt routing')
            routes[name]=backend
    require(set(routes)==required,'Incomplete attempt routing')
    return routes


def actual_routes(plan):
    registry=read(first.originals.REGISTRY);decision=read(remaining.DECISION)
    first_decision=read(first.DECISION)
    require(registry['submitted_jobs']==len(registry['records'])==64
        and decision['jobs']==len(decision['rows'])==258
        and len(first_decision['rows'])==1,'Wrong routing registry counts')
    require(decision['original_v2_registry_sha256']==digest(first.originals.REGISTRY)
        and decision['first_bucket_result_sha256']==remaining.FIRST_RESULT_SHA
        and decision['original_v2_stop_sha256']==remaining.STOP_SHA==digest(remaining.old.OUT/'STOP.json'),
        'Routing decision/STOP changed')
    require(decision['strength_outcomes_used_for_decision'] is False
        and decision['failed_jobs_to_resubmit']==0 and decision['prior_failed_attempts_preserved'] is True,
        'Routing cannot erase failed attempts')
    slots={s['name']:s for s in plan['slots']}
    for item in decision['rows']+first_decision['rows']:
        require(item['name'] in slots and item['original_row_sha256']==slots[item['name']]['original_row_sha256']
            and item['prior_failed_attempts']==[] and item['reason']=='never_submitted', 'Changed routed row/history')
    routes=routing(plan,[r['name'] for r in registry['records']],first.NAME,[r['name'] for r in decision['rows']])
    require(Counter(routes.values())=={'timeout_v2':1,'retained_v2':64,'bucket_first_v3':1,'bucket_remaining_v3':258},
        'Actual recovery partition differs')
    return routes


def locations(name,backend):
    require(backend in BACKENDS,'Unknown attempt backend')
    if backend in ('timeout_v2','retained_v2'):return previous.locations(name)
    manager=first if backend=='bucket_first_v3' else remaining
    if backend=='bucket_first_v3':
        require(name==first.NAME,'Wrong first bucket name')
        folder=first.OUT;review=first.RESULT;bundle=first.PRE/'bundle'
    else:
        folder=remaining.OUT/'jobs'/remaining.attempt(name);review=folder/'review.json'
        bundle=remaining.PRE/'selected'/remaining.attempt(name)
    return {'folder':folder,'review':review,'source':manager.SOURCE,'bundle':bundle,
        'manager':manager,'collector':first.collection,'log':folder/'original.log'}


def inventory(plan=None,routes=None):
    plan=coverage.actual_plan() if plan is None else plan
    routes=actual_routes(plan) if routes is None else routes
    required={s['name']:s for s in plan['slots'] if s['kind']!='preserved_original'}
    require(set(routes)==set(required),'Incomplete routing inventory')
    available=[];missing=[]
    for name in plan['fixed_recovery_order']:
        slot=required[name];backend=routes[name];paths=locations(name,backend);folder=paths['folder']
        files=[folder/'launch.json',folder/'terminal.json',paths['review']]
        absent=[str(p.relative_to(ROOT)) for p in files if not p.is_file()]
        if absent:
            terminal=read(folder/'terminal.json') if (folder/'terminal.json').is_file() else None
            missing.append({'name':name,'backend':backend,'missing':absent,
                'terminal_stage':None if terminal is None else terminal['stage'],
                'failed_handle':terminal['job_id'] if terminal and terminal['stage']=='ERROR' else None})
            continue
        guard,terminal=read(files[0]),read(files[1])
        require(guard['job_id']==terminal['job_id'] and terminal['stage']=='COMPLETED'
            and terminal['public_configuration_verified'] is True,'Incomplete/unbound terminal review')
        available.append({'name':name,'backend':backend,'original_row_sha256':slot['original_row_sha256'],
            'original_failed_handle':previous.first.worker.FAILED_HANDLE if backend=='timeout_v2' else None,
            'job_id':guard['job_id'],'attempt_id':guard['attempt_id'],'stage':'COMPLETED','verified':True,
            'review_sha256':digest(paths['review'])})
    return {'available':available,'missing':missing,'required':len(required),'complete':not missing,
        'review_contents_loaded':False,'statistics_admitted':False}


def final_receipt(log):
    receipts=[]
    for line in log.splitlines():
        try:value=json.loads(line)
        except (ValueError,TypeError):continue
        if isinstance(value,dict) and 'bucket_final_evidence' in value:receipts.append(value)
    require(len(receipts)==1,'Missing/ambiguous bucket final receipt')
    return receipts[0]


def archive_binding(evidence,attempt):
    require(evidence['repo']=='coyotte508/powergrid-ai-germany-v1'
        and evidence['archive_path']=='archives/'+attempt+'-collected.tgz'
        and evidence['remote_archive_verified'] is True and evidence['format']=='tar.gz'
        and re.fullmatch('[a-f0-9]{40}',evidence['revision']),'Unpinned versioned collection archive')
    require(all(re.fullmatch('[a-f0-9]{64}',evidence[k]) for k in ('archive_sha256','manifest_sha256'))
        and type(evidence['archived_files']) is int and evidence['archived_files']>0,'Invalid versioned archive hashes')


def bucket_binding(reference,row,review,guard,terminal,receipt,expected,controls):
    require(reference['backend'] in ('bucket_first_v3','bucket_remaining_v3')
        and reference['name']==row['name'] and reference['original_row_sha256']==object_hash(row),'Wrong canonical bucket row')
    require(reference['stage']=='COMPLETED' and reference['verified'] is True
        and reference['original_failed_handle'] is None,'Unverified reference or invented original failure')
    require(review['job_id']==reference['job_id']==guard['job_id']
        and review['attempt_id']==reference['attempt_id']==guard['attempt_id']==expected['attempt_id']
        and review['original_name']==row['name']==guard['original_name']==expected['row']['name']
        and guard['original_row_sha256']==object_hash(row),'Bucket attempt identity differs')
    require(review['prior_failed_attempts']==guard['prior_failed_attempts']==expected['control']['prior_failed_attempts']==[]
        and expected['control']['reason']=='never_submitted','Unexpected/erased failure history')
    require(guard['source']==controls['source'] and guard['allocation']==first.worker.ALLOCATION
        and guard['transport']==first.worker.TRANSPORT and guard['automatic_job_retries'] is False,'Bucket launch settings differ')
    previous.terminal_binding(terminal,guard,controls['environment'],controls['bootstrap'])
    require(review['terminal']==terminal and review['launch_guard_sha256']==controls['guard_sha256']
        and review['source_descriptor_sha256']==controls['source_sha256']
        and review['manager_sha256']==controls['manager_sha256']
        and review['collector_sha256']==controls['collector_sha256'],'Bucket collector/launch binding differs')
    # Remaining jobs use a shared outer pack manifest and a separate selected-row
    # manifest. They must not be confused or accepted merely because names match.
    require(review['bundle_manifest_sha256']==controls['bundle_manifest_sha256']==expected['bundle_manifest_sha256']
        and review['admission_sha256']==expected['admission_sha256'],'Wrong selected-row preparation')
    require(review['verified'] is True and review['games']==row['shard']['games']
        and review['retained_episodes']==coverage.episodes(row)
        and review['qualification_eligible'] is False and review['qualified'] is False
        and review['reserved_final_seeds_used'] is False and review['versioned_archive_pending'] is False,
        'Wrong/incomplete bucket coverage or premature qualification')
    audit=review['review']['audit']
    require(review['review']['games']==row['shard']['games'] and audit['identity']==row['identity']
        and audit['expected']==row['shard'] and audit['all_receipts_verified'] is True
        and audit['counts']['rollout_caps']==0 and audit['reserved_final_seeds_used'] is False,'Wrong/capped raw review')
    require(receipt['attempt_id']==guard['attempt_id'] and receipt['bucket_final_evidence']==review['envelope_evidence'],
        'Original log and bucket envelope differ')
    require(receipt['status']['stage']=='child_complete_pending_independent_audit'
        and receipt['status']['original_name']==row['name']
        and receipt['status']['prior_failed_attempts']==[],'Original bucket child did not complete')
    first.worker.archives.checked_receipt(review['envelope_evidence'],guard['attempt_id']+'-final')
    archive_binding(review['versioned_collection_archive'],guard['attempt_id'])


def context(plan=None,routes=None):
    plan=coverage.actual_plan() if plan is None else plan
    routes=actual_routes(plan) if routes is None else routes
    prior=previous.context()
    require(prior['plan']==plan,'Canonical v2 plan changed')
    return {'plan':plan,'routes':routes,'previous':prior,'original_source':prior['original_source'],
        'sources':{'bucket_first_v3':first.source_checked(),'bucket_remaining_v3':remaining.source_checked()}}


def authenticate(reference,current):
    name=reference['name'];backend=reference['backend']
    require(current['routes'].get(name)==backend,'Unregistered attempt backend')
    if backend in ('timeout_v2','retained_v2'):
        return previous.authenticate(reference,current['previous'])
    paths=locations(name,backend);folder=paths['folder'];manager=paths['manager'];source=current['sources'][backend]
    row=next(r for r in current['original_source']['rows'] if r['name']==name)
    require(digest(paths['review'])==reference['review_sha256'],'Review bytes changed')
    review=read(paths['review']);terminal=read(folder/'terminal.json')
    if backend=='bucket_first_v3':
        guard=first.checked_guard(folder,source);bundle_sha=source['manifest_sha256']
        require(reference['review_sha256']==remaining.FIRST_RESULT_SHA and reference['job_id']=='6ae32f6741e90535df78a8a6',
            'First bucket proof substituted')
        environment=first.public_environment(source)
    else:
        guard=remaining.checked_guard(folder,source,row);remaining.result_checked(folder,source,row)
        index=read(remaining.PRE/'pack/index.json');bundle_sha=index['rows'][name]['bundle_manifest_sha256']
        environment=remaining.public_environment(source,row)
    expected=first.collection.reference_configuration(paths['bundle'],bundle_sha,first.ORIGINAL)
    controls={'source':source,'source_sha256':digest(paths['source']),'manager_sha256':digest(manager.__file__),
        'collector_sha256':digest(first.collection.__file__),'environment':environment,'bootstrap':manager.bootstrap(),
        'guard_sha256':digest(folder/'launch.json'),'bundle_manifest_sha256':bundle_sha}
    require(terminal['log_sha256']==digest(paths['log']),'Original bucket terminal log changed')
    receipt=final_receipt(paths['log'].read_text())
    bucket_binding(reference,row,review,guard,terminal,receipt,expected,controls)
    archive=review['versioned_collection_archive'];package=folder/(guard['attempt_id']+'-collected')
    # Bind actual local sealed bytes and every member, not only a success boolean.
    compressed=package.with_suffix('.tgz')
    require(digest(compressed)==archive['archive_sha256'],'Versioned collection bytes changed')
    pins=first.worker.archives.verify_archive(compressed,archive['manifest_sha256'])
    require(len(pins)+1==archive['archived_files'],'Versioned member count differs')
    first.worker.base.tree(package,'manifest.json',archive['manifest_sha256'])
    raw_review=read(folder/'raw-review.json')
    require(digest(folder/'raw-review.json')==pins['raw-review.json']
        and all(review[k]==v for k,v in raw_review.items() if k!='versioned_archive_pending')
        and raw_review['versioned_archive_pending'] is True,'Archived independent review differs')
    origin=read(package/'origin.json')
    require(origin['job_id']==guard['job_id'] and origin['terminal']==terminal and origin['source']==source
        and origin['launch_guard_sha256']==controls['guard_sha256']
        and origin['bucket_envelope']==review['envelope_evidence']
        and origin['bucket_checkpoints']==[c['evidence'] for c in review['checkpoint_archives']]
        and origin['new_games']==0 and origin['qualified'] is False,'Archived execution provenance differs')
    envelope=package/'envelope'
    require(read(envelope/'attempt.json')==expected and read(envelope/'run-status.json')==receipt['status']
        and digest(envelope/'manifest.json')==review['envelope_evidence']['manifest_sha256']
        and digest(envelope/'raw/manifest.json')==review['raw_manifest_sha256'],'Archived envelope control differs')
    require(digest(paths['review'])==reference['review_sha256'],'Review changed during authentication')
    # Explicit compatibility field for the unchanged canonical coverage gate;
    # authoritative receipts are never rewritten and bucket history stays intact.
    return {**review,'original_failed_handle':None}


def authenticate_complete(current=None,loader=None):
    plan=coverage.actual_plan() if current is None else current['plan']
    routes=actual_routes(plan) if current is None else current['routes']
    found=inventory(plan,routes)
    def lazy(ref):
        nonlocal current
        if current is None:current=context(plan,routes)
        return authenticate(ref,current)
    result=coverage.require_complete_assignments(plan,found['available'],lazy if loader is None else loader)
    require(result['recovery_shards']==324 and result['recovery_games']==7116,'Actual recovery coverage differs')
    return {**result,'authenticated_recovery_receipts':True,'assignment_hash':object_hash(found['available']),
        'routing_hash':object_hash(routes),'statistics_admitted':False,'raw_reaudit_required':True,'candidate_selected':False}


def inventory_summary(found):
    return {'required_recovery_receipts':found['required'],'available_recovery_receipts':len(found['available']),
        'missing_recovery_receipts':len(found['missing']),'available_by_backend':dict(Counter(r['backend'] for r in found['available'])),
        'missing_by_backend':dict(Counter(r['backend'] for r in found['missing'])),
        'failed_attempts_preserved':[{k:r[k] for k in ('name','backend','terminal_stage','failed_handle')}
            for r in found['missing'] if r['failed_handle']],
        'complete':found['complete'],'review_contents_loaded':False,'statistics_admitted':False}
