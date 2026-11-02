// Frozen bootstrap teacher, NOT a claim of strong play. Keep Germany reference unchanged.
const f = require('./features.cjs');
const eco = require('../strong/economics.cjs');
const { minimumPlantBid } = require('../../engine/dist/src/auction-pricing.js');
function plantValue(g, p, pp) {
    const limit = g.players.length === 2 ? 4 : 3,
        before = eco.plan(g, p, 25),
        old = f.capacity(p);
    const portfolios =
        p.powerPlants.length < limit
            ? [[...p.powerPlants, pp]]
            : p.powerPlants.map((_, i) => [...p.powerPlants.filter((_, j) => i !== j), pp]);
    let best = -Infinity;
    for (const powerPlants of portfolios) {
        const after = eco.plan(g, { ...p, powerPlants }, 25),
            gain = f.capacity({ powerPlants }) - old;
        best = Math.max(
            best,
            pp.number * 0.55 + gain * (p.cities.length + 3 > old ? 10 : 6) + (before.cost - after.cost) * 2
        );
    }
    const reserve = p.cities.length === 0 ? 15 : Math.max(8, Math.min(35, p.cities.length * 1.5));
    return Math.max(0, Math.min(p.money - reserve, best));
}
function scores(g, seat, actions = f.legal(g, seat), style = 'geographic') {
    f.assertScope(g, seat);
    if (!['geographic', 'economic', 'rush'].includes(style)) throw Error('Unknown teacher');
    const raw = eco.scores(g, seat, actions, style === 'rush' ? 'rush' : 'economic'),
        p = g.players[seat];
    const worth = g.chosenPowerPlant ? plantValue(g, p, g.chosenPowerPlant) : 0;
    return actions.map((a, i) => {
        if (a.name === 'ChoosePowerPlant') {
            const pp = g.actualMarket.find((x) => x.number === a.data),
                cost = minimumPlantBid(g, pp),
                v = plantValue(g, p, pp);
            return v >= cost ? 10 + (v - cost) * 0.3 + pp.citiesPowered * 0.3 : -20;
        }
        if (a.name === 'Bid') {
            if (g.round === 1 && !actions.some((x) => x.name === 'Pass')) return -a.data;
            return a.data <= worth
                ? g.options.fastBid
                    ? 10 - Math.abs(a.data - worth) * 0.5
                    : 10 - a.data * 0.2
                : -30 - a.data;
        }
        if (a.name === 'BuyResource' && g.phase === f.E.Phase.Resources) {
            // Legal prices include USA's Recharged $8 supply purchases.
            const target = eco.context(g, seat).fuel.used[f.RES.indexOf(a.data.resource)];
            if (p[a.data.resource + 'Left'] < target) return 30 - f.resourcePrice(g, a.data.resource);
        }
        if (a.name === 'Build' && g.map.crossIslandSurcharge && p.cities.length > 0) {
            // UK second networks must begin in a completely empty city. Reserve
            // access before opponents occupy every entry; otherwise all players
            // can become permanently trapped below the victory threshold.
            const ownedIslands = new Set(p.cities.map((c) => g.map.cities.find((x) => x.name === c.name).island));
            const openIslands = new Set(
                g.map.cities
                    .filter((c) => !g.players.some((q) => q.cities.some((x) => x.name === c.name)))
                    .map((c) => c.island)
            );
            const missing = [...openIslands].filter((island) => !ownedIslands.has(island));
            if (missing.length) {
                const island = g.map.cities.find((c) => c.name === a.data.name).island;
                return missing.includes(island) ? 100 - a.data.price * 0.1 : -20;
            }
        }
        if (a.name === 'Build' && style === 'geographic') {
            const adjacent = g.map.connections.filter((e) => e.nodes.includes(a.data.name));
            const opportunity = adjacent.reduce((sum, e) => {
                const other = e.nodes.find((n) => n !== a.data.name);
                if (p.cities.some((c) => c.name === other)) return sum;
                const occupied = g.players.filter((q) => q.cities.some((c) => c.name === other)).length;
                return sum + (occupied < g.step ? 1 : 0.2) / (1 + e.cost / 10);
            }, 0);
            return raw[i] + Math.min(3, opportunity) * 0.35;
        }
        return raw[i];
    });
}
function choose(g, seat, actions = f.legal(g, seat), style = 'geographic', rng = () => 0.5) {
    const values = scores(g, seat, actions, style);
    if (!values.every(Number.isFinite)) throw Error('Nonfinite teacher');
    let best = -Infinity,
        index = -1;
    values.forEach((v, i) => {
        v += rng() * 1e-6;
        if (v > best) {
            best = v;
            index = i;
        }
    });
    return { index, action: actions[index], values };
}
module.exports = { plantValue, scores, choose };
