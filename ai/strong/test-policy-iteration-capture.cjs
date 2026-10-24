const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const encoders=require('./encoders.cjs');
const revisions=['4.2-discard-correction','4.3-strategic-correction'];
const plain=Object.fromEntries(revisions.map(rev=>[rev,encoders.forRevision(rev)]));
const {decision}=require('./capture-policy-iteration.cjs');
const file=path.join(__dirname,'fixtures/multiplayer-serving-v1.jsonl');
assert.equal(crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex'),'f1c97bf909e38e5df372a89d169d80f5a6f24c00dccefacd60b10b767f1fcfa0');
const counts={};let positions=0;
for(const line of fs.readFileSync(file,'utf8').trim().split('\n')){
    const {state,player}=JSON.parse(line).request;
    for(const rev of revisions){
        const before=JSON.stringify(state),a=plain[rev].encode(state,player),b=encoders.forRevision(rev).encode(state,player);
        const root=b.strategicRoot;delete b.strategicRoot;assert.deepEqual(a,b);assert.equal(JSON.stringify(state),before);
        const kind=decision(a.moves);
        if(kind){
            assert.equal(root.decision,kind);assert.deepEqual(plain[rev].encode(root.request.state,player),a);
            assert.deepEqual(root.request.state.players.map(p=>p.money),state.players.map(p=>p.money));
            assert(root.request.state.players.every(p=>p.lastMove===null));
            const other=structuredClone(state);other.seed='changed';other.powerPlantsDeck=[{number:999}];other.hiddenLog=[{secret:true}];
            other.powerPlantDeckAfterStep3=[{number:888}];other.automation={plans:{0:{secret:true}}};
            other.players.forEach(p=>{p.lastMove={name:'Bid',data:888};if(other.options.fastBid)p.bid=777;});
            if(other.options.fastBid)other.currentBid=777;
            assert.deepEqual(encoders.forRevision(rev).encode(other,player).strategicRoot,root);
            const key=rev+'/'+state.players.length+'p/'+kind;counts[key]=(counts[key]||0)+1;
        }else assert.equal(root,undefined);
    }
    positions++;
}
assert.equal(positions,2553);
for(const rev of revisions)for(const n of [2,3,4,5,6])assert(Object.keys(counts).some(k=>k.startsWith(rev+'/'+n+'p/')));
const original=fs.readFileSync(path.join(__dirname,'bridge.cjs'),'utf8');
const changed=fs.readFileSync(path.join(__dirname,'policy-iteration-bridge.cjs'),'utf8');
assert.equal(changed,original.replace('        episode: e.id,\n        roles: e.roles,','        actor: seat,\n        episode: e.id,\n        roles: e.roles,'));
console.log(JSON.stringify({passed:true,positions,revisions,checks:positions*2,counts,bridge_change:'actor metadata only',qualification_eligible:false}));
