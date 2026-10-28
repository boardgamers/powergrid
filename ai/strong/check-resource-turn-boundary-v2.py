"""Check the boundary correction on recorded turns and the reproduced failure.

Only public input preparation and local legal resource purchases are executed.
No inference, search continuations, complete games, HF jobs or win selection.
"""
from collections import Counter
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import time

from public_policy_development_job_v1 import read, digest

ROOT = Path(__file__).resolve().parents[2]
ARTIFACT = ROOT/'ai/runs/resource-turn-full-artifact-v3'
OUT = ROOT/'ai/runs/resource-turn-boundary-v2-recovered-v1'
RESULT = ROOT/'ai/strong/resource-turn-boundary-results-v2.json'
REPRO = ROOT/'ai/runs/resource-turn-boundary-failure-v1'
FULL = ROOT/'ai/runs/resource-turn-full-integration-v2'
PASS = {'name':'Pass','data':True}
RAW = ROOT/'ai/runs/resource-turn-runtime-hf-v1'
MANIFESTS = {
    'whole-2p':'2575b8e7a307efc70e14a7a20174ddf14e7b72592bb6b1877b56ccf2b9ad974c',
    'corrected-2p':'39d9c0a1f53e1bd4a177bb8a064808998e2f41e56c130b2bf9ae77fe7788b102',
    'anchored-2p':'466fad853bd4a04ccf0f5756af430321a4568cc9b049830277b1e5fcefabf7b1',
}


def save(path,value):
    with path.open('x') as stream:
        json.dump(value,stream,indent=2,allow_nan=False);stream.write('\n')


