// Paired public scenarios across continuation policies and nested search budgets.
const fs = require('node:fs');
const search = require('./search.cjs');
const rows = fs.readFileSync(process.argv[2], 'utf8').trim().split('\n');
const row = JSON.parse(rows[Number(process.argv[3])]);
const continuation = process.argv[4],
    batch = process.argv[5];
if (!['a', 'b'].includes(batch)) throw Error('Invalid batch');
const { state, player } = row.request;
const result = search.choose(state, player, {
    samples: 384,
    candidates: 6,
    geography: true,
    maxSteps: 2400,
    seed: `teacher-reliability-v1-${row.fixtureIndex}-${batch}`,
    continuation,
    includeSamples: true,
});
console.log(
    JSON.stringify({
        fixtureIndex: row.fixtureIndex,
        cell: row.cell,
        round: state.round,
        continuation,
        batch,
        samples: 384,
        result,
    })
);
