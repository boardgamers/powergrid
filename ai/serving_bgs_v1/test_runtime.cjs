'use strict';
// Fresh, bounded engineering positions ONLY; no games, study roots, checkpoints,
// replay corpora, strength measurement, training, Python, network or publication.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { performance } = require('node:perf_hooks');
const { setImmediate: tick } = require('node:timers/promises');
const { createRuntime } = require('./runtime.cjs');
const { SHAS, cloneState, hash, loadIdentity } = require('./identity.cjs');
loadIdentity();
const f = require('../multimap/features.cjs');
const teacher = require('../multimap/teacher_v2.cjs');
const wrapper = require('../../engine/dist/wrapper.js');
const originalAtomic = f.E.moveAI,
    originalWrapper = wrapper.moveAI;
const wrapperFile = path.resolve(__dirname, '../../engine/dist/wrapper.js');
const originalWrapperHash = hash(fs.readFileSync(wrapperFile));
const exportManifestSha256 = '8dac4ba18002a38868920875f0201f54200ac1ae062c51da3d615b189ffad543';
const modelDirectory = path.resolve(__dirname, '../runs/serving-prototype-v1/onnx-final');
const config = (replica = 'replica1') => ({ replica, modelDirectory, exportManifestSha256 });

// The same bounded generator/namespace as serving_v1/fixtures.cjs. It is kept
// here rather than importing its old runtime-version guard, so these tests also
// run on the separately authenticated security-patched deployment Node version.
function makeFixtures() {
    const result = [];
    for (const [mi, map] of ['Germany', 'USA', 'France', 'UK & Ireland'].entries()) {
        for (const [ci, [variant, fastBid]] of [
            ['original', false],
            ['original', true],
            ['recharged', false],
            ['recharged', true],
        ].entries()) {
            const count = [2, 3, 4, 5, 6][(mi + ci) % 5];
            const g = f.E.setup(
                count,
                { map, variant, fastBid, showMoney: true },
                `pg-serving-prototype-v1:fixture:${mi}:${ci}`
            );
            const seen = new Set();
            for (let i = 0; i < 800 && !f.E.ended(g) && seen.size < 6; i++) {
                const player = g.currentPlayers[0],
                    legal = f.legal(g, player);
                const kind =
                    legal.length === 1
                        ? 'forced'
                        : legal.some((m) => m.name === 'ChoosePowerPlant')
                        ? 'nomination'
                        : legal.some((m) => m.name === 'Bid')
                        ? 'bid'
                        : g.phase;
                if (
                    g.newTurn !== false &&
                    ['forced', 'nomination', 'bid', 'Building', 'Resources', 'Bureaucracy'].includes(kind) &&
                    !seen.has(kind)
                ) {
                    seen.add(kind);
                    result.push({
                        id: `${mi}-${ci}-${kind}`,
                        map,
                        variant,
                        fastBid,
                        kind,
                        player,
                        state: cloneState(g),
                    });
                }
                f.E.move(g, cloneState(teacher.choose(g, player, legal, 'geographic').action), player);
            }
            for (const kind of ['nomination', 'bid', 'Building', 'Resources', 'Bureaucracy']) assert(seen.has(kind));
        }
    }
    assert.equal(result.length, 96);
    return result;
}
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
function deferred() {
    let resolve, reject;
    const promise = new Promise((yes, no) => {
        resolve = yes;
        reject = no;
    });
    return { promise, resolve, reject };
}
function fake(replica = 'replica1', handler = (request) => response(request), ready = Promise.resolve()) {
    return {
        replica,
        ready,
        closed: false,
        calls: [],
        closeCalls: 0,
        request(request) {
            this.calls.push(request);
            return handler(request, this.calls.length);
        },
        close() {
            this.closeCalls++;
            this.closed = true;
        },
    };
}
function useFake(t, options = {}) {
    const worker = options.worker || fake(options.replica);
    const rows = [];
    let constructions = 0;
    const runtime = createRuntime(config(options.replica), {
        createTransport(settings) {
            constructions++;
            assert.equal(settings.startupMs, 2000);
            assert.equal(settings.timeoutMs, 1000);
            assert.equal(settings.maxPending, 8);
            return options.factory ? options.factory(settings) : worker;
        },
        onDiagnostic: options.onDiagnostic || ((row) => rows.push(row)),
    });
    t.after(() => runtime.close());
    return { runtime, worker, rows, constructions: () => constructions };
}
async function frozenClock(fn) {
    const old = Date.now,
        random = Math.random;
    Date.now = () => 1800000000123;
    // The ORIGINAL production heuristic samples Math.random; bind that test
    // environment too when comparing two independently generated fallback turns.
    Math.random = () => 0.4;
    try {
        return await fn();
    } finally {
        Date.now = old;
        Math.random = random;
    }
}
function movesFor(state, player, heuristic = false) {
    const g = cloneState(state),
        moves = [];
    for (let i = 0; i < 128; i++) {
        if (heuristic) {
            f.E.moveAI(g, player);
            const last = g.players[player].lastMove;
            moves.push(cloneState({ name: last.name, data: last.data }));
        } else {
            const action = teacher.choose(g, player, f.legal(g, player), 'geographic').action;
            moves.push(cloneState(action));
            f.E.move(g, cloneState(action), player);
        }
        if (g.newTurn !== false) return moves;
    }
    assert.fail('Engineering turn exceeded its bound');
}
async function expected(state, player, heuristic = false) {
    return cloneState(await wrapper.move(cloneState(state), movesFor(state, player, heuristic), player));
}
function complete(rows) {
    return rows.filter((row) => row.event === 'turn-complete').at(-1);
}
function unchanged(state, before) {
    assert.equal(JSON.stringify(state), before);
}

