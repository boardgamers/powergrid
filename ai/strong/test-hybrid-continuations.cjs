const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const c = require('../core.cjs');
const beliefs = require('./sealed-policy-beliefs.cjs');
const { SealedBeliefContinuations } = require('./sealed-belief-continuations.cjs');
const { HybridContinuations, prepare, REVISIONS } = require('./hybrid-continuations.cjs');

const requests = [];
for (let n = 2; n <= 6; n++) for (const variant of ['original', 'recharged']) {
    for (const fastBid of [false, true]) {
        const state = c.E.setup(n, { map: 'Germany', variant, fastBid, showMoney: true },
            `hybrid-adapter-contract-${n}-${variant}-${fastBid}`);
        let player = state.currentPlayers[0];
        c.E.move(state, c.candidates(state, player).find(m => m.name === 'ChoosePowerPlant'), player);
        if (fastBid) {
            player = state.currentPlayers[0];
            c.E.move(state, c.candidates(state, player).find(m => m.name === 'Bid'), player);
        }
        player = state.currentPlayers[0];
        if (fastBid) assert(beliefs.prompts(state, player).length > 0);
        requests.push({ state: beliefs.publicState(state, player), player });
    }
}
const roots = fs.readFileSync(__dirname + '/fixtures/strategic-teacher-probe-v1.jsonl', 'utf8')
    .trim().split('\n').map(JSON.parse);
requests.push(...roots.filter(r => r.phase === 'building').map(r => r.request));
assert.equal(requests.length, 25);

function reset(q, revision, mode = 'neural') {
    const p = prepare({ ...q, featureRevision: revision });
    const neuralBeliefs = mode === 'neural' ? Object.fromEntries(p.prior.map(x =>
        [String(x.actor), x.encoded.moves.find(m => m.name === 'Pass') || x.encoded.moves[0]])) : {};
    return { ...q, featureRevision: revision, mode, belief: 'policy', neuralBeliefs,
        samples: 2, n: 4, options: [0, 1], maxSteps: 24, seed: 'hybrid-adapter-public-v1' };
}

function parentShape(result) {
    return { ...result, observations: result.observations.map(o => !o ? o : {
        ...o, featureRevision: REVISIONS[0], state: o.state.slice(0, 1216),
        actions: o.actions.map(a => a.slice(0, 100)),
    }) };
}

function compare(a, b, qa, qb, normalize = x => x, terminal = false) {
    let left = a.reset(qa), right = b.reset(qb), ended = 0;
    for (;;) {
        assert.deepEqual(normalize(right), left);
        if (terminal) assert(left.ended.every(r => !r.truncated && Number.isFinite(r.value)));
        ended += left.ended.length;
        if (left.observations.every(x => !x)) break;
        const choices = left.observations.map(x => x ? (terminal ? x.teacher : 0) : null);
        left = a.step(choices); right = b.step(choices);
    }
    assert.equal(ended, qa.n);
}

test('both feature revisions preserve every frozen transition and cap record in 25 positions', () => {
    for (const q of requests) for (const mode of ['neural', 'neural_economic']) {
        const old = reset(q, REVISIONS[0], mode);
        for (const revision of REVISIONS) {
            compare(new SealedBeliefContinuations(), new HybridContinuations(),
                old, reset(q, revision, mode), parentShape);
        }
    }
});

test('complete endpoint rollouts retain identical terminal outcomes across all four rules', () => {
    for (const q of requests.slice(0, 20).filter(q => [2, 6].includes(q.state.players.length))) {
        const old = { ...reset(q, REVISIONS[0], 'neural_economic'), maxSteps: 2400 };
        const next = { ...reset(q, REVISIONS[1], 'neural_economic'), maxSteps: 2400 };
        compare(new SealedBeliefContinuations(), new HybridContinuations(), old, next, parentShape, true);
    }
});

test('expanded format covers prior bidders as well as focal and opponent observations', () => {
    let priorActors = 0;
    for (const q of requests) {
        const p = prepare({ ...q, featureRevision: REVISIONS[1] });
        for (const row of [p.observation, ...p.prior.map(x => x.encoded)]) {
            assert.equal(row.featureRevision, REVISIONS[1]);
            assert.equal(row.state.length, 1217);
            assert(row.actions.every(a => a.length === 101));
        }
        priorActors += p.prior.length;
        const batch = new HybridContinuations();
        let result = batch.reset(reset(q, REVISIONS[1]));
        while (result.observations.some(Boolean)) {
            for (const row of result.observations.filter(Boolean)) {
                assert.equal(row.featureRevision, REVISIONS[1]);
                assert.equal(row.state.length, 1217);
                assert(row.actions.every(a => a.length === 101));
            }
            result = batch.step(result.observations.map(x => x ? 0 : null));
        }
    }
    assert(priorActors >= 10);
});

