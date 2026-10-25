// Replay the three hash-selected existing games. No policy inference or new games.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const root = path.resolve(__dirname, '../..');
const runtime = path.join(root, 'ai/runs/resource-replanning-job-source-prepared-v1/layout');
const run = path.join(root, 'ai/runs/resource-plan-consistency-v1');
const read = p => JSON.parse(fs.readFileSync(p, 'utf8'));
const sha = p => crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
const evidence = read(path.join(root, 'ai/strong/resource-replanning-development-complete-evidence-v1.json'));
const manifestPath = path.join(runtime, 'resource-job-manifest.json');
assert.equal(sha(manifestPath), evidence.source.manifest_sha256);
const manifest = read(manifestPath);
for (const [name, expected] of Object.entries(manifest)) assert.equal(sha(path.join(runtime, name)), expected, name);
const assessment = read(path.join(run, 'assessment.json'));
const archiveManifest = read(path.join(root, 'ai/runs/resource-replanning-development-complete-evidence-v1/manifest.json'));
assert.equal(sha(path.join(root, 'ai/runs/resource-replanning-development-complete-evidence-v1/manifest.json')), evidence.manifest_sha256);
const c = require(path.join(runtime, 'ai/core.cjs'));
const eco = require(path.join(runtime, 'ai/strong/economics.cjs'));
const beliefs = require(path.join(runtime, 'ai/strong/sealed-policy-beliefs.cjs'));
const PASS = {name: 'Pass', data: true};

function inventory(g, seat) {
    const p = g.players[seat];
    return {money: p.money, stock: c.RES.map(r => p[r + 'Left']), market: c.RES.map(r => g[r + 'Market'])};
}

function fuel(g, seat) {
    const p = g.players[seat], stock = c.RES.map(r => p[r + 'Left']);
    const output = Math.max(...eco.plans(g, p).filter(plan => plan.used.every((n, i) => n <= stock[i])).map(plan => plan.power));
    return {...inventory(g, seat), cities: p.cities.length, capacity: c.capacity(p),
        fuelSupportedOutput: output, poweredExistingCities: Math.min(output, p.cities.length),
        plants: p.powerPlants.map(plant => ({number: plant.number, type: plant.type, cost: plant.cost, cities: plant.cities}))};
}

function purchaseCopy(g, seat, actions) {
    const copy = structuredClone(g);
    assert.deepEqual(actions.at(-1), PASS);
    for (const move of actions.slice(0, -1)) {
        assert.equal(move.name, 'BuyResource');
        assert(c.allLegal(copy, seat).some(candidate => JSON.stringify(candidate) === JSON.stringify(move)));
        c.E.move(copy, structuredClone(move), seat);
        assert.equal(copy.phase, c.E.Phase.Resources);
        assert.deepEqual(copy.currentPlayers, [seat]);
    }
    return fuel(copy, seat);
}

