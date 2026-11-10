'use strict';
// Trusted local host API, not an HTTP endpoint or a replacement for the BGS wrapper.
const { randomBytes } = require('node:crypto');
const { performance } = require('node:perf_hooks');
const { scheduleDeadline } = require('./deadline.cjs');
const { SHAS, loadIdentity, cloneState, canonical, hash, freeze, requireThat } = require('./identity.cjs');
loadIdentity(); // Authenticate frozen inputs before importing them.
const f = require('../multimap/features.cjs');
const teacher = require('../multimap/teacher_v2.cjs');
const { inputs } = require('../multimap/expert_game.cjs');
const { atomicIndex } = require('../multimap/reference_game.cjs');
const wrapper = require('../../engine/dist/wrapper.js');
const MAPS = ['Germany', 'USA', 'France', 'UK & Ireland'];
const PHASES = ['Auction', 'Resources', 'Building', 'Bureaucracy'];
const optionKeys = [
    'map',
    'variant',
    'fastBid',
    'showMoney',
    'useNewRechargedSetup',
    'trackTotalSpent',
    'chooseRegions',
    'chooseColors',
    'randomizeMap',
    'alternatePowerPlants',
    'endPlantDiscountAtStep3',
    'rechargedStartingResources',
];
function supported(g) {
    const o = g.options;
    return (
        MAPS.includes(g.map.name) &&
        o.map === g.map.name &&
        ['original', 'recharged'].includes(o.variant) &&
        g.players.length >= 2 &&
        g.players.length <= 6 &&
        PHASES.includes(g.phase) &&
        typeof o.fastBid === 'boolean' &&
        o.showMoney === true &&
        o.useNewRechargedSetup === true &&
        o.trackTotalSpent === true &&
        Object.keys(o).every((key) => optionKeys.includes(key)) &&
        ['chooseRegions', 'chooseColors', 'randomizeMap', 'alternatePowerPlants', 'endPlantDiscountAtStep3'].every(
            (key) => o[key] === undefined || o[key] === false
        ) &&
        (o.map === 'France' && o.variant === 'recharged'
            ? o.rechargedStartingResources === true
            : o.rechargedStartingResources === undefined || o.rechargedStartingResources === false)
    );
}
function stateHash(state) {
    return hash(canonical(state));
}
function requestKey(gameId, revision, player) {
    requireThat(
        typeof gameId === 'string' &&
            /^[a-zA-Z0-9_-]{1,80}$/.test(gameId) &&
            Number.isSafeInteger(revision) &&
            revision >= 0 &&
            Number.isSafeInteger(player) &&
            player >= 0,
        'host-request'
    );
    return `${gameId}:${revision}:${player}`;
}
function active(g, player) {
    requireThat(
        g.newTurn !== false && !f.E.ended(g) && g.currentPlayers.includes(player) && g.players[player],
        'inactive-or-tentative'
    );
}
function menu(g, player) {
    const result = Object.entries(g.players[player].availableMoves || {}).flatMap(([name, items]) =>
        (items || []).map((data) => ({ name, data }))
    );
    requireThat(result.length > 0, 'empty-menu');
    return result;
}
function checkResponse(response, request) {
    // Kept at the authoritative action boundary, independently of the backend implementation.
    const { exactKeys } = require('./identity.cjs');
    requireThat(
        exactKeys(response, ['schema', 'requestId', 'replica', 'checkpointSha256', 'index', 'actionCount']) &&
            response.schema === 'pg-replica-serving-response-v1' &&
            response.requestId === request.requestId &&
            response.replica === request.replica &&
            response.checkpointSha256 === SHAS[request.replica] &&
            response.actionCount === request.observation.actions.length &&
            Number.isSafeInteger(response.index) &&
            response.index >= 0 &&
            response.index < response.actionCount,
        'invalid-response'
    );
    return response.index;
}
function deadlineRequest(transport, request, milliseconds) {
    return new Promise((resolve, reject) => {
        const deadline = performance.now() + milliseconds;
        function expired() {
            // Deadline settlement must never depend on cleanup succeeding or completing.
            reject(Object.assign(new Error('inference-timeout'), { code: 'inference-timeout' }));
            try {
                Promise.resolve(transport.close?.()).catch(() => {});
            } catch (_) {
                /* best-effort cleanup */
            }
        }
        const timer = scheduleDeadline(deadline, expired);
        Promise.resolve()
            .then(() => transport.request(request, { timeoutMs: milliseconds }))
            .then((response) => {
                if (performance.now() >= deadline) expired();
                else resolve(response);
            }, reject)
            .finally(() => timer.cancel());
    });
}
class ReplicaBot {
    #replica;
    #transport;
    #limits;
    #pending = new Map();
    #cache = new Map();
    #authority = new WeakMap();
    constructor({ replica, transport, turnMs = 3000, inferenceMs = 1000, fallbackMs = 1000, maxActions = 128 }) {
        requireThat(
            Object.hasOwn(SHAS, replica) &&
                transport &&
                typeof transport.request === 'function' &&
                transport.replica === replica,
            'bot-config'
        );
        requireThat(
            [turnMs, inferenceMs, fallbackMs].every((v) => Number.isSafeInteger(v) && v >= 10 && v <= 5000) &&
                Number.isSafeInteger(maxActions) &&
                maxActions >= 1 &&
                maxActions <= 500,
            'bot-limits'
        );
        this.#replica = replica;
        this.#transport = transport;
        this.#limits = { turnMs, inferenceMs, fallbackMs, maxActions };
    }
    get replica() {
        return this.#replica;
    }
    planTurn({ gameId, revision, player, state }) {
        const key = requestKey(gameId, revision, player),
            base = cloneState(state),
            fingerprint = stateHash(base);
        active(base, player);
        const old = this.#pending.get(key) || this.#cache.get(key);
        if (old) {
            requireThat(old.fingerprint === fingerprint, 'revision-state-conflict');
            return old.promise;
        }
        requireThat(this.#pending.size < 8, 'bot-queue-full');
        const entry = { fingerprint };
        entry.promise = this.#plan(base, { gameId, revision, player, fingerprint })
            .then((plan) => {
                this.#cache.set(key, entry);
                if (this.#cache.size > 64) this.#cache.delete(this.#cache.keys().next().value);
                return plan;
            })
            .finally(() => this.#pending.delete(key));
        this.#pending.set(key, entry);
        return entry.promise;
    }
    async #plan(base, identity) {
        const start = performance.now();
        let moves,
            counts,
            reason = null;
        try {
            requireThat(supported(base), 'unsupported-scope');
            ({ moves, counts } = await this.#build(base, identity.player, false));
        } catch (error) {
            // No error messages/raw states are exposed. Discard ALL speculative learned moves.
            reason = [
                'unsupported-scope',
                'inference-timeout',
                'invalid-response',
                'turn-cap',
                'turn-timeout',
            ].includes(error.code)
                ? error.code
                : 'inference-or-planning-failed';
            ({ moves, counts } = await this.#build(base, identity.player, true));
        }
        const plan = freeze({
            schema: 'pg-replica-turn-plan-v1',
            gameId: identity.gameId,
            revision: identity.revision,
            player: identity.player,
            replica: this.#replica,
            checkpointSha256: SHAS[this.#replica],
            moves: cloneState(moves),
            diagnostics: { fallback: reason !== null, reason, counts, planningMs: performance.now() - start },
        });
        this.#authority.set(plan, { ...identity, moves: cloneState(moves) });
        return plan;
    }
    async #build(base, player, fallback) {
        let g = cloneState(base);
        const moves = [],
            counts = { learned: 0, fixedV2: 0, heuristicFallback: 0 };
        const until = performance.now() + (fallback ? this.#limits.fallbackMs : this.#limits.turnMs);
        for (let i = 0; i < this.#limits.maxActions; i++) {
            requireThat(performance.now() < until, 'turn-timeout');
            requireThat(!f.E.ended(g) && g.currentPlayers.includes(player), 'turn-boundary');
            const legal = fallback ? menu(g, player) : f.legal(g, player);
            let selected;
            if (fallback) {
                // Unchanged production ATOMIC heuristic. Unlike wrapper.moveAI's safety net, never force-commit.
                g = f.E.moveAI(g, player);
                const last = g.players[player].lastMove;
                selected = legal[atomicIndex(legal, { name: last.name, data: last.data })];
                counts.heuristicFallback++;
            } else {
                let index;
                if (legal.length > 1 && ['Auction', 'Building'].includes(g.phase)) {
                    const menuHash = stateHash(legal),
                        observation = inputs(g, player);
                    requireThat(observation.actions.length === legal.length, 'menu-shape');
                    const request = freeze({
                        schema: 'pg-replica-serving-request-v1',
                        requestId: randomBytes(32).toString('hex'),
                        replica: this.#replica,
                        observation,
                    });
                    const remaining = Math.min(this.#limits.inferenceMs, until - performance.now());
                    requireThat(remaining > 0, 'turn-timeout');
                    const response = await deadlineRequest(this.#transport, request, remaining);
                    index = checkResponse(response, request);
                    requireThat(stateHash(f.legal(g, player)) === menuHash, 'menu-changed');
                    counts.learned++;
                } else {
                    index = legal.length === 1 ? 0 : teacher.choose(g, player, legal, 'geographic').index;
                    counts.fixedV2++;
                }
                selected = legal[index];
                atomicIndex(f.legal(g, player), selected);
                g = f.E.move(g, cloneState(selected), player);
            }
            moves.push(cloneState(selected));
            requireThat(performance.now() < until, 'turn-timeout');
            if (g.newTurn !== false) return { moves, counts };
        }
        requireThat(false, 'turn-cap');
    }
    async applyPlan({ gameId, revision, state }, plan) {
        const authority = this.#authority.get(plan);
        const base = cloneState(state);
        requireThat(
            authority &&
                authority.gameId === gameId &&
                authority.revision === revision &&
                authority.fingerprint === stateHash(base),
            'stale-or-untrusted-plan'
        );
        active(base, authority.player);
        // This returns a proposal. Only the host's CAS below persists it.
        const next = await wrapper.move(base, cloneState(authority.moves), authority.player);
        requireThat(wrapper.toSave(next) !== undefined, 'uncommitted-plan');
        return cloneState(next);
    }
}
class MemoryHost {
    #games = new Map();
    #pending = new Map();
    #receipts = new Map();
    add(gameId, state, revision = 0) {
        requestKey(gameId, revision, 0);
        requireThat(!this.#games.has(gameId) && this.#games.size < 64 && state.newTurn !== false, 'host-add');
        this.#games.set(gameId, { state: cloneState(state), revision });
    }
    snapshot(gameId) {
        const row = this.#games.get(gameId);
        requireThat(row, 'unknown-game');
        return cloneState({ gameId, ...row });
    }
    replace(gameId, state, expectedRevision) {
        const row = this.#games.get(gameId);
        requireThat(
            row &&
                row.revision === expectedRevision &&
                state.newTurn !== false &&
                row.revision < Number.MAX_SAFE_INTEGER,
            'stale-replacement'
        );
        this.#games.set(gameId, { state: cloneState(state), revision: row.revision + 1 });
        return this.snapshot(gameId); // Undo also advances the revision; it never restores an old token.
    }
    play(bot, { gameId, revision, player }) {
        const baseKey = requestKey(gameId, revision, player),
            key = `${baseKey}:${bot.replica}`;
        if (this.#receipts.has(key)) return Promise.resolve(this.#receipts.get(key));
        if (this.#pending.has(key)) return this.#pending.get(key);
        const row = this.#games.get(gameId);
        requireThat(row && row.revision === revision && revision < Number.MAX_SAFE_INTEGER, 'stale-revision');
        requireThat(this.#pending.size < 8, 'host-queue-full');
        const promise = (async () => {
            const plan = await bot.planTurn({ gameId, revision, player, state: row.state });
            requireThat(this.#games.get(gameId) === row, 'stale-revision');
            const next = await bot.applyPlan({ gameId, revision, state: row.state }, plan);
            // Recheck AFTER every await. Simultaneous players may race, but cannot overwrite a newer state.
            requireThat(this.#games.get(gameId) === row, 'stale-revision');
            this.#games.set(gameId, { state: next, revision: revision + 1 });
            const receipt = freeze({
                schema: 'pg-replica-turn-receipt-v1',
                gameId,
                baseRevision: revision,
                revision: revision + 1,
                player,
                replica: bot.replica,
                moves: plan.moves,
                diagnostics: plan.diagnostics,
            });
            this.#receipts.set(key, receipt);
            if (this.#receipts.size > 64) this.#receipts.delete(this.#receipts.keys().next().value);
            return receipt;
        })().finally(() => this.#pending.delete(key));
        this.#pending.set(key, promise);
        return promise;
    }
}
module.exports = { ReplicaBot, MemoryHost, supported, checkResponse };
