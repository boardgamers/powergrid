// Read-only compatibility audit of every original multiplayer serving fixture.
// Never calls move(), setup(), a policy, inference, HF, or a final seed source.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const readline = require('node:readline');
const {isDeepStrictEqual: same} = require('node:util');

const ROOT = path.resolve(__dirname, '../..');
const ARTIFACT = path.join(ROOT, 'ai/runs/current-auction-grid-prepared-v1/source/artifact');
const FIXTURES = path.join(ROOT, 'ai/strong/fixtures/multiplayer-serving-v1.jsonl');
const OUT = path.join(ROOT, 'ai/runs/current-engine-serving-fixture-audit-v1');
const RESULT = path.join(ROOT, 'ai/strong/current-engine-serving-fixture-audit-v1.json');
const FIXTURE_SHA = 'f1c97bf909e38e5df372a89d169d80f5a6f24c00dccefacd60b10b767f1fcfa0';
const RUNTIME_SHA = 'fc135130689140b6fd72a76e6e14c59a7fea59717b858d330bac0c7f6aad93df';
const REVISION = '4.3-strategic-correction';
const sha = x => crypto.createHash('sha256').update(x).digest('hex');
const digest = f => sha(fs.readFileSync(f));
const wire = x => JSON.stringify(x);
const save = (f, x) => fs.writeFileSync(f, JSON.stringify(x, null, 2)+'\n', {flag:'wx'});
const relative = f => path.relative(ROOT, f);

