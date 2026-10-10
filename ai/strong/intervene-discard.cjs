// Diagnostic only: one explicitly named root-game discard, with engine legality.
const assert = require('node:assert/strict'), fs = require('node:fs'), core = require('../core.cjs');
const target = JSON.parse(process.env.PG_DISCARD_BRANCH), roots = new WeakSet();
const setup = core.E.setup, move = core.E.move;
let applied = 0;
Object.defineProperty(core.E, 'setup', {configurable: true, enumerable: true, value: function (...args) {
    const state = setup(...args); roots.add(state); return state;
}});
Object.defineProperty(core.E, 'move', {configurable: true, enumerable: true, value: function (state, action, seat) {
    if (roots.has(state) && state.round === target.round && seat === target.seat &&
        action.name === 'DiscardPowerPlant') {
        assert.equal(++applied, 1, 'Intervention must match exactly once');
        assert.equal(action.data, target.original_discard, 'Prefix policy diverged');
        const legal = core.allLegal(state, seat);
        assert(legal.some(a => a.name === action.name && a.data === target.discard), 'Illegal intervention');
        fs.writeFileSync(process.env.PG_TRACE_PATH + '.intervention.json', JSON.stringify({
            applied, original: action, replacement: {name: action.name, data: target.discard},
            round: state.round, seat, legal,
        }) + '\n');
        action = {name: action.name, data: target.discard};
    }
    return move(state, action, seat);
}});
