const E = require('../engine/dist/index.js');
const { map: germany, mapRecharged: germanyRecharged } = require('../engine/dist/src/maps/germany.js');
const seedrandom = require(require.resolve('seedrandom', { paths: [__dirname + '/../engine'] }));
const TYPES = [
    'ChoosePowerPlant',
    'Bid',
    'DiscardPowerPlant',
    'DiscardResources',
    'BuyResource',
    'Build',
    'UsePowerPlant',
    'ChooseRegion',
    'ChooseColor',
    'Pass',
];
const RES = ['coal', 'oil', 'garbage', 'uranium'];
const CITIES = [...new Set([...germany.cities, ...germanyRecharged.cities].map((c) => c.name))].sort();
const PHASES = Object.values(E.Phase);
const onehot = (v, vs) => vs.map((x) => +(x === v));
const plant = (p) =>
    p ? [p.number / 50, p.cost / 4, p.citiesPowered / 8, ...onehot(p.type, [0, 1, 2, 3, 4, 5])] : Array(9).fill(0);
function assertScope(g) {
    if (
        g.map.name !== 'Germany' ||
        g.players.length !== 3 ||
        g.options.randomizeMap ||
        g.map.cities.some((city) => !CITIES.includes(city.name)) ||
        g.options.chooseRegions ||
        g.options.chooseColors
    )
        throw Error('Baseline supports three-player Germany with automatic setup only');
}
function observe(g, seat) {
    assertScope(g);
    const order = [seat, (seat + 1) % 3, (seat + 2) % 3];
    const s = [
        ...onehot(g.phase, PHASES),
        g.round / 20,
        g.step / 3,
        +(g.options.variant === 'recharged'),
        +g.options.fastBid,
        g.cardsLeft / 50,
        +g.nextCardWeak,
        (g.options.fastBid ? 0 : g.currentBid || 0) / 100,
        (g.minimunBid || 0) / 100,
        ...onehot(g.auctioningPlayer, order),
        g.citiesToEndGame / 25,
        g.citiesToStep2 / 20,
    ];
    for (const r of RES)
        s.push(
            (g[r + 'Market'] || 0) / 24,
            (g[r + 'Supply'] || 0) / 24,
            ...(g[r + 'Prices'] || []).slice(0, 24).map((x) => x / 20),
            ...Array(Math.max(0, 24 - (g[r + 'Prices'] || []).length)).fill(0)
        );
    for (const i of order) {
        const p = g.players[i];
        s.push(
            p.money / 500,
            p.cities.length / 22,
            p.housesLeft / 22,
            p.citiesPowered / 22,
            g.playerOrder.indexOf(i) / 2,
            +p.skipAuction,
            +p.passed,
            (g.options.fastBid ? 0 : p.bid || 0) / 100
        );
        for (const r of RES) s.push((p[r + 'Left'] || 0) / 24, (p[r + 'Capacity'] || 0) / 24);
        s.push(p.hybridCapacity / 24);
        for (let j = 0; j < 4; j++) s.push(...plant(p.powerPlants[j]));
    }
    for (let i = 0; i < 4; i++) s.push(...plant(g.actualMarket[i]), ...plant(g.futureMarket[i]));
    s.push(...plant(g.chosenPowerPlant));
    for (const city of CITIES)
        s.push(
            +g.map.cities.some((c) => c.name === city),
            ...order.map((i) => +g.players[i].cities.some((c) => c.name === city))
        );
    if (!s.every(Number.isFinite)) throw Error('Non-finite observation');
    return s;
}
function allLegal(g, seat) {
    return Object.entries(g.players[seat].availableMoves || {}).flatMap(([name, items]) =>
        (items || []).map((data) => ({ name, data }))
    );
}
function candidates(g, seat) {
    const all = allLegal(g, seat),
        bids = all.filter((a) => a.name === 'Bid');
    if (bids.length <= 48) return all;
    const min = bids[0].data,
        max = bids.at(-1).data;
    return all.filter((a) => a.name !== 'Bid' || a.data < min + 8 || a.data % 10 === 0 || a.data === max);
}

