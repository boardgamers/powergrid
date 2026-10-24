const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const readline = require('node:readline');
const crypto = require('node:crypto');
const {performance} = require('node:perf_hooks');
const runtime = path.resolve(process.argv[2]), repository = path.resolve(process.argv[3]);
const output = path.resolve(process.argv[4]);
const c = require(path.join(runtime,'ai/core.cjs'));
const engine = require(path.join(runtime,'engine/dist/src/engine.js'));
const planning = require(path.join(runtime,'engine/dist/src/planning.js'));
const proposals = require(path.join(runtime,'ai/strong/resource-turn-plans-v1.cjs'));
const beliefs = require(path.join(runtime,'ai/strong/sealed-policy-beliefs.cjs'));
const hash = data => crypto.createHash('sha256').update(data).digest('hex');
const digest = file => hash(fs.readFileSync(file));
const read = file => JSON.parse(fs.readFileSync(file));
const clone = value => structuredClone(value);
fs.mkdirSync(output,{recursive:false});
const write = (name,value) => fs.writeFileSync(path.join(output,name),JSON.stringify(value,null,2)+'\n',{flag:'wx'});
const report = {checker_sha256:digest(__filename),resource_positions:0,bundles:0,real_purchases:0,
    zero_options:0,secret_invariance:0,construction_cases:0,construction_paths:0,joint_witnesses:0,
    exhaustive_inventory_states:0,minimum_fuel_price_checks:0,invalid_requests_rejected:0,
    cells:{},timing:{enumerationMs:[],constructionMs:[]},passed:false,
    qualification_eligible:false,new_strength_games:0,new_hf_jobs:0,gradients:false,reserved_final_seeds_used:false};
const selected = new Map();

function engineOutput(g,seat) {
    const p = g.players[seat];
    return engine.calculateMaxCitiesPowered(g,{...p,cities:Array(c.capacity(p))});
}

function checkBundle(q,bundle) {
    const g = clone(q.state), seat = q.player, original = g.players[seat].money;
    const stock = c.RES.map(r => g.players[seat][r+'Left']);
    for (const action of bundle.actions) {
        assert(c.allLegal(g,seat).some(m => JSON.stringify(m) === JSON.stringify(action)));
        c.E.move(g,clone(action),seat);
        assert.equal(g.phase,c.E.Phase.Resources);assert(g.currentPlayers.includes(seat));
        report.real_purchases++;
    }
    assert.equal(original-g.players[seat].money,bundle.cost);
    assert.equal(g.players[seat].money,bundle.remainingMoney);
    assert.deepEqual(c.RES.map((r,i) => g.players[seat][r+'Left']-stock[i]),bundle.counts);
    assert.equal(engineOutput(g,seat),bundle.fuelSupportedOutput);
    assert.equal(engine.calculateMaxCitiesPowered(g,g.players[seat]),bundle.poweredCurrentCities);
    report.bundles++;
}

function secretVariant(q) {
    const hidden = clone(q);
    hidden.state.seed = 'private';hidden.state.powerPlantsDeck = [{number:9999}];
    hidden.state.powerPlantDeckAfterStep3 = [{number:9998}];hidden.state.hiddenLog = [{private:true}];
    hidden.state.currentBid = 9997;
    hidden.state.players.forEach(p => {p.bid = 9996;p.lastMove = {name:'Bid',data:9995};});
    return hidden;
}

function bruteForceFuelCosts(q,bundles) {
    const g = clone(q.state), seat = q.player, p = g.players[seat];
    const held = c.RES.map(r => p[r+'Left']);
    const limits = [p.coalCapacity+p.hybridCapacity,p.oilCapacity+p.hybridCapacity,p.garbageCapacity,p.uraniumCapacity]
        .map((n,i) => Math.min(n-held[i],g[c.RES[i]+'Market']));
    assert(limits.every(n => Number.isInteger(n) && n >= 0));
    const prefixes = c.RES.map((r,i) => {
        const a = [0], prices = g[r+'Prices'], count = g[r+'Market'];
        for (let k = 0; k < limits[i]; k++) a.push(a[a.length-1]+prices[prices.length-count+k]);
        return a;
    });
    const capacity = c.capacity(p), best = Array(capacity+1).fill(Infinity);
    for (let coal=0;coal<=limits[0];coal++) for (let oil=0;oil<=limits[1];oil++)
        for (let garbage=0;garbage<=limits[2];garbage++) for (let uranium=0;uranium<=limits[3];uranium++) {
            const counts = [coal,oil,garbage,uranium], stock = held.map((n,i) => n+counts[i]);
            const cost = counts.reduce((sum,n,i) => sum+prefixes[i][n],0);
            if (cost > p.money) continue;
            // Independent shared-storage check using the sum of overflow into hybrids.
            if (Math.max(0,stock[0]-p.coalCapacity)+Math.max(0,stock[1]-p.oilCapacity) > p.hybridCapacity) continue;
            const player = {...p,cities:Array(capacity)};
            c.RES.forEach((r,i) => {player[r+'Left'] = stock[i];});
            const output = engine.calculateMaxCitiesPowered(g,player);
            for (let n=0;n<=output;n++) best[n] = Math.min(best[n],cost);
            report.exhaustive_inventory_states++;
        }
    for (let n=0;n<=capacity;n++) {
        const offered = Math.min(...bundles.filter(b => b.fuelSupportedOutput >= n).map(b => b.cost));
        assert.equal(offered,best[n],`Missing minimum-cost fuel target ${n}`);
        report.minimum_fuel_price_checks++;
    }
}

