const c = require('./core.cjs'),
    readline = require('node:readline');
let g, seat, opponent, rng, steps;
function advance() {
    while (!c.E.ended(g) && g.currentPlayers[0] !== seat && steps < 1600) {
        const p = g.currentPlayers[0];
        if (opponent === 'legacy') {
            const old = Math.random;
            Math.random = rng;
            try {
                g = c.E.moveAI(g, p);
            } finally {
                Math.random = old;
            }
        } else g = c.E.move(g, c.heuristic(g, p, rng).action, p);
        steps++;
    }
    if (c.E.ended(g) || steps >= 1600)
        return {
            done: true,
            truncated: !c.E.ended(g),
            win: c.E.ended(g) ? c.outcome(g)[seat] : 0,
            round: g.round,
            steps,
            final: g.players.map((p) => ({ powered: p.citiesPowered, money: p.money, cities: p.cities.length })),
        };
    const a = c.candidates(g, seat);
    return {
        done: false,
        state: c.observe(g, seat),
        actions: a.map((x) => c.actionFeatures(g, seat, x)),
        heuristic: c.heuristic(g, seat, rng).index,
    };
}
(async () => {
    for await (const line of readline.createInterface({ input: process.stdin })) {
        try {
            const q = JSON.parse(line);
            if (q.op === 'reset') {
                g = c.start(q.seed, q.variant, q.sealed);
                seat = q.seat;
                opponent = q.opponent || 'heuristic';
                rng = c.seedrandom(q.seed + '-opponents');
                steps = 0;
            } else if (q.op === 'step') {
                g = c.E.move(g, c.candidates(g, seat)[q.action], seat);
                steps++;
            }
            console.log(JSON.stringify(advance()));
        } catch (e) {
            console.error(e.stack);
            process.exit(1);
        }
    }
})();
