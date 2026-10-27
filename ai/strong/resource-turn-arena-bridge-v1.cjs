// Separate research arena: atomic legacy path plus explicitly enabled whole-resource turns.
// Derived from public-arena-bridge.cjs SHA256 4caf83b22e3e20c3d838c082a26f9e96d277a8f3c7cc067871350223c081a8ad.
// Caller verifies the supplied runtime manifest. No model or policy selection here.
const path = require('node:path');
const assert = require('node:assert/strict');
const {checkIdentity,createResourceTurnExchange} = require('./resource-turn-exchange-v1.cjs');
function createResourceTurnArena(runtimeDirectory) {
const runtime = path.resolve(runtimeDirectory);
const engineRequire = name => require(path.resolve(runtime,'ai/strong',name));
const exchange = createResourceTurnExchange(runtime);
const c = engineRequire('../core.cjs'),
    eco = engineRequire('./economics.cjs'),
    encoders = engineRequire('./encoders.cjs');
const { POPULATION_MODES, FROZEN_ROLES, isNeuralRole, populationRoles } = engineRequire('./opponent-population.cjs');
const { isDeepStrictEqual } = require('node:util');
let envs = [],
    sequence = 0;
const seed = process.env.SEED || 'strong-train';
function searchMove(e, seat, options) {
    const result = engineRequire('./search.cjs').choose(e.g, seat, options);
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
    } else if (role === 'economic_capacity_v1') {
        c.E.move(e.g, engineRequire('./economics-v4_1.cjs').choose(e.g, p, e.rng).action, p);
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
        !isNeuralRole(e.roles[e.g.currentPlayers[0]])
    )
        applyBot(e, e.g.currentPlayers[0]);
}
function requestFor(e,seat) {
    const request = {state:engineRequire('./sealed-policy-beliefs.cjs').publicState(e.g,seat),player:seat};
    if (e.publicResourceTurns) Object.assign(request,{requestId:e.id+':'+e.steps,revision:e.steps});
    return request;
}
function observation(e) {
    if (c.E.ended(e.g) || e.steps >= 1600) return null;
    const seat = e.g.currentPlayers[0],
        x = encoders.forRevision(e.featureRevisions[e.roles[seat]]).encode(e.g, seat);
    if (!e.publicMoves) delete x.moves;
    x.request = requestFor(e,seat);
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
            'economic_capacity_v1',
            'heuristic',
            'rush',
            'legacy',
            'selfplay',
            'snapshot0',
            'snapshot1',
            'snapshot2',
            'search',
            'search_geo',
            ...POPULATION_MODES,
        ].includes(mode)
    )
        throw Error('Unknown opponent mode: ' + mode);
    if (POPULATION_MODES.includes(mode) && FROZEN_ROLES.some(role => featureRevisions[role] !== '4.0-multiplayer'))
        throw Error('Population modes require all frozen schema-4 policies');
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
    const roles = POPULATION_MODES.includes(mode)
        ? populationRoles(mode, playerCount, seat, seed, id)
        : opponent === 'selfplay'
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
function handle(q) {
            const ended = [];
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
                    const e = reset(
                        q.mode,
                        q.arenaSeed,
                        index,
                        q.featureRevisions,
                        count,
                        counts ? index : undefined,
                        seat
                    );
                    e.publicMoves = q.publicMoves === true;
                    e.publicResourceTurns = q.publicResourceTurns === true;
                    if (e.publicResourceTurns) {
                        assert(e.publicMoves,'Whole resource turns require explicit public moves');
                        checkIdentity(q.policyIdentity);
                        e.policyIdentity = structuredClone(q.policyIdentity);
                    }
                    return e;
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
                    if (choice && typeof choice === 'object' && Object.hasOwn(choice,'publicResourceTurn')) {
                        assert(e.publicResourceTurns && e.roles[seat]==='learner',
                            'Resource responses require the explicit learner-turn arena');
                        assert.deepEqual(Object.keys(choice),['publicResourceTurn']);
                        assert.equal(e.g.phase,c.E.Phase.Resources);
                        const response = choice.publicResourceTurn;
                        const applied = exchange.execute(e.g,requestFor(e,seat),response,e.policyIdentity);
                        assert(e.steps+applied.atomicMoves <= 1600,
                            'A complete turn may not hide an atomic arena cap');
                        e.g = applied.state;
                        for (const move of response.transaction.actions)
                            e.policyMoves[move.name] = (e.policyMoves[move.name] || 0)+1;
                        e.steps += applied.atomicMoves;
                        // No opponent may act between purchases. Advance only after final Pass.
                        advance(e);
                    } else {
                    if (choice && typeof choice === 'object' && Object.hasOwn(choice, 'publicMove')) {
                        if (!e.publicMoves || Object.keys(choice).length !== 1)
                            throw Error('Public moves require the explicit public-move arena');
                        const matches = legal.filter((move) => isDeepStrictEqual(move, choice.publicMove));
                        if (matches.length !== 1) throw Error('Returned public move is not uniquely legal');
                    }
                    const index = typeof choice === 'object' ? choice.proposal : choice;
                    const action =
                        choice && typeof choice === 'object' && Object.hasOwn(choice, 'publicMove')
                            ? choice.publicMove
                        : typeof choice === 'object' && strategic
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
                    }
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
            return {observations:envs.map(observation),ended};
}
return {handle};
}
module.exports = {createResourceTurnArena};
if (require.main === module) {
    assert(process.argv[2],'Supply a previously verified engine runtime directory');
    const arena = createResourceTurnArena(process.argv[2]);
    (async () => {
        for await (const line of require('node:readline').createInterface({input:process.stdin})) {
            try {console.log(JSON.stringify(arena.handle(JSON.parse(line))));}
            catch (error) {console.error(error.stack);process.exitCode=1;break;}
        }
    })();
}
