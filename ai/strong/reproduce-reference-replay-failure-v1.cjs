// Reproduce one confirmed failed pilot world; never retry the full pilot.
const assert=require('node:assert/strict'), fs=require('node:fs'),path=require('node:path');
const protocol=JSON.parse(fs.readFileSync(process.env.PG_REFERENCE_ROOTS,'utf8'));
process.env.PG_REFERENCE_RUNTIME=protocol.runtime;
const root=protocol.roots[6], q=root.request;
const engine=require(path.join(protocol.runtime,'engine/dist/src/engine.js'));
const original=engine.reconstructState;
let capture;
engine.reconstructState=function(state,to,forcePublicDraws) {
    try {return original(state,to,forcePublicDraws);}
    catch(error) {
        capture={state:structuredClone(state),to,forcePublicDraws,error:error.stack,
            allBalancesPublic:state.players.every(p=>p.money>=0)};
        throw error;
    }
};
const {ReferenceContinuations}=require('./reference-opponent-continuations-v1.cjs');
const batch=new ReferenceContinuations();
try {
    batch.reset({...q,featureRevision:protocol.feature_revision,mode:'reference_opponent_v1',
        referenceOpponent:'search_geo',neuralBeliefs:{},belief:'policy',endgameFilter:true,
        samples:64,n:1,offset:0,options:root.options,seed:root.original_decision.search.seed,maxSteps:2400});
    throw Error('Expected the confirmed failure during the first world initialization');
} catch(error) {
    assert(capture,'Failure did not originate in replay');
    assert(capture.error.includes('not allowed to run the command ChoosePowerPlant'));
    assert(capture.allBalancesPublic);
    fs.writeFileSync(process.env.PG_REFERENCE_FAILURE_OUTPUT,JSON.stringify(capture,null,2)+'\n',{flag:'wx'});
    console.log(JSON.stringify({reproduced:true,root:6,sample:0,action:root.options[0],
        allBalancesPublic:true,round:capture.state.round,phase:capture.state.phase,
        logEntries:capture.state.log.length,originalEngineModified:false}));
}
