// Separately versioned public-information mechanics. No v1 module is patched.
// Only dependency-free calculations are reused; functions closing over the old
// planner/cost/scoring implementations must not be reused here.
const { income, replenishment, fuelVariants } = require('../strong/economics.cjs');
const c = require('../core.cjs');
const f = require('./features.cjs');
const { minimumPlantBid } = require('../../engine/dist/src/auction-pricing.js');
const SCHEMA = 'multimap-economics-v2';

function plans(g, p, unused = false) {
    let result = [{ power: 0, used: [0, 0, 0, 0], plants: [], allocations: [] }];
    // Canonical order makes tied plans independent of portfolio presentation.
    for (const pp of [...p.powerPlants].sort((a, b) => a.number - b.number)) {
        if (unused && !p.powerPlantsNotUsed.includes(pp.number)) continue;
        const next = [...result];
        for (const prev of result)
            for (const need of fuelVariants(pp))
                next.push({
                    power: prev.power + pp.citiesPowered,
                    used: prev.used.map((x, i) => x + need[i]),
                    plants: [...prev.plants, pp.number],
                    allocations: [...prev.allocations, { powerPlant: pp.number, used: need }],
                });
        result = next;
    }
    return result;
}

// Quotes for additional purchases, not a storage-capacity or affordability check.
// Only USA Recharged can draw on this supply pool, after exhausting the market.
// Missing prices/stock fail closed; other maps' supply is never silently buyable.
function purchaseCosts(g, p) {
    const left = f.RES.map((r) => p[r + 'Left']);
    const markets = f.RES.map((r) => g[r + 'Market']);
    const prices = f.RES.map((r) => g[r + 'Prices']);
    const supply = f.RES.map((r) =>
        r === 'coal' && g.map.name === 'USA' && g.options.variant === 'recharged' ? Math.max(0, g.coalSupply || 0) : 0
    );
    const sums = f.RES.map(() => [0]);
    return (used) => {
        let total = 0;
        for (let i = 0; i < 4; i++) {
            const needed = Math.max(0, used[i] - left[i]);
            if (!Number.isInteger(needed)) return Infinity;
            if (!needed) continue;
            const count = markets[i],
                price = prices[i],
                cached = sums[i];
            if (!Number.isInteger(count) || count < 0 || needed > count + supply[i]) return Infinity;
            while (cached.length <= needed) {
                const k = cached.length - 1;
                const marginal = k < count ? price?.[price.length - count + k] : 8;
                cached.push(cached[k] + (Number.isFinite(marginal) && marginal >= 0 ? marginal : Infinity));
            }
            total += cached[needed];
        }
        return total;
    };
}
function purchaseCost(g, p, used) {
    return purchaseCosts(g, p)(used);
}

