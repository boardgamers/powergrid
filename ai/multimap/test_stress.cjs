// Offline deterministic STUB policies/reference only: engineering checks, NOT neural strength evidence.
// No reference process, model loading, labels, fitting, qualification or production evaluation.
const test = require('node:test');
const assert = require('node:assert/strict');
const { spawnSync } = require('node:child_process');
const path = require('node:path');
const x = require('./stress_game.cjs');
const f = require('./features.cjs');
const v1 = require('./teacher.cjs');
const v2 = require('./teacher_v2.cjs');
const expert = require('./expert_game.cjs');
const legacy = require('./reference_game.cjs');
const { inputs: oldInputs } = require('./game_rl.cjs');
const { start, outcome } = require('./game.cjs');

const MAPS = ['Germany', 'USA', 'France', 'UK & Ireland'];
const PHASES = ['Auction', 'Resources', 'Building', 'Bureaucracy'];
const COUNT_KEYS = ['expert24', 'ppo0', 'ppo1', 'ppo2', 'reference', 'teacherV2', 'fixedV2', 'fixedV1'];
const CELLS = MAPS.flatMap((map) =>
    [2, 3, 4, 5, 6].flatMap((players) =>
        ['original', 'recharged'].flatMap((variant) =>
            [false, true].map((fastBid) => ({ map, players, variant, fastBid }))
        )
    )
);
const phaseCounts = () => Object.fromEntries(PHASES.map((phase) => [phase, 0]));
const sum = (counts) => Object.values(counts).reduce((a, b) => a + b, 0);
const total = (counts) => Object.values(counts).reduce((a, b) => a + sum(b), 0);

