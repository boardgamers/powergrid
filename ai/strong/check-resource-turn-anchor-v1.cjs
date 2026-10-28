// Stateless anchor validation on recorded actions; no inference or rollouts.
const assert = require('node:assert/strict');
const path = require('node:path');
const crypto = require('node:crypto');
const {isDeepStrictEqual} = require('node:util');
const {createResourceTurnAnchor} = require('./resource-turn-anchor-v1.cjs');
const runtime = path.resolve(process.argv[2]);
const c = require(path.join(runtime, 'ai/core.cjs'));
const {publicRoot} = require(path.join(runtime, 'ai/strong/resource-turn-search-v1.cjs'));
const {preparePolicy} = require(path.join(runtime, 'ai/strong/population-hybrid-policy.cjs'));
const {createAnalysisScenario} = require(path.join(runtime, 'engine/dist/src/analysis.js'));
const {rolesFor} = require(path.join(runtime, 'ai/strong/population-hybrid-continuations.cjs'));
const hash = value => crypto.createHash('sha256').update(JSON.stringify(value)).digest('hex');
const clone = value => structuredClone(value);
let request, positions, reference;

function latent(state, seat, seed) {
    return Array.from({length: 8}, (_, sample) => {
        const world = createAnalysisScenario(state, {player: seat, seed: seed + '-' + sample});
        const rng = c.seedrandom(seed + '-rollout-' + sample);
        return {sample, deckSha256: hash(world.powerPlantsDeck),
            roles: rolesFor('neural_population', seed, sample, state.players.length, seat),
            rolloutRngPrefix: Array.from({length: 4}, () => rng())};
    });
}

function prepared(q) {
    // A fresh instance for every request: the implementation has no turn cache.
    return createResourceTurnAnchor(runtime).prepare(q);
}

function handle(q) {
    if (q.op === 'reset') {
        request = {...q.request, featureRevision: '4.3-strategic-correction'};
        request.state = publicRoot(request); positions = [];
        reference = preparePolicy(request);
        assert.equal(prepared(request).resourceTurnAnchor.purchasesRewound, 0);
        return reference;
    }
    if (q.op === 'inspect') {
        const anchor = prepared(request), {resourceTurnAnchor, ...observation} = anchor;
        assert.deepEqual(observation, reference, 'Anchor differs from actual first-decision input');
        assert.equal(resourceTurnAnchor.purchasesRewound, positions.length);
        const polluted = clone(request), seat = request.player;
        polluted.requestId = 'unrelated-request-id'; polluted.state.seed = 'unavailable-secret';
        polluted.state.powerPlantsDeck = [{number: 999}]; polluted.state.hiddenLog = [{private: 'ignored'}];
        polluted.state.powerPlantDeckAfterStep3 = [{number: 998}];
        polluted.state.automation = {version: 1, plans: {[(seat+1)%request.state.players.length]: {private:'ignored'}},
            increments: request.state.players.map(() => 1), liveUpdate: true};
        if (polluted.state.options.fastBid) polluted.state.players.forEach((p, i) => {if(i!==seat)p.bid=100000+i;});
        assert.deepEqual(prepared(polluted), anchor, 'Private fields or request ID affect anchor');
        assert.deepEqual(prepared(request), anchor, 'Duplicate request affects anchor');
        const worlds = latent(request.state, seat, q.seed);
        if (positions.length) assert.deepEqual(worlds, positions[0].worlds, 'Latent sampling drift');
        positions.push({request: clone(request), anchor, worlds});
        return {anchor, worlds, privateFieldControl: true, duplicateControl: true,
            currentPrepared: preparePolicy(request)};
    }
    if (q.op === 'move') {
        assert.equal(q.move.name, 'BuyResource');
        assert(c.allLegal(request.state, request.player).some(m => isDeepStrictEqual(m, q.move)));
        const metadata = {cardsLeft: request.state.cardsLeft, nextCardWeak: request.state.nextCardWeak};
        c.E.move(request.state, clone(q.move), request.player); Object.assign(request.state, metadata);
        request.state = publicRoot(request);
        return {phase: request.state.phase, currentPlayers: request.state.currentPlayers};
    }
    if (q.op === 'finish') {
        let rejected = 0;
        for (const item of positions.slice().reverse()) assert.deepEqual(prepared(item.request), item.anchor);
        const mutations = [
            r => {r.state.log = [];},
            r => {r.state.phase = 'Building';},
            r => {r.state.options.showMoney = false;},
            r => {r.state.map.name = 'USA';},
            r => {r.state.newTurn = !r.state.newTurn;},
        ];
        if (positions.length > 1) mutations.push(
            r => {r.state.log.at(-1).move.data.side = 'north';},
            r => {r.state.log.at(-1).move.fromSupply = true;},
            r => {r.state.players[r.player][r.state.log.at(-1).move.data.resource+'Left'] = 0;},
            r => {r.state.log.pop();},
        );
        // Test a single-purchase state so a missing log entry has an observable
        // newTurn mismatch rather than silently treating a truncated prefix as
        // authentic history. Arbitrary forged history is not authenticated here.
        const tested = positions[Math.min(1, positions.length-1)].request;
        for (const mutate of mutations) {
            const bad = clone(tested); mutate(bad);
            assert.throws(() => prepared(bad)); rejected++;
        }
        // In Germany this option does not change prices or the observation.
        const noTotals = clone(positions[0].request); noTotals.state.options.trackTotalSpent = false;
        const expected = preparePolicy(noTotals);
        if (positions.length > 1) {
            const metadata = {cardsLeft: noTotals.state.cardsLeft, nextCardWeak: noTotals.state.nextCardWeak};
            c.E.move(noTotals.state, clone(positions[1].request.state.log.at(-1).move), noTotals.player);
            Object.assign(noTotals.state, metadata);
        }
        const without = prepared(noTotals), {resourceTurnAnchor, ...input} = without;
        assert.deepEqual(input, expected);
        return {positions: positions.length, reversedRequestChecks: positions.length,
            invalidRequestsRejected: rejected, untrackedSpendControl: true};
    }
    throw new Error('Unknown anchor validation operation');
}

(async () => {
    for await (const line of require('node:readline').createInterface({input: process.stdin})) {
        console.log(JSON.stringify(handle(JSON.parse(line))));
    }
})().catch(error => {console.error(error.stack); process.exit(1);});
