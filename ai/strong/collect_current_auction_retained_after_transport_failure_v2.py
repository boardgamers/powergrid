"""Collect only the 64 original retained attempts after their dispatcher stopped.

Preserve STOP and every failed attempt. No submission, retries, replacement games,
policy changes or complete-study claims. Remote observation errors remain unknown.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
import shutil

import manage_current_auction_remaining_v2 as m

OUT=m.ROOT/'ai/runs/current-auction-remaining-failure-inspection-v2'
REGISTRY=m.STRONG/'current-auction-remaining-dispatch-v2.json'


def original_bindings():
    source=m.source_checked();_,rows=m.plan();rows={r['name']:r for r in rows}
    registry=m.read(REGISTRY)
    m.require(registry['submitted_jobs']==64 and registry['submitted_games']==1280
        and registry['source_descriptor_sha256']==m.digest(m.SOURCE),'Wrong original retained batch')
    items=registry['records'];m.require(len(items)==len({r['job_id'] for r in items})==64,'Duplicate original handles')
    folders={p.name for p in (m.OUT/'jobs').iterdir()}
    m.require(folders=={r['attempt_id'] for r in items},'Another attempt appeared; inspect before collection')
    for item in items:
        row=rows[item['name']];folder=m.OUT/'jobs'/item['attempt_id']
        guard=m.checked_guard(folder,source,row)
        m.require(guard['job_id']==item['job_id'] and m.digest(folder/'launch.json')==item['launch_guard_sha256']
            and m.digest(folder/'launch-intent.json')==item['launch_intent_sha256'],'Original launch record changed')
    return source,rows,items


def cycle(limit=8):
    m.require(type(limit) is int and 0<=limit<=64,'Invalid collection bound')
    with m.exclusive(m.OUT,'cycle'):
        m.require((m.OUT/'STOP.json').exists(),'This collector requires the preserved dispatch STOP')
        stop_sha=m.digest(m.OUT/'STOP.json');source,rows,items=original_bindings()
        known=m.read(OUT/'initial-failed-originals.json')
        failures={r['name']:r for r in known['jobs']}
        failures_dir=OUT/'failures';failures_dir.mkdir(exist_ok=True)
        for p in failures_dir.glob('*.json'):
            item=m.read(p);m.require(item['name'] not in failures,'Duplicate preserved failure');failures[item['name']]=item
        api=m.HfApi();observed=[];audited=[];deferred=[];unknown=[];collected=0
        for item in items:
            row=rows[item['name']];folder=m.OUT/'jobs'/item['attempt_id']
            try:status=m.check_one(api,folder,source,row)
            except Exception as error:
                unknown.append({'name':row['name'],'job_id':item['job_id'],'observation_error_type':type(error).__name__});continue
            observed.append(status)
            if row['name'] in failures:
                m.require(not (folder/'review.json').exists(),'A preserved failed attempt cannot become success')
                continue
            if (folder/'review.json').exists():
                report=m.result_checked(folder,source,row);audited.append({'name':row['name'],'job_id':item['job_id'],'games':report['games']});continue
            if status['stage'] in m.WAITING:continue
            if collected>=limit or shutil.disk_usage(m.OUT).free < 10*1024**3:
                deferred.append(status);continue
            collected+=1
            try:report=m.collect_one(api,folder,source,row,status)
            except Exception as error:
                # A missing download is not a new failed HF execution. Preserve
                # the actual remote stage and collector diagnostic separately.
                failure={'name':row['name'],'job_id':item['job_id'],'stage':status['stage'],
                    'collection_error_type':type(error).__name__,'guard_sha256':m.digest(folder/'launch.json'),
                    'verified':False,'new_jobs':0,'qualified':False}
                log=folder/'original.log'
                if log.exists():
                    failure['log_sha256']=m.digest(log);receipts=[]
                    for line in log.read_text().splitlines():
                        try:value=json.loads(line)
                        except (ValueError,TypeError):continue
                        if isinstance(value,dict) and 'recovery_final_evidence' in value:receipts.append(value)
                    failure['final_receipt_count']=len(receipts)
                    if len(receipts)==1:failure['envelope_evidence']=receipts[0]['recovery_final_evidence']
                if (folder/'artifacts/run-status.json').exists():
                    failure['supervisor_status']=m.read(folder/'artifacts/run-status.json')
                    failure['raw_game_files']=len(list((folder/'artifacts/raw/job/evaluation').glob('game-*.json')))
                if status['stage']=='COMPLETED':
                    # A completed job's collection error needs inspection, not
                    # relabelling the job itself as ERROR or a game retry.
                    m.durable(OUT/(item['attempt_id']+'.collection-error.json'),failure)
                    unknown.append(failure)
                else:
                    m.save(failures_dir/(row['name']+'.json'),failure);failures[row['name']]=failure
                print(json.dumps({'preserved':row['name'],'hf_stage':status['stage'],'collector_error':type(error).__name__}),flush=True)
            else:
                audited.append({'name':row['name'],'job_id':item['job_id'],'games':report['games']})
                print(json.dumps({'audited':row['name'],'games':report['games']}),flush=True)
        m.require(m.digest(m.OUT/'STOP.json')==stop_sha,'Dispatch STOP changed during collection')
        report={'checked_at':m.now(),'registry_sha256':m.digest(REGISTRY),'source_sha256':m.digest(m.SOURCE),
            'stop_sha256':stop_sha,'observed':observed,'states':dict(Counter(s['stage'] for s in observed)),
            'audited':audited,'newly_collected':collected,'verified_jobs':len(audited),'verified_games':sum(r['games'] for r in audited),
            'preserved_failure_names':sorted(failures),'deferred_terminals':deferred,'unknown_observations_or_collections':unknown,
            'new_jobs':0,'automatic_retries':False,'complete':False,'qualified':False,'reserved_final_seeds_used':False}
        cycles=OUT/'collection-cycles';cycles.mkdir(exist_ok=True)
        m.save(cycles/(report['checked_at'].replace(':','-')+'.json'),report)
        m.durable(OUT/'collection-state.json',report)
        return {k:report[k] for k in ('checked_at','states','newly_collected','verified_jobs','verified_games','new_jobs')}|{
            'preserved_failures':len(failures),'deferred_terminals':len(deferred),'unknown':len(unknown)}


if __name__=='__main__':
    p=argparse.ArgumentParser(__doc__);p.add_argument('--limit',type=int,default=8);args=p.parse_args()
    print(json.dumps(cycle(args.limit)),flush=True)
