// Public-belief rollout search. The live draw pile and sealed bids are never replayed.
const c = require('../core.cjs'),
    eco = require('./economics.cjs');
const { createAnalysisScenario } = require('../../engine/dist/src/analysis.js');
function shortlist(g, seat, limit = 5) {
    const a = c.candidates(g, seat),
        v = eco.scores(g, seat, a),
        indices = [...a.keys()].sort((i, j) => v[j] - v[i]);
    const chosen = new Set(indices.slice(0, Math.max(1, limit - 2)));
    const pass = a.findIndex((x) => x.name === 'Pass');
    if (pass >= 0) chosen.add(pass);
    chosen.add(c.heuristic(g, seat).index);
    // A sampled middle bid helps find strategic bids not selected by the greedy prior.
    const bids = indices.filter((i) => a[i].name === 'Bid');
    if (bids.length > 4) chosen.add(bids[Math.floor(bids.length / 2)]);
    return [...chosen].slice(0, limit);
}
function choose(g, seat, { samples = 6, candidates = 5, seed = 'public-search', maxSteps = 1200 } = {}) {
    const actions = c.candidates(g, seat),
        options = shortlist(g, seat, candidates);
    if (options.length === 1) return { index: options[0], action: actions[options[0]], evaluations: 0 };
    const totals = Object.fromEntries(options.map((i) => [i, 0]));
    let evaluations = 0,
        truncated = 0;
    for (let sample = 0; sample < samples; sample++) {
        const scenario = createAnalysisScenario(g, { player: seat, seed: seed + '-' + sample });
        for (const index of options) {
            const sim = structuredClone(scenario),
                rng = c.seedrandom(seed + '-rollout-' + sample);
            c.E.move(sim, structuredClone(actions[index]), seat);
            let step = 0;
            while (!c.E.ended(sim) && step++ < maxSteps) {
                const p = sim.currentPlayers[0];
                const move = sample % 2 ? c.heuristic(sim, p, rng).action : eco.choose(sim, p, rng).action;
                c.E.move(sim, move, p);
            }
            if (c.E.ended(sim)) totals[index] += c.outcome(sim)[seat];
            else truncated++;
            evaluations++;
        }
    }
    const prior = eco.scores(g, seat, actions);
    const index = options.sort((a, b) => totals[b] - totals[a] || prior[b] - prior[a])[0];
    return {
        index,
        action: actions[index],
        evaluations,
        truncated,
        winEstimate: totals[index] / samples,
        values: totals,
    };
}
module.exports = { choose, shortlist };
