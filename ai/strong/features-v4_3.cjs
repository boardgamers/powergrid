// Public shortlist membership; preserve every parent feature and legal action.
const base = require('./features-v4_2.cjs');
const search = require('./search.cjs');
const FEATURE_REVISION = '4.3-strategic-correction', STATE_DIM = 1217, ACTION_DIM = 101;
function encode(g, seat) {
    const row = base.encode(g, seat);
    const eligible = row.moves.length > 1 && row.moves.some(m => ['ChoosePowerPlant', 'Bid', 'Build'].includes(m.name));
    const options = new Set(eligible ? search.shortlist(g, seat, 6, true) : []);
    return {...row, featureRevision: FEATURE_REVISION,
        state: [...row.state, +eligible],
        actions: row.actions.map((a, i) => [...a, +options.has(i)])};
}
module.exports = {SCHEMA: 4, FEATURE_REVISION, STATE_DIM, ACTION_DIM, MAX_PLAYERS: 6, encode};
