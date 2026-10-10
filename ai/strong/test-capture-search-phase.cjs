const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const readline = require('node:readline');
const crypto = require('node:crypto');
const encoders = require('./encoders.cjs');
const revisions = ['3.0', '4.0-multiplayer', '4.2-discard-correction'];
const originals = Object.fromEntries(revisions.map(r => [r, encoders.forRevision(r)]));
require('./capture-search-phase.cjs');
const fixture = process.env.PG_SERVING_FIXTURES || path.join(__dirname, 'fixtures/multiplayer-serving-v1.jsonl');
assert.equal(crypto.createHash('sha256').update(fs.readFileSync(fixture)).digest('hex'),
    'f1c97bf909e38e5df372a89d169d80f5a6f24c00dccefacd60b10b767f1fcfa0');
(async () => {
    let positions = 0, checks = 0;
    const phases = {}, players = {};
    for await (const line of readline.createInterface({ input: fs.createReadStream(fixture) })) {
        const {state, player} = JSON.parse(line).request;
        const before = JSON.stringify(state);
        for (const revision of revisions) {
            if (revision === '3.0' && state.players.length !== 3) continue;
            const expected = originals[revision].encode(state, player);
            const result = encoders.forRevision(revision).encode(state, player);
            const moves = expected.moves;
            const phase = moves.length < 2 ? 'other' : moves.some(a => a.name === 'Build') ? 'building'
                : moves.some(a => ['ChoosePowerPlant', 'Bid'].includes(a.name)) ? 'auction' : 'other';
            assert.equal(result.searchPhase, phase);
            delete result.searchPhase;
            assert.deepEqual(result, expected);
            assert.equal(JSON.stringify(state), before);
            phases[phase] = (phases[phase] || 0) + 1;
            checks++;
        }
        players[state.players.length] = (players[state.players.length] || 0) + 1;
        positions++;
    }
    assert.equal(positions, 2553); assert.equal(checks, 5533);
    assert.deepEqual(players, {2:349,3:427,4:527,5:609,6:641});
    assert(phases.auction > 0 && phases.building > 0 && phases.other > 0);
    console.log(JSON.stringify({positions, checks, phases, players, observations_unchanged: true,
        scope: 'Read-only classification and unchanged features; no strength claim'}));
})().catch(error => { console.error(error); process.exitCode = 1; });
