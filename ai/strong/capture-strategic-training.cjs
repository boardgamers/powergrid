// Read-only public roots; no hidden outcomes or teacher choices select positions.
const assert = require('node:assert/strict');
const encoders = require('./encoders.cjs');
const { stripSecret } = require('../../engine/dist/src/engine.js');
const original = encoders.forRevision, wrappers = new Map();
function phase(moves) {
    if (moves.length < 2) return null;
    if (moves.some(m => m.name === 'Build')) return 'building';
    if (moves.some(m => ['ChoosePowerPlant', 'Bid'].includes(m.name))) return 'auction';
    return null;
}
encoders.forRevision = function (revision) {
    if (!wrappers.has(revision)) {
        const encoder = original(revision);
        wrappers.set(revision, { ...encoder, encode(g, seat) {
            const observation = encoder.encode(g, seat), kind = phase(observation.moves);
            if (kind) {
                const before = JSON.stringify(g);
                const state = structuredClone(stripSecret(g, seat));
                delete state.powerPlantDeckAfterStep3;
                state.automation = { ...state.automation, plans: {} };
                if (state.options.fastBid) state.currentBid = 0;
                assert.deepEqual(state.powerPlantsDeck, []);
                assert.deepEqual(state.hiddenLog, []);
                assert.equal(state.seed, 'secret');
                assert(g.options.showMoney);
                assert.equal(JSON.stringify(g), before);
                observation.strategicRoot = { phase: kind, request: {state, player: seat},
                    legal: structuredClone(observation.moves) };
            }
            return observation;
        } });
    }
    return wrappers.get(revision);
};
module.exports = { phase };
