const assert = require('node:assert/strict'),fs = require('node:fs'),path = require('node:path');
const crypto = require('node:crypto'),readline = require('node:readline');
const runtime = path.resolve(process.argv[2]),output = path.resolve(process.argv[3]);
const c = require(path.join(runtime,'ai/core.cjs'));
const encoders = require(path.join(runtime,'ai/strong/encoders.cjs'));
const resource = require(path.join(runtime,'ai/strong/resource-turn-search-v1.cjs'));
const proposals = require(path.join(runtime,'ai/strong/resource-turn-plans-v1.cjs'));
const {PolicyContinuations} = require(path.join(runtime,'ai/strong/population-hybrid-policy.cjs'));
const {rolesFor} = require(path.join(runtime,'ai/strong/population-hybrid-continuations.cjs'));
const {createAnalysisScenario} = require(path.join(runtime,'engine/dist/src/analysis.js'));
const clone = x=>structuredClone(x),rev = '4.3-strategic-correction',encoder = encoders.forRevision(rev);
const hash = b=>crypto.createHash('sha256').update(b).digest('hex');
fs.mkdirSync(output,{recursive:false});
const write = (name,value)=>fs.writeFileSync(path.join(output,name),JSON.stringify(value,null,2)+'\n',{flag:'wx'});
const report = {positions:0,baseline_steps:0,hidden_controls:0,appended_baselines:0,
    cells:{},macro_controls:0,continuation_controls:0,rejected:0,passed:false,
    checker_sha256:hash(fs.readFileSync(__filename)),qualification_eligible:false};
