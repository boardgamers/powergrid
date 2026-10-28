const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const readline=require('node:readline');
const [root,out,artifact]=process.argv.slice(2);
const design=JSON.parse(fs.readFileSync(path.join(out,'design.json'),'utf8'));
const oldEngine=require(path.join(artifact,'runtime/engine/dist/index.js'));
const oldMoves=require(path.join(artifact,'runtime/engine/dist/src/available-moves.js')).availableMoves;
const currentRoot=path.join(out,'source/engine/dist');
const newEngine=require(path.join(currentRoot,'index.js'));
const newMoves=require(path.join(currentRoot,'src/available-moves.js')).availableMoves;
const {autoPassAuctions}=require(path.join(currentRoot,'src/auction-auto-pass.js'));
const core=require(path.join(artifact,'runtime/ai/core.cjs'));
const clone=x=>JSON.parse(JSON.stringify(x));
const same=(a,b)=>JSON.stringify(a)===JSON.stringify(b);
const flat=menu=>Object.entries(menu).flatMap(([name,values])=>(values||[]).map(data=>({name,data})));
const differences=(a,b)=>a.filter(x=>!b.some(y=>same(x,y)));
const increment=(object,key)=>object[key]=(object[key]||0)+1;

async function main(){
 const detail=fs.createWriteStream(path.join(out,'differences.jsonl'),{flags:'wx'});
 const result={current_engine_commit:design.current_engine_commit,current_engine_version:design.current_engine_version,
  scope:'recorded-public-action-menu-compatibility',recorded_games:0,requests:0,old_menu_mismatches:0,
  changed_menus:0,changed_recorded_actions:0,added_actions:0,removed_actions:0,
  changes_by_reason:{},coverage:{players:{},phases:{},rules:{},steps:{},seats:{}},examples:[],synthetic_discount_checks:0,
  synthetic_auto_pass_checks:0,setup_checks:0,setup_differences:0,typecheck:false};
 for(const filename of Object.keys(design.recorded_inputs).sort()){
  result.recorded_games++;
  const lines=readline.createInterface({input:fs.createReadStream(path.join(root,filename)),crlfDelay:Infinity});
  for await(const line of lines){
   const row=JSON.parse(line),q=row.request,g=q.state,seat=q.player;
   assert.equal(g.map.name,'Germany');assert.equal(g.seed,'secret');assert.deepEqual(g.powerPlantsDeck,[]);
   const a=clone(g),b=clone(g),old=oldMoves(a,a.players[seat]),fresh=newMoves(b,b.players[seat]);
   result.requests++;
   for(const [key,value] of Object.entries({players:g.players.length,phases:g.phase,
     rules:g.options.variant+'-'+(g.options.fastBid?'sealed':'open'),steps:g.step,seats:g.players.length+':'+seat}))
    increment(result.coverage[key],value);
   if(!same(old,g.players[seat].availableMoves))result.old_menu_mismatches++;
   a.players[seat].availableMoves=old;assert.deepEqual(core.candidates(a,seat),row.arenaMoves);
   if(same(old,fresh))continue;
   const added=differences(flat(fresh),flat(old)),removed=differences(flat(old),flat(fresh));
   const expected=g.phase==='Auction'&&!g.chosenPowerPlant&&g.options.variant==='recharged'&&g.plantDiscountActive
     &&g.players[seat].money>=1&&g.players[seat].money<g.actualMarket[0].number
     &&added.length===1&&added[0].name==='ChoosePowerPlant'&&added[0].data===g.actualMarket[0].number&&removed.length===0;
   const reason=expected?'discounted_plant_nomination':'other';increment(result.changes_by_reason,reason);
   result.changed_menus++;result.added_actions+=added.length;result.removed_actions+=removed.length;
   const first=row.executedActions[0];if(!flat(fresh).some(x=>same(x,first)))result.changed_recorded_actions++;
   const record={file:filename,requestId:q.requestId,phase:g.phase,round:g.round,step:g.step,
    players:g.players.length,seat,money:g.players[seat].money,variant:g.options.variant,sealed:g.options.fastBid,
    plantDiscountActive:g.plantDiscountActive,lowestPlant:g.actualMarket[0]?.number,added,removed,reason};
   detail.write(JSON.stringify(record)+'\n');if(result.examples.length<8)result.examples.push(record);
  }
 }
 for(let n=2;n<=6;n++)for(const variant of ['original','recharged'])for(const fastBid of [false,true]){
  const options={map:'Germany',variant,fastBid,showMoney:true},seed='engine-compatibility-setup-v1-'+n+'-'+variant+'-'+fastBid;
  const a=oldEngine.setup(n,options,seed),b=newEngine.setup(n,options,seed);
  // Setup clock timestamps are operational, not economic state.
  const stable=g=>{const x=clone(g);for(const p of x.players){delete p.clockStartedAt;delete p.totalTimeUsed;}return x;};
  result.setup_checks++;if(!same(stable(a),stable(b)))result.setup_differences++;
  if(variant!=='recharged')continue;
  const seat=b.currentPlayers[0];b.round=2;b.plantDiscountActive=true;b.players[seat].money=1;
  const old=oldMoves(clone(b),clone(b.players[seat]));const fresh=newMoves(b,b.players[seat]);
  assert(!old.ChoosePowerPlant?.includes(b.actualMarket[0].number));
  assert(fresh.ChoosePowerPlant.includes(b.actualMarket[0].number));result.synthetic_discount_checks++;
  const before=clone(b);autoPassAuctions(b,0);
  assert.deepEqual(b.currentPlayers,before.currentPlayers);assert.equal(b.log.length,before.log.length);
  result.synthetic_auto_pass_checks++;
  b.players[seat].money=0;const previous=b.log.length;autoPassAuctions(b,0);
  assert(b.log.length>previous);assert(b.players[seat].skipAuction||b.players[seat].passed);
  result.synthetic_auto_pass_checks++;
 }
 await new Promise((resolve,reject)=>{detail.once('error',reject);detail.end(resolve);});
 assert.equal(result.recorded_games,33);assert.equal(result.old_menu_mismatches,0);
 result.recorded_menu_parity=result.changed_menus===0;
 result.recorded_actions_still_legal=result.changed_recorded_actions===0;
 result.interpretation='Diagnostic only: menu compatibility on saved public states, not transition/full-game parity, strength, final qualification, or support for alternate decks/revisions/new options.';
 fs.writeFileSync(path.join(out,'assessment.json'),JSON.stringify(result,null,2)+'\n',{flag:'wx'});
 console.log(JSON.stringify(result));
}
main().catch(error=>{console.error(error);process.exitCode=1;});
