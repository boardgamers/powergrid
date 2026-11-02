const assert = require('node:assert/strict');
const { test } = require('node:test');
const fs = require('node:fs');
const path = require('node:path');
const { start } = require('./game.cjs');
const f = require('./features.cjs');
const {
    SEED_NAMESPACE,
    publicState,
    hiddenInvariant,
    atomicIndex,
    validateSpec,
    ReferenceGame,
} = require('./reference_game.cjs');
const spec = {
    map: 'Germany',
    players: 4,
    variant: 'recharged',
    fastBid: true,
    focalSeat: 0,
    focalPolicy: 'reference',
    maxSteps: 4000,
    seed: SEED_NAMESPACE + ':unit',
};

test('all 20 Germany cells are public and hidden-state invariant without mutating state', () => {
    for (const players of [2, 3, 4, 5, 6])
        for (const variant of ['original', 'recharged'])
            for (const fastBid of [false, true]) {
                const g = start({ ...spec, players, variant, fastBid });
                const seat = g.currentPlayers[0],
                    before = JSON.stringify(g);
                const state = hiddenInvariant(g, seat);
                assert.equal(JSON.stringify(g), before);
                assert.equal(state.seed, 'secret');
                assert.deepEqual(state.powerPlantsDeck, []);
                assert.deepEqual(state.hiddenLog, []);
                assert(!Object.hasOwn(state, 'automation'));
                assert(!Object.hasOwn(state, 'powerPlantDeckAfterStep3'));
                assert.equal(JSON.stringify(publicState(g, seat)), JSON.stringify(state));
            }
});

test('atomic move mapping translates thinned indices; object key order is not move identity', () => {
    const all = Array.from({ length: 101 }, (_, data) => ({ name: 'Bid', data }));
    const thin = all.filter((a) => a.data < 8 || a.data % 10 === 0);
    const position = thin.findIndex((a) => a.data === 90);
    assert.notEqual(position, 90);
    assert.equal(atomicIndex(all, thin[position]), 90);
    assert.equal(
        atomicIndex([{ name: 'Build', data: { name: 'Essen', price: 10 } }], {
            data: { price: 10, name: 'Essen' },
            name: 'Build',
        }),
        0
    );
    for (const move of [null, 90, { name: 'Bid', data: -1 }, { name: 'Bid', data: 0, extra: true }])
        assert.throws(() => atomicIndex(all, move));
    assert.throws(() => atomicIndex([all[0], all[0]], all[0]));
});

test('reference responses require request binding and authoritative atomic legality', () => {
    const game = new ReferenceGame(),
        view = game.start(spec);
    assert.equal(view.kind, 'reference');
    const before = JSON.stringify(game.g);
    const response = {
        requestId: view.request.requestId,
        revision: view.request.revision,
        move: { name: 'Bid', data: -1 },
    };
    assert.throws(() => game.step({ index: 0, response }));
    assert.throws(() => game.step({ response: { ...response, requestId: 'stale' } }));
    assert.throws(() => game.step({ response }));
    assert.equal(game.steps, 0);
    assert.equal(JSON.stringify(game.g), before);
    response.move = f.legal(game.g, game.g.currentPlayers[0])[0];
    game.step({ response });
    assert.equal(game.steps, 1);
});

test('old policy is exposed in resource/powering phases too, never replaced by teacher', () => {
    for (const phase of ['Resources', 'Bureaucracy']) {
        const game = new ReferenceGame();
        game.start(spec);
        game.g.phase = phase;
        const actor = game.g.currentPlayers[0];
        game.g.currentPlayers = [actor];
        game.g.players[actor].availableMoves = f.E.availableMoves(game.g, game.g.players[actor]);
        const view = game.view();
        assert.equal(view.kind, 'reference');
        assert.equal(view.phase, phase);
        assert.equal(game.steps, 0);
    }
});

test('teacher/reference controls and only bounded fresh preflight seeds are admitted', () => {
    for (const focalPolicy of ['selected', 'teacher', 'reference']) validateSpec({ ...spec, focalPolicy });
    for (const patch of [
        { map: 'USA' },
        { players: 7 },
        { seed: 'reserved-final' },
        { maxSteps: 999999 },
        { focalSeat: 4 },
        { focalPolicy: 'best-confirmation-seed' },
    ])
        assert.throws(() => validateSpec({ ...spec, ...patch }));
});

const artifact = path.resolve(__dirname, '../runs/multimap-reference-preflight-v1/artifact');
test(
    'archived engine compatibility: 20 cells, thinning, discounts, discards and threshold builds',
    { skip: !fs.existsSync(path.join(artifact, 'policy.json')) },
    () => {
        const report = require('./reference_compatibility.cjs').screen(artifact);
        assert.equal(report.cells, 20);
        assert.equal(report.cases, 160);
        assert.equal(report.preparationFailures, 0);
        assert.equal(report.recomputedMenuMismatches, 0);
        assert.equal(report.hiddenChecks, 160);
        assert.equal(report.thinnedCases, 30);
        assert.equal(report.rows.filter((r) => r.forbiddenBuilds > 0).length, 20);
        assert.equal(
            report.rows.filter((r) => r.tag === 'discounted-one-dollar-nomination' && r.discountActive).length,
            10
        );
        assert(report.rows.some((r) => r.cell.includes('recharged') && r.minimumLegalBid === 1));
        assert(report.rows.some((r) => r.indexTranslationRequired));
        assert(report.rows.every((r) => r.illegalRejected));
    }
);
