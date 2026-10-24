// Version 2: isolated known-balance sampler for nested reference search; fail closed on JSONL errors.
const test=require('node:test'), assert=require('node:assert/strict');
const fs=require('node:fs'), path=require('node:path'), vm=require('node:vm');
const {createRequire}=require('node:module');
const runtime=process.env.PG_REFERENCE_RUNTIME;
const frozen=name=>require(path.join(runtime,name));
const {ReferenceContinuations,referenceAction,worldDigest}=require('./reference-opponent-continuations-v2.cjs');
const {PolicyContinuations,preparePolicy}=frozen('ai/strong/population-hybrid-policy.cjs');
const c=frozen('ai/core.cjs'), beliefs=frozen('ai/strong/sealed-policy-beliefs.cjs');
const fixtures=fs.readFileSync(path.join(runtime,'ai/strong/fixtures/multiplayer-serving-v1.jsonl'),'utf8')
    .trim().split('\n').map(JSON.parse);
const roots=JSON.parse(fs.readFileSync(process.env.PG_REFERENCE_ROOTS,'utf8')).roots;
const revision='4.3-strategic-correction';
const cells=new Map();
for (const f of fixtures) {
    const g=f.request.state;
    if (f.legal.length<2) continue;
    const key=[g.players.length,g.options.variant,!!g.options.fastBid,g.phase].join('/');
    if (!cells.has(key)) cells.set(key,f.request);
}
assert.equal(cells.size,80);

function config(q, options, n=4) {
    const prepared=preparePolicy({...q,featureRevision:revision});
    return {...q,featureRevision:revision,mode:'neural_population',belief:'policy',endgameFilter:true,
        options,samples:4,n,seed:'reference-opponent-tests-v1',maxSteps:8,
        neuralBeliefs:Object.fromEntries(prepared.prior.map(p=>[p.actor,p.encoded.moves[0]]))};
}

test('new worker preserves all 80 rule/count/phase controls, including cap reporting',()=>{
    let caps=0;
    for (const q of cells.values()) {
        const prepared=preparePolicy({...q,featureRevision:revision});
        const options=prepared.moves.map((_,i)=>i).filter(i=>!prepared.lossFilter.forbidden.includes(i)).slice(0,2);
        const request=config(q,options);
        const a=new PolicyContinuations(),b=new ReferenceContinuations();
        let left=a.reset(request),right=b.reset(request);
        for (;;) {
            const plain=structuredClone(right);
            plain.ended.forEach(row=>{assert(row.diagnostic.sampledWorldSha256);delete row.diagnostic;});
            assert.deepEqual(plain,left);
            caps+=left.ended.filter(r=>r.truncated).length;
            if (left.observations.every(r=>!r)) break;
            const actions=left.observations.map(r=>r?r.teacher:null);
            left=a.step(actions);right=b.step(actions);
        }
    }
    assert(caps>0);
});

// Execute the frozen arena's actual applyBot function, rather than a second transcription.
const arena=path.join(runtime,'ai/strong/public-arena-bridge.cjs');
const source=fs.readFileSync(arena,'utf8').split('\n(async () => {')[0];
const sandbox={require:createRequire(arena),process:{env:{}},module:{exports:{}}};
vm.runInNewContext(source+'\nmodule.exports={applyBot};',sandbox,{filename:arena});
function arenaMove(g,actor,role,seed) {
    const e={g:structuredClone(g),roles:g.players.map(()=>role),rng:c.seedrandom(seed),searchStats:{},steps:0};
    sandbox.module.exports.applyBot(e,actor);
    const last=e.g.players[actor].lastMove;
    return {action:{name:last.name,data:structuredClone(last.data)},state:e.g,
        stats:structuredClone(e.searchStats[role] || {decisions:0,evaluations:0,truncated:0})};
}

test('reference moves and budgets exactly match the frozen arena implementation',()=>{
    const chosen=[...cells.values()].filter(q=>q.state.players.length===3);
    assert.equal(chosen.length,16);
    for (const q of chosen) for (const role of ['heuristic','search_geo']) {
        const seed='reference-route-'+role, g=structuredClone(q.state), before=worldDigest(g);
        const result=referenceAction(g,q.player,role,c.seedrandom(seed));
        assert.equal(worldDigest(g),before,'Policy mutated its input');
        const expected=arenaMove(g,q.player,role,seed);
        assert.deepEqual(result.action,expected.action);assert.deepEqual(result.stats,expected.stats);
        assert.equal(result.stats.truncated,0);
        c.E.move(g,result.action,q.player);
        assert.equal(worldDigest(g),worldDigest(expected.state));
    }
});

