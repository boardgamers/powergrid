// Predetermined public-state pairs, not fresh games or policy evaluation.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const assert=require('node:assert/strict'),{isDeepStrictEqual:same}=require('node:util');
const root=path.resolve(__dirname,'../..');
const out=path.join(root,'ai/runs/auction-discount-encoding-v1');
const result=path.join(root,'ai/strong/auction-discount-encoding-results-v1.json');
const read=p=>JSON.parse(fs.readFileSync(p,'utf8'));
const hash=p=>crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
const objectHash=x=>crypto.createHash('sha256').update(JSON.stringify(x)).digest('hex');
const clone=x=>JSON.parse(JSON.stringify(x));
const save=(p,x)=>fs.writeFileSync(p,JSON.stringify(x,null,2)+'\n',{flag:'wx'});
assert(!fs.existsSync(out)&&!fs.existsSync(result),'Inspect prior diagnostic before retrying');
const artifact=path.join(root,'ai/runs/resource-turn-full-artifact-v4');
const manifest=path.join(artifact,'manifest.json');
assert.equal(hash(manifest),'ce05c01a314305f5f0b3f7b55f6a8e13355ee0edb9bf5cae2c9688efd55cf795');
for(const [name,sha] of Object.entries(read(manifest)))assert.equal(hash(path.join(artifact,name)),sha,name);
const current=path.join(root,'ai/runs/current-engine-compatibility-v1');
const engineProof=read(path.join(root,'ai/strong/current-engine-compatibility-evidence-v1.json'));
assert.equal(hash(path.join(current,'build.json')),engineProof.build_sha256);
for(const [name,sha] of Object.entries(read(path.join(current,'build.json')).compiled_files))
 assert.equal(hash(path.join(current,'source/engine',name)),sha,name);
const fixture=path.join(root,'ai/runs/current-engine-policy-v1/inputs.json');
const fixtureProof=read(path.join(root,'ai/strong/current-engine-policy-evidence-v1.json'));
assert.equal(hash(fixture),fixtureProof.inputs_sha256);
const controls=read(fixture).filter(x=>x.kind==='recorded-control');assert.equal(controls.length,10);
const engine=require(path.join(current,'source/engine/dist/index.js'));
const {minimumPlantBid}=require(path.join(current,'source/engine/dist/src/auction-pricing.js'));
const encoder=require(path.join(artifact,'runtime/ai/strong/features-v4_3.cjs'));
const economics=require(path.join(artifact,'runtime/ai/strong/economics.cjs'));
fs.mkdirSync(out);
const design={created_at:new Date().toISOString(),selection:'The same ten recorded-control nomination roots used by current-engine-policy-v1: 2–6 players, Recharged open/sealed, first eligible round>1 from fixed episodes 1 and 3.',
 counterfactual:'Change only plantDiscountActive to false; recompute actor legal menu. Keep all money, portfolios, history and other game fields unchanged. Not a claim that the changed history is naturally reachable.',
 current_engine_commit:engineProof.current_engine_commit,engine_archive:engineProof.archive,
 source_fixture_sha256:hash(fixture),fixture_archive:fixtureProof.archive,
 artifact_manifest_sha256:hash(manifest),checker_sha256:hash(__filename),
 scope:'auction-discount-input-identifiability',new_inference:0,new_search_rollouts:0,
 new_hf_jobs:0,new_full_game_trajectories:0,qualification_eligible:false,reserved_final_seeds_used:false};
save(path.join(out,'design.json'),design);
const records=[];
for(const control of controls){
 const a=clone(control.request.state),b=clone(a),seat=control.request.player;
 assert(a.options.variant==='recharged'&&a.plantDiscountActive&&!a.chosenPowerPlant);
 assert(a.players[seat].money>=a.actualMarket[0].number);
 b.plantDiscountActive=false;
 a.players[seat].availableMoves=engine.availableMoves(a,a.players[seat]);
 b.players[seat].availableMoves=engine.availableMoves(b,b.players[seat]);
 assert.deepEqual(a.players[seat].availableMoves,b.players[seat].availableMoves);
 const x=encoder.encode(a,seat),y=encoder.encode(b,seat);
 assert.equal(x.state.length,1217);assert(x.actions.every(row=>row.length===101));
 assert.deepEqual(x.moves,y.moves);
 const plant=a.actualMarket[0],discounted=minimumPlantBid(a,plant),ordinary=minimumPlantBid(b,plant);
 assert.equal(discounted,1);assert.equal(ordinary,plant.number);assert(ordinary>discounted);
 const index=x.moves.findIndex(m=>m.name==='ChoosePowerPlant'&&m.data===plant.number);assert(index>=0);
 const priors=[economics.scores(a,seat,x.moves),economics.scores(b,seat,y.moves)];
 records.push({requestId:control.request.requestId,sourceRequestId:control.sourceRequestId,
  players:a.players.length,sealed:a.options.fastBid,round:a.round,step:a.step,actor_money:a.players[seat].money,
  plant:plant.number,opening_bid_discounted:discounted,opening_bid_ordinary:ordinary,
  same_legal_menu:true,same_state_features:same(x.state,y.state),same_action_features:same(x.actions,y.actions),
  same_prior:same(x.prior,y.prior),same_teacher:x.teacher===y.teacher,
  same_complete_encoding:same(x,y),same_raw_economic_scores:same(priors[0],priors[1]),
  discounted_nomination_index:index,nomination_prior_with_discount:priors[0][index],nomination_prior_without_discount:priors[1][index],
  encoding_with_discount:x,encoding_without_discount:y,
  state_with_discount_sha256:objectHash(a),state_without_discount_sha256:objectHash(b)});
}
save(path.join(out,'pairs.json'),records);
const report={completed:true,fixtures:10,encoder_calls:20,
 aliased_complete_encodings:records.filter(r=>r.same_complete_encoding).length,
 identical_state_vectors:records.filter(r=>r.same_state_features).length,
 identical_action_matrices:records.filter(r=>r.same_action_features).length,
 identical_raw_priors:records.filter(r=>r.same_raw_economic_scores).length,
 opening_bid_changed:records.filter(r=>r.opening_bid_discounted!==r.opening_bid_ordinary).length,
 cases:records.map(({encoding_with_discount,encoding_without_discount,...rest})=>rest),
 design_sha256:hash(path.join(out,'design.json')),pairs_sha256:hash(path.join(out,'pairs.json')),
 new_inference:0,new_search_rollouts:0,new_hf_jobs:0,new_full_game_trajectories:0,new_gradients:0,
 qualification_eligible:false,reserved_final_seeds_used:false,
 interpretation:'Input-identifiability diagnostic on synthetic paired public states. Identical encodings cannot make a deterministic neural policy directly condition on the changed discount. Does not prove naturally reachable matched states, game regret, causation of weak Recharged results, or that any alternative nomination is better.'};
save(path.join(out,'assessment.json'),report);save(result,report);
console.log(JSON.stringify({fixtures:report.fixtures,encoder_calls:report.encoder_calls,
 aliased_complete_encodings:report.aliased_complete_encodings,opening_bid_changed:report.opening_bid_changed}));
