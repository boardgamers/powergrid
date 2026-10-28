"""Exercise the unchanged filtered model on current-engine discount menus.

Thirty isolated decisions: ten recorded controls and twenty explicitly
counterfactual money fixtures. No continuation search, complete games or HF jobs.
"""
from datetime import datetime,timezone
import json
from pathlib import Path
import subprocess
import sys
import time

from public_policy_development_job_v1 import digest,read

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'ai/runs/current-engine-policy-v1'
RESULT=ROOT/'ai/strong/current-engine-policy-results-v1.json'
ARTIFACT=ROOT/'ai/runs/resource-turn-full-artifact-v4'
ENGINE=ROOT/'ai/runs/current-engine-compatibility-v1'


def save(path,value):
    with path.open('x') as stream:json.dump(value,stream,indent=2,allow_nan=False);stream.write('\n')


def main():
    assert not OUT.exists() and not RESULT.exists(),'Inspect previous diagnostic before retrying'
    design=read(ENGINE/'design.json');build=read(ENGINE/'build.json')
    engine_proof=ROOT/'ai/strong/current-engine-compatibility-evidence-v1.json';proof=read(engine_proof)
    assert proof['design_sha256']==digest(ENGINE/'design.json') and proof['build_sha256']==digest(ENGINE/'build.json')
    assert proof['archive']['remote_archive_verified'] is True
    assert all(digest(ENGINE/'source/engine'/n)==v for n,v in build['compiled_files'].items())
    assert digest(ARTIFACT/'manifest.json')==design['frozen_artifact_manifest_sha256']
    assert all(digest(ARTIFACT/n)==v for n,v in read(ARTIFACT/'manifest.json').items())
    worker=Path(__file__).with_suffix('.cjs');inputs={}
    for n in range(2,7):
        for episode in (1,3):
            name=f'ai/runs/resource-turn-full-integration-v2/model-turn-{n}p-economic/decisions-{episode}.jsonl'
            assert digest(ROOT/name)==design['recorded_inputs'][name];inputs[name]=digest(ROOT/name)
    OUT.mkdir();save(OUT/'design.json',{'created_at':datetime.now(timezone.utc).isoformat(),
        'selection':'First round>1 Recharged nomination with an active discount in fixed recorded episodes 1 and 3 at 2–6 players. Original control plus actor money changed to one or zero; no other economic field edited.',
        'current_engine_commit':proof['current_engine_commit'],'engine_evidence_sha256':digest(engine_proof),
        'artifact_manifest_sha256':digest(ARTIFACT/'manifest.json'),
        'artifact_descriptor_sha256':digest(ARTIFACT/'resource-full-descriptor.json'),
        'python_checker_sha256':digest(__file__),'node_checker_sha256':digest(worker),
        'recorded_inputs':inputs,'mode':'filter','policy_requests':30,'counterfactual_cases':20,
        'new_hf_jobs':0,'new_full_games':0,'qualification_eligible':False,'reserved_final_seeds_used':False})
    with (OUT/'fixture.log').open('x') as log:
        subprocess.run(['node',str(worker),str(ROOT),str(OUT)],cwd='/tmp',stdout=log,stderr=subprocess.STDOUT,check=True)
    fixtures=read(OUT/'inputs.json');assert len(fixtures)==30
    started=time.perf_counter();records=[]
    with (OUT/'policy.stderr.log').open('x') as log:
        process=subprocess.Popen([sys.executable,'-u','-B',str(ARTIFACT/'policy/resource_turn_full_policy_v4.py'),
            '--artifact',str(ARTIFACT),'--mode','filter'],cwd='/tmp',stdin=subprocess.PIPE,stdout=subprocess.PIPE,
            stderr=log,text=True,bufsize=1)
        def call(value):
            process.stdin.write(json.dumps(value,allow_nan=False)+'\n');process.stdin.flush()
            line=process.stdout.readline();assert line,'Policy process exited before reply'
            return json.loads(line)
        try:
            description=call({'op':'describe'});assert 'error' not in description
            save(OUT/'description.json',description)
            with (OUT/'decisions.jsonl').open('x') as receipts:
                for fixture in fixtures:
                    value=call({'op':'decide','request':fixture['request']})
                    ok='error' not in value
                    bound=ok and value['requestId']==fixture['request']['requestId'] and value['revision']==fixture['request']['revision']
                    legal=ok and value['kind']=='atomic' and value['move'] in fixture['legal']
                    identity=ok and value['identity']==description['identity'] and value['qualification_eligible'] is False
                    control=None
                    if fixture['originalDecision'] is not None and ok:
                        clean=lambda d:{k:v for k,v in d.items() if k!='elapsedMs'}
                        control=clean(value['decision'])==clean(fixture['originalDecision'])
                    record={'kind':fixture['kind'],'players':fixture['players'],'sealed':fixture['sealed'],
                        'request':fixture['request'],'response':value,'request_bound':bound,
                        'legal_current_move':legal,'identity_checked':identity,'recorded_control_exact':control}
                    receipts.write(json.dumps(record,allow_nan=False)+'\n');receipts.flush();records.append(record)
        finally:
            if process.stdin:process.stdin.close()
            try:code=process.wait(timeout=15)
            except subprocess.TimeoutExpired:process.terminate();process.wait(timeout=5);raise
    assert code==0
    errors=[{'requestId':r['request']['requestId'],'error':r['response'].get('error')} for r in records if 'error' in r['response']]
    valid=all(r['request_bound'] and r['legal_current_move'] and r['identity_checked'] for r in records)
    controls=[r for r in records if r['kind']=='recorded-control']
    rollouts=sum(r['response'].get('decision',{}).get('search',{}).get('rollouts',0)
        for r in records if isinstance(r['response'].get('decision',{}).get('search'),dict))
    assert rollouts==0
    outcomes={}
    for kind in ('recorded-control','discount-money-one','no-money-pass'):
        group=[r for r in records if r['kind']==kind]
        outcomes[kind]={'requests':len(group),'legal':sum(r['legal_current_move'] for r in group),
            'choose_plant':sum(r['response'].get('move',{}).get('name')=='ChoosePowerPlant' for r in group),
            'pass':sum(r['response'].get('move',{}).get('name')=='Pass' for r in group)}
    result={'completed':len(records)==30,'public_interface_compatible_on_fixtures':valid,
        'recorded_controls_exact':sum(r['recorded_control_exact'] is True for r in controls),'recorded_controls':len(controls),
        'actual_policy_requests':len(records),'errors':errors,'outcomes':outcomes,'rollouts':rollouts,
        'seconds':time.perf_counter()-started,'counterfactual_requests':20,
        'design_sha256':digest(OUT/'design.json'),'inputs_sha256':digest(OUT/'inputs.json'),
        'receipts_sha256':digest(OUT/'decisions.jsonl'),'description_sha256':digest(OUT/'description.json'),
        'new_hf_jobs':0,'new_full_games':0,'new_gradients':0,'qualification_eligible':False,'reserved_final_seeds_used':False,
        'interpretation':'Public filtered-model input/output compatibility and legality only. Synthetic cash interventions do not measure strategic quality; frozen continuation engine still predates nomination-affordability fix. Not full transition or strength validation.'}
    save(OUT/'assessment.json',result);save(RESULT,result);print(json.dumps(result),flush=True)


if __name__=='__main__':main()
