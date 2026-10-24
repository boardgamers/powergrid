// Existing-fixture serving audit; does not change the evaluated policy or play strength games.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const readline = require('node:readline');
const runtime = path.resolve(process.argv[2]);
const currentRoot = path.resolve(process.argv[3]);
const output = path.resolve(process.argv[4]);
const hash = data => crypto.createHash('sha256').update(data).digest('hex');
const digest = file => hash(fs.readFileSync(file));
const write = (name, value) => fs.writeFileSync(path.join(output, name), JSON.stringify(value, null, 2)+'\n', {flag:'wx'});
const c = require(path.join(runtime, 'ai/core.cjs'));
const beliefs = require(path.join(runtime, 'ai/strong/sealed-policy-beliefs.cjs'));
const {preparePolicy} = require(path.join(runtime, 'ai/strong/population-hybrid-policy.cjs'));
const oldAnalysis = require(path.join(runtime, 'engine/dist/src/analysis.js'));
const current = require(path.join(currentRoot, 'engine/dist/index.js'));
const currentAnalysis = require(path.join(currentRoot, 'engine/dist/src/analysis.js'));
const fixturePath = path.join(runtime, 'ai/strong/fixtures/multiplayer-serving-v1.jsonl');
const provenance = JSON.parse(fs.readFileSync(path.join(currentRoot, 'provenance.json')));
fs.mkdirSync(output, {recursive:false});
const report = {
    fixture_sha256: digest(fixturePath), checker_sha256: digest(__filename),
    provenance_sha256: digest(path.join(currentRoot, 'provenance.json')),
    canonical_controls: 0, sealed_roots: 0, cases: 0, cells: {},
    scope: 'Existing Germany serving fixtures, 2–6 players, original/Recharged sealed auctions. Legal alternative actors and legal non-prefix submissions; no strength estimate or platform integration.',
    qualification_eligible: false, reserved_final_seeds_used: false,
    new_strength_games: 0, new_hf_jobs: 0, gradients: false,
    live_evaluation_changed: false, audit_complete: false,
};
const counts = () => ({canonical_controls:0, alternate_actor:0, nonprefix_submitted:0, engine_accepted:0, adapter_rejected:0});
const examples = new Set();
const comparable = state => {
    const result = structuredClone(state);
    delete result.poweringChoices; delete result.pendingMessages;
    result.log = result.log.filter(e => !(e.type === 'event' && /^Starting Step [23]/.test(e.event)));
    return result;
};
function legalAction(state, player) {
    const legal = c.allLegal(state, player);
    assert(legal.length && legal.every(m => ['Bid','Pass'].includes(m.name)));
    // A real legal submission, never a manually edited current-player array.
    return legal.find(m => m.name === 'Bid') || legal[0];
}
function requestFor(state, player) {
    return {state:beliefs.publicState(state, player), player, featureRevision:'4.3-strategic-correction'};
}
function inspectCase(kind, index, before, oldWorld, newWorld, player, submitter) {
    const key = `${before.players.length}p-${before.options.variant}`;
    const cell = report.cells[key];
    const q = requestFor(oldWorld, player), original = JSON.stringify(q);
    const eligible = q.state.playerOrder.filter(i => !q.state.players[i].skipAuction && !q.state.players[i].isDropped);
    const committed = eligible.filter(i => !q.state.currentPlayers.includes(i));
    assert(q.state.currentPlayers.includes(player));
    assert.deepEqual(current.availableMoves(newWorld, newWorld.players[player]), c.E.availableMoves(oldWorld, oldWorld.players[player]));
    const action = legalAction(oldWorld, player);
    const a = structuredClone(oldWorld), b = structuredClone(newWorld);
    c.E.move(a, structuredClone(action), player);
    current.move(b, structuredClone(action), player);
    assert.deepEqual(comparable(b), comparable(a));
    cell.engine_accepted++;
    let error = null;
    try { preparePolicy(q); } catch (e) { error = {name:e.name, message:e.message.split('\n')[0]}; }
    assert.equal(JSON.stringify(q), original, 'Adapter modified the input');
    assert(error && error.name === 'AssertionError', 'Expected serving order assertion');
    const expected = kind === 'alternate_actor' ? 'Teacher uses the canonical simulator actor order' : 'Cannot infer a prior submission order';
    assert.equal(error.message, expected);
    cell[kind]++; cell.adapter_rejected++; report.cases++;
    const row = {fixture:index, kind, cell:key, player, submitter, pending:q.state.currentPlayers,
        eligible, committed, legal_action:action, request_sha256:hash(original),
        current_engine_accepted:true, research_engine_accepted:true, transitions_match:true,
        frozen_adapter_error:error};
    fs.appendFileSync(path.join(output, 'cases.jsonl'), JSON.stringify(row)+'\n');
    const exampleKey = `${key}-${kind}`;
    if (!examples.has(exampleKey)) {
        examples.add(exampleKey);
        write(exampleKey+'.json', {row, request:q});
    }
}

