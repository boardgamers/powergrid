'use strict';
// Fresh, bounded ENGINEERING positions. No frozen study roots/replays or strength outcomes.
const { loadIdentity, cloneState, requireThat } = require('./identity.cjs');
loadIdentity();
const f = require('../multimap/features.cjs');
const teacher = require('../multimap/teacher_v2.cjs');
const { inputs } = require('../multimap/expert_game.cjs');
const NAMESPACE = 'pg-serving-prototype-v1';
const MAPS = ['Germany', 'USA', 'France', 'UK & Ireland'];
function makeFixtures() {
    const result = [];
    for (const [mi, map] of MAPS.entries())
        for (const [ci, [variant, fastBid]] of [
            ['original', false],
            ['original', true],
            ['recharged', false],
            ['recharged', true],
        ].entries()) {
            const players = [2, 3, 4, 5, 6][(mi + ci) % 5];
            const g = f.E.setup(
                players,
                { map, variant, fastBid, showMoney: true },
                `${NAMESPACE}:fixture:${mi}:${ci}`
            );
            const seen = new Set();
            for (let step = 0; step < 800 && !f.E.ended(g) && seen.size < 6; step++) {
                const player = g.currentPlayers[0],
                    legal = f.legal(g, player);
                const kind =
                    legal.length === 1
                        ? 'forced'
                        : legal.some((m) => m.name === 'ChoosePowerPlant')
                        ? 'nomination'
                        : legal.some((m) => m.name === 'Bid')
                        ? 'bid'
                        : g.phase;
                if (
                    g.newTurn !== false &&
                    ['forced', 'nomination', 'bid', 'Building', 'Resources', 'Bureaucracy'].includes(kind) &&
                    !seen.has(kind)
                ) {
                    seen.add(kind);
                    result.push({
                        id: `${mi}-${ci}-${kind}`,
                        map,
                        players,
                        variant,
                        fastBid,
                        kind,
                        player,
                        state: cloneState(g),
                        observation: legal.length > 1 ? inputs(g, player) : null,
                    });
                }
                f.E.move(g, cloneState(teacher.choose(g, player, legal, 'geographic').action), player);
            }
            requireThat(
                ['nomination', 'bid', 'Building', 'Resources', 'Bureaucracy'].every((kind) => seen.has(kind)),
                'fixture-coverage'
            );
        }
    requireThat(result.length <= 96, 'fixture-count');
    return result;
}
module.exports = { makeFixtures, NAMESPACE };
if (require.main === module) {
    const fixtures = makeFixtures();
    // Only public tensors and scope metadata leave this process; never authoritative states or action payloads.
    process.stdout.write(
        JSON.stringify({
            schema: 'pg-serving-engineering-fixtures-v1',
            namespace: NAMESPACE,
            fixtures: fixtures.filter((x) => x.observation).map(({ state, player, ...publicFields }) => publicFields),
        }) + '\n'
    );
}
