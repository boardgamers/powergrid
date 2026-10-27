"""Actual-model public producer checks on previously archived engineering inputs."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
PRIOR = ROOT/'ai/runs/resource-turn-search-v1'
RUNTIME = ROOT/'ai/runs/resource-replanning-job-source-prepared-v1/layout'
MODEL = ROOT/'ai/runs/policy-iteration-trained-8840u-prepared-v2/local-package-frozen-1/policy.onnx'
MODEL_SHA = '55331f43379e8fe89025d93b1a7a48c88e0ea39b4ebd3a7ef8240d4b62753530'
MANIFEST_SHA = 'cebda6cb0ed6a1eff28cad8cd02cb17e37bb62f59595b2237b989337b40a9415'


def read(path):return json.loads(path.read_text())
def digest(path):
    with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def lines(path):return [json.loads(line) for line in path.read_text().splitlines()]
def encode(value):return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)
def write(path,value):
    with path.open('x') as f:json.dump(value,f,indent=2,allow_nan=False);f.write('\n')
def semantic(value):return {k:v for k,v in value.items() if k!='elapsedMs'}


class Worker:
    def __init__(self,out,mode,horizon=2400):
        self.log=(out/f'{mode}-{horizon}.stderr.log').open('x')
        self.proc=subprocess.Popen([sys.executable,'-u','-B',str(ROOT/'ai/strong/resource_turn_public_policy_v1.py'),
            '--runtime',str(RUNTIME),'--manifest','resource-job-manifest.json','--manifest-sha256',MANIFEST_SHA,
            '--model',str(MODEL),'--model-sha256',MODEL_SHA,'--mode',mode,
            '--samples','4','--workers','1','--threads','1','--max-steps',str(horizon)],
            cwd='/tmp',stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=self.log,text=True,bufsize=1)

    def call(self,q):
        # Preserve the engine's insertion-ordered legal menu on the request wire.
        raw=q if isinstance(q,str) else json.dumps(q,separators=(',',':'),allow_nan=False)
        self.proc.stdin.write(raw+'\n');self.proc.stdin.flush()
        line=self.proc.stdout.readline()
        assert line,'Policy exited; inspect preserved stderr'
        return json.loads(line)

    def close(self):
        self.proc.stdin.close();code=self.proc.wait(timeout=30)
        self.proc.stdout.close();self.log.close();assert code==0

    def stop(self):
        if self.proc.poll() is None:self.proc.terminate();self.proc.wait(timeout=30)
        self.log.close()


def main(out):
    pins={
        PRIOR/'selection.json':'3116faa72800379c45d4ebba900b22d7c40cc71a4ef5cccb8dac9e3d1d9a8d4e',
        PRIOR/'trained/baselines.jsonl':'b72519cd01b39fd59e7bd18e7b653ed28363c354e8d638a332df62b907657e10',
        PRIOR/'trained/search.jsonl':'53b5433aad8d4360f5244161a24094a23c04a8c31930181c032b598804ac46e8',
        PRIOR/'runtime/ai/strong/fixtures/multiplayer-serving-v1.jsonl':'f1c97bf909e38e5df372a89d169d80f5a6f24c00dccefacd60b10b767f1fcfa0',
        ROOT/'ai/runs/resource-turn-transaction-v1/receipts.jsonl':'772835eb48f24b01c10fb38570b265faea545167ad82099010cc801fe7ccea0c',
        RUNTIME/'resource-job-manifest.json':MANIFEST_SHA,MODEL:MODEL_SHA}
    for p,sha in pins.items():assert digest(p)==sha,str(p)
    upstream=read(PRIOR/'trained/assessment.json')
    assert upstream['passed']
    for name in ['cap.json']:
        p=PRIOR/'trained'/name;assert digest(p)==upstream['artifacts'][name];pins[p]=digest(p)
    code={name:digest(ROOT/'ai/strong'/name) for name in [
        'resource_turn_public_policy_v1.py','resource-turn-exchange-worker-v1.cjs',
        'resource-turn-exchange-v1.cjs','resource-turn-transaction-v1.cjs',
        'check-resource-turn-public-policy-v1.py','probe-resource-turn-search-v1.py']}
    spec=importlib.util.spec_from_file_location('old_resource_verifier',ROOT/'ai/strong/probe-resource-turn-search-v1.py')
    verifier=importlib.util.module_from_spec(spec);spec.loader.exec_module(verifier)
    def verify_wire(q,result):
        # The historical in-process verifier indexed integer sample keys. JSON
        # object keys are strings; restore only that representation on a copy.
        decoded=copy.deepcopy(result)
        decoded['search']['worlds']={int(k):v for k,v in decoded['search']['worlds'].items()}
        verifier.verify(q,decoded)
    fixtures=lines(PRIOR/'runtime/ai/strong/fixtures/multiplayer-serving-v1.jsonl')
    baseline_gold=lines(PRIOR/'trained/baselines.jsonl');search_gold=lines(PRIOR/'trained/search.jsonl')
    selection=read(PRIOR/'selection.json')
    envelopes={r['label']:r['envelope'] for r in lines(ROOT/'ai/runs/resource-turn-transaction-v1/receipts.jsonl')}
    out.mkdir(exist_ok=False)
    workers=[];began=time.perf_counter()
    report={'passed':False,'baseline_positions':0,'baseline_decisions':0,'search_cases':0,
        'normal_rollouts':0,'normal_caps':0,'hidden_controls':0,'invalid_requests_rejected':0,
        'recovery_checks':0,'cap_controls':0,'new_full_games':0,'new_hf_jobs':0,'gradients':False,
        'qualification_eligible':False,'reserved_final_seeds_used':False,'identities':{}}

    def checked(q,value,mode,horizon=2400):
        assert 'error' not in value,value
        response,diagnostic=value['response'],value['diagnostics']
        specification=diagnostic['specification']
        assert response['contract']=='resource-turn-exchange-v1'
        assert response['requestId']==q['requestId'] and response['revision']==q['revision']
        assert response['qualification_eligible'] is False and diagnostic['qualification_eligible'] is False
        assert specification=={'revision':'resource-turn-public-policy-v1','mode':mode,
            'featureRevision':'4.3-strategic-correction','settings':{'samples':4,'workers':1,'threads':1,'max_steps':horizon},
            'modelSha256':MODEL_SHA,'runtimeManifestSha256':MANIFEST_SHA,
            'adapterHashes':{n:code[n] for n in ['resource_turn_public_policy_v1.py','resource-turn-exchange-worker-v1.cjs',
                'resource-turn-exchange-v1.cjs','resource-turn-transaction-v1.cjs']},'qualification_eligible':False}
        expected={'policySha256':hashlib.sha256(encode(specification).encode()).hexdigest(),
            'modelSha256':MODEL_SHA,'runtimeManifestSha256':MANIFEST_SHA}
        assert response['identity']==expected
        key=f'{mode}-{horizon}'
        if key in report['identities']:assert report['identities'][key]==expected
        report['identities'][key]=expected
        return response['transaction'],diagnostic

    try:
        model=Worker(out,'model');workers.append(model)
        with (out/'baselines.jsonl').open('x') as stream:
            for row in baseline_gold:
                q={**fixtures[row['fixture']]['request'],'requestId':f'fixture-{row["fixture"]}','revision':1}
                value=model.call(q);envelope,detail=checked(q,value,'model')
                assert detail['searchResult'] is None and detail['baselineDecisions']==row['decisions']
                assert envelope==envelopes[q['requestId']]
                stream.write(json.dumps({'fixture':row['fixture'],'output':value},allow_nan=False)+'\n')
                report['baseline_positions']+=1;report['baseline_decisions']+=len(row['decisions'])
                if report['baseline_positions']%100==0:print(json.dumps({'baselines':report['baseline_positions']}),flush=True)
        assert report['baseline_positions']==755 and report['baseline_decisions']==2251
        search=Worker(out,'search');workers.append(search)
        retained={}
        with (out/'search.jsonl').open('x') as stream:
            for row in search_gold:
                label=row['label'];q={**selection['selected'][label]['request'],'requestId':label,'revision':2}
                value=search.call(q);envelope,detail=checked(q,value,'search');actual=detail['searchResult']
                verify_wire(q,actual)
                assert semantic(actual)==semantic(row['result'])
                assert envelope==envelopes[label]
                assert envelope['actions']==actual['actions']==actual['bundles'][actual['selected']]['actions']
                assert actual['search']['truncated']==0
                stream.write(json.dumps({'label':label,'output':value},allow_nan=False)+'\n');stream.flush()
                retained[label]=value;report['search_cases']+=1
                report['normal_rollouts']+=actual['search']['evaluations']
                print(json.dumps({'search':label,'cases':report['search_cases']}),flush=True)
        assert report['search_cases']==23 and report['normal_rollouts']==1232
        label='late-6p-recharged-sealed';q=copy.deepcopy(selection['selected'][label]['request'])
        q.update(requestId='hidden-control',revision=3)
        q['state'].update(seed='private-poison',powerPlantsDeck=[{'number':9999}],
            powerPlantDeckAfterStep3=[{'number':9998}],hiddenLog=[{'private':True}],currentBid=9997)
        for player in q['state']['players']:player.update(bid=9996,lastMove={'name':'Bid','data':9995})
        value=search.call(q);envelope,detail=checked(q,value,'search')
        assert envelope==envelopes[label]
        assert semantic(detail['searchResult'])==semantic(retained[label]['diagnostics']['searchResult'])
        report['hidden_controls']+=1;report['hidden_control_rollouts']=detail['searchResult']['search']['evaluations']
        write(out/'hidden.json',value)
        cap=Worker(out,'search',1);workers.append(cap)
        q={**selection['selected'][label]['request'],'requestId':'cap-control','revision':4}
        value=cap.call(q);envelope,detail=checked(q,value,'search',1);actual=detail['searchResult']
        verify_wire(q,actual);assert semantic(actual)==semantic(read(PRIOR/'trained/cap.json'))
        assert actual['search']['truncated']>0 and actual['selected']==actual['baseline']
        assert envelope['actions']==actual['bundles'][actual['baseline']]['actions']
        assert envelope['actions']==[d['move'] for d in detail['baselineDecisions']]
        report['cap_controls']+=1;report['deliberate_cap_rollouts']=actual['search']['evaluations']
        report['deliberate_caps']=actual['search']['truncated'];write(out/'cap.json',value)
        q={**fixtures[baseline_gold[0]['fixture']]['request'],'requestId':'recovery','revision':5}
        invalid=[{**q,'revision':True},{**q,'player':-1},'null','{"state":NaN}']
        for bad in invalid:
            assert 'error' in model.call(bad);report['invalid_requests_rejected']+=1
        value=model.call(q);envelope,detail=checked(q,value,'model')
        assert envelope==envelopes['fixture-'+str(baseline_gold[0]['fixture'])]
        report['recovery_checks']+=1;write(out/'recovery.json',value)
        for worker in workers:worker.close()
        workers=[]
        for name,sha in code.items():assert digest(ROOT/'ai/strong'/name)==sha
        report.update(passed=True,seconds=time.perf_counter()-began,code_hashes=code,
            input_hashes={str(p.relative_to(ROOT)):sha for p,sha in pins.items()},
            artifacts={p.name:digest(p) for p in out.iterdir() if p.is_file()},
            scope='Actual model/search executed only on saved engineering cases through the new full-turn public producer. Old evaluated bundles and outcomes are unchanged; no new strength games, fitted settings, policy selection or deployment.')
        write(out/'assessment.json',report);print(json.dumps(report),flush=True)
    except BaseException as error:
        for worker in workers:worker.stop()
        write(out/'failure.json',{'error':type(error).__name__+': '+str(error),'partial_report':report})
        raise


if __name__=='__main__':
    main(Path(sys.argv[1]).resolve())
