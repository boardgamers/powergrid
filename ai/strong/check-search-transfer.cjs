// Exercise the unchanged bridge's actual step handler. Stub only the expensive
// search and engine transition: this checks routing, not game strength/legality.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const readline = require('node:readline');
const path = require('node:path');
const vm = require('node:vm');
const crypto = require('node:crypto');
const core = require('../core.cjs');
const encoders = require('./encoders.cjs');
const filename = process.env.PG_SERVING_FIXTURES || path.join(__dirname, 'fixtures/multiplayer-serving-v1.jsonl');
assert.equal(crypto.createHash('sha256').update(fs.readFileSync(filename)).digest('hex'),
    'f1c97bf909e38e5df372a89d169d80f5a6f24c00dccefacd60b10b767f1fcfa0');
let nextLine, reply, fail, searchCalls, applied;
const ended = new WeakSet();
const fakeCore = { ...core, E: { ...core.E,
    ended: g => ended.has(g),
    move: (g, action, seat) => { applied = { action, seat }; ended.add(g); },
}, outcome: g => Array(g.players.length).fill(1 / g.players.length) };
const context = vm.createContext({ process: { env: {}, exit: () => fail(Error('Bridge exited')) },
    console: { log: line => reply(JSON.parse(line)), error: error => fail(Error(String(error))) },
    require: name => {
        if (name === '../core.cjs') return fakeCore;
        if (name === 'node:readline') return { createInterface: () => ({
            [Symbol.asyncIterator]() { return this; },
            next() { return new Promise(resolve => { nextLine = resolve; }); },
        }) };
        if (name === './search.cjs') return { choose: (g, seat, options) => {
            searchCalls.push(options);
            const legal = core.candidates(g, seat), index = (options.extraCandidates[0] + 1) % legal.length;
            return { index, action: legal[index], evaluations: 48, truncated: 0 };
        } };
        return require(name);
    } });
vm.runInContext(fs.readFileSync(path.join(__dirname, 'bridge.cjs'), 'utf8'), context);

(async () => {
    let positions = 0, routes = 0, strategicRoutes = 0, discardRoutes = 0, eligibleDiscards = 0;
    const byPlayers = {};
    for await (const line of readline.createInterface({ input: fs.createReadStream(filename) })) {
        const fixture = JSON.parse(line), { state, player } = fixture.request;
        const expected = core.candidates(state, player);
        for (const revision of ['4.0-multiplayer', '4.2-discard-correction']) {
            const legal = encoders.candidatesForRevision(revision, state, player);
            assert.deepEqual(legal, expected);
            assert.deepEqual(encoders.forRevision(revision).encode(state, player).moves, expected);
            const g = structuredClone(state), proposal = legal.length - 1;
            const strategic = legal.length > 1 && legal.some(a => ['ChoosePowerPlant', 'Bid', 'Build'].includes(a.name));
            searchCalls = []; applied = null;
            context.fixtureEnv = { id: positions, gameSeed: 'routing-only', g,
                roles: Array(g.players.length).fill('learner'), featureRevisions: { learner: revision },
                rng: () => 0.5, steps: 0, policyMoves: {}, searchStats: {} };
            vm.runInContext('envs = [fixtureEnv]', context);
            const result = await new Promise((resolve, reject) => {
                reply = resolve; fail = reject;
                nextLine({ value: JSON.stringify({ op: 'step', actions: [{ proposal, searchSamples: 48,
                    geography: true, disableSearchProposal: false }] }), done: false });
            });
            assert.equal(result.ended.length, 1);
            assert.equal(applied.seat, player);
            assert.deepEqual(JSON.parse(JSON.stringify(applied.action)), legal[strategic ? (proposal + 1) % legal.length : proposal]);
            assert.equal(searchCalls.length, +strategic);
            if (strategic) {
                const options = JSON.parse(JSON.stringify(searchCalls[0]));
                assert.equal(options.samples, 48); assert.equal(options.candidates, 6);
                assert.equal(options.geography, true); assert.deepEqual(options.extraCandidates, [proposal]);
                strategicRoutes++;
            }
            if (legal.every(a => a.name === 'DiscardPowerPlant')) {
                assert.equal(searchCalls.length, 0); discardRoutes++;
                if (revision === '4.2-discard-correction' && encoders.forRevision(revision).eligible(state, legal)) eligibleDiscards++;
            }
            routes++;
        }
        byPlayers[state.players.length] = (byPlayers[state.players.length] || 0) + 1;
        positions++;
    }
    assert.equal(positions, 2553); assert.equal(routes, 5106); assert.equal(discardRoutes, 116); assert.equal(eligibleDiscards, 9);
    assert.deepEqual(byPlayers, {2:349,3:427,4:527,5:609,6:641});
    nextLine({ done: true });
    console.log(JSON.stringify({ positions, routes, strategicRoutes, discardRoutes, eligibleDiscards, byPlayers,
        all_menu_indices_match: true, outside_search_proposals_preserved: true,
        scope: 'Actual bridge routing with stubbed search/transitions; not a complete-game or strength test' }));
})().catch(error => { console.error(error); process.exitCode = 1; });
