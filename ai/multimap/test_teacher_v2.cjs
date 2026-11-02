// Mechanics/legality regression tests only: no qualification, training or datasets.
const assert = require('node:assert/strict');
const { test } = require('node:test');
const f = require('./features.cjs');
const { E, RES } = f;
const eco = require('./economics_v2.cjs');
const teacher = require('./teacher_v2.cjs');
const oldTeacher = require('./teacher.cjs');
const oldEco = require('../strong/economics.cjs');
const { powerPlants } = require('../../engine/dist/src/powerPlants.js');
const styles = ['geographic', 'economic', 'rush'];
const spec = { map: 'Germany', players: 4, variant: 'recharged', fastBid: true };
const start = (overrides = {}) => {
    const s = { ...spec, ...overrides };
    return E.setup(
        s.players,
        { map: s.map, variant: s.variant, fastBid: s.fastBid, showMoney: true },
        s.seed || 'teacher-v2-mechanics-only'
    );
};
const pp = (number) => structuredClone(powerPlants.find((p) => p.number === number));
function install(g, seat, plants, count, fuel = [0, 0, 0, 0]) {
    const p = g.players[seat];
    p.powerPlants = plants;
    p.powerPlantsNotUsed = plants.map((p) => p.number);
    p.cities = g.map.cities.slice(0, count).map((c) => ({ name: c.name, price: 10 }));
    p.housesLeft = 22 - count;
    p.citiesPowered = 0;
    p.hybridCapacity = plants.filter((p) => p.type === 4).reduce((s, p) => s + p.cost * 2, 0);
    RES.forEach((r, i) => {
        p[r + 'Left'] = fuel[i];
        p[r + 'Capacity'] = plants.filter((p) => p.type === i).reduce((s, p) => s + p.cost * 2, 0);
    });
    return p;
}
function ready(g, phase, seat = 0) {
    g.phase = phase;
    g.round = 10;
    g.step = 3;
    g.currentPlayers = [seat];
    g.playerOrder = g.players.map((_, i) => i);
    g.chosenPowerPlant = null;
    g.players.forEach((p) => {
        p.passed = p.id !== seat;
        p.availableMoves = null;
    });
    g.players[seat].availableMoves = E.availableMoves(g, g.players[seat]);
    return g;
}
function legalMove(g, a, seat = 0) {
    assert(
        f.legal(g, seat).some((b) => JSON.stringify(a) === JSON.stringify(b)),
        'engine-generated legal action'
    );
    E.move(g, structuredClone(a), seat);
}
function hybridFixture() {
    const g = start();
    install(g, 0, [pp(21), pp(15)], 7, [3, 1, 0, 0]);
    return ready(g, E.Phase.Bureaucracy);
}
function buildFixture() {
    const g = start();
    install(g, 0, [pp(37), pp(36), pp(46)], 16);
    install(g, 1, [pp(33), pp(44), pp(50)], 15);
    g.players[0].money = 200;
    g.players[1].money = 50;
    return ready(g, E.Phase.Building);
}
// TEST-ONLY historical v2 policy: retain the pre-repair one-build finish veto
// while replaying the original smoke trajectory. The repaired policy can diverge
// before move 706. No production export or frozen v1 helper is replaced/patched.
function preContinuationRepairChoice(g, seat, actions, style) {
    const values = teacher.scores(g, seat, actions, style);
    const p = g.players[seat],
        next = p.cities.length + 1;
    if (g.phase === E.Phase.Building && next >= g.citiesToEndGame) {
        const snapshotPower = eco.plan(g, p, next, { buy: false, endgame: true }).powered;
        const opponents = g.players
            .filter((_, i) => i !== seat)
            .map((q) => ({
                power: eco.plan(g, q, q.cities.length, { buy: false, endgame: true }).powered,
                money: q.money,
                cities: q.cities.length,
            }));
        actions.forEach((a, i) => {
            if (
                a.name === 'Build' &&
                opponents.some(
                    (q) =>
                        q.power > snapshotPower ||
                        (q.power === snapshotPower &&
                            (q.money > p.money - a.data.price ||
                                (q.money === p.money - a.data.price && q.cities > next)))
                )
            )
                values[i] = -30;
        });
    }
    // Default teacher tie-breaking adds the same constant to every score.
    const index = values.indexOf(Math.max(...values));
    return { action: actions[index], index, values };
}
function twoBuildTrajectoryFixture() {
    const g = start({
        fastBid: false,
        seed: 'teacher-v2-smoke-only:Germany:4:recharged:false',
    });
    for (let step = 0; step < 706; step++) {
        assert(!E.ended(g));
        const seat = g.currentPlayers[0],
            actions = f.legal(g, seat);
        const choice = preContinuationRepairChoice(g, seat, actions, styles[(seat + 10) % 3]);
        legalMove(g, choice.action, seat);
    }
    return g;
}
function coalFixture(owned = 2, canonical = false) {
    const g = start({ map: 'USA' });
    // Reproduce the reported small synthetic portfolio; also exercise canonical #10.
    install(g, 0, [canonical ? pp(10) : { number: 8, type: 0, cost: 2, citiesPowered: 3 }], owned);
    g.players[0].money = 100;
    g.coalMarket = 0;
    g.coalSupply = 10;
    return ready(g, E.Phase.Resources);
}
function freeze(x) {
    if (x && typeof x === 'object' && !Object.isFrozen(x)) {
        Object.values(x).forEach(freeze);
        Object.freeze(x);
    }
    return x;
}
function assertAllocation(p, plan, unused = false) {
    assert.equal(new Set(plan.plants).size, plan.plants.length);
    assert.deepEqual(
        plan.allocations.map((x) => x.powerPlant),
        plan.plants
    );
    const sum = [0, 0, 0, 0];
    let power = 0;
    for (const a of plan.allocations) {
        const plant = p.powerPlants.find((p) => p.number === a.powerPlant);
        assert(plant);
        if (unused) assert(p.powerPlantsNotUsed.includes(a.powerPlant));
        assert.equal(
            a.used.reduce((x, y) => x + y, 0),
            plant.cost
        );
        if (plant.type < 4) assert(a.used.every((v, i) => !v || plant.type === i));
        if (plant.type === 4) assert.equal(a.used[2] + a.used[3], 0);
        a.used.forEach((v, i) => {
            sum[i] += v;
        });
        power += plant.citiesPowered;
    }
    assert.deepEqual(sum, plan.used);
    assert.equal(power, plan.power);
    RES.forEach((r, i) => assert(sum[i] <= p[r + 'Left']));
}

