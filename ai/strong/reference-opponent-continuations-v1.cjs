// Diagnostic only: a known arena opponent is not available to a deployed policy.
// Load the verified historical runtime without editing or copying its modules.
const assert = require('node:assert/strict');
const path = require('node:path');
const crypto = require('node:crypto');
const runtime = process.env.PG_REFERENCE_RUNTIME;
assert(runtime && path.isAbsolute(runtime), 'Frozen runtime path required');
const frozen = name => require(path.join(runtime, name));
const c = frozen('ai/core.cjs');
const eco = frozen('ai/strong/economics.cjs');
const search = frozen('ai/strong/search.cjs');
const beliefs = frozen('ai/strong/sealed-policy-beliefs.cjs');
const encoders = frozen('ai/strong/encoders.cjs');
const {createAnalysisScenario} = frozen('engine/dist/src/analysis.js');
const {PolicyContinuations, preparePolicy} = frozen('ai/strong/population-hybrid-policy.cjs');
const clone = structuredClone;
const emptyStats = () => ({decisions:0, evaluations:0, truncated:0});
const addStats = (a, b) => {for (const key of Object.keys(a)) a[key] += b[key];};

function worldDigest(g) {
    const state = clone(g);
    for (const p of state.players) {delete p.clock; delete p.lastActivity;}
    return crypto.createHash('sha256').update(JSON.stringify(state)).digest('hex');
}

function referenceAction(g, seat, role, rng) {
    assert(['heuristic', 'search_geo'].includes(role));
    const stats = emptyStats();
    if (role === 'heuristic')
        return {action:c.heuristic(g, seat, rng).action, stats, decisionRole:'heuristic'};
    const legal = c.candidates(g, seat);
    if (legal.length > 1 && legal.some(a => ['ChoosePowerPlant','Bid','Build'].includes(a.name))) {
        const result = search.choose(g, seat, {samples:16, candidates:6, geography:true,
            maxSteps:2400, seed:'arena-search-'+g.round+'-'+seat+'-'+Math.floor(rng()*1e9)});
        stats.decisions = 1;
        stats.evaluations = result.evaluations || 0;
        stats.truncated = result.truncated || 0;
        return {action:result.action, stats, decisionRole:'search_geo'};
    }
    return {action:eco.choose(g, seat, rng).action, stats, decisionRole:'economic'};
}

function referenceBids(g, earlier, role, seed) {
    const stats = emptyStats();
    const committed = earlier.map(p => {
        // This is a public-policy belief, not reconstruction of the arena's private RNG history.
        const result = referenceAction(p.state, p.actor, role,
            c.seedrandom(seed+':committed-bid:'+p.actor));
        assert(['Bid','Pass'].includes(result.action.name));
        assert(c.allLegal(p.state,p.actor).some(m => JSON.stringify(m)===JSON.stringify(result.action)));
        g.players[p.actor].bid = result.action.name==='Pass' ? 0 : result.action.data;
        addStats(stats, result.stats);
        return {actor:p.actor, role, action:clone(result.action), searchStats:result.stats};
    });
    return {committed, stats};
}

