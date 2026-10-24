"""Actual trained policy integration on existing fixtures; no fresh strength games."""
import argparse
import json
from pathlib import Path
import time

from strategic_collection import ROOT, read, write, digest
from population_hybrid_policy import PopulationPolicy
from hybrid_search import Model, model_revision


def main(output):
    preflight=ROOT/'ai/runs/population-policy-preflight-v1'
    a=read(preflight/'admission.json');runtime=preflight/'runtime'
    assert 'pass 4' in (preflight/'tests.log').read_text() and 'fail 0' in (preflight/'tests.log').read_text()
    for name,sha in a['base_runtime_hashes'].items(): assert digest(runtime/name)==sha
    for name,sha in a['new_code_hashes'].items(): assert digest(runtime/'ai/strong'/name)==sha
    for name,sha in a['population_worker_hashes'].items(): assert digest(runtime/'ai/strong'/name)==sha
    prepared=ROOT/'ai/runs/policy-iteration-trained-8840u-prepared-v2'
    protocol=read(ROOT/'ai/strong/population-hybrid-development-protocol-v1.json')
    model=Model(prepared/'local-package-frozen-1/policy.onnx')
    assert model.sha256==protocol['model_pin']['files']['inference64.onnx']
    fixtures=[json.loads(line) for line in (prepared/'fixtures.jsonl').open()]
    selected=read(ROOT/'ai/runs/trained-hybrid-probe-v2/selected-fixtures.json')
    output.mkdir(parents=True,exist_ok=False)
    report={'model_sha256':model.sha256,'fixture_sha256':digest(prepared/'fixtures.jsonl'),
        'preflight_admission_sha256':digest(preflight/'admission.json'),'protocol_sha256':digest(ROOT/'ai/strong/population-hybrid-development-protocol-v1.json'),
        'code_hashes':{str(p.relative_to(ROOT)):digest(p) for p in [Path(__file__),ROOT/'ai/strong/population_hybrid_policy.py']},
        'positions':0,'filtered_proposals':0,'search_cases':0,'rollouts':0,'caps':0,'checks_complete':False,
        'qualification_eligible':False,'reserved_final_seeds_used':False,'new_strength_games':0,'new_hf_jobs':0}
    policies={arm:PopulationPolicy(model,runtime/'ai/strong/population-hybrid-policy.cjs',arm=arm,samples=8,workers=1)
              for arm in ['model','filter','auction','building','combined']}
    start=time.perf_counter()
    try:
        for fixture in fixtures:
            q=fixture['request'];plain=policies['model'].choose(q);filtered=policies['filter'].choose(q)
            assert plain['search'] is None and filtered['search'] is None
            assert plain['index']==plain['modelProposal']==filtered['modelProposal']
            assert fixture['legal'][plain['index']]==plain['move']
            assert fixture['legal'][filtered['index']]==filtered['move']
            assert (plain['index']!=filtered['index'])==filtered['filterApplied']
            if filtered['filterApplied']:
                assert plain['move']['name']=='Build' and filtered['move']=={'name':'Pass','data':True}
                report['filtered_proposals']+=1
            report['positions']+=1
        print({'positions':report['positions'],'filtered_proposals':report['filtered_proposals']},flush=True)
        for name,fixture in selected.items():
            q=fixture['fixture']['request'];before=json.dumps(q)
            results={arm:policy.choose(q) for arm,policy in policies.items()}
            assert json.dumps(q)==before
            expected='auction' if name.endswith('bid') else 'building'
            for arm,result in results.items():
                assert result['phase']==expected
                assert result['move']==fixture['fixture']['legal'][result['index']]
                active=arm in (expected,'combined')
                assert bool(result['search'])==active
                if active:
                    detail=result['search'];assert detail['usable'] and detail['truncated']==0
                    report['search_cases']+=1;report['rollouts']+=detail['evaluations']
            without_time=lambda result:{k:v for k,v in result.items() if k not in ['elapsedMs','arm']}
            assert without_time(results['combined'])==without_time(results[expected])
            opposite='building' if expected=='auction' else 'auction'
            assert without_time(results[opposite])==without_time(results['filter'])
            with (output/'results.jsonl').open('a') as stream:
                stream.write(json.dumps({'fixture':name,'results':results},allow_nan=False)+'\n')
            print({'fixture':name,'search_cases':report['search_cases'],'rollouts':report['rollouts']},flush=True)
        q=selected['6p-building']['fixture']['request']
        alternatives=[('partition',8,4,2400),('prefix',4,1,2400),('cap',4,1,1)]
        baseline=results['combined'] if name=='6p-building' else policies['combined'].choose(q)
        for label,samples,workers,horizon in alternatives:
            policy=PopulationPolicy(model,runtime/'ai/strong/population-hybrid-policy.cjs',arm='combined',
                samples=samples,workers=workers,max_steps=horizon)
            try:result=policy.choose(q)
            finally:policy.close()
            detail=result['search'];assert detail is not None
            if label=='partition':
                assert without_time(result)==without_time(baseline)
            elif label=='prefix':
                assert detail['seed']==baseline['search']['seed'] and detail['options']==baseline['search']['options']
                for index,values in detail['sampleOutcomes'].items():
                    assert values==baseline['search']['sampleOutcomes'][index][:4]
            else:
                assert detail['truncated']>0 and not detail['usable'] and detail['fallbackReason']=='incomplete-rollouts'
                assert result['index']==policies['filter'].choose(q)['index'] and 'meanCredits' not in detail
            write(output/(label+'.json'),result)
        assert report['positions']==2553 and report['search_cases']==8
        report['checks_complete']=True
    finally:
        for policy in policies.values():policy.close()
        report['seconds']=time.perf_counter()-start
        report['artifacts']={p.name:digest(p) for p in output.iterdir() if p.is_file()}
        report['scope']='Existing-fixture integration only. The deliberate one-step cap test is retained separately; zero normal-budget caps required. No fresh strength or target-CPU timing claim.'
        write(output/'assessment.json',report)


if __name__=='__main__':
    parser=argparse.ArgumentParser(__doc__);parser.add_argument('--output',required=True,type=Path)
    main(parser.parse_args().output.resolve())
