const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs');
const c=require('../core.cjs');
const beliefs=require('./sealed-policy-beliefs.cjs');
const {HybridContinuations}=require('./hybrid-continuations.cjs');
const {PopulationHybridContinuations,prepare,rolesFor,NEW_MODES,POPULATION,REVISIONS}=require('./population-hybrid-continuations.cjs');
const requests=[];
for(let n=2;n<=6;n++) for(const variant of ['original','recharged']) for(const fastBid of [false,true]) {
    const state=c.E.setup(n,{map:'Germany',variant,fastBid,showMoney:true},`population-contract-${n}-${variant}-${fastBid}`);
    let player=state.currentPlayers[0];
    c.E.move(state,c.candidates(state,player).find(m=>m.name==='ChoosePowerPlant'),player);
    if(fastBid) {player=state.currentPlayers[0];c.E.move(state,c.candidates(state,player).find(m=>m.name==='Bid'),player);}
    player=state.currentPlayers[0];requests.push({state:beliefs.publicState(state,player),player});
}
const fixtures=fs.readFileSync(process.env.PG_POPULATION_FIXTURES,'utf8').trim().split('\n').map(JSON.parse);
const building=new Map();
for(const f of fixtures) {
    const q=f.request,g=q.state;
    if(g.phase!=='Building'||f.legal.length<2) continue;
    const key=[g.players.length,g.options.variant,!!g.options.fastBid].join('/');
    if(!building.has(key))building.set(key,q);
}
assert.equal(building.size,20);requests.push(...building.values());assert.equal(requests.length,40);
function reset(q,mode,revision=REVISIONS[1],samples=4,maxSteps=16) {
    const p=prepare({...q,featureRevision:revision});
    const neural=['neural','neural_population'].includes(mode)?Object.fromEntries(p.prior.map(r=>
        [String(r.actor),r.encoded.moves.find(m=>m.name==='Pass')||r.encoded.moves[0]])):{};
    const options=[0,1];assert(p.moves.length>=2);
    return {...q,featureRevision:revision,mode,belief:'policy',neuralBeliefs:neural,
        seed:'population-public-contract',samples,maxSteps,n:samples*options.length,options};
}
function run(Type,q) {
    const batch=new Type();let response=batch.reset(q),ended=[];
    const transcript=[];
    for(;;) {
        transcript.push(response);ended.push(...response.ended);
        response.observations.forEach(o=>{if(o)assert.equal(o.roles[o.actor],'neural');});
        if(response.observations.every(o=>!o))break;
        response=batch.step(response.observations.map(o=>o?o.teacher:null));
    }
    assert.equal(ended.length,q.n);return {transcript,ended};
}
test('role assignments are balanced per opponent, prefix-stable and preserve the focal policy',()=>{
    for(let n=2;n<=6;n++)for(let focal=0;focal<n;focal++) {
        const rows=Array.from({length:8},(_,sample)=>rolesFor('neural_population','test',sample,n,focal));
        assert(rows.every(r=>r[focal]==='neural'));
        for(let seat=0;seat<n;seat++)if(seat!==focal) {
            assert.deepEqual(rows.slice(0,4).map(r=>r[seat]).sort(),[...POPULATION].sort());
            assert.deepEqual(rows.slice(4).map(r=>r[seat]).sort(),[...POPULATION].sort());
        }
    }
});
test('both historical modes preserve exact old responses at every count/rule/phase and revision',()=>{
    for(const q of requests)for(const mode of ['neural','neural_economic'])for(const rev of REVISIONS) {
        const config=reset(q,mode,rev,1,8);
        assert.deepEqual(run(PopulationHybridContinuations,config),run(HybridContinuations,config));
    }
});
test('new modes retain caps, neural actor routing, public input invariance and sealed-role beliefs',()=>{
    for(const q of requests)for(const mode of NEW_MODES) {
        const config=reset(q,mode,REVISIONS[1],4,8),before=JSON.stringify(q);
        const result=run(PopulationHybridContinuations,config);
        assert.equal(JSON.stringify(q),before);
        const hidden=structuredClone(config);
        hidden.state.seed='changed';hidden.state.powerPlantsDeck=[{unknown:true}];hidden.state.hiddenLog=[];
        // Bids in an open auction are public observations, not private inputs.
        if(hidden.state.options.fastBid) hidden.state.players.forEach(p=>p.bid=123);
        delete hidden.state.powerPlantDeckAfterStep3;
        assert.deepEqual(run(PopulationHybridContinuations,hidden),result);
        for(const row of result.ended) {
            assert.equal(row.truncated,row.value===null);
            assert.deepEqual(row.roles,rolesFor(mode,config.seed,row.sample,q.state.players.length,q.player));
            assert.deepEqual(row.searchStats,{decisions:0,evaluations:0,truncated:0});
            row.initialBelief.committed.forEach(b=>assert.equal(b.role,row.roles[b.actor]));
        }
    }
});
test('global world indexing is invariant to worker partition and action reordering',()=>{
    for(const q of requests.filter(r=>r.state.options.fastBid&&[2,6].includes(r.state.players.length))) {
        for(const mode of NEW_MODES) {
            const config=reset(q,mode,REVISIONS[1],4,24);
            const full=run(PopulationHybridContinuations,config).ended;
            const pieces=[...run(PopulationHybridContinuations,{...config,n:3}).ended,
                ...run(PopulationHybridContinuations,{...config,offset:3,n:5}).ended.map(r=>({...r,env:r.env+3}))];
            const sorted=rows=>rows.toSorted((a,b)=>a.env-b.env);
            assert.deepEqual(sorted(pieces),sorted(full));
            const reverse=run(PopulationHybridContinuations,{...config,options:[...config.options].reverse()}).ended;
            const canonical=rows=>rows.map(({env,...r})=>r).toSorted((a,b)=>a.sample-b.sample||a.actionIndex-b.actionIndex);
            assert.deepEqual(canonical(reverse),canonical(full));
        }
    }
});
test('endpoint continuations finish through real engine terminal outcomes',()=>{
    for(const q of [...building.values()].filter(r=>[2,6].includes(r.state.players.length)&&r.state.options.fastBid)) {
        for(const mode of NEW_MODES) {
            const result=run(PopulationHybridContinuations,reset(q,mode,REVISIONS[1],4,2400));
            assert(result.ended.every(r=>!r.truncated&&Number.isFinite(r.value)));
        }
    }
});
