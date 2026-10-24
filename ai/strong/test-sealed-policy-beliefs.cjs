const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const zlib = require('node:zlib');
const {prompts, applyPolicyBids, REVISION} = require('./sealed-policy-beliefs.cjs');
const {StrategicContinuations} = require('./strategic-continuations.cjs');
const {SealedBeliefContinuations} = require('./sealed-belief-continuations.cjs');
const roots = zlib.gunzipSync(fs.readFileSync(__dirname+'/fixtures/strategic-teacher-training-roots-v1.jsonl.gz'))
    .toString().trim().split('\n').map(JSON.parse);
const bids = roots.filter(r => r.sealed && r.decision === 'bid');
const clean = r => ({observations:r.observations,ended:r.ended.map(({initialBelief,...old})=>old)});
function inferred(r, mode) {
    return mode === 'neural' ? Object.fromEntries(prompts(r.request.state,r.request.player)
        .map(p=>[String(p.actor),p.encoded.moves.find(m=>m.name==='Pass')||p.encoded.moves[0]])) : {};
}
function reset(r, mode, belief='policy') {
    return {...r.request,mode,belief,neuralBeliefs:belief==='policy'?inferred(r,mode):{},
        op:'reset',featureRevision:REVISION,samples:2,n:4,options:[0,1],maxSteps:16,seed:'sealed-belief-contract-v1'};
}
test('all320 public prompts ignore forbidden fields and preserve the input',()=>{
    assert.equal(bids.length,320);let count=0;
    for(const r of bids) {
        const q=r.request,before=JSON.stringify(q),a=prompts(q.state,q.player),g=structuredClone(q.state);
        g.seed='forbidden';g.powerPlantsDeck.reverse();g.hiddenLog=[{secret:true}];g.currentBid=999;
        g.powerPlantDeckAfterStep3=[{number:999}];g.automation={plans:{0:{secret:true}}};
        g.players.forEach((p,i)=>{p.bid=500+i;p.lastMove={name:'Bid',data:500+i};});
        assert.deepEqual(prompts(g,q.player),a);assert.equal(JSON.stringify(q),before);count+=a.length;
    }
    assert.equal(count,317);
});
test('uniform control matches every old-worker transition and terminal record',()=>{
    for(const n of [2,6])for(const mode of ['neural','neural_economic']) {
        const r=bids.find(r=>r.players===n&&prompts(r.request.state,r.request.player).length);
        const q=reset(r,mode,'uniform_control');const old=new StrategicContinuations(),next=new SealedBeliefContinuations();
        let a=old.reset(q),b=next.reset(q);
        for(;;){assert.deepEqual(clean(b),a);if(a.observations.every(x=>!x))break;
            const actions=a.observations.map(x=>x?0:null);a=old.step(actions);b=next.step(actions);}
    }
});
test('sampling ignores the candidate and worker split',()=>{
    const r=bids.find(r=>r.players===6&&prompts(r.request.state,r.request.player).length>=2);
    for(const mode of ['neural','neural_economic']) {
        const q=reset(r,mode),full=new SealedBeliefContinuations(),left=new SealedBeliefContinuations(),right=new SealedBeliefContinuations();
        let a=full.reset(q),b=left.reset({...q,n:2}),d=right.reset({...q,n:2,offset:2});
        assert.deepEqual(full.envs[0].initialBelief,full.envs[1].initialBelief);
        assert.deepEqual(full.envs[2].initialBelief,full.envs[3].initialBelief);
        for(;;){assert.deepEqual(a.observations,[...b.observations,...d.observations]);
            assert.deepEqual(a.ended,[...b.ended,...d.ended.map(x=>({...x,env:x.env+2}))]);
            if(a.observations.every(x=>!x))break;
            const actions=a.observations.map(x=>x?0:null);a=full.step(actions);b=left.step(actions.slice(0,2));d=right.step(actions.slice(2));}
    }
});
test('legal passes are possible and invalid injected neural beliefs are rejected',()=>{
    const r=bids.find(r=>prompts(r.request.state,r.request.player).some(p=>p.encoded.moves.some(m=>m.name==='Pass')));
    const prior=prompts(r.request.state,r.request.player),q=reset(r,'neural');
    const g=structuredClone(r.request.state);const trace=applyPolicyBids(g,prior,q.mode,q.neuralBeliefs,q.seed);
    assert(trace.some(p=>p.action.name==='Pass'));assert(trace.every(p=>g.players[p.actor].bid===(p.action.name==='Pass'?0:p.action.data)));
    assert.throws(()=>new SealedBeliefContinuations().reset({...q,neuralBeliefs:{}}));
    const bad=structuredClone(q);bad.neuralBeliefs[prior[0].actor]={name:'Bid',data:999999};
    assert.throws(()=>new SealedBeliefContinuations().reset(bad));
    assert.throws(()=>new SealedBeliefContinuations().reset({...q,belief:'uniform_control'}));
});
test('private-field mutation leaves all policy rollout transitions unchanged',()=>{
    const r=bids.find(r=>r.players===6&&prompts(r.request.state,r.request.player).length>=2);
    for(const mode of ['neural','neural_economic']) {
        const q=reset(r,mode),other=structuredClone(q);
        other.state.powerPlantsDeck=[{number:999}];other.state.seed='secret elsewhere';other.state.hiddenLog=[{secret:true}];
        other.state.currentBid=888;other.state.players.forEach(p=>{p.bid=777;p.lastMove={name:'Bid',data:777};});
        const a=new SealedBeliefContinuations(),b=new SealedBeliefContinuations();let x=a.reset(q),y=b.reset(other);
        for(;;){assert.deepEqual(x,y);if(x.observations.every(x=>!x))break;
            const choices=x.observations.map(x=>x?0:null);x=a.step(choices);y=b.step(choices);}
    }
});
