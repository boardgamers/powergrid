// Diagnostic process only: compare the frozen schema4 model's action menu.
// Never use this temporary candidate override in a game or training worker.
const fs = require('node:fs'), readline = require('node:readline'), assert = require('node:assert/strict'),
    core = require('../core.cjs'), encoder = require('./features-v4.cjs');
async function main() {
    const [input, output] = process.argv.slice(2), fd = fs.openSync(output, 'w');
    let position = 0, rows = 0;
    try {
        for await (const line of readline.createInterface({input: fs.createReadStream(input)})) {
            const {request} = JSON.parse(line), g = request.state, seat = request.player,
                all = core.allLegal(g, seat), kept = core.candidates(g, seat), index = position++;
            if (all.length === kept.length) continue;
            const before = JSON.stringify(g), original = encoder.encode(g, seat), saved = core.candidates;
            let expanded;
            try {
                core.candidates = (state, player) => {
                    assert.equal(state, g); assert.equal(player, seat); return all;
                };
                expanded = encoder.encode(g, seat);
            } finally {core.candidates = saved;}
            assert.equal(core.candidates, saved);
            assert.equal(JSON.stringify(g), before);
            assert.deepEqual(original.moves, kept);
            assert.deepEqual(expanded.moves, all);
            assert.deepEqual(expanded.state, original.state);
            // Menu-relative best-heuristic flags may change. Every other existing
            // action feature must remain bit-for-bit identical.
            const map = new Map(all.map((a, i) => [JSON.stringify(a), i]));
            for (let i = 0; i < kept.length; i++) {
                const full = expanded.actions[map.get(JSON.stringify(kept[i]))];
                assert.deepEqual(full.filter((_, j) => j !== 75), original.actions[i].filter((_, j) => j !== 75));
            }
            assert.deepEqual(encoder.encode(g, seat), original);
            fs.writeSync(fd, JSON.stringify({position: index,
                key: `${g.players.length}p/${g.options.variant}/${g.options.fastBid ? 'sealed' : 'open'}`,
                original, expanded}) + '\n');
            rows++;
        }
    } finally {fs.closeSync(fd);}
    console.log(JSON.stringify({positions: position, expanded_positions: rows,
        identical_state: true, identical_existing_features_except_menu_best_flag: true,
        restored_encoder_exact: true, game_states_unchanged: true}));
}
main().catch(error => {console.error(error); process.exitCode = 1;});