// Independent small recursive oracle: enumerate legal sequential firings, not
// economics.plans/fuelVariants nor the imperfect frozen reference policy.
function oracle(g, p, endgame = false) {
    const prices = RES.map((r) =>
        g[r + 'Market'] > 0 ? g[r + 'Prices'][g[r + 'Prices'].length - g[r + 'Market']] : 20
    );
    const target = p.cities.length;
    let best = { score: -Infinity, powered: -1 };
    function visit(plants, left, power, spent) {
        const powered = Math.min(target, power);
        const score = (endgame ? powered * 1000 : g.paymentTable[powered]) - spent * 0.2;
        if ((endgame && powered > best.powered) || ((!endgame || powered === best.powered) && score > best.score))
            best = { score, powered };
        for (let index = 0; index < plants.length; index++) {
            const plant = plants[index],
                variants = [];
            if (plant.type === 4) {
                for (let coal = 0; coal <= plant.cost; coal++) variants.push([coal, plant.cost - coal, 0, 0]);
            } else {
                const need = [0, 0, 0, 0];
                if (plant.type < 4) need[plant.type] = plant.cost;
                variants.push(need);
            }
            for (const need of variants)
                if (need.every((n, i) => n <= left[i]))
                    visit(
                        plants.filter((_, j) => j !== index),
                        left.map((n, i) => n - need[i]),
                        power + plant.citiesPowered,
                        spent + need.reduce((s, n, i) => s + n * prices[i], 0)
                    );
        }
    }
    visit(
        p.powerPlants.filter((pp) => p.powerPlantsNotUsed.includes(pp.number)),
        RES.map((r) => p[r + 'Left']),
        p.citiesPowered,
        0
    );
    return best;
}
function executeProduction(g, style = 'geographic', reversed = false) {
    let moves = 0;
    while (true) {
        const actions = f.legal(g, 0);
        if (reversed) actions.reverse();
        const a = teacher.choose(g, 0, actions, style).action;
        if (a.name === 'Pass') return moves;
        assert.equal(a.name, 'UsePowerPlant');
        legalMove(g, a);
        assert(++moves <= 4);
    }
}

