// Public-belief rollout search. The live draw pile and sealed bids are never replayed.
const c = require('../core.cjs'),
    eco = require('./economics.cjs');
const { createAnalysisScenario } = require('../../engine/dist/src/analysis.js');
const DEFAULT_MAX_STEPS = 2400;
function shortlist(g, seat, limit = 5, geography = false) {
    const a = c.candidates(g, seat),
        v = eco.scores(g, seat, a),
        indices = [...a.keys()].sort((i, j) => v[j] - v[i]);
    if (geography && a.some((x) => x.name === 'Build')) {
        const ranked = require('./geographic-proposals.cjs').rank(g, seat, a),
            chosen = new Set([indices[0]]),
            add = (index) => {
                if (index >= 0 && chosen.size < limit) chosen.add(index);
            };
        add(a.findIndex((x) => x.name === 'Pass'));
        add(c.heuristic(g, seat).index);
        // Cover different islands/regions before filling equal-price ties.
        for (const key of ['island', 'region']) {
            const seen = new Set();
            for (const x of ranked)
                if (!seen.has(x[key])) {
                    add(x.index);
                    seen.add(x[key]);
                }
        }
        for (const x of ranked) add(x.index);
        for (const i of indices) add(i);
        return [...chosen];
    }
    const chosen = new Set(indices.slice(0, Math.max(1, limit - 2)));
    const pass = a.findIndex((x) => x.name === 'Pass');
    if (pass >= 0) chosen.add(pass);
    chosen.add(c.heuristic(g, seat).index);
    // A sampled middle bid helps find strategic bids not selected by the greedy prior.
    const bids = indices.filter((i) => a[i].name === 'Bid');
    if (bids.length > 4) chosen.add(bids[Math.floor(bids.length / 2)]);
    return [...chosen].slice(0, limit);
}
function choose(
    g,
    seat,
    {
        samples = 6,
        candidates = 5,
        seed = 'public-search',
        maxSteps = DEFAULT_MAX_STEPS,
        extraCandidates = [],
        geography = false,
        includeSamples = false,
        continuation = 'mixed',
    } = {}
) {
    if (!['mixed', 'heuristic', 'economic'].includes(continuation)) throw Error('Invalid continuation policy');
    const actions = c.candidates(g, seat),
        options = [...new Set([...shortlist(g, seat, candidates, geography), ...extraCandidates])];
    if (options.some((i) => !Number.isInteger(i) || i < 0 || i >= actions.length))
        throw Error('Invalid search proposal');
    if (options.length === 1) return { index: options[0], action: actions[options[0]], evaluations: 0 };
    const totals = Object.fromEntries(options.map((i) => [i, 0]));
    const sampleOutcomes = includeSamples ? Object.fromEntries(options.map((i) => [i, []])) : null;
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
                const useHeuristic = continuation === 'heuristic' || (continuation === 'mixed' && sample % 2);
                const move = useHeuristic ? c.heuristic(sim, p, rng).action : eco.choose(sim, p, rng).action;
                c.E.move(sim, move, p);
            }
            if (c.E.ended(sim)) {
                const value = c.outcome(sim)[seat];
                totals[index] += value;
                if (sampleOutcomes) sampleOutcomes[index].push(value);
            } else {
                truncated++;
                if (sampleOutcomes) sampleOutcomes[index].push(null);
            }
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
        ...(sampleOutcomes ? { sampleOutcomes } : {}),
    };
}
module.exports = { choose, shortlist, DEFAULT_MAX_STEPS };
