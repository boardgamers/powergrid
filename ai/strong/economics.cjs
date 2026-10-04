// Public-information economic calculations. Never inspect the hidden deck or sealed bids.
const c = require('../core.cjs');
const income = (g, n) => g.paymentTable[Math.max(0, Math.min(g.paymentTable.length - 1, n))];
function replenishment(g, r, step = g.step) {
    if (
        r === 'uranium' &&
        g.options.variant === 'recharged' &&
        ['Germany', 'Italy'].includes(g.options.map) &&
        g.card39Bought
    )
        return 0;
    return g[r + 'Resupply'][g.players.length - 2][step - 1];
}
function fuelVariants(pp) {
    const base = [0, 0, 0, 0];
    if (pp.type === 4) return Array.from({ length: pp.cost + 1 }, (_, coal) => [coal, pp.cost - coal, 0, 0]);
    if (pp.type < 4) base[pp.type] = pp.cost;
    return [base];
}
function plans(g, p, unused = false) {
    let result = [{ power: 0, used: [0, 0, 0, 0], plants: [] }];
    for (const pp of p.powerPlants) {
        if (unused && !p.powerPlantsNotUsed.includes(pp.number)) continue;
        const next = [...result];
        for (const prev of result)
            for (const need of fuelVariants(pp))
                next.push({
                    power: prev.power + pp.citiesPowered,
                    used: prev.used.map((x, i) => x + need[i]),
                    plants: [...prev.plants, pp.number],
                });
        result = next;
    }
    return result;
}
function purchaseCost(g, p, used) {
    let cost = 0;
    for (let i = 0; i < 4; i++) {
        const resource = c.RES[i],
            needed = Math.max(0, used[i] - p[resource + 'Left']),
            count = g[resource + 'Market'],
            prices = g[resource + 'Prices'];
        for (let k = 0; k < needed; k++) {
            if (k >= count) return Infinity;
            cost += prices && count > k ? prices[prices.length - count + k] : 20;
        }
    }
    return cost;
}
function plan(g, p, target = p.cities.length, { buy = true, unused = false, budget = p.money, endgame = false } = {}) {
    let best = { power: 0, used: [0, 0, 0, 0], plants: [], cost: 0, score: -Infinity };
    for (const option of plans(g, p, unused)) {
        if (!buy && option.used.some((n, i) => n > p[c.RES[i] + 'Left'])) continue;
        const cost = buy ? purchaseCost(g, p, option.used) : 0;
        if (cost > budget) continue;
        const powered = Math.min(target, option.power + (unused ? p.citiesPowered : 0));
        const replacement = buy ? 0 : option.used.reduce((s, n, i) => s + n * c.resourcePrice(g, c.RES[i]), 0);
        const score = (endgame ? powered * 1000 : income(g, powered)) - cost - (buy ? 0 : replacement * 0.2);
        if (score > best.score) best = { ...option, powered, cost, score };
    }
    return best;
}
function demand(g, p) {
    return plan(g, p, Math.max(p.cities.length, Math.min(c.capacity(p), p.cities.length + 3))).used;
}
function futurePressure(g, r) {
    const i = c.RES.indexOf(r),
        needed = g.players.reduce((sum, p) => sum + demand(g, p)[i], 0);
    return needed - replenishment(g, r);
}
function context(g, seat) {
    const p = g.players[seat],
        cap = c.capacity(p),
        maxCities = Math.max(...g.players.map((x) => x.cities.length));
    const imminent = maxCities >= g.citiesToEndGame - 3;
    const target = Math.min(
        g.citiesToEndGame,
        Math.max(p.cities.length, Math.min(cap, p.cities.length + (p.cities.length ? 3 : 2)))
    );
    const fuel = plan(g, p, target, { budget: Math.max(0, p.money - (p.cities.length ? 0 : 10)), endgame: imminent });
    return { p, cap, maxCities, imminent, target, fuel };
}
function plantValue(g, p, pp) {
    const before = plan(g, p, 22),
        currentCap = c.capacity(p);
    let best = -Infinity;
    const portfolios =
        p.powerPlants.length < 3
            ? [[...p.powerPlants, pp]]
            : p.powerPlants.map((_, i) => [...p.powerPlants.filter((x, j) => i !== j), pp]);
    for (const powerPlants of portfolios) {
        const after = plan(g, { ...p, powerPlants }, 22),
            gain = powerPlants.reduce((s, x) => s + x.citiesPowered, 0) - currentCap;
        const fuelSaving = before.cost - after.cost;
        const need = Math.max(0, p.cities.length + 3 - currentCap);
        const value = pp.number * 0.55 + gain * (need > 0 ? 10 : 6) + fuelSaving * 2;
        best = Math.max(best, value);
    }
    const reserve = p.cities.length === 0 ? 15 : Math.max(8, Math.min(35, p.cities.length * 1.5));
    return Math.max(0, Math.min(p.money - reserve, best));
}
function scores(g, seat, actions = c.candidates(g, seat), style = 'economic') {
    const x = context(g, seat),
        p = x.p;
    let production;
    if (g.phase === c.E.Phase.Bureaucracy)
        production = plan(g, p, p.cities.length, {
            buy: false,
            unused: true,
            endgame: Math.max(...g.players.map((p) => p.cities.length)) >= g.citiesToEndGame,
        });
    const building = g.phase === c.E.Phase.Building;
    const possible = building ? plan(g, p, p.cities.length + 1, { buy: false }).powered : 0;
    const availablePower = building ? plan(g, p, x.cap, { buy: false }).powered : 0;
    const opponentPower = building
        ? Math.max(
              ...g.players
                  .filter((z) => z.id !== seat)
                  .map((z) => plan(g, z, z.cities.length + 2, { buy: false }).powered)
          )
        : 0;
    const bidWorth = g.chosenPowerPlant ? plantValue(g, p, g.chosenPowerPlant) : 0;
    return actions.map((a) => {
        const d = a.data;
        switch (a.name) {
            case 'ChoosePowerPlant': {
                const pp = g.actualMarket.find((p) => p.number === d);
                const v = plantValue(g, p, pp);
                return v >= d ? 10 + (v - d) * 0.3 + pp.citiesPowered * 0.3 : -20;
            }
            case 'Bid': {
                const v = bidWorth;
                if (g.round === 1 && !actions.some((a) => a.name === 'Pass')) return -d;
                return d <= v ? (g.options.fastBid ? 10 - Math.abs(d - v) * 0.5 : 10 - d * 0.2) : -30 - d;
            }
            case 'DiscardPowerPlant': {
                const powerPlants = p.powerPlants.filter((pp) => pp.number !== d);
                const pp = plan(g, { ...p, powerPlants }, 22);
                return pp.power * 5 - pp.cost;
            }
            case 'BuyResource': {
                const i = c.RES.indexOf(d.resource),
                    price = c.resourcePrice(g, d.resource);
                if (p[d.resource + 'Left'] < x.fuel.used[i]) return 30 - price;
                // Stock one extra round only when demand exceeds replenishment and today's price is low.
                const surplus = p[d.resource + 'Left'] - x.fuel.used[i],
                    ownNeed = c.fuelDemand(g, p)[d.resource];
                if (
                    style !== 'rush' &&
                    ownNeed > 0 &&
                    surplus < ownNeed &&
                    price <= 2 &&
                    p.money > 35 &&
                    futurePressure(g, d.resource) > 0
                )
                    return 4 - price;
                return -20;
            }
            case 'Build': {
                const next = p.cities.length + 1;
                if (p.money > 140 || g.round > 18) return 10 - d.price * 0.1;
                if (next >= g.citiesToEndGame && possible < opponentPower) return -30;
                if (next <= x.cap && (next <= availablePower || x.imminent)) return 25 - d.price * 0.35;
                if (style === 'rush' && p.money - d.price > 30) return 8 - d.price * 0.15;
                return -20;
            }
            case 'UsePowerPlant':
                return production.plants.includes(d.powerPlant) &&
                    c.RES.every((r, i) => d.resourcesSpent.filter((x) => x === r).length <= production.used[i])
                    ? 20 +
                          d.citiesPowered * 0.1 -
                          d.resourcesSpent.reduce((s, r) => s + c.resourcePrice(g, r), 0) * 0.01
                    : -10;
            case 'DiscardResources':
                return p[d + 'Left'] - x.fuel.used[c.RES.indexOf(d)];
            case 'Pass':
                return 0;
            default:
                return 0;
        }
    });
}
function choose(g, seat, rng = () => 0.5, style = 'economic') {
    const actions = c.candidates(g, seat),
        values = scores(g, seat, actions, style);
    let index = 0,
        best = -Infinity;
    values.forEach((x, i) => {
        x += rng() * 0.001;
        if (x > best) {
            best = x;
            index = i;
        }
    });
    return { index, action: actions[index] };
}
module.exports = {
    income,
    replenishment,
    fuelVariants,
    plans,
    purchaseCost,
    plan,
    demand,
    futurePressure,
    context,
    plantValue,
    scores,
    choose,
};