test('v2 has independent schemas/exports and never replaces frozen exports', () => {
    assert.equal(teacher.SCHEMA, 'multimap-teacher-v2');
    assert.equal(eco.SCHEMA, 'multimap-economics-v2');
    for (const name of ['plans', 'plan', 'purchaseCost', 'purchaseCosts', 'scores'])
        assert.notEqual(eco[name], oldEco[name]);
    assert.notEqual(teacher.choose, oldTeacher.choose);
    assert.equal(require('./teacher.cjs'), oldTeacher);
    assert.equal(require('../strong/economics.cjs'), oldEco);
});

test('legal Build fixture: fueled finish guard precedes rich/late/rush/geographic fallback', () => {
    for (const style of styles)
        for (const [money, round] of [
            [200, 10],
            [100, 19],
            [100, 10],
        ]) {
            const g = buildFixture(),
                p = g.players[0];
            p.money = money;
            g.round = round;
            p.availableMoves = E.availableMoves(g, p);
            const actions = f.legal(g, 0);
            assert(actions.some((a) => a.name === 'Build'));
            const guard = eco.finishGuard(g, 0);
            assert.equal(guard.ownPower, 4);
            assert.equal(guard.opponents[0].power, 15);
            assert(f.capacity(p) > f.capacity(g.players[1]), 'nominal capacity gives the wrong comparison');
            assert.equal(teacher.choose(g, 0, actions, style).action.name, 'Pass');
            if (money > 140 || round > 18) assert.equal(oldTeacher.choose(g, 0, actions, style).action.name, 'Build');
            const counterfactual = structuredClone(g);
            legalMove(
                counterfactual,
                actions.find((a) => a.name === 'Build')
            );
            legalMove(counterfactual, { name: 'Pass', data: true });
            assert(E.ended(counterfactual));
            assert.equal(counterfactual.players[0].citiesPowered, 4);
            assert.equal(E.playersSortedByScore(counterfactual)[0].id, 1);
            legalMove(g, teacher.choose(g, 0, actions, style).action);
            assert(!E.ended(g));
        }
});

test('finish guard uses CURRENT opponent network, focal output ceiling and strict cash tiebreaks', () => {
    const g = buildFixture(),
        p = g.players[0];
    // Opponent nominal capacity 15 but only three existing cities: do not invent future builds.
    g.players[1].cities = g.players[1].cities.slice(0, 3);
    assert.equal(eco.finishGuard(g, 0).opponents[0].power, 3);
    assert.equal(teacher.choose(g, 0).action.name, 'Build');
    g.players[1].cities = g.map.cities.slice(0, 4).map((c) => ({ name: c.name }));
    g.players[1].money = p.money;
    assert.equal(teacher.choose(g, 0).action.name, 'Pass', 'build cost loses cash tiebreak');
    g.players[1].money = 0;
    assert.equal(teacher.choose(g, 0).action.name, 'Build');
    const equal = { triggered: true, ownPower: 4, opponents: [{ power: 4, money: 190, cities: 18 }] };
    assert(!eco.losingFinish(equal, p, 10), 'city-count veto omitted: later builds could change the tie');
    equal.opponents[0].cities = 17;
    assert(!eco.losingFinish(equal, p, 10), 'exact tie is not a known loss');
    equal.opponents[0].money++;
    assert(eco.losingFinish(equal, p, 10), 'strictly worse cash cannot improve through more builds');
    p.cities.pop();
    assert.equal(eco.finishGuard(g, 0).triggered, false);
    assert.equal(teacher.choose(g, 0).action.name, 'Build', 'nonterminal rich fallback preserved');
});

