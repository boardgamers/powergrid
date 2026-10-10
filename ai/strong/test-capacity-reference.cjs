const test = require('node:test'), assert = require('node:assert/strict'),
    c = require('../core.cjs'), old = require('./economics.cjs'), corrected = require('./economics-v4_1.cjs');
test('capacity reference preserves every original choice and RNG consumption at 3–6 players', () => {
    let decisions = 0;
    for (let n = 3; n <= 6; n++) for (const variant of ['original', 'recharged']) for (const fastBid of [false, true]) {
        const seed = `capacity-identity-${n}-${variant}-${fastBid}`,
            g = c.E.setup(n, {map: 'Germany', variant, fastBid, showMoney: true}, seed),
            left = c.seedrandom(seed + '-bot'), right = c.seedrandom(seed + '-bot');
        let steps = 0;
        while (!c.E.ended(g) && steps < 1600) {
            const seat = g.currentPlayers[0], a = old.choose(g, seat, left), b = corrected.choose(g, seat, right);
            assert.deepEqual(b, a);
            c.E.move(g, a.action, seat); steps++; decisions++;
        }
        assert.ok(c.E.ended(g));
        assert.equal(left(), right());
    }
    console.log({unchangedGames: 16, decisions});
});
test('corrected valuation matches the actual two-player addition instead of replacement', () => {
    const g = c.E.setup(2, {map: 'Germany'}, 'capacity-fourth'), p = g.players[0];
    const all = [...g.actualMarket, ...g.futureMarket, ...g.powerPlantsDeck];
    p.powerPlants = [4, 7, 10].map(n => all.find(pp => pp.number === n));
    assert.ok(p.powerPlants.every(Boolean));
    p.money = 55; p.cities = g.map.cities.slice(0, 4); g.round = 4;
    for (const resource of c.RES) g[resource + 'Market'] = g[resource + 'Prices'].length;
    const pp = all.find(pp => pp.number === 11);
    assert.equal(corrected.plantLimit(g), 4);
    const before = old.plan(g, p, 22), after = old.plan(g, {...p, powerPlants: [...p.powerPlants, pp]}, 22);
    const gain = pp.citiesPowered, need = Math.max(0, p.cities.length + 3 - c.capacity(p));
    const expected = Math.max(0, Math.min(47, pp.number * .55 + gain * (need > 0 ? 10 : 6) + (before.cost - after.cost) * 2));
    assert.equal(corrected.plantValue(g, p, pp), expected);
    assert.notEqual(corrected.plantValue(g, p, pp), old.plantValue(g, p, pp));
    const altered = structuredClone(g);
    altered.options.fastBid = true; g.options.fastBid = true;
    altered.currentBid = 999; altered.players.forEach(p => p.bid = 999); altered.powerPlantsDeck.reverse();
    assert.deepEqual(corrected.scores(altered, 0), corrected.scores(g, 0));
});