function plan(g, p, target = p.cities.length, { buy = true, unused = false, budget = p.money, endgame = false } = {}) {
    let best;
    const costOf = buy ? purchaseCosts(g, p) : null;
    const left = f.RES.map((r) => p[r + 'Left']);
    // Preserve v1's opportunity-cost objective, including the $20 scarcity proxy
    // when a market is empty. This is NOT a purchase quote. It stays unchanged
    // as fuel is burnt/returned to supply, making sequential optimization coherent.
    const replacementPrices = buy ? null : f.RES.map((r) => c.resourcePrice(g, r));
    for (const option of plans(g, p, unused)) {
        if (!buy && option.used.some((n, i) => n > left[i])) continue;
        const cost = buy ? costOf(option.used) : 0;
        if (!Number.isFinite(cost) || cost > budget) continue;
        const powered = Math.min(target, option.power + (unused ? p.citiesPowered : 0));
        const replacement = buy ? 0 : option.used.reduce((s, n, i) => s + n * replacementPrices[i], 0);
        const score = (endgame ? powered * 1000 : income(g, powered)) - cost - replacement * 0.2;
        if (
            !best ||
            (endgame && powered > best.powered) ||
            ((!endgame || powered === best.powered) && score > best.score)
        )
            best = { ...option, powered, cost, score };
    }
    if (!best) throw Error('No feasible v2 plan (invalid budget/holdings)');
    return best;
}
function demand(g, p) {
    return plan(g, p, Math.max(p.cities.length, Math.min(f.capacity(p), p.cities.length + 3))).used;
}
function futurePressure(g, r) {
    const i = f.RES.indexOf(r);
    return g.players.reduce((sum, p) => sum + demand(g, p)[i], 0) - replenishment(g, r);
}
function context(g, seat) {
    const p = g.players[seat],
        cap = f.capacity(p);
    const maxCities = Math.max(...g.players.map((x) => x.cities.length));
    const imminent = maxCities >= g.citiesToEndGame - 3;
    const target = Math.min(
        g.citiesToEndGame,
        Math.max(p.cities.length, Math.min(cap, p.cities.length + (p.cities.length ? 3 : 2)))
    );
    const fuel = plan(g, p, target, { budget: Math.max(0, p.money - (p.cities.length ? 0 : 10)), endgame: imminent });
    return { p, cap, maxCities, imminent, target, fuel };
}
// Do not spread an engine player: that would also read bid/lastMove/private
// annotations even though the planner never uses them.
function withPlants(p, powerPlants) {
    return {
        powerPlants,
        cities: p.cities,
        money: p.money,
        citiesPowered: p.citiesPowered,
        powerPlantsNotUsed: p.powerPlantsNotUsed,
        ...Object.fromEntries(f.RES.map((r) => [r + 'Left', p[r + 'Left']])),
    };
}
function plantValue(g, p, pp) {
    const limit = g.players.length === 2 ? 4 : 3;
    const before = plan(g, p, 25),
        old = f.capacity(p);
    const portfolios =
        p.powerPlants.length < limit
            ? [[...p.powerPlants, pp]]
            : p.powerPlants.map((_, i) => [...p.powerPlants.filter((_, j) => i !== j), pp]);
    let best = -Infinity;
    for (const powerPlants of portfolios) {
        const after = plan(g, withPlants(p, powerPlants), 25),
            gain = f.capacity({ powerPlants }) - old;
        best = Math.max(
            best,
            pp.number * 0.55 + gain * (p.cities.length + 3 > old ? 10 : 6) + (before.cost - after.cost) * 2
        );
    }
    const reserve = p.cities.length === 0 ? 15 : Math.max(8, Math.min(35, p.cities.length * 1.5));
    return Math.max(0, Math.min(p.money - reserve, best));
}

