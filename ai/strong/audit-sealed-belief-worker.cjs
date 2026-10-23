// Read-only diagnostic using a hash-verified frozen training runtime.
const assert = require('node:assert/strict');
const path = require('node:path');
const readline = require('node:readline');
const base = process.env.POWERGRID_FROZEN_RUNTIME;
assert(base && path.isAbsolute(base));
const E = require(path.join(base, 'engine/dist/index.js'));
const {createAnalysisScenario} = require(path.join(base, 'engine/dist/src/analysis.js'));
const encoder = require(path.join(base, 'ai/strong/encoders.cjs')).forRevision('4.2-discard-correction');
const economic = require(path.join(base, 'ai/strong/economics.cjs'));
const clone = x => JSON.parse(JSON.stringify(x));
function publicOnly(state, seat) {
    const s = clone(E.stripSecret(state, seat));
    s.currentBid = 0;
    s.players.forEach(p => {p.bid=0;p.lastMove=null;});
    delete s.powerPlantDeckAfterStep3;
    delete s.automation;
    return s;
}
function encode(s, seat) {
    const g=publicOnly(s,seat);
    g.players[seat].availableMoves=E.availableMoves(g,g.players[seat]);
    return encoder.encode(g,seat);
}
function audit(q) {
    const seat=q.player, s=publicOnly(q.state,seat);
    assert(s.options.fastBid && s.chosenPowerPlant && s.options.showMoney);
    assert.equal(s.currentPlayers[0],seat);
    const eligible=s.playerOrder.filter(i=>!s.players[i].skipAuction&&!s.players[i].isDropped);
    const at=eligible.indexOf(seat);assert(at>=0);
    assert.deepEqual(s.currentPlayers,eligible.slice(at));
    const original=encode(s,seat), opponents=[];
    // Rewind only the simultaneous bidding window; no purchase resolves before
    // this actor, so public balances, plants and cities have not changed.
    for(let j=0;j<at;j++) {
        const i=eligible[j], earlier=clone(s);
        earlier.currentPlayers=eligible.slice(j);
        const x=encode(earlier,i);
        // Economic uses the legal menus; restore its acting menu explicitly.
        earlier.players[i].availableMoves=E.availableMoves(earlier,earlier.players[i]);
        const actual=economic.choose(earlier,i,()=>0.5).action;
        assert(x.moves.some(a=>JSON.stringify(a)===JSON.stringify(actual)));
        opponents.push({seat:i,money:s.players[i].money,minimum:s.minimunBid,
            sampled_nonzero:s.players[i].money>=s.minimunBid,
            uniform_mean:s.players[i].money>=s.minimunBid?(s.minimunBid+s.players[i].money)/2:0,
            economic:actual,encoded:x});
    }
    // Independent engine replay: arbitrary legal previous bids/passes must leave
    // the actor's public features and legal menu exactly as captured.
    const replay=createAnalysisScenario(s,{player:seat,seed:'sealed-belief-audit:'+q.rootId});
    replay.currentPlayers=eligible.slice();
    replay.players.forEach(p=>{p.bid=0;p.lastMove=null;});
    for(let j=0;j<at;j++) {
        const i=eligible[j];
        replay.players[i].availableMoves=E.availableMoves(replay,replay.players[i]);
        const menu=encode(replay,i).moves;
        const action=menu.find(a=>a.name==='Pass')||menu.find(a=>a.name==='Bid');
        assert(action);E.move(replay,action,i);
    }
    assert.deepEqual(replay.currentPlayers,s.currentPlayers);
    assert.deepEqual(encode(replay,seat),original);
    // Confirm the frozen scenario sampler uses the stated positive uniform
    // support, including opponents for whom the policy would instead pass.
    const scenario=createAnalysisScenario(s,{player:seat,seed:'sealed-belief-audit:'+q.rootId});
    for(const p of opponents) {
        const bid=scenario.players[p.seat].bid;
        assert(p.sampled_nonzero?Number.isInteger(bid)&&bid>=p.minimum&&bid<=p.money:bid===0);
    }
    return {original,opponents,eligible,already_committed:at};
}
(async()=>{for await(const line of readline.createInterface({input:process.stdin})){
    try{
        const q=JSON.parse(line), result=audit(q);
        // Mutate forbidden data. Neither reconstructed prompt nor hypothetical
        // policy belief may depend on actual sealed bids, deck or lastMove.
        const other=clone(q);
        other.state.players.forEach((p,i)=>{p.bid=999+i;p.lastMove={name:'Bid',data:999+i};});
        other.state.powerPlantsDeck=[{number:999}];other.state.hiddenLog=[{secret:true}];
        other.state.seed='forbidden';other.state.powerPlantDeckAfterStep3=[{number:998}];
        assert.deepEqual(audit(other),result);
        console.log(JSON.stringify(result));
    }catch(e){console.log(JSON.stringify({error:e.stack}));}
}})();