def main():
    assert not OUT.exists() and not RESULT.exists(), 'Inspect prior outcome before retry'
    assert read(REPRO/'assessment.json')['failure_reproduced']
    assert digest(REPRO/'failed-request.json') == '966cd4a7e99b90cc4fade18a322fed1adaf95f938ca1f08ed1da0b9fda926cdf'
    sys.path.insert(0,str(ARTIFACT/'policy'))
    from resource_turn_full_policy_v3 import load_artifact
    from resource_turn_full_arena_v3 import Process
    _,spec,_ = load_artifact(ARTIFACT)
    from hybrid_search import public_seed
    module_spec = importlib.util.spec_from_file_location('boundary_auditor_v2',ROOT/'ai/strong/resource_turn_anchor_verification_v2.py')
    module = importlib.util.module_from_spec(module_spec);module_spec.loader.exec_module(module)
    inputs = {}
    def remember(path,sha=None):
        actual=digest(path)
        if sha is not None: assert actual==sha
        inputs[str(path.relative_to(ROOT))]=actual
    remember(REPRO/'assessment.json');remember(REPRO/'failed-request.json')
    # All 334 turns from the established 33-game replay corpus, selected before
    # this defect was observed, then all resource requests in the three terminal
    # two-player pilots (including the failed pilot's saved prefix).
    remember(FULL/'assessment.json','7899bc2d35afb3d7486bd9940e4cc17245b0f516b6a7f46ccecbfc17e19d4650')
    full=read(FULL/'assessment.json'); streams=[]
    for path in sorted(FULL.glob('model-turn-*/decisions-*.jsonl')):
        remember(path,full['output_hashes'][str(path.relative_to(FULL))]);streams.append((path,'historical-model'))
    for name,sha in MANIFESTS.items():
        raw=RAW/('pg-resource-turn-runtime-v1-'+name)/'artifacts'
        remember(raw/'manifest.json',sha);manifest=read(raw/'manifest.json')
        assert set(manifest)=={str(p.relative_to(raw)) for p in raw.rglob('*') if p.is_file()}-{'manifest.json'}
        assert all(digest(raw/file)==value for file,value in manifest.items())
        for path in sorted((raw/'evaluation').glob('decisions-*.jsonl')):
            remember(path,manifest[str(path.relative_to(raw))]);streams.append((path,name))
    OUT.mkdir();(OUT/'sources').mkdir()
    code={}
    for name in ('check-resource-turn-boundary-v2.py','check-resource-turn-boundary-v2.cjs',
                 'resource-turn-anchor-v2.cjs','resource_turn_anchor_verification_v2.py'):
        path=ROOT/'ai/strong'/name;code[str(path.relative_to(ROOT))]=digest(path)
        shutil.copy2(path,OUT/'sources'/name)
    save(OUT/'design.json',{'input_hashes':inputs,'code_hashes':code,
        'selection':'All resource turns in the established 33-game corpus and all three terminal two-player pilots; reproduced failed entry plus every legal purchase path of depth two and one deterministic buy-until-forced path.',
        'new_hf_jobs':0,'new_inference':False,'search_rollouts':0,'new_full_games':0,
        'qualification_eligible':False,'reserved_final_seeds_used':False})
    worker=Process(['node',str(ROOT/'ai/strong/check-resource-turn-boundary-v2.cjs'),
        str(ARTIFACT/spec['runtime']['directory'])],OUT/'worker.stderr.log')
    began=time.perf_counter();counts=Counter();coverage={k:Counter() for k in ('players','rules','steps','families','entry_committed')}
    records=[]
    def call(op,request,**extra):
        row=worker.call({'op':op,'request':request,**extra})
        assert row['ok'],row.get('rejection')
        return row['result']
    def audit():
        return module.SamplingAudit(lambda q:call('prepare',{'state':q['state'],'player':q['player']}))
    def start(request,family):
        state=request['state'];counts['turns']+=1
        coverage['players'][len(state['players'])]+=1
        coverage['rules'][state['options']['variant']+('/sealed' if state['options']['fastBid'] else '/open')]+=1
        coverage['steps'][state['step']]+=1;coverage['families'][family]+=1
        coverage['entry_committed'][str(state['newTurn'])]+=1
        return call('prepare',request),audit()
    def inspect(request,reference,review):
        result=call('anchor',request);expected,_=review.expected(request)
        assert result['resourceTurnAnchor']==expected['sampling']['anchor']
        assert {k:v for k,v in result.items() if k!='resourceTurnAnchor'}==reference
        assert public_seed(result)==public_seed(reference)==expected['seed']
        counts['positions']+=1
        old=call('old',request)
        if 'result' in old:
            assert {k:v for k,v in old['result'].items() if k!='resourceTurnAnchor'}==reference
            counts['historical_anchor_input_parity']+=1
        else:
            assert 'Purchase history and turn boundary disagree' in old['error']
            counts['old_boundary_rejections']+=1
        assert call('anchor',request)==result;counts['duplicate_checks']+=1
        bad=deepcopy(request);bad['state']['newTurn']=not bad['state']['newTurn']
        assert worker.call({'op':'anchor','request':bad})['ok'] is False
        counts['corrupted_commit_flags_rejected']+=1
        records.append({'request_id':request.get('requestId'),'seed':expected['seed'],
            'anchor':result['resourceTurnAnchor']})
        return expected
    try:
        for path,family in streams:
            reference=review=None
            for line in path.read_text().splitlines():
                row=json.loads(line);request=row['request']
                if request['state']['phase']!='Resources':
                    assert review is None
                    continue
                if review is None:reference,review=start(request,family)
                expected=inspect(request,reference,review)
                if family=='anchored-2p':
                    search=row['response']['decision']['search']
                    if search is not None:
                        assert search['seed']==expected['seed']
                        sampling=deepcopy(expected['sampling']);sampling['mode']='turn-start-public-history-v1'
                        sampling['anchor']['revision']='resource-turn-public-history-anchor-v1'
                        del sampling['anchor']['boundaryCommitted']
                        assert search['sampling']==sampling
                        counts['original_search_seed_receipts_exact']+=1
                actions=row['executedActions'];current=request
                for index,move in enumerate(actions):
                    if index:inspect(current,reference,review)
                    if move==PASS:
                        assert index==len(actions)-1
                        review=reference=None
                    else:
                        assert move['name']=='BuyResource';review.buys+=1
                        if index+1<len(actions):current=call('advance',current,move=move)
            assert review is None, 'Unexpected incomplete recorded resource turn'
        failed=read(REPRO/'failed-request.json')
        reference,review=start(failed,'reproduced-failure')
        inspect(failed,reference,review)
        root=call('prepare',failed)
        buys=[m for m in root['moves'] if m['name']=='BuyResource']
        assert buys
        # Both independent boundaries and inverse reconstruction must survive
        # each actual legal first/second purchase without evaluating any policy.
        for first in buys:
            first_state=call('advance',failed,move=first);review=audit();review.expected(failed);review.buys=1
            inspect(first_state,reference,review);counts['local_purchase_edges']+=1
            for second in [m for m in call('prepare',first_state)['moves'] if m['name']=='BuyResource']:
                second_state=call('advance',first_state,move=second)
                review=audit();review.expected(failed);review.buys=2
                inspect(second_state,reference,review);counts['local_purchase_edges']+=1
            # A stateless helper cannot authenticate omitted purchases against
            # forged balances. The independent chronological auditor detects
            # an omitted log entry even when both commitment flags are false.
            bad=deepcopy(first_state);bad['state']['log'].pop()
            review=audit();review.expected(failed);review.buys=1
            try:review.expected(bad)
            except AssertionError:counts['chronological_log_omissions_rejected']+=1
            else:raise AssertionError('Auditor accepted omitted purchase')
        current=failed;review=audit();review.expected(failed)
        for _ in range(100):
            moves=[m for m in call('prepare',current)['moves'] if m['name']=='BuyResource']
            if not moves:break
            current=call('advance',current,move=moves[0]);review.buys+=1
            inspect(current,reference,review);counts['local_purchase_edges']+=1
        else:raise AssertionError('Unbounded resource purchases')
        # The auditor must never accept a first observation after buying began.
        try:audit().expected(current)
        except AssertionError:counts['late_audit_starts_rejected']+=1
        else:raise AssertionError('Auditor accepted late start')
        worker.close();worker=None
        assert coverage['families']['historical-model']==334
        assert counts['old_boundary_rejections']>=1
        assert all(digest(ROOT/name)==sha for name,sha in {**inputs,**code}.items())
        save(OUT/'positions.json',records)
        result={'passed':True,'counts':dict(counts),'coverage':{k:dict(v) for k,v in coverage.items()},
            'seconds':time.perf_counter()-began,'input_hashes':inputs,'code_hashes':code,
            'output_hashes':{str(p.relative_to(OUT)):digest(p) for p in OUT.rglob('*') if p.is_file()},
            'new_hf_jobs':0,'new_inference':False,'search_rollouts':0,'new_full_games':0,
            'qualification_eligible':False,'reserved_final_seeds_used':False,
            'limitations':'Mechanism and seed-receipt validation only. New helper/auditor are not integrated into a new pinned search policy or full-game artifact. Original failed pilot remains failed.'}
        save(OUT/'assessment.json',result)
        save(RESULT,{**result,'assessment_sha256':digest(OUT/'assessment.json')})
        print(json.dumps({k:result[k] for k in ('passed','counts','coverage','seconds')}),flush=True)
    except BaseException as error:
        save(OUT/'failure.json',{'error':type(error).__name__+': '+str(error),'counts':dict(counts)})
        raise
    finally:
        if worker is not None:worker.close()


if __name__=='__main__':main()