const results = [];
for (const [kind, entry] of Object.entries(assessment.examples)) {
    // These choices were fixed by hash before replay. Abort rather than replace
    // them if a future input would require an unimplemented opponent.
    assert(['legacy', 'economic'].includes(entry.opponent));
    const relative = `ai/runs/resource-replanning-development-collected-v1/resource-replanning-development-v1-resource-filter-${entry.players}p-${entry.opponent}-0-4/artifacts/evaluation`;
    const folder = path.join(root, relative);
    for (const name of ['evaluation.json', `decisions-${entry.episode}.jsonl`]) {
        assert.equal(sha(path.join(folder, name)), archiveManifest[relative + '/' + name]);
    }
    const report = read(path.join(folder, 'evaluation.json'));
    const record = report.results.find(row => row.episode === entry.episode);
    const rows = fs.readFileSync(path.join(folder, `decisions-${entry.episode}.jsonl`), 'utf8').trim().split('\n').map(JSON.parse);
    assert.equal(rows.length, record.decisions);
    const config = report.config, seat = entry.seat;
    const g = c.E.setup(entry.players, {map: 'Germany', variant: record.terminal.variant,
        fastBid: record.terminal.sealed, showMoney: true}, record.terminal.gameSeed);
    const rng = c.seedrandom(record.terminal.gameSeed + '-bot');
    let steps = 0, opponentMoves = 0, purchaseTransitions = 0, detail = null;
    function advance() {
        while (!c.E.ended(g) && g.currentPlayers[0] !== seat) {
            const actor = g.currentPlayers[0];
            if (config.opponent === 'legacy') {
                const old = Math.random;
                Math.random = rng;
                try { c.E.moveAI(g, actor); } finally { Math.random = old; }
            } else c.E.move(g, eco.choose(g, actor, rng, 'economic').action, actor);
            steps++; opponentMoves++;
        }
    }
    advance();
    for (const row of rows) {
        assert(!c.E.ended(g)); assert.equal(g.currentPlayers[0], seat); assert.equal(g.round, row.round);
        const legal = c.candidates(g, seat);
        assert.deepEqual(legal[row.index], row.move);
        if (row.resourcePlan) {
            assert.equal(g.phase, c.E.Phase.Resources);
            const plan = row.resourcePlan;
            const zero = plan.bundles.findIndex(bundle => bundle.id === '0,0,0,0');
            assert.deepEqual(inventory(g, seat), plan.receipts[zero].resourceTurn.afterPurchases);
            for (const bundle of plan.bundles) {
                const after = purchaseCopy(g, seat, bundle.actions);
                assert.equal(g.players[seat].money - after.money, bundle.cost);
            }
        }
        const target = entry.decision ?? entry.first_decision;
        if (row.decision === target) {
            assert.equal(g.round, entry.round);
            let intended, actual;
            if (entry.decision !== undefined) {
                const previous = rows[row.decision - 2];
                assert.equal(previous.decision, entry.previous_decision);
                intended = previous.resourcePlan.actions.slice(1);
                actual = row.resourcePlan.actions;
            } else {
                intended = row.resourcePlan.actions;
                actual = rows.slice(entry.first_decision - 1, entry.last_decision).map(r => r.move);
            }
            detail = {kind, selection: entry, request: {state: beliefs.publicState(g, seat), player: seat},
                intendedActions: intended, selectedOrExecutedActions: actual,
                before: fuel(g, seat), afterIntendedPurchases: purchaseCopy(g, seat, intended),
                afterSelectedOrExecutedPurchases: purchaseCopy(g, seat, actual),
                note: 'Within-turn legal inventory comparison only. No counterfactual continuation or outcome.'};
        }
        const beforeOpponents = opponentMoves;
        c.E.move(g, structuredClone(row.move), seat); steps++;
        if (row.move.name === 'BuyResource') {
            assert.equal(g.phase, c.E.Phase.Resources); assert.deepEqual(g.currentPlayers, [seat]);
        }
        advance();
        if (row.move.name === 'BuyResource') {
            assert.equal(opponentMoves, beforeOpponents); purchaseTransitions++;
        }
    }
    assert(c.E.ended(g)); assert.equal(steps, record.terminal.steps);
    assert.deepEqual(c.outcome(g), record.terminal.value);
    assert.deepEqual({round: g.round, players: g.players.map(p => ({cities: p.cities.length,
        powered: p.citiesPowered, money: p.money, capacity: c.capacity(p), plants: p.powerPlants.map(pp => pp.number)}))}, record.terminal.final);
    assert(detail);
    results.push({kind, complete: true, learnerMoves: rows.length, opponentMoves, purchaseTransitions,
        originalTerminalExact: true, detail});
    console.log(JSON.stringify({kind, learnerMoves: rows.length, purchaseTransitions, originalTerminalExact: true}));
}
const output = {complete: true, runtime_manifest_sha256: sha(manifestPath), unchanged_runtime_files: Object.keys(manifest).length,
    assessment_sha256: sha(path.join(run, 'assessment.json')), replay_code_sha256: sha(__filename),
    original_games_replayed: results.length, results, new_strength_games: 0, policy_inference: false,
    new_hf_jobs: 0, qualification_eligible: false, reserved_final_seeds_used: false};
fs.writeFileSync(path.join(run, 'replays.json'), JSON.stringify(output, null, 2) + '\n', {flag: 'wx'});
