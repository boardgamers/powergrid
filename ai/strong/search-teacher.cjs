// Generate public-belief search supervision; learning itself runs in HF Jobs.
const c = require('../core.cjs'),
    eco = require('./economics.cjs'),
    search = require('./search.cjs'),
    features = require('./features.cjs');
const id = Number(process.argv[2] || 0),
    seed = (process.env.DATA_VERSION || 'search-teacher-v1') + '-' + id,
    g = c.start(seed, id % 2 ? 'recharged' : 'original', id % 4 < 2),
    seat = Math.floor(id / 4) % 3,
    rng = c.seedrandom(seed + '-choices'),
    samples = Number(process.env.SEARCH_SAMPLES || 4),
    rows = [];
let steps = 0;
while (!c.E.ended(g) && steps < 1600) {
    const p = g.currentPlayers[0],
        legal = c.candidates(g, p),
        strategic = legal.length > 1 && legal.some((a) => ['ChoosePowerPlant', 'Bid', 'Build'].includes(a.name));
    let action;
    if (p === seat && strategic) {
        const result = search.choose(g, p, { samples, candidates: 5, seed: seed + '-decision-' + steps });
        action = result.action;
        if (result.evaluations && !result.truncated) {
            const x = features.encode(g, p);
            rows.push({
                state: x.state,
                actions: x.actions,
                target: result.index,
                searchValues: Object.entries(result.values).map(([index, total]) => [Number(index), total / samples]),
                teacherAgrees: result.index === x.teacher,
                phase: g.phase,
                round: g.round,
                seat,
            });
        }
    } else {
        const opponent = ['economic', 'heuristic', 'rush'][Math.floor(id / 12) % 3];
        action =
            p !== seat && opponent === 'heuristic'
                ? c.heuristic(g, p, rng).action
                : eco.choose(g, p, rng, p === seat ? 'economic' : opponent).action;
        if (p === seat && legal.length > 1 && process.env.INCLUDE_ALL_PHASES === '1') {
            const x = features.encode(g, p),
                target = x.moves.findIndex((a) => JSON.stringify(a) === JSON.stringify(action));
            if (target < 0) throw Error('Teacher selected an unrepresented action');
            rows.push({
                state: x.state,
                actions: x.actions,
                target,
                searchValues: [],
                teacherAgrees: true,
                phase: g.phase,
                round: g.round,
                seat,
            });
        }
    }
    c.E.move(g, action, p);
    steps++;
}
const truncated = !c.E.ended(g),
    value = truncated ? [0, 0, 0] : c.outcome(g),
    relativeValue = Array.from({ length: 3 }, (_, i) => value[(seat + i) % 3]);
console.log(
    JSON.stringify({
        id,
        seed,
        featureRevision: features.FEATURE_REVISION,
        steps,
        truncated,
        value,
        rows: rows.map((r) => ({ ...r, value: relativeValue })),
    })
);
