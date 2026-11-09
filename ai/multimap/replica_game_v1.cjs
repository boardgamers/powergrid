// Expert-PPO v2 only. The authoritative 2.0.22 game never crosses this boundary.
const assert = require('node:assert/strict');
const { performance } = require('node:perf_hooks');
const f = require('./features.cjs');
const teacher = require('./teacher.cjs');
const teacherV2 = require('./teacher_v2.cjs');
const { inputs: oldInputs } = require('./game_rl.cjs');
const { start, outcome } = require('./game.cjs');
const { ENGINE_VERSION, publicState, hiddenInvariant, atomicIndex } = require('./reference_game.cjs');
const protocol = require('./replica_protocol_v1.cjs')(process.argv[2]);
assert.equal(ENGINE_VERSION, '2.0.22');
assert.equal(teacherV2.SCHEMA, protocol.fixedTeacher);
const PHASES = ['Auction', 'Resources', 'Building', 'Bureaucracy'];
const FROZEN = ['ppo0', 'ppo1', 'ppo2'];
const FIELDS = [
    'map',
    'players',
    'variant',
    'fastBid',
    'cell',
    'seed',
    'split',
    'update',
    'smoke',
    'deal',
    'focalSeat',
    'opponentMode',
    'opponents',
    'maxSteps',
];

function opponentsFor(spec, ci) {
    const reference = spec.map === 'Germany' && (spec.split !== 'train' || (ci + spec.update) % 2 === 0);
    const pool = spec.split === 'train' ? [...FROZEN, 'self'] : FROZEN;
    let ordinal = 0;
    return {
        opponentMode: reference ? 'reference' : 'mixed',
        opponents: Array.from({ length: spec.players }, (_, seat) => {
            if (seat === spec.focalSeat) return 'learner';
            if (reference) return 'reference';
            const offset = spec.split === 'train' ? spec.update + ordinal++ : seat;
            return pool[(ci + spec.deal + offset) % pool.length];
        }),
    };
}

function validateSpec(spec) {
    if (
        !spec ||
        Object.keys(spec)
            .filter((k) => k !== 'focalTeacher')
            .sort()
            .join('|') !== [...FIELDS].sort().join('|')
    )
        throw Error('Unexpected expert spec fields');
    if (
        Object.hasOwn(spec, 'focalTeacher') &&
        (typeof spec.focalTeacher !== 'boolean' || !['selection', 'confirmation'].includes(spec.split))
    )
        throw Error('Teacher control is evaluation-only');
    if (
        !['warmup', 'train', 'selection', 'confirmation'].includes(spec.split) ||
        typeof spec.smoke !== 'boolean' ||
        !Number.isInteger(spec.update) ||
        spec.update < 0 ||
        spec.update > protocol.updates ||
        (spec.split !== 'train' && spec.update !== 0) ||
        (spec.split === 'train' && spec.update < 1)
    )
        throw Error('Invalid expert split/update');
    const maps =
        spec.split === 'warmup'
            ? ['Germany']
            : spec.split === 'confirmation' && !spec.smoke
            ? [...protocol.trainMaps, ...protocol.transferMaps]
            : protocol.trainMaps;
    const players = spec.smoke ? [2] : protocol.players;
    const variants = spec.smoke ? ['original'] : protocol.variants;
    const fastBids = spec.smoke ? [false] : protocol.fastBids;
    const cells = maps.flatMap((map) =>
        players.flatMap((n) => variants.flatMap((v) => fastBids.map((fast) => `${map}|${n}|${v}|${Number(fast)}`)))
    );
    const cell = `${spec.map}|${spec.players}|${spec.variant}|${Number(spec.fastBid)}`;
    const ci = cells.indexOf(cell);
    const deals = spec.smoke
        ? spec.split === 'warmup'
            ? 2
            : 1
        : spec.split === 'warmup'
        ? protocol.warmupGamesPerCell
        : spec.split === 'train'
        ? protocol.gamesPerCellPerUpdate
        : protocol[spec.split + 'DealsPerCell'];
    const namespace = protocol.seedNamespace + (spec.smoke ? ':smoke' : '');
    const seed = `${namespace}:${spec.split}:${spec.update}:${cell}:${spec.deal}`;
    const rotating =
        spec.split === 'warmup'
            ? (ci + spec.deal) % spec.players
            : (ci + spec.update + spec.players - 1) % spec.players;
    if (
        ci < 0 ||
        !maps.includes(spec.map) ||
        !players.includes(spec.players) ||
        !variants.includes(spec.variant) ||
        !fastBids.includes(spec.fastBid) ||
        !Number.isInteger(spec.players) ||
        !Number.isInteger(spec.deal) ||
        spec.deal < 0 ||
        spec.deal >= deals ||
        !Number.isInteger(spec.focalSeat) ||
        spec.focalSeat < 0 ||
        spec.focalSeat >= spec.players ||
        (['train', 'warmup'].includes(spec.split) && spec.focalSeat !== rotating) ||
        spec.cell !== cell ||
        spec.seed !== seed ||
        spec.maxSteps !== protocol.maxSteps
    )
        throw Error('Invalid bounded expert scope/namespace');
    const expected = opponentsFor(spec, ci);
    assert.equal(spec.opponentMode, expected.opponentMode, 'Wrong expert opponent mode');
    assert.deepEqual(spec.opponents, expected.opponents, 'Wrong complete opponent assignment');
}

