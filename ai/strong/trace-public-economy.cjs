// Read-only research observer. Includes actual fuel fields and legacy root moves.
const fs = require('node:fs');
const path = require('node:path');
const root = process.env.PG_DIAGNOSTIC_RUNTIME;
if (!root || !path.isAbsolute(root)) throw Error('An explicit frozen runtime is required');
const c = require(path.join(root, 'ai/core.cjs'));
const engine = require(path.join(root, 'engine/dist/src/engine.js'));
const roots = new WeakSet();
function summary(g) {
    return {
        round: g.round, step: g.step, phase: g.phase, citiesToEndGame: g.citiesToEndGame,
        currentPlayers: [...g.currentPlayers], playerOrder: [...g.playerOrder],
        market: Object.fromEntries(c.RES.map(r => [r, {count: g[r+'Market'], prices: g[r+'Prices']}])),
        players: g.players.map(p => ({
            money: p.money, cities: p.cities.map(x => x.name), powered: p.citiesPowered,
            capacity: c.capacity(p), resources: Object.fromEntries(c.RES.map(r => [r, p[r+'Left']])),
            powerable: engine.calculateMaxCitiesPowered(g, p),
            fuelSupportedCapacity: engine.calculateMaxCitiesPowered(g, {...p, cities: Array(c.capacity(p))}),
            plants: p.powerPlants.map(pp => ({number: pp.number, capacity: pp.citiesPowered, type: pp.type, cost: pp.cost})),
            totalIncome: p.totalIncome, totalSpentCities: p.totalSpentCities,
            totalSpentConnections: p.totalSpentConnections, totalSpentPlants: p.totalSpentPlants,
            totalSpentResources: p.totalSpentResources,
        })),
    };
}
const setup = c.E.setup, move = c.E.move, moveAI = c.E.moveAI;
Object.defineProperty(c.E, 'setup', {configurable: true, enumerable: true, value: function (...args) {
    const g = setup(...args); roots.add(g); return g;
}});
function record(g, seat, action, legacy, invoke) {
    if (!roots.has(g)) return invoke();
    const before = JSON.stringify(summary(g));
    const result = invoke();
    const actual = legacy ? g.players[seat].lastMove : action;
    fs.appendFileSync(process.env.PG_TRACE_PATH, JSON.stringify({seat, legacy,
        action: {name: actual.name, data: actual.data}, before: JSON.parse(before), after: summary(g)})+'\n');
    return result;
}
Object.defineProperty(c.E, 'move', {configurable: true, enumerable: true, value: function (g, action, seat) {
    return record(g, seat, action, false, () => move(g, action, seat));
}});
Object.defineProperty(c.E, 'moveAI', {configurable: true, enumerable: true, value: function (g, seat) {
    return record(g, seat, null, true, () => moveAI(g, seat));
}});
