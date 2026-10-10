// Schema 4: fixed-size public observations for 2–6 players. Schema 3 stays frozen.
const c = require('../core.cjs'),
    eco = require('./economics.cjs'),
    spatial = require('./spatial.cjs');
const FEATURE_REVISION = '4.0-multiplayer',
    MAX_PLAYERS = 6;
const pad = (xs, n) => [...xs, ...Array(Math.max(0, n - xs.length)).fill(0)];
const plant = (p) =>
    p
        ? [p.number / 50, p.cost / 4, p.citiesPowered / 8, ...Array.from({ length: 7 }, (_, i) => +(p.type === i))]
        : Array(10).fill(0);
function assertScope(g, seat) {
    if (
        g.map.name !== 'Germany' ||
        g.players.length < 2 ||
        g.players.length > 6 ||
        g.options.randomizeMap ||
        g.options.chooseRegions ||
        g.options.chooseColors ||
        g.map.cities.some((x) => !c.CITIES.includes(x.name))
    )
        throw Error('Schema 4 supports automatic Germany games with 2–6 players');
    if (!Number.isInteger(seat) || seat < 0 || seat >= g.players.length) throw Error('Invalid observing seat');
}
function observe(g, seat, geometry = spatial.territories(g, seat)) {
    assertScope(g, seat);
    const n = g.players.length,
        order = Array.from({ length: n }, (_, i) => (seat + i) % n);
    const playerMask = pad(
        order.map(() => 1),
        MAX_PLAYERS
    );
    const global = [
        ...Object.values(c.E.Phase).map((x) => +(x === g.phase)),
        g.round / 20,
        g.step / 3,
        +(g.options.variant === 'recharged'),
        +g.options.fastBid,
        n / 6,
        g.cardsLeft / 50,
        +g.nextCardWeak,
        (g.options.fastBid ? 0 : g.currentBid || 0) / 100,
        (g.minimunBid || 0) / 100,
        g.citiesToEndGame / 25,
        g.citiesToStep2 / 20,
        +!!g.card39Bought,
        g.currentPlayers.length / n,
    ];
    for (const r of c.RES)
        global.push(
            g[r + 'Market'] / 24,
            g[r + 'Supply'] / 24,
            ...pad(
                g[r + 'Prices'].map((x) => x / 20),
                24
            ),
            ...[1, 2, 3].map((step) => eco.replenishment(g, r, step) / 12),
            c.resourcePrice(g, r) / 20,
            Math.min(g[r + 'Supply'], eco.replenishment(g, r), g[r + 'Prices'].length - g[r + 'Market']) / 24
        );
    global.push(
        ...pad(
            g.paymentTable.slice(0, 23).map((x) => x / 200),
            23
        )
    );
    for (let i = 0; i < 4; i++) global.push(...plant(g.actualMarket[i]), ...plant(g.futureMarket[i]));
    global.push(...plant(g.chosenPowerPlant));
    const players = order.map((id) => {
        const p = g.players[id],
            rank = g.playerOrder.indexOf(id),
            demand = eco.demand(g, p),
            fuel = eco.plan(g, p, 22, { buy: false });
        const row = [
            p.money / 500,
            p.cities.length / 22,
            p.housesLeft / 22,
            p.citiesPowered / 22,
            rank / (n - 1),
            (n - 1 - rank) / (n - 1),
            +p.skipAuction,
            +p.passed,
            +g.currentPlayers.includes(id),
            +(g.auctioningPlayer === id),
            (g.options.fastBid ? 0 : p.bid || 0) / 100,
            p.hybridCapacity / 24,
            c.capacity(p) / 22,
            fuel.power / 22,
        ];
        for (const [j, r] of c.RES.entries())
            row.push(
                p[r + 'Left'] / 24,
                p[r + 'Capacity'] / 24,
                demand[j] / 12,
                Math.max(0, demand[j] - p[r + 'Left']) / 12
            );
        for (let i = 0; i < 4; i++)
            row.push(
                ...plant(p.powerPlants[i]),
                +!!p.powerPlants[i] && +p.powerPlantsNotUsed.includes(p.powerPlants[i].number)
            );
        return row;
    });
    const playerWidth = players[0].length;
    while (players.length < MAX_PLAYERS) players.push(Array(playerWidth).fill(0));
    const cities = c.CITIES.flatMap((name) => [
        +g.map.cities.some((x) => x.name === name),
        ...pad(
            order.map((id) => +g.players[id].cities.some((x) => x.name === name)),
            MAX_PLAYERS
        ),
    ]);
    const territory = [];
    for (const [groups, limit] of [
        [geometry.regions, 8],
        [geometry.islands, 4],
    ])
        for (let i = 0; i < limit; i++) {
            const x = groups[i];
            territory.push(
                ...(x
                    ? [
                          1,
                          x.size / 64,
                          x.empty / 64,
                          x.open / 64,
                          x.totalFree / 128,
                          ...pad(
                              x.owned.map((v) => v / 22),
                              MAX_PLAYERS
                          ),
                      ]
                    : Array(11).fill(0))
            );
        }
    territory.push((g.map.crossIslandSurcharge || 0) / 100);
    const state = [...playerMask, ...global, ...players.flat(), ...cities, ...territory];
    if (!state.every(Number.isFinite)) throw Error('Nonfinite schema 4 observation');
    return {
        state,
        playerMask,
        playerOrder: order,
        layout: { global: global.length, player: playerWidth, cities: cities.length, territory: territory.length },
    };
}
function encode(g, seat, movesOverride) {
    const geometry = spatial.territories(g, seat),
        observation = observe(g, seat, geometry);
    const moves = movesOverride || c.candidates(g, seat),
        raw = eco.scores(g, seat, moves),
        best = Math.max(...raw);
    const actions = moves.map((a, i) => {
        const geo = spatial.actionFeatures(g, seat, a, geometry),
            n = g.players.length;
        return [
            ...c.actionFeatures(g, seat, a),
            Math.max(-10, Math.min(10, raw[i] / 10)),
            +(raw[i] === best),
            ...pad(geo.slice(0, n), 6),
            ...pad(geo.slice(n, 2 * n), 6),
            ...pad(geo.slice(2 * n, 3 * n), 6),
            ...geo.slice(3 * n),
        ];
    });
    return {
        featureRevision: FEATURE_REVISION,
        ...observation,
        actions,
        moves,
        prior: raw.map((x) => Math.max(-10, Math.min(10, x / 10))),
        teacher: raw.indexOf(best),
        seat,
    };
}
module.exports = { SCHEMA: 4, FEATURE_REVISION, MAX_PLAYERS, observe, encode };
