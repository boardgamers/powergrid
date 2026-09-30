const c = require('./core.cjs'),
    readline = require('node:readline');
(async () => {
    for await (const line of readline.createInterface({ input: process.stdin })) {
        try {
            const q = JSON.parse(line),
                g = q.state,
                p = q.player;
            if (!Number.isInteger(p) || !g.currentPlayers.includes(p))
                throw Error('Player cannot act in this position');
            const moves = c.candidates(g, p);
            if (!moves.length) throw Error('No legal actions');
            console.log(
                JSON.stringify({
                    state: c.observe(g, p),
                    actions: moves.map((a) => c.actionFeatures(g, p, a)),
                    moves,
                    playerOrder: [p, (p + 1) % 3, (p + 2) % 3],
                })
            );
        } catch (e) {
            console.log(JSON.stringify({ error: e.message }));
        }
    }
})();
