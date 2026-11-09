// Versioned three-arm delta of 6a7cdc6 stress_game.cjs; legacy files unmodified.
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
const protocol = freeze(structuredClone(require('./replica-stress-protocol-v1.json')));
const MAPS = Object.freeze(['Germany', 'USA', 'France', 'UK & Ireland']);
const PLAYERS = Object.freeze([2, 3, 4, 5, 6]);
const VARIANTS = Object.freeze(['original', 'recharged']);
const FAST_BIDS = Object.freeze([false, true]);
const PANELS = Object.freeze(['strong', 'mixed']);
const POLICIES = Object.freeze(['replica1', 'replica2', 'ppo2']);
const PHASES = Object.freeze(['Auction', 'Resources', 'Building', 'Bureaucracy']);
// Includes fixed-phase executors so this exported list is exactly the terminal counts schema.
const CONTROLLERS = Object.freeze([
    'expert24',
    'replica1',
    'replica2',
    'ppo0',
    'ppo1',
    'ppo2',
    'reference',
    'teacherV2',
    'fixedV2',
    'fixedV1',
]);
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

// Independent typed canonical digest pins every protocol field, including prose.
const fs = require('node:fs'),
    crypto = require('node:crypto'),
    path = require('node:path');
const PROTOCOL_SHA256 = '99d6e0e4eac7808f2de8c335361c5611ae4a93edfe8778b30dbe4139fb265d69';
const FROZEN_SOURCES = {
    'stress_game.cjs': '7d3a6408f220bf228837e807ca5e3ed0c6c2f18069a11d0bb8d29f4531b28d47',
    'stress_rollout.py': 'fd1c861e96c42341994fb48fbde9885240ea9d3a3333f13f1297cacae9e7757e',
    'stress_study.py': '1014ed49dbb54d3b0faccf61d694847d8bf3f12967d0abdd44ec1af4e45c2d6f',
    'expert_policy.py': '5304112f56195eec7aa6f89967503e6d08768be7ffb4fc232a7fcfe3349b4213',
    'expert_game.cjs': '6d0580b5054e5fb18b5b872827796665125d9997dd31b720dfe2becb00369942',
    'expert_rollout.py': '3deb6af55d5210caa04d02210a14bd3ff9c7af413afa2b39ef72bb3e3ebfb77e',
    'expert_ppo.py': '4357357fde973deff89d9df908622297ccce6fb89446c6e4cf314f20a5383bd0',
    'expert-protocol-v2.json': 'd9180c76ce072fe03fb1c325466d8d768a919d040ffd27229d4f375f61065796',
    'expert_replicas_v1.py': '8250728734ade2014dff94eff6d1f857b674124f5aa142ccc24002f1aa730cb4',
    'expert-replicas-protocol-v1.json': '130bb9d99e050211c0aecf86b46a98bb8e2cba6fb44371674cd17447d9b7aa5f',
    'replica_game_v1.cjs': 'b6f40b2fcc640484b3c1843d572df377dad34eee2ee1aec2b57241b73c0bd7c1',
    'replica_protocol_v1.cjs': 'c39a6844aaa70d4ec3dde6ab02969afe9aae176417ca3ad315ad260dec692a8a',
    'job_expert_replicas_v1.py': '66163649e35c80377f50d50d0d84d11f98f74b3c6c2d6968e233cb1b4f4032fb',
    'test_expert_replicas_v1.py': 'ffb227869444051ab5373872364f4263016033c0dbb0ffde5538c6e9519e6b6d',
    'launch_expert_replicas_v1.py': '5e6126d482df3febc290a2de2b39777107b8fe33939662e00349a042e183423c',
    'test_launch_expert_replicas_v1.py': '2802ec781d84f0413619d32e502aeff669d525c1e5e9d73018e8eeeb7b7e5da5',
    'preflight_expert_replicas_v1.py': '91c5577472bfe4767f987ec7dae6d277b09bcfcb73443dd614feb3a31031d4f0',
    'test_preflight_expert_replicas_v1.py': '9748637b386321dff38b5f0584acceea33f0d7926c9605fb2f845a16b46b6a3c',
    'game_rl.cjs': 'b3e8996da51841340b6f4f77b803dcbf01e2f72938ee44b7ba66f593d8167157',
    'game.cjs': '3a36d6a74407d7a8454edba898fabf9848a4c0615e960bb94554ae363b5b1e2b',
    'features.cjs': '1ced47a4a5e65946a8fdb207f0d6f87d9b535c698729ec36e008d39e0914803b',
    'teacher.cjs': 'd741947ba120f56a17953b92dc553a30cd4476f9594b3161a8a0adb1af0e88cb',
    'teacher_v2.cjs': '89a5b6c9e8520224eeb1cb34d8543cfccb2d8313002626a50907d4fa996cbdf6',
    'economics_v2.cjs': 'dbb2216b3572e4afc882a3da11f683abd998a54b8672c7acda4843ee142d1897',
    'model.py': '4f790d8fc718ed63f4df1a34c4a71ce1815abfaff50171cb1f6f256fe2f62a3e',
    'residual.py': '83e8cac000a05b2a015fa4f6612e0e4193ecd134e72f79e77123a2a10346e480',
    'candidates.py': '1c839a805d7bbe7a58415c2cea2ae1e98685d6373f3ee9ebbace1e841914d5ed',
    'candidate-pool-v1.json': 'a4f5d80966d9dd5b7af712459dffea255590eeb158b3a8e73cb66b0045d29a4b',
    'ppo.py': 'ea911838c835fc31df2a2566f8ef97531248f43e3cbf6f8cfa4bce0d6d164bee',
    'ppo-protocol-v1.json': '51f86acbbd1a495213c40554b3cc0c7933c92a2fc1608690397fbee76dad3cfe',
    'data.py': '3a166d6baf8e294aff56ac13310867d34892347fc754493def1d347d65670492',
    'reference_evaluate.py': 'e22e7b6e9de687d1c903217c03735434622e22e951cfbf030827f430e757cab9',
    'reference_recover.py': '1d0b7f87fa22c8e5673152abc4496f0b62ce017c2bcdc8b39ae8658febd7fadc',
    'reference_game.cjs': 'cd4e87bc0754a67b3a9bfffba17ac37353c5f1c4391aacc2ae92e18ad2d71949',
    'reference_compatibility.cjs': 'b3e87335eb97bdc301f6eebdd8e3adcb2bcfd3737d8d6d0eca00ff9156a45694',
    'rollout.py': 'ec6bf43926c1ce884e91b402d1881c7eb0efe728b6230eec2ae2fbb209791300',
    'requirements-cpu.txt': '975c2199adeee3550ce7ca31644833fa3fe5605789e6067e86b48610acb8ecf4',
};
const EXPERT = Object.freeze(['expert24', 'replica1', 'replica2']);
function canonical(value) {
    if (Array.isArray(value)) return '[' + value.map(canonical).join(',') + ']';
    if (value !== null && typeof value === 'object')
        return (
            '{' +
            Object.keys(value)
                .sort()
                .map((k) => JSON.stringify(k) + ':' + canonical(value[k]))
                .join(',') +
            '}'
        );
    return JSON.stringify(value);
}
const PROTOCOL_FILE_SHA256 = '1ca5a8fd0979f785cec0656a8738fbc7d5b92f9eb70a9729e0c26ec7916477d3';
function checkProtocol() {
    assert.equal(
        crypto
            .createHash('sha256')
            .update(fs.readFileSync(path.join(__dirname, 'replica-stress-protocol-v1.json')))
            .digest('hex'),
        PROTOCOL_FILE_SHA256,
        'Frozen replica stress protocol bytes changed'
    );
    for (const value of [
        protocol,
        JSON.parse(fs.readFileSync(path.join(__dirname, 'replica-stress-protocol-v1.json'), 'utf8')),
    ])
        assert.equal(
            crypto.createHash('sha256').update(canonical(value)).digest('hex'),
            PROTOCOL_SHA256,
            'Frozen replica stress protocol changed'
        );
}
checkProtocol();
assert.equal(ENGINE_VERSION, '2.0.22');
for (const [name, sha] of Object.entries(FROZEN_SOURCES))
    assert.equal(
        crypto
            .createHash('sha256')
            .update(fs.readFileSync(path.join(__dirname, name)))
            .digest('hex'),
        sha,
        'Frozen old source changed: ' + name
    );
const SMOKE_CELLS = new Set(protocol.smokeScopes.map(([m, n, v, f]) => `${m}|${n}|${v}|${Number(f)}`));

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
        spec.deal >= 8 ||
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
    checkProtocol();
    exactKeys(spec, FIELDS);
    const ci = canonicalIndex(spec);
    if (
        typeof spec.smoke !== 'boolean' ||
        (spec.smoke && !SMOKE_CELLS.has(CELLS[ci])) ||
        !PANELS.includes(spec.panel) ||
        !POLICIES.includes(spec.policy) ||
        !Number.isInteger(spec.deal) ||
        spec.deal < 0 ||
        spec.deal >= (spec.smoke ? 1 : 8) ||
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
        return {
            requestId: `replica-stress-v1-${this.gameId}-${this.steps}`,
            revision: this.steps,
            player: seat,
            state,
        };
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
                const observation = (EXPERT.includes(controller) ? expertInputs : oldInputs)(this.g, seat);
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
module.exports = {
    protocol,
    checkProtocol,
    EXPERT,
    POLICIES,
    PHASES,
    CONTROLLERS,
    controllersFor,
    validateSpec,
    StressGame,
};
