// Authoritative public purchase replay for the integration check, no anchor code.
const assert=require('node:assert/strict');
const path=require('node:path');
const {isDeepStrictEqual}=require('node:util');
const runtime=path.resolve(process.argv[2]);
const c=require(path.join(runtime,'ai/core.cjs'));
const {publicRoot}=require(path.join(runtime,'ai/strong/resource-turn-search-v1.cjs'));
const {preparePolicy}=require(path.join(runtime,'ai/strong/population-hybrid-policy.cjs'));

function handle(q) {
    if(q.op==='prepare')return preparePolicy(q);
    assert.equal(q.op,'purchase');
    const request=q.request,seat=request.player;
    const state=publicRoot({...request,featureRevision:'4.3-strategic-correction'});
    assert.equal(q.move.name,'BuyResource');
    assert(c.allLegal(state,seat).some(move=>isDeepStrictEqual(move,q.move)));
    const metadata={cardsLeft:state.cardsLeft,nextCardWeak:state.nextCardWeak};
    c.E.move(state,structuredClone(q.move),seat);Object.assign(state,metadata);
    assert.equal(state.phase,'Resources');assert.deepEqual(state.currentPlayers,[seat]);
    const revision=request.revision+1;
    return {...request,revision,requestId:'anchor-integration:'+revision,
        state:publicRoot({state,player:seat,featureRevision:'4.3-strategic-correction'})};
}
(async()=>{
    for await(const line of require('node:readline').createInterface({input:process.stdin})) {
        console.log(JSON.stringify(handle(JSON.parse(line))));
    }
})().catch(error=>{console.error(error.stack);process.exit(1);});
