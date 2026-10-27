// Saved-position engine checks only: no inference, sampled worlds or full games.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const {createResourceTurnTransaction} = require('./resource-turn-transaction-v1.cjs');
const root = path.resolve(__dirname,'../..');
const prior = path.join(root,'ai/runs/resource-turn-search-v1');
const runtime = path.join(prior,'runtime');
const output = path.resolve(process.argv[2]);
const read = p => JSON.parse(fs.readFileSync(p,'utf8'));
const sha = p => crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
const clone = x => structuredClone(x);
const inputHashes = {};
function pinned(file, expected) {
    assert.equal(sha(file),expected,file);inputHashes[path.relative(root,file)] = expected;
}
pinned(path.join(prior,'preparation.json'),'e7fcea6fd4b74a4955f3e69a98a951c2d26c8a9e68fc3167e03ddd3b810ff803');
const prep = read(path.join(prior,'preparation.json'));
for (const [name,hash] of Object.entries({...prep.runtime_hashes,...prep.new_files}))
    assert.equal(sha(path.join(runtime,name)),hash,name);
const fixturesPath = path.join(runtime,'ai/strong/fixtures/multiplayer-serving-v1.jsonl');
pinned(fixturesPath,'f1c97bf909e38e5df372a89d169d80f5a6f24c00dccefacd60b10b767f1fcfa0');
pinned(path.join(prior,'selection.json'),'3116faa72800379c45d4ebba900b22d7c40cc71a4ef5cccb8dac9e3d1d9a8d4e');
pinned(path.join(prior,'trained/baselines.jsonl'),'b72519cd01b39fd59e7bd18e7b653ed28363c354e8d638a332df62b907657e10');
pinned(path.join(prior,'trained/search.jsonl'),'53b5433aad8d4360f5244161a24094a23c04a8c31930181c032b598804ac46e8');
const fixtures = fs.readFileSync(fixturesPath,'utf8').trim().split('\n').map(JSON.parse);
const baselines = fs.readFileSync(path.join(prior,'trained/baselines.jsonl'),'utf8').trim().split('\n').map(JSON.parse);
const searches = fs.readFileSync(path.join(prior,'trained/search.jsonl'),'utf8').trim().split('\n').map(JSON.parse);
const selection = read(path.join(prior,'selection.json'));
const transaction = createResourceTurnTransaction(runtime);
const receipts = [],cells = {},report = {passed:false,baseline_positions:0,baseline_actions:0,
    searched_plans:0,rejected_controls:0,hidden_controls:0,new_inference:0,new_games:0,
    new_hf_jobs:0,qualification_eligible:false,reserved_final_seeds_used:false};

function checked(request,actions,label) {
    const before = JSON.stringify(request),beforeActions = JSON.stringify(actions);
    const envelope = transaction.build(request,actions);
    assert.deepEqual(transaction.verify(request,envelope),envelope);
    assert.equal(JSON.stringify(request),before);assert.equal(JSON.stringify(actions),beforeActions);
    assert.deepEqual(envelope.actions,actions);
    receipts.push({label,envelope});return envelope;
}
function rejects(request,envelope) {
    const before = JSON.stringify(request);
    assert.throws(() => transaction.verify(request,envelope));
    assert.equal(JSON.stringify(request),before);report.rejected_controls++;
}
for (const row of baselines) {
    const request = fixtures[row.fixture].request;
    const envelope = checked(request,row.actions,'fixture-'+row.fixture);
    const key = [request.state.players.length,request.state.options.variant,request.state.options.fastBid].join('/');
    cells[key]=(cells[key]||0)+1;report.baseline_positions++;report.baseline_actions+=row.actions.length;
    // Bind both the acting player's resources and all opponents' permitted public money.
    for (const mutate of [q=>q.state.round++,q=>q.state.players[q.player].money++,
        q=>q.state.players[(q.player+1)%q.state.players.length].money++,
        q=>q.state.currentPlayers=[],q=>q.state.options.showMoney=false]) {
        const q = clone(request);mutate(q);rejects(q,envelope);
    }
    for (const mutate of [e=>e.actions=[],e=>e.actions.push({name:'Pass',data:true}),
        e=>e.cost++,e=>e.rootSha256='0'.repeat(64),e=>e.player=(e.player+1)%request.state.players.length,
        e=>e.actions.unshift({name:'BuyResource',data:{resource:'invalid'}}),
        e=>e.actions.unshift({name:'Pass',data:true}),e=>e.qualification_eligible=true]) {
        const e = clone(envelope);mutate(e);rejects(request,e);
    }
    if (row.actions.length>1) {
        const e=clone(envelope);e.actions.pop();rejects(request,e);
    }
    const hidden = clone(request);
    hidden.state.seed='hidden-poison';hidden.state.powerPlantsDeck=[{number:9999}];
    hidden.state.powerPlantDeckAfterStep3=[{number:9998}];hidden.state.hiddenLog=[{private:true}];
    hidden.state.players.forEach(p=>{p.lastMove={name:'Bid',data:9997};if(hidden.state.options.fastBid)p.bid=9996;});
    if(hidden.state.options.fastBid)hidden.state.currentBid=9995;
    assert.deepEqual(transaction.verify(hidden,envelope),envelope);report.hidden_controls++;
}
for (const row of searches) {
    const request = selection.selected[row.label].request,plan=row.result;
    const envelope=checked(request,plan.actions,row.label),bundle=plan.bundles[plan.selected];
    assert.deepEqual(envelope.actions,bundle.actions);assert.deepEqual(envelope.counts,bundle.counts);
    assert.equal(envelope.cost,bundle.cost);
    for (const receipt of plan.receipts.filter(r=>r.actionIndex===plan.selected))
        assert.deepEqual(envelope.afterPurchases,receipt.resourceTurn.afterPurchases);
    report.searched_plans++;
}
assert.equal(report.baseline_positions,755);assert.equal(report.baseline_actions,2251);
assert.equal(Object.keys(cells).length,20);assert.equal(report.searched_plans,23);
report.passed=true;report.cells=cells;report.input_hashes=inputHashes;
report.checker_sha256=sha(__filename);
report.contract_sha256=sha(path.join(__dirname,'resource-turn-transaction-v1.cjs'));
report.scope='Transaction primitive checked on saved positions only. No model-quality claim, serving integration, stateful plan cache, new continuations or new full games. All executed resource actions match the recorded whole-turn plans.';
fs.mkdirSync(output,{recursive:false});
fs.writeFileSync(path.join(output,'receipts.jsonl'),receipts.map(r=>JSON.stringify(r)).join('\n')+'\n',{flag:'wx'});
report.receipts_sha256=sha(path.join(output,'receipts.jsonl'));
fs.writeFileSync(path.join(output,'assessment.json'),JSON.stringify(report,null,2)+'\n',{flag:'wx'});
console.log(JSON.stringify(report));
