"""Canonical confirmation coverage with explicit original/recovery provenance.

No game outcomes, inference, HF API or submission. Completeness of these
assignments only admits a later independent raw audit, never statistics by itself.
"""
from collections import Counter
from pathlib import Path
import re

import current_auction_resource_job_v2 as worker

require, read, digest, object_hash = worker.require, worker.read, worker.digest, worker.object_hash
ROOT=Path(__file__).resolve().parents[2]
TERMINAL_SHA='f5d8fb0386c706531bcc03a099f0d26b52b0b7a83d2f4babac31c417f2b12fa2'


def unique(values,key,label):
    index={}
    for value in values:
        name=key(value);require(name not in index,'Duplicate '+label);index[name]=value
    return index


def episodes(row):
    shard=row['shard'];n=row['players']
    require(type(n) is int and n in range(2,7) and shard['players']==n,'Wrong player count')
    require(shard['seed']==f'current-auction-confirmation-v1-{n}p','Wrong confirmation seeds')
    start,deals=shard['start'],shard['deals']
    require(type(start) is int and type(deals) is int and 0<=start<32 and deals>0
        and start+deals<=32 and shard['games']==deals*4*n,'Invalid planned episode interval')
    return list(range(start*4*n,(start+deals)*4*n))


def build_plan(source,terminal,decision,first_attempt):
    rows=unique(source['rows'],lambda r:r['name'],'canonical row')
    require(len(rows)==terminal['expected_jobs']==decision['full_canonical_shards'],'Canonical shard count differs')
    require(terminal['active_originals']==terminal['deferred_terminals']==[], 'Originals still active/uncollected')
    require(terminal['complete'] is False and terminal['qualified'] is False
        and terminal['reserved_final_seeds_used'] is False,'Wrong terminal snapshot purpose')
    audited=unique(terminal['audited_originals'],lambda r:r['name'],'audited original')
    failed=unique(terminal['failed_originals'],lambda r:r['name'],'failed original')
    unsubmitted=unique(terminal['unsubmitted_jobs'],lambda r:r,'unsubmitted original')
    require(not (set(audited)&set(failed) or set(audited)&set(unsubmitted) or set(failed)&set(unsubmitted)),
        'Original dispositions overlap')
    require(set(audited)|set(failed)|set(unsubmitted)==set(rows),'Original partition omits/introduces canonical rows')
    require(len(audited)==terminal['verified_jobs']==decision['original_audited_shards']
        and len(unsubmitted)==decision['never_submitted_rows'],'Original partition counts differ')
    require(list(failed)==[worker.FAILED_NAME] and failed[worker.FAILED_NAME]['job_id']==worker.FAILED_HANDLE
        and decision['original_failed_handle']==worker.FAILED_HANDLE,'The known original failure must be preserved')
    bad=failed[worker.FAILED_NAME]
    require(bad['verified'] is False and bad['stage']=='ERROR' and bad['row']==rows[worker.FAILED_NAME],
        'Failed original cannot silently become audited')
    require(decision['source_sha256']==worker.SOURCE_SHA and decision['strength_outcomes_used_for_decision'] is False
        and decision['original_failure_erased'] is False and decision['frozen_inputs_changed'] is False,
        'Recovery decision changes scientific inputs')
    fixed=unique(decision['fixed_recovery_rows'],lambda r:r['name'],'recovery row')
    require(set(fixed)==set(failed)|set(unsubmitted) and len(fixed)==decision['recovery_rows'],
        'Recovery cannot replay an audited row or omit missing coverage')
    require(decision['fixed_recovery_rows'][0]['name']==worker.FAILED_NAME,'First recovery must remain the known failed shard')
    slots=[];keys=set();handles=set();counts=Counter();games=Counter();stages=Counter()
    for name,row in rows.items():
        eps=episodes(row);identity=object_hash(row)
        require(row['shard']['name']==name,'Canonical name differs from shard')
        game_keys={(row['arm'],row['shard']['group'],ep) for ep in eps}
        require(not keys.intersection(game_keys),'Overlapping canonical games');keys.update(game_keys)
        if name in audited:
            original=audited[name];kind='preserved_original'
            require(original['stage'] in ('COMPLETED','ERROR'),'Invalid audited original status')
        else:
            record=fixed[name];original=failed.get(name);kind='failed_original_recovery' if original else 'first_execution'
            require(record['original_row_sha256']==identity and record['games']==len(eps),'Frozen recovery row changed')
            require(record['original_handle']==(original['job_id'] if original else None)
                and record['reason']==('original_timeout_missing_raw_data' if original else 'never_submitted'),
                'Recovery disposition differs from original evidence')
        if original:
            handle=original['job_id']
            require(re.fullmatch('[a-f0-9]{24}',handle) and handle not in handles,'Duplicate/invalid original handle')
            handles.add(handle);stages[original['stage']]+=1
        counts[kind]+=1;games[kind]+=len(eps)
        slots.append({'name':name,'kind':kind,'arm':row['arm'],'players':row['players'],
            'original_row_sha256':identity,'shard':row['shard'],'episodes':eps,'original':original})
    require(sum(games.values())==len(keys)==source['games']==decision['full_canonical_games'],'Canonical game count differs')
    require(games['preserved_original']==decision['original_audited_games']
        and games['failed_original_recovery']+games['first_execution']==decision['recovery_unique_games'],
        'Preserved/recovery game counts differ')
    require(sum(r['stage']=='COMPLETED' for r in audited.values())==decision['hf_completed_audited']
        and sum(r['stage']=='ERROR' for r in audited.values())==decision['hf_error_complete_data_audited'],
        'Original error recoveries omitted')
    require(first_attempt['attempt_id']==worker.ATTEMPT
        and first_attempt['original_failed_handle']==worker.FAILED_HANDLE
        and re.fullmatch('[a-f0-9]{24}',first_attempt['job_id']) and first_attempt['job_id'] not in handles,
        'First recovery must have its own exact admitted handle')
    return {'version':2,'source_sha256':worker.SOURCE_SHA,'decision_sha256':worker.DECISION_SHA,
        'canonical_shards':len(slots),'canonical_games':len(keys),'game_keys_sha256':object_hash(sorted(keys)),
        'shards_by_disposition':dict(counts),'games_by_disposition':dict(games),
        'original_hf_status_counts':dict(stages),'original_failure_preserved':bad,
        'first_recovery':first_attempt,
        'fixed_recovery_order':[r['name'] for r in decision['fixed_recovery_rows']], 'slots':slots,
        'qualified':False,'reserved_final_seeds_used':False,'submission_admitted':False,'statistics_admitted':False}


