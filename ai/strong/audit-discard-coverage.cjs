// Read-only coverage audit of the current search/teacher decision gate.
const fs = require('node:fs'), crypto = require('node:crypto'), assert = require('node:assert/strict');
const c = require('../core.cjs'), eco = require('./economics.cjs'), search = require('./search.cjs');
const file = process.argv[2], output = process.argv[3];
assert(file && output, 'Supply serving-fixtures.jsonl and output.json');
const digest = f => crypto.createHash('sha256').update(fs.readFileSync(f)).digest('hex');
for (const name of ['bridge.cjs', 'worker.cjs', 'search-teacher.cjs']) {
    assert(fs.readFileSync(__dirname + '/' + name, 'utf8').includes("['ChoosePowerPlant', 'Bid', 'Build'].includes"),
        'Search gate changed; update this audit before using it');
}
const report = { fixture_sha256: digest(file), positions: 0, discard_positions: 0,
    discard_strategic_search_positions: 0, by_player_count: {}, by_rules: {},
    default_shortlist_omissions: 0, geographic_shortlist_omissions: 0,
    imminent_discard_positions: 0, source_hashes: {},
    scope: 'Read-only coverage of the existing serving fixtures. This corpus is not a prevalence estimate for deployed play. PPO still updates discard decisions; the current search teacher and search-enhanced serving route do not search them.',
    qualification_eligible: false };
for (const line of fs.readFileSync(file, 'utf8').trim().split('\n')) {
    const q = JSON.parse(line).request, g = q.state, seat = q.player, legal = c.candidates(g, seat);
    report.positions++;
    if (!legal.some(a => a.name === 'DiscardPowerPlant')) continue;
    assert(legal.every(a => a.name === 'DiscardPowerPlant'));
    report.discard_positions++;
    report.discard_strategic_search_positions += +(legal.length > 1 && legal.some(a => ['ChoosePowerPlant', 'Bid', 'Build'].includes(a.name)));
    const n = g.players.length, rules = g.options.variant + (g.options.fastBid ? '/sealed' : '/open');
    report.by_player_count[n] = (report.by_player_count[n] || 0) + 1;
    report.by_rules[rules] = (report.by_rules[rules] || 0) + 1;
    report.default_shortlist_omissions += +(search.shortlist(g, seat, 5, false).length < legal.length);
    report.geographic_shortlist_omissions += +(search.shortlist(g, seat, 6, true).length < legal.length);
    report.imminent_discard_positions += +eco.context(g, seat).imminent;
}
for (const name of ['bridge.cjs', 'worker.cjs', 'search-teacher.cjs', 'search.cjs', 'economics.cjs'])
    report.source_hashes['ai/strong/' + name] = digest(__dirname + '/' + name);
fs.writeFileSync(output, JSON.stringify(report, null, 2) + '\n');
console.log({ positions: report.positions, discards: report.discard_positions, searched: report.discard_strategic_search_positions });
