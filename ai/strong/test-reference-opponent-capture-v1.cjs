// Canonical privacy and observation checks; no search, training or HF submission.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const {publicExample} = require('./capture-reference-opponent-v1.cjs');
const runtime = path.resolve(process.argv[2]);
const file = path.join(__dirname, 'fixtures/multiplayer-serving-v1.jsonl');
assert.equal(crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex'),
    'f1c97bf909e38e5df372a89d169d80f5a6f24c00dccefacd60b10b767f1fcfa0');
const counts = {}, phases = {};
let positions = 0;
for (const line of fs.readFileSync(file, 'utf8').trim().split('\n')) {
    const {state, player} = JSON.parse(line).request;
    const before = JSON.stringify(state);
    const example = publicExample(runtime, state, player);
    assert.equal(JSON.stringify(state), before);
    const other = structuredClone(state);
    other.seed = 'private-seed-changed';
    other.powerPlantsDeck = [{number: 999}];
    other.hiddenLog = [{private: true}];
    other.powerPlantDeckAfterStep3 = [{number: 888}];
    other.automation = {plans: {0: {private: true}}};
    other.players.forEach(p => {p.lastMove = {name:'Bid', data:888}; if (other.options.fastBid) p.bid = 777;});
    if (other.options.fastBid) other.currentBid = 777;
    assert.deepEqual(publicExample(runtime, other, player), example);
    assert.equal(example.observation.featureRevision, '4.3-strategic-correction');
    assert.equal(example.observation.state.length, 1217);
    assert(example.observation.actions.every(a => a.length === 101));
    assert.equal(example.observation.actions.length, example.observation.moves.length);
    counts[state.players.length] = (counts[state.players.length] || 0) + 1;
    phases[state.phase] = (phases[state.phase] || 0) + 1;
    positions++;
}
assert.equal(positions, 2553);
assert.deepEqual(counts, {2:349, 3:427, 4:527, 5:609, 6:641});
console.log(JSON.stringify({positions, counts, phases, hidden_field_mutations:positions,
    public_features_exact:true, game_states_unchanged:true, real_teacher_calls:0,
    gradients:false, qualification_eligible:false}));
