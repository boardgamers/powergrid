// Generate public-belief search supervision; learning itself runs in HF Jobs.
const c = require('../core.cjs'),
    eco = require('./economics.cjs'),
    search = require('./search.cjs'),
    features = require(process.env.FEATURE_REVISION === '4.0-multiplayer' ? './features-v4.cjs' : './features.cjs');
const playerCount = Number(process.env.PLAYER_COUNT || 3);
if (!Number.isInteger(playerCount) || playerCount < 2 || playerCount > 6) throw Error('Invalid teacher player count');
if (playerCount !== 3 && features.SCHEMA !== 4) throw Error('Multiplayer games require schema 4');
const id = Number(process.argv[2] || 0),
    seed =
        (process.env.DATA_VERSION || 'search-teacher-v1') +
        (features.SCHEMA === 4 ? '-' + playerCount + 'p' : '') +
        '-' +
        id,
    g = c.E.setup(
        playerCount,
        { map: 'Germany', variant: id % 2 ? 'recharged' : 'original', fastBid: id % 4 < 2, showMoney: true },
        seed
    ),
    seat = Math.floor(id / 4) % playerCount,
    rng = c.seedrandom(seed + '-choices'),
    samples = Number(process.env.SEARCH_SAMPLES || 4),
    rows = [];
let steps = 0;
const searchStats = { decisions: 0, evaluations: 0, truncated: 0 };
while (!c.E.ended(g) && steps < 1600) {
    const p = g.currentPlayers[0],
        legal = c.candidates(g, p),
        strategic = legal.length > 1 && legal.some((a) => ['ChoosePowerPlant', 'Bid', 'Build'].includes(a.name));
    let action;
    if (p === seat && strategic) {
        const result = search.choose(g, p, {
            samples,
            candidates: process.env.GEOGRAPHY === '1' ? 6 : 5,
            geography: process.env.GEOGRAPHY === '1',
            seed: seed + '-decision-' + steps,
        });
        action = result.action;
        searchStats.decisions++;
        searchStats.evaluations += result.evaluations || 0;
        searchStats.truncated += result.truncated || 0;
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
        const opponent = ['economic', 'heuristic', 'rush'][Math.floor(id / (4 * playerCount)) % 3];
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
    value = truncated ? Array(playerCount).fill(0) : c.outcome(g),
    relativeValue = Array.from({ length: features.SCHEMA === 4 ? 6 : 3 }, (_, i) =>
        i < playerCount ? value[(seat + i) % playerCount] : 0
    );
console.log(
    JSON.stringify({
        id,
        seed,
        featureRevision: features.FEATURE_REVISION,
        playerCount,
        variant: g.options.variant,
        sealed: !!g.options.fastBid,
        searchStats,
        steps,
        truncated,
        value,
        rows: rows.map((r) => ({ ...r, value: relativeValue })),
    })
);
