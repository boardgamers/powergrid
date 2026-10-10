// Read-only diagnostic preload. Never change a chosen action or an engine state.
const fs = require('node:fs');
const c = require('../core.cjs'), eco = require('./economics.cjs');
const roots = new WeakSet(), setup = c.E.setup, move = c.E.move;
function capacityAwareValue(g, p, pp) {
    const before = eco.plan(g, p, 22), currentCap = c.capacity(p);
    const limit = g.players.length === 2 ? 4 : 3;
    const portfolios = p.powerPlants.length < limit
        ? [[...p.powerPlants, pp]]
        : p.powerPlants.map((_, i) => [...p.powerPlants.filter((x, j) => i !== j), pp]);
    let best = -Infinity;
    for (const powerPlants of portfolios) {
        const after = eco.plan(g, {...p, powerPlants}, 22);
        const gain = c.capacity({powerPlants}) - currentCap;
        const need = Math.max(0, p.cities.length + 3 - currentCap);
        best = Math.max(best, pp.number * .55 + gain * (need > 0 ? 10 : 6) + (before.cost - after.cost) * 2);
    }
    const reserve = p.cities.length === 0 ? 15 : Math.max(8, Math.min(35, p.cities.length * 1.5));
    return Math.max(0, Math.min(p.money - reserve, best));
}
const emit = record => fs.appendFileSync(process.env.PG_PLANT_AUDIT_PATH, JSON.stringify(record) + '\n');
Object.defineProperty(c.E, 'setup', {configurable: true, enumerable: true, value: function (...args) {
    const g = setup(...args); roots.add(g); return g;
}});
Object.defineProperty(c.E, 'move', {configurable: true, enumerable: true, value: function (g, action, seat) {
    if (roots.has(g)) {
        const p = g.players[seat];
        if (g.players.length === 2 && p.powerPlants.length === 3 && ['ChoosePowerPlant', 'Bid'].includes(action.name)) {
            const plants = action.name === 'Bid' ? [g.chosenPowerPlant] : g.actualMarket;
            for (const pp of plants.filter(Boolean)) emit({kind: 'fourth_plant_value', round: g.round, seat,
                action, money: p.money, cities: p.cities.length, held: p.powerPlants.map(pp => pp.number),
                offered: pp.number, original_value: eco.plantValue(g, p, pp),
                capacity_aware_value: capacityAwareValue(g, p, pp)});
        }
        if (action.name === 'DiscardPowerPlant') {
            const encoder = require('./features-v4.cjs');
            const state = encoder.observe(g, seat).state;
            emit({kind: 'discard_observation', round: g.round, seat, action,
                state_dimension: state.length, owned_count: p.powerPlants.length,
                represented_slots: p.powerPlants.slice(0, 4).map(pp => pp.number),
                extra_plants: p.powerPlants.slice(4), chosen_plant: g.chosenPowerPlant || null,
                selected_capacity: p.powerPlants.find(pp => pp.number === action.data).citiesPowered,
                smallest_capacity: Math.min(...p.powerPlants.map(pp => pp.citiesPowered)),
                held_fuel: Object.fromEntries(c.RES.map(r => [r, p[r + 'Left']])),
                remaining_capacity: c.capacity(p) - p.powerPlants.find(pp => pp.number === action.data).citiesPowered});
        }
    }
    return move(g, action, seat);
}});
module.exports = {capacityAwareValue};
