// Experimental heterogeneous opponent continuations. Historical workers unchanged.
const assert=require('node:assert/strict');
const {HybridContinuations,prepare,REVISIONS}=require('./hybrid-continuations.cjs');
const {createAnalysisScenario}=require('../../engine/dist/src/analysis.js');
const beliefs=require('./sealed-policy-beliefs.cjs');
const encoders=require('./encoders.cjs');
const search=require('./search.cjs');
const eco=require('./economics.cjs');
const c=require('../core.cjs');
const CONTROL_MODES=['neural','neural_economic'];
const NEW_MODES=['neural_legacy','neural_rush','neural_population'];
const POPULATION=['neural','economic','legacy','rush'];

function rolesFor(mode,seed,sample,count,focal) {
    assert([...CONTROL_MODES,...NEW_MODES].includes(mode));
    assert(Number.isInteger(sample)&&sample>=0&&Number.isInteger(count)&&count>=2&&count<=6);
    assert(Number.isInteger(focal)&&focal>=0&&focal<count);
    return Array.from({length:count},(_,seat)=>{
        if(seat===focal||mode==='neural') return 'neural';
        if(mode==='neural_economic') return 'economic';
        if(mode==='neural_legacy') return 'legacy';
        if(mode==='neural_rush') return 'rush';
        // Each opponent spans all four roles in every four consecutive worlds.
        // Independent public-seed offsets allow heterogeneous tables. Roles and
        // worlds are shared across candidate actions and worker partitions.
        const offset=Math.floor(c.seedrandom(seed+'-opponent-role-'+seat)()*POPULATION.length);
        return POPULATION[(sample+offset)%POPULATION.length];
    });
}

function legacyAction(state,seat,rng) {
    const copy=structuredClone(state), previous=Math.random;
    try {Math.random=rng;c.E.moveAI(copy,seat);}
    finally {Math.random=previous;}
    const action=copy.players[seat].lastMove;
    return {name:action.name,data:structuredClone(action.data)};
}

function applyPriorBids(g,earlier,roles,neural,seed) {
    return earlier.map(p=>{
        const role=roles[p.actor], rng=c.seedrandom(seed+':committed-bid:'+p.actor);
        const action=role==='neural'?neural[p.actor]:role==='legacy'?legacyAction(p.state,p.actor,rng):
            eco.choose(p.state,p.actor,rng,role).action;
        assert(action&&['Bid','Pass'].includes(action.name));
        // A legacy bid may be a legal integer omitted from the neural shortlist.
        assert(c.allLegal(p.state,p.actor).some(a=>JSON.stringify(a)===JSON.stringify(action)),
            'Illegal inferred public-policy bid');
        g.players[p.actor].bid=action.name==='Pass'?0:action.data;
        return {actor:p.actor,role,action:structuredClone(action)};
    });
}

class PopulationHybridContinuations extends HybridContinuations {
    reset(q) {
        if(CONTROL_MODES.includes(q.mode)) return super.reset(q);
        assert(NEW_MODES.includes(q.mode),'Unknown population continuation mode');
        assert.equal(q.belief,'policy');assert(REVISIONS.includes(q.featureRevision));
        assert(Number.isInteger(q.samples)&&q.samples>0&&q.samples<=64);
        assert(Number.isInteger(q.maxSteps)&&q.maxSteps>0&&q.maxSteps<=2400);
        assert(typeof q.seed==='string'&&q.seed.length>0);
        const state=beliefs.publicState(q.state,q.player);
        const actions=c.candidates(state,q.player);
        const options=q.options||search.shortlist(state,q.player,6,true);
        assert(options.length&&new Set(options).size===options.length);
        assert(options.every(i=>Number.isInteger(i)&&i>=0&&i<actions.length));
        const offset=q.offset||0;
        assert(Number.isInteger(offset)&&offset>=0&&Number.isInteger(q.n)&&q.n>0);
        assert(offset+q.n<=q.samples*options.length);
        const earlier=beliefs.prompts(state,q.player),neural=q.neuralBeliefs||{};
        assert.deepEqual(Object.keys(neural).sort(),q.mode==='neural_population'?
            earlier.map(p=>String(p.actor)).sort():[]);
        this.mode=q.mode;
        this.hybridEncoder=this.encoder=encoders.forRevision(q.featureRevision);
        this.envs=Array.from({length:q.n},(_,i)=>{
            const index=i+offset,sample=Math.floor(index/options.length);
            const actionIndex=options[index%options.length],seed=q.seed+'-'+sample;
            const roles=rolesFor(q.mode,q.seed,sample,state.players.length,q.player);
            const g=createAnalysisScenario(state,{player:q.player,seed});
            const committed=applyPriorBids(g,earlier,roles,neural,seed);
            c.E.move(g,structuredClone(actions[actionIndex]),q.player);
            return {g,sample,actionIndex,steps:0,maxSteps:q.maxSteps,player:q.player,
                continuation:'neural',reported:false,rng:c.seedrandom(q.seed+'-rollout-'+sample),roles,
                policyDecisions:{neural:0,economic:0,legacy:0,rush:0,forced:0},
                searchStats:{decisions:0,evaluations:0,truncated:0},
                initialBelief:{kind:'policy_population_v1',committed}};
        });
        return this.reply();
    }

    advance(e) {
        if(CONTROL_MODES.includes(this.mode)) return super.advance(e);
        while(!c.E.ended(e.g)&&e.steps<e.maxSteps) {
            const seat=e.g.currentPlayers[0],role=e.roles[seat],legal=c.candidates(e.g,seat);
            if(role==='neural'&&legal.length>1) return;
            if(role==='legacy') {
                const previous=Math.random;
                try {Math.random=e.rng;c.E.moveAI(e.g,seat);}
                finally {Math.random=previous;}
                e.policyDecisions.legacy++;
            } else {
                assert(['neural','economic','rush'].includes(role));
                const action=role==='neural'?legal[0]:eco.choose(e.g,seat,e.rng,role).action;
                c.E.move(e.g,action,seat);
                e.policyDecisions[role==='neural'?'forced':role]++;
            }
            e.steps++;
        }
    }
}

module.exports={PopulationHybridContinuations,prepare,rolesFor,applyPriorBids,
    CONTROL_MODES,NEW_MODES,POPULATION,REVISIONS};
if(require.main===module) {
    const batch=new PopulationHybridContinuations();
    (async()=>{
        for await(const line of require('node:readline').createInterface({input:process.stdin})) {
            try {
                const q=JSON.parse(line);assert(['prepare','reset','step'].includes(q.op));
                console.log(JSON.stringify(q.op==='prepare'?prepare(q):q.op==='reset'?batch.reset(q):batch.step(q.actions)));
            } catch(error) {console.error(error.stack);process.exit(1);}
        }
    })();
}