function checkConstruction(label,q) {
    const started = performance.now();
    const result = proposals.proposals(q);
    report.timing.constructionMs.push(performance.now()-started);
    assert.deepEqual(proposals.proposals(secretVariant(q)),result);
    assert.equal(result.selectedMove,null);assert.equal(result.construction.optimal,false);
    const byCities = new Map(result.construction.paths.map(p => [p.cities,p]));
    for (const path of result.construction.paths) {
        let plan = planning.startRoundPlan(proposals.publicRoot(q),q.player,c.E.Phase.Building);
        for (const action of path.actions) plan = planning.planMove(plan,action);
        assert.equal(plan.state.players[q.player].cities.length,path.cities);
        assert.equal(q.state.players[q.player].money-plan.state.players[q.player].money,path.cost);
        report.construction_paths++;
    }
    for (const joint of result.joint) {
        const bundle = result.bundles.find(b => b.id === joint.bundle);
        assert(joint.witnesses.length);
        const witness = joint.witnesses[joint.witnesses.length-1], path = byCities.get(witness.cities);
        let plan = planning.startRoundPlan(proposals.publicRoot(q),q.player,c.E.Phase.Resources);
        for (const action of bundle.actions) plan = planning.planMove(plan,action);
        plan = planning.planMove(plan,{name:'Pass',data:true});
        for (const action of path.actions) plan = planning.planMove(plan,action);
        const p = plan.state.players[q.player];
        assert.equal(p.money,witness.remainingMoney);assert.equal(p.cities.length,witness.cities);
        assert.equal(engine.calculateMaxCitiesPowered(plan.state,p),witness.powered);
        assert.equal(bundle.cost+path.cost,witness.totalCost);
        report.joint_witnesses++;
    }
    bruteForceFuelCosts(q,result.bundles);
    report.construction_cases++;
    write(label+'.json',{request:q,result});
    console.log(JSON.stringify({case:label,bundles:result.bundles.length,paths:result.construction.paths.length,
        constructionMs:report.timing.constructionMs[report.timing.constructionMs.length-1]}));
    return result;
}

function summary(g) {
    return {round:g.round,step:g.step,phase:g.phase,citiesToEndGame:g.citiesToEndGame,
        currentPlayers:[...g.currentPlayers],playerOrder:[...g.playerOrder],
        market:Object.fromEntries(c.RES.map(r => [r,{count:g[r+'Market'],prices:g[r+'Prices']}])),
        players:g.players.map(p => ({money:p.money,cities:p.cities.map(x=>x.name),powered:p.citiesPowered,
            capacity:c.capacity(p),resources:Object.fromEntries(c.RES.map(r=>[r,p[r+'Left']])),
            powerable:engine.calculateMaxCitiesPowered(g,p),fuelSupportedCapacity:engineOutput(g,p.id),
            plants:p.powerPlants.map(pp=>({number:pp.number,capacity:pp.citiesPowered,type:pp.type,cost:pp.cost})),
            totalIncome:p.totalIncome,totalSpentCities:p.totalSpentCities,totalSpentConnections:p.totalSpentConnections,
            totalSpentPlants:p.totalSpentPlants,totalSpentResources:p.totalSpentResources}))};
}

