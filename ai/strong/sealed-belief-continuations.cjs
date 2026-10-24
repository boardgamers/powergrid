// Versioned teacher: infer earlier sealed submissions from public opponent policies.
const assert = require('node:assert/strict');
const { StrategicContinuations } = require('./strategic-continuations.cjs');
const { createAnalysisScenario } = require('../../engine/dist/src/analysis.js');
const c = require('../core.cjs');
const encoders = require('./encoders.cjs');
const search = require('./search.cjs');
const beliefs = require('./sealed-policy-beliefs.cjs');
class SealedBeliefContinuations extends StrategicContinuations {
    reset(q) {
        assert(['policy', 'uniform_control'].includes(q.belief));
        assert(['neural', 'neural_economic'].includes(q.mode));
        assert.equal(q.featureRevision, beliefs.REVISION);
        assert(Number.isInteger(q.samples) && q.samples > 0 && Number.isInteger(q.maxSteps) && q.maxSteps > 0);
        const actions = c.candidates(q.state, q.player);
        const options = q.options || search.shortlist(q.state, q.player, 6, true);
        assert(options.length && new Set(options).size === options.length);
        assert(options.every(i => Number.isInteger(i) && i >= 0 && i < actions.length));
        const offset = q.offset || 0;
        assert(Number.isInteger(offset) && offset >= 0 && Number.isInteger(q.n) && q.n > 0);
        assert(offset + q.n <= q.samples * options.length);
        const earlier = beliefs.prompts(q.state, q.player);
        const neural = q.neuralBeliefs || {};
        if (q.belief === 'uniform_control') assert.deepEqual(neural, {});
        if (q.belief === 'policy') {
            assert.deepEqual(Object.keys(neural).sort(), q.mode === 'neural' ? earlier.map(p => String(p.actor)).sort() : []);
        }
        this.mode = q.mode; this.encoder = encoders.forRevision(q.featureRevision);
        this.envs = Array.from({length: q.n}, (_, i) => {
            const index = i + offset, sample = Math.floor(index / options.length);
            const actionIndex = options[index % options.length];
            const seed = q.seed + '-' + sample;
            const g = createAnalysisScenario(q.state, {player: q.player, seed});
            const trace = q.belief === 'policy' ? beliefs.applyPolicyBids(g, earlier, q.mode, neural, seed) :
                earlier.map(p => ({actor: p.actor, role: 'uniform', action: g.players[p.actor].bid ?
                    {name: 'Bid', data: g.players[p.actor].bid} : {name: 'Pass', data: true}}));
            c.E.move(g, structuredClone(actions[actionIndex]), q.player);
            return {g, sample, actionIndex, steps: 0, maxSteps: q.maxSteps, player: q.player,
                continuation: 'neural', reported: false, rng: c.seedrandom(q.seed + '-rollout-' + sample),
                initialBelief: {kind: q.belief, committed: trace}};
        });
        return this.reply();
    }
    reply() {
        const result = super.reply();
        for (const row of result.ended) row.initialBelief = structuredClone(this.envs[row.env].initialBelief);
        return result;
    }
}
module.exports = { SealedBeliefContinuations };
if (require.main === module) {
    const batch = new SealedBeliefContinuations();
    (async () => {
        for await (const line of require('node:readline').createInterface({input: process.stdin})) {
            try {
                const q = JSON.parse(line);
                if (q.op === 'prepare') {
                    const observation = encoders.forRevision(q.featureRevision).encode(q.state, q.player);
                    const moves = observation.moves; delete observation.moves;
                    const prior = beliefs.prompts(q.state, q.player).map(p => ({actor:p.actor, encoded:p.encoded}));
                    console.log(JSON.stringify({observation, moves, options:search.shortlist(q.state,q.player,6,true), prior}));
                } else if (q.op === 'belief-traces') {
                    assert(['policy','uniform_control'].includes(q.belief));
                    assert(Number.isInteger(q.samples) && q.samples > 0 && q.samples <= 48);
                    const prior = beliefs.prompts(q.state,q.player);
                    const traces = Array.from({length:q.samples},(_,sample)=>{
                        const seed=q.seed+'-'+sample;
                        const g=createAnalysisScenario(q.state,{player:q.player,seed});
                        return q.belief==='policy' ? beliefs.applyPolicyBids(g,prior,q.mode,q.neuralBeliefs||{},seed) :
                            prior.map(p=>({actor:p.actor,role:'uniform',action:g.players[p.actor].bid ?
                                {name:'Bid',data:g.players[p.actor].bid}:{name:'Pass',data:true}}));
                    });
                    console.log(JSON.stringify({traces}));
                } else {
                    assert(['reset','step'].includes(q.op));
                    console.log(JSON.stringify(q.op === 'reset' ? batch.reset(q) : batch.step(q.actions)));
                }
            } catch (e) {console.error(e.stack);process.exit(1);}
        }
    })();
}
