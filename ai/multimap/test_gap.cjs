// Offline unit tests with deterministic STUB experts; never start ReferenceProcess.
const test = require('node:test');
const assert = require('node:assert/strict');
const { isDeepStrictEqual } = require('node:util');
const gap = require('./gap_game.cjs');
const f = require('./features.cjs');
const teacher = require('./teacher.cjs');
const { inputs } = require('./game_rl.cjs');
const { start, outcome } = require('./game.cjs');
const legacy = require('./reference_game.cjs');
const p = gap.protocol;

function spec(policy = 'teacher', seat = 0, fastBid = false) {
    const cell = `Germany|2|original|${Number(fastBid)}`;
    return {
        map: 'Germany',
        players: 2,
        variant: 'original',
        fastBid,
        cell,
        deal: 0,
        seed: `${fastBid ? p.seedNamespace : p.smokeNamespace}:${cell}:0`,
        focalSeat: seat,
        focalPolicy: policy,
        maxSteps: 4000,
    };
}
function response(view, move) {
    return { response: { requestId: view.request.requestId, revision: view.request.revision, move } };
}
function stubExpert(g) {
    // Explicit deterministic mock, not evidence about retained FILTER strength.
    const seat = g.currentPlayers[0],
        moves = f.legal(g, seat);
    return moves.length === 1 ? moves[0] : teacher.choose(g, seat, moves, 'economic').action;
}
function playStub(s) {
    const game = new gap.GapGame();
    let view = game.start(s);
    while (!view.terminal) view = game.step(response(view, stubExpert(game.g)));
    return view;
}

test('frozen ten arms route exactly one phase each; no PPO or nonfocal teacher routing', () => {
    assert.equal(p.policies.length, 10);
    for (const arm of p.policies)
        for (const phase of p.phases) {
            const teacher =
                arm === 'teacher' ||
                arm === `reference-except-${phase}` ||
                (arm.startsWith('teacher-except-') && arm !== `teacher-except-${phase}`);
            assert.equal(gap.controller(arm, phase), teacher ? 'teacher' : 'reference');
        }
    assert.throws(() => gap.controller('ppo0', 'Auction'));
    assert.throws(() => gap.controller('teacher', 'unknown'));
});

test('own strict namespace guard leaves reference bridge namespace untouched', () => {
    gap.validateSpec(spec());
    gap.validateSpec(spec('reference', 1, true));
    assert.throws(() => legacy.validateSpec(spec()));
    for (const patch of [
        { seed: 'pg-multimap-neural-screen-20261102-v1:Germany|2|original|0:0' },
        { seed: p.seedNamespace + ':final:Germany|2|original|0:0' },
        { deal: 2 },
        { seed: p.smokeNamespace + ':Germany|2|original|0:1', deal: 1 },
        { fastBid: 0 },
        { map: 'USA' },
        { focalPolicy: 'selected' },
        { maxSteps: 2 },
        { focalSeat: 2 },
        { hiddenState: {} },
    ])
        assert.throws(() => gap.validateSpec({ ...spec(), ...patch }));
});

test('bound math: >16+epsilon separated, exactly16 can tie, exact floor20 distinguished', () => {
    const eps = p.priorGapEpsilon,
        prior = [0, 0, -16, -16 - eps / 2, -16 - 2 * eps, -20];
    const checks = prior.map((_, i) => gap.priorDiagnostic(prior, i, 0));
    assert.deepEqual(
        checks.map((x) => x.cannotOutscoreTeacherBestWithCurrentBound),
        [false, false, false, false, true, true]
    );
    assert.deepEqual(
        checks.map((x) => x.exactFloor20),
        [false, false, false, false, false, true]
    );
    assert.equal(prior[2] + 8, prior[0] - 8); // Tie is not strictly unreachable.
    assert(prior[4] + 8 < prior[0] - 8);
    assert.equal(checks[1].priorGap, 0);
    assert.equal(checks[1].teacherExpertAgreement, false); // Same prior != same atomic move.
    const row = gap.phaseCounter();
    checks.forEach((x) => gap.recordComparison(row, x));
    assert.equal(row.multiActionDecisions, 6);
    assert.equal(row.teacherExpertAgreement, 1);
    assert.equal(row.forcedMoves, 0);
    assert.equal(row.priorGapMax, 20);
    assert.equal(row.cannotOutscoreTeacherBestWithCurrentBound, 2);
    assert.equal(row.exactFloor20, 1);
    assert.deepEqual(row.priorGapHistogram, [2, 0, 0, 0, 0, 1, 3]);
    for (const bad of [
        [0, NaN],
        [0, -21],
        [-1, -2],
        [0, 1],
    ])
        assert.throws(() => gap.priorDiagnostic(bad, 1, 0));
    assert.throws(() => gap.priorDiagnostic([0, -1], 1, 1));
});

