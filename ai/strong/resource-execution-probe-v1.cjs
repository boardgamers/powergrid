// Independent authoritative-engine stepping for engineering resource-turn checks.
const assert=require('node:assert/strict'),{isDeepStrictEqual}=require('node:util');
const c=require('../core.cjs'),beliefs=require('./sealed-policy-beliefs.cjs');
const {createAnalysisScenario}=require('../../engine/dist/src/analysis.js');
const {calculateMaxCitiesPowered}=require('../../engine/dist/src/engine.js');
let g,seat,done;
function summary() {
    const p=g.players[seat];
    return {money:p.money,resources:c.RES.map(r=>p[r+'Left']),market:c.RES.map(r=>g[r+'Market']),
        fuelSupportedOutput:calculateMaxCitiesPowered(g,{...p,cities:Array(c.capacity(p))}),
        phase:g.phase,round:g.round,currentPlayers:g.currentPlayers};
}
function response() {
    return {done,summary:summary(),request:done?null:{state:beliefs.publicState(g,seat),player:seat},
        legal:done?[]:c.candidates(g,seat)};
}
(async()=>{
    for await(const line of require('node:readline').createInterface({input:process.stdin})) {
        const q=JSON.parse(line);
        if(q.op==='reset') {
            seat=q.request.player;
            g=createAnalysisScenario(beliefs.publicState(q.request.state,seat),{player:seat,seed:q.seed});done=false;
            assert.equal(g.phase,c.E.Phase.Resources);assert.deepEqual(g.currentPlayers,[seat]);
        } else if(q.op==='step') {
            assert(!done);assert(q.move.name==='BuyResource'||isDeepStrictEqual(q.move,{name:'Pass',data:true}));
            assert(c.allLegal(g,seat).some(m=>isDeepStrictEqual(m,q.move)));
            done=q.move.name==='Pass';c.E.move(g,structuredClone(q.move),seat);
            if(!done){assert.equal(g.phase,c.E.Phase.Resources);assert.deepEqual(g.currentPlayers,[seat]);}
        } else throw Error('Unknown resource-execution operation');
        console.log(JSON.stringify(response()));
    }
})().catch(error=>{console.error(error.stack);process.exitCode=1;});
