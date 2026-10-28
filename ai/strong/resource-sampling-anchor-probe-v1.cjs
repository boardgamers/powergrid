// Sampling-only probe over public recorded roots. No inference or continuations.
const assert = require('node:assert/strict');
const path = require('node:path');
const crypto = require('node:crypto');
const runtime = path.resolve(process.argv[2]);
const c = require(path.join(runtime,'ai/core.cjs'));
const {publicRoot,prepareResource,ModelResourceTurn} = require(path.join(runtime,'ai/strong/resource-turn-search-v1.cjs'));
const {publicState} = require(path.join(runtime,'ai/strong/sealed-policy-beliefs.cjs'));
const {rolesFor} = require(path.join(runtime,'ai/strong/population-hybrid-continuations.cjs'));
const {createAnalysisScenario} = require(path.join(runtime,'engine/dist/src/analysis.js'));
const clone = x => structuredClone(x);
const hash = x => crypto.createHash('sha256').update(JSON.stringify(x)).digest('hex');
const PASS = {name:'Pass',data:true};
let state,seat;

function prepared(q) {
    return prepareResource({state,player:seat,featureRevision:'4.3-strategic-correction',baselineActions:q.baselineActions});
}

function worlds(input,seed,samples) {
    assert(samples===8 && typeof seed==='string' && seed.startsWith('hybrid-public-v1-'));
    const g=publicRoot({state:input,player:seat,featureRevision:'4.3-strategic-correction'});
    return Array.from({length:samples},(_,sample)=>{
        const world=createAnalysisScenario(g,{player:seat,seed:seed+'-'+sample});
        const rng=c.seedrandom(seed+'-rollout-'+sample);
        return {sample,deckSha256:hash(world.powerPlantsDeck),deckNumbers:world.powerPlantsDeck.map(p=>p.number),
            roles:rolesFor('neural_population',seed,sample,g.players.length,seat),
            rolloutRngPrefix:Array.from({length:4},()=>rng()),
            publicMoney:world.players.map(p=>p.money),
            buyerStock:c.RES.map(r=>world.players[seat][r+'Left']),market:c.RES.map(r=>world[r+'Market'])};
    });
}

function inspect(q) {
    const anchored=worlds(state,q.anchorSeed,q.samples),resampled=worlds(state,q.currentSeed,q.samples);
    const polluted=clone(state);
    polluted.seed='not-the-real-game-seed';polluted.powerPlantsDeck=[{number:999}];
    polluted.powerPlantDeckAfterStep3=[{number:998}];polluted.hiddenLog=[{private:'ignored'}];
    polluted.automation={version:1,plans:{[(seat+1)%state.players.length]:{private:'ignored'}},
        increments:state.players.map(()=>1),liveUpdate:true};
    if(polluted.options.fastBid)polluted.players.forEach((p,i)=>{if(i!==seat)p.bid=100000+i;});
    assert.deepEqual(worlds(polluted,q.anchorSeed,q.samples),anchored,'Private fields affected sampled worlds');
    for(const row of anchored) {
        assert.deepEqual(row.publicMoney,state.players.map(p=>p.money));
        assert.deepEqual(row.buyerStock,c.RES.map(r=>state.players[seat][r+'Left']));
        assert.deepEqual(row.market,c.RES.map(r=>state[r+'Market']));
    }
    return {anchored,resampled,hiddenFieldControl:true,
        phase:state.phase,round:state.round,step:state.step,player:seat};
}

function handle(q) {
    if(q.op==='reset') {
        seat=q.request.player;state=publicRoot({...q.request,featureRevision:'4.3-strategic-correction'});
        return {publicRequest:{...q.request,state:clone(state)}};
    }
    if(q.op==='prepare')return prepared(q);
    if(q.op==='inspect')return inspect(q);
    if(q.op==='move') {
        assert(c.allLegal(state,seat).some(m=>JSON.stringify(m)===JSON.stringify(q.move)),'Recorded move not legal');
        assert(q.move.name==='BuyResource'||JSON.stringify(q.move)===JSON.stringify(PASS));
        const metadata={cardsLeft:state.cardsLeft,nextCardWeak:state.nextCardWeak};
        const before=clone(state);
        c.E.move(state,clone(q.move),seat);
        const rawMetadata={cardsLeft:state.cardsLeft,nextCardWeak:state.nextCardWeak};
        let baselineMetadata=null;
        if(q.move.name==='BuyResource') {
            assert.equal(state.phase,c.E.Phase.Resources);assert.deepEqual(state.currentPlayers,[seat]);
            // E.move recomputes these from the secret deck, which a public root
            // deliberately omits. A Resources purchase cannot alter either fact.
            Object.assign(state,metadata);
            for(let sample=0;sample<8;sample++) {
                const possible=createAnalysisScenario(before,{player:seat,seed:q.anchorSeed+'-'+sample});
                c.E.move(possible,clone(q.move),seat);
                assert.deepEqual({cardsLeft:possible.cardsLeft,nextCardWeak:possible.nextCardWeak},metadata);
                assert.deepEqual(c.allLegal(possible,seat),c.allLegal(state,seat));
                for(const r of c.RES) {
                    assert.equal(possible[r+'Market'],state[r+'Market']);
                    assert.equal(possible.players[seat][r+'Left'],state.players[seat][r+'Left']);
                }
                assert.equal(possible.players[seat].money,state.players[seat].money);
            }
            // Directly inspect the unchanged historical model-turn primitive;
            // no model inference is needed to expose its post-purchase inputs.
            const baseline=new ModelResourceTurn();baseline.reset({state:before,player:seat,featureRevision:'4.3-strategic-correction'});
            baseline.step(baseline.moves.findIndex(m=>JSON.stringify(m)===JSON.stringify(q.move)));
            baselineMetadata={cardsLeft:baseline.g.cardsLeft,nextCardWeak:baseline.g.nextCardWeak};
            state=publicState(state,seat);
        }
        return {phase:state.phase,round:state.round,currentPlayers:state.currentPlayers,
            publicMetadata:metadata,rawMetadata,historicalBaselineMetadata:baselineMetadata,
            privateWorldTransitionControls:q.move.name==='BuyResource'?8:0};
    }
    throw new Error('Unsupported probe operation');
}

(async()=>{
    for await(const line of require('node:readline').createInterface({input:process.stdin})) {
        const q=JSON.parse(line);console.log(JSON.stringify(handle(q)));
    }
})().catch(error=>{console.error(error.stack);process.exit(1);});
