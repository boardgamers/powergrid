// Read-only phase tag for an isolated diagnostic. No state, menu or feature changes.
const encoders = require('./encoders.cjs');
const original = encoders.forRevision;
const wrappers = new Map();
function phase(moves) {
    if (moves.length < 2) return 'other';
    if (moves.some(a => a.name === 'Build')) return 'building';
    if (moves.some(a => ['ChoosePowerPlant', 'Bid'].includes(a.name))) return 'auction';
    return 'other';
}
encoders.forRevision = function (revision) {
    if (!wrappers.has(revision)) {
        const encoder = original(revision);
        wrappers.set(revision, { ...encoder, encode(g, seat) {
            const observation = encoder.encode(g, seat);
            return { ...observation, searchPhase: phase(observation.moves) };
        } });
    }
    return wrappers.get(revision);
};
module.exports = { phase };
