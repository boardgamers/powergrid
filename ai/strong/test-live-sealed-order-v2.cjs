const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const readline = require('node:readline');
const crypto = require('node:crypto');
const oldRoot = path.resolve(process.argv[2]), newRoot = path.resolve(process.argv[3]);
const output = path.resolve(process.argv[4]);
const hash = data => crypto.createHash('sha256').update(data).digest('hex');
const c = require(path.join(newRoot, 'ai/core.cjs'));
const oldPolicy = require(path.join(oldRoot, 'ai/strong/population-hybrid-policy.cjs'));
const newPolicy = require(path.join(newRoot, 'ai/strong/population-hybrid-policy.cjs'));
const beliefs = require(path.join(newRoot, 'ai/strong/sealed-policy-beliefs.cjs'));
const oldBeliefs = require(path.join(oldRoot, 'ai/strong/sealed-policy-beliefs.cjs'));
const {createAnalysisScenario} = require(path.join(newRoot, 'engine/dist/src/analysis.js'));
const fixturePath = path.join(newRoot, 'ai/strong/fixtures/multiplayer-serving-v1.jsonl');
const clone = value => structuredClone(value);
const qFor = (state, player) => ({state:beliefs.publicState(state, player), player, featureRevision:'4.3-strategic-correction'});
const actionFor = (state, actor) => c.allLegal(state, actor).find(m => m.name === 'Bid') || {name:'Pass', data:true};
fs.mkdirSync(output, {recursive:false});
const write = (name, value) => fs.writeFileSync(path.join(output, name), JSON.stringify(value, null, 2)+'\n', {flag:'wx'});
const report = {checker_sha256:hash(fs.readFileSync(__filename)), canonical_controls:0, audit_regressions:0,
    subset_requests:0, prior_prompts_checked:0, secret_invariance_checks:0, invalid_requests_rejected:0,
    cells:{}, fixed_order_resolution_checks:0, passed:false,
    qualification_eligible:false, reserved_final_seeds_used:false, new_strength_games:0, new_hf_jobs:0, gradients:false};
const selected = {}, searched = new Set();
const requests = fs.openSync(path.join(output, 'requests.jsonl'), 'wx');
const controlTraces = crypto.createHash('sha256');

function checkRequest(state, player, label, family, save=true) {
    const q = qFor(state, player), before = JSON.stringify(q);
    const root = newPolicy.preparePolicy(q), prior = beliefs.prompts(q.state, player);
    const plan = beliefs.submissionPlan(q.state, player);
    assert.deepEqual(root.moves, c.candidates(state, player));
    assert.deepEqual(prior.map(p => p.actor), plan.submitted);
    for (const p of prior) {
        assert(p.state.currentPlayers.includes(p.actor));
        assert.deepEqual(p.state.playerOrder, state.playerOrder);
        assert.equal(p.state.auctioningPlayer, state.auctioningPlayer);
        assert.deepEqual(p.encoded.moves, c.candidates(p.state, p.actor));
        assert(p.encoded.moves.every(m => ['Bid','Pass'].includes(m.name)));
        report.prior_prompts_checked++;
    }
    assert.equal(JSON.stringify(q), before);
    const hidden = clone(q);
    hidden.state.seed = 'private-seed-must-not-influence-order';
    hidden.state.powerPlantsDeck = [{number:9999}];
    hidden.state.powerPlantDeckAfterStep3 = [{number:9998}];
    hidden.state.hiddenLog = [{type:'private', secret:'never-visible'}];
    hidden.state.currentBid = 9997;
    hidden.state.players.forEach(p => {p.bid = 9996; p.lastMove = {name:'Bid',data:9995};});
    assert.deepEqual(newPolicy.preparePolicy(hidden), root);
    report.secret_invariance_checks++;
    const key = `${state.players.length}p-${state.options.variant}`;
    const cell = report.cells[key] ||= {audit:0, subset:0};
    cell[family]++;
    if (save) fs.writeSync(requests, JSON.stringify({label, family, request:q, legal:root.moves, plan})+'\n');
    const at = plan.eligible.indexOf(player);
    const oldCanonical = q.state.currentPlayers[0] === player &&
        JSON.stringify(q.state.currentPlayers) === JSON.stringify(plan.eligible.slice(at));
    assert.equal(plan.canonical, oldCanonical);
    if (oldCanonical) assert.deepEqual(newPolicy.preparePolicy(q), oldPolicy.preparePolicy(q));
    if (family === 'subset' && !oldCanonical && state.players.length >= 2) {
        const type = plan.submitted.length ? 'committed' : 'pending';
        const sampleKey = `${key}-${type}`;
        if (!searched.has(sampleKey)) {
            searched.add(sampleKey); write(sampleKey+'.json', {label, request:q, legal:root.moves, plan});
        }
    }
    return q;
}

