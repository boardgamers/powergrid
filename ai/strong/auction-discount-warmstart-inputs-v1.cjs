const assert = require('node:assert/strict'), path = require('node:path'), readline = require('node:readline');
const base = require(path.join(path.resolve(process.argv[2]), 'ai/strong/features-v4_3.cjs'));
const extension = require('./features-v4_4.cjs');
readline.createInterface({input: process.stdin}).on('line', line => {
    try {
        const answers = JSON.parse(line).map(fixture => {
            const {state, player} = fixture.request;
            const original = base.encode(state, player), row = extension.extend(state, original);
            assert.deepEqual(row.moves, fixture.legal);
            assert.deepEqual(row.state.slice(0, 1217), original.state);
            assert.deepEqual(row.actions.map(a => a.slice(0, 101)), original.actions);
            return {state: row.state, actions: row.actions};
        });
        process.stdout.write(JSON.stringify(answers) + '\n');
    } catch (error) {process.stderr.write(error.stack + '\n'); process.exit(1);}
});
