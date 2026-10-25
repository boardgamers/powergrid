// Passive public inputs and actual search-policy choices for a future surrogate.
// This installs only in a dedicated arena process, never in live search workers.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const digest = value => crypto.createHash('sha256').update(JSON.stringify(value)).digest('hex');

function publicExample(runtime, state, player) {
    const load = name => require(path.join(runtime, name));
    const encoder = load('ai/strong/encoders.cjs').forRevision('4.3-strategic-correction');
    const beliefs = load('ai/strong/sealed-policy-beliefs.cjs');
    assert.equal(state.options.showMoney, true);
    const before = JSON.stringify(state);
    const request = {state: beliefs.publicState(state, player), player};
    const observation = encoder.encode(request.state, player);
    assert.deepEqual(observation, encoder.encode(state, player), 'Private fields changed model inputs');
    assert.equal(JSON.stringify(state), before);
    assert.equal(request.state.seed, 'secret');
    assert.deepEqual(request.state.powerPlantsDeck, []);
    assert.deepEqual(request.state.hiddenLog, []);
    assert.equal(request.state.powerPlantDeckAfterStep3, undefined);
    assert.equal(request.state.automation, undefined);
    assert(request.state.players.every(p => p.lastMove === null));
    if (state.options.fastBid) {
        assert.equal(request.state.currentBid, 0);
        assert(request.state.players.every(p => p.bid === 0));
    }
    assert.deepEqual(request.state.players.map(p => p.money), state.players.map(p => p.money));
    return {request, observation, publicRootSha256: digest(request),
        playerCount: state.players.length, seat: player, variant: state.options.variant,
        sealed: !!state.options.fastBid, round: state.round, phase: state.phase};
}

function install(runtime, output) {
    assert(path.isAbsolute(runtime) && path.isAbsolute(output));
    const search = require(path.join(runtime, 'ai/strong/search.cjs'));
    const original = search.choose;
    const fd = fs.openSync(output, 'wx');
    let ordinal = 0, depth = 0;
    search.choose = function (state, player, options = {}) {
        assert.equal(depth, 0, 'This capture is for actual arena decisions, not nested teacher calls');
        depth++;
        try {
            const before = JSON.stringify(state), optionsBefore = JSON.stringify(options);
            const example = publicExample(runtime, state, player);
            const started = process.hrtime.bigint();
            const result = original.call(this, state, player, options);
            const elapsedMs = Number(process.hrtime.bigint() - started) / 1e6;
            assert.equal(JSON.stringify(state), before, 'Teacher mutated game state');
            assert.equal(JSON.stringify(options), optionsBefore, 'Teacher mutated supplied settings');
            assert(Number.isInteger(result.index));
            assert.deepEqual(example.observation.moves[result.index], result.action);
            assert(example.observation.moves.length > 1);
            assert(example.observation.moves.some(m => ['ChoosePowerPlant', 'Bid', 'Build'].includes(m.name)));
            const record = {ordinal: ordinal++, ...example, target: result.index,
                teacher: {options: structuredClone(options), result: structuredClone(result), elapsedMs},
                purpose: 'Opponent-policy behavior imitation; no claim that this action is optimal.',
                qualification_eligible: false};
            fs.writeSync(fd, JSON.stringify(record) + '\n');
            return result;
        } finally { depth--; }
    };
    return () => { search.choose = original; fs.closeSync(fd); };
}

module.exports = {publicExample, install};
if (require.main === module) {
    const runtime = process.env.PG_OPPONENT_CAPTURE_RUNTIME;
    const output = process.env.PG_OPPONENT_CAPTURE_OUTPUT;
    assert(runtime && output);
    install(runtime, output);
    require(path.join(runtime, 'ai/strong/public-arena-bridge.cjs'));
}
