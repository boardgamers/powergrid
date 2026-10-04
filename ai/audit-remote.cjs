const fs = require('node:fs');
const { parseEnv } = require('node:util');
const { createRequire } = require('node:module');
const requireApi = createRequire('/home/bgs/boardgamers-mono/apps/api/package.json');
const { MongoClient } = requireApi('mongodb');
(async () => {
    const env = parseEnv(fs.readFileSync('/home/bgs/boardgamers-mono/apps/api/.env', 'utf8'));
    const client = await MongoClient.connect(env.dbUrl, { serverSelectionTimeoutMS: 10000 });
    try {
        const db = client.db(env.dbName || 'bgs');
        const c = db.collection('games');
        const counts = await c
            .aggregate(
                [
                    { $match: { 'game.name': 'powergrid' } },
                    {
                        $group: {
                            _id: {
                                version: '$game.version',
                                status: '$status',
                                map: '$game.options.map',
                                variant: '$game.options.variant',
                                players: '$options.setup.nbPlayers',
                            },
                            n: { $sum: 1 },
                        },
                    },
                ],
                { maxTimeMS: 20000 }
            )
            .toArray();
        const sample = await c.findOne(
            { 'game.name': 'powergrid', status: 'ended' },
            { projection: { data: 1, game: 1, options: 1, players: 1, status: 1 } }
        );
        console.log(
            JSON.stringify(
                {
                    counts,
                    sample: sample && {
                        dataType: typeof sample.data,
                        dataKeys: typeof sample.data === 'object' ? Object.keys(sample.data || {}) : undefined,
                        dataLength: typeof sample.data === 'string' ? sample.data.length : undefined,
                        game: sample.game,
                        playerFields: Object.keys(sample.players[0] || {}),
                        hasSeed: !!sample.options?.setup?.seed,
                    },
                },
                null,
                2
            )
        );
    } finally {
        await client.close();
    }
})().catch((e) => {
    console.error(e.name, e.code);
    process.exit(1);
});
