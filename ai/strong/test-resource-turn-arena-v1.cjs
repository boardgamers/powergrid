// Replay recorded choices only. No inference, newly sampled games, or HF submissions.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const {spawn} = require('node:child_process');
const {createInterface} = require('node:readline');
const {once} = require('node:events');
const {createResourceTurnArena} = require('./resource-turn-arena-bridge-v1.cjs');
const {createResourceTurnExchange} = require('./resource-turn-exchange-v1.cjs');
const root = path.resolve(__dirname,'../..');
const runtime = path.join(root,'ai/runs/resource-replanning-job-source-prepared-v1/layout');
const out = path.resolve(process.argv[2]);
const read = p=>JSON.parse(fs.readFileSync(p,'utf8'));
const sha = p=>crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
const hash = value=>crypto.createHash('sha256').update(JSON.stringify(value)).digest('hex');
const clone = value=>structuredClone(value);
const codeHashes = Object.fromEntries(['resource-turn-exchange-v1.cjs','resource-turn-arena-bridge-v1.cjs',
    'resource-turn-transaction-v1.cjs','test-resource-turn-arena-v1.cjs'].map(name=>[name,sha(path.join(__dirname,name))]));
const inputs = {};
const evidencePath = path.join(root,'ai/strong/resource-replanning-development-complete-evidence-v1.json');
const evidence = read(evidencePath);
const manifestPath = path.join(runtime,'resource-job-manifest.json');
assert.equal(sha(manifestPath),evidence.source.manifest_sha256);
const runtimeManifest = read(manifestPath);
for (const [name,expected] of Object.entries(runtimeManifest))
    assert.equal(sha(path.join(runtime,name)),expected,name);
const archiveManifestPath = path.join(root,'ai/runs/resource-replanning-development-complete-evidence-v1/manifest.json');
assert.equal(sha(archiveManifestPath),evidence.manifest_sha256);
const archiveManifest = read(archiveManifestPath);
function recorded(name) {
    const file = path.join(root,name), digest = sha(file);
    assert.equal(digest,archiveManifest[name],name);inputs[name]=digest;return file;
}
const c = require(path.join(runtime,'ai/core.cjs'));
const exchange = createResourceTurnExchange(runtime);
const identity = {modelSha256:'55331f43379e8fe89025d93b1a7a48c88e0ea39b4ebd3a7ef8240d4b62753530',
    runtimeManifestSha256:sha(manifestPath),
    policySha256:hash({kind:'recorded-atomic-choices-grouped-through-Pass',deals:[0],inference:false})};

// Compare the original logical trajectory. Only legacy-bot wall-clock bookkeeping
// and the explicitly added request metadata/public legal menu may differ.
function semantic(value) {
    // Match the JSON wire representation (undefined optional engine properties
    // are omitted by both subprocesses).
    const result = JSON.parse(JSON.stringify(value));
    for (const row of result.observations) {
        if (!row) continue;
        delete row.moves;delete row.request.requestId;delete row.request.revision;
        for (const player of row.request.state.players) {
            delete player.clockStartedAt;delete player.totalTimeUsed;
            if (player.lastMove) {delete player.lastMove.time;delete player.lastMove.serverTime;}
        }
        for (const event of row.request.state.log || []) if (event.move) {
            delete event.move.time;delete event.move.serverTime;
        }
    }
    return result;
}

function worker(entry,args,label) {
    const stderr = fs.openSync(path.join(out,label+'.stderr.log'),'wx');
    const process = spawn(global.process.execPath,[entry,...args],{cwd:'/tmp',stdio:['pipe','pipe',stderr]});
    fs.closeSync(stderr);
    const lines = createInterface({input:process.stdout})[Symbol.asyncIterator]();
    const exit = once(process,'exit');
    return {
        async call(request) {
            process.stdin.write(JSON.stringify(request)+'\n');
            let timer;
            try {
                const result = await Promise.race([lines.next(),new Promise((_,reject)=>{
                    timer=setTimeout(()=>reject(new Error(label+' response timeout')),30000);
                })]);
                assert(!result.done,label+' exited; inspect preserved stderr');
                return JSON.parse(result.value);
            } finally {clearTimeout(timer);}
        },
        async close() {
            process.stdin.end();
            const [code,signal] = await exit;assert.equal(code,0,label+' '+signal);
        },
        stop() {process.kill('SIGTERM');}
    };
}

