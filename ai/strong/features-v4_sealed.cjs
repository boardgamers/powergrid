// Versioned action-menu experiment. Same schema4 features and frozen weights;
// preserve original actor menus unless this exact revision is requested.
const c = require('../core.cjs'), base = require('./features-v4.cjs');
const FEATURE_REVISION = '4.0-sealed-all-bids';
function candidates(g, seat) {
    return g.options.fastBid ? c.allLegal(g, seat) : c.candidates(g, seat);
}
function encode(g, seat) {
    return {...base.encode(g, seat, candidates(g, seat)), featureRevision: FEATURE_REVISION};
}
module.exports = {SCHEMA: 4, FEATURE_REVISION, MAX_PLAYERS: 6,
    observe: base.observe, candidates, encode};