// Deliberately independent of controllersFor: catch both routing and canonical-index mistakes.
function assignment(s, ci) {
    const result = Array(s.players);
    result[s.focalSeat] = s.policy;
    const pool =
        s.map === 'Germany'
            ? ['ppo0', 'ppo1', 'ppo2', 'teacherV2', 'reference']
            : ['ppo0', 'ppo1', 'ppo2', 'teacherV2'];
    for (let ordinal = 0; ordinal < s.players - 1; ordinal++) {
        const seat = (s.focalSeat + ordinal + 1) % s.players;
        const i = ci + s.deal + ordinal;
        result[seat] =
            s.panel === 'strong'
                ? s.map === 'Germany'
                    ? 'reference'
                    : 'expert24'
                : i % 2
                ? pool[Math.floor(i / 2) % pool.length]
                : 'expert24';
    }
    return result;
}
function spec(ci = 20, panel = 'strong', policy = 'expert24', focalSeat = 0, smoke = true, deal = 0) {
    const s = { ...CELLS[ci], smoke, deal, focalSeat, panel, policy, maxSteps: 4000 };
    s.cell = `${s.map}|${s.players}|${s.variant}|${Number(s.fastBid)}`;
    s.seed = `pg-multimap-stress-20261103-v1${smoke ? ':smoke' : ''}:${panel}:${s.cell}:${deal}`;
    s.controllers = assignment(s, ci);
    return s;
}
function bound(view, move) {
    return { requestId: view.request.requestId, revision: view.revision, move };
}
function firstReference(ci = 1) {
    const s = spec(ci),
        seat = start(s).currentPlayers[0];
    return spec(ci, 'strong', 'expert24', (seat + 1) % s.players);
}
function firstPolicy(ci = 20, policy = 'expert24') {
    const s = spec(ci);
    return spec(ci, 'strong', policy, start(s).currentPlayers[0]);
}
function fakeReference(state, seat) {
    // Public-state-only deterministic fake. This does NOT approximate the retained reference's strength.
    const moves = f.legal(state, seat);
    return moves.length === 1 ? moves[0] : v1.choose(state, seat, moves, 'economic').action;
}
function playStub(s) {
    const game = new x.StressGame();
    const served = Object.fromEntries(x.CONTROLLERS.map((controller) => [controller, phaseCounts()]));
    let view = game.request({ op: 'start', spec: s });
    const checked = new Set();
    while (!view.terminal) {
        assert.equal(view.controller, s.controllers[view.seat]);
        assert.equal(view.seat, game.g.currentPlayers[0]);
        assert.equal(view.phase, game.g.phase);
        assert.equal(view.revision, game.steps);
        for (const key of ['expertRequired', 'expertIndex', 'expertCounts', 'targets'])
            assert(!Object.hasOwn(view, key));
        served[view.controller][view.phase]++;
        const moves = f.legal(game.g, view.seat);
        if (view.kind === 'policy') {
            assert(['Auction', 'Building'].includes(view.phase));
            assert(moves.length > 1);
            assert(!Object.hasOwn(view, 'request'));
            assert(Number.isFinite(view.featureMs) && view.featureMs >= 0);
            assert.equal(view.observation.prior.length, moves.length);
            assert.equal(view.observation.actions.length, moves.length);
            const key = `${view.controller}:${view.phase}`;
            if (!checked.has(key)) {
                checked.add(key);
                assert.deepEqual(
                    view.observation,
                    (view.controller === 'expert24' ? expert.inputs : oldInputs)(game.g, view.seat)
                );
            }
            const index = view.observation.prior.indexOf(Math.max(...view.observation.prior));
            view = game.request({ op: 'step', index });
        } else {
            assert.equal(view.kind, 'reference');
            assert.equal(view.controller, 'reference');
            assert.equal(s.map, 'Germany');
            assert(!Object.hasOwn(view, 'observation'));
            assert(!Object.hasOwn(view, 'featureMs'));
            assert.deepEqual(Object.keys(view.request).sort(), ['player', 'requestId', 'revision', 'state']);
            assert.equal(view.request.player, view.seat);
            assert.deepEqual(view.request.state, legacy.publicState(game.g, view.seat));
            view = game.request({ op: 'step', response: bound(view, fakeReference(view.request.state, view.seat)) });
        }
    }
    assert.deepEqual(
        Object.keys(view).sort(),
        ['terminal', 'credit', 'steps', 'rounds', 'counts', 'seatCounts', 'publicChecks'].sort()
    );
    assert.equal(view.credit.length, s.players);
    assert(view.credit.every((v) => Number.isFinite(v) && v >= 0 && v <= 1));
    assert(Math.abs(view.credit.reduce((a, b) => a + b, 0) - 1) < 1e-12);
    assert(view.steps > 0 && view.steps <= 4000);
    assert.equal(total(view.counts), view.steps);
    assert.equal(total(view.seatCounts), view.steps);
    assert.equal(view.seatCounts.length, s.players);
    assert.deepEqual(Object.keys(view.counts), COUNT_KEYS);
    for (const counts of [...Object.values(view.counts), ...view.seatCounts]) {
        assert.deepEqual(Object.keys(counts), PHASES);
        assert(Object.values(counts).every((n) => Number.isInteger(n) && n >= 0));
    }
    for (const controller of ['expert24', 'ppo0', 'ppo1', 'ppo2', 'reference'])
        assert.deepEqual(view.counts[controller], served[controller]);
    assert.deepEqual(view.publicChecks, {
        hiddenInvariant: sum(served.reference),
        referenceAtomicLegal: sum(served.reference),
        fullMenuPrior: ['expert24', 'ppo0', 'ppo1', 'ppo2'].reduce((a, name) => a + sum(served[name]), 0),
        expertAtomicLegal: 0,
    });
    for (const key of ['seed', 'availableMoves', 'hiddenLog', 'powerPlantsDeck', 'expertRequired', 'targets'])
        assert(!JSON.stringify(view).includes(`"${key}"`));
    assert(JSON.stringify(view).length < 4096);
    assert.deepEqual(game.view(), view);
    assert.throws(() => game.request({ op: 'label' }), /forbidden/);
    assert.throws(() => game.request({ op: 'step', index: 0 }));
    return view;
}
function directStub(s) {
    // Synchronous authoritative-engine control: no bridge, pending decisions or prior conversion.
    const g = start(s),
        counts = Object.fromEntries(COUNT_KEYS.map((name) => [name, phaseCounts()]));
    const seatCounts = Array.from({ length: s.players }, phaseCounts);
    let steps = 0;
    while (!f.E.ended(g)) {
        assert(steps < 4000);
        const seat = g.currentPlayers[0],
            phase = g.phase,
            moves = f.legal(g, seat),
            controller = s.controllers[seat];
        const old = ['ppo0', 'ppo1', 'ppo2'].includes(controller);
        const actual =
            controller === 'reference' || controller === 'teacherV2'
                ? controller
                : moves.length > 1 && ['Auction', 'Building'].includes(phase)
                ? controller
                : old
                ? 'fixedV1'
                : 'fixedV2';
        const action =
            controller === 'reference'
                ? fakeReference(legacy.publicState(g, seat), seat)
                : moves.length === 1
                ? moves[0]
                : (old ? v1 : v2).choose(g, seat, moves, 'geographic').action;
        f.E.move(g, structuredClone(action), seat);
        counts[actual][phase]++;
        seatCounts[seat][phase]++;
        steps++;
    }
    return { terminal: true, credit: outcome(g), steps, rounds: g.round, counts, seatCounts };
}
function assertParity(view, direct) {
    for (const key of Object.keys(direct)) assert.deepEqual(view[key], direct[key], key);
}

