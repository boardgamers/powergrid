// Validate every captured input/target; replay deterministic representative calls.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {publicExample} = require('./capture-reference-opponent-v1.cjs');
const runtime = path.resolve(process.argv[2]);
const file = path.resolve(process.argv[3]);
const output = path.resolve(process.argv[4]);
assert(!fs.existsSync(output));
const search = require(path.join(runtime, 'ai/strong/search.cjs'));
const rows = fs.readFileSync(file, 'utf8').trim().split('\n').filter(Boolean).map(JSON.parse);
assert(rows.length > 0);
const totals = {decisions:0, evaluations:0, truncated:0};
const groups = new Map();
for (const [i, row] of rows.entries()) {
    assert.equal(row.ordinal, i);
    assert.equal(row.qualification_eligible, false);
    const example = publicExample(runtime, row.request.state, row.request.player);
    for (const [key, value] of Object.entries(example)) assert.deepEqual(row[key], value);
    const options = row.teacher.options, result = row.teacher.result;
    assert.equal(options.samples, 16);
    assert.equal(options.candidates, 6);
    assert.equal(options.geography, true);
    assert.equal(options.maxSteps ?? 2400, 2400);
    assert.equal(options.continuation ?? 'mixed', 'mixed');
    assert.equal(row.target, result.index);
    assert.deepEqual(row.observation.moves[row.target], result.action);
    assert.equal(result.truncated || 0, 0);
    totals.decisions++;
    totals.evaluations += result.evaluations || 0;
    totals.truncated += result.truncated || 0;
    const kind = row.observation.moves.some(m => m.name === 'Build') ? 'building'
        : row.observation.moves.some(m => m.name === 'Bid') ? 'bid' : 'plant';
    if (!groups.has(kind)) groups.set(kind, []);
    groups.get(kind).push(i);
}
const selected = [...new Set([...groups.values()].flatMap(indices => [indices[0], indices.at(-1)]))].sort((a,b)=>a-b);
for (const i of selected) {
    const row = rows[i];
    const result = search.choose(row.request.state, row.request.player, row.teacher.options);
    assert.deepEqual(result, row.teacher.result, `Public teacher replay differs at ${i}`);
}
const result = {rows: rows.length, totals, public_replays: selected,
    public_feature_and_menu_checks: rows.length, all_targets_legal:true,
    training_eligible:false, qualification_eligible:false};
fs.writeFileSync(output, JSON.stringify(result, null, 2) + '\n', {flag:'wx'});
console.log(JSON.stringify(result));