test('public projection + frozen prior/teacher invariant to hidden poison (open/sealed)', () => {
    for (const fast of [false, true]) {
        const game = start(spec('teacher', 0, fast)),
            seat = game.currentPlayers[0];
        const before = JSON.stringify(game),
            publicView = gap.hiddenInvariant(game, seat);
        assert.deepEqual(publicView, legacy.publicState(game, seat));
        const poison = structuredClone(game);
        poison.seed = 'poison';
        poison.powerPlantsDeck.reverse();
        poison.hiddenLog = [{ secret: true }];
        poison.powerPlantDeckAfterStep3 = [{ number: 999 }];
        poison.automation = { plans: { [seat]: { secret: true } } };
        poison.players.forEach((q) => {
            q.lastMove = { secret: true };
            if (fast) q.bid = 999;
        });
        if (fast) poison.currentBid = 999;
        assert.deepEqual(gap.publicState(poison, seat), publicView);
        assert.deepEqual(inputs(poison, seat), inputs(game, seat));
        assert.deepEqual(teacher.choose(poison, seat).action, teacher.choose(game, seat).action);
        assert.equal(JSON.stringify(game), before);
    }
});

test('teacher multi-action requests counterfactual expert, illegal/unbound/index replies never apply', () => {
    const game = new gap.GapGame();
    let view = game.start(spec());
    while (view.request.player !== 0) view = game.step(response(view, stubExpert(game.g)));
    assert.equal(view.actualController, 'teacher');
    assert.equal(view.focalComparison, true);
    const before = JSON.stringify(game.g),
        step = game.steps;
    const moves = f.legal(game.g, 0),
        actual = teacher.choose(game.g, 0, moves).action;
    const expert = moves.find((move) => !isDeepStrictEqual(move, actual));
    assert(expert);
    for (const req of [
        response(view, { name: 'DefinitelyIllegal', data: null }),
        { index: 0, ...response(view, expert) },
        { response: { ...response(view, expert).response, revision: step + 1 } },
    ]) {
        assert.throws(() => game.step(req));
        assert.equal(JSON.stringify(game.g), before);
        assert.equal(game.steps, step);
    }
    const expected = structuredClone(game.g);
    f.E.move(expected, structuredClone(actual), 0);
    game.step(response(view, expert));
    // First decision moves to the nonfocal auction player: no auto teacher step here.
    assert.deepEqual(game.g, expected);
    assert.equal(game.phaseCounters.Auction.teacherExpertAgreement, 0);
    assert.equal(game.phaseCounters.Auction.multiActionDecisions, 1);
    assert.equal(game.counts.focalTeacher.Auction, 1);
    assert.equal(game.publicChecks.fullMenuPrior, 1);
    assert.equal(game.publicChecks.teacherAtomicLegal, 1);
    assert.throws(() => gap.atomicIndex([moves[0], moves[0]], moves[0]));
});

test('stub-expert all-reference seat rotations reproduce terminal vectors and exact counters', () => {
    const outcomes = [0, 1].map((seat) => playStub(spec('reference', seat)));
    assert.deepEqual(outcomes[0].credit, outcomes[1].credit);
    assert.equal(outcomes[0].credit[0] + outcomes[1].credit[1], 1);
    for (const view of outcomes) {
        assert.equal(view.publicChecks.hiddenInvariant, view.steps);
        assert.equal(view.publicChecks.expertAtomicLegal, view.steps);
        let multi = 0,
            forced = 0;
        for (const phase of p.phases) {
            const c = view.phaseCounters[phase];
            multi += c.multiActionDecisions;
            forced += c.forcedMoves;
            assert.equal(
                c.priorGapHistogram.reduce((a, b) => a + b, 0),
                c.multiActionDecisions
            );
            assert.equal(view.counts.focalReference[phase], c.multiActionDecisions + c.forcedMoves);
            assert.equal(view.counts.focalTeacher[phase], 0);
        }
        assert(forced > 0); // Not counted as agreement or a prior sample.
        assert.equal(view.publicChecks.fullMenuPrior, multi);
        assert.equal(view.publicChecks.teacherAtomicLegal, multi);
        assert.equal(
            Object.values(view.counts)
                .flatMap(Object.values)
                .reduce((a, b) => a + b, 0),
            view.steps
        );
        assert(!JSON.stringify(view).includes('availableMoves'));
    }
});

test('teacher control exactly matches independent existing deterministic teacher loop', () => {
    const s = spec(),
        g = start(s);
    let steps = 0;
    while (!f.E.ended(g)) {
        assert(steps < 4000);
        const seat = g.currentPlayers[0],
            moves = f.legal(g, seat);
        const move =
            seat === s.focalSeat
                ? moves.length === 1
                    ? moves[0]
                    : teacher.choose(g, seat, moves, 'geographic').action
                : stubExpert(g);
        f.E.move(g, structuredClone(move), seat);
        steps++;
    }
    const view = playStub(s);
    assert.deepEqual(view.credit, outcome(g));
    assert.equal(view.steps, steps);
    assert.equal(view.rounds, g.round);
    assert.equal(
        Object.values(view.counts.focalReference).reduce((a, b) => a + b, 0),
        0
    );
    const forced = Object.values(view.phaseCounters).reduce((a, c) => a + c.forcedMoves, 0);
    assert.equal(view.publicChecks.hiddenInvariant, steps - forced);
});
