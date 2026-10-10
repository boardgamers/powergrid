const current = require('./features.cjs');
function forRevision(revision = current.FEATURE_REVISION) {
    if (revision === current.FEATURE_REVISION) return current;
    if (revision === '4.0-multiplayer') return require('./features-v4.cjs');
    if (revision === '4.1-five-plants') return require('./features-v4_1.cjs');
    if (revision === '4.1-five-plants-zero-inputs') return require('./features-v4_1_control.cjs');
    if (revision === '3.0') return require('./features-v3_0.cjs');
    throw Error('Unsupported feature revision: ' + revision);
}
module.exports = { forRevision };