test('explicit replica/config only, no implicit winner or per-state config', async (t) => {
    for (const invalid of [
        undefined,
        {},
        { ...config(), replica: undefined },
        { ...config(), replica: 'winner' },
        { ...config(), replica: 'replica3' },
        { ...config(), modelDirectory: '' },
        { ...config(), modelDirectory: '../models' },
        { ...config(), exportManifestSha256: 'bad' },
        { ...config(), startupMs: 1 },
    ])
        assert.throws(() => createRuntime(invalid), /runtime-config/);
    assert.throws(() => createRuntime(config(), { createTransport: true }), /runtime-options/);
    for (const replica of ['replica1', 'replica2']) {
        const h = useFake(t, { replica });
        assert.equal(h.runtime.getStatus().state, 'idle');
        assert.equal(h.constructions(), 0);
        await h.runtime.moveAI(nomination.state, nomination.player);
        assert.equal(h.runtime.getStatus().replica, replica);
        assert(h.worker.calls.length > 0);
        assert(h.worker.calls.every((r) => r.replica === replica));
    }
});

test('all 96 targeted positions: full turn, exact wrapper result, replay, clocks and increments; no new game fields', async (t) => {
    const h = useFake(t);
    await frozenClock(async () => {
        for (const fixture of fixtures) {
            const before = JSON.stringify(fixture.state);
            const saved = await h.runtime.moveAI(fixture.state, fixture.player);
            assert.deepEqual(saved, await expected(fixture.state, fixture.player), fixture.id);
            assert.notEqual(saved.newTurn, false);
            assert.notEqual(wrapper.toSave(saved), undefined);
            assert.equal(complete(h.rows).fallback, false, fixture.id);
            assert.deepEqual(cloneState(wrapper.replay(cloneState(saved))), saved, fixture.id);
            assert.equal(
                wrapper.timeIncrements(saved)[fixture.player],
                wrapper.timeIncrements(fixture.state)[fixture.player] + 1
            );
            const added = [...saved.log, ...(saved.hiddenLog || [])].filter(
                (entry) => entry.type === 'move' && entry.move.serverTime === Date.now()
            );
            assert(added.length > 0);
            unchanged(fixture.state, before);
        }
    });
    assert.equal(h.constructions(), 1);
    assert.equal(h.runtime.getStatus().activeCalls, 0);
});

