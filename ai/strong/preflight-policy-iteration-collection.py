"""Exact twin collection and reencoded model proposals across both behavior schemas."""
from policy_iteration_collection import ROOT,PROTOCOL,read,write,run,verify

p=read(PROTOCOL);out=ROOT/'ai/runs/policy-iteration-preflight-v2';out.mkdir(exist_ok=False);cases=[]
for n in [2,6]:
    for key in p['behaviors']:
        for opponent in p['opponents']:
            path=out/f'{n}p-{key}-{opponent}'
            # The parent cases additionally compare the sole bridge metadata
            # change against the original historical bridge for whole games.
            script='ai/strong/bridge.cjs' if key=='parent' else 'ai/strong/policy-iteration-bridge.cjs'
            run(n,key,opponent,path,smoke=True,plain_script=script)
            result=verify(path,n,key,opponent,smoke=True)
            cases.append({'players':n,'behavior':key,'opponent':opponent,'original_bridge_control':key=='parent',**result})
            print(cases[-1],flush=True)
report={'passed':True,'cases':cases,'games':sum(r['games'] for r in cases),'engine_game_runs':2*sum(r['games'] for r in cases),
    'roots':sum(r['roots'] for r in cases),'gradients':False,'labels_generated':False,'qualification_eligible':False}
assert report['games']==192
write(out/'preflight.json',report);print({'passed':True,'games':report['games'],'roots':report['roots']},flush=True)
