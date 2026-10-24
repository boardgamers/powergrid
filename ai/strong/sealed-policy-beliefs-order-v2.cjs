// Experimental replacement in an isolated runtime; never overwrite a running evaluation.
const assert = require('node:assert/strict');
const c = require('../core.cjs');
const encoders = require('./encoders.cjs');
const eco = require('./economics.cjs');
const REVISION = '4.2-discard-correction';
const BELIEF_REVISION = 'public-submission-order-v2';
const clone = x => structuredClone(x);

function publicState(state, seat) {
    const g = clone(c.E.stripSecret(state, seat));
    g.seed = 'secret'; g.powerPlantsDeck = []; g.hiddenLog = [];
    delete g.powerPlantDeckAfterStep3; delete g.automation;
    if (g.options.fastBid) g.currentBid = 0;
    g.players.forEach(p => { p.lastMove = null; if (g.options.fastBid) p.bid = 0; });
    return g;
}

function submissionPlan(state, seat) {
    assert(state.options.showMoney, 'Belief model requires permitted public balances');
    const eligible = state.playerOrder.filter(i => !state.players[i].skipAuction && !state.players[i].isDropped);
    const pending = state.currentPlayers;
    assert(pending.includes(seat), 'Focal player must still be eligible to submit');
    assert.equal(new Set(pending).size, pending.length, 'Duplicate pending player');
    assert.deepEqual(pending, eligible.filter(i => pending.includes(i)), 'Invalid pending players/order');
    const submitted = eligible.filter(i => !pending.includes(i));
    const canonical = pending[0] === seat && pending.every((actor, index) => actor === eligible[submitted.length+index]);
    return {eligible, pending:clone(pending), submitted, canonical,
        historyAssumption: canonical ? 'canonical-public-order' : 'submitted-in-public-order-then-pending'};
}

function prompts(state, seat) {
    const g = publicState(state, seat);
    if (!g.options.fastBid || g.phase !== c.E.Phase.Auction || !g.chosenPowerPlant) return [];
    const {eligible, pending, submitted} = submissionPlan(g, seat);
    // Public state identifies who submitted, not their order. Use one explicit
    // plausible history for committed-policy prompts. This is a belief-model
    // approximation, not recovered history; canonical simulator inputs are exact.
    return submitted.map((actor, index) => {
        const earlier = clone(g);
        const remaining = new Set([...submitted.slice(index), ...pending]);
        earlier.currentPlayers = eligible.filter(i => remaining.has(i));
        earlier.players.forEach(p => {
            p.availableMoves = earlier.currentPlayers.includes(p.id) ? c.E.availableMoves(earlier, p) : null;
        });
        const encoded = encoders.forRevision(REVISION).encode(earlier, actor);
        assert(encoded.moves.length && encoded.moves.every(m => ['Bid','Pass'].includes(m.name)));
        return {actor, state:earlier, encoded};
    });
}

function applyPolicyBids(scenario, earlier, mode, neuralBeliefs, seed) {
    assert(['neural','neural_economic'].includes(mode));
    const expectedKeys = mode === 'neural' ? earlier.map(p => String(p.actor)).sort() : [];
    assert.deepEqual(Object.keys(neuralBeliefs).sort(), expectedKeys, 'Wrong neural belief actors');
    return earlier.map(p => {
        const role = mode === 'neural' ? 'neural' : 'economic';
        const action = role === 'neural' ? neuralBeliefs[p.actor] :
            eco.choose(p.state, p.actor, c.seedrandom(seed+':committed-bid:'+p.actor)).action;
        assert(p.encoded.moves.some(m => JSON.stringify(m) === JSON.stringify(action)), 'Illegal inferred bid');
        assert(['Bid','Pass'].includes(action.name));
        scenario.players[p.actor].bid = action.name === 'Pass' ? 0 : action.data;
        return {actor:p.actor, role, action:clone(action)};
    });
}

module.exports = {REVISION, BELIEF_REVISION, publicState, submissionPlan, prompts, applyPolicyBids};
