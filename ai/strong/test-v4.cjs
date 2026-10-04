const test = require('node:test'),
    assert = require('node:assert/strict');
const c = require('../core.cjs'),
    f = require('./features-v4.cjs'),
    old = require('./features.cjs'),
    eco = require('./economics.cjs');
test('schema 4 covers complete 2–6 player games in all four rule combinations', () => {
    let decisions = 0;
    for (let n = 2; n <= 6; n++)
        for (const variant of ['original', 'recharged'])
            for (const fastBid of [false, true]) {
                const g = c.E.setup(
                    n,
                    { map: 'Germany', variant, fastBid, showMoney: true },
                    `v4-${n}-${variant}-${fastBid}`
                );
                let steps = 0;
                while (!c.E.ended(g) && steps < 2400) {
                    const seat = g.currentPlayers[0],
                        x = f.encode(g, seat);
                    assert.equal(x.state.length, 1149);
                    assert.equal(
                        x.playerMask.reduce((a, b) => a + b),
                        n
                    );
                    assert.deepEqual(
                        x.playerOrder,
                        Array.from({ length: n }, (_, i) => (seat + i) % n)
                    );
                    assert.ok(x.actions.every((a) => a.length === 98 && a.every(Number.isFinite)));
                    assert.deepEqual(x.state.slice(264 + 74 * n, 708), Array(74 * (6 - n)).fill(0));
                    if (steps === 0 && fastBid) {
                        const before = f.encode(g, seat),
                            hidden = structuredClone(g);
                        hidden.currentBid = 999;
                        hidden.players.forEach((p) => (p.bid = 999));
                        hidden.powerPlantsDeck.reverse();
                        hidden.seed = 'hidden';
                        assert.deepEqual(f.encode(hidden, seat), before);
                    }
                    c.E.move(g, x.moves[x.teacher], seat);
                    steps++;
                    decisions++;
                }
                assert.ok(c.E.ended(g), `unfinished ${n}/${variant}/${fastBid} at ${steps}`);
                assert.equal(c.outcome(g).length, n);
            }
    console.log({ completeGames: 20, decisions });
});
test('schema 3 representation remains unchanged and schema 4 observes every opponent', () => {
    const g = c.start('frozen-feature'),
        seat = g.currentPlayers[0];
    assert.equal(old.encode(g, seat).state.length, 738);
    for (let n = 2; n <= 6; n++) {
        const game = c.E.setup(n, { map: 'Germany' }, 'public-' + n),
            viewer = game.currentPlayers[0];
        for (let other = 0; other < n; other++) {
            const before = f.observe(game, viewer).state;
            game.players[other].money++;
            assert.notDeepEqual(f.observe(game, viewer).state, before);
        }
        assert.equal(eco.replenishment(game, 'coal'), game.coalResupply[n - 2][game.step - 1]);
    }
});