test('frozen 80-cell scope: complete production 5120 and smoke 1280 plans with paired independent roots', () => {
    assert.deepEqual(x.PHASES, PHASES);
    assert.deepEqual(x.CONTROLLERS, COUNT_KEYS);
    assert.equal(x.protocol.schema, 'multimap-population-stress-v1');
    assert.equal(x.protocol.seedNamespace, 'pg-multimap-stress-20261103-v1');
    assert(Object.isFrozen(x.protocol) && Object.isFrozen(x.protocol.maps));
    const roots = { production: new Set(), smoke: new Set() },
        seen = new Set();
    for (const smoke of [false, true]) {
        let games = 0;
        for (let ci = 0; ci < 80; ci++)
            for (const panel of ['strong', 'mixed'])
                for (let deal = 0; deal < (smoke ? 1 : 4); deal++)
                    for (let seat = 0; seat < CELLS[ci].players; seat++) {
                        const a = spec(ci, panel, 'expert24', seat, smoke, deal),
                            b = spec(ci, panel, 'ppo2', seat, smoke, deal);
                        for (const s of [a, b]) {
                            x.validateSpec(s);
                            assert.deepEqual(x.controllersFor(s), s.controllers);
                            assert.deepEqual(x.controllersFor(s, ci), s.controllers);
                            s.controllers.forEach((name) => seen.add(name));
                            if (s.map !== 'Germany') assert(!s.controllers.includes('reference'));
                            games++;
                        }
                        assert.equal(a.seed, b.seed);
                        assert.equal(a.seed, spec(ci, panel, 'expert24', 0, smoke, deal).seed);
                        assert.deepEqual(
                            a.controllers.filter((_, i) => i !== seat),
                            b.controllers.filter((_, i) => i !== seat)
                        );
                        roots[smoke ? 'smoke' : 'production'].add(a.seed);
                        if (smoke)
                            assert.deepEqual(a.controllers, spec(ci, panel, 'expert24', seat, false, 0).controllers);
                    }
        assert.equal(games, smoke ? 1280 : 5120);
    }
    assert.equal(roots.production.size, 640);
    assert.equal(roots.smoke.size, 160);
    assert([...roots.smoke].every((seed) => !roots.production.has(seed)));
    assert.deepEqual([...seen].sort(), COUNT_KEYS.slice(0, 6).sort());
    assert.notEqual(spec(20, 'strong').seed, spec(20, 'mixed').seed);
});

