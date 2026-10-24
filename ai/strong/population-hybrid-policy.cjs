// Isolated research policy adapter; historical workers and serving stay unchanged.
const assert = require('node:assert/strict');
const {isDeepStrictEqual} = require('node:util');
const {PopulationHybridContinuations, prepare} = require('./population-hybrid-continuations.cjs');
const beliefs = require('./sealed-policy-beliefs.cjs');
const c = require('../core.cjs');
const {calculateMaxCitiesPowered} = require('../../engine/dist/src/engine.js');
const certificate = require('./endgame-loss-filter.cjs').createFilter(c, calculateMaxCitiesPowered);

function preparePolicy(q) {
    const result = prepare(q), state = beliefs.publicState(q.state, q.player);
    const certified = result.moves.map(move => certificate(state, q.player, move));
    const forbidden = certified.flatMap((value, index) => value ? [index] : []);
    const passIndex = result.moves.findIndex(move => move.name === 'Pass' && move.data === true);
    if (forbidden.length) assert(passIndex >= 0);
    return {...result, lossFilter: {forbidden, passIndex, certificate: certified.find(Boolean) || null}};
}

class PolicyContinuations extends PopulationHybridContinuations {
    reset(q) {
        assert.equal(q.mode, 'neural_population');
        assert.equal(typeof q.endgameFilter, 'boolean');
        this.endgameFilter = q.endgameFilter;
        if (this.endgameFilter) {
            const forbidden = preparePolicy(q).lossFilter.forbidden;
            assert(q.options.every(index => !forbidden.includes(index)), 'Certified losing root action');
        }
        return super.reset(q);
    }

    step(actions) {
        assert.equal(actions.length, this.envs.length);
        const executed = actions.map((choice, index) => {
            const e = this.envs[index];
            if (!this.endgameFilter || e.reported || e.g.currentPlayers[0] !== e.player) return choice;
            const legal = c.candidates(e.g, e.player);
            assert(Number.isInteger(choice) && choice >= 0 && choice < legal.length);
            const proof = certificate(e.g, e.player, legal[choice]);
            if (!proof) return choice;
            const replacement = legal.findIndex(move => isDeepStrictEqual(move, proof.replacement));
            assert(replacement >= 0);
            e.filterOverrides = (e.filterOverrides || 0) + 1;
            return replacement;
        });
        return super.step(executed);
    }

    reply() {
        const result = super.reply();
        for (const row of result.ended) row.filterOverrides = this.envs[row.env].filterOverrides || 0;
        return result;
    }
}

module.exports = {PolicyContinuations, preparePolicy};
if (require.main === module) {
    const batch = new PolicyContinuations();
    (async () => {
        for await (const line of require('node:readline').createInterface({input:process.stdin})) {
            try {
                const q = JSON.parse(line);
                assert(['prepare','reset','step'].includes(q.op));
                console.log(JSON.stringify(q.op === 'prepare' ? preparePolicy(q) :
                    q.op === 'reset' ? batch.reset(q) : batch.step(q.actions)));
            } catch (error) { console.error(error.stack); process.exit(1); }
        }
    })();
}
