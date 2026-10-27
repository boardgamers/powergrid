// Public inference routing, unchanged controls and oracle-equivalence boundaries.
const test = require('node:test'), assert = require('node:assert/strict');
const fs = require('node:fs'), path = require('node:path');
const runtime = process.env.PG_REFERENCE_RUNTIME;
const frozen = name => require(path.join(runtime, name));
const {SurrogateContinuations, preparePolicy} = require('./surrogate-opponent-continuations-v1.cjs');
const {ReferenceContinuations, referenceBids, worldDigest} = require('./reference-opponent-continuations-v2.cjs');
const search = require('./reference-search-public-balances-v1.cjs');
const c = frozen('ai/core.cjs'), beliefs = frozen('ai/strong/sealed-policy-beliefs.cjs');
const encoder = frozen('ai/strong/encoders.cjs').forRevision('4.3-strategic-correction');
const fixtures = fs.readFileSync(path.join(runtime, 'ai/strong/fixtures/multiplayer-serving-v1.jsonl'), 'utf8').trim().split('\n').map(JSON.parse);
const revision = '4.3-strategic-correction', cells = new Map(), strategicCells = new Map();
// Legacy controls stamp wall time on moves. Fix the test clock so full-state
// equality includes clocks as well as game state; production code is untouched.
const wallClock = Date.now; Date.now = () => 1792899000000;
test.after(() => {Date.now = wallClock;});
for (const fixture of fixtures) {
    if (fixture.legal.length < 2) continue;
    const q = fixture.request, g = q.state, prefix = [g.players.length, g.options.variant, !!g.options.fastBid].join('/');
    const phase = fixture.legal.some(m => m.name === 'Bid') ? 'bid' : fixture.legal.some(m => m.name === 'ChoosePowerPlant') ? 'plant' : fixture.legal.some(m => m.name === 'Build') ? 'building' : null;
    if (!cells.has(prefix + '/' + g.phase)) cells.set(prefix + '/' + g.phase, q);
    if (phase && !strategicCells.has(prefix + '/' + phase)) strategicCells.set(prefix + '/' + phase, q);
}
assert.equal(cells.size, 80); assert.equal(strategicCells.size, 60);

function priorChoice(observation) {
    if (observation.actions.length === 1) return 0;
    let best = -1;
    observation.actions.forEach((a, i) => {
        if (a[100] === 1 && (best < 0 || a[74] > observation.actions[best][74])) best = i;
    });
    assert(best >= 0); return best;
}

test('recovered six-player sealed prior accepts only the unique forced bid', () => {
    const fixture = require('./fixtures/conservative-auction-forced-prior-v1.json');
    const request = fixture.request, root = preparePolicy({...request, featureRevision: revision});
    const forced = root.prior.find(p => p.encoded.moves.length === 1);
    assert(forced);
    assert.equal(forced.actor, 2);
    assert.deepEqual(forced.encoded.moves, [{name: 'Bid', data: 26}]);
    assert.equal(forced.encoded.state.at(-1), 0);
    assert.equal(forced.encoded.actions[0][100], 0);
    const q = config(request), before = structuredClone(q);
    const batch = new SurrogateContinuations();
    batch.reset(q);
    assert.deepEqual(q, before);
    assert(batch.envs.every(e => e.initialBelief.committed.some(p =>
        p.actor === 2 && p.action.name === 'Bid' && p.action.data === 26)));
    const forcedPass = root.prior.find(p => p.encoded.moves.length === 1 && p.encoded.moves[0].name === 'Pass');
    assert(forcedPass);
    const illegalPassReplacement = structuredClone(q);
    illegalPassReplacement.surrogateBeliefs[0][forcedPass.actor] = {name: 'Bid', data: 26};
    assert.throws(() => new SurrogateContinuations().reset(illegalPassReplacement), /outside public shortlist/);
    for (const wrong of [{name: 'Pass'}, {name: 'Bid', data: 27}]) {
        const bad = structuredClone(q); bad.surrogateBeliefs[0][forced.actor] = wrong;
        assert.throws(() => new SurrogateContinuations().reset(bad), /outside public shortlist/);
    }
    const broadRequest = structuredClone(request);
    broadRequest.state.players[forcedPass.actor].money = 80;
    const broad = preparePolicy({...broadRequest, featureRevision: revision});
    const prior = broad.prior.find(p => p.encoded.moves.length > 1 && p.encoded.actions.some(a => a[100] === 0));
    assert(prior, 'Need a real choice to check that shortlist enforcement is preserved');
    const bad = config(broadRequest);
    bad.surrogateBeliefs[0][prior.actor] = prior.encoded.moves[prior.encoded.actions.findIndex(a => a[100] === 0)];
    assert.throws(() => new SurrogateContinuations().reset(bad), /outside public shortlist/);
});
function config(request, mode = 'surrogate_opponent_v1') {
    const root = preparePolicy({...request, featureRevision: revision});
    const options = root.moves.map((_, i) => i).filter(i => !root.lossFilter.forbidden.includes(i)).slice(0, 2);
    assert(options.length);
    const bids = Object.fromEntries(root.prior.map(p => [p.actor, p.encoded.moves[priorChoice(p.encoded)]]));
    const q = {...request, featureRevision: revision, mode, belief: 'policy', endgameFilter: true,
        options, samples: 4, n: options.length * 4, maxSteps: 4, seed: 'surrogate-worker-engineering-v1', neuralBeliefs: {}};
    if (mode === 'surrogate_opponent_v1') q.surrogateBeliefs = Array.from({length: 4}, () => structuredClone(bids));
    else if (mode === 'neural_population') q.neuralBeliefs = bids;
    else q.referenceOpponent = 'search_geo';
    return q;
}

