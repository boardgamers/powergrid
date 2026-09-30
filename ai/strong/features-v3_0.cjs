// Frozen encoder for historical checkpoints; do not update its semantics.
const c = require('../core.cjs'),
    eco = require('./economics-v3_0.cjs');
const SCHEMA = 3;
const spatial = require('./spatial.cjs');
function observe(g, seat, geometry) {
    const state = c.observe(g, seat),
        order = [seat, (seat + 1) % 3, (seat + 2) % 3];
    for (const r of c.RES) {
        const supplies = g[r + 'Resupply'][g.players.length - 2];
        state.push(...supplies.map((n) => n / 12), c.resourcePrice(g, r) / 20);
        // Exact capped refill available now, and shared demand under full portfolio use.
        state.push(Math.min(g[r + 'Supply'], eco.replenishment(g, r), g[r + 'Prices'].length - g[r + 'Market']) / 24);
    }
    state.push(g.currentPlayers.length / 3, ...order.map((i) => +g.currentPlayers.includes(i)));
    for (const id of order) {
        const p = g.players[id],
            desired = eco.demand(g, p),
            fuelled = eco.plan(g, p, 22, { buy: false });
        state.push(
            c.capacity(p) / 22,
            fuelled.power / 22,
            ...desired.map((n) => n / 12),
            ...p.powerPlants.slice(0, 4).map((pp) => +p.powerPlantsNotUsed.includes(pp.number)),
            ...Array(Math.max(0, 4 - p.powerPlants.length)).fill(0)
        );
        state.push(...Array.from({ length: 4 }, (_, i) => +(p.powerPlants[i]?.type === 6)));
        const rank = g.playerOrder.indexOf(id);
        state.push(rank / 2, (2 - rank) / 2, +!p.passed, +!p.skipAuction);
        for (const r of c.RES) {
            const i = c.RES.indexOf(r);
            state.push(Math.max(0, desired[i] - p[r + 'Left']) / 12);
        }
    }
    state.push(...g.paymentTable.slice(0, 23).map((n) => n / 200));
    if (!state.every(Number.isFinite)) throw Error('nonfinite strong observation');
    return [...state, ...spatial.stateFeatures(g, seat, geometry)];
}
function encode(g, seat) {
    const moves = c.candidates(g, seat),
        prior = eco.scores(g, seat, moves),
        p = g.players[seat];
    const best = Math.max(...prior);
    const geometry = spatial.territories(g, seat),
        worth = new Map(),
        ownDemand = eco.demand(g, p);
    const plantWorth = (pp) => {
        if (!worth.has(pp.number)) worth.set(pp.number, eco.plantValue(g, p, pp));
        return worth.get(pp.number);
    };
    const actions = moves.map((a, i) => {
        const pp = a.name === 'ChoosePowerPlant' ? g.actualMarket.find((p) => p.number === a.data) : g.chosenPowerPlant;
        const cost =
            a.name === 'BuyResource'
                ? c.resourcePrice(g, a.data.resource)
                : a.name === 'Bid'
                ? a.data
                : a.data?.price || 0;
        const extra = [
            Math.max(-10, Math.min(10, prior[i] / 10)),
            +(prior[i] === best),
            cost / Math.max(1, p.money),
            Math.max(0, p.money - cost) / 200,
        ];
        if (pp) extra.push(plantWorth(pp) / 200, pp.citiesPowered / 8, pp.cost / 4);
        else extra.push(0, 0, 0);
        if (a.name === 'BuyResource') {
            const r = a.data.resource,
                j = c.RES.indexOf(r);
            extra.push(eco.replenishment(g, r) / 12, (ownDemand[j] - p[r + 'Left']) / 12);
        } else extra.push(0, 0);
        return [...c.actionFeatures(g, seat, a), ...extra, ...spatial.actionFeatures(g, seat, a, geometry)];
    });
    return {
        featureRevision: '3.0',
        state: observe(g, seat, geometry),
        actions,
        moves,
        prior: prior.map((x) => Math.max(-10, Math.min(10, x / 10))),
        teacher: prior.indexOf(best),
        seat,
    };
}
module.exports = { SCHEMA, observe, encode };
