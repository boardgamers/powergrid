// Corrected public model baseline; unchanged candidate construction/continuations.
// Run only from the separately pinned artifact's policy directory.
const assert=require('node:assert/strict');
const path=require('node:path');
const {createModelResourceTurn}=require('./resource-model-turn-v2.cjs');
const {createResourceTurnAnchor}=require('./resource-turn-anchor-v2.cjs');
const runtime=path.resolve(__dirname,'../runtime');
const {prepareResource,ResourceContinuations}=require(path.join(runtime,'ai/strong/resource-turn-search-v1.cjs'));
const ModelTurn=createModelResourceTurn(runtime);
const turn=new ModelTurn(),batch=new ResourceContinuations(),anchor=createResourceTurnAnchor(runtime);
(async()=>{
    for await(const line of require('node:readline').createInterface({input:process.stdin})) {
        const q=JSON.parse(line);
        assert(['baseline-reset','baseline-step','prepare','anchor-prepare','reset','step'].includes(q.op));
        const result=q.op==='baseline-reset'?turn.reset(q):q.op==='baseline-step'?turn.step(q.index):
            q.op==='anchor-prepare'?anchor.prepare(q):q.op==='prepare'?prepareResource(q):q.op==='reset'?batch.reset(q):batch.step(q.actions);
        console.log(JSON.stringify(result));
    }
})().catch(error=>{console.error(error.stack);process.exit(1);});
