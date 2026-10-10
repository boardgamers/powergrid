const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const readline = require('node:readline');
const crypto = require('node:crypto');
const encoders = require('./encoders.cjs');
const baseline = encoders.forRevision('4.2-discard-correction');
const { phase } = require('./capture-strategic-training.cjs');
const captured = encoders.forRevision('4.2-discard-correction');
const file = process.env.PG_SERVING_FIXTURES || path.join(__dirname, 'fixtures/multiplayer-serving-v1.jsonl');
assert.equal(crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex'),
    'f1c97bf909e38e5df372a89d169d80f5a6f24c00dccefacd60b10b767f1fcfa0');
(async () => {
    const counts = { positions: 0, auction: 0, building: 0, excluded: 0, by_players: {} };
    for await (const line of readline.createInterface({input: fs.createReadStream(file)})) {
        const {state, player} = JSON.parse(line).request;
        const before = JSON.stringify(state), plain = baseline.encode(state, player);
        const observation = captured.encode(state, player), root = observation.strategicRoot;
        delete observation.strategicRoot;
        assert.deepEqual(observation, plain);
        assert.equal(JSON.stringify(state), before);
        const kind = phase(plain.moves);
        if (kind) {
            assert(root && root.phase === kind);
            assert.deepEqual(baseline.encode(root.request.state, player), plain, 'Public root changes model inputs/menu');
            assert.deepEqual(root.request.state.players.map(p => p.money), state.players.map(p => p.money));
            const hidden = structuredClone(state);
            hidden.seed = 'private-change'; hidden.powerPlantsDeck = [{number: 999}];
            hidden.powerPlantDeckAfterStep3 = [{number: 888}]; hidden.hiddenLog = [{secret: true}];
            hidden.automation = {...hidden.automation, plans: {0: {private: true}, 1: {private: true}}};
            if (hidden.options.fastBid) {
                hidden.currentBid = 999;
                hidden.players.forEach((p, i) => {if (i !== player) p.bid = 999;});
            }
            assert.deepEqual(captured.encode(hidden, player).strategicRoot, root, 'Private data leaked');
            counts[kind]++;
            counts.by_players[state.players.length] = (counts.by_players[state.players.length] || 0)+1;
        } else {
            assert.equal(root, undefined); counts.excluded++;
        }
        counts.positions++;
    }
    assert.equal(counts.positions, 2553);
    assert(counts.auction > 0 && counts.building > 0 && counts.excluded > 0);
    assert.deepEqual(Object.keys(counts.by_players), ['2','3','4','5','6']);
    console.log(JSON.stringify({...counts, observations_unchanged: true, private_data_invariant: true}));
})().catch(error => {console.error(error); process.exitCode = 1;});
