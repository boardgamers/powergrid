"""Read and verify the first observed recovery checkpoints, without game analysis.

This observation is not the final raw game audit or the final child-liveness
gate. It downloads immutable saved data and reuses the tested pair validator.
"""
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import re
from tempfile import TemporaryDirectory

import manage_current_auction_resource_recovery_v2 as m

OBSERVATION=m.OUT/'checks/retention-2026-10-29T09-15-16.664893+00-00.json'
OUT=m.ROOT/'ai/runs/current-auction-first-recovery-live-retention-v2'
REPORT=m.STRONG/'current-auction-first-recovery-live-retention-v2.json'


def main():
    require=m.require
    require(not OUT.exists() and not REPORT.exists(),'Inspect prior live-check outcome before retrying')
    source=m.source_checked();observation=m.read(OBSERVATION);before=m.check(source)
    require(observation['job_id']==before['job_id']=='6ae3083f3fb22a235dd56000'
        and observation['stage']=='RUNNING' and not observation['traceback_seen'],'Wrong live observation')
    config=m.collection.reference_configuration(m.PRE/'bundle',source['manifest_sha256'],m.ORIGINAL)
    row=config['row'];n=row['players'];shard=row['shard']
    expected=set(range(shard['start']*4*n,(shard['start']+shard['deals'])*4*n))
    receipts=observation['receipts'];require(len(receipts)==10,'Only the first fixed ten observations')
    require(all(set(r)=={'checkpoint_evidence','attempt_id'} and r['attempt_id']==m.worker.ATTEMPT for r in receipts),
        'Unexpected checkpoint receipt')
    names=[Path(r['checkpoint_evidence']['archive_path']).name.removesuffix('.tgz') for r in receipts]
    require(len(set(names))==len(names) and all(re.fullmatch(re.escape(m.worker.ATTEMPT)+r'-checkpoint-[0-9]{4}',name) for name in names),
        'Duplicate/foreign checkpoint archive')
    OUT.mkdir();m.save(OUT/'intent.json',{'observation_sha256':m.digest(OBSERVATION),
        'source_descriptor_sha256':m.digest(m.SOURCE),'code_sha256':m.digest(__file__),'new_hf_jobs':0,'new_games':0})
    m.save(OUT/'before.json',before)
    (m.OUT/'checkpoints').mkdir(exist_ok=True)

    def verify(item):
        name,receipt=item;evidence=receipt['checkpoint_evidence']
        m.collection.checked_evidence(evidence,name)
        folder=m.download(evidence,m.OUT/'checkpoints'/name)
        pins=m.read(folder/'manifest.json');metadata=m.read(folder/'checkpoint.json')
        require(metadata['version']==2 and metadata['context']==config['context']
            and metadata['raw_audited'] is False and metadata['execution_complete'] is False
            and metadata['qualified'] is False,'Checkpoint context/purpose changed')
        batch=metadata['episodes'];require(batch and batch==sorted(set(batch))
            and all(type(ep) is int and ep in expected for ep in batch),'Wrong planned episode set')
        require(set(metadata['pair_hashes'])=={str(ep) for ep in batch},'Missing checkpoint pair hashes')
        wanted={'checkpoint.json'}
        with TemporaryDirectory(prefix='pair-check-',dir=OUT) as tmp:
            for ep in batch:
                pair=m.worker.retention.capture_pair(folder,ep,Path(tmp),row)
                require(pair is not None and pair['hashes']==metadata['pair_hashes'][str(ep)],'Incomplete or changed original pair')
                for filename,sha in pair['hashes'].items():
                    require(pins[filename]==sha,'Pair differs from manifest');wanted.add(filename)
        require(set(pins)==wanted,'Unexpected checkpoint file set')
        return {'evidence':evidence,'episodes':batch,'bytes':sum((folder/name).stat().st_size for name in wanted),
            'context_and_pair_hashes_verified':True,'raw_game_audited':False}

    with ThreadPoolExecutor(max_workers=4) as pool:
        results=list(pool.map(verify,zip(names,receipts)))
    all_episodes=[ep for item in results for ep in item['episodes']]
    require(len(all_episodes)==len(set(all_episodes))==11,'Duplicate or unexpected retained episode count')
    m.save(OUT/'verified-checkpoints.json',results)
    after=m.check(source);m.save(OUT/'after.json',after)
    report={'passed':True,'job_id':before['job_id'],'checkpoints':len(results),'retained_game_pairs':len(all_episodes),
        'episodes':sorted(all_episodes),'expected_games':16,'checkpoint_archives':results,
        'original_failed_handle':m.worker.FAILED_HANDLE,'before':before,'after':after,
        'bytes_verified':sum(item['bytes'] for item in results),'observation_sha256':m.digest(OBSERVATION),
        'code_sha256':m.digest(__file__),'retention_validator_sha256':m.digest(m.worker.retention.__file__),
        'frozen_context_sha256':m.worker.object_hash(config['context']),
        'new_hf_jobs':0,'new_games':0,'new_inference':0,'strength_outcomes_aggregated':False,
        'complete_attempt_audited':False,'child_liveness_proof_pending_final_envelope':True,
        'remaining_rows_admitted':False,'qualified':False,'reserved_final_seeds_used':False,
        'previous_goal_turn_classification':'progress','current_goal_turn_classification':'progress','goal_status':'active'}
    m.save(REPORT,report)
    print(json.dumps({k:report[k] for k in ('passed','job_id','checkpoints','retained_game_pairs','episodes',
        'bytes_verified','after','complete_attempt_audited','remaining_rows_admitted')}),flush=True)


if __name__=='__main__':main()
