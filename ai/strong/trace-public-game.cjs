// Diagnostic preload: observe actual root-game moves without changing decisions.
const fs = require('node:fs');
const c = require('../core.cjs');
const roots = new WeakSet(), setup = c.E.setup, move = c.E.move;
function summary(g) {
    return {
        round: g.round, step: g.step, phase: g.phase,
        currentPlayers: g.currentPlayers, playerOrder: g.playerOrder,
        players: g.players.map(p => ({
            money: p.money, cities: p.cities.map(x => x.name),
            powered: p.citiesPowered, capacity: c.capacity(p),
            resources: p.resources,
            plants: p.powerPlants.map(pp => ({number: pp.number, capacity: pp.citiesPowered})),
        })),
    };
}
Object.defineProperty(c.E, 'setup', {configurable: true, enumerable: true, value: function (...args) {
    const g = setup(...args);
    roots.add(g);
    return g;
}});
Object.defineProperty(c.E, 'move', {configurable: true, enumerable: true, value: function (g, action, seat) {
    if (!roots.has(g)) return move(g, action, seat);
    const before = JSON.stringify({seat, action, before: summary(g)});
    const result = move(g, action, seat);
    fs.appendFileSync(process.env.PG_TRACE_PATH,
        JSON.stringify({...JSON.parse(before), after: summary(g)}) + '\n');
    return result;
}});