test('natural 706-move regression: preserve the winning Bremen/Hannover continuation after end is triggered', () => {
    const g = twoBuildTrajectoryFixture(),
        p = g.players[2];
    assert.equal(g.phase, E.Phase.Building);
    assert.equal(g.round, 11);
    assert.equal(g.citiesToEndGame, 17);
    assert.deepEqual(g.currentPlayers, [2]);
    assert(g.players.every((q) => q.passed === (q.id !== 2)));
    assert.equal(p.cities.length, 16);
    assert.equal(p.money, 74);
    assert.deepEqual(
        p.powerPlants.map((plant) => plant.number),
        [20, 40, 38]
    );
    assert.deepEqual(
        RES.map((r) => p[r + 'Left']),
        [3, 2, 3, 0]
    );
    assert.equal(g.players[0].cities.length, 17);
    assert.equal(g.players[0].money, 67);
    const guard = eco.finishGuard(g, 2);
    assert.equal(guard.ownPower, 18, 'optimistic full-fuel ceiling, NOT the next-city snapshot of 17');
    assert.deepEqual(guard.opponents[0], { power: 17, money: 67, cities: 17 });
    const actions = f.legal(g, 2);
    const oldChoice = preContinuationRepairChoice(g, 2, actions, 'geographic');
    assert.equal(oldChoice.action.name, 'Pass');
    actions.forEach((a, i) => {
        if (a.name === 'Build') assert.equal(oldChoice.values[i], -30);
    });
    const pass = structuredClone(g);
    legalMove(pass, oldChoice.action, 2);
    assert(E.ended(pass));
    assert.equal(E.playersSortedByScore(pass)[0].id, 0);
    assert.equal(pass.players[2].citiesPowered, 16);

    // The first build alone really loses the cash tiebreak. That is not a
    // certificate about the two-build continuation, even though opponents have
    // already triggered the end and all passed.
    const firstOnly = structuredClone(g);
    const bremen = actions.find((a) => a.name === 'Build' && a.data.name === 'Bremen');
    assert.equal(bremen.data.price, 28);
    legalMove(firstOnly, bremen, 2);
    assert(!E.ended(firstOnly), 'threshold does not stop Building');
    legalMove(firstOnly, { name: 'Pass', data: true }, 2);
    assert(E.ended(firstOnly));
    assert.equal(firstOnly.players[2].citiesPowered, 17);
    assert.equal(firstOnly.players[2].money, 46);
    assert.equal(E.playersSortedByScore(firstOnly)[0].id, 0);

    for (const style of styles)
        for (const prescribedRoute of [true, false]) {
            const h = structuredClone(g);
            for (const [name, price] of [
                ['Bremen', 28],
                ['Hannover', 30],
            ]) {
                const legal = f.legal(h, 2),
                    choice = teacher.choose(h, 2, legal, style);
                const routeIndex = legal.findIndex((a) => a.name === 'Build' && a.data.name === name);
                assert(routeIndex >= 0);
                assert.equal(legal[routeIndex].data.price, price);
                assert(choice.values[routeIndex] > 0, 'reported winning continuation is not vetoed');
                assert(!eco.losingFinish(eco.finishGuard(h, 2), h.players[2], price));
                // Equal-price choices need not match the reported route (e.g.
                // economic can choose Köln second); both routes must still win.
                assert.equal(choice.action.name, 'Build');
                assert.equal(choice.action.data.price, price);
                legalMove(h, prescribedRoute ? legal[routeIndex] : choice.action, 2);
                assert(!E.ended(h));
                assert.deepEqual(h.currentPlayers, [2]);
            }
            assert.equal(h.players[2].cities.length, 18);
            assert.equal(h.players[2].money, 16);
            assert.equal(teacher.choose(h, 2, f.legal(h, 2), style).action.name, 'Pass');
            legalMove(h, { name: 'Pass', data: true }, 2);
            assert(E.ended(h));
            assert.equal(h.players[2].citiesPowered, 18, 'engine powers automatically; no Bureaucracy policy ran');
            assert.equal(E.playersSortedByScore(h)[0].id, 2);
        }
});

