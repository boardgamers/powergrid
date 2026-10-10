const test = require('node:test');
const assert = require('node:assert/strict');
const { StrategicContinuations, MODES } = require('./strategic-continuations.cjs');
const { ContinuationBatch } = require('./continuation-rollouts.cjs');
const c = require('../core.cjs');
const search = require('./search.cjs');
const fixture = require('./fixtures/search-horizon-six-player.json');
const q = { state: fixture.state, player: fixture.seat, seed: 'strategic-continuations-contract-v1',
    featureRevision: '4.2-discard-correction', samples: 2, maxSteps: 2400 };
const options = search.shortlist(q.state, q.player, 6, true);
const baseShape = r => ({ ended: r.ended.map(({ roles, searchStats, policyDecisions, ...x }) => x),
    observations: r.observations.map(x => { if (!x) return x;
        const { actor, focalPlayer, roles, ...old } = x; return old; }) });

test('neural and mixed controls reproduce the historical rollout worker', () => {
    for (const [mode, continuation] of [['neural', 'neural'], ['mixed_control', 'mixed']]) {
        const plain = new ContinuationBatch(), next = new StrategicContinuations();
        const request = { ...q, options, n: options.length * 2, maxSteps: mode === 'neural' ? 12 : 2400 };
        let a = plain.reset({ ...request, continuation }), b = next.reset({ ...request, mode });
        for (;;) {
            assert.deepEqual(baseShape(b), a);
            if (a.observations.every(x => x === null)) break;
            const actions = a.observations.map(x => x ? 0 : null);
            a = plain.step(actions); b = next.step(actions);
        }
    }
});

test('opponent routing retains the neural focal player; offsets do not change trajectories', () => {
    const request = { ...q, options, n: options.length * 2, maxSteps: 18, mode: 'neural_economic' };
    const full = new StrategicContinuations(), left = new StrategicContinuations(), right = new StrategicContinuations();
    let a = full.reset(request), b = left.reset({ ...request, n: options.length }),
        d = right.reset({ ...request, n: options.length, offset: options.length });
    for (;;) {
        assert.deepEqual(a.observations, [...b.observations, ...d.observations]);
        assert.deepEqual(a.ended, [...b.ended, ...d.ended.map(x => ({ ...x, env: x.env + options.length }))]);
        for (const row of a.observations.filter(Boolean)) {
            assert.equal(row.actor, q.player);
            assert.equal(row.roles[row.actor], 'neural');
            assert.ok(row.roles.every((role, seat) => role === (seat === q.player ? 'neural' : 'economic')));
        }
        if (a.observations.every(x => x === null)) break;
        const actions = a.observations.map(x => x ? 0 : null);
        a = full.step(actions); b = left.step(actions.slice(0, options.length)); d = right.step(actions.slice(options.length));
    }
});

test('hidden live deck, private seed and sealed bids cannot affect paired continuations', () => {
    const state = c.start('strategic-continuation-info', 'original', true);
    let player = state.currentPlayers[0]; c.E.move(state, c.candidates(state, player)[0], player);
    player = state.currentPlayers[0];
    const hidden = structuredClone(state); hidden.powerPlantsDeck.reverse(); hidden.seed = 'private-elsewhere';
    hidden.players.forEach((p, i) => { if (i !== player) p.bid = 123; });
    hidden.currentBid = 456; hidden.hiddenLog = [{ secret: 'never use' }];
    const original = JSON.stringify(state);
    for (const mode of ['neural', 'neural_economic', 'mixed_control']) {
        const request = { ...q, state, player, mode, options: [0, 1], n: 4, maxSteps: 12 };
        const a = new StrategicContinuations(), b = new StrategicContinuations();
        let left = a.reset(request), right = b.reset({ ...request, state: hidden });
        for (;;) {
            assert.deepEqual(left, right);
            if (left.observations.every(x => x === null)) break;
            const actions = left.observations.map(x => x ? 0 : null);
            left = a.step(actions); right = b.step(actions);
        }
    }
    assert.equal(JSON.stringify(state), original);
});

test('nested search uses the full reference budget and exposes every inner cap', () => {
    const original = search.choose; let calls = 0;
    search.choose = (state, seat, config) => {
        calls++; assert.equal(config.samples, 16); assert.equal(config.candidates, 6);
        assert.equal(config.maxSteps, 2400); assert.equal(config.geography, true);
        return { action: c.candidates(state, seat)[0], evaluations: 96, truncated: 1 };
    };
    try {
        const engine = new StrategicContinuations();
        let result = engine.reset({ ...q, options, n: options.length * 2, mode: 'neural_search', maxSteps: 40 });
        let ended = result.ended;
        while (result.observations.some(Boolean)) {
            assert.ok(result.observations.filter(Boolean).every(o => o.actor === q.player));
            result = engine.step(result.observations.map(x => x ? 0 : null)); ended.push(...result.ended);
        }
        assert.ok(calls > 0); assert.equal(ended.reduce((sum, x) => sum + x.searchStats.truncated, 0), calls);
        assert.equal(ended.reduce((sum, x) => sum + x.searchStats.evaluations, 0), 96 * calls);
        assert.ok(ended.every(x => x.truncated ? x.value === null : Number.isFinite(x.value)));
    } finally { search.choose = original; }
});
