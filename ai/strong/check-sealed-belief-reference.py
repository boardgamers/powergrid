"""Independent archived-trace and initial-belief checks for the full-game preflight."""
import gzip,json
from sealed_belief_pilot import ROOT,PROTOCOL,read,write,reference_rows,Node,REVISION

p=read(PROTOCOL);pin=read(ROOT/'ai/strong/strategic-teacher-training-roots-v1.json')
with gzip.open(ROOT/pin['file'],'rt') as f:roots={r['rootId']:r for r in map(json.loads,f)}
with gzip.open(ROOT/'ai/runs/sealed-belief-preflight-v1/controls.jsonl.gz','rt') as f:cases=list(map(json.loads,f))
node=Node('strong/sealed-belief-continuations.cjs');checked=0
try:
    for mode in p['modes']:
        subset=[c for c in cases if c['old']['mode']==mode]
        refs=reference_rows([roots[c['root']] for c in subset],mode,p)
        for case in subset:
            root=roots[case['root']];control=case['control'];old=refs[root['rootId'],'a']
            lookup={(r['sample'],r['actionIndex']):r for r in old['rollouts']}
            for row in control['rollouts']:
                actual={k:v for k,v in row.items() if k not in ['env','initialBelief']}
                expected={k:v for k,v in lookup[row['sample'],row['actionIndex']].items() if k!='env'}
                assert actual==expected,'Preflight differs from immutable original teacher trace'
                checked+=1
            for name in ['control','policy']:
                row=case[name]
                traces=node.call({'op':'belief-traces',**root['request'],'samples':2,'seed':row['seed'],
                    'mode':mode,'belief':row['belief'],'neuralBeliefs':row['neural_beliefs']})['traces']
                assert all(r['initialBelief']=={'kind':row['belief'],'committed':traces[r['sample']]} for r in row['rollouts'])
finally:node.close()
assert checked==64
report={'passed':True,'old_teacher_terminal_rollouts_reproduced':checked,'belief_trace_rollouts_checked':checked*2,'qualification_eligible':False}
write(ROOT/'ai/runs/sealed-belief-preflight-v1/reference-check.json',report);print(report)
