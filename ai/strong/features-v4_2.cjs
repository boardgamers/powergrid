// Append a public, stateless eligibility bit; never change the parent prefix/menu.
const base = require('./features-v4_1.cjs');
const FEATURE_REVISION = '4.2-discard-correction', STATE_DIM = 1216, ACTION_DIM = 100;
function eligible(g, moves) {
    return moves.length > 1 && moves.every(a => a.name === 'DiscardPowerPlant') &&
        Math.max(...g.players.map(p => p.cities.length)) >= g.citiesToEndGame - 3;
}
function encode(g, seat) {
    const row = base.encode(g, seat);
    return {...row, featureRevision: FEATURE_REVISION, state: [...row.state, +eligible(g, row.moves)]};
}
module.exports = {SCHEMA: 4, FEATURE_REVISION, STATE_DIM, ACTION_DIM, MAX_PLAYERS: 6, encode, eligible};
