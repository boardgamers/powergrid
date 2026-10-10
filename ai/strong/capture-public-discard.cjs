// Read-only observation extension for a separate, frozen diagnostic collection.
const assert = require('node:assert/strict');
const encoders = require('./encoders.cjs');
const { stripSecret } = require('../../engine/dist/src/engine.js');
const original = encoders.forRevision, wrappers = new Map(), seen = new WeakMap();

encoders.forRevision = function (revision) {
    if (!wrappers.has(revision)) {
        const encoder = original(revision);
        wrappers.set(revision, { ...encoder, encode(g, seat) {
            const observation = encoder.encode(g, seat);
            const moves = observation.moves;
            if (moves.length > 1 && moves.every(a => a.name === 'DiscardPowerPlant') &&
                Math.max(...g.players.map(p => p.cities.length)) >= g.citiesToEndGame - 3 &&
                !seen.get(g)?.has(seat)) {
                const before = JSON.stringify(g);
                const state = structuredClone(stripSecret(g, seat));
                delete state.powerPlantDeckAfterStep3;
                // No queued plans or hidden bids are needed for this diagnosis.
                state.automation = { ...state.automation, plans: {} };
                if (state.options.fastBid) state.currentBid = 0;
                assert.deepEqual(state.powerPlantsDeck, []);
                assert.deepEqual(state.hiddenLog, []);
                assert.equal(state.seed, 'secret');
                assert(g.options.showMoney, 'This experiment explicitly exposes opponents money');
                assert.equal(JSON.stringify(g), before, 'Observation capture mutated the game');
                observation.discardRoot = { request: { state, player: seat }, legal: structuredClone(moves),
                    eligibility: 'First observed multi-choice discard per actor/game with max public cities >= end threshold minus3; no outcome or terminal-round filter.' };
                if (!seen.has(g)) seen.set(g, new Set());
                seen.get(g).add(seat);
            }
            return observation;
        } });
    }
    return wrappers.get(revision);
};