class ReferenceContinuations extends PolicyContinuations {
    reset(q) {
        assert(['neural_population','reference_opponent_v1'].includes(q.mode));
        assert.equal(q.featureRevision,'4.3-strategic-correction');
        assert.equal(q.belief,'policy'); assert.equal(q.endgameFilter,true);
        assert(Number.isInteger(q.samples) && q.samples>0 && q.samples<=64);
        assert(Number.isInteger(q.maxSteps) && q.maxSteps>0 && q.maxSteps<=2400);
        assert(typeof q.seed==='string' && q.seed.length>0);
        const offset=q.offset || 0, state=beliefs.publicState(q.state,q.player);
        const prepared=preparePolicy({...q,state}), options=q.options;
        assert(Array.isArray(options) && options.length && new Set(options).size===options.length);
        assert(options.every(i=>Number.isInteger(i) && i>=0 && i<prepared.moves.length &&
            !prepared.lossFilter.forbidden.includes(i)));
        assert(Number.isInteger(offset) && offset>=0 && Number.isInteger(q.n) && q.n>0);
        assert(offset+q.n<=q.samples*options.length);
        this.initialWorlds = new Map();
        const scenarios = new Map();
        for (let i=offset; i<offset+q.n; i++) {
            const sample=Math.floor(i/options.length);
            if (scenarios.has(sample)) continue;
            const g=createAnalysisScenario(state,{player:q.player,seed:q.seed+'-'+sample});
            this.initialWorlds.set(sample,worldDigest(g));
            scenarios.set(sample,g);
        }
        if (q.mode==='neural_population') return super.reset({...q,state});
        assert(['heuristic','search_geo'].includes(q.referenceOpponent));
        assert.deepEqual(q.neuralBeliefs || {}, {});
        const earlier=beliefs.prompts(state,q.player), prior=new Map();
        for (const [sample,g] of scenarios)
            prior.set(sample,referenceBids(g,earlier,q.referenceOpponent,q.seed+'-'+sample));
        this.mode=q.mode; this.endgameFilter=true;
        this.hybridEncoder=this.encoder=encoders.forRevision(q.featureRevision);
        this.envs=Array.from({length:q.n},(_,i)=>{
            const index=i+offset, sample=Math.floor(index/options.length);
            const actionIndex=options[index%options.length], g=clone(scenarios.get(sample));
            c.E.move(g,clone(prepared.moves[actionIndex]),q.player);
            return {g,sample,actionIndex,steps:0,maxSteps:q.maxSteps,player:q.player,
                continuation:'neural',reported:false,rng:c.seedrandom(q.seed+'-rollout-'+sample),
                roles:state.players.map((_,seat)=>seat===q.player?'neural':q.referenceOpponent),
                policyDecisions:{neural:0,economic:0,heuristic:0,search_geo:0,forced:0},
                searchStats:emptyStats(), priorSearchStats:clone(prior.get(sample).stats),
                initialBelief:{kind:'reference_opponent_v1',committed:clone(prior.get(sample).committed)}};
        });
        return this.reply();
    }

    advance(e) {
        if (this.mode==='neural_population') return super.advance(e);
        while (!c.E.ended(e.g) && e.steps<e.maxSteps) {
            const actor=e.g.currentPlayers[0], role=e.roles[actor], legal=c.candidates(e.g,actor);
            if (role==='neural' && legal.length>1) return;
            let action;
            if (role==='neural') {action=legal[0]; e.policyDecisions.forced++;}
            else {
                const result=referenceAction(e.g,actor,role,e.rng);
                action=result.action; addStats(e.searchStats,result.stats);
                e.policyDecisions[result.decisionRole]++;
            }
            c.E.move(e.g,action,actor); e.steps++;
        }
    }

    reply() {
        const result=super.reply();
        for (const row of result.ended) {
            const e=this.envs[row.env];
            row.diagnostic={sampledWorldSha256:this.initialWorlds.get(e.sample),
                priorSearchStats:clone(e.priorSearchStats || emptyStats()),
                terminal:row.truncated ? null : e.g.players.map(p=>({
                    powered:p.citiesPowered,money:p.money,cities:p.cities.length}))};
        }
        return result;
    }
}

module.exports={ReferenceContinuations,referenceAction,referenceBids,worldDigest};
if (require.main===module) {
    const batch=new ReferenceContinuations();
    (async()=>{
        for await (const line of require('node:readline').createInterface({input:process.stdin})) {
            const q=JSON.parse(line); assert(['prepare','reset','step'].includes(q.op));
            console.log(JSON.stringify(q.op==='prepare'?preparePolicy(q):
                q.op==='reset'?batch.reset(q):batch.step(q.actions)));
        }
    })().catch(error=>{console.error(error.stack);process.exitCode=1;});
}
