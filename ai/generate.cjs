const fs = require('node:fs'),
    c = require('./core.cjs');
const count = Number(process.env.GAMES || 600),
    rng = c.seedrandom('dataset-v1'),
    out = fs.openSync(process.argv[2] || 'dataset.jsonl', 'w');
let samples = 0,
    completed = 0,
    truncated = 0;
function writeEpisode(rows, g, id) {
    const result = c.outcome(g);
    for (const row of rows) {
        row.value = [row.seat, (row.seat + 1) % 3, (row.seat + 2) % 3].map((i) => result[i]);
        row.game = id;
        fs.writeSync(out, JSON.stringify(row) + '\n');
        samples++;
    }
}
for (let i = 0; i < count; i++) {
    let g = c.start('train-v1-' + i, i % 2 ? 'recharged' : 'original', i % 4 < 2),
        rows = [],
        n = 0;
    while (!c.E.ended(g) && n++ < 1600) {
        const seat = g.currentPlayers[0],
            a = c.candidates(g, seat),
            h = c.heuristic(g, seat, rng);
        if (a.length > 1 && rng() < 0.4)
            rows.push({
                state: c.observe(g, seat),
                actions: a.map((x) => c.actionFeatures(g, seat, x)),
                target: h.index,
                seat,
                weight: 1,
            });
        let index = rng() < 0.015 ? Math.floor(rng() * a.length) : h.index;
        g = c.E.move(g, a[index], seat);
    }
    if (c.E.ended(g)) {
        writeEpisode(rows, g, 'synthetic-' + i);
        completed++;
    } else truncated++;
    if (i % 100 === 99) console.error(JSON.stringify({ games: i + 1, samples, completed, truncated }));
}
const path = 'ai/private-data/verified-games.jsonl';
if (fs.existsSync(path))
    for (const line of fs.readFileSync(path, 'utf8').split('\n').filter(Boolean)) {
        const h = JSON.parse(line);
        if (h.options.chooseColors || h.options.chooseRegions || h.options.randomizeMap) {
            console.error(JSON.stringify({ skippedHumanGame: h.id, reason: 'unsupported setup' }));
            continue;
        }
        let g = c.E.setup(3, h.options, h.seed),
            rows = [];
        for (const m of h.moves) {
            const seat = m.player,
                a = c.candidates(g, seat),
                target = a.findIndex(
                    (x) => JSON.stringify(x.data) === JSON.stringify(m.move.data) && x.name === m.move.name
                );
            if (target >= 0 && a.length > 1)
                rows.push({
                    state: c.observe(g, seat),
                    actions: a.map((x) => c.actionFeatures(g, seat, x)),
                    target,
                    seat,
                    weight: 1.5,
                });
            g = c.E.move(g, m.move, seat);
        }
        writeEpisode(rows, g, 'human-' + h.id);
    }
fs.closeSync(out);
console.error(JSON.stringify({ completed, truncated, samples }));
