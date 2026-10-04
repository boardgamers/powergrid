const c = require('../core.cjs'),
    eco = require('./economics.cjs'),
    encoders = require('./encoders.cjs'),
    readline = require('node:readline');
let envs = [],
    sequence = 0;
const seed = process.env.SEED || 'strong-train';
function searchMove(e, seat, options) {
    const result = require('./search.cjs').choose(e.g, seat, options);
    const role = e.roles[seat];
    const stats = (e.searchStats[role] ||= { decisions: 0, evaluations: 0, truncated: 0 });
    stats.decisions++;
    stats.evaluations += result.evaluations || 0;
    stats.truncated += result.truncated || 0;
    return result.action;
}
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
    } else if (role === 'search' || role === 'search_geo') {
        const legal = c.candidates(e.g, p),
            strategic = legal.length > 1 && legal.some((a) => ['ChoosePowerPlant', 'Bid', 'Build'].includes(a.name));
        c.E.move(
            e.g,
            strategic
                ? searchMove(e, p, {
                      samples: role === 'search_geo' ? 16 : 4,
                      candidates: role === 'search_geo' ? 6 : 5,
                      geography: role === 'search_geo',
                      seed: 'arena-search-' + e.g.round + '-' + p + '-' + Math.floor(e.rng() * 1e9),
                  })
                : eco.choose(e.g, p, e.rng).action,
            p
        );
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
        x = encoders.forRevision(e.featureRevisions[e.roles[seat]]).encode(e.g, seat);
    delete x.moves;
    return {
        ...x,
        episode: e.id,
        roles: e.roles,
        round: e.g.round,
        variant: e.g.options.variant,
        sealed: !!e.g.options.fastBid,
        playerCount: e.g.players.length,
    };
}
function reset(mode = 'mixed', arenaSeed, arenaId, featureRevisions = {}, playerCount = 3, trainingIndex, learnerSeat) {
    if (!Number.isInteger(playerCount) || playerCount < 2 || playerCount > 6) throw Error('Invalid player count');
    if (
        ![
            'mixed',
            'mixed_search',
            'mixed_search_geo',
            'economic',
            'heuristic',
            'rush',
            'legacy',
            'selfplay',
            'snapshot0',
            'snapshot1',
            'snapshot2',
            'search',
            'search_geo',
        ].includes(mode)
    )
        throw Error('Unknown opponent mode: ' + mode);
    const id = arenaSeed === undefined ? trainingIndex ?? sequence++ : arenaId,
        seat = learnerSeat ?? Math.floor(id / 4) % playerCount,
        kind = Math.floor(c.seedrandom(seed + '-opponents-' + id)() * 8);
    const opponent =
        mode === 'mixed' || mode === 'mixed_search' || mode === 'mixed_search_geo'
            ? [
                  'economic',
                  'heuristic',
                  'rush',
                  mode === 'mixed_search_geo' ? 'search_geo' : mode === 'mixed_search' ? 'search' : 'legacy',
                  'selfplay',
                  'snapshot0',
                  'snapshot1',
                  'snapshot2',
              ][kind]
            : mode;
    const roles =
        opponent === 'selfplay'
            ? Array(playerCount).fill('learner')
            : Array.from({ length: playerCount }, (_, i) => (i === seat ? 'learner' : opponent));
    const gameSeed = arenaSeed === undefined ? seed + '-' + id : arenaSeed + '-' + Math.floor(id / (4 * playerCount));
    const e = {
        id,
        gameSeed,
        g: c.E.setup(
            playerCount,
            { map: 'Germany', variant: id % 2 ? 'recharged' : 'original', fastBid: id % 4 < 2, showMoney: true },
            gameSeed
        ),
        roles,
        rng: c.seedrandom(arenaSeed === undefined ? seed + '-bot-' + id : gameSeed + '-bot'),
        steps: 0,
        policyMoves: {},
        searchStats: {},
        featureRevisions,
    };
    advance(e);
    return e;
}
(async () => {
    for await (const line of readline.createInterface({ input: process.stdin })) {
        try {
            const q = JSON.parse(line),
                ended = [];
            if (q.op === 'reset') {
                const counts = q.playerCounts;
                if (
                    counts &&
                    (q.arenaSeed !== undefined ||
                        !Array.isArray(counts) ||
                        !counts.length ||
                        new Set(counts).size !== counts.length ||
                        counts.some((n) => !Number.isInteger(n) || n < 2 || n > 6))
                )
                    throw Error('Mixed player counts require a valid training-only schedule');
                envs = Array.from({ length: q.n }, (_, i) => {
                    const index = (q.offset || 0) + i;
                    const count = counts ? counts[Math.floor(index / 4) % counts.length] : q.playerCount ?? 3;
                    const seat = counts ? Math.floor(index / (4 * counts.length)) % count : undefined;
                    return reset(
                        q.mode,
                        q.arenaSeed,
                        index,
                        q.featureRevisions,
                        count,
                        counts ? index : undefined,
                        seat
                    );
                });
            } else if (q.op === 'step')
                for (let i = 0; i < envs.length; i++) {
                    const e = envs[i];
                    if (q.actions[i] === null) continue;
                    const seat = e.g.currentPlayers[0];
                    const legal = c.candidates(e.g, seat),
                        choice = q.actions[i];
                    const strategic =
                        legal.length > 1 && legal.some((a) => ['ChoosePowerPlant', 'Bid', 'Build'].includes(a.name));
                    const index = typeof choice === 'object' ? choice.proposal : choice;
                    const action =
                        typeof choice === 'object' && strategic
                            ? searchMove(e, seat, {
                                  samples: choice.searchSamples,
                                  candidates: 6,
                                  extraCandidates: choice.disableSearchProposal ? [] : [index],
                                  geography: !!choice.geography,
                                  seed: 'arena-guided-' + e.id + '-' + e.steps,
                              })
                            : legal[index];
                    c.E.move(e.g, action, seat);
                    if (e.roles[seat] === 'learner') e.policyMoves[action.name] = (e.policyMoves[action.name] || 0) + 1;
                    e.steps++;
                    advance(e);
                    if (c.E.ended(e.g) || e.steps >= 1600)
                        ended.push({
                            env: i,
                            episode: e.id,
                            gameSeed: e.gameSeed,
                            truncated: !c.E.ended(e.g),
                            value: c.E.ended(e.g) ? c.outcome(e.g) : Array(e.g.players.length).fill(0),
                            playerCount: e.g.players.length,
                            variant: e.g.options.variant,
                            sealed: !!e.g.options.fastBid,
                            steps: e.steps,
                            roles: e.roles,
                            policyMoves: e.policyMoves,
                            searchStats: e.searchStats,
                            final: {
                                round: e.g.round,
                                players: e.g.players.map((p) => ({
                                    cities: p.cities.length,
                                    powered: p.citiesPowered,
                                    money: p.money,
                                    capacity: c.capacity(p),
                                    plants: p.powerPlants.map((pp) => pp.number),
                                })),
                            },
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
