// Diagnostic-only bridge. Authoritative state and full legal menus stay in Node.
// Only scrubbed public requests cross to exact ReferenceProcess; never persist them.
const assert = require('node:assert/strict');
const f = require('./features.cjs');
const teacher = require('./teacher.cjs');
const { inputs } = require('./game_rl.cjs');
const { start, outcome } = require('./game.cjs');
const { ENGINE_VERSION, publicState, hiddenInvariant, atomicIndex } = require('./reference_game.cjs');
const protocol = require('./gap-protocol-v1.json');
const priorProtocol = require('./ppo-protocol-v1.json');
assert.equal(ENGINE_VERSION, protocol.authoritativeEngineRelease);
assert.equal(priorProtocol.priorFloor, protocol.priorFloor);
assert.equal(priorProtocol.residualBound, protocol.residualBound);

function controller(policy, phase) {
    if (!protocol.policies.includes(policy) || !protocol.phases.includes(phase))
        throw Error('Unknown diagnostic arm/phase');
    return protocol.phaseRoutes[policy][phase];
}

function validateSpec(spec) {
    const fields = [
        'map',
        'players',
        'variant',
        'fastBid',
        'cell',
        'seed',
        'deal',
        'focalSeat',
        'maxSteps',
        'focalPolicy',
    ];
    if (!spec || Object.keys(spec).sort().join('|') !== fields.sort().join('|'))
        throw Error('Unexpected diagnostic spec fields');
    const cell = `${spec.map}|${spec.players}|${spec.variant}|${Number(spec.fastBid)}`;
    const full = `${protocol.seedNamespace}:${cell}:${spec.deal}`;
    const smoke = `${protocol.smokeNamespace}:${cell}:0`;
    if (
        spec.map !== 'Germany' ||
        !protocol.players.includes(spec.players) ||
        !protocol.variants.includes(spec.variant) ||
        !protocol.fastBids.includes(spec.fastBid) ||
        !Number.isInteger(spec.focalSeat) ||
        spec.focalSeat < 0 ||
        spec.focalSeat >= spec.players ||
        !Number.isInteger(spec.deal) ||
        spec.deal < 0 ||
        spec.deal >= protocol.dealsPerCell ||
        spec.cell !== cell ||
        spec.maxSteps !== protocol.maxSteps ||
        !protocol.policies.includes(spec.focalPolicy) ||
        !(
            spec.seed === full ||
            (spec.seed === smoke &&
                spec.deal === 0 &&
                spec.players === 2 &&
                spec.variant === 'original' &&
                spec.fastBid === false)
        )
    )
        throw Error('Invalid frozen diagnostic spec/namespace');
}

function phaseCounter() {
    return {
        multiActionDecisions: 0,
        forcedMoves: 0,
        teacherExpertAgreement: 0,
        priorGapSum: 0,
        priorGapMax: 0,
        priorGapHistogram: protocol.priorGapHistogramUpperBounds.map(() => 0),
        cannotOutscoreTeacherBestWithCurrentBound: 0,
        exactFloor20: 0,
    };
}

function priorDiagnostic(prior, expertIndex, teacherIndex) {
    if (
        !Array.isArray(prior) ||
        prior.length < 2 ||
        !prior.every((v) => Number.isFinite(v) && v >= protocol.priorFloor && v <= 0) ||
        Math.max(...prior) !== 0 ||
        !Number.isInteger(expertIndex) ||
        expertIndex < 0 ||
        expertIndex >= prior.length ||
        !Number.isInteger(teacherIndex) ||
        teacherIndex < 0 ||
        teacherIndex >= prior.length ||
        prior[teacherIndex] !== 0
    )
        throw Error('Invalid full-menu frozen prior/teacher-best index');
    const priorGap = Math.max(0, -prior[expertIndex]);
    // A gap of exactly 16 can tie at residual endpoints; NOT strictly unreachable.
    return {
        priorGap,
        histogramIndex: protocol.priorGapHistogramUpperBounds.findIndex((v) => priorGap <= v),
        cannotOutscoreTeacherBestWithCurrentBound: priorGap > 2 * protocol.residualBound + protocol.priorGapEpsilon,
        exactFloor20: prior[expertIndex] === -20,
        teacherExpertAgreement: expertIndex === teacherIndex,
    };
}

function recordComparison(counter, comparison) {
    counter.multiActionDecisions++;
    counter.teacherExpertAgreement += Number(comparison.teacherExpertAgreement);
    counter.priorGapSum += comparison.priorGap;
    counter.priorGapMax = Math.max(counter.priorGapMax, comparison.priorGap);
    counter.priorGapHistogram[comparison.histogramIndex]++;
    counter.cannotOutscoreTeacherBestWithCurrentBound += Number(comparison.cannotOutscoreTeacherBestWithCurrentBound);
    counter.exactFloor20 += Number(comparison.exactFloor20);
}