test('coalesced lazy startup across concurrent isolated games; no host identity, CAS or cross-call deduplication', async (t) => {
    const gate = deferred(),
        worker = fake('replica1', (r) => response(r), gate.promise);
    const h = useFake(t, { worker });
    const cases = fixtures.filter((x) => x.kind === 'nomination').slice(0, 4);
    const states = cases.map((x) => cloneState(x.state)),
        before = states.map((s) => JSON.stringify(s));
    await frozenClock(async () => {
        const pending = states.map((state, i) => h.runtime.moveAI(state, cases[i].player));
        await tick();
        assert.equal(h.constructions(), 1);
        assert.equal(h.runtime.getStatus().state, 'starting');
        assert.equal(h.runtime.getStatus().activeCalls, 4);
        assert.equal(worker.calls.length, 0);
        gate.resolve();
        const results = await Promise.all(pending);
        for (const [i, result] of results.entries()) {
            assert.deepEqual(result, await expected(cases[i].state, cases[i].player));
            unchanged(states[i], before[i]);
        }
        const calls = worker.calls.length;
        const a = await h.runtime.moveAI(nomination.state, nomination.player);
        const b = await h.runtime.moveAI(nomination.state, nomination.player);
        assert.notStrictEqual(a, b);
        assert.deepEqual(a, b);
        assert(worker.calls.length > calls + 1); // Same G/player is an independent proposal, not a receipt.
        assert.equal(new Set(worker.calls.map((r) => r.requestId)).size, worker.calls.length);
    });
    assert.equal(h.runtime.getStatus().activeCalls, 0);
});

test('max eight active calls, immediate overload rejection, slots released on completion', async (t) => {
    const gate = deferred(),
        h = useFake(t, { worker: fake('replica1', (r) => response(r), gate.promise) });
    const pending = Array.from({ length: 8 }, () => h.runtime.moveAI(nomination.state, nomination.player));
    await assert.rejects(h.runtime.moveAI(nomination.state, nomination.player), /runtime-busy/);
    assert.equal(h.runtime.getStatus().activeCalls, 8);
    gate.resolve();
    await Promise.all(pending);
    assert.equal(h.runtime.getStatus().activeCalls, 0);
    assert.equal(h.constructions(), 1);
});

test('input is detached before awaiting startup, caller changes are neither overwritten nor incorporated', async (t) => {
    const gate = deferred(),
        h = useFake(t, { worker: fake('replica1', (r) => response(r), gate.promise) });
    await frozenClock(async () => {
        const state = cloneState(nomination.state);
        const promise = h.runtime.moveAI(state, nomination.player);
        state.players[nomination.player].money++;
        const changed = JSON.stringify(state);
        gate.resolve();
        assert.deepEqual(await promise, await expected(nomination.state, nomination.player));
        unchanged(state, changed);
    });
});

test('malformed, inactive, ended and tentative inputs reject before factory or model diagnostics', async (t) => {
    const h = useFake(t);
    const cases = [
        null,
        {},
        { ...nomination.state, newTurn: false },
        { ...nomination.state, phase: f.E.Phase.GameEnd },
        { ...nomination.state, phase: 'unknown-phase' },
        { ...nomination.state, currentPlayers: [] },
        { ...nomination.state, map: null },
    ];
    const noMenu = cloneState(nomination.state);
    noMenu.players[nomination.player].availableMoves = { Bid: 'malformed' };
    cases.push(noMenu);
    const badNumbers = cloneState(nomination.state);
    badNumbers.players[nomination.player].money = Infinity;
    cases.push(badNumbers);
    const badShape = cloneState(nomination.state);
    delete badShape.map.cities;
    cases.push(badShape);
    for (const state of cases)
        await assert.rejects(h.runtime.moveAI(state, nomination.player), /runtime-(invalid|inactive)-state/);
    for (const player of [-1, 99, '0', NaN])
        await assert.rejects(h.runtime.moveAI(nomination.state, player), /runtime-inactive-state/);
    assert.equal(h.constructions(), 0);
    assert.deepEqual(h.rows, []);
    assert.equal(h.runtime.getStatus().state, 'idle');
    assert.equal(h.runtime.getStatus().activeCalls, 0);
});

