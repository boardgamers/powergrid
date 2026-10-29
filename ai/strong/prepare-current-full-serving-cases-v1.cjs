// Project original fixtures with the frozen engine, preserving insertion order.
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const crypto=require('node:crypto'),readline=require('node:readline');
const root=path.resolve(__dirname,'../..');
const artifact=path.join(root,'ai/runs/current-auction-grid-prepared-v1/source/artifact');
const sha=x=>crypto.createHash('sha256').update(x).digest('hex');
const fixture=path.join(root,'ai/strong/fixtures/multiplayer-serving-v1.jsonl');
const proofFile=path.join(root,'ai/runs/current-engine-serving-fixture-audit-v1/cases.jsonl');
const report=JSON.parse(fs.readFileSync(path.join(root,'ai/strong/current-engine-serving-fixture-audit-v1.json')));
async function main(){
    assert(process.argv.length===3 && report.passed && report.positions===2553 && report.issues.length===0);
    assert.equal(sha(fs.readFileSync(fixture)),report.fixture_sha256);
    assert.equal(sha(fs.readFileSync(proofFile)),report.cases_sha256);
    assert.equal(sha(fs.readFileSync(path.join(artifact,'manifest.json'))),report.runtime_manifest_sha256);
    const proofs=fs.readFileSync(proofFile,'utf8').trimEnd().split('\n').map(JSON.parse);
    const {publicState}=require(path.join(artifact,'ai/strong/sealed-policy-beliefs.cjs'));
    const output=fs.openSync(process.argv[2],'wx');let index=0;
    try{
        for await(const line of readline.createInterface({input:fs.createReadStream(fixture),crlfDelay:Infinity})){
            const f=JSON.parse(line),q=f.request,p=proofs[index],state=publicState(q.state,q.player);
            const request={...q,state};
            assert(p.index===index && p.original_line_sha256===sha(line) && p.issues.length===0);
            assert.equal(sha(JSON.stringify(request)),p.public_request_sha256);
            assert.equal(sha(JSON.stringify(f.legal)),p.current_legal_sha256);
            const c={index,players:state.players.length,stage:state.phase,variant:state.options.variant,
                sealed:state.options.fastBid,request,legal:f.legal,player_order:p.player_order,
                original_line_sha256:p.original_line_sha256};
            fs.writeSync(output,JSON.stringify(c)+'\n');index++;
        }
        assert.equal(index,2553);
    }finally{fs.closeSync(output);}
    console.log(JSON.stringify({positions:index,source_fixture_sha256:report.fixture_sha256}));
}
main().catch(e=>{console.error(e.stack);process.exitCode=1;});