function hidden(q) {
    const x = clone(q);x.state.seed='secret-poison';x.state.powerPlantsDeck=[{number:9999}];
    x.state.powerPlantDeckAfterStep3=[{number:9998}];x.state.hiddenLog=[{private:true}];
    x.state.players.forEach(p=>{p.lastMove={name:'Bid',data:9997};if(x.state.options.fastBid)p.bid=9996;});
    if(x.state.options.fastBid)x.state.currentBid=9995;return x;
}
function normalized(response) {
    const row=clone(response);for(const r of row.ended){delete r.resourceTurn;delete r.terminal;}return row;
}
function reference(q,root) {
    const batch = new PolicyContinuations();batch.mode='neural_population';batch.endgameFilter=true;
    batch.encoder=batch.hybridEncoder=encoder;
    batch.envs = Array.from({length:q.n},(_,index)=>{
        const sample=Math.floor(index/root.bundles.length),actionIndex=index%root.bundles.length;
        const g=createAnalysisScenario(resource.publicRoot(q),{player:q.player,seed:q.seed+'-'+sample});
        const sampledWorldSha256=resource.worldDigest(g),bundle=root.bundles[actionIndex];
        const money=g.players[q.player].money,stock=c.RES.map(r=>g.players[q.player][r+'Left']);
        for(const action of bundle.actions.slice(0,-1)) {
            assert(c.allLegal(g,q.player).some(x=>JSON.stringify(x)===JSON.stringify(action)));
            c.E.move(g,clone(action),q.player);
        }
        assert.equal(money-g.players[q.player].money,bundle.cost);
        assert.deepEqual(c.RES.map((r,i)=>g.players[q.player][r+'Left']-stock[i]),bundle.counts);
        assert(c.allLegal(g,q.player).some(x=>x.name==='Pass'&&x.data===true));
        c.E.move(g,{name:'Pass',data:true},q.player);report.macro_controls++;
        return {g,sample,actionIndex,steps:0,maxSteps:q.maxSteps,player:q.player,continuation:'neural',
            reported:false,rng:c.seedrandom(q.seed+'-rollout-'+sample),
            roles:rolesFor('neural_population',q.seed,sample,g.players.length,q.player),
            policyDecisions:{neural:0,economic:0,legacy:0,rush:0,forced:0},
            searchStats:{decisions:0,evaluations:0,truncated:0},
            initialBelief:{kind:'resource_population_v1',committed:[],sampledWorldSha256}};
    });return batch;
}
(async()=>{
    const selected=new Map();
    const fixture=path.join(runtime,'ai/strong/fixtures/multiplayer-serving-v1.jsonl');
    assert.equal(hash(fs.readFileSync(fixture)),'f1c97bf909e38e5df372a89d169d80f5a6f24c00dccefacd60b10b767f1fcfa0');
    for await(const line of readline.createInterface({input:fs.createReadStream(fixture)})) {
        const q={...JSON.parse(line).request,featureRevision:rev};if(q.state.phase!==c.E.Phase.Resources)continue;
        const before=JSON.stringify(q),turn=new resource.ModelResourceTurn(),g=resource.publicRoot(q);
        let r=turn.reset(q),actions=[];
        const poisoned=new resource.ModelResourceTurn();assert.deepEqual(poisoned.reset(hidden(q)),r);
        while(!r.done) {
            const observation=encoder.encode(g,q.player),moves=observation.moves;delete observation.moves;
            assert.deepEqual(r.observation,observation);assert.deepEqual(r.moves,moves);
            // Partial purchases deliberately exercise baselines outside the full-cycle menu.
            const buy=moves.findIndex(m=>m.name==='BuyResource');
            const at=actions.length<1+report.positions%5&&buy>=0 ? buy : moves.findIndex(m=>m.name==='Pass'&&m.data===true);
            const action=clone(moves[at]);actions.push(action);
            if(action.name==='BuyResource')c.E.move(g,action,q.player);
            r=turn.step(at);report.baseline_steps++;
        }
        assert.deepEqual(r.actions,actions);assert.throws(()=>turn.step(0));
        const config={...q,baselineActions:actions};
        const root=resource.prepareResource(config),same=resource.prepareResource(hidden(config));
        assert.deepEqual(root,same);report.hidden_controls++;
        assert.deepEqual(root.bundles[root.baseline].actions,actions);
        if(!proposals.fuelBundles(resource.publicRoot(q),q.player).bundles.some(b=>b.id===root.bundles[root.baseline].id))
            report.appended_baselines++;
        assert.equal(JSON.stringify(q),before);
        const key=[q.state.players.length,q.state.options.variant,q.state.options.fastBid].join('/');
        report.cells[key]=(report.cells[key]||0)+1;
        if(!selected.has(key))selected.set(key,config);report.positions++;
    }
    assert.equal(report.positions,755);assert.equal(selected.size,20);assert(report.appended_baselines>0);
    for(const [key,q] of selected) {
        const root=resource.prepareResource(q),config={...q,mode:'resource_population',endgameFilter:true,
            samples:4,n:4*root.bundles.length,seed:'resource-contract-'+key,maxSteps:12};
        const actual=new resource.ResourceContinuations(),control=reference(config,root);
        let a=actual.reset(config),b=control.reply();
        for(;;) {
            assert.deepEqual(normalized(a),b);report.continuation_controls++;
            if(a.observations.every(o=>!o))break;
            const moves=a.observations.map(o=>o?o.teacher:null);a=actual.step(moves);b=control.step(moves);
        }
        for(const change of [x=>{x.baselineActions=[];},x=>{x.baselineActions=[{name:'Pass',data:true},{name:'Pass',data:true}];},
            x=>{x.baselineActions=[{name:'BuyResource',data:{resource:'bogus'}},{name:'Pass',data:true}];},
            x=>{x.state.currentPlayers=[];},x=>{x.state.options.showMoney=false;}]) {
            const bad=clone(q);change(bad);assert.throws(()=>resource.prepareResource(bad));report.rejected++;
        }
    }
    report.passed=true;write('assessment.json',report);console.log(JSON.stringify(report));
})().catch(error=>{write('failure.json',{error:error.stack,report});console.error(error.stack);process.exitCode=1;});
