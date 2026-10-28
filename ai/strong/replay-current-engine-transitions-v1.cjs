// Fixed historical decisions through both engines. No model or search calls.
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const {isDeepStrictEqual:same}=require('node:util');
const [root,out]=process.argv.slice(2);
const read=p=>JSON.parse(fs.readFileSync(p,'utf8'));
const clone=x=>JSON.parse(JSON.stringify(x));
const design=read(path.join(out,'design.json'));
const runtime=path.join(root,'ai/runs/resource-turn-full-artifact-v4/runtime');
const c=require(path.join(runtime,'ai/core.cjs'));
const eco=require(path.join(runtime,'ai/strong/economics.cjs'));
const beliefs=require(path.join(runtime,'ai/strong/sealed-policy-beliefs.cjs'));
const fresh=require(path.join(root,'ai/runs/current-engine-compatibility-v1/source/engine/dist/index.js'));
const write=(name,x)=>fs.writeFileSync(path.join(out,name),JSON.stringify(x,null,2)+'\n',{flag:'wx'});
const increment=(obj,key)=>obj[key]=(obj[key]||0)+1;
const flat=menu=>Object.entries(menu||{}).flatMap(([name,values])=>(values||[]).map(data=>({name,data})));
function publicStable(g){
 const x=clone(g);
 const unstamp=move=>{if(move){delete move.time;delete move.serverTime;}};
 for(const p of x.players){delete p.clockStartedAt;delete p.totalTimeUsed;unstamp(p.lastMove);}
 for(const item of [...x.log,...x.hiddenLog])if(item.type==='move')unstamp(item.move);
 return x;
}
function economic(g){
 const {log,hiddenLog,poweringChoices,pendingMessages,...rest}=g;
 return clone({...rest,players:g.players.map(p=>{
  const {clockStartedAt,totalTimeUsed,availableMoves,...other}=p;return other;
 })});
}
function semanticLogs(log){return clone(log.map(row=>{
 if(row.type==='move')return {type:row.type,player:row.player,move:{name:row.move.name,data:row.move.data}};
 if(row.type==='event')return {type:row.type,event:row.event};
 return row;
}));}
function diffKeys(a,b){return [...new Set([...Object.keys(a),...Object.keys(b)])].filter(k=>!same(a[k],b[k]));}
const report={passed:false,scope:'fixed-historical-transition-replay',recorded_games:0,
 original_requests_exact:0,learner_moves:0,opponent_moves:0,transitions:0,
 changed_economic_transitions:0,changed_legal_menus:0,newly_affordable_nominations:0,
 current_action_rejections:0,changed_log_transitions:0,changed_hidden_log_transitions:0,terminal_economies_exact:0,
 coverage:{players:{},rules:{},phases:{},steps:{},moves:{},seats:{}},games:[],
 new_inference:0,new_search_rollouts:0,new_hf_jobs:0,new_full_game_trajectories:0,
 qualification_eligible:false,reserved_final_seeds_used:false};
