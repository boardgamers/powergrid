// Isolated resource-turn search. No serving integration or job submission.
const assert = require('node:assert/strict');
const {isDeepStrictEqual} = require('node:util');
const crypto = require('node:crypto');
const c = require('../core.cjs');
const proposals = require('./resource-turn-plans-v1.cjs');
const encoders = require('./encoders.cjs');
const {preparePolicy,PolicyContinuations} = require('./population-hybrid-policy.cjs');
const {rolesFor} = require('./population-hybrid-continuations.cjs');
const {createAnalysisScenario} = require('../../engine/dist/src/analysis.js');
const clone = value => structuredClone(value);
const PASS = {name:'Pass',data:true};

function publicRoot(q) {
    const g = proposals.publicRoot(q);
    assert.deepEqual(g.currentPlayers,[q.player],'Resource turns must have one buyer');
    assert.equal(q.featureRevision,'4.3-strategic-correction');
    return g;
}

function legalMove(g,seat,move) {
    assert(c.allLegal(g,seat).some(m => isDeepStrictEqual(m,move)),'Illegal resource-plan move');
}

function purchases(g,seat,actions) {
    assert(Array.isArray(actions) && actions.length > 0);
    assert(isDeepStrictEqual(actions.at(-1),PASS),'A complete resource turn must end in Pass');
    const initial = g.players[seat].money, counts = [0,0,0,0];
    for (const move of actions.slice(0,-1)) {
        assert.equal(move.name,'BuyResource','Only purchases may precede the final Pass');
        const index = c.RES.indexOf(move.data.resource);assert(index >= 0);
        legalMove(g,seat,move);c.E.move(g,clone(move),seat);counts[index]++;
        assert.equal(g.phase,c.E.Phase.Resources);assert.deepEqual(g.currentPlayers,[seat]);
    }
    legalMove(g,seat,PASS);
    return {counts,cost:initial-g.players[seat].money};
}

class ModelResourceTurn {
    reset(q) {
        this.g = publicRoot(q);this.seat = q.player;this.done = false;this.actions = [];
        this.encoder = encoders.forRevision(q.featureRevision);
        this.bound = 1+c.RES.reduce((n,r) => n+this.g[r+'Market'],0);
        return this.reply();
    }
    step(index) {
        assert(!this.done);assert(Number.isInteger(index) && index >= 0 && index < this.moves.length);
        const action = clone(this.moves[index]);
        this.actions.push(action);assert(this.actions.length <= this.bound);
        if (isDeepStrictEqual(action,PASS)) this.done = true;
        else {
            assert.equal(action.name,'BuyResource');
            legalMove(this.g,this.seat,action);c.E.move(this.g,action,this.seat);
        }
        return this.reply();
    }
    reply() {
        if (this.done) return {done:true,actions:clone(this.actions)};
        const observation = this.encoder.encode(this.g,this.seat);
        this.moves = observation.moves;delete observation.moves;
        assert(this.moves.every(m => m.name==='BuyResource' || isDeepStrictEqual(m,PASS)));
        return {done:false,observation,moves:clone(this.moves)};
    }
}

function prepareResource(q) {
    const g = publicRoot(q), generated = proposals.fuelBundles(g,q.player);
    const baseline = purchases(clone(g),q.player,q.baselineActions);
    const id = baseline.counts.join(',');
    const bundles = generated.bundles.map(b => ({id:b.id,counts:b.counts,cost:b.cost,
        actions:[...b.actions,clone(PASS)],baseline:b.id===id}));
    const at = bundles.findIndex(b => b.id===id);
    // Preserve the exact model action order, including unusual partial stockpiles.
    if (at >= 0) {
        assert.equal(bundles[at].cost,baseline.cost);
        bundles[at].actions = clone(q.baselineActions);
    } else bundles.push({id,...baseline,actions:clone(q.baselineActions),baseline:true});
    assert(bundles.some(b => b.id==='0,0,0,0'));
    assert.equal(bundles.filter(b => b.baseline).length,1);
    return {...preparePolicy(q),bundles,baseline:bundles.findIndex(b=>b.baseline),
        scope:'Complete fuel bundles plus exact model turn; future building follows the continuation policy.'};
}