function actionFeatures(g, seat, a) {
    const d = a.data,
        p = g.players[seat];
    const pp =
        a.name === 'ChoosePowerPlant'
            ? g.actualMarket.find((x) => x.number === d)
            : a.name === 'DiscardPowerPlant'
            ? p.powerPlants.find((x) => x.number === d)
            : a.name === 'UsePowerPlant'
            ? p.powerPlants.find((x) => x.number === d.powerPlant)
            : g.chosenPowerPlant;
    const cost = a.name === 'Bid' ? d : a.name === 'BuyResource' ? resourcePrice(g, d.resource) : d?.price || 0;
    return [
        ...onehot(a.name, TYPES),
        cost / 500,
        cost / Math.max(p.money, 1),
        ...onehot(d?.resource || (typeof d === 'string' ? d : ''), RES),
        ...plant(pp),
        ...onehot(d?.name, CITIES),
        (d?.citiesPowered || 0) / 20,
        ...RES.map((r) => (d?.resourcesSpent || []).filter((x) => x === r).length / 4),
    ];
}
function resourcePrice(g, resource, offset = 0) {
    const prices = g[resource + 'Prices'];
    const count = g[resource + 'Market'];
    return prices && count > offset ? prices[prices.length - count + offset] : 20;
}
function fuelDemand(g, p) {
    const target = Math.min(Math.max(p.cities.length, Math.min(3, capacity(p))), capacity(p));
    let powered = 0;
    const need = Object.fromEntries(RES.map((r) => [r, 0]));
    const ps = [...p.powerPlants].sort((a, b) => fuelCost(g, a) / a.citiesPowered - fuelCost(g, b) / b.citiesPowered);
    for (const pp of ps) {
        if (powered >= target) break;
        powered += pp.citiesPowered;
        let resource = RES[pp.type];
        if (pp.type === 4) resource = resourcePrice(g, 'coal') <= resourcePrice(g, 'oil') ? 'coal' : 'oil';
        if (resource) need[resource] += pp.cost;
    }
    return need;
}
function fuelCost(g, pp) {
    return (
        pp.cost *
        (pp.type === 4
            ? Math.min(resourcePrice(g, 'coal'), resourcePrice(g, 'oil'))
            : RES[pp.type]
            ? resourcePrice(g, RES[pp.type])
            : 0)
    );
}
const capacity = (p) => p.powerPlants.reduce((n, x) => n + x.citiesPowered, 0);
function plantWorth(g, p, pp) {
    let old = 0;
    if (p.powerPlants.length >= 3) old = Math.min(...p.powerPlants.map((x) => x.citiesPowered));
    const gain = Math.max(0, pp.citiesPowered - old);
    const reserve = Math.max(12, Math.min(40, p.cities.length * 2 + 10));
    const useful = gain > 0 || fuelCost(g, pp) < 3;
    return useful ? Math.min(p.money - reserve, pp.number + gain * 5 - fuelCost(g, pp)) : 0;
}
function heuristicScore(g, seat, a) {
    const p = g.players[seat],
        d = a.data,
        cap = capacity(p);
    switch (a.name) {
        case 'ChoosePowerPlant': {
            const pp = g.actualMarket.find((x) => x.number === d);
            const worth = plantWorth(g, p, pp);
            return worth >= d ? 20 + pp.citiesPowered * 5 - fuelCost(g, pp) - d * 0.2 : -100 - d;
        }
        case 'Bid': {
            const worth = Math.max(g.round === 1 ? g.minimunBid : 0, plantWorth(g, p, g.chosenPowerPlant));
            if (d > worth) return -100 - d;
            return g.options.fastBid ? 20 - Math.abs(worth - d) : 30 - d * 0.1;
        }
        case 'DiscardPowerPlant': {
            const pp = p.powerPlants.find((x) => x.number === d);
            return 10 - pp.citiesPowered * 5 + fuelCost(g, pp);
        }
        case 'DiscardResources':
            return 10 + (p[d + 'Left'] || 0);
        case 'BuyResource': {
            const need = fuelDemand(g, p),
                price = resourcePrice(g, d.resource);
            return p[d.resource + 'Left'] < need[d.resource] && p.money - price >= Math.max(0, p.cities.length ? 0 : 12)
                ? 20 - price
                : -100;
        }
        case 'Build': {
            const desired =
                p.money > 150 || g.round > 18
                    ? g.citiesToEndGame
                    : Math.min(g.citiesToEndGame, cap + (p.money > 100 ? 1 : 0));
            return p.cities.length < desired ? 30 - d.price * 0.5 : -100;
        }
        case 'UsePowerPlant':
            return (
                40 + (d.citiesPowered || 0) * 5 - (d.resourcesSpent || []).reduce((n, r) => n + resourcePrice(g, r), 0)
            );
        case 'Pass':
            return 0;
        default:
            return 1;
    }
}
function heuristic(g, seat, rng = () => 0.5) {
    const a = candidates(g, seat);
    let best = 0,
        v = -Infinity;
    a.forEach((x, i) => {
        const score = heuristicScore(g, seat, x) + rng() * 0.01;
        if (score > v) {
            v = score;
            best = i;
        }
    });
    return { index: best, action: a[best] };
}
function outcome(g) {
    const sorted = E.playersSortedByScore(g),
        top = sorted[0],
        w = g.players.map(
            (p) =>
                +(
                    p.citiesPowered === top.citiesPowered &&
                    p.money === top.money &&
                    p.cities.length === top.cities.length
                )
        );
    return w.map((x) => x / w.reduce((a, b) => a + b, 0));
}
function start(seed, variant = 'original', fastBid = false) {
    return E.setup(3, { map: 'Germany', variant, fastBid, showMoney: true }, seed);
}
module.exports = {
    E,
    CITIES,
    TYPES,
    RES,
    observe,
    allLegal,
    candidates,
    actionFeatures,
    heuristic,
    heuristicScore,
    outcome,
    start,
    seedrandom,
    resourcePrice,
    fuelDemand,
    fuelCost,
    capacity,
};