// Conditional finish guard, NOT an opponent-guaranteed-play certificate.
// Building continues past the end threshold. Compare CURRENT opponent networks
// against an optimistic focal ceiling over ALL remaining build continuations:
// maximum output feasible with held fuel, ignoring city/network and build-budget
// limits. The scoped engine computes final maximum power automatically after
// everyone passes; no competent Bureaucracy powering assumption is needed.
// Opponents may still build/spend cash, and the focal ceiling may be unreachable.
// There is no final-round income payout in scope.
function finishGuard(g, seat) {
    const p = g.players[seat],
        next = p.cities.length + 1;
    if (next < g.citiesToEndGame) return { triggered: false, ownPower: null, opponents: [] };
    const ownPower = plan(g, p, f.capacity(p), { buy: false, endgame: true }).powered;
    const opponents = g.players
        .filter((_, i) => i !== seat)
        .map((q) => ({
            power: plan(g, q, q.cities.length, { buy: false, endgame: true }).powered,
            money: q.money,
            cities: q.cities.length,
        }));
    return { triggered: true, ownPower, opponents };
}
function losingFinish(guard, p, price) {
    // Legal scoped builds never refund money, so post-FIRST-build cash is an
    // upper bound for every continuation. Do not veto on a current city-count
    // tiebreak: more builds can change it. Equal cash is deliberately left open,
    // without assuming strictly positive future build prices.
    return (
        guard.triggered &&
        guard.opponents.some(
            (q) => q.power > guard.ownPower || (q.power === guard.ownPower && q.money > p.money - price)
        )
    );
}
function scores(g, seat, actions = f.legal(g, seat), style = 'economic') {
    f.assertScope(g, seat);
    if (!['economic', 'rush', 'geographic'].includes(style)) throw Error('Unknown teacher');
    const x = context(g, seat),
        p = x.p;
    const production =
        g.phase === f.E.Phase.Bureaucracy
            ? plan(g, p, p.cities.length, {
                  buy: false,
                  unused: true,
                  endgame: x.maxCities >= g.citiesToEndGame,
              })
            : null;
    const building = g.phase === f.E.Phase.Building;
    const guard = building ? finishGuard(g, seat) : { triggered: false };
    const availablePower = building ? plan(g, p, x.cap, { buy: false }).powered : 0;
    const bidWorth = g.chosenPowerPlant ? plantValue(g, p, g.chosenPowerPlant) : 0;
    return actions.map((a) => {
        const d = a.data;
        switch (a.name) {
            case 'ChoosePowerPlant': {
                const pp = g.actualMarket.find((pp) => pp.number === d),
                    v = plantValue(g, p, pp);
                const cost = minimumPlantBid(g, pp);
                return v >= cost ? 10 + (v - cost) * 0.3 + pp.citiesPowered * 0.3 : -20;
            }
            case 'Bid':
                if (g.round === 1 && !actions.some((a) => a.name === 'Pass')) return -d;
                return d <= bidWorth ? (g.options.fastBid ? 10 - Math.abs(d - bidWorth) * 0.5 : 10 - d * 0.2) : -30 - d;
            case 'DiscardPowerPlant': {
                const powerPlants = p.powerPlants.filter((pp) => pp.number !== d);
                const pp = plan(g, withPlants(p, powerPlants), 22);
                return pp.power * 5 - pp.cost;
            }
            case 'BuyResource': {
                const i = f.RES.indexOf(d.resource),
                    price = f.resourcePrice(g, d.resource);
                if (p[d.resource + 'Left'] < x.fuel.used[i]) return 30 - price;
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
                if (losingFinish(guard, p, d.price)) return -30;
                if (p.money > 140 || g.round > 18) return 10 - d.price * 0.1;
                if (next <= x.cap && (next <= availablePower || x.imminent)) return 25 - d.price * 0.35;
                if (style === 'rush' && p.money - d.price > 30) return 8 - d.price * 0.15;
                return -20;
            }
            case 'UsePowerPlant': {
                const allocation = production?.allocations.find((x) => x.powerPlant === d.powerPlant);
                return allocation &&
                    f.RES.every((r, i) => d.resourcesSpent.filter((x) => x === r).length === allocation.used[i])
                    ? 20 +
                          d.citiesPowered * 0.1 -
                          d.resourcesSpent.reduce((s, r) => s + c.resourcePrice(g, r), 0) * 0.01
                    : -10;
            }
            case 'DiscardResources':
                return p[d + 'Left'] - x.fuel.used[f.RES.indexOf(d)];
            case 'Pass':
                return 0;
            default:
                return 0;
        }
    });
}
function choose(g, seat, rng = () => 0.5, style = 'economic') {
    const actions = f.legal(g, seat),
        values = scores(g, seat, actions, style);
    if (!values.every(Number.isFinite)) throw Error('Nonfinite v2 economics');
    let index = 0,
        best = -Infinity;
    values.forEach((v, i) => {
        v += rng() * 0.001;
        if (v > best) {
            best = v;
            index = i;
        }
    });
    return { index, action: actions[index] };
}
module.exports = {
    SCHEMA,
    income,
    replenishment,
    fuelVariants,
    plans,
    purchaseCost,
    purchaseCosts,
    plan,
    demand,
    futurePressure,
    context,
    plantValue,
    finishGuard,
    losingFinish,
    scores,
    choose,
};
