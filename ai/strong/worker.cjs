const encoders = require('./encoders.cjs'),
    readline = require('node:readline');
(async () => {
    for await (const line of readline.createInterface({ input: process.stdin })) {
        try {
            const q = JSON.parse(line),
                g = q.state,
                p = q.player;
            if (!Number.isInteger(p) || !g.currentPlayers.includes(p)) throw Error('Player cannot act');
            const x = encoders.forRevision(q.featureRevision).encode(g, p);
            if (q.op === 'search') {
                if (!Number.isInteger(q.proposal) || q.proposal < 0 || q.proposal >= x.moves.length)
                    throw Error('Invalid search proposal');
                if (!Number.isInteger(q.samples) || q.samples < 1 || q.samples > 64)
                    throw Error('Search samples must be 1..64');
                const strategic =
                    x.moves.length > 1 && x.moves.some((a) => ['ChoosePowerPlant', 'Bid', 'Build'].includes(a.name));
                const result = strategic
                    ? require('./search.cjs').choose(g, p, {
                          samples: q.samples,
                          candidates: 6,
                          extraCandidates: [q.proposal],
                          geography: !!q.geography,
                          seed: 'serving-' + (q.requestId || 'public'),
                      })
                    : { index: q.proposal, action: x.moves[q.proposal], evaluations: 0 };
                console.log(JSON.stringify(result));
                continue;
            }
            console.log(JSON.stringify({ ...x, playerOrder: [p, (p + 1) % 3, (p + 2) % 3] }));
        } catch (e) {
            console.log(JSON.stringify({ error: e.message }));
        }
    }
})();
