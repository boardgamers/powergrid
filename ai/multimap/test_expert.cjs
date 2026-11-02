// Offline STUB oracle/model tests; not evidence of neural playing strength.
const test = require('node:test');
const assert = require('node:assert/strict');
const x = require('./expert_game.cjs');
const f = require('./features.cjs');
const old = require('./teacher.cjs');
const v2 = require('./teacher_v2.cjs');
const { start, outcome } = require('./game.cjs');
const p = x.protocol;
function spec(split = 'selection', ci = 0, seat = 0, smoke = true, deal = 0, update = 0) {
    const maps =
        split === 'warmup'
            ? ['Germany']
            : split === 'confirmation' && !smoke
            ? [...p.trainMaps, ...p.transferMaps]
            : p.trainMaps;
    const cells = maps.flatMap((map) =>
        (smoke ? [2] : p.players).flatMap((players) =>
            (smoke ? ['original'] : p.variants).flatMap((variant) =>
                (smoke ? [false] : p.fastBids).map((fastBid) => ({ map, players, variant, fastBid }))
            )
        )
    );
    const s = { ...cells[ci], split, smoke, deal, update, maxSteps: 4000 };
    s.cell = `${s.map}|${s.players}|${s.variant}|${Number(s.fastBid)}`;
    s.seed = `${p.seedNamespace}${smoke ? ':smoke' : ''}:${split}:${update}:${s.cell}:${deal}`;
    s.focalSeat =
        split === 'warmup' ? (ci + deal) % s.players : split === 'train' ? (ci + update - 1) % s.players : seat;
    return { ...s, ...x.opponentsFor(s, ci) };
}
function bound(view, move) {
    return { requestId: view.request.requestId, revision: view.revision, move };
}
function gold(game) {
    return old.choose(game.g, game.g.currentPlayers[0]).action;
}
function play(s) {
    const game = new x.ExpertGame();
    let view = game.start(s);
    while (!view.terminal) {
        if (view.kind === 'reference') view = game.step({ op: 'step', response: bound(view, gold(game)) });
        else {
            let index = view.observation.prior.indexOf(Math.max(...view.observation.prior));
            if (view.expertRequired) {
                const label = game.label({ op: 'label', response: bound(view, gold(game)) });
                if (s.split === 'warmup') index = label.expertIndex;
            }
            view = game.step({ op: 'step', index });
        }
    }
    return view;
}
test('strict scope, independent namespaces, transfer evaluation only and evaluation-only teacher flag', () => {
    for (const split of ['warmup', 'train', 'selection', 'confirmation']) {
        const count = split === 'warmup' ? 20 : split === 'confirmation' ? 120 : 80;
        for (let ci = 0; ci < count; ci++) x.validateSpec(spec(split, ci, 0, false, 0, split === 'train' ? 1 : 0));
    }
    for (const patch of [
        { focalTeacher: 1 },
        { seed: 'final:0' },
        { map: 'Italy' },
        { fastBid: 0 },
        { maxSteps: 2 },
        { private: {} },
    ])
        assert.throws(() => x.validateSpec({ ...spec(), ...patch }));
    x.validateSpec({ ...spec(), focalTeacher: true });
    assert.throws(() => x.validateSpec({ ...spec('train', 0, 0, true, 0, 1), focalTeacher: false }));
    assert.throws(() => x.validateSpec(spec('train')));
    assert.throws(() => require('./reference_game.cjs').validateSpec(spec()));
});
test('smoke training covers all three frozen opponents and greedy self; selection never uses self', () => {
    assert.deepEqual(
        [0, 1, 2, 3].map((i) => spec('train', i, 0, true, 0, 1).opponents.filter((x) => x !== 'learner')[0]),
        ['ppo1', 'ppo2', 'self', 'ppo0']
    );
    for (let ci = 0; ci < 120; ci++) assert(!spec('confirmation', ci, 0, false).opponents.includes('self'));
});
test('new prior and public projection ignore hidden information, including sealed pending bids', () => {
    for (const ci of [0, 1]) {
        const g = start(spec('selection', ci, 0, false)),
            seat = g.currentPlayers[0],
            before = JSON.stringify(g);
        const poison = structuredClone(g);
        poison.seed = 'hidden';
        poison.powerPlantsDeck.reverse();
        poison.hiddenLog = [{ secret: true }];
        poison.powerPlantDeckAfterStep3 = [{ number: 999 }];
        poison.automation = { plans: { [seat]: { secret: true } } };
        poison.players.forEach((q) => {
            q.lastMove = { secret: true };
            if (g.options.fastBid) q.bid = 999;
        });
        if (g.options.fastBid) poison.currentBid = 999;
        assert.deepEqual(x.publicState(poison, seat), x.publicState(g, seat));
        assert.deepEqual(x.inputs(poison, seat), x.inputs(g, seat));
        assert.deepEqual(v2.choose(poison, seat).action, v2.choose(g, seat).action);
        assert.equal(JSON.stringify(g), before);
    }
});
test('counterfactual label bound to full menu, required before student action, no action applied by labeling', () => {
    const game = new x.ExpertGame();
    let view = game.start(spec('train', 0, 0, true, 0, 1));
    assert.equal(view.kind, 'learner');
    assert.equal(view.expertRequired, true);
    const before = JSON.stringify(game.g),
        moves = f.legal(game.g, view.seat);
    assert.throws(() => game.step({ op: 'step', index: 0 }));
    for (const response of [
        bound(view, { name: 'illegal' }),
        { ...bound(view, moves[0]), revision: 999 },
        { ...bound(view, moves[0]), index: 0 },
    ])
        assert.throws(() => game.label({ op: 'label', response }));
    const label = game.label({ op: 'label', response: bound(view, moves[moves.length - 1]) });
    assert.equal(label.expertIndex, moves.length - 1);
    assert.equal(JSON.stringify(game.g), before);
    assert.throws(() => game.label({ op: 'label', response: bound(view, moves[0]) }));
    assert.throws(() => game.step({ op: 'step', index: moves.length }));
    game.step({ op: 'step', index: 0 }); // Student need not execute the expert choice (DAgger).
    assert.equal(game.counts.learner.Auction, 1);
});
test('warmup executes expert, evaluation/unsupported maps cannot request expert', () => {
    const game = new x.ExpertGame();
    const view = game.start(spec('warmup'));
    const moves = f.legal(game.g, view.seat);
    game.label({ op: 'label', response: bound(view, moves[moves.length - 1]) });
    assert.throws(() => game.step({ op: 'step', index: 0 }));
    game.step({ op: 'step', index: moves.length - 1 });
    const evalGame = new x.ExpertGame();
    const e = evalGame.start(spec());
    assert.equal(e.expertRequired, false);
    assert(!e.request);
    assert.throws(() => evalGame.publicRequest(0, 'expert'));
    const usa = new x.ExpertGame();
    usa.start(spec('train', 1, 0, true, 0, 1));
    assert.throws(() => usa.publicRequest(0, 'expert'));
});
test('zero scorer and direct v2 teacher have exact full-game parity in four-map stub population', () => {
    for (let ci = 0; ci < 4; ci++) {
        const s = spec('selection', ci),
            a = play(s),
            b = play({ ...s, focalTeacher: true });
        for (const key of ['credit', 'steps', 'rounds', 'terminal']) assert.deepEqual(a[key], b[key]);
        assert.equal(
            Object.values(b.counts.learner).reduce((a, b) => a + b, 0),
            0
        );
        assert(Object.values(b.counts.focalTeacher).reduce((a, b) => a + b, 0) > 0);
        assert.equal(
            Object.values(a.expertCounts).reduce((a, b) => a + b, 0),
            0
        );
        assert.equal(
            Object.values(a.counts)
                .flatMap(Object.values)
                .reduce((a, b) => a + b, 0),
            a.steps
        );
    }
});
test('stub-oracle warmup and all-map training finish with exact label/routing counts; caps fail', () => {
    for (const s of [spec('warmup'), ...[0, 1, 2, 3].map((i) => spec('train', i, 0, true, 0, 1))]) {
        const result = play(s);
        const actual = s.split === 'warmup' ? result.counts.warmupExpert : result.counts.learner;
        assert.deepEqual(
            result.expertCounts,
            s.map === 'Germany' ? actual : Object.fromEntries(x.PHASES.map((p) => [p, 0]))
        );
        assert.equal(
            result.publicChecks.hiddenInvariant,
            result.publicChecks.referenceAtomicLegal + result.publicChecks.expertAtomicLegal
        );
    }
    const game = new x.ExpertGame();
    game.start(spec());
    game.steps = 4000;
    assert.throws(() => game.view(), /capped/);
});