test('unsupported scope uses original whole-turn heuristic without loading a worker', async (t) => {
    const h = useFake(t, {
        factory() {
            assert.fail('Unsupported scope must not initialize');
        },
    });
    await frozenClock(async () => {
        for (const option of [{ showMoney: false }, { chooseRegions: true }, { endPlantDiscountAtStep3: true }]) {
            const state = cloneState(nomination.state);
            Object.assign(state.options, option);
            const before = JSON.stringify(state);
            assert.deepEqual(
                await h.runtime.moveAI(state, nomination.player),
                await expected(state, nomination.player, true)
            );
            assert.equal(complete(h.rows).reason, 'unsupported-scope');
            assert(complete(h.rows).counts.heuristicFallback > 0);
            unchanged(state, before);
        }
    });
    assert.equal(h.constructions(), 0);
    assert.equal(h.runtime.getStatus().state, 'idle');
});

test('fixed-v2 Resources/Bureaucracy do not initialize ONNX, even while circuit fallback is observable', async (t) => {
    const h = useFake(t, {
        factory() {
            throw Error('unavailable');
        },
    });
    const positions = ['Resources', 'Bureaucracy'].map((kind) => fixtures.find((x) => x.kind === kind));
    for (const fixture of positions) await h.runtime.moveAI(fixture.state, fixture.player);
    assert.equal(h.constructions(), 0);
    await h.runtime.moveAI(nomination.state, nomination.player);
    assert.equal(h.runtime.getStatus().state, 'fallback');
    for (const fixture of positions) {
        await h.runtime.moveAI(fixture.state, fixture.player);
        assert.equal(complete(h.rows).fallback, false);
        assert(complete(h.rows).counts.fixedV2 > 0);
        assert.equal(complete(h.rows).state, 'fallback');
    }
    assert.equal(h.constructions(), 1);
});

for (const mode of ['constructor-throw', 'factory-reject', 'ready-reject', 'factory-hang', 'ready-hang']) {
    test(`${mode}: bounded startup, sanitized sticky circuit and whole-turn heuristic fallback`, async (t) => {
        const h = useFake(t, {
            factory() {
                if (mode === 'constructor-throw') throw Error('PRIVATE-ERROR');
                if (mode === 'factory-reject') return Promise.reject(Error('PRIVATE-ERROR'));
                if (mode === 'factory-hang') return new Promise(() => {});
                const worker = fake(
                    'replica1',
                    () => assert.fail('unready request'),
                    mode === 'ready-hang' ? new Promise(() => {}) : Promise.reject(Error('PRIVATE-ERROR'))
                );
                worker.close = () => {
                    throw Error('PRIVATE-CLEANUP');
                };
                return worker;
            },
        });
        const before = JSON.stringify(nomination.state),
            started = performance.now();
        await frozenClock(async () => {
            assert.deepEqual(
                await h.runtime.moveAI(nomination.state, nomination.player),
                await expected(nomination.state, nomination.player, true)
            );
        });
        const elapsed = performance.now() - started;
        assert(elapsed < 4500, `Startup exceeded engineering budget: ${Math.round(elapsed)}ms`);
        if (mode.endsWith('hang')) assert(elapsed >= 1900);
        assert.equal(h.runtime.getStatus().state, 'fallback');
        assert.equal(h.runtime.getStatus().circuitReason, mode.endsWith('hang') ? 'startup-timeout' : 'startup-failed');
        assert(complete(h.rows).fallback);
        assert.equal(complete(h.rows).counts.learned, 0);
        await h.runtime.moveAI(nomination.state, nomination.player);
        assert.equal(h.constructions(), 1);
        assert.equal(h.rows.filter((r) => r.event === 'circuit-open').length, 1);
        assert(!JSON.stringify(h.rows).includes('PRIVATE'));
        unchanged(nomination.state, before);
    });
}

