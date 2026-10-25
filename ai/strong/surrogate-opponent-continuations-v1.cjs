// Isolated diagnostic adapter: replace reference strategic choices with public-model queries.
const assert = require('node:assert/strict');
const path = require('node:path');
const {isDeepStrictEqual} = require('node:util');
const runtime = process.env.PG_REFERENCE_RUNTIME;
assert(runtime && path.isAbsolute(runtime), 'Frozen runtime path required');
const frozen = name => require(path.join(runtime, name));
const {ReferenceContinuations, worldDigest} = require('./reference-opponent-continuations-v2.cjs');
const {preparePolicy} = frozen('ai/strong/population-hybrid-policy.cjs');
const {ContinuationBatch} = frozen('ai/strong/continuation-rollouts.cjs');
const c = frozen('ai/core.cjs'), eco = frozen('ai/strong/economics.cjs');
const beliefs = frozen('ai/strong/sealed-policy-beliefs.cjs');
const encoder = frozen('ai/strong/encoders.cjs').forRevision('4.3-strategic-correction');
const {createAnalysisScenario} = frozen('engine/dist/src/analysis.js');
const {calculateMaxCitiesPowered} = frozen('engine/dist/src/engine.js');
const certificate = frozen('ai/strong/endgame-loss-filter.cjs').createFilter(c, calculateMaxCitiesPowered);
const strategic = legal => legal.some(m => ['ChoosePowerPlant', 'Bid', 'Build'].includes(m.name));
const emptyStats = () => ({decisions: 0, evaluations: 0, truncated: 0});

class SurrogateContinuations extends ReferenceContinuations {
    reset(q) {
        if (q.mode !== 'surrogate_opponent_v1') {
            assert.equal(q.surrogateBeliefs, undefined);
            return super.reset(q);
        }
        assert.equal(q.featureRevision, '4.3-strategic-correction');
        assert.equal(q.belief, 'policy'); assert.equal(q.endgameFilter, true);
        assert.deepEqual(q.neuralBeliefs || {}, {});
        assert.equal(q.referenceOpponent, undefined, 'Surrogate inputs do not include arena opponent identity');
        assert(Number.isInteger(q.samples) && q.samples > 0 && q.samples <= 64);
        assert(Number.isInteger(q.maxSteps) && q.maxSteps > 0 && q.maxSteps <= 2400);
        assert(typeof q.seed === 'string' && q.seed.length > 0);
        const state = beliefs.publicState(q.state, q.player);
        assert.equal(state.options.showMoney, true);
        const prepared = preparePolicy({...q, state}), options = q.options, offset = q.offset || 0;
        assert(Array.isArray(options) && options.length && new Set(options).size === options.length);
        assert(options.every(i => Number.isInteger(i) && i >= 0 && i < prepared.moves.length && !prepared.lossFilter.forbidden.includes(i)));
        assert(Number.isInteger(offset) && offset >= 0 && Number.isInteger(q.n) && q.n > 0);
        assert(offset + q.n <= q.samples * options.length);
        assert(Array.isArray(q.surrogateBeliefs) && q.surrogateBeliefs.length === q.samples);
        const actors = prepared.prior.map(p => String(p.actor)).sort();
        for (const inferred of q.surrogateBeliefs) {
            assert.deepEqual(Object.keys(inferred).sort(), actors, 'Missing or unexpected prior-bid actors');
            for (const p of prepared.prior) {
                const action = inferred[p.actor];
                assert(action && ['Bid', 'Pass'].includes(action.name));
                const index = p.encoded.moves.findIndex(m => isDeepStrictEqual(m, action));
                assert(index >= 0 && p.encoded.actions[index][100] === 1, 'Prior bid outside public shortlist');
            }
        }
        this.mode = q.mode; this.endgameFilter = true; this.hybridEncoder = this.encoder = encoder;
        this.initialWorlds = new Map();
        const worlds = new Map();
        for (let i = offset; i < offset + q.n; i++) {
            const sample = Math.floor(i / options.length);
            if (worlds.has(sample)) continue;
            const g = createAnalysisScenario(state, {player: q.player, seed: q.seed + '-' + sample});
            this.initialWorlds.set(sample, worldDigest(g));
            const committed = prepared.prior.map(p => {
                const action = structuredClone(q.surrogateBeliefs[sample][p.actor]);
                g.players[p.actor].bid = action.name === 'Pass' ? 0 : action.data;
                return {actor: p.actor, role: 'surrogate', action};
            });
            worlds.set(sample, {g, committed});
        }
        this.envs = Array.from({length: q.n}, (_, i) => {
            const index = offset + i, sample = Math.floor(index / options.length);
            const actionIndex = options[index % options.length], g = structuredClone(worlds.get(sample).g);
            c.E.move(g, structuredClone(prepared.moves[actionIndex]), q.player);
            return {g, sample, actionIndex, steps: 0, maxSteps: q.maxSteps, player: q.player,
                continuation: 'neural', reported: false, rng: c.seedrandom(q.seed + '-rollout-' + sample),
                roles: state.players.map((_, seat) => seat === q.player ? 'neural' : 'surrogate'),
                policyDecisions: {neural: 0, economic: 0, surrogate: 0, forced: 0},
                searchStats: emptyStats(), priorSearchStats: emptyStats(),
                initialBelief: {kind: 'surrogate_opponent_v1', committed: structuredClone(worlds.get(sample).committed)}};
        });
        return this.reply();
    }