function drive(q, Type = SurrogateContinuations, oracle = false, inspect = () => {}) {
    const batch = new Type(), rows = []; let response = batch.reset(q), queries = 0, calls = 0;
    for (;;) {
        rows.push(...response.ended);
        if (response.observations.every(o => !o)) break;
        const actions = response.observations.map((o, i) => {
            if (!o) return null;
            const e = batch.envs[i], expected = encoder.encode(beliefs.publicState(e.g, o.actor), o.actor);
            delete expected.moves;
            const clean = structuredClone(o); delete clean.actor; delete clean.focalPlayer; delete clean.roles;
            assert.deepEqual(clean, expected, 'Emitted query differed from sanitized public features');
            assert(!('pendingTeacherSeed' in o) && !('rng' in o));
            if (o.roles[o.actor] !== 'surrogate') return o.teacher;
            queries++;
            if (!oracle) return priorChoice(o);
            const result = search.choose(e.g, o.actor, {samples: 16, candidates: 6, geography: true,
                maxSteps: 2400, seed: e.pendingTeacherSeed});
            assert.equal(result.truncated || 0, 0); calls++;
            return result.index;
        });
        inspect(batch, response, actions);
        response = batch.step(actions);
    }
    rows.sort((a, b) => a.env - b.env);
    return {batch, rows, queries, calls};
}

test('all 80 historical population control contexts stay exactly unchanged', () => {
    for (const request of cells.values()) {
        const q = config(request, 'neural_population');
        const a = drive(q, ReferenceContinuations), b = drive(q);
        assert.deepEqual(b.rows, a.rows);
        assert.deepEqual(b.batch.envs.map(e => worldDigest(e.g)), a.batch.envs.map(e => worldDigest(e.g)));
    }
});

test('all 60 strategic contexts emit only public queries; secret mutations, caps and shortlist errors are handled', () => {
    let queries = 0, caps = 0, rejected = 0;
    for (const request of strategicCells.values()) {
        const q = config(request), before = JSON.stringify(q);
        const result = drive(q, SurrogateContinuations, false, (batch, response, actions) => {
            if (rejected) return;
            const index = response.observations.findIndex(o => o && o.roles[o.actor] === 'surrogate' && o.actions.some(a => a[100] !== 1));
            if (index < 0) return;
            const wrong = [...actions]; wrong[index] = response.observations[index].actions.findIndex(a => a[100] !== 1);
            const snapshots = batch.envs.map(e => worldDigest(e.g));
            assert.throws(() => batch.step(wrong), /outside public shortlist/);
            assert.deepEqual(batch.envs.map(e => worldDigest(e.g)), snapshots); rejected++;
        });
        assert.equal(JSON.stringify(q), before, 'Worker mutated its request');
        const polluted = structuredClone(q);
        polluted.state.seed = 'private'; polluted.state.powerPlantsDeck = [{number: 987654}];
        polluted.state.powerPlantDeckAfterStep3 = [999]; polluted.state.hiddenLog = [{secret: true}];
        polluted.state.automation = {version: 1, plans: {}, increments: q.state.players.map(() => 123), liveUpdate: true};
        polluted.state.players.forEach(p => {p.lastMove = {name: 'Bid', data: 777}; if (q.state.options.fastBid) p.bid = 777;});
        if (q.state.options.fastBid) polluted.state.currentBid = 777;
        assert.deepEqual(drive(polluted).rows, result.rows);
        queries += result.queries; caps += result.rows.filter(r => r.truncated).length;
        for (const row of result.rows) {
            assert.equal(Object.values(row.policyDecisions).reduce((a, b) => a+b, 0), row.steps);
            assert(row.steps <= 4); assert.deepEqual(row.searchStats, {decisions: 0, evaluations: 0, truncated: 0});
            if (row.truncated) {assert.equal(row.value, null); assert.equal(row.diagnostic.terminal, null);}
        }
    }
    assert(queries > 0 && caps > 0); assert.equal(rejected, 1);
    console.log(JSON.stringify({publicContexts: 60, surrogateQueries: queries, intentionallyCapped: caps, illegalShortlistRejected: rejected}));
});

