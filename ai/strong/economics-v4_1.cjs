// Versioned auction cues. Keep economics.cjs and schema 4.0 baselines unchanged.
const c = require('../core.cjs'), old = require('./economics.cjs');
function plantLimit(g) {
    if (g.map.name !== 'Germany' || g.players.length < 2 || g.players.length > 6)
        throw Error('Plant-limit cues support Germany with 2–6 players');
    return g.players.length === 2 ? 4 : 3;
}
function plantValue(g, p, pp) {
    const limit = plantLimit(g);
    if (limit === 3 || p.powerPlants.length !== 3) return old.plantValue(g, p, pp);
    // At three plants a two-player purchase adds capacity, without replacement.
    const before = old.plan(g, p, 22),
        powerPlants = [...p.powerPlants, pp],
        after = old.plan(g, {...p, powerPlants}, 22),
        gain = c.capacity({powerPlants}) - c.capacity(p),
        need = Math.max(0, p.cities.length + 3 - c.capacity(p)),
        value = pp.number * 0.55 + gain * (need > 0 ? 10 : 6) + (before.cost - after.cost) * 2,
        reserve = p.cities.length === 0 ? 15 : Math.max(8, Math.min(35, p.cities.length * 1.5));
    return Math.max(0, Math.min(p.money - reserve, value));
}
function scores(g, seat, actions = c.candidates(g, seat)) {
    const values = old.scores(g, seat, actions), p = g.players[seat];
    if (plantLimit(g) !== 4 || p.powerPlants.length !== 3) return values;
    const worth = g.chosenPowerPlant ? plantValue(g, p, g.chosenPowerPlant) : 0;
    return actions.map((a, i) => {
        if (a.name === 'ChoosePowerPlant') {
            const pp = g.actualMarket.find(pp => pp.number === a.data), v = plantValue(g, p, pp);
            return v >= a.data ? 10 + (v - a.data) * 0.3 + pp.citiesPowered * 0.3 : -20;
        }
        if (a.name === 'Bid') {
            if (g.round === 1 && !actions.some(a => a.name === 'Pass')) return -a.data;
            return a.data <= worth
                ? (g.options.fastBid ? 10 - Math.abs(a.data - worth) * 0.5 : 10 - a.data * 0.2)
                : -30 - a.data;
        }
        return values[i];
    });
}
function choose(g, seat, rng = () => 0.5) {
    const actions = c.candidates(g, seat), values = scores(g, seat, actions);
    let index = 0, best = -Infinity;
    values.forEach((value, i) => {
        value += rng() * 0.001;
        if (value > best) {best = value; index = i;}
    });
    return {index, action: actions[index]};
}
module.exports = {plantLimit, plantValue, scores, choose};
