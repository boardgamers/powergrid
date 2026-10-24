// Research proposals only: no chosen move, learned value, serving integration or job submission.
const assert = require('node:assert/strict');
const c = require('../core.cjs');
const eco = require('./economics.cjs');
const beliefs = require('./sealed-policy-beliefs.cjs');
const planning = require('../../engine/dist/src/planning.js');
const REVISION = 'resource-turn-proposals-v1';
const clone = value => structuredClone(value);
const compareText = (a,b) => a < b ? -1 : a > b ? 1 : 0;

function publicRoot(request) {
    const g = beliefs.publicState(request.state,request.player);
    assert.equal(g.map.name,'Germany','Only standard Germany is supported');
    assert(['original','recharged'].includes(g.options.variant));
    assert(g.players.length >= 2 && g.players.length <= 6);
    assert.equal(g.phase,c.E.Phase.Resources);
    assert(g.currentPlayers.includes(request.player),'Only a pending resource buyer');
    assert(g.options.showMoney && g.players.every(p => !p.isDropped && p.money >= 0));
    const p = g.players[request.player];
    assert(!p.passed && p.powerPlants.every(pp => Number.isInteger(pp.type) && pp.type >= 0 && pp.type <= 6));
    assert(p.powerPlants.filter(pp => pp.type >= 5).every(pp => pp.cost === 0));
    assert(p.powerPlants.length <= (g.players.length === 2 ? 4 : 3));
    for (const resource of c.RES) {
        assert(Number.isInteger(g[resource+'Market']) && g[resource+'Market'] >= 0);
        assert(g[resource+'Market'] <= g[resource+'Prices'].length);
        assert(Number.isInteger(p[resource+'Left']) && p[resource+'Left'] >= 0);
    }
    return g;
}

function stockFits(player,stock) {
    const hybrid = player.hybridCapacity;
    return stock[0] <= player.coalCapacity+hybrid-Math.max(0,stock[1]-player.oilCapacity) &&
        stock[1] <= player.oilCapacity+hybrid-Math.max(0,stock[0]-player.coalCapacity) &&
        stock[2] <= player.garbageCapacity && stock[3] <= player.uraniumCapacity;
}

function maximumOutput(plans,stock) {
    return Math.max(...plans.filter(p => p.used.every((n,i) => n <= stock[i])).map(p => p.power));
}

function fuelBundles(state,seat) {
    const player = state.players[seat], plans = eco.plans(state,player);
    const held = c.RES.map(r => player[r+'Left']);
    const unique = new Map();
    let combinations = 0, unavailable = 0, unaffordable = 0, overStorage = 0;
    // Two-cycle requirements expose some reserve/denial alternatives; they do
    // not assert two future rounds or enumerate every possible stockpile.
    for (const cycles of [1,2]) for (const plan of plans) {
        combinations++;
        const counts = plan.used.map((n,i) => Math.max(0,n*cycles-held[i]));
        const stock = held.map((n,i) => n+counts[i]);
        if (!stockFits(player,stock)) {overStorage++;continue;}
        let cost = 0, valid = true;
        for (let i = 0; i < 4; i++) {
            const resource = c.RES[i], count = state[resource+'Market'], prices = state[resource+'Prices'];
            if (counts[i] > count) {valid = false;break;}
            for (let k = 0; k < counts[i]; k++) cost += prices[prices.length-count+k];
        }
        if (!valid) {unavailable++;continue;}
        if (cost > player.money) {unaffordable++;continue;}
        const key = counts.join(',');
        if (!unique.has(key)) {
            const output = maximumOutput(plans,stock);
            unique.set(key,{id:key,counts,cost,remainingMoney:player.money-cost,stock,
                fuelSupportedOutput:output,poweredCurrentCities:Math.min(player.cities.length,output),
                actions:counts.flatMap((count,i) => Array.from({length:count},() =>
                    ({name:'BuyResource',data:{resource:c.RES[i]}}))),requirements:[]});
        }
        unique.get(key).requirements.push({cycles,plants:plan.plants,output:plan.power,used:plan.used});
    }
    assert(unique.has('0,0,0,0'),'The zero-purchase baseline must be preserved');
    const bundles = [...unique.values()].sort((a,b) => a.cost-b.cost || compareText(a.id,b.id));
    return {bundles,enumeration:{plantRequirementCombinations:combinations,uniqueBundles:bundles.length,
        unavailable,unaffordable,overStorage,zeroPurchasePreserved:true,
        scope:'Every plant-subset/hybrid-split requirement for one or two identical fuel cycles; not every stockpile or a value ranking.'}};
}

