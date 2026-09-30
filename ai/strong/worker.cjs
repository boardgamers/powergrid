const f = require('./features.cjs'),
    readline = require('node:readline');
(async () => {
    for await (const line of readline.createInterface({ input: process.stdin })) {
        try {
            const q = JSON.parse(line),
                g = q.state,
                p = q.player;
            if (!Number.isInteger(p) || !g.currentPlayers.includes(p)) throw Error('Player cannot act');
            const x = f.encode(g, p);
            console.log(JSON.stringify({ ...x, playerOrder: [p, (p + 1) % 3, (p + 2) % 3] }));
        } catch (e) {
            console.log(JSON.stringify({ error: e.message }));
        }
    }
})();
