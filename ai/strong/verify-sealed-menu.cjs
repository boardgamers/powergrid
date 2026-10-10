// Preserve old encoder output; give the new menu its own engine-legal fixtures.
const fs = require('node:fs'), readline = require('node:readline'), assert = require('node:assert/strict'),
    crypto = require('node:crypto'), core = require('../core.cjs'), base = require('./features-v4.cjs'),
    full = require('./features-v4_sealed.cjs'), encoders = require('./encoders.cjs');
async function main() {
    const [input, reference, output] = process.argv.slice(2),
        prior = fs.readFileSync(reference, 'utf8').trim().split('\n'), fd = fs.openSync(output, 'w'),
        requests = crypto.createHash('sha256');
    const stats = {positions: 0, changed_legal_lists: 0, expanded_sealed_menus: 0,
        omitted_actions_engine_replayed: 0, by_player_count: {},
        old_encoder_exact: true, old_actor_menus_exact: true, open_encoder_exact: true,
        hidden_information_invariant: true, identical_requests: true};
    try {
        for await (const line of readline.createInterface({input: fs.createReadStream(input)})) {
            const fixture = JSON.parse(line), q = fixture.request, g = q.state, seat = q.player,
                old = base.encode(g, seat), expanded = full.encode(g, seat), legal = core.allLegal(g, seat);
            assert.deepEqual(old, JSON.parse(prior[stats.positions]));
            assert.deepEqual(encoders.candidatesForRevision('4.0-multiplayer', g, seat), old.moves);
            assert.deepEqual(encoders.candidatesForRevision(full.FEATURE_REVISION, g, seat), expanded.moves);
            assert.deepEqual(expanded.state, old.state);
            assert.deepEqual(fixture.legal, old.moves);
            if (!g.options.fastBid || legal.length === old.moves.length)
                assert.deepEqual({...expanded, featureRevision: old.featureRevision}, old);
            else {
                stats.expanded_sealed_menus++;
                assert.deepEqual(expanded.moves, legal);
                const kept = new Set(old.moves.map(x => JSON.stringify(x)));
                for (const action of legal.filter(x => !kept.has(JSON.stringify(x)))) {
                    assert.equal(action.name, 'Bid');
                    // Ask the authoritative engine to apply each added action on
                    // an independent copy; never continue or train on that copy.
                    core.E.move(structuredClone(g), action, seat);
                    stats.omitted_actions_engine_replayed++;
                }
            }
            const hidden = structuredClone(g);
            hidden.powerPlantsDeck.reverse(); hidden.seed = 'sealed-menu-hidden-test';
            hidden.automation = {plans: {0: {round: 99, phases: [{phase: 'Building', moves: [{name: 'Pass'}]}]}}};
            hidden.players.forEach(p => {p.queuedMoves = [{name: 'Pass'}]; if (g.options.fastBid) p.bid = 997;});
            if (g.options.fastBid) hidden.currentBid = 998;
            assert.deepEqual(full.encode(hidden, seat), expanded);
            stats.positions++;
            stats.by_player_count[g.players.length] = (stats.by_player_count[g.players.length] || 0) + 1;
            stats.changed_legal_lists += +(legal.length !== fixture.legal.length);
            requests.update(JSON.stringify(q) + '\n');
            fs.writeSync(fd, JSON.stringify({...fixture, legal}) + '\n');
        }
    } finally {fs.closeSync(fd);}
    assert.equal(stats.positions, prior.length);
    const hash = path => crypto.createHash('sha256').update(fs.readFileSync(path)).digest('hex');
    Object.assign(stats, {original_fixture_sha256: hash(input), reference_sha256: hash(reference),
        engine_legal_fixture_sha256: hash(output), request_stream_sha256: requests.digest('hex')});
    fs.writeFileSync(output + '.json', JSON.stringify(stats, null, 2) + '\n');
    console.log(JSON.stringify(stats));
}
main().catch(error => {console.error(error); process.exitCode = 1;});