test('mixed weak-pool order, full canonical smoke index and relative-seat rotation are exact', () => {
    const germany = spec(17, 'mixed');
    assert.deepEqual(germany.controllers, ['expert24', 'teacherV2', 'expert24', 'reference', 'expert24', 'ppo0']);
    assert.deepEqual(x.controllersFor(germany), germany.controllers);
    const nonGermany = spec(37, 'mixed');
    assert.deepEqual(nonGermany.controllers, ['expert24', 'ppo2', 'expert24', 'teacherV2', 'expert24', 'ppo0']);
    assert.deepEqual(x.controllersFor(nonGermany), nonGermany.controllers);
    for (let seat = 0; seat < 6; seat++) {
        const rotated = x.controllersFor(spec(17, 'mixed', 'expert24', seat));
        assert.deepEqual(
            Array.from({ length: 6 }, (_, i) => rotated[(seat + i) % 6]),
            germany.controllers
        );
    }
    assert.throws(() => x.controllersFor(spec(37, 'mixed'), 1));
    assert.throws(() => x.controllersFor(spec(37, 'mixed'), '37'));
});

test('strict specs deny training/labels/transfer maps/custom config/seeds and never weaken legacy guards', () => {
    const s = spec();
    for (const patch of [
        { map: 'Italy' },
        { map: 'Benelux' },
        { map: 'UK' },
        { map: 'Germany' },
        { players: '2' },
        { players: true },
        { players: 1 },
        { players: 7 },
        { players: 2.5 },
        { fastBid: 0 },
        { fastBid: 'false' },
        { fastBid: null },
        { smoke: 0 },
        { smoke: 'true' },
        { variant: 'random' },
        { deal: 1 },
        { deal: -1 },
        { deal: '0' },
        { deal: false },
        { focalSeat: '0' },
        { focalSeat: true },
        { focalSeat: -1 },
        { focalSeat: 2 },
        { focalSeat: 0.5 },
        { policy: 'ppo0' },
        { policy: 'ppo1' },
        { policy: 'teacherV2' },
        { policy: 'reference' },
        { policy: 'self' },
        { panel: 'train' },
        { panel: 'selection' },
        { maxSteps: 3999 },
        { maxSteps: '4000' },
        { cell: 'USA|2|original|false' },
        { cell: 20 },
        { seed: 'custom' },
        { seed: null },
        { seed: s.seed + ':expert24' },
        { seed: s.seed + ':0' },
        { seed: s.seed.replace(':smoke', '') },
        { seed: s.seed.replace(':strong:', ':mixed:') },
        { seed: expert.protocol.seedNamespace + ':0' },
        { split: 'train' },
        { labels: true },
        { expertRequired: false },
        { focalTeacher: true },
        { update: 0 },
        { options: {} },
        { config: {} },
        { samples: 8 },
        { training: false },
        { controllers: ['expert24'] },
        { controllers: ['ppo2', 'expert24'] },
        { controllers: ['expert24', 'teacherV2'] },
        { controllers: { 0: 'expert24', 1: 'expert24' } },
    ])
        assert.throws(() => x.validateSpec({ ...s, ...patch }));
    for (const key of Object.keys(s)) {
        const missing = { ...s };
        delete missing[key];
        assert.throws(() => x.validateSpec(missing));
    }
    for (const value of [null, [], true, 'spec', 1]) assert.throws(() => x.validateSpec(value));
    assert.throws(() => x.validateSpec({ ...spec(20, 'strong', 'expert24', 0, false, 3), deal: 4 }));
    const extra = structuredClone(s);
    extra.controllers.extra = 'expert24';
    assert.throws(() => x.validateSpec(extra));
    assert.throws(() => expert.validateSpec(s));
    assert.throws(() => legacy.validateSpec(s));
    assert(!(new x.StressGame() instanceof expert.ExpertGame));
    assert(!(new x.StressGame() instanceof legacy.ReferenceGame));
});

