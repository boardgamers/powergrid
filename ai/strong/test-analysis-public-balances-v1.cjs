const test=require('node:test'),assert=require('node:assert/strict');
const fs=require('node:fs'),path=require('node:path');
const runtime=process.env.PG_REFERENCE_RUNTIME;
const original=require(path.join(runtime,'engine/dist/src/analysis.js')).createAnalysisScenario;
const repaired=require('./analysis-public-balances-v1.cjs').createAnalysisScenario;
const fixtures=fs.readFileSync(path.join(runtime,'ai/strong/fixtures/multiplayer-serving-v1.jsonl'),'utf8')
    .trim().split('\n').map(JSON.parse);
const failure=JSON.parse(fs.readFileSync(process.env.PG_REFERENCE_FAILURE_INPUT,'utf8'));
function clean(g) {
    const state=structuredClone(g);
    for (const p of state.players) {delete p.clock;delete p.lastActivity;}
    return state;
}

test('all 2553 public fixtures retain exact sampled worlds with the repair',()=>{
    assert.equal(fixtures.length,2553);
    for (const [i,fixture] of fixtures.entries()) {
        const {state,player}=fixture.request, before=JSON.stringify(state);
        const options={player,seed:'public-balance-parity-v1-'+i};
        assert(state.players.every(p=>p.money>=0));
        assert.deepEqual(clean(repaired(state,options)),clean(original(state,options)));
        assert.equal(JSON.stringify(state),before);
    }
});

test('unknown balances still use the historical replay and recover identical money',()=>{
    for (const fixture of fixtures.slice(0,24)) {
        const {state,player}=structuredClone(fixture.request);
        state.players[(player+1)%state.players.length].money=-1;
        const options={player,seed:'public-balance-unknown-v1'};
        const left=original(state,options),right=repaired(state,options);
        assert(left.players.every(p=>p.money>=0));
        assert.deepEqual(clean(left),clean(right));
    }
});

test('captured nested sealed-bid failure samples without inventing a public history',()=>{
    const state=failure.state,options={player:state.currentPlayers[0],seed:'captured-nested-failure-v1'};
    assert(state.players.every(p=>p.money>=0));
    assert.throws(()=>original(state,options),/not allowed to run the command ChoosePowerPlant/);
    const sampled=repaired(state,options);
    assert.deepEqual(sampled.log,state.log);
    assert.deepEqual(sampled.players.map(p=>p.money),state.players.map(p=>p.money));
    assert.deepEqual(sampled.currentPlayers,state.currentPlayers);
    assert.equal(sampled.powerPlantsDeck.length,state.cardsLeft);
    const polluted=structuredClone(state);
    polluted.seed='unknown-secret-seed';polluted.powerPlantsDeck=[{number:123456}];
    polluted.powerPlantDeckAfterStep3=[{number:654321}];
    polluted.hiddenLog=[{private:true}];
    for (const p of polluted.players) if (p.id!==options.player) p.bid=999;
    assert.deepEqual(clean(repaired(polluted,options)),clean(sampled));
});
