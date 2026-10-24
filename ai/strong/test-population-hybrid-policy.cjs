const test = require('node:test'), assert = require('node:assert/strict'), fs = require('node:fs');
const {preparePolicy, PolicyContinuations} = require('./population-hybrid-policy.cjs');
const {PopulationHybridContinuations, prepare} = require('./population-hybrid-continuations.cjs');
const c = require('../core.cjs');
const fixtures = fs.readFileSync(process.env.PG_POPULATION_FIXTURES, 'utf8').trim().split('\n').map(JSON.parse);
const revision = '4.3-strategic-correction';
const positives = [];

test('all serving fixtures retain legal menus, public observations and read-only loss certificates', () => {
    let certified = 0;
    for (const fixture of fixtures) {
        const q = {...fixture.request, featureRevision:revision}, before = JSON.stringify(q);
        const {lossFilter, ...actual} = preparePolicy(q);
        assert.deepEqual(actual, prepare(q));
        assert.deepEqual(actual.moves, fixture.legal);
        assert.equal(JSON.stringify(q), before);
        if (lossFilter.forbidden.length) {
            certified += lossFilter.forbidden.length;
            assert.deepEqual(actual.moves[lossFilter.passIndex], {name:'Pass', data:true});
            assert(lossFilter.certificate.fuelUpperBound < lossFilter.certificate.opponentLowerBound);
            assert(lossFilter.forbidden.every(index => actual.moves[index].name === 'Build'));
            positives.push({q, lossFilter});
        }
    }
    assert.equal(fixtures.length, 2553);
    assert.equal(certified, 24);
});

test('future focal decisions obey the filter while disabled and opponent policies stay unchanged', () => {
    assert(positives.length);
    for (const {q, lossFilter} of positives) for (const enabled of [false,true]) for (const focal of [true,false]) {
        const batch = new PolicyContinuations(), state = structuredClone(q.state);
        batch.endgameFilter = enabled;
        batch.envs = [{g:state, player:focal ? q.player : (q.player+1)%state.players.length,
            roles:state.players.map(()=>'neural'), policyDecisions:{neural:0}, steps:0, reported:false}];
        batch.reply = () => ({}); // Inspect the immediate real-engine move before further simulation.
        const expected = structuredClone(q.state);
        const index = enabled && focal ? lossFilter.passIndex : lossFilter.forbidden[0];
        c.E.move(expected, c.candidates(expected,q.player)[index], q.player);
        batch.step([lossFilter.forbidden[0]]);
        // Engine clocks depend on wall time; compare all gameplay state via public observations.
        const publicState = require('./sealed-policy-beliefs.cjs').publicState;
        function gameplay(g) {
            const row = publicState(g,q.player);
            for (const player of row.players) { delete player.clock; delete player.lastActivity; }
            return row;
        }
        assert.deepEqual(gameplay(state), gameplay(expected));
        assert.equal(batch.envs[0].filterOverrides || 0, enabled && focal ? 1 : 0);
        assert.equal(batch.envs[0].steps, 1);
    }
});

test('disabled filtering preserves population continuations and caps exactly', () => {
    const cells = new Map();
    for (const fixture of fixtures) {
        const q = fixture.request, g = q.state;
        if (fixture.legal.length < 2) continue;
        const key = [g.players.length,g.options.variant,!!g.options.fastBid,g.phase].join('/');
        if (!cells.has(key)) cells.set(key,q);
    }
    assert.equal(cells.size,80);
    for (const q of cells.values()) {
        const p = prepare({...q,featureRevision:revision});
        const config = {...q,featureRevision:revision, mode:'neural_population',belief:'policy',
            neuralBeliefs:Object.fromEntries(p.prior.map(r=>[r.actor,r.encoded.moves[0]])),
            samples:4,n:8,options:[0,1],seed:'population-policy-control',maxSteps:8,endgameFilter:false};
        const a = new PopulationHybridContinuations(), b = new PolicyContinuations();
        let left = a.reset(config), right = b.reset(config);
        for (;;) {
            const clean = structuredClone(right);
            clean.ended.forEach(row=>{assert.equal(row.filterOverrides,0);delete row.filterOverrides;});
            assert.deepEqual(clean,left);
            if (left.observations.every(row=>!row)) break;
            const actions = left.observations.map(row=>row ? row.teacher : null);
            left=a.step(actions);right=b.step(actions);
        }
    }
});

test('enabled filtering rejects certified root actions before starting simulations', () => {
    for (const {q,lossFilter} of positives) {
        assert.throws(()=>new PolicyContinuations().reset({...q,mode:'neural_population',endgameFilter:true,
            options:[lossFilter.forbidden[0]]}), /Certified losing root action/);
    }
});