async function main() {
    fs.mkdirSync(out,{recursive:false});
    const receiptsPath = path.join(out,'receipts.jsonl');
    const fd = fs.openSync(receiptsPath,'wx');
    const original = worker(path.join(runtime,'ai/strong/public-arena-bridge.cjs'),[],'original');
    const wire = worker(path.join(__dirname,'resource-turn-arena-bridge-v1.cjs'),[runtime],'whole-turn');
    const direct = createResourceTurnArena(runtime);
    const report = {passed:false,original_games_replayed:0,recorded_learner_actions:0,
        resource_turns:0,resource_actions:0,rejected_controls:0,hidden_controls:0,clock_binding_controls:0,
        new_inference:0,new_full_games:0,new_hf_jobs:0,qualification_eligible:false,
        reserved_final_seeds_used:false,cases:[]};
    try {
        // Predetermined coverage, never selected by outcomes: all seats/all four
        // rules in deal zero versus economic, plus seat zero legacy and old search.
        for (const [arm,opponent,allSeats] of [['filter','economic',true],['filter','legacy',false],
            ['resource-filter','economic',false]]) for (let n=2;n<=6;n++) {
            const folder = `ai/runs/resource-replanning-development-collected-v1/resource-replanning-development-v1-${arm}-${n}p-${opponent}-0-4/artifacts/evaluation`;
            const evaluation = read(recorded(folder+'/evaluation.json'));
            assert.equal(evaluation.config.model_sha256,identity.modelSha256);
            assert.equal(evaluation.config.opponent,opponent);assert.equal(evaluation.config.players,n);
            assert.equal(evaluation.config.arm,arm);assert(evaluation.all_complete);
            for (let episode=0;episode<4*(allSeats?n:1);episode++) {
                const record = evaluation.results.find(r=>r.episode===episode);assert(record);
                const file = recorded(folder+`/decisions-${episode}.jsonl`);
                assert.equal(sha(file),record.decision_receipt_sha256);
                const rows = fs.readFileSync(file,'utf8').trim().split('\n').map(JSON.parse);
                const reset = {op:'reset',n:1,offset:episode,arenaSeed:evaluation.config.seed,
                    playerCount:n,mode:opponent,featureRevisions:{learner:'4.3-strategic-correction'}};
                let reference = await original.call(reset);
                const enabled = {...reset,publicMoves:true,publicResourceTurns:true,policyIdentity:identity};
                let actual = await wire.call(enabled), local = direct.handle(clone(enabled));
                assert.deepEqual(semantic(actual),semantic(reference));
                assert.deepEqual(semantic(local),semantic(reference));
                let index=0,turns=0,actions=0,negativeChecked=false;
                while (index<rows.length) {
                    const row = rows[index], observation = actual.observations[0];assert(observation);
                    assert.equal(observation.round,row.round);
                    assert.deepEqual(observation.moves[row.index],row.move);
                    if (observation.request.state.phase === c.E.Phase.Resources) {
                        const from=index,buffer=[];
                        do {
                            assert(index<rows.length);
                            const next=rows[index++];buffer.push(next.move);
                            assert(['BuyResource','Pass'].includes(next.move.name));
                            reference=await original.call({op:'step',actions:[next.index]});
                        } while (buffer.at(-1).name!=='Pass');
                        const response=exchange.respond(observation.request,buffer,identity);
                        // Independent legacy bots stamp different wall-clock values.
                        // Each response must bind its own exact root; do not weaken
                        // the execution contract to make cross-instance hashes match.
                        const localRequest=local.observations[0].request;
                        const localResponse=exchange.respond(localRequest,buffer,identity);
                        const a=clone(response),b=clone(localResponse);
                        delete a.transaction.rootSha256;delete b.transaction.rootSha256;
                        assert.deepEqual(a,b);
                        if(response.transaction.rootSha256!==localResponse.transaction.rootSha256) {
                            assert.throws(()=>direct.handle({op:'step',actions:[{publicResourceTurn:response}]}));
                            report.clock_binding_controls++;
                        }
                        if (!negativeChecked) {
                            const changes = [r=>r.requestId+='-stale',r=>r.revision++,
                                r=>r.identity.modelSha256='0'.repeat(64),r=>r.transaction.cost++,
                                r=>r.transaction.actions.pop(),r=>r.transaction.actions.push({name:'Pass',data:true}),
                                r=>r.extra=true,r=>r.transaction.player=(r.transaction.player+1)%n,
                                r=>r.transaction.rootSha256='0'.repeat(64),
                                r=>r.transaction.actions.splice(-1,0,{name:'BuyResource',data:{resource:'bad'}})];
                            for (const mutate of changes) {
                                const bad=clone(localResponse);mutate(bad);
                                assert.throws(()=>direct.handle({op:'step',actions:[{publicResourceTurn:bad}]}));
                                report.rejected_controls++;
                            }
                            const stale=clone(localRequest);stale.state.players[stale.player].money++;
                            const staleResponse=exchange.respond(stale,buffer,identity);
                            assert.throws(()=>direct.handle({op:'step',actions:[{publicResourceTurn:staleResponse}]}));
                            report.rejected_controls++;
                            negativeChecked=true;
                        }
                        const poisoned=clone(observation.request);
                        poisoned.state.seed='private-poison';poisoned.state.powerPlantsDeck=[{number:9999}];
                        poisoned.state.powerPlantDeckAfterStep3=[{number:9998}];
                        poisoned.state.hiddenLog=[{secret:true}];
                        if(poisoned.state.options.fastBid) {
                            poisoned.state.currentBid=9997;
                            poisoned.state.players.forEach(p=>p.bid=9996);
                        }
                        assert.deepEqual(exchange.respond(poisoned,buffer,identity),response);
                        report.hidden_controls++;
                        const command={op:'step',actions:[{publicResourceTurn:response}]};
                        actual=await wire.call(command);
                        local=direct.handle({op:'step',actions:[{publicResourceTurn:localResponse}]});
                        turns++;actions+=buffer.length;
                        fs.writeSync(fd,JSON.stringify({arm,opponent,players:n,episode,first_decision:from+1,
                            last_decision:index,response,following_observation_sha256:hash(semantic(actual))})+'\n');
                    } else {
                        index++;
                        reference=await original.call({op:'step',actions:[row.index]});
                        const command={op:'step',actions:[{publicMove:row.move}]};
                        actual=await wire.call(command);local=direct.handle(clone(command));
                    }
                    assert.deepEqual(semantic(actual),semantic(reference),'Wire trajectory differs from original atomic replay');
                    assert.deepEqual(semantic(local),semantic(reference),'Direct trajectory or rejection rollback differs');
                }
                assert.equal(actual.ended.length,1);assert.deepEqual(actual.observations,[null]);
                const terminal=clone(record.terminal);delete terminal.seat;delete terminal.win;
                assert.deepEqual(actual.ended[0],terminal,'Original complete game outcome/counters changed');
                assert(negativeChecked);assert.equal(rows.length,record.decisions);
                report.original_games_replayed++;report.recorded_learner_actions+=rows.length;
                report.resource_turns+=turns;report.resource_actions+=actions;
                report.cases.push({arm,opponent,players:n,episode,seat:record.terminal.seat,
                    variant:terminal.variant,sealed:terminal.sealed,resource_turns:turns,
                    resource_actions:actions,recorded_learner_actions:rows.length,original_terminal_exact:true});
            }
            console.log(JSON.stringify({arm,opponent,players:n,replayed:report.original_games_replayed}));
        }
        assert.equal(report.original_games_replayed,120);
        await original.close();await wire.close();
        fs.closeSync(fd);
        report.passed=true;report.identity=identity;
        report.runtime_files_verified=Object.keys(runtimeManifest).length;
        report.runtime_manifest_sha256=sha(manifestPath);report.inputs=inputs;
        report.upstream_evidence_sha256=sha(evidencePath);report.upstream_archive_manifest_sha256=sha(archiveManifestPath);
        for (const [name,digest] of Object.entries(codeHashes)) assert.equal(sha(path.join(__dirname,name)),digest);
        report.code_hashes=codeHashes;
        report.receipts_sha256=sha(receiptsPath);
        report.scope='Original recorded choices replayed as whole resource turns through a separate JSON arena and direct adapter. Exact logical observations, atomic step counts and original terminal results; no new strength games, policy inference, strategy selection or deployment.';
        fs.writeFileSync(path.join(out,'assessment.json'),JSON.stringify(report,null,2)+'\n',{flag:'wx'});
        console.log(JSON.stringify({...report,cases:report.cases.length,inputs:Object.keys(inputs).length}));
    } catch(error) {
        original.stop();wire.stop();fs.closeSync(fd);
        fs.writeFileSync(path.join(out,'failure.json'),JSON.stringify({error:error.stack,report},null,2)+'\n',{flag:'wx'});
        throw error;
    }
}
main().catch(error=>{console.error(error.stack);process.exitCode=1;});