function auctionOutcome(g) {
    return {players:g.players.map(p => ({id:p.id, money:p.money, plants:p.powerPlants,
        skipAuction:p.skipAuction, passed:p.passed})), currentPlayers:g.currentPlayers,
        playerOrder:g.playerOrder, phase:g.phase, market:g.actualMarket, future:g.futureMarket,
        chosen:g.chosenPowerPlant, minimum:g.minimunBid, auctioning:g.auctioningPlayer};
}

(async () => {
    let index = 0;
    for await (const line of readline.createInterface({input:fs.createReadStream(fixturePath)})) {
        const f = JSON.parse(line), {state, player} = f.request;
        const q = {...f.request, featureRevision:'4.3-strategic-correction'};
        const a = oldPolicy.preparePolicy(q), b = newPolicy.preparePolicy(q);
        assert.deepEqual(b, a); assert.deepEqual(b.moves, f.legal);
        assert.deepEqual(beliefs.prompts(state, player), oldBeliefs.prompts(state, player));
        controlTraces.update(JSON.stringify(a)); report.canonical_controls++;
        if (state.options.fastBid && state.phase === c.E.Phase.Auction && state.chosenPowerPlant) {
            const key = `${state.players.length}p-${state.options.variant}`;
            if (!selected[key] || state.currentPlayers.length > selected[key].state.currentPlayers.length)
                selected[key] = {state, player, fixture:index};
            const world = createAnalysisScenario(state, {player, seed:`live-sealed-order-audit-v1-${index}`});
            for (const actor of state.currentPlayers.slice(1)) {
                checkRequest(world, actor, `${index}-alternate-${actor}`, 'audit'); report.audit_regressions++;
                const after = clone(world); c.E.move(after, actionFor(after, actor), actor);
                checkRequest(after, player, `${index}-submitted-${actor}`, 'audit'); report.audit_regressions++;
            }
        }
        index++;
    }
    for (const [key, source] of Object.entries(selected)) {
        const {state, player, fixture} = source, seats = state.currentPlayers;
        assert.equal(seats.length, state.players.length, 'Require every seat initially pending');
        const base = createAnalysisScenario(state, {player, seed:`sealed-order-subsets-v2-${fixture}`});
        for (let mask = 0; mask < 2**seats.length-1; mask++) {
            const g = clone(base);
            const submitted = seats.filter((_, i) => mask & (1<<i));
            for (const actor of submitted.slice().reverse()) c.E.move(g, actionFor(g, actor), actor);
            for (const actor of g.currentPlayers) {
                checkRequest(g, actor, `${key}-mask${mask}-actor${actor}`, 'subset'); report.subset_requests++;
            }
        }
        // Sealed tie/cost resolution must preserve real seat/auction order. Fixed
        // bids produce the same strategic outcome in every cyclic/reversed order.
        const actions = Object.fromEntries(seats.map(actor => [actor, actionFor(base, actor)]));
        let reference;
        for (let shift = 0; shift < seats.length; shift++) for (const reverse of [false, true]) {
            let order = [...seats.slice(shift), ...seats.slice(0, shift)];
            if (reverse) order.reverse();
            const g = clone(base);
            for (const actor of order) c.E.move(g, clone(actions[actor]), actor);
            const result = auctionOutcome(g);
            if (reference) assert.deepEqual(result, reference); else reference = result;
            report.fixed_order_resolution_checks++;
        }
        const q = qFor(base, seats[0]);
        for (const mutate of [
            x => x.state.currentPlayers.push(x.state.currentPlayers[0]),
            x => {x.state.currentPlayers = x.state.currentPlayers.slice().reverse();},
            x => {x.state.currentPlayers = x.state.currentPlayers.slice(1);},
            x => {x.state.options.showMoney = false;},
        ]) {
            const bad = clone(q); mutate(bad);
            assert.throws(() => beliefs.prompts(bad.state, bad.player), {name:'AssertionError'});
            report.invalid_requests_rejected++;
        }
    }
    assert.equal(report.canonical_controls,2553); assert.equal(report.audit_regressions,446);
    assert.equal(report.subset_requests,640); assert.equal(report.invalid_requests_rejected,40);
    assert.equal(report.secret_invariance_checks,1086);
    assert.equal(Object.keys(report.cells).length,10);
    report.canonical_control_trace_sha256 = controlTraces.digest('hex');
    report.requests_sha256 = hash(fs.readFileSync(path.join(output,'requests.jsonl')));
    report.passed = true;
    report.scope = 'Exact old/new preparations on 2,553 canonical fixtures, 446 known failures, all nonempty pending subsets/actors in ten full-seat fixtures, hidden-data invariance and legal auction resolution. No strength or production qualification.';
    report.history_assumption = 'Committed bidders are inferred in their public player order, then actual pending bidders remain. Their real hidden submission order is unknown. This approximation is explicit, deterministic, and canonical behavior is unchanged.';
    write('assessment.json',report); console.log(JSON.stringify(report));
})().catch(error => {write('failure.json',{error:error.stack,report});console.error(error);process.exitCode=1;})
    .finally(() => fs.closeSync(requests));
