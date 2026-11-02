const assert = require('node:assert/strict');
const { test } = require('node:test');
const f = require('./features.cjs'),
    t = require('./teacher.cjs'),
    { start, collect } = require('./game.cjs');
const spec = { map: 'Germany', players: 4, variant: 'recharged', fastBid: true, seed: 'multimap-unit-v1' };
test('public encoder and teacher ignore hidden deck, bid, seed, plans and logs', () => {
    const g = start(spec),
        seat = g.currentPlayers[0],
        base = f.encode(g, seat),
        scores = t.scores(g, seat);
    g.seed = 'poison';
    g.powerPlantsDeck.reverse();
    g.powerPlantDeckAfterStep3 = [{ number: 777 }];
    g.hiddenLog = [{ secret: 'poison' }];
    g.log = [];
    g.poweringChoices = { secret: 123 };
    g.automation = { plans: { secret: 456 } };
    g.currentBid = 777;
    for (const p of g.players) {
        p.bid = 999;
        p.lastMove = { secret: 'poison' };
    }
    assert.deepEqual(f.encode(g, seat), base);
    assert.deepEqual(t.scores(g, seat), scores);
});
test('city permutation preserves tensors up to permutation and action references', () => {
    const g = start(spec),
        seat = g.currentPlayers[0],
        a = f.encode(g, seat);
    g.map.cities.reverse();
    const b = f.encode(g, seat),
        n = a.nodes.length;
    assert.deepEqual(a.global, b.global);
    assert.deepEqual(a.players, b.players);
    assert.deepEqual(a.actions, b.actions);
    assert.deepEqual(a.nodes, b.nodes.slice().reverse());
    for (let k = 0; k < 4; k++)
        for (let i = 0; i < n; i++)
            for (let j = 0; j < n; j++) assert.equal(a.relations[k][i][j], b.relations[k][n - 1 - i][n - 1 - j]);
});
test('six maps and all player counts/variants/auctions complete legally with finite features', () => {
    for (const map of f.MAPS)
        for (const players of [2, 3, 4, 5, 6])
            for (const variant of ['original', 'recharged'])
                for (const fastBid of [false, true]) {
                    const x = collect({
                        map,
                        players,
                        variant,
                        fastBid,
                        seed: `multimap-smoke-v1:${map}:${players}:${variant}:${fastBid}`,
                        samplesPerPhase: 1,
                    });
                    assert(x.terminal);
                    assert(Math.abs(x.credit.reduce((a, b) => a + b, 0) - 1) < 1e-8);
                    for (const r of x.rows) {
                        assert.equal(r.global.length, 273);
                        assert.equal(r.players[0].length, 80);
                        assert.equal(r.nodes[0].length, 36);
                        assert.equal(r.actions[0].length, 34);
                        assert(r.targets.some((x) => x === 1));
                    }
                }
});
test('reject unsupported maps and private-money games instead of pretending support', () => {
    const g = start(spec),
        seat = g.currentPlayers[0];
    g.options.showMoney = false;
    assert.throws(() => f.encode(g, seat));
    g.options.showMoney = true;
    g.map.name = 'Korea';
    assert.throws(() => f.encode(g, seat));
});
test('all legal bids retained, resource cost and discount encoded from actual rules', () => {
    const g = start({ ...spec, players: 2 });
    g.players[0].availableMoves = { Bid: Array.from({ length: 501 }, (_, i) => i) };
    g.currentPlayers = [0];
    assert.equal(f.legal(g, 0).length, 501);
    g.coalMarket = 0;
    g.coalSupply = 10;
    g.map.name = 'USA';
    assert.equal(f.resourcePrice(g, 'coal'), 8);
});
