// Replay saved public action histories; never call a policy or an opponent.
const fs = require('node:fs'), path = require('node:path'), zlib = require('node:zlib');
const assert = require('node:assert/strict'), {isDeepStrictEqual: same} = require('node:util');
const [root, out] = process.argv.slice(2);
const read = p => JSON.parse(fs.readFileSync(p, 'utf8'));
const clone = x => JSON.parse(JSON.stringify(x));
const design = read(path.join(out, 'design.json'));
const oldPath = path.join(root, design.runtime, 'engine/dist');
const newPath = path.join(root, design.current_engine, 'dist');
const oldEngine = require(path.join(oldPath, 'index.js'));
const newEngine = require(path.join(newPath, 'index.js'));
const oldStrip = require(path.join(oldPath, 'src/engine.js')).stripSecret;
const newStrip = require(path.join(newPath, 'src/engine.js')).stripSecret;
const extension = require('./features-v4_4.cjs');
const write = (name, x) => fs.writeFileSync(path.join(out, name), JSON.stringify(x, null, 2) + '\n', {flag: 'wx'});
const flat = menu => Object.entries(menu || {}).flatMap(([name, values]) => (values || []).map(data => ({name, data})));
const count = (table, key) => table[key] = (table[key] || 0) + 1;
function publicState(g, seat, strip) {
    const x = clone(strip(g, seat));
    delete x.powerPlantDeckAfterStep3; delete x.automation;
    if (x.options.fastBid) x.currentBid = 0;
    for (const p of x.players) {p.lastMove = null; if (x.options.fastBid) p.bid = 0;}
    assert.deepEqual(x.powerPlantsDeck, []); assert.deepEqual(x.hiddenLog, []);
    assert.equal(x.seed, 'secret'); assert(x.options.showMoney);
    return x;
}
function stable(x) {
    const g = clone(x);
    for (const p of g.players) {delete p.clockStartedAt; delete p.totalTimeUsed;}
    for (const item of [...g.log, ...g.hiddenLog])
        if (item.type === 'move') {delete item.move.time; delete item.move.serverTime;}
    return g;
}
function economic(g) {
    const {log, hiddenLog, poweringChoices, pendingMessages, ...rest} = g;
    return clone({...rest, players: g.players.map(p => {
        const {clockStartedAt, totalTimeUsed, availableMoves, ...other} = p;
        if (other.lastMove) {other.lastMove = {...other.lastMove}; delete other.lastMove.time; delete other.lastMove.serverTime;}
        return other;
    })});
}
const prefixes = zlib.gunzipSync(fs.readFileSync(path.join(out, 'prefixes.jsonl.gz'))).toString().trim().split('\n').map(JSON.parse);
const report = {passed: false, prefixes_verified: 0, transitions: 0, newly_affordable_roots: 0,
    learner_roots: 0, opponent_roots: 0, coverage: {players: {}, rules: {}, splits: {}, steps: {}},
    prefixes: [], interpretation: 'Natural fixed-history public states recovered before recorded actions; no altered action choices, teacher targets or strength results.'};
const roots = fs.openSync(path.join(out, 'newly-affordable-roots.jsonl'), 'wx');
let active = null;
try {
    for (const prefix of prefixes) {
        const n = prefix.players, seat = prefix.request.player;
        active = {source_root_id: prefix.rootId, players: n, episode: prefix.episode, split: prefix.split};
        const options = {map: 'Germany', variant: prefix.variant, fastBid: prefix.sealed, showMoney: true};
        assert(prefix.gameSeed.startsWith('policy-iteration-training-v2-'));
        const old = oldEngine.setup(n, options, prefix.gameSeed), current = newEngine.setup(n, options, prefix.gameSeed);
        assert.deepEqual(economic(old), economic(current));
        const moves = prefix.request.state.log.filter(item => item.type === 'move');
        let steps = 0, gaps = 0;
        for (const item of moves) {
            const actor = item.player;
            assert.equal(old.currentPlayers[0], actor, 'Recorded public moves not in execution order');
            assert.equal(current.currentPlayers[0], actor);
            const oldMoves = flat(old.players[actor].availableMoves), nextMoves = flat(current.players[actor].availableMoves);
            const added = nextMoves.filter(a => !oldMoves.some(b => same(a, b)));
            const removed = oldMoves.filter(a => !nextMoves.some(b => same(a, b)));
            if (added.length || removed.length) {
                assert.equal(current.phase, 'Auction'); assert(!current.chosenPowerPlant);
                assert.equal(current.options.variant, 'recharged'); assert(current.plantDiscountActive);
                const cheapest = current.actualMarket[0];
                assert(current.players[actor].money >= 1 && current.players[actor].money < cheapest.number);
                assert.deepEqual(added, [{name: 'ChoosePowerPlant', data: cheapest.number}]);
                assert.deepEqual(removed, []); assert.deepEqual(oldMoves, [{name: 'Pass', data: true}]);
                assert.equal(extension.openingBid(current, cheapest), 1);
                const request = {state: publicState(current, actor, newStrip), player: actor};
                const row = {...active, source_public_root_sha256: prefix.public_root_sha256,
                    gameSeed: prefix.gameSeed, deal: prefix.deal, before_move: steps,
                    round: current.round, step: current.step, variant: prefix.variant, sealed: prefix.sealed,
                    role: actor === seat ? 'learner' : 'economic', money: current.players[actor].money,
                    plant: cheapest.number, opening_bid: 1, old_legal: oldMoves, legal: nextMoves, request,
                    recorded_action: {name: item.move.name, data: item.move.data}, labelled: false};
                fs.writeSync(roots, JSON.stringify(row) + '\n');
                report.newly_affordable_roots++; gaps++;
                report[actor === seat ? 'learner_roots' : 'opponent_roots']++;
                count(report.coverage.players, n); count(report.coverage.rules, prefix.variant + '/' + (prefix.sealed ? 'sealed' : 'open'));
                count(report.coverage.splits, prefix.split); count(report.coverage.steps, current.step);
            }
            const move = {name: item.move.name, data: clone(item.move.data)};
            assert(oldMoves.some(a => same(a, move)), 'Recorded move is not legal in the original engine');
            assert(nextMoves.some(a => same(a, move)), 'Recorded move is not legal in the current engine');
            oldEngine.move(old, clone(move), actor); newEngine.move(current, clone(move), actor);
            assert.deepEqual(economic(old), economic(current), 'Fixed economic transition differs');
            report.transitions++; steps++;
        }
        assert.equal(old.currentPlayers[0], seat);
        assert.deepEqual(stable(publicState(old, seat, oldStrip)), stable(prefix.request.state), 'Historical public root did not reconstruct');
        report.prefixes_verified++;
        report.prefixes.push({...active, transitions: steps, newly_affordable_roots: gaps, historical_public_root_exact: true});
        console.log(JSON.stringify({prefixes_verified: report.prefixes_verified, transitions: report.transitions, newly_affordable_roots: report.newly_affordable_roots}));
    }
    assert.equal(report.prefixes_verified, design.expected_prefixes);
    report.passed = true; write('assessment.json', report);
} catch (error) {
    write('failure.json', {error: error.stack, active, report}); console.error(error.stack); process.exitCode = 1;
} finally {fs.closeSync(roots);}
