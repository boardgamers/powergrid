'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const { setImmediate: tick } = require('node:timers/promises');
const { ReplicaBot, MemoryHost, supported } = require('./adapter.cjs');
const { cloneState, SHAS } = require('./identity.cjs');
const { makeFixtures } = require('./fixtures.cjs');
const f = require('../multimap/features.cjs');
const teacher = require('../multimap/teacher_v2.cjs');
const { inputs } = require('../multimap/expert_game.cjs');
const wrapper = require('../../engine/dist/wrapper.js');
const fixtures = makeFixtures();
const nomination = fixtures.find((x) => x.kind === 'nomination');
const building = fixtures.find((x) => x.kind === 'Building' && x.map === 'Germany' && !x.fastBid);
function response(request, index = request.observation.prior.indexOf(0)) {
    return {
        schema: 'pg-replica-serving-response-v1',
        requestId: request.requestId,
        replica: request.replica,
        checkpointSha256: SHAS[request.replica],
        index,
        actionCount: request.observation.actions.length,
    };
}
function fake(handler = (r) => response(r)) {
    const transport = {
        replica: 'replica1',
        calls: [],
        closed: false,
        request(request) {
            this.calls.push(request);
            return handler(request, this.calls.length);
        },
        close() {
            this.closed = true;
        },
    };
    return transport;
}
function request(fixture, gameId = 'test', revision = 0) {
    return { state: fixture.state, player: fixture.player, gameId, revision };
}
function goldMoves(state, player) {
    const g = cloneState(state),
        moves = [];
    for (let i = 0; i < 128; i++) {
        const action = teacher.choose(g, player, f.legal(g, player), 'geographic').action;
        moves.push(cloneState(action));
        f.E.move(g, cloneState(action), player);
        if (g.newTurn !== false) return moves;
    }
    assert.fail('gold turn capped');
}
test('all 96 fresh positions: exact v2 observations/fixed phases, canonical full-turn mapping and replay', async () => {
    assert.equal(fixtures.length, 96);
    for (const fixture of fixtures) {
        const before = JSON.stringify(fixture.state),
            transport = fake((r) => response(r));
        const bot = new ReplicaBot({ replica: 'replica1', transport });
        assert(supported(fixture.state));
        const plan = await bot.planTurn(request(fixture));
        assert.equal(plan.diagnostics.fallback, false, fixture.id);
        assert.deepEqual(plan.moves, goldMoves(fixture.state, fixture.player), fixture.id);
        if (['Resources', 'Bureaucracy'].includes(fixture.kind)) assert.equal(transport.calls.length, 0);
        const simulated = cloneState(fixture.state);
        let query = 0;
        for (const move of plan.moves) {
            if (f.legal(simulated, fixture.player).length > 1 && ['Auction', 'Building'].includes(simulated.phase)) {
                assert.deepEqual(transport.calls[query++].observation, inputs(simulated, fixture.player));
                assert.deepEqual(Object.keys(transport.calls[query - 1]).sort(), [
                    'observation',
                    'replica',
                    'requestId',
                    'schema',
                ]);
            }
            f.E.move(simulated, cloneState(move), fixture.player);
        }
        const saved = await bot.applyPlan(request(fixture), plan);
        assert.notEqual(saved.newTurn, false);
        assert.deepEqual(cloneState(wrapper.replay(cloneState(saved))), saved, fixture.id);
        assert.equal(JSON.stringify(fixture.state), before);
        assert(Object.isFrozen(plan) && Object.isFrozen(plan.moves));
    }
});
test('multi-action plan stops at FIRST real boundary and cannot be forged or used on changed menus', async () => {
    const bot = new ReplicaBot({
        replica: 'replica1',
        transport: fake(() => {
            throw Error('unused');
        }),
    });
    const fixture = fixtures.find((x) => x.kind === 'Resources' && goldMoves(x.state, x.player).length > 1);
    const plan = await bot.planTurn(request(fixture));
    assert(plan.moves.length > 1);
    await assert.rejects(bot.applyPlan(request(fixture), cloneState(plan)), /stale-or-untrusted/);
    const changed = cloneState(fixture.state);
    changed.players[fixture.player].availableMoves.Pass = [];
    await assert.rejects(bot.applyPlan({ ...request(fixture), state: changed }, plan), /stale-or-untrusted/);
    assert.throws(() => plan.moves.push({ name: 'Pass', data: true }), TypeError);
});
test('duplicates coalesce and completed receipts do not commit or infer twice', async () => {
    let release;
    const transport = fake((r, count) =>
        count === 1
            ? new Promise((resolve) => {
                  release = () => resolve(response(r));
              })
            : response(r)
    );
    const bot = new ReplicaBot({ replica: 'replica1', transport }),
        host = new MemoryHost();
    host.add('duplicate', nomination.state);
    const req = { gameId: 'duplicate', revision: 0, player: nomination.player };
    const a = host.play(bot, req),
        b = host.play(bot, req);
    assert.strictEqual(a, b);
    await tick();
    release();
    const receipt = await a,
        callCount = transport.calls.length;
    assert.equal(receipt.diagnostics.fallback, false);
    assert.strictEqual(await host.play(bot, req), receipt);
    assert.equal(host.snapshot('duplicate').revision, 1);
    assert.equal(transport.calls.length, callCount);
    assert.equal(wrapper.timeIncrements(host.snapshot('duplicate').state)[nomination.player], 1);
    const restarted = new MemoryHost(),
        snapshot = host.snapshot('duplicate');
    restarted.add('duplicate', snapshot.state, snapshot.revision);
    assert.throws(() => restarted.play(bot, req), /stale-revision/); // No replay after cache loss.
});
test('input state is detached; same revision with changed state conflicts', async () => {
    const transport = fake((r) => response(r)),
        bot = new ReplicaBot({ replica: 'replica1', transport });
    const state = cloneState(nomination.state),
        req = { ...request(nomination), state };
    const pending = bot.planTurn(req);
    state.players[nomination.player].money++;
    assert.throws(() => bot.planTurn(req), /revision-state-conflict/);
    const plan = await pending;
    await assert.rejects(bot.applyPlan(req, plan), /stale-or-untrusted/);
});
test('undo/replacement invalidates in-flight inference without falling back on stale state', async () => {
    let release;
    const transport = fake((r, count) =>
        count === 1
            ? new Promise((resolve) => {
                  release = () => resolve(response(r));
              })
            : response(r)
    );
    const bot = new ReplicaBot({ replica: 'replica1', transport }),
        host = new MemoryHost();
    host.add('undo', nomination.state);
    const pending = host.play(bot, { gameId: 'undo', revision: 0, player: nomination.player });
    await tick();
    host.replace('undo', nomination.state, 0);
    release();
    await assert.rejects(pending, /stale-revision/);
    assert.deepEqual(host.snapshot('undo'), { gameId: 'undo', revision: 1, state: nomination.state });
});
test('simultaneous players use CAS after awaits; one wins, the other must refresh', async () => {
    const fixture = fixtures.find((x) => x.kind === 'Bureaucracy' && x.state.currentPlayers.length > 1);
    const host = new MemoryHost(),
        bot = new ReplicaBot({ replica: 'replica1', transport: fake() });
    host.add('simultaneous', fixture.state);
    const results = await Promise.allSettled(
        fixture.state.currentPlayers
            .slice(0, 2)
            .map((player) => host.play(bot, { gameId: 'simultaneous', revision: 0, player }))
    );
    assert.equal(results.filter((x) => x.status === 'fulfilled').length, 1);
    assert.equal(results.filter((x) => x.status === 'rejected' && x.reason.code === 'stale-revision').length, 1);
    assert.equal(host.snapshot('simultaneous').revision, 1);
});
test('sealed bids commit with unchanged visible log, using explicit host revision', async () => {
    const fixture = fixtures.find((x) => x.kind === 'bid' && x.fastBid && x.state.currentPlayers.length > 1);
    const host = new MemoryHost(),
        bot = new ReplicaBot({ replica: 'replica1', transport: fake((r) => response(r, 0)) });
    host.add('sealed', fixture.state);
    await host.play(bot, { gameId: 'sealed', revision: 0, player: fixture.player });
    const saved = host.snapshot('sealed');
    assert.equal(saved.revision, 1);
    assert.equal(saved.state.log.length, fixture.state.log.length);
    assert(saved.state.hiddenLog.length > fixture.state.hiddenLog.length);
    assert.deepEqual(cloneState(wrapper.replay(cloneState(saved.state))), saved.state);
});
test('invalid identity, index, extra fields, worker failure and timeout use observable WHOLE-turn fallback', async () => {
    const mutations = [
        (r) => ({ ...response(r), index: -1 }),
        (r) => ({ ...response(r), index: 1.5 }),
        (r) => ({ ...response(r), index: NaN }),
        (r) => ({ ...response(r), requestId: 'bad' }),
        (r) => ({ ...response(r), replica: 'replica2' }),
        (r) => ({ ...response(r), checkpointSha256: '0'.repeat(64) }),
        (r) => ({ ...response(r), actionCount: 999 }),
        (r) => ({ ...response(r), raw: 'forbidden' }),
        () => {
            throw Error('private error never copied');
        },
    ];
    for (const mutate of mutations) {
        const bot = new ReplicaBot({ replica: 'replica1', transport: fake(mutate) });
        const plan = await bot.planTurn(request(nomination));
        assert(plan.diagnostics.fallback);
        assert.equal(plan.diagnostics.counts.learned, 0);
        assert.equal(plan.diagnostics.counts.heuristicFallback, plan.moves.length);
        assert.notEqual((await bot.applyPlan(request(nomination), plan)).newTurn, false);
        assert(!JSON.stringify(plan.diagnostics).includes('private error'));
    }
    let late;
    const transport = fake(
        (r) =>
            new Promise((resolve) => {
                late = () => resolve(response(r));
            })
    );
    const bot = new ReplicaBot({ replica: 'replica1', transport, inferenceMs: 10 });
    const host = new MemoryHost();
    host.add('timeout', nomination.state);
    const receipt = await host.play(bot, { gameId: 'timeout', revision: 0, player: nomination.player });
    assert(receipt.diagnostics.fallback && transport.closed);
    late();
    await tick();
    assert.equal(host.snapshot('timeout').revision, 1);
});
test('timeout settles and falls back even if cleanup throws or rejects', async () => {
    for (const close of [
        () => {
            throw Error('cleanup');
        },
        () => Promise.reject(Error('cleanup')),
    ]) {
        const transport = fake(() => new Promise(() => {}));
        transport.close = close;
        const bot = new ReplicaBot({ replica: 'replica1', transport, inferenceMs: 10 });
        const plan = await bot.planTurn(request(nomination));
        assert.equal(plan.diagnostics.reason, 'inference-timeout');
        assert.notEqual((await bot.applyPlan(request(nomination), plan)).newTurn, false);
        await tick();
    }
});
test('non-prior indices stay bound to their canonical menu and stop at exactly one boundary', async () => {
    for (const fixture of fixtures) {
        const bot = new ReplicaBot({
            replica: 'replica1',
            transport: fake((r) => response(r, r.observation.actions.length - 1)),
        });
        const plan = await bot.planTurn(request(fixture));
        assert.equal(plan.diagnostics.fallback, false);
        const g = cloneState(fixture.state);
        for (const [i, move] of plan.moves.entries()) {
            assert(f.legal(g, fixture.player).some((candidate) => JSON.stringify(candidate) === JSON.stringify(move)));
            f.E.move(g, cloneState(move), fixture.player);
            assert.equal(g.newTurn !== false, i === plan.moves.length - 1);
        }
    }
});
test('a partially planned learned turn is discarded on failure', async () => {
    const transport = fake((r, count) => (count === 1 ? response(r, 0) : { ...response(r), index: -1 }));
    const bot = new ReplicaBot({ replica: 'replica1', transport });
    const plan = await bot.planTurn(request(building));
    assert(transport.calls.length >= 2);
    assert(plan.diagnostics.fallback);
    assert.equal(plan.diagnostics.counts.learned, 0);
    assert.equal(plan.diagnostics.counts.heuristicFallback, plan.moves.length);
    assert.notEqual((await bot.applyPlan(request(building), plan)).newTurn, false);
});
test('out-of-scope opts use heuristic only; inactive/tentative and capped turns never commit', async () => {
    for (const change of [
        (g) => {
            g.options.showMoney = false;
        },
        (g) => {
            g.options.chooseRegions = true;
        },
        (g) => {
            g.map.name = g.options.map = 'Italy';
        },
        (g) => {
            g.options.endPlantDiscountAtStep3 = true;
        },
    ]) {
        const state = cloneState(nomination.state);
        change(state);
        const transport = fake(() => {
            throw Error('must not infer');
        });
        const plan = await new ReplicaBot({ replica: 'replica1', transport }).planTurn({
            ...request(nomination),
            state,
        });
        assert.equal(plan.diagnostics.reason, 'unsupported-scope');
        assert.equal(transport.calls.length, 0);
    }
    const bot = new ReplicaBot({ replica: 'replica1', transport: fake() });
    assert.throws(
        () => bot.planTurn({ ...request(nomination), state: { ...nomination.state, newTurn: false } }),
        /tentative/
    );
    assert.throws(() => bot.planTurn({ ...request(nomination), player: 99 }), /inactive/);
    const state = cloneState(building.state),
        p = building.player;
    state.players[p].availableMoves = { Build: [state.players[p].availableMoves.Build[0]] };
    const host = new MemoryHost();
    host.add('cap', state);
    const capped = new ReplicaBot({ replica: 'replica1', transport: fake(), maxActions: 1 });
    await assert.rejects(host.play(capped, { gameId: 'cap', revision: 0, player: p }), /turn-cap/);
    assert.deepEqual(host.snapshot('cap'), { gameId: 'cap', revision: 0, state });
});
test('public observations/priors ignore poisoned hidden state; nonfinite state rejected before JSON normalization', () => {
    const fixture = fixtures.find((x) => x.kind === 'bid' && x.fastBid),
        state = cloneState(fixture.state);
    state.seed = 'poison';
    state.powerPlantsDeck.reverse();
    state.hiddenLog = [{ secret: true }];
    state.powerPlantDeckAfterStep3 = [{ number: 999 }];
    state.currentBid = 999;
    state.players.forEach((p) => {
        p.lastMove = { secret: true };
        p.bid = 999;
    });
    assert.deepEqual(inputs(state, fixture.player), fixture.observation);
    state.players[fixture.player].money = Infinity;
    assert.throws(() => cloneState(state), /non-json-value/);
});
