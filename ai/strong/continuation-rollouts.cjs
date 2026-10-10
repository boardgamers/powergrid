// Batched public-belief continuations. Neural inference lives in the Python driver.
const c = require('../core.cjs');
const eco = require('./economics.cjs');
const search = require('./search.cjs');
const encoders = require('./encoders.cjs');
const { createAnalysisScenario } = require('../../engine/dist/src/analysis.js');

class ContinuationBatch {
    reset(q) {
        if (!['neural', 'mixed', 'economic', 'heuristic'].includes(q.continuation))
            throw Error('Invalid continuation policy');
        if (!Number.isInteger(q.samples) || q.samples < 1 || !Number.isInteger(q.maxSteps) || q.maxSteps < 1)
            throw Error('Invalid rollout budget');
        const actions = c.candidates(q.state, q.player);
        const options = q.options || search.shortlist(q.state, q.player, 6, true);
        if (!options.length || new Set(options).size !== options.length ||
            options.some(i => !Number.isInteger(i) || i < 0 || i >= actions.length))
            throw Error('Invalid search proposal');
        const offset = q.offset || 0;
        if (!Number.isInteger(offset) || offset < 0 || !Number.isInteger(q.n) || q.n < 1 ||
            offset + q.n > q.samples * options.length) throw Error('Invalid rollout range');
        this.encoder = encoders.forRevision(q.featureRevision);
        this.envs = Array.from({ length: q.n }, (_, i) => {
            const index = i + offset, sample = Math.floor(index / options.length);
            const actionIndex = options[index % options.length];
            const g = createAnalysisScenario(q.state, { player: q.player, seed: q.seed + '-' + sample });
            c.E.move(g, structuredClone(actions[actionIndex]), q.player);
            return { g, sample, actionIndex, steps: 0, maxSteps: q.maxSteps, player: q.player,
                continuation: q.continuation, reported: false, rng: c.seedrandom(q.seed + '-rollout-' + sample) };
        });
        return this.reply();
    }

    advance(e) {
        while (!c.E.ended(e.g) && e.steps < e.maxSteps) {
            const seat = e.g.currentPlayers[0];
            if (e.continuation === 'neural') {
                const actions = c.candidates(e.g, seat);
                if (actions.length !== 1) return;
                c.E.move(e.g, actions[0], seat);
            } else {
                const heuristic = e.continuation === 'heuristic' || (e.continuation === 'mixed' && e.sample % 2);
                c.E.move(e.g, heuristic ? c.heuristic(e.g, seat, e.rng).action : eco.choose(e.g, seat, e.rng).action, seat);
            }
            e.steps++;
        }
    }

    step(actions) {
        if (actions.length !== this.envs.length) throw Error('Incorrect action count');
        for (let i = 0; i < this.envs.length; i++) {
            const e = this.envs[i], choice = actions[i];
            if (e.reported) {
                if (choice !== null) throw Error('Action after rollout completion');
                continue;
            }
            const seat = e.g.currentPlayers[0], legal = c.candidates(e.g, seat);
            if (!Number.isInteger(choice) || choice < 0 || choice >= legal.length)
                throw Error('Invalid rollout action');
            c.E.move(e.g, legal[choice], seat);
            e.steps++;
        }
        return this.reply();
    }

    reply() {
        const ended = [];
        const observations = this.envs.map((e, env) => {
            if (e.reported) return null;
            this.advance(e);
            if (c.E.ended(e.g) || e.steps >= e.maxSteps) {
                e.reported = true;
                const truncated = !c.E.ended(e.g);
                ended.push({ env, sample: e.sample, actionIndex: e.actionIndex, steps: e.steps,
                    truncated, value: truncated ? null : c.outcome(e.g)[e.player] });
                return null;
            }
            const result = this.encoder.encode(e.g, e.g.currentPlayers[0]);
            delete result.moves;
            return result;
        });
        return { observations, ended };
    }
}

module.exports = { ContinuationBatch };
if (require.main === module) {
    const batch = new ContinuationBatch();
    (async () => {
        for await (const line of require('node:readline').createInterface({ input: process.stdin })) {
            try {
                const q = JSON.parse(line);
                if (q.op === 'prepare') {
                    const observation = encoders.forRevision(q.featureRevision).encode(q.state, q.player);
                    delete observation.moves;
                    console.log(JSON.stringify({ observation, options: search.shortlist(q.state, q.player, 6, true) }));
                    continue;
                }
                if (!['reset', 'step'].includes(q.op)) throw Error('Unknown operation');
                console.log(JSON.stringify(q.op === 'reset' ? batch.reset(q) : batch.step(q.actions)));
            } catch (error) {
                console.error(error.stack);
                process.exit(1);
            }
        }
    })();
}