test('externally supplied actual search choices reproduce reference states and RNG across all counts', () => {
    const chosen = [...strategicCells.entries()].filter(([key]) =>
        ['2/original/false/plant', '3/recharged/true/bid', '4/original/true/bid',
         '5/recharged/false/building', '6/original/false/building'].includes(key)).map(([, q]) => q);
    assert.equal(chosen.length, 5); let calls = 0, priors = 0;
    for (const [i, request] of chosen.entries()) {
        const q = config(request, 'reference_opponent_v1');
        q.samples = q.n = 1; q.options = [q.options[0]]; q.maxSteps = 3; q.seed += '-oracle-' + i;
        const earlier = beliefs.prompts(request.state, request.player);
        const bids = referenceBids(structuredClone(request.state), earlier, 'search_geo', q.seed + '-0');
        assert.equal(bids.stats.truncated, 0); priors += bids.committed.length;
        const next = {...q, mode: 'surrogate_opponent_v1', surrogateBeliefs: [Object.fromEntries(bids.committed.map(p => [p.actor, p.action]))]};
        delete next.referenceOpponent;
        const a = drive(q, ReferenceContinuations), b = drive(next, SurrogateContinuations, true);
        assert.deepEqual(b.batch.envs.map(e => worldDigest(e.g)), a.batch.envs.map(e => worldDigest(e.g)));
        assert.deepEqual(b.batch.envs.map(e => [e.rng(), e.rng(), e.rng()]), a.batch.envs.map(e => [e.rng(), e.rng(), e.rng()]));
        for (const field of ['sample', 'actionIndex', 'steps', 'truncated', 'value']) assert.equal(b.rows[0][field], a.rows[0][field]);
        assert.deepEqual(b.rows[0].diagnostic.terminal, a.rows[0].diagnostic.terminal);
        assert.equal(b.rows[0].diagnostic.sampledWorldSha256, a.rows[0].diagnostic.sampledWorldSha256);
        assert.equal(b.rows[0].policyDecisions.surrogate, a.rows[0].policyDecisions.search_geo);
        for (const role of ['economic', 'neural', 'forced']) assert.equal(b.rows[0].policyDecisions[role], a.rows[0].policyDecisions[role]);
        calls += b.calls;
    }
    assert(calls > 0); console.log(JSON.stringify({oracleRoots: 5, actualSearchCalls: calls, priorBids: priors, gradientUpdates: 0}));
});

test('worker partitions retain identical worlds, prior beliefs and trajectories', () => {
    const request = [...strategicCells.values()].find(q => q.state.players.length === 4 && q.state.options.fastBid && beliefs.prompts(q.state, q.player).length);
    assert(request);
    const q = config(request); assert.equal(q.n, 8);
    const whole = drive(q), a = drive({...q, n: 3}), b = drive({...q, n: 5, offset: 3});
    assert.deepEqual([...a.rows, ...b.rows.map(row => ({...row, env: row.env+3}))], whole.rows);
    assert.deepEqual([...a.batch.envs, ...b.batch.envs].map(e => worldDigest(e.g)), whole.batch.envs.map(e => worldDigest(e.g)));
    const bad = structuredClone(q); bad.surrogateBeliefs[0] = {};
    assert.throws(() => new SurrogateContinuations().reset(bad), /prior-bid actors/);
    assert.throws(() => new SurrogateContinuations().reset({...q, referenceOpponent: 'search_geo'}), /arena opponent identity/);
    assert.throws(() => new SurrogateContinuations().reset({...q, maxSteps: 0}));
    assert.throws(() => new SurrogateContinuations().reset({...q, offset: 7, n: 2}));
});

test('invalid JSONL request exits immediately with stdin open', async () => {
    const {spawn} = require('node:child_process');
    const child = spawn(process.execPath, [path.join(__dirname, 'surrogate-opponent-continuations-v1.cjs')], {env: process.env, stdio: ['pipe', 'pipe', 'pipe']});
    let errors = '', output = ''; child.stderr.on('data', d => errors += d); child.stdout.on('data', d => output += d);
    const done = new Promise((resolve, reject) => {
        const timer = setTimeout(() => {child.kill(); reject(Error('Invalid input left worker alive'));}, 5000);
        child.once('error', e => {clearTimeout(timer); reject(e);});
        child.once('close', code => {clearTimeout(timer); resolve(code);});
    });
    child.stdin.write(JSON.stringify({op: 'invalid-operation'}) + '\n');
    assert.equal(await done, 1); assert(errors.includes('AssertionError')); assert.equal(output, '');
});
