// Independent full-state feature check; only corrected public features leave it.
const assert=require('node:assert/strict');
const path=require('node:path');
const {isDeepStrictEqual}=require('node:util');
const {createModelResourceTurn}=require('./resource-model-turn-v2.cjs');
const runtime=path.resolve(process.argv[2]);
const c=require(path.join(runtime,'ai/core.cjs'));
const {publicRoot}=require(path.join(runtime,'ai/strong/resource-turn-search-v1.cjs'));
const {createAnalysisScenario}=require(path.join(runtime,'engine/dist/src/analysis.js'));
const encoder=require(path.join(runtime,'ai/strong/encoders.cjs')).forRevision('4.3-strategic-correction');
const ModelTurn=createModelResourceTurn(runtime);
let modelTurn,worlds,checks,steps;

function checkedReply(reply) {
    if(!reply.done)for(const world of worlds) {
        const encoded=encoder.encode(world,modelTurn.seat),moves=encoded.moves;delete encoded.moves;
        assert.deepEqual(reply.observation,encoded,'Corrected public features differ from a complete sampled state');
        assert.deepEqual(reply.moves,moves,'Corrected legal menu differs from a complete sampled state');
        checks++;
    }
    return {...reply,privateStateFeatureChecks:checks,atomicPurchases:steps,
        publicMetadata:{cardsLeft:modelTurn.g.cardsLeft,nextCardWeak:modelTurn.g.nextCardWeak}};
}

function handle(q) {
    if(q.op==='reset') {
        assert(q.samples===8);modelTurn=new ModelTurn();checks=0;steps=0;
        const state=publicRoot({...q.request,featureRevision:'4.3-strategic-correction'});
        worlds=Array.from({length:8},(_,sample)=>createAnalysisScenario(state,{player:q.request.player,seed:q.seed+'-'+sample}));
        return checkedReply(modelTurn.reset({...q.request,featureRevision:'4.3-strategic-correction'}));
    }
    assert.equal(q.op,'step');assert(!modelTurn.done);
    const move=modelTurn.moves[q.index];assert(move);
    for(const world of worlds) {
        assert(c.allLegal(world,modelTurn.seat).some(m=>isDeepStrictEqual(m,move)));
        if(move.name==='BuyResource')c.E.move(world,structuredClone(move),modelTurn.seat);
        else assert.deepEqual(move,{name:'Pass',data:true});
    }
    if(move.name==='BuyResource')steps++;
    return checkedReply(modelTurn.step(q.index));
}

(async()=>{
    for await(const line of require('node:readline').createInterface({input:process.stdin}))console.log(JSON.stringify(handle(JSON.parse(line))));
})().catch(error=>{console.error(error.stack);process.exit(1);});
