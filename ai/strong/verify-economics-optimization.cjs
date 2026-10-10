// Compare an isolated candidate runtime with the immutable experiment runtime.
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const baselineRoot = path.resolve(process.argv[2]);
const candidateRoot = path.resolve(process.argv[3]);
const load = root => ({ core: require(root + '/ai/core.cjs'),
    eco: require(root + '/ai/strong/economics.cjs'), search: require(root + '/ai/strong/search.cjs') });
const before = load(baselineRoot), after = load(candidateRoot);
const fixtures = fs.readFileSync(process.argv[4], 'utf8').trim().split('\n').map(JSON.parse);
let plans = 0, games = 0, decisions = 0;
for (const { request: { state: g } } of fixtures) {
    for (const p of g.players) {
        const cost = after.eco.purchaseCosts(g, p);
        for (let i = 0; i < 256; i++) {
            const used = [i % 9, Math.floor(i / 3) % 9, Math.floor(i / 7) % 9, Math.floor(i / 13) % 9];
            assert.equal(cost(used), before.eco.purchaseCost(g, p, used));
        }
        for (const buy of [false, true]) for (const unused of [false, true]) for (const endgame of [false, true]) {
            for (const budget of [0, 25, p.money]) {
                const options = { buy, unused, endgame, budget };
                assert.deepEqual(after.eco.plan(g, p, 22, options), before.eco.plan(g, p, 22, options));
                plans++;
            }
        }
    }
}
for (let n = 2; n <= 6; n++) for (let variant of ['original', 'recharged']) for (let sealed of [false, true]) {
    for (let seed = 0; seed < 2; seed++) {
        const options = { map: 'Germany', variant, fastBid: sealed, showMoney: true },
            key = `economic-equivalence-${n}-${variant}-${sealed}-${seed}`,
            a = before.core.E.setup(n, options, key), b = after.core.E.setup(n, options, key),
            ra = before.core.seedrandom(key), rb = after.core.seedrandom(key);
        let steps = 0;
        while (!before.core.E.ended(a) && steps++ < 1800) {
            const seat = a.currentPlayers[0];
            assert.equal(seat, b.currentPlayers[0]);
            const x = before.eco.choose(a, seat, ra), y = after.eco.choose(b, seat, rb);
            assert.deepEqual(x, y);
            before.core.E.move(a, x.action, seat); after.core.E.move(b, y.action, seat);
            decisions++;
        }
        assert.ok(before.core.E.ended(a) && after.core.E.ended(b));
        assert.deepEqual(a, b);
        games++;
    }
}
const baselineResults = [];
const timings = [];
console.log(JSON.stringify({ stage: 'games_verified', plans, games, decisions }));
for (let repeat = 0; repeat < 3; repeat++) {
    for (const label of repeat % 2 ? ['candidate', 'baseline'] : ['baseline', 'candidate']) {
        const engine = label === 'baseline' ? before : after;
        const start = performance.now();
        let rollouts = 0;
        for (let i = 0; i < fixtures.length; i++) {
            const row = fixtures[i];
            const result = engine.search.choose(row.request.state, row.request.player, {
                samples: 4, candidates: 6, geography: true, maxSteps: 2400,
                seed: `search-profile-v1-${row.fixtureIndex}`, includeSamples: true,
            });
            assert.equal(result.truncated || 0, 0);
            rollouts += result.evaluations;
            if (repeat === 0 && label === 'baseline') baselineResults.push(result);
            else assert.deepEqual(result, baselineResults[i]);
        }
        const timing = { repeat, label, seconds: (performance.now() - start) / 1000, rollouts };
        timings.push(timing); console.log(JSON.stringify(timing));
    }
}
console.log(JSON.stringify({ stage: 'verified', plans, games, decisions, positions: fixtures.length,
    exact_search_outcomes: true, timings }));
