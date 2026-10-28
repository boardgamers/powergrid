const assert = require('node:assert/strict'), fs = require('node:fs'), path = require('node:path');
const root = path.resolve(__dirname, '../..');
const base = require(path.join(root, 'ai/runs/resource-turn-full-artifact-v4/runtime/ai/strong/features-v4_3.cjs'));
const current = path.join(root, 'ai/runs/current-engine-compatibility-v1/source/engine/dist');
const engine = require(path.join(current, 'index.js'));
const {minimumPlantBid} = require(path.join(current, 'src/auction-pricing.js'));
const extension = require('./features-v4_4.cjs');
const inputs = JSON.parse(fs.readFileSync(path.join(root, 'ai/runs/current-engine-policy-v1/inputs.json'), 'utf8'));
const clone = x => JSON.parse(JSON.stringify(x));
let encodings = 0, separatedPairs = 0;

function check(g, seat) {
    const before = clone(g), parent = base.encode(g, seat), parentBefore = clone(parent);
    const row = extension.extend(g, parent);
    assert.equal(row.state.length, 1218);
    assert(row.actions.every(a => a.length === 103));
    assert.deepEqual(row.state.slice(0, 1217), parent.state);
    assert.deepEqual(row.actions.map(a => a.slice(0, 101)), parent.actions);
    assert.deepEqual({...row, state: parent.state, actions: parent.actions, featureRevision: parent.featureRevision}, parent);
    for (const [i, move] of row.moves.entries()) {
        if (move.name === 'ChoosePowerPlant') {
            const plant = g.actualMarket.find(p => p.number === move.data);
            const bid = minimumPlantBid(g, plant);
            assert.deepEqual(row.actions[i].slice(101), [bid / 50, (plant.number - bid) / 50]);
        } else assert.deepEqual(row.actions[i].slice(101), [0, 0]);
    }
    assert.deepEqual(g, before); assert.deepEqual(parent, parentBefore);
    encodings++;
    return row;
}

for (const fixture of inputs) {
    const g = clone(fixture.request.state), seat = fixture.request.player;
    g.players[seat].availableMoves = engine.availableMoves(g, g.players[seat]);
    const row = check(g, seat);
    if (fixture.kind === 'recorded-control') {
        const without = clone(g); without.plantDiscountActive = false;
        without.players[seat].availableMoves = engine.availableMoves(without, without.players[seat]);
        const other = check(without, seat);
        assert.deepEqual(row.moves, other.moves);
        assert.deepEqual(row.state.slice(0, 1217), other.state.slice(0, 1217));
        assert.deepEqual(row.actions.map(a => a.slice(0, 101)), other.actions.map(a => a.slice(0, 101)));
        assert.notDeepEqual(row.state, other.state); assert.notDeepEqual(row.actions, other.actions);
        separatedPairs++;
    }
    if (fixture.kind === 'discount-money-one') {
        const i = row.moves.findIndex(m => m.name === 'ChoosePowerPlant' && m.data === g.actualMarket[0].number);
        assert(i >= 0); assert.equal(row.actions[i][101], 1 / 50);
    }
    if (fixture.kind === 'no-money-pass') assert(row.moves.every(m => m.name === 'Pass'));
}
assert.equal(encodings, 40); assert.equal(separatedPairs, 10);

// Exercise non-auction phases and invalid inputs without importing a mutable engine.
const g = clone(inputs[0].request.state);
const parent = {featureRevision: '4.3-strategic-correction', state: Array(1217).fill(0),
    moves: ['Bid', 'Pass', 'Build', 'BuyCoal', 'ActivatePowerPlant', 'DiscardPowerPlant'].map(name => ({name, data: 3})),
    actions: Array.from({length: 6}, () => Array(101).fill(0))};
assert(extension.extend(g, parent).actions.every(a => a[101] === 0 && a[102] === 0));
assert.throws(() => extension.extend({...g, plantDiscountActive: undefined}, parent), /public plantDiscountActive/);
assert.throws(() => extension.extend(g, {...parent, featureRevision: '4.2-discard-correction'}), /unchanged schema 4.3/);
assert.throws(() => extension.extend(g, {...parent, moves: [{name: 'ChoosePowerPlant', data: 999}], actions: [parent.actions[0]]}), /absent/);
assert.equal(extension.openingBid({...g, options: {...g.options, variant: 'original'}, plantDiscountActive: true}, g.actualMarket[0]), g.actualMarket[0].number);
console.log(JSON.stringify({passed: true, actual_fixture_encodings: encodings, formerly_aliased_pairs_separated: separatedPairs,
    additional_contract_checks: 5, new_inference: 0, new_games: 0}));