test('17-power ceiling still vetoes a first build losing the 17-power opponent cash tiebreak', () => {
    const g = start();
    const p = install(g, 0, [pp(20), pp(40), pp(42)], 16, [5, 2, 0, 0]);
    const q = install(g, 1, [pp(30), pp(32), pp(35)], 17, [0, 4, 3, 0]);
    p.money = 74;
    q.money = 67;
    ready(g, E.Phase.Building);
    const guard = eco.finishGuard(g, 0),
        actions = f.legal(g, 0);
    assert.equal(guard.ownPower, 17);
    assert.equal(guard.opponents[0].power, 17);
    assert(actions.some((a) => a.name === 'Build'));
    actions
        .filter((a) => a.name === 'Build')
        .forEach((a) => {
            assert(p.money - a.data.price < q.money);
            assert(eco.losingFinish(guard, p, a.data.price));
        });
    for (const style of styles) assert.equal(teacher.choose(g, 0, actions, style).action.name, 'Pass');
    legalMove(
        g,
        actions.find((a) => a.name === 'Build')
    );
    legalMove(g, { name: 'Pass', data: true });
    assert(E.ended(g));
    assert.equal(p.citiesPowered, 17);
    assert.equal(q.citiesPowered, 17);
    assert.equal(E.playersSortedByScore(g)[0].id, 1);
});

test('legal hybrid fixture: per-plant fuel splits execute all seven cities in any ordering/style', () => {
    const baseline = hybridFixture();
    const bad = oldTeacher.choose(baseline, 0).action;
    assert.equal(bad.data.powerPlant, 21);
    assert.deepEqual(bad.data.resourcesSpent, ['coal', 'coal']);
    legalMove(baseline, bad);
    assert.equal(oldTeacher.choose(baseline, 0).action.name, 'Pass');
    assert.equal(baseline.players[0].citiesPowered, 4);
    for (const style of styles)
        for (const reversePlants of [false, true])
            for (const reverseMoves of [false, true])
                for (const endgame of [false, true]) {
                    const g = hybridFixture(),
                        p = g.players[0];
                    if (endgame) g.citiesToEndGame = 7;
                    if (reversePlants) p.powerPlants.reverse();
                    const plan = eco.plan(g, p, 7, { buy: false, unused: true, endgame });
                    assertAllocation(p, plan, true);
                    assert.deepEqual(plan.allocations.find((a) => a.powerPlant === 21).used, [1, 1, 0, 0]);
                    assert.equal(executeProduction(g, style, reverseMoves), 2);
                    assert.equal(p.citiesPowered, 7);
                    assert.equal(p.coalLeft + p.oilLeft, 0);
                }
});

test('legal USA supply fixture: both target planner and repeated engine purchases buy needed $8 coal', () => {
    for (const style of styles)
        for (const owned of [2, 3])
            for (const canonical of [false, true]) {
                const g = coalFixture(owned, canonical),
                    p = g.players[0];
                assert.equal(oldEco.context(g, 0).fuel.used[0], 0);
                assert.equal(oldTeacher.choose(g, 0, f.legal(g, 0), style).action.name, 'Pass');
                assert.equal(eco.context(g, 0).fuel.used[0], 2);
                assert.equal(eco.purchaseCost(g, p, [2, 0, 0, 0]), 16);
                for (let i = 0; i < 2; i++) {
                    const a = teacher.choose(g, 0, f.legal(g, 0), style).action;
                    assert.equal(a.name, 'BuyResource');
                    assert.equal(a.data.resource, 'coal');
                    legalMove(g, a);
                }
                assert.equal(p.money, 84);
                assert.equal(p.coalLeft, 2);
                assert.equal(g.coalSupply, 8);
                assert.equal(teacher.choose(g, 0).action.name, 'Pass');
                assert.equal(eco.plan(g, p, owned, { buy: false }).powered, canonical ? 2 : owned);
            }
});

