// Canonical public roots from changing behavior policies; no outcome filtering.
const assert = require('node:assert/strict');
const encoders = require('./encoders.cjs');
const {stripSecret} = require('../../engine/dist/src/engine.js');
const original = encoders.forRevision, wrappers = new Map();
function decision(moves) {
    if (moves.length < 2) return null;
    for (const [name, kind] of [['ChoosePowerPlant','nomination'],['Bid','bid'],['Build','building']]) {
        if (moves.some(m=>m.name===name)) return kind;
    }
    return null;
}
function publicState(g, seat) {
    const state=structuredClone(stripSecret(g,seat));
    delete state.powerPlantDeckAfterStep3;delete state.automation;
    if(state.options.fastBid)state.currentBid=0;
    state.players.forEach(p=>{p.lastMove=null;if(state.options.fastBid)p.bid=0;});
    return state;
}
encoders.forRevision=function(revision){
    if(!wrappers.has(revision)){
        const encoder=original(revision);
        wrappers.set(revision,{...encoder,encode(g,seat){
            const observation=encoder.encode(g,seat),kind=decision(observation.moves);
            if(kind){
                const state=publicState(g,seat);
                assert.deepEqual(state.powerPlantsDeck,[]);assert.deepEqual(state.hiddenLog,[]);
                assert.equal(state.seed,'secret');assert(state.options.showMoney);
                observation.strategicRoot={decision:kind,request:{state,player:seat},legal:structuredClone(observation.moves)};
            }
            return observation;
        }});
    }
    return wrappers.get(revision);
};
module.exports={decision,publicState};
