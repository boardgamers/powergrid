const assert = require('node:assert/strict');
const { test } = require('node:test');
const { inputs, request } = require('./game_rl.cjs');
const { start } = require('./game.cjs');
const f = require('./features.cjs'),
    teacher = require('./teacher.cjs');
const protocol = require('./ppo-protocol-v1.json');
const spec = {
    map: 'Germany',
    players: 4,
    variant: 'recharged',
    fastBid: true,
    seed: 'multimap-rl-unit-v1',
    focalSeat: 0,
};

test('zero residual follows teacher for every supported cell, fixed phases are not exposed', () => {
    for (const map of f.MAPS)
        for (const players of protocol.players)
            for (const variant of protocol.variants)
                for (const fastBid of protocol.fastBids) {
                    const s = {
                        ...spec,
                        map,
                        players,
                        variant,
                        fastBid,
                        seed: `rl-parity-v1:${map}:${players}:${variant}:${fastBid}`,
                    };
                    let r = request({ op: 'start', spec: s });
                    while (!r.terminal) {
                        assert(protocol.learnedPhases.includes(r.phase));
                        assert.equal(r.observation.prior.length, r.observation.actions.length);
                        const prior = r.observation.prior;
                        assert(prior.every(Number.isFinite));
                        r = request({ op: 'step', index: prior.indexOf(Math.max(...prior)) });
                    }
                    const reference = request({ op: 'start', spec: { ...s, focalTeacher: true } });
                    assert.deepEqual(r, reference);
                }
});

test('prior uses public fields only throughout sealed-auction games', () => {
    const g = start(spec);
    let checked = 0;
    for (let step = 0; step < 150 && !f.E.ended(g); step++) {
        const seat = g.currentPlayers[0],
            moves = f.legal(g, seat);
        if (protocol.learnedPhases.includes(g.phase) && moves.length > 1 && step % 3 === 0) {
            const before = inputs(g, seat),
                hidden = structuredClone(g);
            hidden.seed = 'poison';
            hidden.powerPlantsDeck.reverse();
            hidden.log = [];
            hidden.powerPlantDeckAfterStep3 = [{ number: 777 }];
            hidden.hiddenLog = ['poison'];
            hidden.poweringChoices = {};
            hidden.automation = {};
            hidden.currentBid = 777;
            for (const p of hidden.players) {
                p.bid = 999;
                p.lastMove = { secret: true };
            }
            assert.deepEqual(inputs(hidden, seat), before);
            checked++;
        }
        f.E.move(g, structuredClone(teacher.choose(g, seat, moves).action), seat);
    }
    assert(checked > 10);
});

test('retain every legal bid and reject malformed RL setup/actions', () => {
    const g = start(spec);
    g.players[0].availableMoves = { Bid: Array.from({ length: 501 }, (_, i) => i) };
    g.currentPlayers = [0];
    assert.equal(inputs(g, 0).prior.length, 501);
    assert.throws(() => request({ op: 'start', spec: { ...spec, variant: 'Original' } }));
    request({ op: 'start', spec });
    assert.throws(() => request({ op: 'step', index: -1 }));
});
