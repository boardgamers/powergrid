const test = require('node:test'),
    assert = require('node:assert/strict'),
    c = require('../core.cjs'),
    f = require('./features.cjs'),
    spatial = require('./spatial.cjs'),
    eco = require('./economics.cjs');
test('restock, acting players, holdings and cities are observable; sealed values are not', () => {
    const g = c.start('information', 'recharged', true),
        seat = g.currentPlayers[0],
        original = f.encode(g, seat);
    g.players[(seat + 1) % 3].bid = 999;
    g.currentBid = 999;
    g.powerPlantsDeck.reverse();
    g.seed = 'secret';
    assert.deepEqual(f.encode(g, seat), original);
    g.coalResupply[1][0]++;
    assert.notDeepEqual(f.observe(g, seat), original.state);
    const before = f.observe(g, seat);
    g.players[(seat + 1) % 3].cities.push({ name: g.map.cities[0].name, position: 0 });
    assert.notDeepEqual(f.observe(g, seat), before);
    assert.equal(original.state.length, 738);
    assert.ok(original.actions.every((a) => a.length === 96 && a.every(Number.isFinite)));
});
test('UK/Ireland tracks opponent presence and empty slots on both islands', () => {
    const g = c.E.setup(3, { map: 'UK & Ireland' }, 'islands'),
        gb = g.map.cities.find((c) => c.island === 'gb'),
        ie = g.map.cities.find((c) => c.island === 'ie');
    const initial = spatial.territories(g, 0);
    g.players[1].cities.push({ name: gb.name, position: 0 });
    let t = spatial.territories(g, 0);
    assert.equal(t.islands.find((x) => x.name === 'gb').owned[1], 1);
    assert.equal(t.islands.find((x) => x.name === 'ie').owned[1], 0);
    g.players[1].cities.push({ name: ie.name, position: 0 });
    t = spatial.territories(g, 0);
    assert.ok(t.islands.every((x) => x.owned[1] === 1));
    for (const island of t.islands) {
        const old = initial.islands.find((x) => x.name === island.name);
        assert.equal(island.empty, old.empty - 1);
        assert.equal(island.open, old.open - 1);
    }
});
test('projected order uses cities and highest-plant tie break', () => {
    const g = c.start('order');
    g.players[0].cities = [{ name: 'a' }];
    g.players[1].cities = [{ name: 'b' }, { name: 'c' }];
    g.players[0].powerPlants = [{ number: 20 }];
    g.players[1].powerPlants = [{ number: 10 }];
    assert.equal(spatial.orderAfterBuild(g, 0)[0], 0);
});
test('economic production consumes a feasible fuel combination and completes games', () => {
    for (let i = 0; i < 12; i++) {
        const g = c.start('strong-legal-' + i, i % 2 ? 'recharged' : 'original', i % 4 < 2),
            rng = c.seedrandom('tie' + i);
        let steps = 0;
        while (!c.E.ended(g) && steps++ < 1800) {
            const p = g.currentPlayers[0],
                x = eco.choose(g, p, rng);
            assert.ok(Number.isFinite(eco.scores(g, p, [x.action])[0]));
            c.E.move(g, x.action, p);
        }
        assert.ok(c.E.ended(g));
    }
});

test('search choices do not change with hidden deck order or sealed bid amounts', () => {
    const search = require('./search.cjs'),
        g = c.start('search-info', 'original', true);
    let p = g.currentPlayers[0];
    c.E.move(g, c.candidates(g, p)[0], p);
    p = g.currentPlayers[0];
    const first = search.choose(g, p, { samples: 2, candidates: 3, seed: 'same-belief', maxSteps: 700 });
    g.powerPlantsDeck.reverse();
    g.players.forEach((x, i) => {
        if (i !== p) x.bid = 123;
    });
    g.currentBid = 456;
    g.hiddenLog = [{ secret: 'not observable' }];
    const second = search.choose(g, p, { samples: 2, candidates: 3, seed: 'same-belief', maxSteps: 700 });
    assert.equal(first.index, second.index);
    assert.deepEqual(first.values, second.values);
});

test('public topology preserves map edges, ownership and island crossing rule', () => {
    const graph = require('./public-graph.cjs');
    for (const map of ['Germany', 'UK & Ireland', 'USA', 'France']) {
        const g = c.E.setup(3, { map }, 'graph');
        const x = graph.encode(g, 0);
        assert.equal(x.nodes.length, g.map.cities.length);
        assert.ok(x.edges.every((e) => e.a >= 0 && e.b >= 0 && e.cost >= 0));
        g.seed = 'private';
        g.powerPlantsDeck.reverse();
        g.players[1].bid = 999;
        assert.deepEqual(graph.encode(g, 0), x);
    }
});
