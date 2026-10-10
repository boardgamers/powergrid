const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const readline = require('node:readline');
const path = require('node:path');
const encoders = require('./encoders.cjs');
const originalEncoder = encoders.forRevision('4.0-multiplayer');
require('./capture-discard-training.cjs');

test('capture leaves inputs/game intact and omits hidden deck, bids and plans', async () => {
    const fixtures = process.env.PG_SERVING_FIXTURES || path.join(__dirname, 'fixtures/multiplayer-serving-v1.jsonl');
    let checked = 0;
    for await (const line of readline.createInterface({ input: fs.createReadStream(fixtures) })) {
        const { state, player } = JSON.parse(line).request;
        const legal = require('../core.cjs').candidates(state, player);
        if (legal.length < 2 || !legal.every(a => a.name === 'DiscardPowerPlant') ||
            Math.max(...state.players.map(p => p.cities.length)) < state.citiesToEndGame - 3) continue;
        const encoder = encoders.forRevision('4.0-multiplayer');
        const a = structuredClone(state), b = structuredClone(state);
        b.seed = 'different-private-seed';
        b.powerPlantsDeck = [{ number: 999 }];
        b.powerPlantDeckAfterStep3 = [{ number: 888 }];
        b.hiddenLog = [{ secret: 'unobservable' }];
        b.automation = { ...b.automation, plans: { 0: { private: true }, 1: { private: true } } };
        if (b.options.fastBid) {
            b.currentBid = 999;
            b.players.forEach((p, i) => { if (i !== player) p.bid = 999; });
        }
        const before = JSON.stringify(a), baseline = originalEncoder.encode(a, player);
        const captured = encoder.encode(a, player), hiddenVariant = encoder.encode(b, player);
        const root = captured.discardRoot;
        assert(root);
        assert.deepEqual(root, hiddenVariant.discardRoot);
        delete captured.discardRoot;
        assert.deepEqual(captured, baseline);
        assert.equal(JSON.stringify(a), before);
        assert.deepEqual(root.request.state.players.map(p => p.money), state.players.map(p => p.money));
        assert.deepEqual(root.legal, legal);
        assert.deepEqual(encoder.encode(a, player).discardRoot, root, 'every eligible observation is captured without changing public data');
        checked++;
    }
    assert.equal(checked, 9);
});