test('partially learned turn is discarded on invalid response; poisoned transport is never respawned', async (t) => {
    const h = useFake(t, {
        worker: fake('replica1', (r, count) => (count === 1 ? response(r, 0) : { ...response(r), index: -1 })),
    });
    await frozenClock(async () => {
        assert.deepEqual(
            await h.runtime.moveAI(building.state, building.player),
            await expected(building.state, building.player, true)
        );
    });
    assert(h.worker.calls.length >= 2);
    assert(h.worker.closed);
    assert.equal(complete(h.rows).counts.learned, 0);
    assert(complete(h.rows).counts.heuristicFallback > 0);
    const calls = h.worker.calls.length;
    await h.runtime.moveAI(nomination.state, nomination.player);
    assert.equal(h.worker.calls.length, calls);
    assert.equal(h.constructions(), 1);
});

test('inference hang falls back within budget; late response and rejecting cleanup cannot revive worker', async (t) => {
    const gate = deferred();
    const worker = fake('replica1', () => gate.promise);
    worker.close = () => {
        worker.closed = true;
        return Promise.reject(Error('PRIVATE-CLEANUP'));
    };
    const h = useFake(t, { worker });
    const before = JSON.stringify(nomination.state),
        started = performance.now();
    const result = await h.runtime.moveAI(nomination.state, nomination.player);
    assert(performance.now() - started < 3000);
    assert.notEqual(result.newTurn, false);
    assert.equal(h.runtime.getStatus().state, 'fallback');
    assert.equal(h.runtime.getStatus().circuitReason, 'inference-timeout');
    assert.equal(complete(h.rows).counts.learned, 0);
    gate.resolve(response(worker.calls[0]));
    await tick();
    await h.runtime.moveAI(nomination.state, nomination.player);
    assert.equal(worker.calls.length, 1);
    assert.equal(h.constructions(), 1);
    unchanged(nomination.state, before);
});

test('worker fatal between calls poisons shared instance; requests fail together without respawn', async (t) => {
    const h = useFake(t);
    await h.runtime.moveAI(nomination.state, nomination.player);
    h.worker.closed = true;
    assert.equal(h.runtime.getStatus().state, 'fallback');
    const calls = h.worker.calls.length;
    await Promise.all([
        h.runtime.moveAI(nomination.state, nomination.player),
        h.runtime.moveAI(building.state, building.player),
    ]);
    assert.equal(h.worker.calls.length, calls);
    assert.equal(h.constructions(), 1);
    assert(
        h.rows
            .filter((r) => r.event === 'turn-complete')
            .slice(-2)
            .every((r) => r.fallback)
    );
});

test('diagnostics contain no raw input/error details; callback throws/rejections cannot break commit', async (t) => {
    const worker = fake('replica1', () => {
        throw Object.assign(Error('PRIVATE-STACK'), { code: 'PRIVATE-CODE' });
    });
    const h = useFake(t, { worker });
    const state = cloneState(nomination.state);
    state.players[nomination.player].name = 'PRIVATE-NAME';
    state.seed = 'PRIVATE-SEED';
    await h.runtime.moveAI(state, nomination.player);
    const output = JSON.stringify([h.rows, h.runtime.getStatus()]);
    for (const forbidden of ['PRIVATE', 'observation', 'requestId', 'gameId', 'player', 'moves', modelDirectory])
        assert(!output.includes(forbidden));
    assert(Object.isFrozen(h.runtime.getStatus()));
    for (const callback of [
        () => {
            throw Error('PRIVATE-CALLBACK');
        },
        () => Promise.reject(Error('PRIVATE-CALLBACK')),
    ]) {
        const other = useFake(t, { onDiagnostic: callback });
        assert.notEqual((await other.runtime.moveAI(nomination.state, nomination.player)).newTurn, false);
    }
    await tick();
});

test('close is terminal/idempotent before startup and never implicitly restarts', async (t) => {
    const h = useFake(t);
    h.runtime.close();
    h.runtime.close();
    assert.equal(h.runtime.getStatus().state, 'closed');
    await assert.rejects(h.runtime.moveAI(nomination.state, nomination.player), /runtime-closed/);
    assert.equal(h.constructions(), 0);
    assert.equal(h.rows.filter((r) => r.event === 'closed').length, 1);
});