test('USA exact mixed market/supply quotes, budgets, stock limits and per-call cache isolation', () => {
    const g = coalFixture(),
        p = g.players[0];
    g.coalMarket = 2;
    g.coalSupply = 3;
    p.coalLeft = 1;
    const prices = g.coalPrices.slice(-2);
    const expected = [
        0,
        0,
        prices[0],
        prices[0] + prices[1],
        prices[0] + prices[1] + 8,
        prices[0] + prices[1] + 16,
        prices[0] + prices[1] + 24,
        Infinity,
    ];
    const cached = eco.purchaseCosts(g, p);
    const oilPrice = g.oilPrices[g.oilPrices.length - g.oilMarket];
    assert.equal(cached([6, 1, 0, 0]), expected[6] + oilPrice);
    assert.equal(eco.purchaseCost(g, p, [6, 1, 0, 0]), expected[6] + oilPrice);
    assert.equal(cached([6, g.oilMarket + 1, 0, 0]), Infinity);
    for (const n of [7, 4, 2, 6, 0, 3, 1, 5, 4]) {
        assert.equal(cached([n, 0, 0, 0]), expected[n]);
        assert.equal(eco.purchaseCost(g, p, [n, 0, 0, 0]), expected[n]);
    }
    // Exercise the quote through legal market-then-supply moves too.
    for (let i = 0; i < 3; i++) {
        p.availableMoves = E.availableMoves(g, p);
        legalMove(
            g,
            f.legal(g, 0).find((a) => a.name === 'BuyResource' && a.data.resource === 'coal')
        );
    }
    assert.equal(100 - p.money, prices[0] + prices[1] + 8);
    assert.equal(p.coalLeft, p.coalCapacity);
    assert(
        !f.legal(g, 0).some((a) => a.name === 'BuyResource' && a.data.resource === 'coal'),
        'engine storage limit honored'
    );
    g.coalMarket = 0;
    g.coalSupply = 0;
    p.coalLeft = 0;
    assert.equal(eco.purchaseCost(g, p, [1, 0, 0, 0]), Infinity);
    assert.equal(cached([6, 0, 0, 0]), expected[6], 'cache retains its call-local stock/holding snapshot');
    g.coalSupply = 1;
    assert.equal(eco.purchaseCost(g, p, [2, 0, 0, 0]), Infinity);
    assert.equal(eco.context(g, 0).fuel.powered, 0);
    g.coalSupply = 2;
    p.money = 15;
    assert.equal(eco.context(g, 0).fuel.powered, 0);
    p.money = 16;
    assert.equal(eco.context(g, 0).fuel.powered, 3);
    g.coalMarket = 1;
    g.coalPrices = [];
    assert.equal(eco.purchaseCost(g, p, [1, 0, 0, 0]), Infinity);
});

test('supply exceptions fail closed on every other scoped map/variant/resource', () => {
    for (const map of f.MAPS)
        for (const variant of ['original', 'recharged']) {
            const g = start({ map, variant }),
                p = g.players[0];
            RES.forEach((r) => {
                g[r + 'Market'] = 0;
                g[r + 'Supply'] = 10;
            });
            const cached = eco.purchaseCosts(g, p);
            RES.forEach((r, i) => {
                const use = [0, 0, 0, 0];
                use[i] = 1;
                const expected = map === 'USA' && variant === 'recharged' && r === 'coal' ? 8 : Infinity;
                assert.equal(cached(use), expected);
                assert.equal(eco.purchaseCost(g, p, use), expected);
            });
        }
});

test('enumerated production plans/continuations match an independent small brute-force oracle', () => {
    const g = start();
    const portfolios = [
        [15, 21],
        [12, 21, 16],
        [15, 21, 13],
        [6, 11, 21],
        [13, 18, 22, 27],
    ];
    let cases = 0;
    for (const plants of portfolios)
        for (let coal = 0; coal <= 4; coal++)
            for (let oil = 0; oil <= 3; oil++)
                for (const target of [2, 5, 7])
                    for (const already of [0, 1])
                        for (const endgame of [false, true]) {
                            const p = install(g, 0, plants.map(pp), target, [coal, oil, 1, 1]);
                            p.citiesPowered = already;
                            if (already) p.powerPlantsNotUsed = p.powerPlantsNotUsed.slice(1);
                            const reference = oracle(g, p, endgame);
                            const plan = eco.plan(g, p, target, { buy: false, unused: true, endgame });
                            assertAllocation(p, plan, true);
                            assert(Math.abs(plan.score - reference.score) < 1e-8);
                            if (endgame) assert.equal(plan.powered, reference.powered);
                            const reversed = {
                                ...p,
                                powerPlants: [...p.powerPlants].reverse(),
                                powerPlantsNotUsed: [...p.powerPlantsNotUsed].reverse(),
                            };
                            assert.deepEqual(
                                eco.plan(g, reversed, target, { buy: false, unused: true, endgame }),
                                plan
                            );
                            // Every selected first firing must admit an optimal continuation.
                            for (const a of plan.allocations) {
                                const plant = p.powerPlants.find((pp) => pp.number === a.powerPlant);
                                const q = {
                                    ...p,
                                    citiesPowered: p.citiesPowered + plant.citiesPowered,
                                    powerPlantsNotUsed: p.powerPlantsNotUsed.filter((n) => n !== a.powerPlant),
                                };
                                let spent = 0;
                                RES.forEach((r, i) => {
                                    q[r + 'Left'] -= a.used[i];
                                    const price = g[r + 'Market']
                                        ? g[r + 'Prices'][g[r + 'Prices'].length - g[r + 'Market']]
                                        : 20;
                                    spent += a.used[i] * price;
                                });
                                const cont = eco.plan(g, q, target, { buy: false, unused: true, endgame });
                                assertAllocation(q, cont, true);
                                assert(Math.abs(cont.score - spent * 0.2 - plan.score) < 1e-8);
                                assert(Math.abs(cont.score - oracle(g, q, endgame).score) < 1e-8);
                            }
                            cases++;
                        }
    assert.equal(cases, 1200);
});

