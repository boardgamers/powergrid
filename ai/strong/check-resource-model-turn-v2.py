"""Actual frozen-model inference with corrected public deck metadata.

Uses the same predetermined 20 recorded roots; independently compares each input
and legal menu with eight complete sampled states. Does not play full games.
"""
import json
from pathlib import Path
import subprocess
import sys
import time

from public_policy_development_job_v1 import read,digest

ROOT=Path(__file__).resolve().parents[2]
RUNTIME=ROOT/'ai/runs/resource-replanning-job-source-prepared-v1/layout'
OUT=ROOT/'ai/runs/resource-model-turn-v2'
RESULT=ROOT/'ai/strong/resource-model-turn-results-v2.json'
MODEL=ROOT/'ai/runs/policy-iteration-trained-8840u-prepared-v2/local-package-frozen-1/policy.onnx'
MODEL_SHA='55331f43379e8fe89025d93b1a7a48c88e0ea39b4ebd3a7ef8240d4b62753530'
MANIFEST_SHA='cebda6cb0ed6a1eff28cad8cd02cb17e37bb62f59595b2237b989337b40a9415'
ROOT_FILES={
 'resource-turn-full-integration-v1':'0451d6e1189a9c0008386efc13cbcff0d54ab28290a521b19f42fb243b86f227',
 'resource-turn-full-integration-recovered-v1':'61e59190b8084292d757e06febe9a6fa847a183bf6ce1fc80c71bab5ec77b40a'}


def write(path,value):
    with path.open('x') as stream:json.dump(value,stream,indent=2,allow_nan=False);stream.write('\n')


def main():
    assert not OUT.exists() and not RESULT.exists(),'Inspect existing check before repeating'
    assert digest(RUNTIME/'resource-job-manifest.json')==MANIFEST_SHA and digest(MODEL)==MODEL_SHA
    hashes=read(RUNTIME/'resource-job-manifest.json')
    assert all(digest(RUNTIME/name)==sha for name,sha in hashes.items())
    sys.path.insert(0,str(RUNTIME/'ai/strong'))
    from hybrid_search import Model,predict_batch
    assert digest(Path(sys.modules['hybrid_search'].__file__))==hashes['ai/strong/hybrid_search.py']
    model=Model(MODEL,threads=1);assert model.sha256==MODEL_SHA
    roots=[];inputs={}
    for name,sha in ROOT_FILES.items():
        p=ROOT/'ai/runs'/name/'search-roots.jsonl';assert digest(p)==sha;inputs[str(p.relative_to(ROOT))]=sha
        roots.extend(json.loads(line) for line in p.read_text().splitlines())
    assert [(r['players'],r['episode']) for r in roots]==[(n,e) for n in range(2,7) for e in range(4)]
    OUT.mkdir();began=time.perf_counter();cases=[];counts={'turns':0,'model_decisions':0,'private_state_feature_checks':0,
        'purchases':0,'changed_plans':0,'changed_initial_decisions':0}
    code={str((ROOT/'ai/strong'/name).relative_to(ROOT)):digest(ROOT/'ai/strong'/name) for name in (
        'resource-model-turn-v2.cjs','check-resource-model-turn-v2.cjs','check-resource-model-turn-v2.py')}
    write(OUT/'design.json',{'scope':'Fix only public cardsLeft/nextCardWeak after simulated Resources purchases; exact frozen model and 20 predetermined roots.',
        'code_hashes':code,'inputs':inputs,'model_sha256':MODEL_SHA,'runtime_manifest_sha256':MANIFEST_SHA,
        'samples_per_root':8,'new_hf_jobs':0,'rollouts':0,'new_full_game_trajectories':0,'qualification_eligible':False})
    err=(OUT/'worker.stderr.log').open('x')
    worker=subprocess.Popen(['node',str(ROOT/'ai/strong/check-resource-model-turn-v2.cjs'),str(RUNTIME)],
        stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=err,text=True,bufsize=1)
    def call(value):
        worker.stdin.write(json.dumps(value,allow_nan=False)+'\n');worker.stdin.flush()
        line=worker.stdout.readline();assert line,'Checker exited; inspect preserved stderr'
        return json.loads(line)
    try:
        with (OUT/'turns.jsonl').open('x') as stream:
            for root in roots:
                reference=root['recorded_atomic_decision']['resourcePlan'];trace=[]
                reply=call({'op':'reset','request':root['request'],'seed':reference['search']['seed'],'samples':8})
                while not reply['done']:
                    index=predict_batch(model,[reply['observation']])[0]
                    trace.append({'index':index,'move':reply['moves'][index],
                        'publicMetadata':reply['publicMetadata'],'privateStateFeatureChecks':reply['privateStateFeatureChecks']})
                    reply=call({'op':'step','index':index})
                actions=[r['move'] for r in trace];assert actions==reply['actions']
                old=[r['move'] for r in reference['baselineDecisions']]
                assert trace[0]['index']==reference['baselineDecisions'][0]['index'] and actions[0]==old[0]
                case={'players':root['players'],'episode':root['episode'],'request':root['request'],
                    'corrected_trace':trace,'corrected_actions':actions,'historical_actions':old,
                    'plan_changed':actions!=old,'checks':reply['privateStateFeatureChecks'],
                    'atomic_purchases':reply['atomicPurchases']}
                counts['turns']+=1;counts['model_decisions']+=len(trace);counts['private_state_feature_checks']+=reply['privateStateFeatureChecks']
                counts['purchases']+=reply['atomicPurchases'];counts['changed_plans']+=actions!=old
                stream.write(json.dumps(case,allow_nan=False)+'\n');stream.flush();cases.append({k:v for k,v in case.items() if k!='request'})
                print(json.dumps({'turns_checked':counts['turns'],'expected':20}),flush=True)
        worker.stdin.close();assert worker.wait(timeout=30)==0;err.close()
        assert all(digest(ROOT/name)==sha for name,sha in {**code,**inputs}.items())
        report={'passed':True,'counts':counts,'cases':cases,'input_hashes':inputs,'code_hashes':code,
            'model_sha256':MODEL_SHA,'runtime_manifest_sha256':MANIFEST_SHA,'seconds':time.perf_counter()-began,
            'output_hashes':{p.name:digest(p) for p in OUT.iterdir() if p.is_file()},
            'new_hf_jobs':0,'rollouts':0,'new_full_game_trajectories':0,'gradients':False,
            'qualification_eligible':False,'reserved_final_seeds_used':False,
            'interpretation':'Actual model input features and legal menus agree with eight complete sampled states after every corrected public purchase on 20 roots. Plan changes are not evidence of strength improvement. The corrected primitive is not integrated into a full-game artifact yet.'}
        write(OUT/'assessment.json',report);write(RESULT,{**report,'assessment_sha256':digest(OUT/'assessment.json')})
        print(json.dumps({k:v for k,v in report.items() if k not in ('cases','input_hashes','code_hashes','output_hashes')}),flush=True)
    except BaseException as error:
        if worker.poll() is None:worker.terminate();worker.wait(timeout=30)
        err.close();write(OUT/'failure.json',{'error':type(error).__name__+': '+str(error),'counts':counts});raise


if __name__=='__main__':main()
