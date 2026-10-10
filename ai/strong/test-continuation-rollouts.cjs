const test = require('node:test');
const assert = require('node:assert/strict');
const { ContinuationBatch } = require('./continuation-rollouts.cjs');
const search = require('./search.cjs');
const c = require('../core.cjs');
const fixture = require('./fixtures/search-horizon-six-player.json');

const request = { state: fixture.state, player: fixture.seat, seed: 'continuation-regression',
    samples: 2, maxSteps: 2400, featureRevision: '4.0-multiplayer' };

test('batched engine reproduces reference continuations with identical public scenarios', () => {
    const original = JSON.stringify(fixture.state);
    const options = search.shortlist(fixture.state, fixture.seat, 6, true);
    for (const continuation of ['mixed', 'economic', 'heuristic']) {
        const expected = search.choose(fixture.state, fixture.seat, {
            samples: 2, candidates: 6, geography: true, seed: request.seed,
            maxSteps: request.maxSteps, continuation, includeSamples: true,
        });
        const actual = new ContinuationBatch().reset({ ...request, continuation, options, n: options.length * 2 });
        assert.ok(actual.observations.every(x => x === null));
        assert.equal(actual.ended.length, options.length * 2);
        for (const end of actual.ended) {
            assert.equal(end.value, expected.sampleOutcomes[end.actionIndex][end.sample]);
            assert.equal(end.truncated, end.value === null);
        }
    }
    assert.equal(JSON.stringify(fixture.state), original);
});

test('neural continuations obey legality, caps, and worker offsets', () => {
    const options = search.shortlist(fixture.state, fixture.seat, 6, true);
    const q = { ...request, maxSteps: 3, continuation: 'neural', options, n: options.length * 2 };
    const full = new ContinuationBatch(), a = new ContinuationBatch(), b = new ContinuationBatch();
    const first = full.reset(q);
    const left = a.reset({ ...q, n: options.length });
    const right = b.reset({ ...q, n: options.length, offset: options.length });
    assert.deepEqual(first.observations, [...left.observations, ...right.observations]);
    assert.throws(() => full.step(Array(q.n).fill(-1)), /Invalid rollout action|Action after/);
    let response = first, ended = [...first.ended];
    while (response.observations.some(Boolean)) {
        response = full.step(response.observations.map(x => x ? 0 : null));
        ended.push(...response.ended);
    }
    assert.equal(ended.length, q.n);
    assert.equal(new Set(ended.map(e => e.env)).size, q.n);
    assert.ok(ended.every(e => !e.truncated || e.value === null));
    assert.ok(ended.every(e => e.steps <= 3));
});

test('neural rollout observations do not reveal actual hidden deck or sealed bids', () => {
    const state = c.start('neural-rollout-info', 'original', true);
    let player = state.currentPlayers[0];
    c.E.move(state, c.candidates(state, player)[0], player);
    player = state.currentPlayers[0];
    const options = search.shortlist(state, player, 6, true);
    const q = { ...request, state, player, options, n: options.length * 2,
        maxSteps: 12, continuation: 'neural' };
    const a = new ContinuationBatch(), b = new ContinuationBatch();
    let left = a.reset(q);
    const hidden = structuredClone(state);
    hidden.powerPlantsDeck.reverse();
    hidden.seed = 'other-private-seed';
    hidden.players.forEach((p, i) => { if (i !== player) p.bid = 123; });
    hidden.currentBid = 456;
    hidden.hiddenLog = [{ secret: 'not observable' }];
    let right = b.reset({ ...q, state: hidden });
    for (;;) {
        assert.deepEqual(left, right);
        if (!left.observations.some(Boolean)) break;
        const actions = left.observations.map(x => x ? 0 : null);
        left = a.step(actions);
        right = b.step(actions);
    }
});
