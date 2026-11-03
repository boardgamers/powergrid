// Evaluation-only population stress bridge. Frozen serving/training guards are unchanged.
// Only public tensors or the retained reference's scrubbed request leave Node.
const assert = require('node:assert/strict');
const { performance } = require('node:perf_hooks');
const f = require('./features.cjs');
const teacherV1 = require('./teacher.cjs');
const teacherV2 = require('./teacher_v2.cjs');
const { inputs: expertInputs } = require('./expert_game.cjs');
const { inputs: oldInputs } = require('./game_rl.cjs');
const { start, outcome } = require('./game.cjs');
const { ENGINE_VERSION, hiddenInvariant, atomicIndex } = require('./reference_game.cjs');

function freeze(value) {
    if (value && typeof value === 'object') {
        Object.values(value).forEach(freeze);
        Object.freeze(value);
    }
    return value;
}
const protocol = freeze(structuredClone(require('./stress-protocol-v1.json')));
const MAPS = Object.freeze(['Germany', 'USA', 'France', 'UK & Ireland']);
const PLAYERS = Object.freeze([2, 3, 4, 5, 6]);
const VARIANTS = Object.freeze(['original', 'recharged']);
const FAST_BIDS = Object.freeze([false, true]);
const PANELS = Object.freeze(['strong', 'mixed']);
const POLICIES = Object.freeze(['expert24', 'ppo2']);
const PHASES = Object.freeze(['Auction', 'Resources', 'Building', 'Bureaucracy']);
// Includes fixed-phase executors so this exported list is exactly the terminal counts schema.
const CONTROLLERS = Object.freeze(['expert24', 'ppo0', 'ppo1', 'ppo2', 'reference', 'teacherV2', 'fixedV2', 'fixedV1']);
const COUNT_KEYS = CONTROLLERS;
const OLD = Object.freeze(['ppo0', 'ppo1', 'ppo2']);
const LEARNED = Object.freeze(['Auction', 'Building']);
const FIELDS = Object.freeze([
    'map',
    'players',
    'variant',
    'fastBid',
    'cell',
    'seed',
    'smoke',
    'deal',
    'focalSeat',
    'panel',
    'policy',
    'controllers',
    'maxSteps',
]);
const CELLS = MAPS.flatMap((map) =>
    PLAYERS.flatMap((n) =>
        VARIANTS.flatMap((variant) => FAST_BIDS.map((fast) => `${map}|${n}|${variant}|${Number(fast)}`))
    )
);

// Independently pin scope, rather than treating a supplied config/spec as authority.
assert.equal(ENGINE_VERSION, '2.0.22');
assert.equal(protocol.schema, 'multimap-population-stress-v1');
assert.equal(protocol.seedNamespace, 'pg-multimap-stress-20261103-v1');
for (const [key, expected] of Object.entries({
    maps: MAPS,
    players: PLAYERS,
    variants: VARIANTS,
    fastBids: FAST_BIDS,
    panels: PANELS,
    policies: POLICIES,
    dealsPerCell: 4,
    smokeDealsPerCell: 1,
    maxSteps: 4000,
}))
    assert.deepEqual(protocol[key], expected, 'Unexpected frozen stress protocol');