test('normal income/opportunity cost may save fuel, whereas endgame maximizes power', () => {
    const g = start();
    const p = install(g, 0, [pp(13), pp(8)], 2, [3, 0, 0, 0]);
    g.coalMarket = 0;
    const normal = eco.plan(g, p, 2, { buy: false });
    const end = eco.plan(g, p, 2, { buy: false, endgame: true });
    assert.equal(normal.powered, 1); // $11 extra income is less than the $12 opportunity penalty.
    assert.equal(end.powered, 2);
    for (const endgame of [false, true]) {
        const h = structuredClone(g);
        ready(h, E.Phase.Bureaucracy);
        if (endgame) h.citiesToEndGame = 2;
        executeProduction(h);
        assert.equal(Math.min(2, h.players[0].citiesPowered), endgame ? 2 : 1);
    }
});

test('USA supply returns during firing do not change the continuation opportunity-cost objective', () => {
    const g = hybridFixture(),
        p = g.players[0];
    g.map.name = 'USA';
    g.options.map = 'USA';
    g.coalMarket = 0;
    g.coalSupply = 0;
    const initial = eco.plan(g, p, 7, { buy: false, unused: true });
    const a = teacher.choose(g, 0).action;
    const spent = a.data.resourcesSpent.reduce(
        (s, r) => s + (g[r + 'Market'] ? g[r + 'Prices'][g[r + 'Prices'].length - g[r + 'Market']] : 20),
        0
    );
    legalMove(g, a);
    assert(g.coalSupply > 0);
    const continuation = eco.plan(g, p, 7, { buy: false, unused: true });
    assert(Math.abs(continuation.score - spent * 0.2 - initial.score) < 1e-8);
    executeProduction(g);
    assert.equal(p.citiesPowered, 7);
});

test('state-global read-only/hidden-state invariant on all three fixtures and auctions', () => {
    const auction = start();
    const cases = [buildFixture(), hybridFixture(), coalFixture(), auction];
    for (const original of cases) {
        const g = structuredClone(original),
            seat = g.currentPlayers[0];
        const actions = f.legal(g, seat),
            serialized = JSON.stringify(g);
        const base = styles.map((style) => teacher.scores(g, seat, actions, style));
        const plan = eco.plan(g, g.players[seat]);
        freeze(g);
        freeze(actions);
        styles.forEach((style, i) => assert.deepEqual(teacher.choose(g, seat, actions, style).values, base[i]));
        assertAllocation(g.players[seat], eco.plan(g, g.players[seat], undefined, { buy: false }));
        assert.equal(JSON.stringify(g), serialized);
        const hidden = structuredClone(original);
        const forbidden = [
            'seed',
            'powerPlantsDeck',
            'powerPlantDeckAfterStep3',
            'hiddenLog',
            'log',
            'poweringChoices',
            'automation',
            'currentBid',
        ];
        forbidden.forEach((key) =>
            Object.defineProperty(hidden, key, {
                get() {
                    throw Error('hidden read: ' + key);
                },
                configurable: true,
            })
        );
        hidden.players.forEach((p) =>
            ['bid', 'lastMove'].forEach((key) =>
                Object.defineProperty(p, key, {
                    get() {
                        throw Error('hidden player read: ' + key);
                    },
                    configurable: true,
                })
            )
        );
        styles.forEach((style, i) => assert.deepEqual(teacher.scores(hidden, seat, actions, style), base[i]));
        assert.deepEqual(eco.plan(hidden, hidden.players[seat]), plan);
        // No global retained cache: changing public holdings changes the result,
        // and replaying the original state returns the original answer.
        const other = hybridFixture();
        other.players[0].coalLeft = 0;
        teacher.scores(other, 0);
        assert.deepEqual(teacher.scores(g, seat, actions), base[0]);
    }
});

