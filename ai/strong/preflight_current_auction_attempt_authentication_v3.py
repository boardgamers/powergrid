"""Exercise new routing with actual existing receipts, without repeating raw audits."""
from pathlib import Path
import json
from unittest.mock import patch

import current_auction_attempt_authentication_v3 as a

OUT=a.ROOT/'ai/runs/current-auction-attempt-authentication-preflight-v3'
REPORT=a.ROOT/'ai/strong/current-auction-attempt-authentication-preflight-v3.json'


def main():
    a.require(not OUT.exists() and not REPORT.exists(),'Inspect prior preflight before repeating')
    OUT.mkdir();plan=a.coverage.actual_plan();routes=a.actual_routes(plan);found=a.inventory(plan,routes)
    a.require(not found['complete'],'Do not run partial-preflight on a completed study')
    a.remaining.save(OUT/'intent.json',{'canonical_games':plan['canonical_games'],'new_jobs':0,'new_games':0,
        'raw_reaudits':0,'statistics_admitted':False,'code_sha256':a.digest(a.__file__)})
    with patch.object(a,'context') as context,patch.object(a,'authenticate') as loader:
        try:a.authenticate_complete()
        except ValueError as error:
            a.require(str(error)=='Incomplete recovery coverage; do not read outcomes','Unexpected refusal')
        else:raise ValueError('Incomplete study admitted')
        context.assert_not_called();loader.assert_not_called()
    current=a.context(plan,routes);proofs=[]
    # One existing record from each newly integrated real backend. This only
    # binds metadata and the first bucket job's already sealed archive bytes.
    # It performs no simulations, inference, raw-decision re-audit or comparison.
    for backend in ('retained_v2','bucket_first_v3'):
        reference=next(r for r in found['available'] if r['backend']==backend)
        review=a.authenticate(reference,current)
        a.require(review['games']==len(a.coverage.episodes(next(r for r in current['original_source']['rows']
            if r['name']==reference['name']))),'Wrong real reference coverage')
        proofs.append({'reference':reference,'games':review['games'],
            'all_original_receipts_verified_in_saved_review':review['review']['audit']['all_receipts_verified'],
            'archive':review.get('versioned_collection_archive',review['envelope_evidence']),
            'raw_reaudits':0,'statistics_admitted':False})
    test=a.ROOT/'ai/strong/test_current_auction_attempt_authentication_v3.py'
    log=a.ROOT/'ai/runs/current-auction-attempt-authentication-tests-v3-first.log'
    a.require('Ran 23 tests' in log.read_text() and log.read_text().rstrip().endswith('OK'),'Tests incomplete')
    report={'passed':True,'checked_at':a.remaining.now(),'canonical_shards':plan['canonical_shards'],
        'canonical_games':plan['canonical_games'],'canonical_game_keys_sha256':plan['game_keys_sha256'],
        'routing_sha256':a.object_hash(routes),'inventory':a.inventory_summary(found),'actual_receipt_bindings':proofs,
        'incomplete_entry_rejected_before_context':True,'incomplete_entry_review_loader_calls':0,
        'bucket_remaining_collection_not_yet_exercised':True,
        'new_tests':23,'code_sha256':a.digest(a.__file__),'preflight_sha256':a.digest(__file__),
        'test_sha256':a.digest(test),'test_log_sha256':a.digest(log),
        'frozen_input_hashes':{str(p.relative_to(a.ROOT)):a.digest(p) for p in
            (Path(a.previous.__file__),Path(a.coverage.__file__),Path(a.first.__file__),Path(a.remaining.__file__),
             Path(a.first.collection.__file__),a.first.SOURCE,a.remaining.SOURCE,a.remaining.DECISION,a.first.originals.REGISTRY)},
        'raw_reaudits':0,'new_jobs':0,'new_games':0,'inference_requests':0,'statistics_admitted':False,
        'candidate_selected':False,'qualified':False,'reserved_final_seeds_used':False}
    a.remaining.save(OUT/'routing.json',routes);a.remaining.save(OUT/'inventory.json',found)
    a.remaining.save(REPORT,report)
    print(json.dumps({'passed':True,'inventory':report['inventory'],'actual_bindings':len(proofs),'raw_reaudits':0}),flush=True)


if __name__=='__main__':main()
