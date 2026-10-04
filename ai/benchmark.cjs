const c = require('./core.cjs'),
    fs = require('node:fs'),
    os = require('node:os'),
    { performance } = require('node:perf_hooks');
let runs = [];
for (const variant of ['original', 'recharged'])
    for (const sealed of [false, true]) {
        let steps = 0,
            ended = 0;
        const t = performance.now();
        for (let i = 0; i < 100; i++) {
            let g = c.start('benchmark-' + i, variant, sealed),
                rng = c.seedrandom('policy-' + i),
                n = 0;
            while (!c.E.ended(g) && n++ < 1600) {
                const p = g.currentPlayers[0];
                g = c.E.move(g, c.heuristic(g, p, rng).action, p);
                steps++;
            }
            ended += +c.E.ended(g);
        }
        const sec = (performance.now() - t) / 1000;
        runs.push({
            variant,
            sealed,
            games: 100,
            ended,
            steps,
            seconds: sec,
            gamesPerSecond: 100 / sec,
            stepsPerSecond: steps / sec,
        });
    }
const result = { cpu: os.cpus()[0].model, node: process.version, runs };
console.log(JSON.stringify(result, null, 2));
