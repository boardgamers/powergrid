const test = require('node:test'), assert = require('node:assert/strict');
const fs = require('node:fs'), readline = require('node:readline'), path = require('node:path');
const encoders = require('./encoders.cjs');
test('all serving menus/prefixes stay fixed; eligibility is public and stateless', async () => {
    const fixtures = process.env.PG_SERVING_FIXTURES || path.join(__dirname, 'fixtures/multiplayer-serving-v1.jsonl');
    let positions = 0, eligible = 0;
    for await (const line of readline.createInterface({input: fs.createReadStream(fixtures)})) {
        const {state, player} = JSON.parse(line).request;
        const old = encoders.forRevision('4.1-five-plants').encode(state, player);
        const next = encoders.forRevision('4.2-discard-correction').encode(state, player);
        assert.deepEqual(next.moves, old.moves);
        assert.deepEqual(next.actions, old.actions);
        assert.deepEqual(next.state.slice(0, 1215), old.state);
        assert.equal(next.state.length, 1216);
        const late = Math.max(...state.players.map(p => p.cities.length)) >= state.citiesToEndGame - 3;
        const wanted = next.moves.length > 1 && next.moves.every(m => m.name === 'DiscardPowerPlant') && late;
        assert.equal(next.state[1215], +wanted);
        if (wanted) {
            eligible++;
            const hidden = structuredClone(state);
            hidden.seed = 'never-visible'; hidden.powerPlantsDeck = [{number: 999}];
            hidden.powerPlantDeckAfterStep3 = [{number: 888}]; hidden.hiddenLog = [{secret: true}];
            hidden.automation = {...hidden.automation, plans: {0: {secret: true}}};
            if (hidden.options.fastBid) {
                hidden.currentBid = 999;
                hidden.players.forEach(p => { p.bid = 999; });
            }
            assert.deepEqual(encoders.forRevision('4.2-discard-correction').encode(hidden, player), next);
            assert.deepEqual(encoders.forRevision('4.2-discard-correction').encode(state, player), next);
        }
        positions++;
    }
    assert.equal(positions, 2553); assert.equal(eligible, 9);
});
