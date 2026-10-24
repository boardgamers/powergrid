const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const crypto=require('node:crypto');
const {createFilter}=require('./endgame-loss-filter.cjs');
const root=path.resolve(__dirname,'../..');
const prepared=path.join(root,'ai/runs/policy-iteration-trained-8840u-prepared-v2');
const runtime=path.join(root,'ai/runs/policy-iteration-legacy-replays-v1/runtime');
const digest=p=>crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
const selection=JSON.parse(fs.readFileSync(path.join(root,'ai/runs/policy-iteration-legacy-replays-v1/selection.json'),'utf8'));
for(const [name,sha] of Object.entries(selection.runtime_hashes)) assert.equal(digest(path.join(runtime,name)),sha);
const manifest=JSON.parse(fs.readFileSync(path.join(prepared,'manifest.json'),'utf8'));
const fixtures=path.join(prepared,'fixtures.jsonl');assert.equal(digest(fixtures),manifest.fixtures_sha256);
const c=require(path.join(runtime,'ai/core.cjs'));
const engine=require(path.join(runtime,'engine/dist/src/engine.js'));
const check=createFilter(c,engine.calculateMaxCitiesPowered);
const rows=fs.readFileSync(fixtures,'utf8').trim().split('\n').map(JSON.parse);
assert.equal(rows.length,2553);
const byCount={},certificates=[];
let choices=0;
for(let i=0;i<rows.length;i++) {
    const {request,legal}=rows[i], g=request.state, seat=request.player;
    const count=g.players.length;
    const cell=(byCount[count]||={positions:0,choices:0,certified_builds:0});cell.positions++;
    const before=JSON.stringify(g);
    for(const proposal of legal) {
        cell.choices++;choices++;
        const certificate=check(g,seat,proposal);
        if(certificate) {
            assert.equal(proposal.name,'Build');
            assert(legal.some(a=>JSON.stringify(a)===JSON.stringify(certificate.replacement)));
            assert(certificate.fuelUpperBound<certificate.opponentLowerBound);
            const hidden=structuredClone(g);hidden.seed='unrelated';hidden.powerPlantsDeck=[];hidden.hiddenLog=[];
            hidden.players.forEach(p=>p.bid=0);delete hidden.powerPlantDeckAfterStep3;
            assert.deepEqual(check(hidden,seat,proposal),certificate);
            certificates.push({fixture:i,players:count,proposal,certificate});cell.certified_builds++;
        }
    }
    assert.equal(JSON.stringify(g),before);
}
assert.deepEqual(Object.fromEntries(Object.entries(byCount).map(([n,v])=>[n,v.positions])),
    {'2':349,'3':427,'4':527,'5':609,'6':641});
const output=process.argv[2];assert(output&&!fs.existsSync(output));
const result={positions:rows.length,choices,by_player_count:byCount,certificates,
    all_inputs_unchanged:true,all_replacements_legal:true,private_future_invariance:true,
    fixtures_sha256:digest(fixtures),source:selection.source,
    code_hashes:Object.fromEntries([__filename,path.join(__dirname,'endgame-loss-filter.cjs')].map(p=>[path.relative(root,p),digest(p)])),
    new_strength_games:0,candidate_selected:false,qualification_eligible:false,reserved_final_seeds_used:false,
    scope:'All existing serving fixtures and their supplied legal moves, across 2–6 players. Read-only legality and scope probe only; no performance, strength or qualification claim.'};
fs.writeFileSync(output,JSON.stringify(result,null,2)+'\n');
console.log(JSON.stringify({positions:rows.length,choices,by_player_count:byCount}));
