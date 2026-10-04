const fs = require('node:fs'),
    assert = require('node:assert/strict');
const c = require('./core.cjs');
const games = fs.readFileSync('ai/private-data/human-games.jsonl', 'utf8').trim().split('\n').map(JSON.parse);
const results = [];
let admitted = [];
const clean = (p) => ({
    money: p.money,
    citiesPowered: p.citiesPowered,
    cities: p.cities.map((c) => c.name).sort(),
    powerPlants: p.powerPlants.map((p) => p.number).sort((a, b) => a - b),
});
for (const h of games) {
    let count = 0;
    try {
        if (h.players.some((p) => p.dropped || p.quit || p.bot)) throw Error('dropped/quit/bot');
        if (h.phase !== c.E.Phase.GameEnd) throw Error('not engine terminal');
        let g = c.E.setup(3, h.options, h.seed);
        for (const m of h.moves) {
            g = c.E.move(g, m.move, m.player);
            count++;
        }
        assert.deepEqual(g.players.map(clean), h.final);
        assert.ok(c.E.ended(g));
        admitted.push(h);
        results.push({
            id: h.id,
            version: h.version,
            variant: h.options.variant,
            sealed: !!h.options.fastBid,
            moves: count,
            accepted: true,
        });
    } catch (e) {
        results.push({ id: h.id, version: h.version, moves: count, accepted: false, reason: e.message.split('\n')[0] });
    }
}
fs.writeFileSync('ai/private-data/verified-games.jsonl', admitted.map((x) => JSON.stringify(x)).join('\n'));
const report = {
    total: games.length,
    accepted: admitted.length,
    acceptedSealed: admitted.filter((x) => x.options.fastBid).length,
    results,
};
fs.writeFileSync('ai/replay-audit.json', JSON.stringify(report, null, 2));
console.log({
    total: games.length,
    accepted: admitted.length,
    reasons: results.reduce((o, r) => {
        let k = r.accepted ? 'accepted' : r.reason;
        o[k] = (o[k] || 0) + 1;
        return o;
    }, {}),
});