    advance(e) {
        if (this.mode !== 'surrogate_opponent_v1') return super.advance(e);
        while (!c.E.ended(e.g) && e.steps < e.maxSteps) {
            const seat = e.g.currentPlayers[0], role = e.roles[seat], legal = c.candidates(e.g, seat);
            if (role === 'neural' && legal.length > 1) return;
            if (role === 'surrogate' && legal.length > 1 && strategic(legal)) {
                // Reference search consumes one outer RNG draw per strategic
                // choice. Preserve it even though deterministic inference does
                // not use the seed. It never enters an emitted observation.
                if (e.pendingTeacherSeed === undefined)
                    e.pendingTeacherSeed = 'arena-search-' + e.g.round + '-' + seat + '-' + Math.floor(e.rng() * 1e9);
                return;
            }
            assert(e.pendingTeacherSeed === undefined);
            const action = role === 'neural' ? legal[0] : eco.choose(e.g, seat, e.rng).action;
            e.policyDecisions[role === 'neural' ? 'forced' : 'economic']++;
            c.E.move(e.g, action, seat); e.steps++;
        }
    }

    step(actions) {
        if (this.mode !== 'surrogate_opponent_v1') return super.step(actions);
        assert.equal(actions.length, this.envs.length);
        const executed = actions.map((choice, i) => {
            const e = this.envs[i];
            if (e.reported) { assert.equal(choice, null); return null; }
            const seat = e.g.currentPlayers[0], legal = c.candidates(e.g, seat);
            assert(Number.isInteger(choice) && choice >= 0 && choice < legal.length);
            if (e.roles[seat] === 'surrogate') {
                assert(strategic(legal) && e.pendingTeacherSeed !== undefined);
                assert.equal(encoder.encode(e.g, seat).actions[choice][100], 1, 'Surrogate choice outside public shortlist');
                return choice;
            }
            assert.equal(seat, e.player); assert(e.pendingTeacherSeed === undefined);
            const proof = certificate(e.g, seat, legal[choice]);
            if (!proof) return choice;
            const replacement = legal.findIndex(move => isDeepStrictEqual(move, proof.replacement));
            assert(replacement >= 0); return replacement;
        });
        // Validate every environment before advancing any of them.
        this.envs.forEach((e, i) => {
            if (e.reported) return;
            const role = e.roles[e.g.currentPlayers[0]];
            e.policyDecisions[role]++;
            if (executed[i] !== actions[i]) e.filterOverrides = (e.filterOverrides || 0) + 1;
            delete e.pendingTeacherSeed;
        });
        return ContinuationBatch.prototype.step.call(this, executed);
    }
}

module.exports = {SurrogateContinuations, preparePolicy};
if (require.main === module) {
    const batch = new SurrogateContinuations();
    (async () => {
        for await (const line of require('node:readline').createInterface({input: process.stdin})) {
            const q = JSON.parse(line); assert(['prepare', 'reset', 'step'].includes(q.op));
            console.log(JSON.stringify(q.op === 'prepare' ? preparePolicy(q) : q.op === 'reset' ? batch.reset(q) : batch.step(q.actions)));
        }
    })().catch(error => { console.error(error.stack); process.exit(1); });
}
