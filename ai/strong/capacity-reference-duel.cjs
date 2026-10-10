// No learning. Paired 2p games of the versioned capacity reference vs original economics.
const fs = require('node:fs'), crypto = require('node:crypto'),
    c = require('../core.cjs'), old = require('./economics.cjs'), corrected = require('./economics-v4_1.cjs');
const [protocolFile, output] = process.argv.slice(2), protocolBytes = fs.readFileSync(protocolFile),
    protocol = JSON.parse(protocolBytes), results = [];
let differingChoices = 0;
for (const deal of protocol.deal_offsets) for (let seat = 0; seat < 2; seat++)
    for (const variant of ['original', 'recharged']) for (const sealed of [false, true]) {
        const gameSeed = protocol.seed + '-' + deal,
            g = c.E.setup(2, {map: 'Germany', variant, fastBid: sealed, showMoney: true}, gameSeed),
            rng = c.seedrandom(gameSeed + '-bot');
        let steps = 0;
        while (!c.E.ended(g) && steps < 1600) {
            const player = g.currentPlayers[0], policy = player === seat ? corrected : old;
            // Compare deterministic score argmax without consuming the actual game RNG.
            if (player === seat && corrected.choose(g, player).index !== old.choose(g, player).index) differingChoices++;
            c.E.move(g, policy.choose(g, player, rng).action, player); steps++;
        }
        const truncated = !c.E.ended(g), value = truncated ? [0, 0] : c.outcome(g);
        results.push({gameSeed, seat, playerCount: 2, variant, sealed, steps, truncated, value,
            roles: [0, 1].map(p => p === seat ? 'learner' : 'economic'), win: value[seat], searchStats: {},
            final: g.players.map(p => ({money: p.money, cities: p.cities.length, capacity: c.capacity(p), powered: p.citiesPowered}))});
    }
if (results.some(r => r.truncated)) throw Error('Capacity reference duel truncated');
fs.writeFileSync(output, JSON.stringify({candidate: 'economic_capacity_v1', opponent: 'economic',
    protocol_sha256: crypto.createHash('sha256').update(protocolBytes).digest('hex'),
    seed: protocol.seed, games: results.length, truncated: 0, differingChoices, results}, null, 2) + '\n');
console.log(JSON.stringify({games: results.length, truncated: 0, differingChoices}));