function worldDigest(g) {
    const value = clone(g);
    for (const p of value.players) {delete p.clock;delete p.lastActivity;}
    return crypto.createHash('sha256').update(JSON.stringify(value)).digest('hex');
}

class ResourceContinuations extends PolicyContinuations {
    reset(q) {
        const state = publicRoot(q), root = prepareResource(q), seat = q.player;
        assert.equal(q.mode,'resource_population');assert.equal(q.endgameFilter,true);
        assert(Number.isInteger(q.samples) && q.samples>=4 && q.samples<=64 && q.samples%4===0);
        assert(Number.isInteger(q.maxSteps) && q.maxSteps>0 && q.maxSteps<=2400);
        assert(typeof q.seed==='string' && q.seed.length>0);
        const offset = q.offset || 0;
        assert(Number.isInteger(offset) && offset>=0 && Number.isInteger(q.n) && q.n>0);
        assert(offset+q.n <= q.samples*root.bundles.length);
        this.mode = 'neural_population';this.endgameFilter = true;
        this.hybridEncoder = this.encoder = encoders.forRevision(q.featureRevision);
        this.envs = Array.from({length:q.n},(_,i) => {
            const index = i+offset, sample = Math.floor(index/root.bundles.length);
            const actionIndex = index%root.bundles.length, bundle = root.bundles[actionIndex];
            const g = createAnalysisScenario(state,{player:seat,seed:q.seed+'-'+sample});
            const sampledWorldSha256 = worldDigest(g);
            const applied = purchases(g,seat,bundle.actions);
            assert.deepEqual(applied,{counts:bundle.counts,cost:bundle.cost});
            const afterPurchases = {money:g.players[seat].money,
                stock:c.RES.map(r=>g.players[seat][r+'Left']),market:c.RES.map(r=>g[r+'Market'])};
            c.E.move(g,clone(PASS),seat);
            return {g,sample,actionIndex,steps:0,maxSteps:q.maxSteps,player:seat,
                continuation:'neural',reported:false,rng:c.seedrandom(q.seed+'-rollout-'+sample),
                roles:rolesFor('neural_population',q.seed,sample,state.players.length,seat),
                policyDecisions:{neural:0,economic:0,legacy:0,rush:0,forced:0},
                searchStats:{decisions:0,evaluations:0,truncated:0},
                initialBelief:{kind:'resource_population_v1',committed:[],sampledWorldSha256},
                resourceTurn:{bundleId:bundle.id,actions:clone(bundle.actions),...applied,afterPurchases}};
        });
        return this.reply();
    }
    reply() {
        const response = super.reply();
        for (const row of response.ended) {
            const e = this.envs[row.env];row.resourceTurn = clone(e.resourceTurn);
            row.terminal = row.truncated ? null : e.g.players.map(p=>({
                powered:p.citiesPowered,money:p.money,cities:p.cities.length,
                capacity:c.capacity(p)}));
        }
        return response;
    }
}

module.exports = {ModelResourceTurn,prepareResource,ResourceContinuations,publicRoot,purchases,worldDigest};
if (require.main === module) {
    const turn = new ModelResourceTurn(), batch = new ResourceContinuations();
    (async()=>{
        for await (const line of require('node:readline').createInterface({input:process.stdin})) {
            const q = JSON.parse(line);
            assert(['baseline-reset','baseline-step','prepare','reset','step'].includes(q.op));
            const result = q.op==='baseline-reset' ? turn.reset(q) :
                q.op==='baseline-step' ? turn.step(q.index) :
                q.op==='prepare' ? prepareResource(q) : q.op==='reset' ? batch.reset(q) : batch.step(q.actions);
            console.log(JSON.stringify(result));
        }
    })().catch(error=>{console.error(error.stack);process.exitCode=1;});
}
