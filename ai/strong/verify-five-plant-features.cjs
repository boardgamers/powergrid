// Exhaustive fixture check; encode all rows for CPU inference/ONNX verification.
const fs = require('node:fs'), readline = require('node:readline'), assert = require('node:assert/strict'),
    crypto = require('node:crypto'), base = require('./features-v4.cjs'), next = require('./features-v4_1.cjs'),
    eco = require('./economics-v4_1.cjs');
async function main() {
    const [input, output] = process.argv.slice(2), stats = {positions: 0, by_player_count: {},
        five_plant_positions: 0, three_plant_two_player_positions: 0, changed_action_cue_positions: 0,
        hidden_information_invariant: true, legacy_prefix_exact: true};
    const fd = fs.openSync(output, 'w');
    try {
        for await (const line of readline.createInterface({input: fs.createReadStream(input)})) {
            const {request} = JSON.parse(line), g = request.state, seat = request.player,
                old = base.encode(g, seat), row = next.encode(g, seat), before = JSON.stringify(g);
            assert.equal(row.state.length, next.STATE_DIM);
            assert.deepEqual(row.state.slice(0, 1149), old.state);
            assert.deepEqual(row.actions.map(a => a.slice(0, 98)), old.actions);
            for (const key of ['moves', 'prior', 'teacher', 'seat', 'playerMask', 'playerOrder'])
                assert.deepEqual(row[key], old[key]);
            assert.ok(row.state.every(Number.isFinite));
            assert.ok(row.actions.every(a => a.length === 100 && a.every(Number.isFinite)));
            const corrected = eco.scores(g, seat, row.moves), best = Math.max(...corrected);
            assert.deepEqual(row.actions.map(a => a.slice(98)), corrected.map(v =>
                [Math.max(-10, Math.min(10, v / 10)), +(v === best)]));
            const n = g.players.length;
            assert.deepEqual(row.state.slice(1149 + 11 * n), Array(11 * (6 - n)).fill(0));
            for (let i = 0; i < n; i++) {
                const p = g.players[row.playerOrder[i]], pp = p.powerPlants[4];
                assert.deepEqual(row.state.slice(1149 + i * 11, 1160 + i * 11), pp
                    ? [pp.number / 50, pp.cost / 4, pp.citiesPowered / 8,
                        ...Array.from({length: 7}, (_, t) => +(pp.type === t)), +p.powerPlantsNotUsed.includes(pp.number)]
                    : Array(11).fill(0));
            }
            const hidden = structuredClone(g);
            hidden.powerPlantsDeck.reverse(); hidden.seed = 'hidden-fixture-perturbation';
            hidden.automation = {version: 1, increments: Array(n).fill(42), liveUpdate: true,
                plans: Object.fromEntries(g.players.map((_, id) => [id, {round: g.round,
                    revision: 999, requestId: 'private-plan', phases: [{phase: 'Building', moves: [{name: 'Pass'}]}]}]))};
            hidden.players.forEach(p => {
                p.queuedMoves = [{name: 'Pass'}]; p.pendingMoves = [{name: 'Pass'}];
                if (g.options.fastBid) p.bid = 997;
            });
            if (g.options.fastBid) hidden.currentBid = 998;
            assert.deepEqual(next.encode(hidden, seat), row);
            assert.equal(JSON.stringify(g), before);
            stats.positions++;
            stats.by_player_count[n] = (stats.by_player_count[n] || 0) + 1;
            stats.five_plant_positions += +g.players.some(p => p.powerPlants.length === 5);
            stats.three_plant_two_player_positions += +(n === 2 && g.players[seat].powerPlants.length === 3);
            stats.changed_action_cue_positions += +row.actions.some(a => a[98] !== a[74] || a[99] !== a[75]);
            fs.writeSync(fd, JSON.stringify(row) + '\n');
        }
    } finally {fs.closeSync(fd);}
    stats.fixture_sha256 = crypto.createHash('sha256').update(fs.readFileSync(input)).digest('hex');
    stats.encoded_sha256 = crypto.createHash('sha256').update(fs.readFileSync(output)).digest('hex');
    fs.writeFileSync(output + '.json', JSON.stringify(stats, null, 2) + '\n');
    console.log(JSON.stringify(stats));
}
main().catch(e => {console.error(e); process.exitCode = 1;});