async function main() {
    assert(!fs.existsSync(OUT) && !fs.existsSync(RESULT), 'Inspect original outcome before any retry');
    assert.equal(digest(FIXTURES), FIXTURE_SHA);
    assert.equal(digest(path.join(ARTIFACT,'manifest.json')), RUNTIME_SHA);
    const manifest = JSON.parse(fs.readFileSync(path.join(ARTIFACT,'manifest.json')));
    const checkInputs = () => {
        assert.equal(digest(FIXTURES), FIXTURE_SHA);
        assert.equal(digest(path.join(ARTIFACT,'manifest.json')), RUNTIME_SHA);
        for (const [n,h] of Object.entries(manifest)) assert.equal(digest(path.join(ARTIFACT,n)), h, n);
    };
    checkInputs();
    const c = require(path.join(ARTIFACT,'ai/core.cjs'));
    const beliefs = require(path.join(ARTIFACT,'ai/strong/sealed-policy-beliefs.cjs'));
    const encoder = require(path.join(ARTIFACT,'ai/strong/encoders.cjs')).forRevision(REVISION);
    fs.mkdirSync(OUT);
    save(path.join(OUT,'intent.json'), {started_at:new Date().toISOString(),pid:process.pid,
        fixture_sha256:FIXTURE_SHA, runtime_manifest_sha256:RUNTIME_SHA,
        script_sha256:digest(__filename), expected_positions:2553,
        scope:'Read-only current-engine menu/public-projection/feature audit; no inference or game execution.',
        new_full_games:0,new_policy_calls:0,new_hf_jobs:0,reserved_final_seeds_used:false});
    const fd = fs.openSync(path.join(OUT,'cases.jsonl'), 'wx');
    let total=0; const issues=[], counts={}, seen=new Set();
    const increment = key => {counts[key]=(counts[key]||0)+1;};
    try {
        const stream=readline.createInterface({input:fs.createReadStream(FIXTURES),crlfDelay:Infinity});
        for await (const line of stream) {
            const fixture=JSON.parse(line), q=fixture.request, original=wire(q), n=q.state.players.length;
            assert(!seen.has(q.requestId), 'Duplicate original request');seen.add(q.requestId);
            const row={index:total,requestId:q.requestId,revision:q.revision,player:q.player,players:n,
                phase:q.state.phase,variant:q.state.options.variant,sealed:q.state.options.fastBid,
                original_line_sha256:sha(line),original_legal_sha256:sha(wire(fixture.legal)),issues:[]};
            const inspect=(ok,label)=>{if(!ok)row.issues.push(label);};
            try {
                const g=beliefs.publicState(q.state,q.player), publicBefore=wire(g);
                inspect(n>=2 && n<=6 && g.map.name==='Germany','unsupported_scope');
                inspect(g.currentPlayers.includes(q.player),'actor_not_pending');
                inspect(g.options.showMoney===true && g.players.every((p,i)=>p.money===q.state.players[i].money),'public_money_changed');
                inspect(g.seed==='secret' && g.powerPlantsDeck.length===0 && g.hiddenLog.length===0
                    && !Object.hasOwn(g,'powerPlantDeckAfterStep3') && !Object.hasOwn(g,'automation')
                    && g.players.every(p=>p.lastMove===null && (!g.options.fastBid || p.bid===0)), 'private_fields_retained');
                const cached=c.candidates(g,q.player);
                inspect(same(cached,fixture.legal),'original_public_menu_changed');
                const fresh=structuredClone(g);
                fresh.players[q.player].availableMoves=c.E.availableMoves(fresh,fresh.players[q.player]);
                const current=c.candidates(fresh,q.player);
                inspect(same(current,cached),'current_engine_menu_changed');
                row.original_menu_size=cached.length;row.current_menu_size=current.length;
                row.removed_actions=cached.filter(m=>!current.some(a=>same(a,m)));
                row.added_actions=current.filter(m=>!cached.some(a=>same(a,m)));
                row.current_legal_sha256=sha(wire(current));row.public_request_sha256=sha(wire({...q,state:g}));
                const features=encoder.encode(g,q.player);
                inspect(features.state.length===encoder.STATE_DIM && features.state.every(Number.isFinite)
                    && features.actions.length===cached.length && features.actions.every(a=>a.length===encoder.ACTION_DIM && a.every(Number.isFinite)),'invalid_features');
                inspect(same(features.moves,cached),'feature_menu_changed');
                inspect(same(features.playerOrder,Array.from({length:n},(_,i)=>(q.player+i)%n)),'player_order_changed');
                row.features_sha256=sha(wire(features));row.player_order=features.playerOrder;
                inspect(wire(g)===publicBefore,'public_input_mutated');
                inspect(wire(q)===original,'original_input_mutated');
            } catch(error) {row.issues.push('preparation_error');row.error={name:error.name,message:error.message};}
            total++;increment('players_'+n);increment('rule_'+row.variant+'_'+(row.sealed?'sealed':'open'));increment('phase_'+row.phase);
            for(const issue of row.issues)increment(issue);
            if(row.issues.length)issues.push({index:row.index,requestId:row.requestId,issues:row.issues});
            fs.writeSync(fd,wire(row)+'\n');
        }
    } finally {fs.closeSync(fd);}
    assert.equal(total,2553);checkInputs();
    const result={complete:true,passed:issues.length===0,created_at:new Date().toISOString(),
        positions:total,counts,issues,fixture_sha256:FIXTURE_SHA,runtime_manifest_sha256:RUNTIME_SHA,
        script_sha256:digest(__filename),cases_path:relative(path.join(OUT,'cases.jsonl')),
        cases_sha256:digest(path.join(OUT,'cases.jsonl')),intent_sha256:digest(path.join(OUT,'intent.json')),
        original_positions_preserved:true,new_full_games:0,new_policy_calls:0,new_hf_jobs:0,
        candidate_selected:false,qualified:false,reserved_final_seeds_used:false,
        scope:'Compatibility of all original saved fixtures with current engine public preparation only. No neural/checkpoint/export/serving parity or search-strength claim.'};
    save(RESULT,result);
    console.log(wire({complete:true,passed:result.passed,positions:total,issue_positions:issues.length,counts}));
}
main().catch(e=>{console.error(e.stack);process.exitCode=1;});
