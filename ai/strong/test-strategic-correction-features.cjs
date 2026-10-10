const test = require('node:test'), assert = require('node:assert/strict');
const fs = require('node:fs'), readline = require('node:readline'), path = require('node:path');
const parent = require('./features-v4_2.cjs'), next = require('./features-v4_3.cjs');
const search = require('./search.cjs');
test('2553 parent prefixes/menus and exact public teacher shortlists', async () => {
    const fixtures = process.env.PG_SERVING_FIXTURES || path.join(__dirname, 'fixtures/multiplayer-serving-v1.jsonl');
    let positions = 0, eligible = 0;
    const phases = new Set();
    for await (const line of readline.createInterface({input: fs.createReadStream(fixtures)})) {
        const {state, player} = JSON.parse(line).request;
        const a = parent.encode(state, player), b = next.encode(state, player);
        assert.deepEqual(b.moves, a.moves);
        assert.deepEqual(b.state.slice(0, 1216), a.state);
        assert.deepEqual(b.actions.map(x => x.slice(0, 100)), a.actions);
        assert.equal(b.state.length, 1217);
        assert.ok(b.actions.every(x => x.length === 101));
        const wanted = a.moves.length > 1 && a.moves.some(m => ['ChoosePowerPlant', 'Bid', 'Build'].includes(m.name));
        assert.equal(b.state[1216], +wanted);
        const actual = b.actions.flatMap((x, i) => x[100] ? [i] : []);
        const expected = wanted ? search.shortlist(state, player, 6, true).sort((x,y) => x-y) : [];
        assert.deepEqual(actual, expected);
        if (wanted) {
            eligible++;
            for (const m of a.moves) if (['ChoosePowerPlant', 'Bid', 'Build'].includes(m.name)) phases.add(m.name);
            const hidden = structuredClone(state);
            hidden.seed = 'irrelevant-real-game-seed'; hidden.powerPlantsDeck = [{number: 999}];
            hidden.powerPlantDeckAfterStep3 = [{number: 888}]; hidden.hiddenLog = [{secret: true}];
            hidden.automation = {...hidden.automation, plans: {0: {secret: true}}};
            assert.deepEqual(next.encode(hidden, player), b);
        }
        positions++;
    }
    assert.equal(positions, 2553);
    assert.ok(eligible > 0);
    assert.deepEqual([...phases].sort(), ['Bid', 'Build', 'ChoosePowerPlant']);
    console.log(JSON.stringify({positions, eligible, parent_features_and_menus_identical: true,
        exact_teacher_shortlists: true, hidden_state_does_not_change_features: true}));
});
