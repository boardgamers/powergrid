const c = require('../core.cjs'),
    eco = require('./economics.cjs'),
    search = require('./search.cjs');
const seeds = +(process.env.SEEDS || 20),
    candidate = process.argv[2] || 'economic',
    opponent = process.argv[3] || 'heuristic';
function play(g, p, type, rng) {
    if (type === 'search') {
        const legal = c.candidates(g, p),
            strategic = legal.length > 1 && legal.some((a) => ['ChoosePowerPlant', 'Bid', 'Build'].includes(a.name));
        return c.E.move(
            g,
            strategic
                ? search.choose(g, p, {
                      samples: 4,
                      candidates: 5,
                      seed: 'search-' + g.round + '-' + p + '-' + Math.floor(rng() * 1e9),
                  }).action
                : eco.choose(g, p, rng).action,
            p
        );
    }
    if (type === 'legacy') {
        const old = Math.random;
        Math.random = rng;
        try {
            return c.E.moveAI(g, p);
        } finally {
            Math.random = old;
        }
    }
    return c.E.move(g, type === 'heuristic' ? c.heuristic(g, p, rng).action : eco.choose(g, p, rng, type).action, p);
}
let results = [];
for (const variant of ['original', 'recharged'])
    for (const sealed of [false, true]) {
        for (let seed = +(process.env.SEED_START || 0); seed < +(process.env.SEED_START || 0) + seeds; seed++)
            for (let seat = 0; seat < 3; seat++) {
                let g = c.start('strong-dev-' + seed, variant, sealed),
                    rng = c.seedrandom('strong-' + seed),
                    steps = 0;
                while (!c.E.ended(g) && steps++ < 1600) {
                    const p = g.currentPlayers[0];
                    g = play(g, p, p === seat ? candidate : opponent, rng);
                }
                results.push({
                    variant,
                    sealed,
                    seed,
                    seat,
                    steps,
                    truncated: !c.E.ended(g),
                    win: c.E.ended(g) ? c.outcome(g)[seat] : 0,
                });
            }
        const rows = results.filter((r) => r.variant === variant && r.sealed === sealed);
        console.error(
            JSON.stringify({
                variant,
                sealed,
                win: rows.reduce((s, r) => s + r.win, 0) / rows.length,
                truncated: rows.filter((r) => r.truncated).length,
            })
        );
    }
console.log(
    JSON.stringify({
        candidate,
        opponent,
        seeds,
        win: results.reduce((s, r) => s + r.win, 0) / results.length,
        results,
    })
);