function inputs(g, seat) {
    const moves = f.legal(g, seat),
        observation = f.encode(g, seat, moves);
    const scores = teacherV2.scores(g, seat, moves, 'geographic');
    const best = Math.max(...scores),
        temps = protocol.priorTemperatures;
    const temperature = moves.some((a) => a.name === 'Bid')
        ? g.options.fastBid
            ? temps.sealedBid
            : temps.openBid
        : moves.some((a) => a.name === 'ChoosePowerPlant')
        ? temps.nomination
        : temps.other;
    if (scores.length !== moves.length || !scores.every(Number.isFinite)) throw Error('Invalid v2 scores');
    observation.prior = scores.map((v) => Math.max(protocol.priorFloor, (v - best) / temperature));
    return observation;
}
function phaseCounts() {
    return Object.fromEntries(PHASES.map((p) => [p, 0]));
}
function exactKeys(object, keys) {
    if (!object || Object.keys(object).sort().join('|') !== [...keys].sort().join('|'))
        throw Error('Unexpected expert operation fields');
}

class ExpertGame {
    start(spec) {
        validateSpec(spec);
        if (this.g && !f.E.ended(this.g)) throw Error('Cannot abandon an active expert game');
        this.spec = structuredClone(spec);
        this.g = start(spec);
        this.steps = 0;
        this.pending = null;
        this.counts = Object.fromEntries(
            ['learner', 'warmupExpert', 'reference', 'self', ...FROZEN, 'fixedV2', 'fixedV1', 'focalTeacher'].map(
                (k) => [k, phaseCounts()]
            )
        );
        this.expertCounts = phaseCounts();
        this.publicChecks = { hiddenInvariant: 0, referenceAtomicLegal: 0, expertAtomicLegal: 0, fullMenuPrior: 0 };
        return this.view();
    }
    apply(move, controller) {
        const seat = this.g.currentPlayers[0],
            phase = this.g.phase;
        const moves = f.legal(this.g, seat),
            index = atomicIndex(moves, move);
        f.E.move(this.g, structuredClone(moves[index]), seat);
        this.counts[controller][phase]++;
        this.steps++;
    }
    publicRequest(seat, purpose) {
        if (this.spec.map !== 'Germany') throw Error('Reference is Germany-only');
        if (
            purpose === 'expert' &&
            (!['train', 'warmup'].includes(this.spec.split) ||
                seat !== this.spec.focalSeat ||
                !protocol.learnedPhases.includes(this.g.phase))
        )
            throw Error('Expert labels forbidden for this decision');
        const state = hiddenInvariant(this.g, seat);
        this.publicChecks.hiddenInvariant++;
        return { requestId: `expert-v2-${purpose}-${this.steps}`, revision: this.steps, player: seat, state };
    }
    view() {
        while (!f.E.ended(this.g)) {
            if (this.steps >= this.spec.maxSteps) throw Error('Expert game capped; no terminal labels fabricated');
            const seat = this.g.currentPlayers[0],
                phase = this.g.phase,
                moves = f.legal(this.g, seat);
            if (!PHASES.includes(phase)) throw Error('Unknown expert phase');
            const controller = this.spec.opponents[seat];
            if (seat === this.spec.focalSeat && this.spec.focalTeacher) {
                this.apply(
                    moves.length === 1 ? moves[0] : teacherV2.choose(this.g, seat, moves, 'geographic').action,
                    'focalTeacher'
                );
                continue;
            }
            if (controller === 'reference') {
                const request = this.publicRequest(seat, 'opponent');
                this.pending = { kind: 'reference', seat, phase, request };
                return { terminal: false, kind: 'reference', seat, phase, controller, request, revision: this.steps };
            }
            if (moves.length > 1 && protocol.learnedPhases.includes(phase)) {
                const began = performance.now();
                const kind = controller === 'learner' ? 'learner' : 'opponent';
                const expertRequired =
                    kind === 'learner' && this.spec.map === 'Germany' && ['warmup', 'train'].includes(this.spec.split);
                const observation = FROZEN.includes(controller) ? oldInputs(this.g, seat) : inputs(this.g, seat);
                assert.equal(observation.prior.length, moves.length);
                this.publicChecks.fullMenuPrior++;
                const request = expertRequired ? this.publicRequest(seat, 'expert') : undefined;
                this.pending = { kind, seat, phase, controller, expertRequired, expertIndex: null, request };
                return {
                    terminal: false,
                    kind,
                    seat,
                    phase,
                    controller,
                    expertRequired,
                    observation,
                    request,
                    revision: this.steps,
                    featureMs: performance.now() - began,
                };
            }
            const old = FROZEN.includes(controller),
                t = old ? teacher : teacherV2;
            this.apply(
                moves.length === 1 ? moves[0] : t.choose(this.g, seat, moves, 'geographic').action,
                old ? 'fixedV1' : 'fixedV2'
            );
        }
        this.pending = null;
        return {
            terminal: true,
            credit: outcome(this.g),
            steps: this.steps,
            rounds: this.g.round,
            counts: this.counts,
            expertCounts: this.expertCounts,
            publicChecks: this.publicChecks,
        };
    }
    boundIndex(response) {
        if (
            !response ||
            Object.hasOwn(response, 'index') ||
            response.requestId !== this.pending.request.requestId ||
            response.revision !== this.steps
        )
            throw Error('Expected bound reference atomic response, never an index');
        return atomicIndex(f.legal(this.g, this.pending.seat), response.move);
    }
    label(req) {
        exactKeys(req, ['op', 'response']);
        if (
            !this.pending ||
            this.pending.kind !== 'learner' ||
            !this.pending.expertRequired ||
            this.pending.expertIndex !== null
        )
            throw Error('No pending counterfactual expert label');
        // Resolve against the FULL authoritative menu BEFORE any student action.
        const index = this.boundIndex(req.response);
        this.pending.expertIndex = index;
        this.expertCounts[this.pending.phase]++;
        this.publicChecks.expertAtomicLegal++;
        return { labeled: true, expertIndex: index, revision: this.steps };
    }
    step(req) {
        if (!this.pending) throw Error('No pending expert decision');
        const pending = this.pending,
            moves = f.legal(this.g, pending.seat);
        let index, controller;
        if (pending.kind === 'reference') {
            exactKeys(req, ['op', 'response']);
            index = this.boundIndex(req.response);
            this.publicChecks.referenceAtomicLegal++;
            controller = 'reference';
        } else {
            exactKeys(req, ['op', 'index']);
            if (pending.expertRequired && pending.expertIndex === null)
                throw Error('Counterfactual expert response required before application');
            if (!Number.isInteger(req.index) || req.index < 0 || req.index >= moves.length)
                throw Error('Illegal full-menu policy index');
            index = req.index;
            if (this.spec.split === 'warmup' && pending.kind === 'learner' && index !== pending.expertIndex)
                throw Error('Warmup must execute exact expert learned action');
            controller =
                this.spec.split === 'warmup' && pending.kind === 'learner' ? 'warmupExpert' : pending.controller;
        }
        this.pending = null;
        this.apply(moves[index], controller);
        return this.view();
    }
    request(req) {
        if (req.op === 'start') {
            exactKeys(req, ['op', 'spec']);
            return this.start(req.spec);
        }
        if (req.op === 'label') return this.label(req);
        if (req.op === 'step') return this.step(req);
        throw Error('Unknown expert operation');
    }
}

if (require.main === module) {
    const game = new ExpertGame();
    let failed = false;
    require('node:readline')
        .createInterface({ input: process.stdin })
        .on('line', (line) => {
            try {
                if (failed) throw Error('Bridge already failed');
                console.log(JSON.stringify(game.request(JSON.parse(line))));
            } catch (error) {
                failed = true;
                // No request/state/atomic action traces in errors or artifacts.
                console.log(
                    JSON.stringify({
                        error: error.message.includes('capped') ? 'expert-capped' : 'expert-bridge-error',
                    })
                );
            }
        });
}
module.exports = {
    protocol,
    PHASES,
    FROZEN,
    opponentsFor,
    validateSpec,
    inputs,
    ExpertGame,
    publicState,
    hiddenInvariant,
    atomicIndex,
};