test('close before the factory microtask prevents even a queued startup from constructing a worker', async (t) => {
    const h = useFake(t);
    const pending = h.runtime.moveAI(nomination.state, nomination.player);
    h.runtime.close();
    await assert.rejects(pending, /runtime-closed/);
    assert.equal(h.constructions(), 0);
    assert.equal(h.runtime.getStatus().activeCalls, 0);
});

test('close during startup rejects promptly, disposes a late-created worker and never applies', async (t) => {
    const gate = deferred(),
        h = useFake(t, { factory: () => gate.promise });
    const before = JSON.stringify(nomination.state);
    const pending = h.runtime.moveAI(nomination.state, nomination.player);
    await tick();
    h.runtime.close();
    await assert.rejects(pending, /runtime-closed/);
    const late = fake();
    gate.resolve(late);
    await tick();
    assert(late.closed);
    assert.equal(late.calls.length, 0);
    assert.equal(h.runtime.getStatus().activeCalls, 0);
    assert(!complete(h.rows));
    unchanged(nomination.state, before);
});

test('close in-flight rejects without applying late learned output or mutating caller state', async (t) => {
    const gate = deferred(),
        h = useFake(t, { worker: fake('replica1', () => gate.promise) });
    const before = JSON.stringify(nomination.state);
    const pending = h.runtime.moveAI(nomination.state, nomination.player);
    await tick();
    assert.equal(h.worker.calls.length, 1);
    h.runtime.close();
    await assert.rejects(pending, /runtime-closed/);
    gate.resolve(response(h.worker.calls[0]));
    await tick();
    assert.equal(h.runtime.getStatus().state, 'closed');
    assert.equal(h.runtime.getStatus().activeCalls, 0);
    assert(!complete(h.rows));
    unchanged(nomination.state, before);
});

test('wrapper auto-pass and premoves remain authoritative after one manual committed turn', async (t) => {
    const h = useFake(t);
    await frozenClock(async () => {
        // Deliberately targeted engineering state: other bidders cannot afford a plant.
        const auction = cloneState(nomination.state);
        auction.players.forEach((p, i) => {
            if (i !== nomination.player) p.money = 0;
        });
        const auto = await h.runtime.moveAI(auction, nomination.player);
        assert.deepEqual(auto, await expected(auction, nomination.player));
        assert(wrapper.timeIncrements(auto).some((count, seat) => seat !== nomination.player && count > 0));
        const nextPlayer = building.state.players.find((p) => p.id !== building.player).id;
        const queued = await wrapper.move(
            cloneState(building.state),
            {
                type: 'premoves',
                requestId: 'engineering-premove',
                round: building.state.round,
                revision: 0,
                phases: [{ phase: 'Building', moves: [{ name: 'Pass', data: true }] }],
            },
            nextPlayer
        );
        const before = JSON.stringify(queued);
        const saved = await h.runtime.moveAI(queued, building.player);
        assert.deepEqual(saved, await expected(queued, building.player));
        assert.equal(wrapper.timeIncrements(saved)[building.player], 1);
        assert.equal(wrapper.timeIncrements(saved)[nextPlayer], 1);
        assert.deepEqual(cloneState(wrapper.replay(cloneState(saved))), saved);
        unchanged(queued, before);
    });
});

test('core source identity failure fails closed rather than becoming model fallback', async (t) => {
    const h = useFake(t);
    const originalRead = fs.readFileSync;
    let tamperedReads = 0;
    fs.readFileSync = function (name, ...args) {
        const bytes = originalRead.call(this, name, ...args);
        if (typeof name === 'string' && path.resolve(name) === wrapperFile) {
            tamperedReads++;
            return Buffer.concat([Buffer.from(bytes), Buffer.from('\n// simulated damage\n')]);
        }
        return bytes;
    };
    try {
        assert.throws(() => createRuntime(config()), /runtime-source-identity/);
        await assert.rejects(h.runtime.moveAI(nomination.state, nomination.player), /runtime-source-identity/);
    } finally {
        fs.readFileSync = originalRead;
    }
    assert(tamperedReads > 0);
    assert.equal(h.constructions(), 0);
    assert.deepEqual(h.rows, []);
});

