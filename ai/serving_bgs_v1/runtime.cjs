'use strict';
// Private opt-in entry runtime. The artifact entry creates ONE instance, not one
// instance per request. This module never replaces either original moveAI export.
// G/player is the entire platform contract: locking, persistence and retries are
// the host's responsibility. Ephemeral plan bindings below are NOT host revisions,
// a durable cache, CAS, deduplication, or an exactly-once guarantee.
const path = require('node:path');
const { randomBytes } = require('node:crypto');
const { performance } = require('node:perf_hooks');
const { SHAS, cloneState, loadIdentity, exactKeys, canonical } = require('./identity.cjs');
const { scheduleDeadline } = require('./deadline.cjs');
const LIMITS = Object.freeze({ startupMs: 2000, inferenceMs: 1000, turnMs: 3000, fallbackMs: 1000, maxActiveCalls: 8 });
const error = (code) => Object.assign(new Error(code), { code });

function verifyCore() {
    // Fail CLOSED, outside all model-fallback catch blocks. The versioned Node
    // source guard authenticates the engine/runtime before imports or use.
    try {
        loadIdentity();
    } catch (_) {
        throw error('runtime-source-identity');
    }
}

function createRuntime(config, options = {}) {
    if (
        !exactKeys(config, ['replica', 'modelDirectory', 'exportManifestSha256']) ||
        !Object.hasOwn(SHAS, config.replica) ||
        typeof config.modelDirectory !== 'string' ||
        !config.modelDirectory.length ||
        config.modelDirectory.includes('\0') ||
        config.modelDirectory.split(/[\\/]/).includes('..') ||
        typeof config.exportManifestSha256 !== 'string' ||
        !/^[0-9a-f]{64}$/.test(config.exportManifestSha256)
    )
        throw error('runtime-config');
    if (
        !options ||
        typeof options !== 'object' ||
        Array.isArray(options) ||
        Object.keys(options).some((key) => !['createTransport', 'onDiagnostic'].includes(key)) ||
        (options.createTransport !== undefined && typeof options.createTransport !== 'function') ||
        (options.onDiagnostic !== undefined && typeof options.onDiagnostic !== 'function')
    )
        throw error('runtime-options');
    const checked = Object.freeze({ ...config, modelDirectory: path.resolve(config.modelDirectory) });
    verifyCore();
    const { ReplicaBot, supported, checkResponse } = require('./adapter.cjs');
    const { OnnxTransport, validateObservation } = require('./onnx.cjs');
    const { inputs } = require('../multimap/expert_game.cjs');
    const f = require('../multimap/features.cjs');
    // A trusted engineering-test seam, never an option accepted from game state.
    const createTransport = options.createTransport || ((settings) => new OnnxTransport(settings));
    const onDiagnostic = options.onDiagnostic;
    let phase = 'idle',
        circuitReason = null,
        closed = false,
        activeCalls = 0;
    let transport = null,
        initialization = null;
    const waiters = new Set();

    function diagnostic(event, details = {}) {
        // Only our fixed vocabulary and adapter's fixed numeric counters leave.
        // Never include state, player, call/request IDs, moves, tensors, paths,
        // library output, arbitrary error codes, messages or stacks.
        if (!onDiagnostic) return;
        const row = Object.freeze({
            schema: 'pg-replica-bgs-diagnostic-v1',
            event,
            replica: checked.replica,
            state: phase,
            circuitReason,
            ...details,
        });
        try {
            Promise.resolve(onDiagnostic(row)).catch(() => {});
        } catch (_) {
            /* Observability cannot break a committed proposal. */
        }
    }
    function dispose(value) {
        try {
            Promise.resolve(value?.close?.()).catch(() => {});
        } catch (_) {
            /* Cleanup is best effort and never awaited on the turn path. */
        }
    }
    function stopWaiters(code) {
        for (const reject of [...waiters]) reject(error(code));
    }
    function trip(reason) {
        if (closed || circuitReason) return;
        circuitReason = reason;
        phase = 'fallback';
        const old = transport;
        transport = null;
        stopWaiters('runtime-unavailable');
        dispose(old);
        diagnostic('circuit-open');
    }
    function assertOpen() {
        if (closed) throw error('runtime-closed');
    }
    function wait(promise, milliseconds, timeoutCode) {
        // Both startup (including the factory) and inference are bounded even for
        // a broken test transport whose ready/request/close never settles. JS
        // timers cannot preempt synchronous engine work or blocked native calls.
        return new Promise((resolve, reject) => {
            const until = performance.now() + milliseconds;
            let settled = false;
            function finish(value, failed) {
                if (settled) return;
                settled = true;
                timer.cancel();
                waiters.delete(cancel);
                if (failed) reject(value);
                else resolve(value);
            }
            const cancel = (reason) => finish(reason, true);
            const timer = scheduleDeadline(until, () => cancel(error(timeoutCode)));
            waiters.add(cancel);
            Promise.resolve(promise).then((value) => {
                if (performance.now() >= until) cancel(error(timeoutCode));
                else finish(value, false);
            }, cancel);
            if (closed) cancel(error('runtime-closed'));
        });
    }
    const unavailable = Object.freeze({
        replica: checked.replica,
        closed: true,
        request() {
            return Promise.reject(error('runtime-unavailable'));
        },
        close() {},
    });
    const learned = Object.freeze({
        replica: checked.replica,
        get closed() {
            return closed || !!circuitReason || !!transport?.closed;
        },
        async request(request, { timeoutMs = LIMITS.inferenceMs } = {}) {
            assertOpen();
            if (circuitReason || !transport || transport.closed) {
                trip('worker-closed');
                throw error('runtime-unavailable');
            }
            const current = transport;
            try {
                const result = await wait(
                    Promise.resolve().then(() => {
                        assertOpen();
                        if (circuitReason) throw error('runtime-unavailable');
                        return current.request(request, { timeoutMs });
                    }),
                    Math.min(timeoutMs, LIMITS.inferenceMs),
                    'runtime-inference-timeout'
                );
                assertOpen();
                if (circuitReason || current.closed) throw error('runtime-unavailable');
                checkResponse(result, request); // Also poison malformed responses from a test transport.
                return result;
            } catch (cause) {
                trip(cause?.code === 'runtime-inference-timeout' ? 'inference-timeout' : 'inference-failed');
                throw error('runtime-unavailable');
            }
        },
        // ReplicaBot calls this when its independent inference deadline expires.
        close() {
            trip('inference-timeout');
        },
    });

    async function ready() {
        assertOpen();
        if (circuitReason) return unavailable;
        if (transport?.closed) {
            trip('worker-closed');
            return unavailable;
        }
        if (!initialization) {
            phase = 'starting';
            initialization = (async () => {
                let accepting = true;
                try {
                    const starting = Promise.resolve()
                        .then(() => {
                            assertOpen();
                            if (!accepting || circuitReason) throw error('runtime-unavailable');
                            return createTransport(
                                Object.freeze({
                                    ...checked,
                                    startupMs: LIMITS.startupMs,
                                    timeoutMs: LIMITS.inferenceMs,
                                    maxPending: LIMITS.maxActiveCalls,
                                })
                            );
                        })
                        .then(async (candidate) => {
                            if (!accepting || closed || circuitReason) {
                                dispose(candidate);
                                throw error('runtime-unavailable');
                            }
                            transport = candidate;
                            if (
                                !candidate ||
                                candidate.replica !== checked.replica ||
                                typeof candidate.request !== 'function' ||
                                typeof candidate.close !== 'function' ||
                                !candidate.ready ||
                                typeof candidate.ready.then !== 'function'
                            )
                                throw error('runtime-transport');
                            await candidate.ready;
                            if (!accepting || closed || circuitReason || candidate.closed)
                                throw error('runtime-unavailable');
                        });
                    await wait(starting, LIMITS.startupMs, 'runtime-startup-timeout');
                    assertOpen();
                    phase = 'ready';
                    return learned;
                } catch (cause) {
                    assertOpen();
                    // OnnxTransport/worker authenticate their own core sources.
                    // Do not relabel a broken engine/source inventory as a model
                    // failure, even if the worker only reported startup-failed.
                    verifyCore();
                    trip(cause?.code === 'runtime-startup-timeout' ? 'startup-timeout' : 'startup-failed');
                    return unavailable;
                } finally {
                    accepting = false;
                    if (closed || phase !== 'ready') {
                        dispose(transport);
                        transport = null;
                    }
                }
            })();
        }
        return initialization;
    }

    function validate(state, player) {
        let base, inScope;
        try {
            base = cloneState(state); // Detach before the first await, never mutate caller G.
            if (
                !base ||
                typeof base !== 'object' ||
                Array.isArray(base) ||
                !Array.isArray(base.players) ||
                base.players.length < 2 ||
                base.players.length > 6 ||
                !Array.isArray(base.currentPlayers) ||
                !base.map ||
                typeof base.map.name !== 'string' ||
                !base.options ||
                typeof base.options !== 'object' ||
                Array.isArray(base.options) ||
                !Object.values(f.E.Phase).includes(base.phase) ||
                !Array.isArray(base.log)
            )
                throw error('runtime-invalid-state');
            if (
                !Number.isSafeInteger(player) ||
                player < 0 ||
                !base.players[player] ||
                !base.currentPlayers.includes(player) ||
                base.newTurn === false ||
                f.E.ended(base)
            )
                throw error('runtime-inactive-state');
            const menu = base.players[player].availableMoves;
            if (
                !menu ||
                typeof menu !== 'object' ||
                Array.isArray(menu) ||
                Object.values(menu).some((items) => !Array.isArray(items)) ||
                !Object.values(menu).some((items) => items.length)
            )
                throw error('runtime-invalid-state');
            inScope = supported(base);
            if (inScope) {
                const legal = f.legal(base, player);
                // Reject malformed public observations BEFORE loading a worker;
                // such input errors are not a model-health/circuit event. Forced
                // menus still get feature/finite-number validation, even though
                // the inference tensor validator requires two or more actions.
                const observation = inputs(base, player);
                canonical(observation);
                if (legal.length > 1) validateObservation(observation);
            }
        } catch (cause) {
            throw error(cause?.code === 'runtime-inactive-state' ? 'runtime-inactive-state' : 'runtime-invalid-state');
        }
        return { base, inScope };
    }

    async function moveAI(state, player) {
        assertOpen();
        if (activeCalls >= LIMITS.maxActiveCalls) throw error('runtime-busy');
        activeCalls++;
        try {
            const { base, inScope } = validate(state, player);
            verifyCore();
            // Unsupported scopes go straight through ReplicaBot's original
            // heuristic fallback. Resources/Bureaucracy keep its fixed-v2 policy
            // without loading ONNX. A circuit is reported separately: fixed-v2
            // turns need not claim to have used the heuristic fallback.
            const backend = inScope && ['Auction', 'Building'].includes(base.phase) ? await ready() : unavailable;
            assertOpen();
            const bot = new ReplicaBot({
                replica: checked.replica,
                transport: backend,
                turnMs: LIMITS.turnMs,
                inferenceMs: LIMITS.inferenceMs,
                fallbackMs: LIMITS.fallbackMs,
            });
            const binding = { gameId: randomBytes(32).toString('hex'), revision: 0 };
            const plan = await bot.planTurn({ ...binding, state: base, player });
            assertOpen();
            verifyCore();
            // One authoritative wrapper.move on a private clone. It owns server
            // clocks, increments, auto-pass and premoves; never force a commit.
            const next = await bot.applyPlan({ ...binding, state: base }, plan);
            assertOpen();
            diagnostic('turn-complete', {
                fallback: plan.diagnostics.fallback,
                reason: plan.diagnostics.reason,
                counts: Object.freeze({ ...plan.diagnostics.counts }),
            });
            assertOpen();
            return next;
        } finally {
            activeCalls--;
            // No bot, binding, plan or authoritative G is put in a shared cache.
        }
    }
    function close() {
        if (closed) return;
        closed = true;
        phase = 'closed';
        stopWaiters('runtime-closed');
        const old = transport;
        transport = null;
        dispose(old);
        diagnostic('closed');
    }
    function getStatus() {
        if (!closed && transport?.closed) trip('worker-closed');
        return Object.freeze({ replica: checked.replica, state: phase, circuitReason, activeCalls, limits: LIMITS });
    }
    return Object.freeze({ moveAI, close, getStatus });
}

module.exports = { createRuntime };
