"""One atomic decision per public request; resource plans are recomputed, never cached."""
import argparse
import json
from pathlib import Path
import sys
import time

from hybrid_search import Model
from population_hybrid_policy import PopulationPolicy,ARMS
from resource_turn_search_v1 import ResourceTurnSearch

RESOURCE_ARMS=('resource-filter','resource-combined')


class ResourceReplanningPolicy:
    def __init__(self,model,worker,*,arm,samples=8,workers=1,max_steps=2400):
        if arm not in (*ARMS,*RESOURCE_ARMS):raise ValueError('Unknown resource-policy arm')
        self.arm=arm;self.samples=samples;self.workers=workers;self.max_steps=max_steps;self.model=model
        self.runtime=Path(worker).resolve().parent
        self.base=PopulationPolicy(model,self.runtime/'population-hybrid-policy.cjs',
            arm=arm.removeprefix('resource-'),samples=samples,workers=workers,max_steps=max_steps)
        self.resource=None

    def close(self):
        if self.resource is not None:self.resource.close();self.resource=None
        self.base.close()

    def choose(self,request):
        begin=time.perf_counter();plain=self.base.choose(request)
        if self.arm not in RESOURCE_ARMS:return plain
        result={**plain,'arm':self.arm,'resourcePlan':None,
            'executionMode':'stateless-atomic-resource-replanning-v1'}
        if request['state']['phase']!='Resources':return result
        root=self.base.node.call({'op':'prepare','state':request['state'],'player':request['player'],
            'featureRevision':self.base.revision})
        assert plain['search'] is None and not plain['filterApplied']
        if len(root['moves'])<2:return result
        if self.resource is None:
            self.resource=ResourceTurnSearch(self.model,self.runtime/'resource-turn-search-v1.cjs',
                samples=self.samples,workers=self.workers,max_steps=self.max_steps)
        plan=self.resource.choose(request)
        assert plan['baselineDecisions'][0]=={'index':plain['modelProposal'],'move':plain['move']}
        # Only this move is part of the execution contract. The remainder is a
        # simulated continuation and is not a pending plan for any later request.
        move=plan['firstMove'];index=root['moves'].index(move)
        result.update(index=index,move=move,phase='resources',search=plan['search'],resourcePlan=plan)
        result['elapsedMs']=1000*(time.perf_counter()-begin)
        return result


def main():
    parser=argparse.ArgumentParser(__doc__)
    parser.add_argument('--model',required=True,type=Path)
    parser.add_argument('--runtime',required=True,type=Path)
    parser.add_argument('--arm',choices=RESOURCE_ARMS,default='resource-filter')
    parser.add_argument('--samples',type=int,default=8)
    parser.add_argument('--workers',type=int,default=1)
    parser.add_argument('--diagnostics',action='store_true')
    args=parser.parse_args()
    policy=ResourceReplanningPolicy(Model(args.model),args.runtime/'ai/strong/population-hybrid-policy.cjs',
        arm=args.arm,samples=args.samples,workers=args.workers)
    try:
        for line in sys.stdin:
            q={}
            try:
                value=json.loads(line)
                if not isinstance(value,dict):raise ValueError('Request must be a JSON object')
                q=value;result=policy.choose(q)
                response={'requestId':q.get('requestId'),'revision':q.get('revision'),
                    'move':result['move'],'modelSha256':policy.model.sha256,
                    'executionMode':result['executionMode'],'elapsedMs':result['elapsedMs'],
                    'qualification_eligible':False}
                if args.diagnostics:response['decision']=result
            except Exception as error:
                response={'requestId':q.get('requestId'),'revision':q.get('revision'),
                    'error':type(error).__name__+': '+str(error)}
            print(json.dumps(response,allow_nan=False),flush=True)
    finally:policy.close()


if __name__=='__main__':main()
