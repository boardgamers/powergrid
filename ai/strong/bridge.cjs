const c = require('../core.cjs'),
    eco = require('./economics.cjs'),
    f = require('./features.cjs'),
    readline = require('node:readline');
let envs = [],
    sequence = 0;
const seed = process.env.SEED || 'strong-train';
function applyBot(e, p) {
    const role = e.roles[p];
    if (role === 'legacy') {
        const old = Math.random;
        Math.random = e.rng;
        try {
            c.E.moveAI(e.g, p);
        } finally {
            Math.random = old;
        }
    } else
        c.E.move(
            e.g,
            role === 'heuristic' ? c.heuristic(e.g, p, e.rng).action : eco.choose(e.g, p, e.rng, role).action,
            p
        );
    e.steps++;
}
function advance(e) {
    while (
        !c.E.ended(e.g) &&
        e.steps < 1600 &&
        !['learner', 'snapshot0', 'snapshot1', 'snapshot2'].includes(e.roles[e.g.currentPlayers[0]])
    )
        applyBot(e, e.g.currentPlayers[0]);
}
function observation(e) {
    if (c.E.ended(e.g) || e.steps >= 1600) return null;
    const seat = e.g.currentPlayers[0],
        x = f.encode(e.g, seat);
    delete x.moves;
    return { ...x, episode: e.id, roles: e.roles, round: e.g.round };
}
function reset(mode = 'mixed') {
    const id = sequence++,
        seat = Math.floor(id / 4) % 3,
        kind = Math.floor(c.seedrandom(seed + '-opponents-' + id)() * 8);
    const opponent =
        mode === 'mixed'
            ? ['economic', 'heuristic', 'rush', 'legacy', 'selfplay', 'snapshot0', 'snapshot1', 'snapshot2'][kind]
            : mode;
    const roles =
        opponent === 'selfplay'
            ? ['learner', 'learner', 'learner']
            : Array.from({ length: 3 }, (_, i) => (i === seat ? 'learner' : opponent));
    const e = {
        id,
        g: c.start(seed + '-' + id, id % 2 ? 'recharged' : 'original', id % 4 < 2),
        roles,
        rng: c.seedrandom(seed + '-bot-' + id),
        steps: 0,
    };
    advance(e);
    return e;
}
(async () => {
    for await (const line of readline.createInterface({ input: process.stdin })) {
        try {
            const q = JSON.parse(line),
                ended = [];
            if (q.op === 'reset') envs = Array.from({ length: q.n }, () => reset(q.mode));
            else if (q.op === 'step')
                for (let i = 0; i < envs.length; i++) {
                    const e = envs[i];
                    if (q.actions[i] === null) continue;
                    const seat = e.g.currentPlayers[0];
                    c.E.move(e.g, c.candidates(e.g, seat)[q.actions[i]], seat);
                    e.steps++;
                    advance(e);
                    if (c.E.ended(e.g) || e.steps >= 1600)
                        ended.push({
                            env: i,
                            episode: e.id,
                            truncated: !c.E.ended(e.g),
                            value: c.E.ended(e.g) ? c.outcome(e.g) : [0, 0, 0],
                            steps: e.steps,
                            roles: e.roles,
                        });
                }
            else throw Error('unknown op');
            console.log(JSON.stringify({ observations: envs.map(observation), ended }));
        } catch (err) {
            console.error(err.stack);
            process.exit(1);
        }
    }
})();
