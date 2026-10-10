// Development CPU profile only; no gradients or strength qualification.
const fs = require('node:fs');
const crypto = require('node:crypto');
const path = require('node:path');
const search = require(path.resolve(process.argv[2], 'ai/strong/search.cjs'));
const fixtures = fs.readFileSync(process.argv[3]);
const rows = fixtures.toString().trim().split('\n').map(JSON.parse);
const start = performance.now();
const results = rows.map(row => {
    const begin = performance.now();
    const result = search.choose(row.request.state, row.request.player, {
        samples: 4, candidates: 6, geography: true, maxSteps: 2400,
        seed: `search-profile-v1-${row.fixtureIndex}`,
    });
    return { fixtureIndex: row.fixtureIndex, cell: row.cell,
        evaluations: result.evaluations, truncated: result.truncated || 0,
        elapsed_ms: performance.now() - begin };
});
console.log(JSON.stringify({ fixtures_sha256: crypto.createHash('sha256').update(fixtures).digest('hex'),
    elapsed_ms: performance.now() - start, samples: 4, results }));