test('both immutable priors, both teachers and public projection ignore poisoned hidden information', () => {
    for (const ci of [0, 1, 20, 21, 40, 41, 60, 61]) {
        const g = start(spec(ci));
        for (let stage = 0; stage < 2; stage++) {
            // Some non-Germany map definitions contain setup functions; policy tensors only
            // consume their serializable public data, and reference projection is Germany-only.
            const seat = g.currentPlayers[0],
                before = JSON.stringify(g);
            const poison = g.map.name === 'Germany' ? structuredClone(g) : JSON.parse(before);
            poison.seed = 'SECRET-POISON';
            poison.powerPlantsDeck.reverse();
            poison.hiddenLog = [{ secret: true }];
            poison.powerPlantDeckAfterStep3 = [{ number: 999 }];
            poison.automation = { plans: { [seat]: { secret: true } } };
            poison.players.forEach((p) => {
                p.lastMove = { secret: true };
                if (poison.options.fastBid) p.bid = 999;
            });
            if (poison.options.fastBid) poison.currentBid = 999;
            if (g.map.name === 'Germany')
                assert.deepEqual(legacy.publicState(poison, seat), legacy.hiddenInvariant(g, seat));
            for (const inputs of [expert.inputs, oldInputs]) assert.deepEqual(inputs(poison, seat), inputs(g, seat));
            for (const teacher of [v1, v2])
                assert.deepEqual(teacher.choose(poison, seat).action, teacher.choose(g, seat).action);
            assert.equal(JSON.stringify(g), before);
            if (stage === 0) {
                const move = f.legal(g, seat).find((a) => a.name === 'ChoosePowerPlant');
                f.E.move(g, structuredClone(move), seat);
            }
        }
    }
});

test('labels and unsupported operations always fail; policy uses complete menu, exact old/new priors and no state', () => {
    for (const policy of ['expert24', 'ppo2']) {
        const game = new x.StressGame(),
            s = firstPolicy(20, policy);
        assert.throws(() => game.label(), /forbidden/);
        assert.throws(() => game.request({ op: 'label', response: {} }), /forbidden/);
        assert.throws(() => game.view());
        let view = game.request({ op: 'start', spec: s });
        assert.equal(view.kind, 'policy');
        assert.equal(view.controller, policy);
        const before = JSON.stringify(game.g),
            checks = structuredClone(game.publicChecks);
        const moves = f.legal(game.g, view.seat);
        assert.deepEqual(view.observation, (policy === 'expert24' ? expert.inputs : oldInputs)(game.g, view.seat));
        assert.equal(view.observation.prior.length, moves.length);
        assert(!JSON.stringify(view).includes('availableMoves'));
        assert(!Object.hasOwn(view, 'request'));
        for (const req of [
            null,
            { op: 'collect', spec: s },
            { op: 'sample' },
            { op: 'label' },
            { op: 'train' },
            { op: 'step', index: -1 },
            { op: 'step', index: moves.length },
            { op: 'step', index: '0' },
            { op: 'step', index: true },
            { op: 'step', index: 0.5 },
            { op: 'step', index: 0, sample: false },
            { op: 'step', index: 0, revision: view.revision },
            { op: 'step', response: { index: 0 } },
            { op: 'start', spec: s },
            { op: 'start', spec: s, labels: false },
        ]) {
            assert.throws(() => game.request(req));
            assert.equal(JSON.stringify(game.g), before);
            assert.deepEqual(game.publicChecks, checks);
        }
        assert.throws(() => game.publicRequest(view.seat));
        s.controllers[view.seat] = 'reference'; // Caller mutation cannot change an active assignment.
        assert.equal(game.spec.controllers[view.seat], policy);
        const cached = game.view();
        assert.deepEqual(cached, view);
        cached.observation.prior[0] = 123;
        assert.deepEqual(game.view(), view);
        assert.deepEqual(game.publicChecks, checks);
        view = game.step({ op: 'step', index: moves.length - 1 }); // No truncation or top-k menu.
        assert.equal(game.counts[policy].Auction, 1);
        assert(game.steps > 0);
        assert.equal(game.publicChecks.expertAtomicLegal, 0);
    }
});

