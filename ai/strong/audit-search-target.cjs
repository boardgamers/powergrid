// Independent search batches on fixed development positions; no learning.
const fs = require('node:fs');
const search = require('./search.cjs');
const c = require('../core.cjs');
const rows = fs.readFileSync(process.argv[2], 'utf8').trim().split('\n');
const row = JSON.parse(rows[Number(process.argv[3])]);
const { state, player } = row.request;
const batches = ['a', 'b'].map((batch) => {
    const result = search.choose(state, player, {
        samples: 48,
        candidates: 6,
        geography: true,
        maxSteps: 2400,
        seed: `teacher-reliability-v1-${row.fixtureIndex}-${batch}`,
        includeSamples: true,
    });
    return { batch, ...result };
});
console.log(
    JSON.stringify({
        fixtureIndex: row.fixtureIndex,
        cell: row.cell,
        round: state.round,
        actions: c.candidates(state, player),
        samplePolicies: Array.from({ length: 48 }, (_, i) => (i % 2 ? 'heuristic' : 'economic')),
        batches,
    })
);