class GapGame {
    start(spec) {
        validateSpec(spec);
        this.spec = structuredClone(spec);
        this.g = start(spec);
        this.steps = 0;
        this.pending = null;
        this.counts = Object.fromEntries(
            ['focalReference', 'focalTeacher', 'nonfocalReference'].map((k) => [
                k,
                Object.fromEntries(protocol.phases.map((p) => [p, 0])),
            ])
        );
        this.phaseCounters = Object.fromEntries(protocol.phases.map((p) => [p, phaseCounter()]));
        this.publicChecks = { hiddenInvariant: 0, expertAtomicLegal: 0, fullMenuPrior: 0, teacherAtomicLegal: 0 };
        return this.view();
    }
    apply(move, actor) {
        const seat = this.g.currentPlayers[0],
            phase = this.g.phase;
        const legal = f.legal(this.g, seat),
            index = atomicIndex(legal, move);
        f.E.move(this.g, structuredClone(legal[index]), seat);
        this.counts[actor][phase]++;
        this.steps++;
    }
    view() {
        while (!f.E.ended(this.g)) {
            if (this.steps >= this.spec.maxSteps) throw Error('Diagnostic game capped; no terminal credit fabricated');
            const seat = this.g.currentPlayers[0],
                phase = this.g.phase;
            const focal = seat === this.spec.focalSeat,
                moves = f.legal(this.g, seat);
            const actual = focal ? controller(this.spec.focalPolicy, phase) : 'reference';
            if (!protocol.phases.includes(phase)) throw Error('Unexpected diagnostic phase');
            // Forced teacher actions are genuinely forced, not expert agreement samples.
            if (focal && moves.length === 1 && actual === 'teacher') {
                this.phaseCounters[phase].forcedMoves++;
                this.apply(moves[0], 'focalTeacher');
                continue;
            }
            const state = hiddenInvariant(this.g, seat);
            this.publicChecks.hiddenInvariant++;
            this.pending = { seat, phase, focal, actual, multi: moves.length > 1 };
            return {
                terminal: false,
                kind: 'reference',
                phase,
                actualController: actual,
                focalComparison: focal && moves.length > 1,
                request: { requestId: `gap-${this.steps}`, revision: this.steps, player: seat, state },
            };
        }
        this.pending = null;
        return {
            terminal: true,
            credit: outcome(this.g),
            steps: this.steps,
            rounds: this.g.round,
            counts: this.counts,
            phaseCounters: this.phaseCounters,
            publicChecks: this.publicChecks,
        };
    }
    step(req) {
        if (
            !this.pending ||
            Object.hasOwn(req, 'index') ||
            !req.response ||
            req.response.requestId !== `gap-${this.steps}` ||
            req.response.revision !== this.steps
        )
            throw Error('Expected bound exact-reference atomic response, never an action index');
        const { seat, phase, focal, actual, multi } = this.pending;
        const moves = f.legal(this.g, seat);
        // Even a counterfactual response must be uniquely authoritative-legal BEFORE any application.
        const expertIndex = atomicIndex(moves, req.response.move);
        this.publicChecks.expertAtomicLegal++;
        let teacherIndex;
        if (focal && multi) {
            const prior = inputs(this.g, seat).prior; // Exact frozen prior, FULL authoritative menu.
            assert.equal(prior.length, moves.length, 'Prior/legal-menu mismatch');
            teacherIndex = atomicIndex(moves, teacher.choose(this.g, seat, moves, 'geographic').action);
            const comparison = priorDiagnostic(prior, expertIndex, teacherIndex);
            this.publicChecks.fullMenuPrior++;
            this.publicChecks.teacherAtomicLegal++;
            recordComparison(this.phaseCounters[phase], comparison);
        } else if (focal) this.phaseCounters[phase].forcedMoves++;
        this.pending = null;
        this.apply(
            moves[actual === 'teacher' ? teacherIndex : expertIndex],
            focal ? (actual === 'teacher' ? 'focalTeacher' : 'focalReference') : 'nonfocalReference'
        );
        return this.view();
    }
}

if (require.main === module) {
    const game = new GapGame();
    let failed = false;
    require('node:readline')
        .createInterface({ input: process.stdin })
        .on('line', (line) => {
            try {
                if (failed) throw Error('Diagnostic bridge already failed; no silent retry');
                const req = JSON.parse(line);
                const result = req.op === 'start' ? game.start(req.spec) : req.op === 'step' ? game.step(req) : null;
                if (!result) throw Error('Unknown diagnostic operation');
                console.log(JSON.stringify(result));
            } catch (error) {
                failed = true;
                // Fixed bounded code, not assertion payloads that could include actions/states.
                console.log(
                    JSON.stringify({
                        error: error.message.includes('capped') ? 'diagnostic-capped' : 'diagnostic-bridge-error',
                    })
                );
            }
        });
}
module.exports = {
    protocol,
    controller,
    validateSpec,
    phaseCounter,
    priorDiagnostic,
    recordComparison,
    GapGame,
    publicState,
    hiddenInvariant,
    atomicIndex,
};