test('two-player four-plant valuation, actual minimum pricing, all bids and style fallbacks remain', () => {
    const g = start({ players: 2 }),
        p = install(g, 0, [pp(13), pp(18), pp(22)], 5);
    p.money = 200;
    assert.equal(teacher.plantValue(g, p, pp(27)), oldTeacher.plantValue(g, p, pp(27)));
    const withRoom = teacher.plantValue(g, p, pp(27));
    g.players.push(structuredClone(g.players[1]));
    assert(teacher.plantValue(g, p, pp(27)) < withRoom, 'three-player limit remains three');
    const auction = start();
    const seat = auction.currentPlayers[0];
    auction.round = 2;
    auction.actualMarket = [pp(50)];
    auction.plantDiscountActive = true;
    auction.players[seat].money = 30;
    assert(E.availableMoves(auction, auction.players[seat]).ChoosePowerPlant.includes(50));
    const moves = [
        { name: 'ChoosePowerPlant', data: 50 },
        { name: 'Pass', data: true },
    ];
    assert(teacher.scores(auction, seat, moves)[0] > 0, 'discount nomination compares to $1, not plant number');
    auction.plantDiscountActive = false;
    assert(!E.availableMoves(auction, auction.players[seat]).ChoosePowerPlant?.includes(50));
    assert(teacher.scores(auction, seat, moves)[0] < 0);
    auction.players[seat].availableMoves = { Bid: Array.from({ length: 501 }, (_, i) => i) };
    assert.equal(f.legal(auction, seat).length, 501);
    assert.equal(teacher.scores(auction, seat).length, 501);
    assert.throws(() => teacher.scores(auction, seat, moves, 'unknown'));
    auction.options.showMoney = false;
    assert.throws(() => teacher.scores(auction, seat, moves));
});

test('UK second-island safety is preserved, but cannot bypass the finish guard', () => {
    const g = start({ map: 'UK & Ireland' });
    install(g, 0, [pp(13)], 1);
    g.players[0].money = 200;
    ready(g, E.Phase.Building);
    const home = g.map.cities.find((c) => c.name === g.players[0].cities[0].name).island;
    for (const style of styles) {
        const action = teacher.choose(g, 0, f.legal(g, 0), style).action;
        assert.equal(action.name, 'Build');
        assert.notEqual(g.map.cities.find((c) => c.name === action.data.name).island, home);
    }
    g.citiesToEndGame = 2;
    install(g, 1, [pp(18)], 2);
    g.players[0].availableMoves = E.availableMoves(g, g.players[0]);
    for (const style of styles) assert.equal(teacher.choose(g, 0, f.legal(g, 0), style).action.name, 'Pass');
});

test('120 scoped cells finish legal full games across rotating styles (smoke only, zero qualification)', () => {
    let cells = 0,
        totalSteps = 0;
    for (const map of f.MAPS)
        for (const players of [2, 3, 4, 5, 6])
            for (const variant of ['original', 'recharged'])
                for (const fastBid of [false, true]) {
                    const seed = `teacher-v2-smoke-only:${map}:${players}:${variant}:${fastBid}`;
                    const g = start({ map, players, variant, fastBid, seed });
                    let steps = 0;
                    while (!E.ended(g)) {
                        assert(steps < 4000, `capped smoke cell: ${seed}`);
                        const seat = g.currentPlayers[0],
                            actions = f.legal(g, seat);
                        const decision = teacher.choose(g, seat, actions, styles[(seat + cells) % 3]);
                        assert(decision.values.every(Number.isFinite));
                        assert.equal(decision.action, actions[decision.index]);
                        E.move(g, structuredClone(decision.action), seat);
                        steps++;
                    }
                    assert(g.players.some((p) => p.cities.length >= g.citiesToEndGame));
                    totalSteps += steps;
                    cells++;
                }
    assert.equal(cells, 120);
    console.log(`v2 mechanics smoke: ${cells} terminal cells, ${totalSteps} legal moves; zero qualification games`);
});