def actual_plan():
    source_path=ROOT/'ai/strong/current-auction-grid-source-v1.json'
    decision_path=ROOT/'ai/strong/current-auction-resource-recovery-decision-v2.json'
    require(digest(source_path)==worker.SOURCE_SHA and digest(decision_path)==worker.DECISION_SHA,'Frozen source/decision changed')
    decision=read(decision_path);terminal_path=ROOT/decision['original_terminal_cycle']
    require(digest(terminal_path)==TERMINAL_SHA==decision['original_terminal_cycle_sha256'],'Terminal snapshot changed')
    guard_path=ROOT/'ai/runs/current-auction-resource-recovery-hf-v2/launch.json'
    supervisor_path=ROOT/'ai/strong/current-auction-resource-supervisor-source-v2.json'
    guard=read(guard_path);supervisor=read(supervisor_path)
    require(guard['source']==supervisor and supervisor['remote_archive_verified'] is True
        and guard['allocation']==worker.ALLOCATION and guard['automatic_retries'] is False,
        'Actual recovery launch/publication changed')
    require(guard['job_id']=='6ae3083f3fb22a235dd56000','Do not substitute another first recovery')
    plan=build_plan(read(source_path),read(terminal_path),decision,
        {k:guard[k] for k in ('job_id','attempt_id','original_failed_handle')})
    require(plan['canonical_shards']==944 and plan['canonical_games']==26880
        and plan['shards_by_disposition']=={'preserved_original':620,'failed_original_recovery':1,'first_execution':323},
        'Actual confirmation partition differs')
    return {**plan,'input_hashes':{str(p.relative_to(ROOT)):digest(p) for p in
        (source_path,decision_path,terminal_path,guard_path,supervisor_path,Path(__file__))}}


def require_complete_assignments(plan,attempts,load_review):
    """Check all attempt references before reading a single review/outcome.

The loader must authenticate each reference's launch, admission and full receipt.
Returned reviews still require complete raw re-auditing before statistics. This
function cannot turn coverage flags or synthetic test evidence into strength.
"""
    required={slot['name']:slot for slot in plan['slots'] if slot['kind']!='preserved_original'}
    indexed=unique(attempts,lambda a:a['name'],'recovery assignment')
    require(set(indexed)==set(required),'Incomplete recovery coverage; do not read outcomes')
    first=indexed[worker.FAILED_NAME]
    require(all(first[k]==value for k,value in plan['first_recovery'].items()),
        'First recovery differs from the exact admitted attempt')
    original_handles={s['original']['job_id'] for s in plan['slots'] if s['original']}
    handles=set(original_handles);attempt_ids=set()
    for name,attempt in indexed.items():
        slot=required[name]
        require(attempt['original_row_sha256']==slot['original_row_sha256'],'Recovery assignment changed planned game row')
        require(attempt['original_failed_handle']==(worker.FAILED_HANDLE if slot['kind']=='failed_original_recovery' else None),
            'Recovery erased failure or invented original handle')
        handle=attempt['job_id'];identity=attempt['attempt_id']
        require(re.fullmatch('[a-f0-9]{24}',handle) and handle not in handles,'Duplicate/original recovery handle')
        require(isinstance(identity,str) and re.fullmatch('[a-z0-9_-]+',identity)
            and identity not in attempt_ids,'Duplicate/invalid attempt identity')
        require(attempt['stage']=='COMPLETED' and attempt['verified'] is True,'Recovery is not terminal and independently verified')
        require(re.fullmatch('[a-f0-9]{64}',attempt['review_sha256']),'Unpinned recovery review')
        handles.add(handle);attempt_ids.add(identity)
    reviews={}
    for name in plan['fixed_recovery_order']:
        attempt=indexed[name];slot=required[name];review=load_review(attempt)
        require(review['verified'] is True and review['original_name']==name and review['job_id']==attempt['job_id']
            and review['attempt_id']==attempt['attempt_id'] and review['original_failed_handle']==attempt['original_failed_handle'],
            'Loaded recovery review differs from assignment')
        require(review['games']==len(slot['episodes']) and review['retained_episodes']==slot['episodes'],
            'Recovery omitted/duplicated/substituted planned episodes')
        require(review['qualified'] is False and review['reserved_final_seeds_used'] is False
            and review['review']['audit']['all_receipts_verified'] is True
            and review['review']['audit']['counts']['rollout_caps']==0,'Unverified/capped recovery or wrong purpose')
        reviews[name]=review
    return {'coverage_complete':True,'recovery_shards':len(reviews),
        'recovery_games':sum(r['games'] for r in reviews.values()),'reviews':reviews,
        'original_failure_preserved':plan['original_failure_preserved'],
        'statistics_admitted':False,'raw_reaudit_required':True,'qualified':False,'reserved_final_seeds_used':False}
