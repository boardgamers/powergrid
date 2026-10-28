// Canonical regression plus actual-wrapper failures; no neural inference.
const fs = require('node:fs'), path = require('node:path'), assert = require('node:assert/strict');
const crypto = require('node:crypto');
const root = path.resolve(process.argv[2]);
const base = path.join(root, 'ai/runs/current-engine-auction-v1');
const out = path.join(root, 'ai/runs/current-engine-auction-v2');
const artifact = path.join(out, 'artifact');
const digest = p => crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
const read = p => JSON.parse(fs.readFileSync(p, 'utf8'));
const write = (p, value) => fs.writeFileSync(p, JSON.stringify(value, null, 2) + '\n', {flag:'wx'});
const old = require(path.join(base, 'artifact/ai/strong/population-hybrid-policy.cjs')).preparePolicy;
const current = require(path.join(artifact, 'ai/strong/population-hybrid-policy.cjs')).preparePolicy;
const beliefs = require(path.join(artifact, 'ai/strong/sealed-policy-beliefs.cjs'));
const c = require(path.join(artifact, 'ai/core.cjs'));
const prep = read(path.join(out, 'prepared.json'));
assert.equal(digest(path.join(artifact, 'manifest.json')), prep.runtime_manifest_sha256);
for (const [name, sha] of Object.entries(read(path.join(artifact, 'manifest.json')))) assert.equal(digest(path.join(artifact,name)),sha);
const inputs = path.join(base, 'inputs.jsonl');
const rows = fs.readFileSync(inputs, 'utf8').trim().split('\n').map(JSON.parse);
assert.equal(rows.length, 2693);
const casesPath = path.join(root, 'ai/runs/current-engine-auction-wrapper-diagnostic-v3/cases.json');
assert.equal(digest(casesPath), prep.wrapper_cases_sha256);
write(path.join(out, 'order-check-intent.json'), {created_at: new Date().toISOString(),
    inputs_sha256: digest(inputs), cases_sha256: digest(casesPath), worker_sha256: digest(__filename),
    runtime_manifest_sha256: prep.runtime_manifest_sha256, new_inference: 0, new_full_games: 0, new_hf_jobs: 0});
let canonical = 0;
for (const row of rows) {
    const q = {...row.request, featureRevision:'4.3-strategic-correction'};
    assert.deepEqual(current(q), old(q), `Canonical preparation changed: ${row.name}`);
    canonical++;
    if (canonical % 500 === 0) console.log(JSON.stringify({canonical}));
}
const cases = read(casesPath), records = [];
for (const row of cases) {
    const q = {...row.request, featureRevision:'4.3-strategic-correction'};
    const prepared = current(q), g = beliefs.publicState(q.state,q.player);
    assert.deepEqual(prepared.moves, c.candidates(g,q.player));
    const eligible = g.playerOrder.filter(i => !g.players[i].skipAuction && !g.players[i].isDropped);
    const expected = g.options.fastBid && g.phase === 'Auction' && g.chosenPowerPlant ?
        eligible.filter(i => !g.currentPlayers.includes(i)) : [];
    assert.deepEqual(prepared.prior.map(p=>p.actor), expected);
    if (row.autoPassed !== undefined && expected.includes(row.autoPassed))
        assert.deepEqual(prepared.prior.find(p=>p.actor===row.autoPassed).encoded.moves, [{name:'Pass',data:true}]);
    const changed = structuredClone(q);
    changed.state.seed = 'hidden'; changed.state.powerPlantsDeck = [{number:999}];
    changed.state.hiddenLog = [{secret:true}]; changed.state.currentBid = 999;
    changed.state.players.forEach(p=>{p.bid=999;p.lastMove={name:'SECRET'};});
    assert.deepEqual(current(changed), prepared, 'Hidden input affected noncanonical prompts');
    if (g.options.fastBid && g.phase === 'Auction' && g.chosenPowerPlant) {
        const reordered = structuredClone(q); reordered.state.currentPlayers.reverse();
        assert.deepEqual(current(reordered), prepared, 'Public waiting-list permutation changed prompts');
    }
    records.push({name:row.name, previous_compatible:row.compatible, now_compatible:true,
        prior_actors:prepared.prior.map(p=>p.actor), forced_auto_pass_prior:row.autoPassed ?? null});
}
assert.equal(canonical,2693); assert.equal(records.length,20);
const result = {passed:true, canonical_positions_exact:canonical, wrapper_cases:20,
    previously_failing_cases_fixed:records.filter(r=>!r.previous_compatible).length,
    records, runtime_manifest_sha256:prep.runtime_manifest_sha256,
    inputs_sha256:digest(inputs), cases_sha256:digest(casesPath), worker_sha256:digest(__filename),
    new_inference:0,new_full_games:0,new_hf_jobs:0,qualification_eligible:false,reserved_final_seeds_used:false,
    interpretation:'Public preparation and membership checks only; actual model/search continuations on the repaired inputs remain required.'};
write(path.join(out,'order-assessment.json'),result);
console.log(JSON.stringify({passed:true,canonical_positions_exact:canonical,wrapper_cases:20,previously_failing_cases_fixed:result.previously_failing_cases_fixed}));
