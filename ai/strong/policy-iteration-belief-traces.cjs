// Independent trace reconstruction for larger paired-world label batches.
const assert = require('node:assert/strict');
const beliefs = require('./sealed-policy-beliefs.cjs');
const {createAnalysisScenario} = require('../../engine/dist/src/analysis.js');
const readline = require('node:readline');
readline.createInterface({input: process.stdin}).on('line', line => {
    try {
        const q = JSON.parse(line);
        assert(Number.isInteger(q.samples) && q.samples > 0 && q.samples <= 96);
        assert(['neural', 'neural_economic'].includes(q.mode));
        const prior = beliefs.prompts(q.state, q.player);
        const traces = Array.from({length: q.samples}, (_, sample) => {
            const seed = q.seed + '-' + sample;
            const g = createAnalysisScenario(q.state, {player: q.player, seed});
            return beliefs.applyPolicyBids(g, prior, q.mode, q.neuralBeliefs || {}, seed);
        });
        process.stdout.write(JSON.stringify({traces}) + '\n');
    } catch (e) { process.stderr.write(String(e.stack) + '\n'); process.exit(1); }
});