test('reference replies bind request/revision and authoritative atomic move, never a legacy menu index', () => {
    const s = firstReference(),
        game = new x.StressGame(),
        second = new x.StressGame();
    const view = game.start(s),
        other = second.start(s);
    assert.equal(view.kind, 'reference');
    assert.equal(view.request.state.seed, 'secret');
    assert.deepEqual(view.request.state.powerPlantsDeck, []);
    assert.deepEqual(view.request.state.hiddenLog, []);
    assert.equal(view.request.state.currentBid, 0);
    assert(view.request.state.players.every((p) => p.bid === 0));
    assert(!Object.hasOwn(view.request.state, 'automation'));
    assert(!Object.hasOwn(view.request.state, 'powerPlantDeckAfterStep3'));
    assert.notEqual(view.request.requestId, other.request.requestId);
    const moves = f.legal(game.g, view.seat),
        last = moves.at(-1);
    const before = JSON.stringify(game.g),
        checks = structuredClone(game.publicChecks);
    for (const req of [
        { op: 'step', index: 0 },
        { op: 'step', response: { index: 0 } },
        { op: 'step', response: { ...bound(view, last), index: moves.length - 1 } },
        { op: 'step', response: { ...bound(view, last), revision: view.revision + 1 } },
        { op: 'step', response: { ...bound(view, last), revision: String(view.revision) } },
        { op: 'step', response: bound(other, last) },
        { op: 'step', response: { ...bound(view, last), requestId: 'stale' } },
        { op: 'step', response: bound(view, { name: 'IllegalMove', data: null }) },
        { op: 'step', response: bound(view, { ...last, extra: true }) },
        { op: 'step', response: bound(view, moves.length - 1) },
        { op: 'step', response: bound(view, last), index: 0 },
        { op: 'label', response: bound(view, last) },
    ]) {
        assert.throws(() => game.request(req));
        assert.equal(JSON.stringify(game.g), before);
        assert.deepEqual(game.publicChecks, checks);
    }
    assert.throws(() => legacy.atomicIndex([last, last], last));
    assert.throws(() => game.publicRequest(s.focalSeat));
    const cached = game.view();
    cached.request.requestId = 'edited';
    cached.request.state.players[view.seat].money = -999;
    assert.deepEqual(game.view(), view);
    assert.deepEqual(game.publicChecks, checks);
    // Service metadata is allowed, but only its bound atomic move is consumed.
    game.step({ op: 'step', response: { ...bound(view, last), elapsedMs: 0, backend: 'STUB-engineering-only' } });
    assert.equal(game.publicChecks.referenceAtomicLegal, 1);
    assert.equal(game.counts.reference.Auction, 1);
    assert.throws(() => game.step({ op: 'step', response: bound(view, last) }));
});

test('homogeneous strong non-Germany all-seat controls have exact synchronous-STUB parity, not strength', () => {
    for (const ci of [20, 47, 69]) {
        // USA 2/open, France 3/recharged/sealed, UK 4/sealed.
        const s = spec(ci),
            expected = directStub(s),
            results = [];
        assert(s.controllers.every((controller) => controller === 'expert24'));
        for (let seat = 0; seat < s.players; seat++) {
            const view = playStub(spec(ci, 'strong', 'expert24', seat));
            assertParity(view, expected);
            assert.equal(sum(view.counts.fixedV1), 0);
            assert.equal(sum(view.counts.reference), 0);
            assert(sum(view.counts.expert24) > 0 && sum(view.counts.fixedV2) > 0);
            results.push(view);
        }
        assert.equal(
            results.reduce((a, result, seat) => a + result.credit[seat], 0),
            1
        );
        if (s.players === 2) assert.equal(results[0].credit[0], 1 - results[1].credit[1]);
    }
});

