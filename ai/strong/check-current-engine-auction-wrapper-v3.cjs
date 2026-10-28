// Bounded setup/nomination fixtures, not fresh full games or policy inference.
const fs = require('node:fs'), path = require('node:path'), assert = require('node:assert/strict');
const crypto = require('node:crypto');
const root = path.resolve(process.argv[2]);
const artifact = path.join(root, 'ai/runs/current-engine-auction-v1/artifact');
const out = path.join(root, 'ai/runs/current-engine-auction-wrapper-diagnostic-v3');
assert(!fs.existsSync(out), 'Inspect the previous diagnostic before retrying');
const digest = name => crypto.createHash('sha256').update(fs.readFileSync(name)).digest('hex');
const prepared = JSON.parse(fs.readFileSync(path.join(path.dirname(artifact), 'prepared.json'), 'utf8'));
assert.equal(digest(path.join(artifact, 'manifest.json')), prepared.runtime_manifest_sha256);
for (const [name, sha] of Object.entries(JSON.parse(fs.readFileSync(path.join(artifact, 'manifest.json'), 'utf8'))))
    assert.equal(digest(path.join(artifact, name)), sha);
const E = require(path.join(artifact, 'engine/dist/index.js'));
const scenario = require(path.join(artifact, 'engine/dist/src/analysis.js')).createAnalysisScenario;
const pricing = require(path.join(artifact, 'engine/dist/src/auction-pricing.js')).minimumPlantBid;
const poolPath = path.join(root, 'ai/strong/fixtures/multiplayer-serving-v1.jsonl');
assert.equal(digest(poolPath), 'f1c97bf909e38e5df372a89d169d80f5a6f24c00dccefacd60b10b767f1fcfa0');
const pool = fs.readFileSync(poolPath, 'utf8').trim().split('\n').map(JSON.parse);
const W = require(path.join(artifact, 'engine/dist/wrapper.js'));
const beliefs = require(path.join(artifact, 'ai/strong/sealed-policy-beliefs.cjs'));
const {preparePolicy} = require(path.join(artifact, 'ai/strong/population-hybrid-policy.cjs'));
fs.mkdirSync(out);
const write = (name, value) => fs.writeFileSync(path.join(out, name), JSON.stringify(value, null, 2) + '\n', {flag: 'wx'});
write('design.json', {created_at: new Date().toISOString(), runtime_manifest_sha256: prepared.runtime_manifest_sha256,
    worker_sha256: digest(__filename), fixture_pool_sha256: digest(poolPath), selection: 'First archived round>1 sealed nomination per count/variant with at least min(N,3) eligible bidders and all able to afford the chosen plant. Commit nomination+bid, then test a later pending actor and actual wrapper auto-pass of a later zero-cash player.',
    counterfactual_cash_cases: 10, saved_nomination_roots: 10, new_full_games: 0, new_inference: 0, new_hf_jobs: 0,
    qualification_eligible: false, reserved_final_seeds_used: false});
function probe(g, seat, name) {
    const request = {requestId: name, revision: 0, player: seat, state: beliefs.publicState(g, seat)};
    let error = null, preparedRoot = null;
    try {preparedRoot = preparePolicy({...request, featureRevision: '4.3-strategic-correction'});}
    catch (failure) {error = {name: failure.name, message: failure.message};}
    return {name, players: g.players.length, variant: g.options.variant, request,
        pending: g.currentPlayers, eligible: g.playerOrder.filter(i => !g.players[i].skipAuction && !g.players[i].isDropped),
        compatible: !error, error, preparedMoves: preparedRoot?.moves};
}
(async () => {
    const records = [];
    for (let n = 2; n <= 6; n++) for (const variant of ['original', 'recharged']) {
        const seed = `current-engine-wrapper-diagnostic-v1-${n}p-${variant}`;
        const source = pool.find(f => {
            const g = f.request.state, p = f.request.player;
            if (g.players.length !== n || g.options.variant !== variant || !g.options.fastBid ||
                g.round <= 1 || g.phase !== 'Auction' || g.chosenPowerPlant) return false;
            const choices = E.availableMoves(g, g.players[p]).ChoosePowerPlant;
            const eligible = g.playerOrder.filter(i => !g.players[i].skipAuction && !g.players[i].isDropped);
            if (!choices?.length || eligible.length < Math.min(n,3)) return false;
            const plant = g.actualMarket.find(x => x.number === choices[0]);
            return eligible.every(i => g.players[i].money >= pricing(g,plant));
        });
        assert(source, `Missing predetermined nomination ${n}p ${variant}`);
        const start = scenario(source.request.state, {player: source.request.player, seed});
        const actor = source.request.player, other = start.playerOrder.findLast(i => i !== actor && !start.players[i].skipAuction && !start.players[i].isDropped);
        const nomination = {name: 'ChoosePowerPlant', data: start.players[actor].availableMoves.ChoosePowerPlant[0]};
        const normal = E.move(structuredClone(start), structuredClone(nomination), actor);
        const bid = {name: 'Bid', data: normal.minimunBid};
        E.move(normal, structuredClone(bid), actor);
        assert(normal.currentPlayers.includes(other));
        if (n > 2) assert(normal.currentPlayers[0] !== other);
        records.push(probe(normal, other, `${n}p-${variant}-pending-actor`));
        const zero = structuredClone(start); zero.players[other].money = 0;
        const after = await W.move(zero, [structuredClone(nomination), structuredClone(bid)], actor);
        if (n > 2) {
            assert.equal(after.phase, 'Auction'); assert(after.chosenPowerPlant);
            assert(!after.currentPlayers.includes(other));
            assert.equal(after.players[other].bid, 0);
        } else assert(!after.chosenPowerPlant, 'Two-player auction should resolve, possibly with a discard pending');
        assert(after.currentPlayers.length);
        const row = probe(after, after.currentPlayers[0], `${n}p-${variant}-wrapper-auto-pass`);
        row.autoPassed = other; row.counterfactualCash = true; records.push(row);
    }
    write('cases.json', records);
    const result = {completed_at: new Date().toISOString(), cases: records.length,
        compatible: records.filter(r => r.compatible).length,
        incompatible: records.filter(r => !r.compatible).map(r => ({name: r.name, error: r.error})),
        runtime_manifest_sha256: prepared.runtime_manifest_sha256,
        design_sha256: digest(path.join(out, 'design.json')), cases_sha256: digest(path.join(out, 'cases.json')),
        scope: 'Actual wrapper auto-pass and noncanonical pending-seat input compatibility. Cash edits are counterfactual; no claim of natural frequency or playing strength.',
        saved_nomination_roots: 10, new_full_games: 0, new_inference: 0, new_hf_jobs: 0,
        qualification_eligible: false, reserved_final_seeds_used: false};
    write('assessment.json', result); console.log(JSON.stringify(result));
})().catch(error => {console.error(error.stack); process.exit(1);});
