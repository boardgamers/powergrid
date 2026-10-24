// One frozen diagnostic Build-versus-Pass branch. No serving or training use.
const assert = require('node:assert/strict'), fs = require('node:fs'), path = require('node:path');
const root = process.env.PG_DIAGNOSTIC_RUNTIME;
assert(root && path.isAbsolute(root));
const c = require(path.join(root, 'ai/core.cjs'));
const target = JSON.parse(process.env.PG_ENDGAME_BRANCH), roots = new WeakSet();
assert(['original', 'pass'].includes(target.branch));
const setup = c.E.setup, move = c.E.move;
let applied = 0;
Object.defineProperty(c.E, 'setup', {configurable: true, enumerable: true, value: function (...args) {
    const state = setup(...args); roots.add(state); return state;
}});
Object.defineProperty(c.E, 'move', {configurable: true, enumerable: true, value: function (state, action, seat) {
    if (roots.has(state) && state.round === target.round && seat === target.seat &&
        action.name === 'Build' && action.data.name === target.original.data.name) {
        assert.equal(++applied, 1, 'Intervention must match exactly once');
        assert.deepEqual(action, target.original, 'Prefix policy diverged');
        assert.equal(state.citiesToEndGame, target.threshold);
        assert(state.players.every(p => p.cities.length < state.citiesToEndGame));
        assert.equal(state.players[seat].cities.length+1, state.citiesToEndGame);
        const legal = c.allLegal(state, seat);
        const replacement = target.branch === 'original' ? action : {name: 'Pass', data: true};
        assert(legal.some(a => JSON.stringify(a) === JSON.stringify(replacement)), 'Illegal branch');
        fs.writeFileSync(process.env.PG_TRACE_PATH+'.intervention.json', JSON.stringify({
            applied, branch: target.branch, original: action, replacement,
            round: state.round, seat, legal,
        })+'\n');
        action = replacement;
    }
    return move(state, action, seat);
}});
