const c = require('./core.cjs'),
    readline = require('node:readline');
let envs = [],
    sequence = 0;
const seed = process.env.SEED || 'rollout-v1';
const rng = c.seedrandom(seed);
function reset() {
    const id = sequence++;
    return { g: c.start(seed + '-' + id, id % 2 ? 'recharged' : 'original', id % 4 < 2), id, steps: 0 };
}
function obs(e) {
    const seat = e.g.currentPlayers[0],
        a = c.candidates(e.g, seat);
    return {
        state: c.observe(e.g, seat),
        actions: a.map((x) => c.actionFeatures(e.g, seat, x)),
        seat,
        episode: e.id,
        heuristic: c.heuristic(e.g, seat, rng).index,
    };
}
(async () => {
    for await (const line of readline.createInterface({ input: process.stdin })) {
        try {
            const q = JSON.parse(line);
            let ended = [];
            if (q.op === 'reset') {
                envs = Array.from({ length: q.n }, reset);
            } else if (q.op === 'step') {
                q.actions.forEach((action, i) => {
                    const e = envs[i],
                        seat = e.g.currentPlayers[0];
                    e.g = c.E.move(e.g, c.candidates(e.g, seat)[action], seat);
                    e.steps++;
                    if (c.E.ended(e.g) || e.steps >= 1600) {
                        ended.push({
                            env: i,
                            episode: e.id,
                            truncated: !c.E.ended(e.g),
                            value: c.E.ended(e.g) ? c.outcome(e.g) : null,
                            steps: e.steps,
                            round: e.g.round,
                        });
                        envs[i] = reset();
                    }
                });
            } else throw Error('unknown operation');
            console.log(JSON.stringify({ observations: envs.map(obs), ended }));
        } catch (e) {
            console.error(e.stack);
            process.exit(1);
        }
    }
})();
