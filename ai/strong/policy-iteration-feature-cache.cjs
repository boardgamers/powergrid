// Encode through an immutable runtime; retain the original parent input hash.
const assert = require('node:assert/strict');
const path = require('node:path');
const readline = require('node:readline');
const runtime = path.resolve(process.argv[2]);
const encoders = require(path.join(runtime, 'ai/strong/encoders.cjs'));
const {inputHash} = require('./policy-iteration-input-hashes.cjs');
const strategic = encoders.forRevision('4.3-strategic-correction');
const parent = encoders.forRevision('4.2-discard-correction');
readline.createInterface({input: process.stdin}).on('line', line => {
    try {
        const result = JSON.parse(line).map(root => {
            const {state, player} = root.request;
            const base = parent.encode(state, player), row = strategic.encode(state, player);
            assert.deepEqual(base.moves, root.legal);
            assert.deepEqual(row.moves, base.moves);
            assert.deepEqual(row.state.slice(0, 1216), base.state);
            assert.deepEqual(row.actions.map(a => a.slice(0, 100)), base.actions);
            assert.equal(row.state.length, 1217);
            assert.equal(row.state[1216], 1);
            return {rootId: root.rootId, policy_input_sha256: inputHash(base.state, base.actions), row};
        });
        process.stdout.write(JSON.stringify(result) + '\n');
    } catch (error) {
        process.stderr.write(error.stack + '\n');
        process.exit(1);
    }
});
