// Compare the frozen research engine with a separately compiled production commit.
// This is a compatibility audit, never a model-strength or deployment claim.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const readline = require('node:readline');
const crypto = require('node:crypto');
const oldRoot = path.resolve(process.argv[2]);
const newRoot = path.resolve(process.argv[3]);
const output = path.resolve(process.argv[4]);
const old = require(path.join(oldRoot, 'engine/dist/index.js'));
const current = require(path.join(newRoot, 'engine/dist/index.js'));
const core = require(path.join(oldRoot, 'ai/core.cjs'));
const eco = require(path.join(oldRoot, 'ai/strong/economics.cjs'));
const encoders = require(path.join(oldRoot, 'ai/strong/encoders.cjs'));
const fixturePath = path.join(oldRoot, 'ai/strong/fixtures/multiplayer-serving-v1.jsonl');
const hash = value => crypto.createHash('sha256').update(value).digest('hex');
assert.equal(hash(fs.readFileSync(fixturePath)), 'f1c97bf909e38e5df372a89d169d80f5a6f24c00dccefacd60b10b767f1fcfa0');
const provenance = JSON.parse(fs.readFileSync(path.join(newRoot, 'provenance.json')));
for (const [name, digest] of Object.entries(provenance.production_engine_files))
    assert.equal(hash(fs.readFileSync(path.join(newRoot, name))), digest);

function comparable(g) {
    const result = {...g};
    // New snapshots allow users to revise an already submitted powering choice;
    // announcements are presentation metadata. Keep every other state field.
    delete result.poweringChoices;
    delete result.pendingMessages;
    result.log = g.log.filter(entry => !(entry.type === 'event' && /^Starting Step [23]/.test(entry.event)));
    return result;
}
function sameState(a, b, label) {
    assert.deepEqual(comparable(b), comparable(a), label);
}
function botStep(engine, state, player, seed, time) {
    const random = Math.random, now = Date.now;
    Math.random = core.seedrandom(seed); Date.now = () => time;
    try { engine.moveAI(state, player); return null; }
    catch (error) { return String(error.message); }
    finally { Math.random = random; Date.now = now; }
}

(async () => {
    const result = {provenance, fixture_sha256: hash(fs.readFileSync(fixturePath)), fixtures: 0,
        feature_checks: 0, legal_menu_checks: 0, default_bot: {identical: 0, different: []}, games: [],
        exclusions: ['root.poweringChoices', 'root.pendingMessages', 'log event text starting with Starting Step2/3'],
        qualification_eligible: false,
        scope: 'Germany original/Recharged, open/sealed,2–6p; ordinary current-player decisions only. No pending choice revisions, wrapper scheduling or platform transport tested. No strength qualification.'};
    for await (const line of readline.createInterface({input: fs.createReadStream(fixturePath)})) {
        const fixture = JSON.parse(line), {state, player} = fixture.request;
        const a = structuredClone(state), b = structuredClone(state);
        assert.deepEqual(current.availableMoves(b, b.players[player]), old.availableMoves(a, a.players[player]));
        result.legal_menu_checks++;
        const p = structuredClone(state);
        p.poweringChoices = {[player]: {round: state.round, money: state.players[player].money}};
        p.pendingMessages = ['Starting Step 3.'];
        for (const revision of ['4.0-multiplayer', '4.2-discard-correction']) {
            const encoder = encoders.forRevision(revision);
            assert.deepEqual(encoder.encode(p, player), encoder.encode(state, player));
            result.feature_checks++;
        }
        const x = structuredClone(state), y = structuredClone(state);
        const seed = 'production-engine-fixture-'+result.fixtures;
        const oldError = botStep(old, x, player, seed, 100000000);
        const newError = botStep(current, y, player, seed, 100000000);
        if (!oldError && !newError) {
            try { sameState(x, y, 'Default bot transition'); result.default_bot.identical++; }
            catch (error) { result.default_bot.different.push({fixture: result.fixtures, old_move: x.players[player].lastMove,
                new_move: y.players[player].lastMove, state_transition_equal: false}); }
        } else result.default_bot.different.push({fixture: result.fixtures, old_error: oldError, new_error: newError});
        result.fixtures++;
    }
    assert.equal(result.fixtures, 2553); assert.equal(result.feature_checks, 5106);
    for (const players of [2,3,4,5,6]) for (const variant of ['original', 'recharged'])
        for (const sealed of [false, true]) for (let deal = 0; deal < 4; deal++) {
            const seed = `production-engine-compat-v1-${players}p-${variant}-${sealed}-${deal}`;
            const options = {map: 'Germany', variant, fastBid: sealed, showMoney: true};
            const a = old.setup(players, options, seed), b = current.setup(players, options, seed);
            const rng = core.seedrandom(seed+'-policy');
            const trace = crypto.createHash('sha256'), phases = {};
            let moves = 0;
            sameState(a, b, seed+' setup');
            while (!old.ended(a) && moves < 1600) {
                assert(!current.ended(b));
                assert.deepEqual(b.currentPlayers, a.currentPlayers);
                const seat = a.currentPlayers[0], g = structuredClone(a);
                const action = (seat % 2 ? core.heuristic(g, seat, rng) : eco.choose(g, seat, rng)).action;
                phases[a.phase] = (phases[a.phase] || 0)+1;
                old.move(a, structuredClone(action), seat); current.move(b, structuredClone(action), seat);
                sameState(a, b, seed+' move'+moves);
                trace.update(JSON.stringify({seat, action, state: comparable(a)}));
                moves++;
            }
            assert(old.ended(a) && current.ended(b), seed+' truncated');
            assert.deepEqual(core.outcome(a), core.outcome(b));
            result.games.push({seed, players, variant, sealed, moves, phases, outcome: core.outcome(a),
                trace_sha256: trace.digest('hex'), all_transitions_match: true});
            console.log(JSON.stringify({games: result.games.length, players, variant, sealed, moves}));
        }
    assert.equal(result.games.length, 80);
    result.passed = true;
    fs.writeFileSync(output, JSON.stringify(result, null, 2)+'\n', {flag: 'wx'});
    console.log(JSON.stringify({fixtures: result.fixtures, games: result.games.length,
        default_bot_identical: result.default_bot.identical, default_bot_differences: result.default_bot.different.length,
        passed: true, qualification_eligible: false}));
})().catch(error => { console.error(error); process.exitCode = 1; });