(async () => {
    assert.equal(report.fixture_sha256, 'f1c97bf909e38e5df372a89d169d80f5a6f24c00dccefacd60b10b767f1fcfa0');
    for (const [name, sha] of Object.entries(provenance.research_runtime_hashes)) assert.equal(digest(path.join(runtime, name)), sha);
    for (const [name, sha] of Object.entries(provenance.production_engine_files)) assert.equal(digest(path.join(currentRoot, name)), sha);
    report.research_files_verified = Object.keys(provenance.research_runtime_hashes).length;
    let index = 0;
    for await (const line of readline.createInterface({input:fs.createReadStream(fixturePath)})) {
        const fixture = JSON.parse(line), {state, player} = fixture.request;
        const root = preparePolicy({...fixture.request, featureRevision:'4.3-strategic-correction'});
        assert.deepEqual(root.moves, fixture.legal);
        report.canonical_controls++;
        if (state.options.fastBid && state.phase === c.E.Phase.Auction && state.chosenPowerPlant) {
            report.sealed_roots++;
            const key = `${state.players.length}p-${state.options.variant}`;
            const cell = report.cells[key] ||= counts();
            cell.canonical_controls++;
            const options = {player, seed:`live-sealed-order-audit-v1-${index}`};
            const a = oldAnalysis.createAnalysisScenario(state, options);
            const b = currentAnalysis.createAnalysisScenario(state, options);
            assert.deepEqual(comparable(b), comparable(a));
            for (const actor of state.currentPlayers.slice(1)) {
                inspectCase('alternate_actor', index, state, a, b, actor, null);
                const x = structuredClone(a), y = structuredClone(b);
                const action = legalAction(x, actor);
                c.E.move(x, structuredClone(action), actor); current.move(y, structuredClone(action), actor);
                assert.deepEqual(comparable(y), comparable(x));
                assert(x.currentPlayers.length && x.currentPlayers[0] === player);
                inspectCase('nonprefix_submitted', index, state, x, y, player, actor);
            }
        }
        index++;
    }
    assert.equal(report.canonical_controls, 2553);
    assert.equal(Object.keys(report.cells).length, 10);
    for (const cell of Object.values(report.cells)) {
        assert(cell.alternate_actor > 0 && cell.nonprefix_submitted > 0);
        assert.equal(cell.engine_accepted, cell.adapter_rejected);
    }
    report.representative_requests = examples.size;
    report.audit_complete = true;
    report.finding = 'The frozen adapter rejects legal asynchronous sealed-auction requests, including model/filter arms, before model inference. Both current and research engines accept these actions.';
    report.next_step = 'Build a separately versioned adapter; infer submitted actors from eligible minus pending, preserve public player/auction order, and model unknown submission history explicitly. Keep the running canonical grid unchanged.';
    write('assessment.json', report);
    console.log(JSON.stringify(report));
})().catch(error => {
    write('failure.json', {error:error.stack, report}); console.error(error); process.exitCode = 1;
});
