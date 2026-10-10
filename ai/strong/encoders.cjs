const current = require('./features.cjs');
function forRevision(revision = current.FEATURE_REVISION) {
    if (revision === current.FEATURE_REVISION) return current;
    if (revision === '4.0-multiplayer') return require('./features-v4.cjs');
    if (revision === '4.0-sealed-all-bids') return require('./features-v4_sealed.cjs');
    if (revision === '4.1-five-plants') return require('./features-v4_1.cjs');
    if (revision === '4.3-strategic-correction') return require('./features-v4_3.cjs');
    if (revision === '4.2-discard-correction') return require('./features-v4_2.cjs');
    if (revision === '4.1-five-plants-zero-inputs') return require('./features-v4_1_control.cjs');
    if (revision === '3.0') return require('./features-v3_0.cjs');
    throw Error('Unsupported feature revision: ' + revision);
}
function candidatesForRevision(revision, g, seat) {
    const encoder = forRevision(revision);
    return (encoder.candidates || require('../core.cjs').candidates)(g, seat);
}
module.exports = { forRevision, candidatesForRevision };