for (const point of ['startup-failure', 'after-inference']) {
    test(`core corruption ${point} fails closed without a model-fallback or committed event`, async (t) => {
        let damaged = false;
        const worker = fake('replica1', (request) => {
            damaged = true;
            return response(request);
        });
        const h = useFake(
            t,
            point === 'startup-failure'
                ? {
                      factory() {
                          damaged = true;
                          throw Error('simulated-startup-failure');
                      },
                  }
                : { worker }
        );
        const originalRead = fs.readFileSync;
        const before = JSON.stringify(nomination.state);
        fs.readFileSync = function (name, ...args) {
            const bytes = originalRead.call(this, name, ...args);
            if (damaged && typeof name === 'string' && path.resolve(name) === wrapperFile)
                return Buffer.concat([Buffer.from(bytes), Buffer.from('\n// simulated damage\n')]);
            return bytes;
        };
        try {
            await assert.rejects(h.runtime.moveAI(nomination.state, nomination.player), /runtime-source-identity/);
        } finally {
            fs.readFileSync = originalRead;
        }
        assert(damaged);
        assert.equal(h.runtime.getStatus().activeCalls, 0);
        assert.equal(h.runtime.getStatus().circuitReason, null);
        assert.deepEqual(h.rows, []);
        unchanged(nomination.state, before);
        if (point === 'after-inference') assert(worker.calls.length > 0);
    });
}

let realUnavailable = null;
try {
    for (const name of ['export-manifest.json', 'replica1.onnx', 'replica2.onnx'])
        fs.accessSync(path.join(modelDirectory, name));
    require.resolve('onnxruntime-node', { paths: [__dirname] });
} catch (_) {
    realUnavailable = 'Optional local final ONNX bundle/native dependency absent (no installation or export performed)';
}

for (const replica of ['replica1', 'replica2']) {
    test(
        `optional real final ONNX ${replica}: selected nomination/Building turns and replay`,
        { skip: realUnavailable || false },
        async (t) => {
            assert.equal(
                hash(fs.readFileSync(path.join(modelDirectory, 'export-manifest.json'))),
                exportManifestSha256
            );
            const rows = [],
                runtime = createRuntime(config(replica), { onDiagnostic: (row) => rows.push(row) });
            t.after(() => runtime.close());
            for (const fixture of [nomination, building]) {
                const before = JSON.stringify(fixture.state),
                    started = performance.now();
                const saved = await runtime.moveAI(fixture.state, fixture.player);
                assert(performance.now() - started < 9000);
                assert.equal(runtime.getStatus().state, 'ready');
                assert.equal(complete(rows).fallback, false);
                assert(complete(rows).counts.learned > 0);
                assert.notEqual(wrapper.toSave(saved), undefined);
                assert.deepEqual(cloneState(wrapper.replay(cloneState(saved))), saved);
                unchanged(fixture.state, before);
            }
        }
    );
}

test(
    'optional real startup validates missing model directory and pinned export digest before inference',
    { skip: realUnavailable || false },
    async (t) => {
        for (const settings of [
            { ...config(), modelDirectory: path.join(modelDirectory, 'missing') },
            { ...config(), exportManifestSha256: '0'.repeat(64) },
        ]) {
            const rows = [],
                runtime = createRuntime(settings, { onDiagnostic: (r) => rows.push(r) });
            t.after(() => runtime.close());
            await frozenClock(async () => {
                assert.deepEqual(
                    await runtime.moveAI(nomination.state, nomination.player),
                    await expected(nomination.state, nomination.player, true)
                );
            });
            assert.equal(runtime.getStatus().state, 'fallback');
            assert.equal(complete(rows).counts.learned, 0);
        }
    }
);

test('original atomic/wrapper moveAI exports and wrapper source are unchanged', () => {
    assert.strictEqual(f.E.moveAI, originalAtomic);
    assert.strictEqual(wrapper.moveAI, originalWrapper);
    assert.equal(hash(fs.readFileSync(wrapperFile)), originalWrapperHash);
    loadIdentity();
});
