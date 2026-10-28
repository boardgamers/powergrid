// Predetermined counterfactual input fixtures, not game rollouts or strength data.
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const [root,out]=process.argv.slice(2);
const compiled=path.join(root,'ai/runs/current-engine-compatibility-v1/source/engine/dist');
const E=require(path.join(compiled,'index.js'));
const fresh=require(path.join(compiled,'src/available-moves.js')).availableMoves;
const old=require(path.join(root,'ai/runs/resource-turn-full-artifact-v4/runtime/engine/dist/src/available-moves.js')).availableMoves;
const base=path.join(root,'ai/runs/resource-turn-full-integration-v2');
const clone=x=>JSON.parse(JSON.stringify(x));
const flat=menu=>Object.entries(menu).flatMap(([name,values])=>(values||[]).map(data=>({name,data})));
const inputs=[];
for(let n=2;n<=6;n++)for(const sealed of [true,false]){
 const filename=path.join(base,`model-turn-${n}p-economic`,`decisions-${sealed?1:3}.jsonl`);
 const rows=fs.readFileSync(filename,'utf8').trim().split('\n').map(JSON.parse);
 const row=rows.find(r=>{const g=r.request.state,p=g.players[r.request.player];return g.phase==='Auction'
  &&g.round>1&&!g.chosenPowerPlant&&g.options.variant==='recharged'&&g.options.fastBid===sealed
  &&g.plantDiscountActive&&p.availableMoves.ChoosePowerPlant?.includes(g.actualMarket[0].number);});
 assert(row,'Missing predetermined qualifying root');
 for(const kind of ['recorded-control','discount-money-one','no-money-pass']){
  const request=clone(row.request),g=request.state,seat=request.player;
  if(kind==='discount-money-one')g.players[seat].money=1;
  if(kind==='no-money-pass')g.players[seat].money=0;
  const menu=fresh(g,g.players[seat]),oldMenu=old(g,g.players[seat]);
  g.players[seat].availableMoves=menu;
  const publicState=clone(E.stripSecret(g,seat));publicState.seed='secret';publicState.powerPlantsDeck=[];
  publicState.hiddenLog=[];delete publicState.powerPlantDeckAfterStep3;delete publicState.automation;
  if(sealed){publicState.currentBid=0;publicState.players.forEach(p=>p.bid=0);}
  request.state=publicState;request.requestId=`compatibility-${n}p-${sealed?'sealed':'open'}-${kind}`;
  const legal=flat(menu);
  if(kind==='discount-money-one'){
   assert(menu.ChoosePowerPlant.includes(g.actualMarket[0].number));
   assert(!oldMenu.ChoosePowerPlant?.includes(g.actualMarket[0].number));
  }
  if(kind==='no-money-pass')assert.deepEqual(legal,[{name:'Pass',data:true}]);
  inputs.push({kind,players:n,sealed,request,legal,currentMenu:menu,frozenMenu:oldMenu,
   source:path.relative(root,filename),sourceRequestId:row.request.requestId,
   originalDecision:kind==='recorded-control'?row.response.decision:null,
   counterfactual:kind!=='recorded-control'});
 }
}
assert.equal(inputs.length,30);
fs.writeFileSync(path.join(out,'inputs.json'),JSON.stringify(inputs)+'\n',{flag:'wx'});
console.log(JSON.stringify({cases:inputs.length,recorded_controls:10,counterfactual_cases:20}));