function routeKey(plan,seat) {
    return plan.state.players[seat].cities.map(city => city.name).sort().join('|');
}

function constructionFrontier(state,seat,{beamWidth=8,branchWidth=6}={}) {
    assert(Number.isInteger(beamWidth) && beamWidth >= 1 && beamWidth <= 32);
    assert(Number.isInteger(branchWidth) && branchWidth >= 1 && branchWidth <= 42);
    const player = state.players[seat], start = planning.startRoundPlan(state,seat,c.E.Phase.Building);
    let frontier = [start], expanded = 0;
    const paths = [{cities:player.cities.length,cost:0,actions:[]}];
    const price = plan => player.money-plan.state.players[seat].money;
    const order = (a,b) => price(a)-price(b) || compareText(routeKey(a,seat),routeKey(b,seat)) ||
        compareText(JSON.stringify(a.entries),JSON.stringify(b.entries));
    for (let count = player.cities.length+1; count <= 21 && frontier.length; count++) {
        const candidates = new Map();
        for (const plan of frontier) {
            const offered = plan.state.players[seat].availableMoves.Build || [];
            const options = offered.slice().sort((a,b) => a.price-b.price || compareText(a.name,b.name));
            for (const data of options.slice(0,branchWidth)) {
                const next = planning.planMove(plan,{name:'Build',data:clone(data)});
                expanded++;
                assert.equal(next.state.players[seat].cities.length,count);
                assert(next.state.players[seat].money >= 0);
                const key = routeKey(next,seat), previous = candidates.get(key);
                if (!previous || order(next,previous) < 0) candidates.set(key,next);
            }
        }
        frontier = [...candidates.values()].sort(order).slice(0,beamWidth);
        if (frontier.length) {
            const best = frontier[0];
            paths.push({cities:count,cost:price(best),actions:best.entries.map(entry => entry.move)});
        }
    }
    return {beamWidth,branchWidth,expanded,paths,optimal:false,
        scope:'Legal construction witnesses on the current board, holding opponents fixed and predicting no deck draws. Bounded beam search; failure to find a path is not proof of impossibility.'};
}

function proposals(request,options={}) {
    const state = publicRoot(request), seat = request.player, player = state.players[seat];
    const {bundles,enumeration} = fuelBundles(state,seat);
    const construction = options.construction === false ? null : constructionFrontier(state,seat,options);
    const joint = construction && bundles.map(bundle => {
        const witnesses = construction.paths.filter(path => path.cost+bundle.cost <= player.money);
        return {bundle:bundle.id,witnesses:witnesses.map(path => ({cities:path.cities,
            constructionCost:path.cost,totalCost:path.cost+bundle.cost,
            remainingMoney:player.money-path.cost-bundle.cost,
            powered:Math.min(path.cities,bundle.fuelSupportedOutput)}))};
    });
    return {revision:REVISION,seat,phase:state.phase,round:state.round,step:state.step,
        cities:player.cities.length,money:player.money,capacity:c.capacity(player),
        endThreshold:state.citiesToEndGame,bundles,enumeration,construction,joint,
        selectedMove:null,qualification_eligible:false,
        assumptions:'Public candidate proposals only. No opponent response or later city availability is predicted. Construction witnesses annotate bundles without pruning them; fuel denial/reserves and city routes still require actual opponent continuations and fresh evaluation.'};
}

module.exports = {REVISION,publicRoot,stockFits,maximumOutput,fuelBundles,constructionFrontier,proposals};
if (require.main === module) {
    (async () => {
        for await (const line of require('node:readline').createInterface({input:process.stdin})) {
            const q = JSON.parse(line);
            console.log(JSON.stringify(proposals(q,q.options || {})));
        }
    })().catch(error => {console.error(error);process.exitCode=1;});
}
