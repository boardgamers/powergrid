// Hash the inputs actually seen by the frozen parent, without scoring actions.
const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const readline = require('node:readline');
const path = require('node:path');
const encoders = require(path.join(process.argv[2], 'ai/strong/encoders.cjs'));
const encoder = encoders.forRevision('4.2-discard-correction');
function floats(values) {
    const b = Buffer.alloc(values.length * 4);
    values.forEach((v, i) => { const x = Math.fround(v); assert(Number.isFinite(x)); b.writeFloatLE(x === 0 ? 0 : x, i * 4); });
    return b;
}
function inputHash(state, actions) {
    assert.equal(state.length, 1216);
    assert(actions.length > 1 && actions.every(a => a.length === 100));
    const h = crypto.createHash('sha256');
    h.update(JSON.stringify([state.length, actions.length, 100]));
    h.update(floats(state));
    // Ignore menu ordering but retain multiplicities: equivalent inputs should
    // not cross the split merely because a legal-menu order changed.
    actions.map(floats).sort(Buffer.compare).forEach(a => h.update(a));
    return h.digest('hex');
}
if (require.main === module) {
    readline.createInterface({input: process.stdin}).on('line', line => {
        try {
            const rows = JSON.parse(line);
            const result = rows.map(r => {
                const x = encoder.encode(r.request.state, r.request.player);
                assert.deepEqual(x.moves, r.legal);
                return {rootId: r.rootId, policy_input_sha256: inputHash(x.state, x.actions)};
            });
            process.stdout.write(JSON.stringify(result) + '\n');
        } catch (e) { process.stderr.write(String(e.stack) + '\n'); process.exit(1); }
    });
}
module.exports = {inputHash};
