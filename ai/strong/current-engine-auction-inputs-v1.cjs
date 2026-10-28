// Recompute current menus and public observations without generating games.
const assert = require('node:assert/strict'), path = require('node:path');
const crypto = require('node:crypto'), readline = require('node:readline');
const [oldRoot, newRoot] = process.argv.slice(2).map(x => path.resolve(x));
const load = root => ({
    c: require(path.join(root, 'ai/core.cjs')),
    beliefs: require(path.join(root, 'ai/strong/sealed-policy-beliefs.cjs')),
    prepare: require(path.join(root, 'ai/strong/population-hybrid-policy.cjs')).preparePolicy,
    scenario: require(path.join(root, 'engine/dist/src/analysis.js')).createAnalysisScenario,
});
const old = load(oldRoot), current = load(newRoot);
const clone = structuredClone;
const canonical = value => Array.isArray(value) ? value.map(canonical) : value && typeof value === 'object' ?
    Object.fromEntries(Object.keys(value).sort().filter(k => value[k] !== undefined).map(k => [k, canonical(value[k])])) : value;
const sha = value => crypto.createHash('sha256').update(JSON.stringify(canonical(value))).digest('hex');

function refresh(runtime, request) {
    const state = runtime.beliefs.publicState(request.state, request.player);
    state.players[request.player].availableMoves = runtime.c.E.availableMoves(state, state.players[request.player]);
    const prepared = runtime.prepare({state, player: request.player, featureRevision: '4.3-strategic-correction'});
    assert.deepEqual(prepared.moves, runtime.c.candidates(state, request.player));
    return {request: {...clone(request), state}, prepared};
}

function make(fixture, publicCheck) {
    const a = refresh(old, fixture.request), b = refresh(current, fixture.request);
    if (fixture.origin === 'natural-current' || fixture.origin === 'counterfactual-current')
        assert.deepEqual(b.prepared.moves, fixture.legal);
    else assert.deepEqual(a.prepared.moves, fixture.legal);
    const menusEqual = sha(a.prepared.moves) === sha(b.prepared.moves);
    if (menusEqual) assert.deepEqual(b.prepared, a.prepared, 'Unexplained public feature/prior/filter change');
    else {
        const g = b.request.state, seat = b.request.player;
        assert.equal(g.options.variant, 'recharged');
        assert.equal(g.phase, 'Auction'); assert(!g.chosenPowerPlant && g.plantDiscountActive);
        assert(g.players[seat].money >= 1 && g.players[seat].money < g.actualMarket[0].number);
        const added = b.prepared.moves.filter(x => !a.prepared.moves.some(y => sha(x) === sha(y)));
        assert.deepEqual(added, [{name: 'ChoosePowerPlant', data: g.actualMarket[0].number}]);
        assert.deepEqual(b.prepared.moves.filter(x => !added.includes(x)), a.prepared.moves);
    }
    let informationBoundary = false;
    if (publicCheck) {
        const hidden = clone(fixture.request), g = hidden.state;
        g.seed = 'PRIVATE-SEED-MUST-NOT-ENTER-POLICY';
        g.powerPlantsDeck = [{number: 9001, type: 8, cost: 99, citiesPowered: 99}];
        g.powerPlantDeckAfterStep3 = [{number: 9002}];
        g.hiddenLog = [{secret: 'PRIVATE-LOG'}]; g.automation = {plans: {0: 'PRIVATE-PLAN'}};
        g.players.forEach((p, i) => {p.lastMove = {name: 'PRIVATE-MOVE', data: i};
            if (g.options.fastBid) p.bid = 9000 + i;});
        if (g.options.fastBid) g.currentBid = 9000;
        const altered = refresh(current, hidden);
        assert.deepEqual(altered.prepared, b.prepared, 'Hidden data affected prepared observation');
        const seed = 'current-engine-information-boundary-v1';
        const left = current.scenario(b.request.state, {player: b.request.player, seed});
        const right = current.scenario(altered.request.state, {player: altered.request.player, seed});
        assert.deepEqual(right, left, 'Hidden data affected reconstructed public world');
        assert.equal(left.cardsLeft, b.request.state.cardsLeft);
        assert.equal(left.powerPlantsDeck.length, b.request.state.cardsLeft);
        informationBoundary = true;
    }
    return {...fixture, request: b.request, legal: b.prepared.moves,
        oldLegal: a.prepared.moves, menusEqual, preparedExact: sha(a.prepared) === sha(b.prepared),
        oldPreparedSha256: sha(a.prepared), preparedSha256: sha(b.prepared),
        options: b.prepared.options, informationBoundary};
}

readline.createInterface({input: process.stdin}).on('line', line => {
    try {
        const q = JSON.parse(line);
        process.stdout.write(JSON.stringify(q.fixtures.map(f => make(f, q.publicCheck))) + '\n');
    } catch (error) {process.stderr.write(error.stack + '\n'); process.exit(1);}
});

