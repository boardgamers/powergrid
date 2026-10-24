// Replay every recorded public move through the frozen engine; no neural calls.
const fs=require('node:fs'), path=require('node:path'), assert=require('node:assert/strict');
const {createFilter}=require('./endgame-loss-filter.cjs');
const root=path.resolve(__dirname,'../..');
const previous=path.join(root,'ai/runs/policy-iteration-legacy-replays-v1');
const reference=path.join(root,'ai/runs/policy-iteration-economy-replays-v1');
const runtime=path.join(previous,'runtime');
const c=require(path.join(runtime,'ai/core.cjs'));
const engine=require(path.join(runtime,'engine/dist/src/engine.js'));
const selection=JSON.parse(fs.readFileSync(path.join(previous,'selection.json'),'utf8'));
const protocol=JSON.parse(fs.readFileSync(path.join(__dirname,'policy-iteration-endgame-counterfactual-protocol-v1.json'),'utf8'));
const branches=JSON.parse(fs.readFileSync(path.join(root,'ai/runs/policy-iteration-endgame-branches-v1/branches.json'),'utf8'));
const crypto=require('node:crypto');
const digest=p=>crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
for(const [name,sha] of Object.entries(selection.runtime_hashes)) assert.equal(digest(path.join(runtime,name)),sha);
const check=createFilter(c,engine.calculateMaxCitiesPowered);
function summary(g) {
    return {round:g.round,step:g.step,phase:g.phase,citiesToEndGame:g.citiesToEndGame,
        currentPlayers:[...g.currentPlayers],playerOrder:[...g.playerOrder],
        market:Object.fromEntries(c.RES.map(r=>[r,{count:g[r+'Market'],prices:g[r+'Prices']}])),
        players:g.players.map(p=>({money:p.money,cities:p.cities.map(x=>x.name),powered:p.citiesPowered,
            capacity:c.capacity(p),resources:Object.fromEntries(c.RES.map(r=>[r,p[r+'Left']])),
            powerable:engine.calculateMaxCitiesPowered(g,p),
            fuelSupportedCapacity:engine.calculateMaxCitiesPowered(g,{...p,cities:Array(c.capacity(p))}),
            plants:p.powerPlants.map(pp=>({number:pp.number,capacity:pp.citiesPowered,type:pp.type,cost:pp.cost})),
            totalIncome:p.totalIncome,totalSpentCities:p.totalSpentCities,
            totalSpentConnections:p.totalSpentConnections,totalSpentPlants:p.totalSpentPlants,
            totalSpentResources:p.totalSpentResources}))};
}
const records=[], games=[];
let allMoves=0;
for(const [name,request] of Object.entries(selection.requested)) {
    const e=request.expected;
    const file=path.join(reference,name+'.jsonl');
    const recorded=JSON.parse(fs.readFileSync(path.join(reference,'replays.json'),'utf8'))[name];
    assert.equal(digest(file),recorded.trace_sha256);
    const trace=fs.readFileSync(file,'utf8').trim().split('\n').map(JSON.parse);
    const g=c.E.setup(5,{map:'Germany',variant:e.variant,fastBid:e.sealed,showMoney:true},e.gameSeed);
    for(let i=0;i<trace.length;i++) {
        const row=trace[i];
        assert.deepEqual(summary(g),row.before);
        if(!row.legacy) {
            const before=JSON.stringify(g), certificate=check(g,row.seat,row.action);
            assert.equal(JSON.stringify(g),before,'Certificate mutated the engine state');
            const changed=structuredClone(g);
            changed.seed='unrelated';changed.powerPlantsDeck=[];changed.hiddenLog=[];
            delete changed.powerPlantDeckAfterStep3;
            assert.deepEqual(check(changed,row.seat,row.action),certificate,'Certificate used private future information');
            const target=protocol.cases.find(q=>q.name===name && q.round===g.round &&
                q.seat===row.seat && JSON.stringify(q.original)===JSON.stringify(row.action));
            if(target) {
                const original=branches.find(b=>b.name===name && b.branch==='original');
                const alternative=branches.find(b=>b.name===name && b.branch==='pass');
                assert(original && alternative && !original.truncated && !alternative.truncated);
                if(certificate) assert.equal(original.win,0,'Strict loss certificate contradicted by original play');
                records.push({name,model:request.model,root_index:i,certificate,
                    original_win:original.win,pass_win:alternative.win});
            } else assert.equal(certificate,null,'Unexpected certified root outside the fixed threshold cases');
        }
        c.E.move(g,structuredClone(row.action),row.seat);
        assert.deepEqual(summary(g),row.after);
    }
    assert.equal(g.phase,'Game End');
    assert.equal(trace.length,e.steps);
    allMoves+=trace.length;games.push({name,moves:trace.length,trace_sha256:digest(file)});
}
assert.equal(records.length,protocol.cases.length);
const certified=records.filter(r=>r.certificate);
const result={games:games.length,root_moves:allMoves,threshold_cases:records.length,
    certified_cases:certified.length,
    certified_changes:{gains:certified.filter(r=>r.pass_win>r.original_win).length,
        losses:certified.filter(r=>r.pass_win<r.original_win).length,
        unchanged:certified.filter(r=>r.pass_win===r.original_win).length},
    all_before_and_after_states_match:true,all_checks_read_only:true,private_future_invariance:true,
    records,game_provenance:games,source:selection.source,
    code_hashes:Object.fromEntries([__filename,path.join(__dirname,'endgame-loss-filter.cjs')]
        .map(p=>[path.relative(root,p),digest(p)])),
    new_strength_games:0,candidate_selected:false,qualification_eligible:false,reserved_final_seeds_used:false,
    scope:'Engineering certificate audit on 49 fixed outcome-selected five-player Germany games. Full root ledgers replay through the frozen engine with identical states. Certificates do not use outcomes, private bids or deck order. The eight diagnosed certificate branches are not a fresh win-rate sample or qualification; no serving/evaluation integration.'};
const output=process.argv[2];assert(output && !fs.existsSync(output));
fs.writeFileSync(output,JSON.stringify(result,null,2)+'\n');
console.log(JSON.stringify({games:result.games,root_moves:allMoves,threshold_cases:records.length,
    certified_cases:certified.length,certified_changes:result.certified_changes}));
