// Evaluation-only bridge. The authoritative 2.0.22 state never leaves Node.
const assert = require('node:assert/strict');
const { isDeepStrictEqual } = require('node:util');
const f = require('./features.cjs');
const teacher = require('./teacher.cjs');
const { inputs } = require('./game_rl.cjs');
const { start, outcome } = require('./game.cjs');
const protocol = require('./ppo-protocol-v1.json');
const ENGINE_VERSION = require('../../engine/package.json').version;
const SEED_NAMESPACE = 'pg-multimap-reference-preflight-v1';
const SCREEN_NAMESPACE = 'pg-multimap-neural-screen-20261102-v1';
assert.equal(ENGINE_VERSION, '2.0.22');

function publicState(g, seat) {
    // Same public scrub as the pinned sealed-policy-beliefs.cjs, but use the
    // authoritative engine's projection. No log sorting: object insertion order
    // affects the old tie-breaking policy and must survive JSON transport.
    const state = structuredClone(f.E.stripSecret(g, seat));
    state.seed = 'secret';
    state.powerPlantsDeck = [];
    state.hiddenLog = [];
    delete state.powerPlantDeckAfterStep3;
    delete state.automation;
    if (state.options.fastBid) state.currentBid = 0;
    state.players.forEach((p) => {
        p.lastMove = null;
        if (state.options.fastBid) p.bid = 0;
    });
    return state;
}

function hiddenInvariant(g, seat) {
    const before = JSON.stringify(g),
        hidden = structuredClone(g);
    hidden.seed = 'reference-hidden-poison';
    hidden.powerPlantsDeck = [...hidden.powerPlantsDeck].reverse();
    hidden.powerPlantDeckAfterStep3 = [{ number: 999 }];
    hidden.hiddenLog = [{ secret: 'poison' }];
    hidden.automation = { plans: { [seat]: { secret: true } } };
    hidden.players.forEach((p) => {
        p.lastMove = { secret: true };
        if (hidden.options.fastBid) p.bid = 999;
    });
    if (hidden.options.fastBid) hidden.currentBid = 999;
    const original = publicState(g, seat),
        poisoned = publicState(hidden, seat);
    assert.equal(JSON.stringify(poisoned), JSON.stringify(original), 'Hidden-state leak in public projection');
    assert.equal(JSON.stringify(g), before, 'Public projection mutated authoritative state');
    assert.equal(original.seed, 'secret');
    assert.deepEqual(original.powerPlantsDeck, []);
    assert.deepEqual(original.hiddenLog, []);
    if (g.options.fastBid) assert(original.players.every((p) => p.bid === 0));
    return original;
}

function atomicIndex(moves, move) {
    const matches = moves.flatMap((candidate, index) => (isDeepStrictEqual(candidate, move) ? [index] : []));
    if (matches.length !== 1) throw Error('Returned reference atomic move is not uniquely authoritative-legal');
    return matches[0];
}

function validateSpec(spec) {
    if (
        spec.map !== 'Germany' ||
        !protocol.players.includes(spec.players) ||
        !protocol.variants.includes(spec.variant) ||
        !protocol.fastBids.includes(spec.fastBid) ||
        !Number.isInteger(spec.focalSeat) ||
        spec.focalSeat < 0 ||
        spec.focalSeat >= spec.players ||
        typeof spec.seed !== 'string' ||
        ![SEED_NAMESPACE, SCREEN_NAMESPACE].some((prefix) => spec.seed.startsWith(prefix + ':')) ||
        spec.maxSteps !== protocol.maxSteps ||
        !['selected', 'teacher', 'reference'].includes(spec.focalPolicy || 'selected')
    )
        throw Error('Invalid bounded reference evaluation spec');
}

class ReferenceGame {
    start(spec) {
        validateSpec(spec);
        this.spec = spec;
        this.g = start(spec);
        this.steps = 0;
        this.counts = { ppo: {}, reference: {}, fixed: {} };
        this.hiddenChecks = 0;
        this.pending = null;
        return this.view();
    }
    apply(move, kind) {
        const g = this.g,
            seat = g.currentPlayers[0],
            phase = g.phase;
        const legal = f.legal(g, seat);
        const index = atomicIndex(legal, move);
        f.E.move(g, structuredClone(legal[index]), seat);
        this.counts[kind][phase] = (this.counts[kind][phase] || 0) + 1;
        this.steps++;
    }
    view() {
        while (!f.E.ended(this.g)) {
            if (this.steps >= this.spec.maxSteps) throw Error('Reference game capped; no terminal credit fabricated');
            const seat = this.g.currentPlayers[0],
                moves = f.legal(this.g, seat);
            if (seat !== this.spec.focalSeat || this.spec.focalPolicy === 'reference') {
                const state = hiddenInvariant(this.g, seat);
                this.hiddenChecks++;
                this.pending = 'reference';
                return {
                    terminal: false,
                    kind: 'reference',
                    phase: this.g.phase,
                    request: { requestId: `reference-${this.steps}`, revision: this.steps, player: seat, state },
                };
            }
            if (
                this.spec.focalPolicy !== 'teacher' &&
                moves.length > 1 &&
                protocol.learnedPhases.includes(this.g.phase)
            ) {
                this.pending = 'ppo';
                return { terminal: false, kind: 'ppo', phase: this.g.phase, observation: inputs(this.g, seat) };
            }
            this.apply(
                moves.length === 1 ? moves[0] : teacher.choose(this.g, seat, moves, 'geographic').action,
                'fixed'
            );
        }
        this.pending = null;
        return {
            terminal: true,
            credit: outcome(this.g),
            steps: this.steps,
            rounds: this.g.round,
            counts: this.counts,
            hiddenChecks: this.hiddenChecks,
        };
    }
    step(req) {
        if (this.pending === 'reference') {
            if (
                Object.hasOwn(req, 'index') ||
                !req.response ||
                req.response.requestId !== `reference-${this.steps}` ||
                req.response.revision !== this.steps
            )
                throw Error('Reference response must bind request/revision and supply an atomic move, never an index');
            this.apply(req.response.move, 'reference');
        } else if (this.pending === 'ppo') {
            const moves = f.legal(this.g, this.g.currentPlayers[0]);
            if (!Number.isInteger(req.index) || req.index < 0 || req.index >= moves.length)
                throw Error('Illegal PPO action index');
            this.apply(moves[req.index], 'ppo');
        } else throw Error('No pending decision');
        return this.view();
    }
}

if (require.main === module) {
    const game = new ReferenceGame();
    require('node:readline')
        .createInterface({ input: process.stdin })
        .on('line', (line) => {
            try {
                const req = JSON.parse(line);
                const result = req.op === 'start' ? game.start(req.spec) : req.op === 'step' ? game.step(req) : null;
                if (!result) throw Error('Unknown reference operation');
                console.log(JSON.stringify(result));
            } catch (error) {
                console.log(JSON.stringify({ error: error.message }));
            }
        });
}
module.exports = {
    ENGINE_VERSION,
    SEED_NAMESPACE,
    publicState,
    hiddenInvariant,
    atomicIndex,
    validateSpec,
    ReferenceGame,
};