(async () => {
    const prep = read(path.join(path.dirname(runtime),'preparation.json'));
    for (const [name,sha] of Object.entries(prep.runtime_hashes)) assert.equal(digest(path.join(runtime,name)),sha);
    assert.equal(digest(path.join(runtime,'ai/strong/resource-turn-plans-v1.cjs')),prep.proposal_module_sha256);
    const fixture = path.join(runtime,'ai/strong/fixtures/multiplayer-serving-v1.jsonl');
    assert.equal(digest(fixture),'f1c97bf909e38e5df372a89d169d80f5a6f24c00dccefacd60b10b767f1fcfa0');
    let index = 0;
    for await (const line of readline.createInterface({input:fs.createReadStream(fixture)})) {
        const {request} = JSON.parse(line), {state,player} = request;
        if (state.phase !== c.E.Phase.Resources) {index++;continue;}
        const before = JSON.stringify(request), start = performance.now();
        const result = proposals.proposals(request,{construction:false});
        report.timing.enumerationMs.push(performance.now()-start);
        assert.equal(JSON.stringify(request),before);
        assert.deepEqual(proposals.proposals(secretVariant(request),{construction:false}),result);
        report.secret_invariance++;
        assert(result.bundles.some(b => b.id === '0,0,0,0'));
        assert.equal(new Set(result.bundles.map(b=>b.id)).size,result.bundles.length);
        report.zero_options++;
        for (const bundle of result.bundles) checkBundle(request,bundle);
        const key = `${state.players.length}p-${state.options.variant}-${state.options.fastBid?'sealed':'open'}`;
        report.cells[key] = (report.cells[key] || 0)+1;
        const first = key+'-first', largest = key+'-largest-budget';
        if (!selected.has(first)) selected.set(first,{index,request});
        if (!selected.has(largest) || state.players[player].money > selected.get(largest).request.state.players[player].money)
            selected.set(largest,{index,request});
        report.resource_positions++;index++;
    }
    assert.equal(report.resource_positions,755);assert.equal(Object.keys(report.cells).length,20);
    for (const [label,{request}] of selected) checkConstruction(label,request);
    const protocolPath = path.join(repository,'ai/strong/weak-cell-resource-counterfactual-v1.json');
    const protocol = read(protocolPath), referenceRoot = path.join(repository,protocol.reference_directory);
    const tracePath = path.join(referenceRoot,protocol.case+'.jsonl');
    assert.equal(digest(tracePath),protocol.reference_trace_sha256);
    const expected = read(path.join(referenceRoot,'selection.json')).requested[protocol.case].expected;
    const trace = fs.readFileSync(tracePath,'utf8').trim().split('\n').map(JSON.parse);
    const g = c.E.setup(expected.playerCount,{map:'Germany',variant:expected.variant,
        fastBid:expected.sealed,showMoney:true},expected.gameSeed);
    for (let i=0;i<protocol.root_index;i++) {
        assert.deepEqual(summary(g),trace[i].before);
        c.E.move(g,clone(trace[i].action),trace[i].seat);
        assert.deepEqual(summary(g),trace[i].after);
    }
    assert.deepEqual(summary(g),trace[protocol.root_index].before);
    const q = {state:beliefs.publicState(g,protocol.target.seat),player:protocol.target.seat};
    const result = checkConstruction('known-resource-omission',q);
    const bundle = result.bundles.find(b => b.id === '3,0,0,0');
    assert(bundle && bundle.cost === 17 && bundle.fuelSupportedOutput === 24);
    const joint = result.joint.find(j=>j.bundle===bundle.id).witnesses.find(w=>w.cities===21);
    assert(joint && joint.powered === 21 && joint.remainingMoney >= 0);
    report.known_case = {prefix_moves_replayed:protocol.root_index,reference_trace_sha256:protocol.reference_trace_sha256,
        bundle:bundle.id,cost:bundle.cost,fuelSupportedOutput:bundle.fuelSupportedOutput,witness:joint};
    for (const modify of [x=>{x.state.map.name='USA';},x=>{x.state.options.showMoney=false;},
        x=>{x.state.phase='Auction';},x=>{x.state.currentPlayers=[];}]) {
        const bad = clone(q);modify(bad);
        assert.throws(()=>proposals.proposals(bad),{name:'AssertionError'});report.invalid_requests_rejected++;
    }
    assert.equal(report.construction_cases,41);
    report.passed = true;
    report.scope = 'Candidate-generator engineering only. 755 existing resource positions, 40 fixed construction representatives and one reproduced omission; minimum fuel costs independently checked by exhaustive legal inventory enumeration. No chosen move, value model, opponent-response prediction or strength/latency qualification.';
    report.preparation_sha256 = digest(path.join(path.dirname(runtime),'preparation.json'));
    write('assessment.json',report);
    console.log(JSON.stringify({...report,timing:{enumerationSamples:report.timing.enumerationMs.length,
        constructionSamples:report.timing.constructionMs.length}}));
})().catch(error=>{write('failure.json',{error:error.stack,report});console.error(error);process.exitCode=1;});