const details=fs.openSync(path.join(out,'differences.jsonl'),'wx');
let active=null;
function detail(x){fs.writeSync(details,JSON.stringify({...active,...x})+'\n');}
try{
 for(const item of design.games){
  const rows=fs.readFileSync(path.join(root,item.decisions),'utf8').trim().split('\n').map(JSON.parse);
  const terminal=read(path.join(root,item.record)).terminal;
  const n=terminal.playerCount,seat=terminal.seat;
  assert(['economic','legacy'].includes(item.opponent));
  const options={map:'Germany',variant:terminal.variant,fastBid:terminal.sealed,showMoney:true};
  assert(!terminal.gameSeed.includes('final')&&!terminal.gameSeed.includes('reserved'));
  const old=c.E.setup(n,options,terminal.gameSeed),next=fresh.setup(n,options,terminal.gameSeed);
  const rng=c.seedrandom(terminal.gameSeed+'-bot');
  active={case:item.decisions,players:n,seat};
  assert.deepEqual(economic(old),economic(next),'Setup economic mismatch');
  let requests=0,steps=0,learnerMoves=0,opponentMoves=0;const policyMoves={};
  function apply(move,actor,alreadyApplied=false,before){
   const where=before||{phase:old.phase,step:old.step,round:old.round};
   const currentMenu=next.players[actor].availableMoves;
   assert.equal(next.currentPlayers[0],actor,'Current engine actor changed');
   assert(Object.keys(move).every(k=>['name','data','time','serverTime','usedPlantDiscount','fromSupply'].includes(k)),
    'Unexpected historical move field: '+Object.keys(move).join(','));
   const input=Object.fromEntries(Object.entries(move).filter(([k])=>['name','data','time','serverTime'].includes(k)));
   const legal=flat(currentMenu).some(x=>same(x,{name:move.name,data:move.data}));
   if(!legal){report.current_action_rejections++;detail({kind:'current-action-rejection',steps,where,actor,move,currentMenu});throw Error('Recorded action rejected by current engine');}
   const oldLog=before?.logLength??old.log.length,newLog=next.log.length;
   if(!alreadyApplied)c.E.move(old,clone(input),actor);
   fresh.move(next,clone(input),actor);
   report.transitions++;steps++;
   for(const [key,value] of Object.entries({players:n,rules:terminal.variant+'-'+(terminal.sealed?'sealed':'open'),
    phases:where.phase,steps:where.step,moves:move.name,seats:n+':'+actor}))increment(report.coverage[key],value);
   const a=economic(old),b=economic(next);
   if(!same(a,b)){report.changed_economic_transitions++;detail({kind:'economic-state',steps,where,actor,move,keys:diffKeys(a,b),old:a,current:b});throw Error('Economic transition mismatch');}
   // Menu differences are recorded independently rather than removed from the result.
   for(let p=0;p<n;p++){
    const left=old.players[p].availableMoves,right=next.players[p].availableMoves;
    if(same(clone(left),clone(right)))continue;
    const added=flat(right).filter(x=>!flat(left).some(y=>same(x,y)));
    const removed=flat(left).filter(x=>!flat(right).some(y=>same(x,y)));
    const expected=next.phase==='Auction'&&!next.chosenPowerPlant&&next.options.variant==='recharged'
     &&next.plantDiscountActive&&added.length===1&&removed.length===0
     &&added[0].name==='ChoosePowerPlant'&&added[0].data===next.actualMarket[0]?.number
     &&next.players[p].money>=1&&next.players[p].money<next.actualMarket[0].number;
    report.changed_legal_menus++;if(expected)report.newly_affordable_nominations++;
    detail({kind:'menu',steps,actor:p,expected_discount_change:expected,added,removed});
    assert(expected,'Unexpected current-engine legal menu difference');
   }
   const la=semanticLogs(old.log.slice(oldLog));
   const lb=semanticLogs(next.log.slice(newLog));
   if(!same(la,lb)){report.changed_log_transitions++;detail({kind:'log',steps,where,actor,move,old:la,current:lb});}
   if(!same(semanticLogs(old.hiddenLog),semanticLogs(next.hiddenLog))){report.changed_hidden_log_transitions++;throw Error('Sealed bid log mismatch');}
  }
  function advance(){
   while(!c.E.ended(old)&&old.currentPlayers[0]!==seat){
    assert(steps<1600);const p=old.currentPlayers[0];
    if(item.opponent==='legacy'){
     const before={phase:old.phase,step:old.step,round:old.round,logLength:old.log.length};
     const random=Math.random;Math.random=rng;
     try{c.E.moveAI(old,p);}finally{Math.random=random;}
     apply(clone(old.players[p].lastMove),p,true,before);
    }else apply(eco.choose(old,p,rng,item.opponent).action,p);
    opponentMoves++;report.opponent_moves++;
   }
  }
  advance();
  for(const row of rows){
   assert(!c.E.ended(old));assert.equal(old.currentPlayers[0],seat);
   assert.equal(steps,row.request.revision);
   assert.deepEqual(publicStable(beliefs.publicState(old,seat)),publicStable(row.request.state),'Historical public request mismatch');
   assert.deepEqual(c.candidates(old,seat),row.arenaMoves,'Historical menu mismatch');
   report.original_requests_exact++;requests++;
   for(const move of row.executedActions){
    assert.equal(old.currentPlayers[0],seat);apply(move,seat);
    increment(policyMoves,move.name);learnerMoves++;report.learner_moves++;
   }
   advance();
  }
  const summary=g=>({round:g.round,players:g.players.map(p=>({cities:p.cities.length,powered:p.citiesPowered,
   money:p.money,capacity:c.capacity(p),plants:p.powerPlants.map(x=>x.number)}))});
  assert(c.E.ended(old)&&fresh.ended(next));
  assert.equal(steps,terminal.steps);assert.deepEqual(policyMoves,terminal.policyMoves);
  assert.deepEqual(c.outcome(old),terminal.value);assert.deepEqual(summary(old),terminal.final);
  assert.deepEqual(summary(next),terminal.final);assert.deepEqual(c.outcome(next),terminal.value);
  report.terminal_economies_exact++;report.recorded_games++;
  const game={...active,requests,steps,learner_moves:learnerMoves,opponent_moves:opponentMoves,
   terminal_exact:true,final:summary(next)};
  report.games.push(game);console.log(JSON.stringify({completed_games:report.recorded_games,transitions:report.transitions}));
 }
 assert.equal(report.recorded_games,33);assert.equal(report.original_requests_exact,3443);
 assert.equal(report.learner_moves,4720);assert.equal(report.changed_economic_transitions,0);
 report.passed=true;
 report.interpretation='Fixed-action economic transition parity on 33 recorded games. New UI/revision metadata and clocks are excluded explicitly; menu/log differences are reported. Does not test automatic wrapper moves, edited choices, alternate decks, new options, fresh-policy strength, or current-engine search migration.';
 write('assessment.json',report);
}catch(error){write('failure.json',{error:error.stack,active,report});console.error(error.stack);process.exitCode=1;}
finally{fs.closeSync(details);}