function snapshot(q) {
    const batch=new ReferenceContinuations();
    batch.reply=()=>batch.envs.map(e=>({sample:e.sample,actionIndex:e.actionIndex,
        world:batch.initialWorlds.get(e.sample),after:worldDigest(e.g),roles:e.roles,
        belief:e.initialBelief,prior:e.priorSearchStats}));
    return batch.reset(q);
}

test('both fixed actions share worlds; hidden fields cannot change worlds or prior bids',()=>{
    let priorCount=0;
    for (const [i,root] of roots.entries()) {
        const d=root.original_decision, q=config(root.request,[d.modelProposal,d.index],2);
        q.seed=d.search.seed;
        const control=snapshot(q);
        q.mode='reference_opponent_v1';q.referenceOpponent=i===2?'heuristic':'search_geo';q.neuralBeliefs={};
        const expected=snapshot(q), polluted=structuredClone(q);
        polluted.state.seed='should-never-influence-the-sample';
        polluted.state.powerPlantsDeck=[{number:987654}];polluted.state.powerPlantDeckAfterStep3=[456];
        polluted.state.hiddenLog=[{private:'secret'}];
        polluted.state.players.forEach(p=>{p.lastMove={name:'Bid',data:777};if(q.state.options.fastBid)p.bid=777;});
        assert.deepEqual(snapshot(polluted),expected);
        assert(expected.every((row,j)=>row.world===control[j].world));
        assert.equal(expected[0].world,expected[1].world);
        assert.deepEqual(expected[0].belief,expected[1].belief);
        const prompts=beliefs.prompts(q.state,q.player);
        for (const prior of expected[0].belief.committed) {
            const prompt=prompts.find(p=>p.actor===prior.actor);
            const actual=arenaMove(prompt.state,prior.actor,q.referenceOpponent,q.seed+'-0:committed-bid:'+prior.actor);
            assert.deepEqual(prior.action,actual.action);assert.deepEqual(prior.searchStats,actual.stats);
            priorCount++;
        }
    }
    assert(priorCount>0);
});

test('partition offsets preserve worlds, beliefs and candidate identities',()=>{
    const root=roots[6],d=root.original_decision,q=config(root.request,[d.modelProposal,d.index],4);
    q.seed=d.search.seed;q.mode='reference_opponent_v1';q.referenceOpponent='heuristic';q.neuralBeliefs={};
    const whole=snapshot(q), chunks=[...snapshot({...q,n:1}),...snapshot({...q,offset:1,n:3})];
    assert.deepEqual(whole,chunks);
    assert.throws(()=>snapshot({...q,maxSteps:0}));
    assert.throws(()=>snapshot({...q,offset:7,n:4}));
    assert.throws(()=>snapshot({...q,referenceOpponent:'unknown'}));
    assert.throws(()=>snapshot({...q,endgameFilter:false}));
});

test('nested repair handles the captured state while the historical sampler stays unchanged',()=>{
    const failure=JSON.parse(fs.readFileSync(process.env.PG_REFERENCE_FAILURE_INPUT,'utf8'));
    const g=failure.state,seat=g.currentPlayers[0];
    const options={samples:1,candidates:2,maxSteps:2400,seed:'nested-repair-isolation-v2',geography:true};
    const historical=frozen('ai/strong/search.cjs');
    assert.throws(()=>historical.choose(g,seat,options),/not allowed to run the command ChoosePowerPlant/);
    const repaired=require('./reference-search-public-balances-v1.cjs').choose(g,seat,options);
    assert.equal(repaired.truncated,0);assert(repaired.evaluations>0);
    assert(c.candidates(g,seat).some(move=>JSON.stringify(move)===JSON.stringify(repaired.action)));
    assert.throws(()=>historical.choose(g,seat,options),/not allowed to run the command ChoosePowerPlant/);
});

test('invalid JSONL request exits immediately with stdin still open',async()=>{
    const {spawn}=require('node:child_process');
    const child=spawn(process.execPath,[path.join(__dirname,'reference-opponent-continuations-v2.cjs')],
        {env:process.env,stdio:['pipe','pipe','pipe']});
    let error='',output='';child.stderr.on('data',data=>error+=data);child.stdout.on('data',data=>output+=data);
    const result=new Promise((resolve,reject)=>{
        const timer=setTimeout(()=>{child.kill();reject(Error('Worker left invalid input alive'));},5000);
        child.once('error',e=>{clearTimeout(timer);reject(e);});
        child.once('close',code=>{clearTimeout(timer);resolve(code);});
    });
    child.stdin.write(JSON.stringify({op:'invalid-operation'})+'\n');
    assert.equal(await result,1);assert(error.includes('AssertionError'));assert.equal(output,'');
});
