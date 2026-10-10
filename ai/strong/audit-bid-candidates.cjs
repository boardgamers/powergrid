// Read-only candidate coverage audit. Heuristic scores are not optimal-action labels.
const fs = require('node:fs'), readline = require('node:readline'), crypto = require('node:crypto'),
    assert = require('node:assert/strict'), core = require('../core.cjs'),
    economic = require('./economics.cjs'), corrected = require('./economics-v4_1.cjs');
const hash = path => crypto.createHash('sha256').update(fs.readFileSync(path)).digest('hex');
async function main() {
    const [input, output] = process.argv.slice(2), rows = [], cells = {};
    let positions = 0;
    for await (const line of readline.createInterface({input: fs.createReadStream(input)})) {
        const fixture = JSON.parse(line), {state: g, player: seat} = fixture.request;
        positions++;
        const all = core.allLegal(g, seat), kept = core.candidates(g, seat),
            allKeys = new Set(all.map(a => JSON.stringify(a))), keptKeys = new Set(kept.map(a => JSON.stringify(a))),
            bids = all.filter(a => a.name === 'Bid'), omitted = all.filter(a => !keptKeys.has(JSON.stringify(a)));
        assert.ok(kept.every(a => allKeys.has(JSON.stringify(a))));
        assert.ok(omitted.every(a => a.name === 'Bid'), 'Unexpected non-bid pruning');
        if (!bids.length) continue;
        const key = `${g.players.length}p/${g.options.variant}/${g.options.fastBid ? 'sealed' : 'open'}`;
        const cell = cells[key] ||= {positions: 0, pruned_positions: 0, legal_bids: 0,
            omitted_bids: 0, old_best_all_omitted: 0, corrected_best_all_omitted: 0};
        cell.positions++; cell.pruned_positions += +(omitted.length > 0);
        cell.legal_bids += bids.length; cell.omitted_bids += omitted.length;
        if (!omitted.length) continue;
        const before = JSON.stringify(g), comparisons = {};
        for (const [name, policy] of [['old', economic], ['corrected', corrected]]) {
            const scores = policy.scores(g, seat, all), best = Math.max(...scores),
                retainedBest = Math.max(...scores.filter((_, i) => keptKeys.has(JSON.stringify(all[i])))),
                lost = best > retainedBest;
            cell[name + '_best_all_omitted'] += +lost;
            comparisons[name] = {best_all_omitted: lost, heuristic_score_gap: best - retainedBest,
                preferred_legal_moves: all.filter((_, i) => scores[i] === best)};
        }
        assert.equal(JSON.stringify(g), before);
        rows.push({fixture_position: positions - 1, key, round: g.round,
            seat, money: g.players[seat].money, legal_bids: bids.length,
            kept_bids: kept.filter(a => a.name === 'Bid').map(a => a.data),
            omitted_bids: omitted.length, comparisons});
    }
    const report = {positions, fixture_sha256: hash(input), cells,
        pruned_positions: rows.length, rows,
        runtime_sha256: Object.fromEntries(['../core.cjs', './economics.cjs', './economics-v4_1.cjs'].map(p => [p, hash(require.resolve(p))])),
        all_nonbid_actions_retained: true, all_states_unchanged: true,
        interpretation: 'Coverage of the fixed serving fixture corpus, not a representative frequency estimate. Missing heuristic-preferred bids are a candidate-generation limitation, not proof of a better legal move or playing-strength gain. No training, encoder, baseline, or active experiment was changed.',
        qualification_eligible: false};
    fs.writeFileSync(output, JSON.stringify(report, null, 2) + '\n');
    console.log(JSON.stringify({positions, pruned_positions: rows.length, cells}));
}
main().catch(error => {console.error(error); process.exitCode = 1;});
