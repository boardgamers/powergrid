const fs = require('node:fs'),
    { parseEnv } = require('node:util'),
    { createRequire } = require('node:module'),
    { createHash } = require('node:crypto');
const { MongoClient } = createRequire('/home/bgs/boardgamers-mono/apps/api/package.json')('mongodb');
(async () => {
    const env = parseEnv(fs.readFileSync('/home/bgs/boardgamers-mono/apps/api/.env', 'utf8'));
    const c = await MongoClient.connect(env.dbUrl);
    try {
        for await (const g of c
            .db(env.dbName || 'bgs')
            .collection('games')
            .find(
                {
                    'game.name': 'powergrid',
                    status: 'ended',
                    'game.options.map': 'Germany',
                    'options.setup.nbPlayers': 3,
                    'options.meta.unlisted': { $ne: true },
                },
                { projection: { _id: 1, game: 1, options: 1, data: 1, players: 1 } }
            )
            .maxTimeMS(20000)) {
            const d = g.data;
            if (!d || typeof d !== 'object') continue;
            const cleanPlayer = (p) => ({
                money: p.money,
                citiesPowered: p.citiesPowered,
                cities: p.cities?.map((c) => c.name).sort(),
                powerPlants: p.powerPlants?.map((p) => p.number).sort((a, b) => a - b),
            });
            console.log(
                JSON.stringify({
                    id: createHash('sha256')
                        .update('powergrid-ai-v1:' + g._id)
                        .digest('hex')
                        .slice(0, 20),
                    version: g.game.version,
                    options: d.options || g.game.options,
                    seed: d.seed || g.options.setup.seed,
                    players: g.players.map((p) => ({
                        bot: !!p.isBot,
                        dropped: !!p.dropped,
                        quit: !!p.quit,
                        rating: p.elo?.initial,
                        ranking: p.ranking,
                    })),
                    moves: (d.log || [])
                        .filter((x) => x.type === 'move')
                        .map((x) => ({ player: x.player, move: x.move })),
                    final: d.players.map(cleanPlayer),
                    phase: d.phase,
                    round: d.round,
                })
            );
        }
    } finally {
        await c.close();
    }
})().catch((e) => {
    console.error(e.name, e.code);
    process.exit(1);
});
