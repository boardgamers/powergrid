const test = require('node:test'),
    assert = require('node:assert/strict'),
    c = require('./core.cjs');
test('hidden deck, seed, premoves and sealed bids cannot change observations or candidates', () => {
    let g = c.start('privacy', 'original', true);
    g = c.E.move(g, c.candidates(g, g.currentPlayers[0])[0], g.currentPlayers[0]);
    const p = g.currentPlayers[0],
        a = c.observe(g, p),
        moves = c.candidates(g, p).map((m) => c.actionFeatures(g, p, m));
    g.seed = 'do not use';
    g.powerPlantsDeck.reverse();
    g.hiddenLog = [{ secret: 123 }];
    g.automation = { plans: { 1: { secret: 321 } } };
    g.currentBid = 999;
    g.players.forEach((x, i) => {
        if (i !== p) x.bid = 987 + i;
    });
    assert.deepEqual(c.observe(g, p), a);
    assert.deepEqual(
        c.candidates(g, p).map((m) => c.actionFeatures(g, p, m)),
        moves
    );
});
test('original/recharged and sealed/open produce finite fixed features and legal complete games', () => {
    for (let seed = 0; seed < 16; seed++) {
        let g = c.start('test-' + seed, seed % 2 ? 'original' : 'recharged', seed % 4 < 2),
            rng = c.seedrandom('bot' + seed),
            steps = 0;
        while (!c.E.ended(g) && steps++ < 1600) {
            const p = g.currentPlayers[0],
                a = c.candidates(g, p);
            assert.equal(c.observe(g, p).length, 541);
            for (const m of a) {
                const f = c.actionFeatures(g, p, m);
                assert.equal(f.length, 74);
                assert.ok(f.every(Number.isFinite));
            }
            g = c.E.move(g, c.heuristic(g, p, rng).action, p);
        }
        assert.ok(c.E.ended(g));
        assert.equal(
            c.outcome(g).reduce((a, b) => a + b, 0),
            1
        );
    }
});
test('seeded heuristic runs reproduce terminal state', () => {
    function run() {
        let g = c.start('repeat', 'recharged', true),
            r = c.seedrandom('tie');
        for (let i = 0; i < 1600 && !c.E.ended(g); i++) {
            const p = g.currentPlayers[0];
            g = c.E.move(g, c.heuristic(g, p, r).action, p);
        }
        return JSON.stringify(g);
    }
    assert.equal(run(), run());
});

test('unsupported maps, player counts and drafts are rejected', () => {
    for (const options of [{ map: 'USA' }, { randomizeMap: true }, { chooseRegions: true }, { chooseColors: true }]) {
        const g = c.E.setup(3, { map: 'Germany', ...options }, 'scope');
        assert.throws(() => c.observe(g, g.currentPlayers[0]), /Baseline supports/);
    }
    const g = c.E.setup(4, { map: 'Germany' }, 'scope');
    assert.throws(() => c.observe(g, g.currentPlayers[0]), /Baseline supports/);
});

test('Recharged replacement cities have distinct action features', () => {
    const g = c.start('city-encoding', 'recharged');
    for (const [replacement, original] of [
        ['Stralsund', 'Torgelow'],
        ['Mainz', 'Wiesbaden'],
    ]) {
        assert.ok(c.CITIES.includes(replacement));
        assert.notDeepEqual(
            c.actionFeatures(g, 0, { name: 'Build', data: { name: replacement, price: 10 } }),
            c.actionFeatures(g, 0, { name: 'Build', data: { name: original, price: 10 } })
        );
    }
});
