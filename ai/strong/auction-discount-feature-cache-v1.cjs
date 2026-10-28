// Re-encode recorded training roots through a pinned parent, without inference.
const assert = require('node:assert/strict'), path = require('node:path');
const readline = require('node:readline');
const parent = require(path.join(path.resolve(process.argv[2]), 'ai/strong/features-v4_3.cjs'));
const enginePath = path.resolve(process.argv[3]);
const engine = require(path.join(enginePath, 'dist/index.js'));
const {minimumPlantBid} = require(path.join(enginePath, 'dist/src/auction-pricing.js'));
const extension = require('./features-v4_4.cjs');
const {inputHash} = require('./policy-iteration-input-hashes.cjs');

readline.createInterface({input: process.stdin}).on('line', line => {
    try {
        const answers = JSON.parse(line).map(root => {
            const {state, player} = root.request;
            const before = JSON.stringify(state);
            const base = parent.encode(state, player), row = extension.extend(state, base);
            assert.deepEqual(base.moves, root.legal);
            assert.deepEqual(row.state.slice(0, 1217), base.state);
            assert.deepEqual(row.actions.map(a => a.slice(0, 101)), base.actions);
            for (const key of Object.keys(base))
                if (!['state', 'actions', 'featureRevision'].includes(key)) assert.deepEqual(row[key], base[key]);
            for (let i = 0; i < row.moves.length; i++) {
                const move = row.moves[i];
                if (move.name === 'ChoosePowerPlant') {
                    const plant = state.actualMarket.find(p => p.number === move.data);
                    const expected = minimumPlantBid(state, plant);
                    assert.equal(row.actions[i][101], expected / 50);
                    assert.equal(row.actions[i][102], (plant.number - expected) / 50);
                } else assert.deepEqual(row.actions[i].slice(101), [0, 0]);
            }
            const current = engine.availableMoves(state, state.players[player]);
            assert.equal(JSON.stringify(state), before, 'Read-only feature check mutated a public state');
            return {rootId: root.rootId,
                policy_input_sha256: inputHash(base.state.slice(0, 1216), base.actions.map(a => a.slice(0, 100))),
                state: row.state, actions: row.actions,
                current_nominations: current.ChoosePowerPlant || []};
        });
        process.stdout.write(JSON.stringify(answers) + '\n');
    } catch (error) {
        process.stderr.write(error.stack + '\n');
        process.exit(1);
    }
});
