"""Actual-model resource search on frozen engineering fixtures, never strength games."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT/'ai/runs/resource-turn-search-v1'


def read(path):return json.loads(path.read_text())
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def write(path,value):path.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n')
def semantic(result):return {k:v for k,v in result.items() if k!='elapsedMs'}


def verify(q,result):
    assert not result['qualification_eligible']
    s=result['search'];bundles=result['bundles'];baseline=result['baseline']
    assert bundles[baseline]['actions']==[d['move'] for d in result['baselineDecisions']]
    assert result['actions']==bundles[result['selected']]['actions']
    assert result['firstMove']==result['actions'][0]
    assert len({b['id'] for b in bundles})==len(bundles)
    g=q['state'];p=g['players'][q['player']];resources=['coal','oil','garbage','uranium']
    by_id={b['id']:b for b in bundles};assert '0,0,0,0' in by_id
    for b in bundles:
        assert b['actions'][-1]=={'name':'Pass','data':True}
        counts=[sum(a=={'name':'BuyResource','data':{'resource':r}} for a in b['actions'][:-1]) for r in resources]
        assert sum(counts)==len(b['actions'])-1 and counts==b['counts']
        assert b['id']==','.join(map(str,counts))
        costs=[]
        for r,n in zip(resources,counts):
            prices=g[r+'Prices'];left=g[r+'Market'];assert n<=left
            costs.extend(prices[len(prices)-left:len(prices)-left+n])
        assert sum(costs)==b['cost']<=p['money']
    rows=result['receipts'];assert len(rows)==s['evaluations']==len(bundles)*s['samples']
    outcomes={b['id']:[] for b in bundles};caps=0
    for i,row in enumerate(rows):
        sample,index=divmod(i,len(bundles));b=bundles[index]
        assert row['env']==i and row['sample']==sample and row['actionIndex']==index
        assert row['resourceTurn']['bundleId']==b['id'] and row['resourceTurn']['actions']==b['actions']
        expected={'money':p['money']-b['cost'],
            'stock':[p[r+'Left']+n for r,n in zip(resources,b['counts'])],
            'market':[g[r+'Market']-n for r,n in zip(resources,b['counts'])]}
        assert row['resourceTurn']['afterPurchases']==expected
        assert sum(row['policyDecisions'].values())==row['steps']<=s['maxSteps']
        assert row['initialBelief']==s['worlds'][sample]['initialBelief']
        if row['truncated']:
            assert row['value'] is None and row['terminal'] is None;caps+=1
        else:
            scores=[(p['powered'],p['money'],p['cities']) for p in row['terminal']]
            best=max(scores);winners=[i for i,score in enumerate(scores) if score==best]
            expected=1/len(winners) if q['player'] in winners else 0
            assert row['value']==expected
        outcomes[b['id']].append(row['value'])
    assert outcomes==s['sampleOutcomes'] and caps==s['truncated']
    if caps:
        assert not s['usable'] and s['meanCredits'] is None and result['selected']==baseline
    else:
        means={key:sum(values)/len(values) for key,values in outcomes.items()}
        assert means==s['meanCredits']
        choice=max(range(len(bundles)),key=lambda i:(means[bundles[i]['id']],i==baseline,-i))
        assert choice==result['selected'] and s['usable']


def main():
    prep=read(BASE/'preparation.json');runtime=BASE/'runtime'
    for name,sha in {**prep['runtime_hashes'],**prep['new_files']}.items():assert digest(runtime/name)==sha
    for name,sha in read(ROOT/'ai/strong/population-hybrid-development-plan-v1.json')['dependency_hashes'].items():
        assert digest(ROOT/name)==sha
    assert read(BASE/'contract/assessment.json')['passed']
    sys.path.insert(0,str(runtime/'ai/strong'))
    from resource_turn_search_v1 import ResourceTurnSearch
    from hybrid_search import Model,Node,predict_batch
    model=Model(ROOT/'ai/runs/policy-iteration-trained-8840u-prepared-v2/local-package-frozen-1/policy.onnx')
    assert model.sha256=='55331f43379e8fe89025d93b1a7a48c88e0ea39b4ebd3a7ef8240d4b62753530'
    selection=read(BASE/'selection.json');out=BASE/'trained';out.mkdir(exist_ok=False)
    fixture=runtime/'ai/strong/fixtures/multiplayer-serving-v1.jsonl';assert digest(fixture)==selection['fixture_sha256']
    report={'passed':False,'checker_sha256':digest(Path(__file__)),
        'preparation_sha256':digest(BASE/'preparation.json'),'selection_sha256':digest(BASE/'selection.json'),
        'model_sha256':model.sha256,'baseline_positions':0,'baseline_decisions':0,'search_cases':0,
        'rollouts':0,'normal_caps':0,'qualification_eligible':False,'new_hf_jobs':0,
        'new_strength_games':0,'gradients':False,'reserved_final_seeds_used':False}
    policy=ResourceTurnSearch(model,runtime/'ai/strong/resource-turn-search-v1.cjs',samples=4,workers=1)
    reference=Node(str(runtime/'ai/strong/population-hybrid-policy.cjs'))
    started=time.perf_counter()
    try:
        with (out/'baselines.jsonl').open('x') as stream:
            for index,line in enumerate(fixture.open()):
                f=json.loads(line);q=f['request']
                if q['state']['phase']!='Resources':continue
                config,trace=policy.baseline(q)
                plain=reference.call({**config,'op':'prepare'})
                first=predict_batch(model,[plain['observation']])[0]
                assert first==trace[0]['index'] and plain['moves'][first]==trace[0]['move']
                prepared=policy.node.call({**config,'op':'prepare'})
                assert prepared['bundles'][prepared['baseline']]['actions']==config['baselineActions']
                stream.write(json.dumps({'fixture':index,'actions':config['baselineActions'],'decisions':trace})+'\n')
                report['baseline_positions']+=1;report['baseline_decisions']+=len(trace)
                if report['baseline_positions']%100==0:print({'baseline_positions':report['baseline_positions']},flush=True)
        assert report['baseline_positions']==755
        retained={}
        with (out/'search.jsonl').open('x') as stream:
            for label,entry in selection['selected'].items():
                q=entry['request'];before=json.dumps(q);result=policy.choose(q);assert json.dumps(q)==before
                verify(q,result);assert result['search']['truncated']==0
                retained[label]=result;stream.write(json.dumps({'label':label,'result':result},allow_nan=False)+'\n');stream.flush()
                report['search_cases']+=1;report['rollouts']+=result['search']['evaluations']
                print({'search':label,'rollouts':result['search']['evaluations'],'seconds':result['elapsedMs']/1000,
                    'baseline':result['bundles'][result['baseline']]['id'],
                    'selected':result['bundles'][result['selected']]['id']},flush=True)
        label='late-6p-recharged-sealed';q=selection['selected'][label]['request'];base=retained[label]
        for name,samples,workers,horizon in [('partition',4,4,2400),('prefix',8,1,2400),('hidden',4,1,2400),('cap',4,1,1)]:
            modified=copy.deepcopy(q)
            if name=='hidden':
                g=modified['state'];g['seed']='private-ignored';g['powerPlantsDeck']=[{'number':9999}]
                g['powerPlantDeckAfterStep3']=[{'number':9998}];g['hiddenLog']=[{'private':True}];g['currentBid']=9997
                for p in g['players']:p['bid']=9996;p['lastMove']={'name':'Bid','data':9995}
            other=ResourceTurnSearch(model,runtime/'ai/strong/resource-turn-search-v1.cjs',samples=samples,workers=workers,max_steps=horizon)
            try:result=other.choose(modified)
            finally:other.close()
            verify(modified,result)
            if name in ['partition','hidden']:assert semantic(result)==semantic(base)
            elif name=='prefix':
                assert result['search']['seed']==base['search']['seed'] and result['bundles']==base['bundles']
                for key,values in base['search']['sampleOutcomes'].items():assert values==result['search']['sampleOutcomes'][key][:4]
            else:
                assert result['search']['truncated']>0 and result['selected']==result['baseline']
            if name!='cap':assert result['search']['truncated']==0
            write(out/(name+'.json'),result);print({'control':name,'rollouts':result['search']['evaluations']},flush=True)
        report['passed']=True
    finally:
        policy.close();reference.close();report['seconds']=time.perf_counter()-started
        report['artifacts']={p.name:digest(p) for p in out.iterdir() if p.is_file()}
        report['scope']='Existing engineering fixtures only. Full plans must be committed, not replanned at each purchase. Population weights are uncalibrated; no playing-strength, target-latency or production claim.'
        write(out/'assessment.json',report)
    print(json.dumps(report),flush=True)


if __name__=='__main__':main()
