// Check recorded public examples and replay deterministic teacher calls.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { publicExample } = require('./capture-reference-opponent-v1.cjs');

function verify(runtime, rows, expected) {
    const search = require(path.join(runtime, 'ai/strong/search.cjs'));
    const totals = { decisions: 0, evaluations: 0, truncated: 0 }, groups = new Map();
    assert(rows.length > 0);
    for (const [i, row] of rows.entries()) {
        assert.equal(row.ordinal, i);
        assert.equal(row.qualification_eligible, false);
        assert.equal(row.playerCount, expected.players);
        assert.notEqual(row.seat, expected.focal_seat);
        assert.equal(row.variant, expected.rule % 2 ? 'recharged' : 'original');
        assert.equal(row.sealed, expected.rule < 2);
        const example = publicExample(runtime, row.request.state, row.request.player);
        for (const [key, value] of Object.entries(example)) assert.deepEqual(row[key], value);
        const o = row.observation, options = row.teacher.options, result = row.teacher.result;
        assert.equal(o.featureRevision, '4.3-strategic-correction');
        assert.equal(o.state.length, 1217);
        assert(o.state.every(Number.isFinite));
        assert(o.actions.every(a => a.length === 101 && a.every(Number.isFinite)));
        assert.equal(options.samples, 16);
        assert.equal(options.candidates, 6);
        assert.equal(options.geography, true);
        assert.equal(options.maxSteps ?? 2400, 2400);
        assert.equal(options.continuation ?? 'mixed', 'mixed');
        assert(Number.isInteger(row.target) && row.target >= 0 && row.target < o.moves.length);
        assert.equal(row.target, result.index);
        assert.deepEqual(o.moves[row.target], result.action);
        assert.equal(result.truncated || 0, 0);
        assert(Number.isInteger(result.evaluations) && result.evaluations >= 0);
        if (result.evaluations) {
            assert.equal(result.evaluations, 16 * Object.keys(result.values).length);
            assert(Object.entries(result.values).every(([k,v]) => Number.isInteger(+k) && +k >= 0 && +k < o.moves.length && Number.isFinite(v) && v >= 0 && v <= 16));
            assert.equal(result.values[row.target], Math.max(...Object.values(result.values)));
            assert.equal(result.winEstimate, result.values[row.target] / 16);
        }
        totals.decisions++;
        totals.evaluations += result.evaluations;
        const phase = o.moves.some(m => m.name === 'Build') ? 'building'
            : o.moves.some(m => m.name === 'Bid') ? 'bid' : 'plant';
        assert(o.moves.some(m => ['Build', 'Bid', 'ChoosePowerPlant'].includes(m.name)));
        if (!groups.has(phase)) groups.set(phase, []);
        groups.get(phase).push(i);
    }
    const selected = [...new Set([...groups.values()].flatMap(ix => [ix[0], ix.at(-1)]))].sort((a,b) => a-b);
    for (const i of selected) {
        const row = rows[i];
        assert.deepEqual(search.choose(row.request.state, row.request.player, row.teacher.options), row.teacher.result);
    }
    return { rows: rows.length, totals, public_replays: selected,
        phase_rows: Object.fromEntries([...groups].map(([phase, ix]) => [phase, ix.length])),
        public_inputs_and_targets_verified: true, qualification_eligible: false };
}

module.exports = { verify };
if (require.main === module) {
    const [runtime, input, contract, output] = process.argv.slice(2);
    assert(!fs.existsSync(output));
    const rows = fs.readFileSync(input, 'utf8').trim().split('\n').filter(Boolean).map(JSON.parse);
    const result = verify(path.resolve(runtime), rows, JSON.parse(fs.readFileSync(contract, 'utf8')));
    fs.writeFileSync(output, JSON.stringify(result, null, 2) + '\n', { flag: 'wx' });
    console.log(JSON.stringify(result));
}
