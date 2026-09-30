const c = require('../core.cjs'),
    eco = require('./economics.cjs');
const counts = process.env.MULTIPLAYER === '1' ? [2, 3, 4, 5, 6] : [3];
for (const n of counts)
    for (let game = 0; game < 4; game++) {
        const g = c.E.setup(
                n,
                { map: 'Germany', variant: game % 2 ? 'recharged' : 'original', fastBid: game < 2, showMoney: true },
                'strong-serving-' + game
            ),
            rng = c.seedrandom('strong-serving-ties-' + game);
        let step = 0;
        while (!c.E.ended(g) && step < 1600) {
            const player = g.currentPlayers[0];
            if (step % 4 === 0)
                console.log(
                    JSON.stringify({
                        request: { state: g, player, requestId: `${n}p-${game}-${step}`, revision: step },
                        legal: c.candidates(g, player),
                    })
                );
            c.E.move(g, eco.choose(g, player, rng).action, player);
            step++;
        }
        if (!c.E.ended(g)) throw Error('Fixture game did not finish');
    }
