"""Four predeclared full-game execution smokes; no strength estimate or HF launch."""
from concurrent.futures import ProcessPoolExecutor,as_completed
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[2];BASE=ROOT/'ai/runs/resource-replanning-v1'
def read(p):return json.loads(p.read_text())
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,d):p.write_text(json.dumps(d,indent=2,allow_nan=False)+'\n')


def play_one(case):
    runtime=BASE/'runtime';sys.path.insert(0,str(runtime/'ai/strong'))
    spec=importlib.util.spec_from_file_location('resource_game_driver',runtime/'ai/strong/evaluate-resource-replanning-v1.py')
    driver=importlib.util.module_from_spec(spec);spec.loader.exec_module(driver)
    model=ROOT/'ai/runs/policy-iteration-trained-8840u-prepared-v2/local-package-frozen-1/policy.onnx'
    out=BASE/'games'/case['label'];out.mkdir(exist_ok=False)
    config={**case,'model':str(model),'model_sha256':digest(model),'runtime':str(runtime),
        'arm':'resource-filter','samples':4,'search_workers':1,'output':str(out),'opponent_model':None}
    write(out/'config.json',config)
    result=driver.play(config,case['episode'])
    assert not result['terminal']['truncated'] and result['rollout_caps']==0
    decisions=[json.loads(line) for line in (out/f"decisions-{case['episode']}.jsonl").open()]
    assert len(decisions)==result['decisions']
    resource_decisions=rollouts=0
    for i,row in enumerate(decisions):
        assert row['decision']==i+1 and row['arm']=='resource-filter'
        assert row['executionMode']=='stateless-atomic-resource-replanning-v1'
        if row['resourcePlan']:
            plan=row['resourcePlan'];assert row['phase']=='resources' and row['move']==plan['firstMove']
            assert row['search']==plan['search'] and row['search']['usable'] and not row['search']['truncated']
            assert row['modelProposal']==plan['baselineDecisions'][0]['index']
            assert row['move']==plan['actions'][0] and len(plan['receipts'])==row['search']['evaluations']
            resource_decisions+=1;rollouts+=row['search']['evaluations']
        else:assert row['search'] is None
    assert resource_decisions>0 and rollouts==result['rollouts']
    terminal=result['terminal'];assert terminal['seat']==0 and terminal['playerCount']==case['players']
    assert terminal['roles']==['learner']+['economic']*(case['players']-1)
    assert terminal['variant']==('recharged' if case['episode']%2 else 'original')
    assert terminal['sealed']==(case['episode']%4<2)
    assert terminal['gameSeed']==case['seed']+'-0'
    scores=[(p['powered'],p['money'],p['cities']) for p in terminal['final']['players']]
    winners=[i for i,score in enumerate(scores) if score==max(scores)]
    values=[1/len(winners) if i in winners else 0 for i in range(case['players'])]
    assert values==terminal['value'] and terminal['win']==values[0]
    proof={'label':case['label'],'result':result,'resource_decisions':resource_decisions,
        'receipt_sha256':digest(out/f"decisions-{case['episode']}.jsonl"),'config_sha256':digest(out/'config.json'),
        'passed':True,'qualification_eligible':False}
    write(out/'verified.json',proof)
    return proof


def main():
    prep=read(BASE/'preparation.json')
    for name,sha in {**prep['runtime_hashes'],**prep['new_files']}.items():assert digest(BASE/'runtime'/name)==sha
    for name,sha in read(ROOT/'ai/strong/population-hybrid-development-plan-v1.json')['dependency_hashes'].items():assert digest(ROOT/name)==sha
    assert read(BASE/'checks-v2/assessment.json')['passed']
    cases=read(BASE/'selection.json')['game_smokes'];assert len(cases)==4
    out=BASE/'games';out.mkdir(exist_ok=False);records=[];errors=[];start=time.perf_counter()
    try:
        with ProcessPoolExecutor(max_workers=2) as pool:
            futures={pool.submit(play_one,case):case['label'] for case in cases}
            for future in as_completed(futures):
                label=futures[future]
                try:
                    row=future.result();records.append(row)
                    print({'game':label,'resource_decisions':row['resource_decisions'],
                        'rollouts':row['result']['rollouts'],'seconds':row['result']['seconds']},flush=True)
                except Exception as error:
                    errors.append({'label':label,'error':repr(error)});print(errors[-1],flush=True)
        assert not errors and len(records)==4
    finally:
        report={'passed':not errors and len(records)==4,'checker_sha256':digest(Path(__file__)),
            'preparation_sha256':digest(BASE/'preparation.json'),'selection_sha256':digest(BASE/'selection.json'),
            'records':sorted(records,key=lambda r:r['label']),'errors':errors,'seconds':time.perf_counter()-start,
            'scope':'Four fixed full-game integration smokes against economic, only seat0, 2p/6p original-open and Recharged-sealed. Not a strength estimate, candidate screen or final qualification.',
            'new_engineering_games':4,'new_strength_games':0,'new_hf_jobs':0,'gradients':False,
            'qualification_eligible':False,'reserved_final_seeds_used':False}
        write(out/'assessment.json',report)


if __name__=='__main__':main()