function object(value) {
    return (
        value !== null &&
        typeof value === 'object' &&
        !Array.isArray(value) &&
        [Object.prototype, null].includes(Object.getPrototypeOf(value))
    );
}
function exactKeys(value, keys) {
    if (
        !object(value) ||
        Reflect.ownKeys(value).length !== keys.length ||
        !keys.every((key) => Object.hasOwn(value, key))
    )
        throw Error('Unexpected stress fields');
}
function canonicalIndex(spec) {
    if (
        !object(spec) ||
        !MAPS.includes(spec.map) ||
        !Number.isInteger(spec.players) ||
        !PLAYERS.includes(spec.players) ||
        !VARIANTS.includes(spec.variant) ||
        typeof spec.fastBid !== 'boolean'
    )
        throw Error('Invalid stress cell');
    return CELLS.indexOf(`${spec.map}|${spec.players}|${spec.variant}|${Number(spec.fastBid)}`);
}
function controllersFor(spec, ci = canonicalIndex(spec)) {
    if (
        ci !== canonicalIndex(spec) ||
        !PANELS.includes(spec.panel) ||
        !POLICIES.includes(spec.policy) ||
        !Number.isInteger(spec.deal) ||
        spec.deal < 0 ||
        spec.deal >= 4 ||
        !Number.isInteger(spec.focalSeat) ||
        spec.focalSeat < 0 ||
        spec.focalSeat >= spec.players
    )
        throw Error('Invalid stress assignment');
    const weakPool = [...OLD, 'teacherV2', ...(spec.map === 'Germany' ? ['reference'] : [])];
    return Array.from({ length: spec.players }, (_, seat) => {
        if (seat === spec.focalSeat) return spec.policy;
        if (spec.panel === 'strong') return spec.map === 'Germany' ? 'reference' : 'expert24';
        const ordinal = ((seat - spec.focalSeat + spec.players) % spec.players) - 1;
        const i = ci + spec.deal + ordinal;
        return i % 2 === 0 ? 'expert24' : weakPool[Math.floor(i / 2) % weakPool.length];
    });
}
function validateSpec(spec) {
    exactKeys(spec, FIELDS);
    const ci = canonicalIndex(spec);
    if (
        typeof spec.smoke !== 'boolean' ||
        !PANELS.includes(spec.panel) ||
        !POLICIES.includes(spec.policy) ||
        !Number.isInteger(spec.deal) ||
        spec.deal < 0 ||
        spec.deal >= (spec.smoke ? 1 : 4) ||
        !Number.isInteger(spec.focalSeat) ||
        spec.focalSeat < 0 ||
        spec.focalSeat >= spec.players ||
        spec.cell !== CELLS[ci] ||
        spec.maxSteps !== 4000 ||
        spec.seed !== `${protocol.seedNamespace}${spec.smoke ? ':smoke' : ''}:${spec.panel}:${CELLS[ci]}:${spec.deal}`
    )
        throw Error('Invalid bounded stress scope/namespace');
    assert.deepEqual(spec.controllers, controllersFor(spec, ci), 'Wrong complete stress assignment');
}
function phaseCounts() {
    return Object.fromEntries(PHASES.map((phase) => [phase, 0]));
}
function capped() {
    const error = Error('Stress game capped; no terminal credit fabricated');
    error.code = 'STRESS_CAPPED';
    throw error;
}
let nextGameId = 0;

