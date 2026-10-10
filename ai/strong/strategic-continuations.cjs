// Paired public-world continuations with a neural focal player and fixed opponents.
// This is a new worker; historical continuation/search workers remain unchanged.
const { ContinuationBatch } = require('./continuation-rollouts.cjs');
const c = require('../core.cjs');
const eco = require('./economics.cjs');
const search = require('./search.cjs');
const encoders = require('./encoders.cjs');
const MODES = ['neural', 'neural_economic', 'neural_search', 'mixed_control'];

class StrategicContinuations extends ContinuationBatch {
    reset(q) {
        if (!MODES.includes(q.mode)) throw Error('Invalid strategic continuation mode');
        if (q.featureRevision !== '4.2-discard-correction') throw Error('Unexpected feature revision');
        this.mode = q.mode;
        return super.reset({ ...q, continuation: q.mode === 'mixed_control' ? 'mixed' : 'neural' });
    }

    initialize(e) {
        if (e.roles) return;
        const opponent = this.mode === 'neural_search' ? 'search_geo' :
            this.mode === 'neural_economic' ? 'economic' : 'neural';
        e.roles = e.g.players.map((_, seat) => this.mode === 'mixed_control' ?
            (e.sample % 2 ? 'heuristic' : 'economic') : seat === e.player ? 'neural' : opponent);
        e.policyDecisions = { neural: 0, economic: 0, heuristic: 0, search_geo: 0, forced: 0 };
        e.searchStats = { decisions: 0, evaluations: 0, truncated: 0 };
    }

    advance(e) {
        this.initialize(e);
        if (this.mode === 'mixed_control') {
            while (!c.E.ended(e.g) && e.steps < e.maxSteps) {
                const seat = e.g.currentPlayers[0], role = e.roles[seat];
                const move = role === 'heuristic' ? c.heuristic(e.g, seat, e.rng).action :
                    eco.choose(e.g, seat, e.rng).action;
                c.E.move(e.g, move, seat);
                e.policyDecisions[role]++;
                e.steps++;
            }
            return;
        }
        while (!c.E.ended(e.g) && e.steps < e.maxSteps) {
            const seat = e.g.currentPlayers[0], role = e.roles[seat];
            const legal = c.candidates(e.g, seat);
            if (role === 'neural' && legal.length > 1) return;
            let move;
            if (role === 'neural') {
                move = legal[0];
                e.policyDecisions.forced++;
            } else if (role === 'search_geo' && legal.length > 1 &&
                legal.some(a => ['ChoosePowerPlant', 'Bid', 'Build'].includes(a.name))) {
                // Same opponent budget and phase routing as the independent arena reference.
                const result = search.choose(e.g, seat, { samples: 16, candidates: 6,
                    geography: true, maxSteps: 2400,
                    seed: 'arena-search-' + e.g.round + '-' + seat + '-' + Math.floor(e.rng() * 1e9) });
                move = result.action;
                e.searchStats.decisions++;
                e.searchStats.evaluations += result.evaluations || 0;
                e.searchStats.truncated += result.truncated || 0;
                e.policyDecisions.search_geo++;
            } else {
                move = eco.choose(e.g, seat, e.rng).action;
                e.policyDecisions.economic++;
            }
            c.E.move(e.g, move, seat);
            e.steps++;
        }
    }

    step(actions) {
        if (actions.length !== this.envs.length) throw Error('Incorrect action count');
        for (let i = 0; i < actions.length; i++) {
            const e = this.envs[i];
            if (!e.reported) {
                if (e.roles[e.g.currentPlayers[0]] !== 'neural') throw Error('Wrong neural actor');
                e.policyDecisions.neural++;
            }
        }
        return super.step(actions);
    }

    reply() {
        const result = super.reply();
        for (const row of result.ended) {
            const e = this.envs[row.env];
            row.roles = e.roles;
            row.searchStats = { ...e.searchStats };
            row.policyDecisions = { ...e.policyDecisions };
        }
        result.observations.forEach((o, i) => {
            if (!o) return;
            const e = this.envs[i];
            o.actor = e.g.currentPlayers[0];
            o.focalPlayer = e.player;
            o.roles = e.roles;
        });
        return result;
    }
}

module.exports = { StrategicContinuations, MODES };
if (require.main === module) {
    const batch = new StrategicContinuations();
    (async () => {
        for await (const line of require('node:readline').createInterface({ input: process.stdin })) {
            try {
                const q = JSON.parse(line);
                if (q.op === 'prepare') {
                    const observation = encoders.forRevision(q.featureRevision).encode(q.state, q.player);
                    const moves = observation.moves;
                    delete observation.moves;
                    console.log(JSON.stringify({ observation, moves,
                        options: search.shortlist(q.state, q.player, 6, true) }));
                } else {
                    if (!['reset', 'step'].includes(q.op)) throw Error('Unknown operation');
                    console.log(JSON.stringify(q.op === 'reset' ? batch.reset(q) : batch.step(q.actions)));
                }
            } catch (error) {
                console.error(error.stack);
                process.exit(1);
            }
        }
    })();
}
