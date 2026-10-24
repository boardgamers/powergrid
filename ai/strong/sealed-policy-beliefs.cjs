// Research belief model. Historical engine and teacher stay unchanged.
const assert = require('node:assert/strict');
const c = require('../core.cjs');
const encoders = require('./encoders.cjs');
const eco = require('./economics.cjs');
const REVISION = '4.2-discard-correction';
const clone = x => structuredClone(x);
function publicState(state, seat) {
    const g = clone(c.E.stripSecret(state, seat));
    g.seed = 'secret'; g.powerPlantsDeck = []; g.hiddenLog = [];
    delete g.powerPlantDeckAfterStep3; delete g.automation;
    if (g.options.fastBid) g.currentBid = 0;
    g.players.forEach(p => { p.lastMove = null; if (g.options.fastBid) p.bid = 0; });
    return g;
}
function prompts(state, seat) {
    const g = publicState(state, seat);
    if (!g.options.fastBid || g.phase !== c.E.Phase.Auction || !g.chosenPowerPlant) return [];
    assert(g.options.showMoney, 'Belief model requires permitted public balances');
    assert.equal(g.currentPlayers[0], seat, 'Teacher uses the canonical simulator actor order');
    const eligible = g.playerOrder.filter(i => !g.players[i].skipAuction && !g.players[i].isDropped);
    const at = eligible.indexOf(seat); assert(at >= 0);
    assert.deepEqual(g.currentPlayers, eligible.slice(at), 'Cannot infer a prior submission order');
    return eligible.slice(0, at).map((actor, index) => {
        const earlier = clone(g);
        earlier.currentPlayers = eligible.slice(index);
        earlier.players.forEach(p => {
            p.availableMoves = earlier.currentPlayers.includes(p.id) ? c.E.availableMoves(earlier, p) : null;
        });
        const encoded = encoders.forRevision(REVISION).encode(earlier, actor);
        assert(encoded.moves.length && encoded.moves.every(m => ['Bid', 'Pass'].includes(m.name)));
        return { actor, state: earlier, encoded };
    });
}
function applyPolicyBids(scenario, earlier, mode, neuralBeliefs, seed) {
    assert(['neural', 'neural_economic'].includes(mode));
    const expectedKeys = mode === 'neural' ? earlier.map(p => String(p.actor)).sort() : [];
    assert.deepEqual(Object.keys(neuralBeliefs).sort(), expectedKeys, 'Wrong neural belief actors');
    return earlier.map(p => {
        const role = mode === 'neural' ? 'neural' : 'economic';
        const action = role === 'neural' ? neuralBeliefs[p.actor] :
            eco.choose(p.state, p.actor, c.seedrandom(seed + ':committed-bid:' + p.actor)).action;
        assert(p.encoded.moves.some(m => JSON.stringify(m) === JSON.stringify(action)), 'Illegal inferred bid');
        assert(['Bid', 'Pass'].includes(action.name));
        scenario.players[p.actor].bid = action.name === 'Pass' ? 0 : action.data;
        return { actor: p.actor, role, action: clone(action) };
    });
}
module.exports = { REVISION, publicState, prompts, applyPolicyBids };