class StressGame {
    start(spec) {
        validateSpec(spec);
        if (this.g && !f.E.ended(this.g)) throw Error('Cannot abandon an active stress game');
        this.spec = freeze(structuredClone(spec));
        this.g = start(this.spec);
        this.gameId = ++nextGameId;
        this.steps = 0;
        this.pending = null;
        this.counts = Object.fromEntries(COUNT_KEYS.map((controller) => [controller, phaseCounts()]));
        // Actual engine seat indices, not player-order positions. Totals include forced moves.
        this.seatCounts = Array.from({ length: spec.players }, phaseCounts);
        this.publicChecks = { hiddenInvariant: 0, referenceAtomicLegal: 0, fullMenuPrior: 0, expertAtomicLegal: 0 };
        return this.view();
    }
    apply(move, controller) {
        if (this.steps >= 4000) capped();
        const seat = this.g.currentPlayers[0],
            phase = this.g.phase;
        if (!COUNT_KEYS.includes(controller) || !PHASES.includes(phase)) throw Error('Invalid stress actor');
        const moves = f.legal(this.g, seat),
            index = atomicIndex(moves, move);
        f.E.move(this.g, structuredClone(moves[index]), seat);
        this.counts[controller][phase]++;
        this.seatCounts[seat][phase]++;
        this.steps++;
    }
    publicRequest(seat) {
        if (
            !this.g ||
            this.spec.map !== 'Germany' ||
            seat !== this.g.currentPlayers[0] ||
            this.spec.controllers[seat] !== 'reference'
        )
            throw Error('No reference request for this seat');
        const state = hiddenInvariant(this.g, seat);
        this.publicChecks.hiddenInvariant++;
        return { requestId: `stress-v1-${this.gameId}-${this.steps}`, revision: this.steps, player: seat, state };
    }
    view() {
        if (!this.g) throw Error('No stress game');
        while (!f.E.ended(this.g)) {
            if (this.steps >= 4000) capped();
            // Re-reading a decision neither emits another request nor inflates public-check counts.
            if (this.pending) return structuredClone(this.pending.decision);
            const seat = this.g.currentPlayers[0],
                phase = this.g.phase,
                moves = f.legal(this.g, seat);
            if (!PHASES.includes(phase)) throw Error('Unknown stress phase');
            const controller = this.spec.controllers[seat];
            const common = { terminal: false, controller, seat, phase, revision: this.steps };
            if (controller === 'reference') {
                const request = this.publicRequest(seat);
                const decision = { ...common, kind: 'reference', request };
                this.pending = {
                    kind: 'reference',
                    seat,
                    phase,
                    controller,
                    revision: this.steps,
                    requestId: request.requestId,
                    decision,
                };
                return structuredClone(decision);
            }
            if (controller !== 'teacherV2' && moves.length > 1 && LEARNED.includes(phase)) {
                const began = performance.now();
                const observation = (controller === 'expert24' ? expertInputs : oldInputs)(this.g, seat);
                if (
                    observation.prior.length !== moves.length ||
                    observation.actions.length !== moves.length ||
                    !observation.prior.every(Number.isFinite)
                )
                    throw Error('Invalid full-menu stress prior');
                this.publicChecks.fullMenuPrior++;
                const decision = { ...common, kind: 'policy', observation, featureMs: performance.now() - began };
                this.pending = { kind: 'policy', seat, phase, controller, revision: this.steps, decision };
                return structuredClone(decision);
            }
            const old = OLD.includes(controller),
                teacher = old ? teacherV1 : teacherV2;
            this.apply(
                moves.length === 1 ? moves[0] : teacher.choose(this.g, seat, moves, 'geographic').action,
                controller === 'teacherV2' ? 'teacherV2' : old ? 'fixedV1' : 'fixedV2'
            );
        }
        this.pending = null;
        return structuredClone({
            terminal: true,
            credit: outcome(this.g),
            steps: this.steps,
            rounds: this.g.round,
            counts: this.counts,
            seatCounts: this.seatCounts,
            publicChecks: this.publicChecks,
        });
    }
    boundIndex(response) {
        // Retained service identity/timing metadata may accompany the atomic move. Never use an old index.
        if (
            !object(response) ||
            Object.hasOwn(response, 'index') ||
            !['requestId', 'revision', 'move'].every((key) => Object.hasOwn(response, key)) ||
            response.requestId !== this.pending.requestId ||
            response.revision !== this.pending.revision
        )
            throw Error('Expected bound reference atomic response, never an index');
        return atomicIndex(f.legal(this.g, this.pending.seat), response.move);
    }
    label() {
        throw Error('Labels forbidden in evaluation-only stress bridge');
    }
    step(req) {
        if (!this.pending) throw Error('No pending stress decision');
        if (this.steps >= 4000) capped();
        const pending = this.pending;
        if (
            !object(req) ||
            req.op !== 'step' ||
            pending.revision !== this.steps ||
            pending.seat !== this.g.currentPlayers[0] ||
            pending.phase !== this.g.phase
        )
            throw Error('Stale stress decision');
        const moves = f.legal(this.g, pending.seat);
        let index;
        if (pending.kind === 'reference') {
            exactKeys(req, ['op', 'response']);
            index = this.boundIndex(req.response);
        } else {
            exactKeys(req, ['op', 'index']);
            if (!Number.isInteger(req.index) || req.index < 0 || req.index >= moves.length)
                throw Error('Illegal full-menu policy index');
            index = req.index;
        }
        this.apply(moves[index], pending.controller);
        if (pending.kind === 'reference') this.publicChecks.referenceAtomicLegal++;
        this.pending = null;
        return this.view();
    }
    request(req) {
        if (!object(req)) throw Error('Invalid stress operation');
        if (req.op === 'start') {
            exactKeys(req, ['op', 'spec']);
            return this.start(req.spec);
        }
        if (req.op === 'label') return this.label();
        if (req.op === 'step') return this.step(req);
        throw Error('Unknown stress operation');
    }
}

if (require.main === module) {
    const game = new StressGame();
    let failed = false;
    require('node:readline')
        .createInterface({ input: process.stdin })
        .on('line', (line) => {
            try {
                if (failed || Buffer.byteLength(line, 'utf8') > 1024 * 1024) throw Error('Invalid stress transport');
                console.log(JSON.stringify(game.request(JSON.parse(line))));
            } catch (error) {
                failed = true;
                // Never log requests, raw states, atomic actions, stack traces or model traces.
                console.log(
                    JSON.stringify({ error: error.code === 'STRESS_CAPPED' ? 'stress-capped' : 'stress-bridge-error' })
                );
            }
        });
}
module.exports = { protocol, PHASES, CONTROLLERS, controllersFor, validateSpec, StressGame };