test('private fields cannot change preparation, beliefs or any expanded-format transition', () => {
    for (const q of requests.filter(q => q.state.options.fastBid)) {
        const before = JSON.stringify(q), other = structuredClone(q);
        other.state.seed = 'forbidden'; other.state.powerPlantsDeck = [{ number: 999 }];
        other.state.powerPlantDeckAfterStep3 = [{ number: 888 }];
        other.state.hiddenLog = [{ secret: true }]; other.state.currentBid = 777;
        other.state.automation = { plans: { 0: { secret: true } } };
        other.state.players.forEach(p => { p.bid = 666; p.lastMove = { name: 'Bid', data: 666 }; });
        assert.deepEqual(prepare({ ...q, featureRevision: REVISIONS[1] }),
            prepare({ ...other, featureRevision: REVISIONS[1] }));
        for (const mode of ['neural', 'neural_economic']) {
            compare(new HybridContinuations(), new HybridContinuations(),
                reset(q, REVISIONS[1], mode), reset(other, REVISIONS[1], mode));
        }
        assert.equal(JSON.stringify(q), before);
    }
});

test('worker partitioning preserves paired worlds, action outcomes and prior bids', () => {
    const q = requests.find(q => q.state.players.length === 6 && q.state.options.fastBid);
    for (const mode of ['neural', 'neural_economic']) {
        const request = reset(q, REVISIONS[1], mode);
        const full = new HybridContinuations(), left = new HybridContinuations(), right = new HybridContinuations();
        let a = full.reset(request), b = left.reset({ ...request, n: 2 }),
            d = right.reset({ ...request, n: 2, offset: 2 });
        assert.deepEqual(full.envs[0].initialBelief, full.envs[1].initialBelief);
        for (;;) {
            assert.deepEqual(a.observations, [...b.observations, ...d.observations]);
            assert.deepEqual(a.ended, [...b.ended, ...d.ended.map(x => ({ ...x, env: x.env + 2 }))]);
            if (a.observations.every(x => !x)) break;
            const choices = a.observations.map(x => x ? 0 : null);
            a = full.step(choices); b = left.step(choices.slice(0, 2)); d = right.step(choices.slice(2));
        }
    }
});

test('unsupported formats and illegal or missing beliefs fail before accepting a rollout', () => {
    // Opening auctions can require everyone to bid; reach a real later auction.
    const state = c.E.setup(4, { map: 'Germany', variant: 'recharged', fastBid: true, showMoney: true },
        'hybrid-adapter-pass-contract');
    const rng = c.seedrandom('hybrid-adapter-pass-moves');
    let q;
    for (let step = 0; step < 2400 && !c.E.ended(state); step++) {
        const player = state.currentPlayers[0];
        if (beliefs.prompts(state, player).some(p => p.encoded.moves.some(m => m.name === 'Pass'))) {
            q = { state: beliefs.publicState(state, player), player }; break;
        }
        c.E.move(state, c.heuristic(state, player, rng).action, player);
    }
    assert(q, 'No legal prior pass reached');
    const request = reset(q, REVISIONS[1]);
    assert(Object.values(request.neuralBeliefs).some(m => m.name === 'Pass'));
    const valid = new HybridContinuations();
    valid.reset(request);
    assert(valid.envs.every(e => e.initialBelief.committed.some(p => p.action.name === 'Pass')));
    for (const revision of [undefined, '4.0-sealed-all-bids', '4.4-unknown']) {
        assert.throws(() => prepare({ ...q, featureRevision: revision }));
        assert.throws(() => new HybridContinuations().reset({ ...request, featureRevision: revision }));
    }
    assert.throws(() => new HybridContinuations().reset({ ...request, neuralBeliefs: {} }));
    const bad = structuredClone(request);
    bad.neuralBeliefs[Object.keys(bad.neuralBeliefs)[0]] = { name: 'Bid', data: 999999 };
    assert.throws(() => new HybridContinuations().reset(bad));
});
