// Explicit research ablation: identical encoder work/shapes, without the new inputs.
const full = require('./features-v4_1.cjs');
const FEATURE_REVISION = '4.1-five-plants-zero-inputs';
function observe(g, seat, geometry) {
    const row = full.observe(g, seat, geometry);
    row.state.fill(0, 1149);
    return row;
}
function encode(g, seat) {
    const row = full.encode(g, seat);
    row.state.fill(0, 1149);
    row.actions.forEach(action => action.fill(0, 98));
    row.featureRevision = FEATURE_REVISION;
    return row;
}
module.exports = {...full, FEATURE_REVISION, observe, encode};
