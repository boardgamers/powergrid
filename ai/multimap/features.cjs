// Schema v1: public tensors only; no city IDs, map-name one-hots or teacher scores.
const E = require('../../engine/dist/index.js');
const { minimumPlantBid } = require('../../engine/dist/src/auction-pricing.js');
const protocol = require('./protocol.json');
const RES = ['coal', 'oil', 'garbage', 'uranium'];
const TYPES = [
    'ChoosePowerPlant',
    'Bid',
    'DiscardPowerPlant',
    'DiscardResources',
    'BuyResource',
    'Build',
    'UsePowerPlant',
    'Pass',
];
const MAPS = [...protocol.trainMaps, ...protocol.transferMaps];
const pad = (a, n) => {
    if (a.length > n) throw Error(`Overflow ${a.length} > ${n}`);
    return [...a, ...Array(n - a.length).fill(0)];
};
const plant = (p) =>
    p
        ? [1, p.number / 100, p.cost / 4, p.citiesPowered / 10, ...Array.from({ length: 7 }, (_, i) => +(p.type === i))]
        : Array(11).fill(0);
const capacity = (p) => p.powerPlants.reduce((n, x) => n + x.citiesPowered, 0);
function assertScope(g, seat) {
    if (
        !MAPS.includes(g.map.name) ||
        !g.options.showMoney ||
        g.options.randomizeMap ||
        g.options.chooseRegions ||
        g.options.chooseColors ||
        g.options.alternatePowerPlants ||
        g.players.length < 2 ||
        g.players.length > 6
    )
        throw Error('Unsupported multi-map v1 scope');
    if (!Number.isInteger(seat) || !g.currentPlayers.includes(seat)) throw Error('Not an active seat');
}
function legal(g, seat) {
    assertScope(g, seat);
    const moves = Object.entries(g.players[seat].availableMoves || {}).flatMap(([name, items]) =>
        (items || []).map((data) => ({ name, data }))
    );
    if (!moves.length || moves.some((a) => !TYPES.includes(a.name))) throw Error('Empty or unknown legal action');
    return moves;
}
function refill(g, r, step) {
    if (
        r === 'uranium' &&
        g.options.variant === 'recharged' &&
        ['Germany', 'Italy'].includes(g.map.name) &&
        g.card39Bought
    )
        return 0;
    return g[r + 'Resupply'][g.players.length - 2][step - 1];
}
function resourcePrice(g, resource) {
    const count = g[resource + 'Market'],
        prices = g[resource + 'Prices'];
    if (count > 0) return prices[prices.length - count];
    if (resource === 'coal' && g.map.name === 'USA' && g.options.variant === 'recharged' && g.coalSupply > 0) return 8;
    throw Error('No resource available');
}
function encode(g, seat, moves = legal(g, seat)) {
    assertScope(g, seat);
    const n = g.players.length,
        order = [seat, ...g.playerOrder.filter((id) => id !== seat)],
        p = g.players[seat];
    const global = [
        ...Object.values(E.Phase).map((x) => +(g.phase === x)),
        g.round / 30,
        g.step / 3,
        n / 6,
        +(g.options.variant === 'recharged'),
        +!!g.options.fastBid,
        g.cardsLeft / 60,
        +!!g.nextCardWeak,
        (g.options.fastBid ? 0 : g.currentBid || 0) / 500,
        (g.minimunBid || 0) / 100,
        g.citiesToEndGame / 25,
        g.citiesToStep2 / 20,
        +!!g.card39Bought,
        +!!g.plantDiscountActive,
        +!!g.options.endPlantDiscountAtStep3,
        (g.map.crossIslandSurcharge || 0) / 100,
        (n === 2 ? 4 : 3) / 5,
        g.map.cities.length / 64,
        // Rule semantics, not map identities. New special-rule maps require a new scope audit.
        +(g.options.variant === 'recharged' && g.map.name === 'USA'),
        +(['Germany', 'Italy'].includes(g.map.name) && g.options.variant === 'recharged'),
        +(g.map.name === 'Benelux'),
    ];
    for (const r of RES)
        global.push(
            g[r + 'Market'] / 24,
            g[r + 'Supply'] / 24,
            ...pad(
                g[r + 'Prices'].map((v) => v / 20),
                24
            ),
            ...[1, 2, 3].map((s) => refill(g, r, s) / 12)
        );
    global.push(
        ...pad(
            g.paymentTable.map((v) => v / 200),
            30
        )
    );
    for (let i = 0; i < 4; i++) global.push(...plant(g.actualMarket[i]), ...plant(g.futureMarket[i]));
    global.push(...plant(g.chosenPowerPlant));
    const players = order.map((id) => {
        const q = g.players[id];
        return [
            q.money / 500,
            q.cities.length / 25,
            q.housesLeft / 25,
            q.citiesPowered / 25,
            g.playerOrder.indexOf(id) / 5,
            +g.currentPlayers.includes(id),
            +(g.auctioningPlayer === id),
            +!!q.skipAuction,
            +!!q.passed,
            capacity(q) / 25,
            q.hybridCapacity / 24,
            (g.options.fastBid ? 0 : q.bid || 0) / 500,
            ...RES.flatMap((r) => [q[r + 'Left'] / 24, q[r + 'Capacity'] / 24]),
            ...Array.from({ length: 5 }, (_, i) => [
                ...plant(q.powerPlants[i]),
                +(!!q.powerPlants[i] && q.powerPlantsNotUsed.includes(q.powerPlants[i].number)),
            ]).flat(),
        ];
    });
    const cityIndex = new Map(g.map.cities.map((x, i) => [x.name, i]));
    const build = new Map();
    for (const a of moves)
        if (a.name === 'Build') build.set(a.data.name, Math.min(build.get(a.data.name) ?? Infinity, a.data.price));
    const owns = order.map((id) => new Set(g.players[id].cities.map((c) => c.name)));
    const nodes = g.map.cities.map((city) => {
        const owners = pad(
                owns.map((s) => +s.has(city.name)),
                6
            ),
            occupied = owners.reduce((a, b) => a + b, 0);
        const blocked = !!g.blockedCities?.includes(city.name),
            unavailable = blocked || (city.transregional && g.step < 2);
        const slots = city.singleOccupancy ? 1 : city.stepSlots?.[g.step - 1] ?? g.step;
        const cap = city.singleOccupancy ? 1 : city.slotCosts?.length ?? 3;
        const region = g.map.cities.filter((x) => x.region === city.region),
            island = g.map.cities.filter((x) => x.island === city.island);
        return [
            ...owners,
            occupied / 3,
            unavailable ? 0 : Math.max(0, Math.min(cap, slots) - occupied) / 3,
            blocked ? 0 : Math.max(0, cap - occupied) / 3,
            +blocked,
            +!!city.transregional,
            +!!g.map.noUraniumRegions?.includes(city.region),
            +!!g.map.startingCities?.includes(city.name),
            ...pad(city.slotCosts || [10, 15, 20], 3).map((x) => x / 40),
            ...(city.stepSlots || [1, 2, 3]).map((x) => x / 3),
            (city.connectionCost || 0) / 40,
            +build.has(city.name),
            (build.get(city.name) || 0) / 100,
            region.length / 64,
            island.length / 64,
            ...pad(
                order.map(
                    (id) => g.players[id].cities.filter((x) => region.some((y) => y.name === x.name)).length / 25
                ),
                6
            ),
            ...pad(
                order.map(
                    (id) => g.players[id].cities.filter((x) => island.some((y) => y.name === x.name)).length / 25
                ),
                6
            ),
        ];
    });
    // Four relations: weighted links, unweighted links, same region, same island.
    // No scalar region/island IDs are learned. Matrices permute with city order.
    const size = nodes.length,
        relations = Array.from({ length: 4 }, () => Array.from({ length: size }, () => Array(size).fill(0)));
    for (const e of g.map.connections) {
        const a = cityIndex.get(e.nodes[0]),
            b = cityIndex.get(e.nodes[1]);
        if (a === undefined || b === undefined) continue;
        relations[0][a][b] = relations[0][b][a] = 1 / (1 + e.cost / 10);
        relations[1][a][b] = relations[1][b][a] = 1;
    }
    for (let i = 0; i < size; i++)
        for (let j = 0; j < size; j++) {
            relations[2][i][j] = +(g.map.cities[i].region === g.map.cities[j].region);
            relations[3][i][j] = +(g.map.cities[i].island === g.map.cities[j].island);
        }
    // Normalize by a fixed degree scale, not row-normalize: retain degree/cost magnitudes.
    for (let k = 0; k < 4; k++)
        for (let i = 0; i < size; i++) for (let j = 0; j < size; j++) relations[k][i][j] /= k < 2 ? 8 : 64;
    const actionCity = [],
        actions = moves.map((a) => {
            const d = a.data;
            const pp =
                a.name === 'ChoosePowerPlant'
                    ? g.actualMarket.find((x) => x.number === d)
                    : a.name === 'DiscardPowerPlant'
                    ? p.powerPlants.find((x) => x.number === d)
                    : a.name === 'UsePowerPlant'
                    ? p.powerPlants.find((x) => x.number === d.powerPlant)
                    : g.chosenPowerPlant;
            const cost =
                a.name === 'Bid'
                    ? d
                    : a.name === 'ChoosePowerPlant'
                    ? minimumPlantBid(g, pp)
                    : a.name === 'BuyResource'
                    ? resourcePrice(g, d.resource)
                    : d?.price || 0;
            actionCity.push(a.name === 'Build' ? cityIndex.get(d.name) : -1);
            return [
                ...TYPES.map((t) => +(a.name === t)),
                cost / 500,
                cost / Math.max(1, p.money),
                ...RES.map((r) => +(r === (d?.resource || d))),
                ...plant(pp),
                (d?.citiesPowered || 0) / 25,
                ...RES.map((r) => (d?.resourcesSpent || []).filter((x) => x === r).length / 4),
                +!!d?.freeJump,
                +!!d?.fromStorage,
                +(d?.side === 'north'),
                +(d?.side === 'south'),
            ];
        });
    const result = { schema: protocol.schema, global, players, nodes, relations, actions, actionCity };
    for (const [key, value] of Object.entries(result))
        if (key !== 'schema' && !value.flat(Infinity).every(Number.isFinite)) throw Error(`Nonfinite ${key}`);
    return result;
}
module.exports = { E, RES, TYPES, MAPS, capacity, legal, encode, assertScope, refill, resourcePrice };