test('mixed and Germany strong full-game STUBs preserve per-seat/controller/phase counters across 2..6 scope', () => {
    const aggregate = Object.fromEntries(COUNT_KEYS.map((name) => [name, phaseCounts()]));
    for (const s of [
        spec(8, 'strong', 'expert24', 1), // Germany/open reference all phases.
        spec(17, 'mixed', 'ppo2', 2), // Germany/6/sealed: includes reference at weak-pool END.
        spec(32, 'mixed', 'expert24', 4), // USA/5/open: ppo0 and ppo1.
        spec(55, 'mixed', 'ppo2', 1), // France/5/recharged/sealed, teacherV2.
        spec(79, 'mixed', 'expert24', 5), // UK/6/recharged/sealed.
    ]) {
        const view = playStub(s);
        assertParity(view, directStub(s));
        for (const controller of COUNT_KEYS)
            for (const phase of PHASES) aggregate[controller][phase] += view.counts[controller][phase];
        for (let seat = 0; seat < s.players; seat++) assert(sum(view.seatCounts[seat]) > 0);
    }
    for (const controller of COUNT_KEYS) assert(sum(aggregate[controller]) > 0, controller);
    for (const controller of ['expert24', 'ppo0', 'ppo1', 'ppo2']) {
        assert(aggregate[controller].Auction > 0 && aggregate[controller].Building > 0, controller);
        assert.equal(aggregate[controller].Resources, 0);
        assert.equal(aggregate[controller].Bureaucracy, 0);
    }
    for (const controller of ['teacherV2', 'reference'])
        for (const phase of PHASES) assert(aggregate[controller][phase] > 0, `${controller}:${phase}`);
    for (const controller of ['fixedV1', 'fixedV2']) {
        assert(aggregate[controller].Resources > 0 && aggregate[controller].Bureaucracy > 0);
        assert(aggregate[controller].Auction > 0); // Forced learned-phase moves are fixed, not model calls.
    }
});

test('hard cap never fabricates terminal credit, including a pending policy or reference step', () => {
    for (const s of [firstPolicy(), firstReference()]) {
        const game = new x.StressGame(),
            view = game.start(s),
            before = JSON.stringify(game.g);
        game.steps = 4000;
        assert.throws(
            () => game.view(),
            (error) => error.code === 'STRESS_CAPPED'
        );
        assert.throws(
            () =>
                game.step(
                    view.kind === 'policy'
                        ? { op: 'step', index: 0 }
                        : { op: 'step', response: bound(view, f.legal(game.g, view.seat)[0]) }
                ),
            (error) => error.code === 'STRESS_CAPPED'
        );
        assert.equal(JSON.stringify(game.g), before);
        assert(!f.E.ended(game.g));
        assert.throws(() => outcome(game.g));
    }
});

test('JSON-lines errors are generic, bounded and fail-closed without raw state/action traces', () => {
    const bridge = path.join(__dirname, 'stress_game.cjs');
    const run = (lines) => {
        const result = spawnSync(process.execPath, [bridge], {
            input: lines.join('\n') + '\n',
            encoding: 'utf8',
            timeout: 15000,
            maxBuffer: 2 * 1024 * 1024,
        });
        assert.equal(result.status, 0);
        assert.equal(result.stderr, '');
        assert(!result.stdout.includes('SECRET-TRANSPORT-POISON'));
        return result.stdout
            .trim()
            .split('\n')
            .map((line) => JSON.parse(line));
    };
    const startLine = JSON.stringify({ op: 'start', spec: firstPolicy() });
    const rows = run([startLine, JSON.stringify({ op: 'label', state: 'SECRET-TRANSPORT-POISON' }), startLine]);
    assert.equal(rows[0].kind, 'policy');
    assert(!Object.hasOwn(rows[0], 'request'));
    assert.deepEqual(rows.slice(1), [{ error: 'stress-bridge-error' }, { error: 'stress-bridge-error' }]);
    for (const bad of ['{"SECRET-TRANSPORT-POISON":', 'null', 'x'.repeat(1024 * 1024 + 1)])
        assert.deepEqual(run([bad, startLine]), [{ error: 'stress-bridge-error' }, { error: 'stress-bridge-error' }]);
});
