// Research-only stateless sampling anchor. Requires the canonical public log.
// Historical adapters stay unchanged. This does not choose or execute a move.
const assert = require('node:assert/strict');
const path = require('node:path');
const {isDeepStrictEqual} = require('node:util');
const REVISION = 'resource-turn-public-history-anchor-v1';
const clone = value => structuredClone(value);

function createResourceTurnAnchor(runtimeDirectory) {
    const runtime = path.resolve(runtimeDirectory);
    const c = require(path.join(runtime, 'ai/core.cjs'));
    const {publicRoot} = require(path.join(runtime, 'ai/strong/resource-turn-search-v1.cjs'));
    const {preparePolicy} = require(path.join(runtime, 'ai/strong/population-hybrid-policy.cjs'));
    const ownBuy = (entry, seat) => entry?.type === 'move' && entry.player === seat && entry.move?.name === 'BuyResource';

    function prepare(request) {
        const current = publicRoot(request), seat = request.player, anchor = clone(current);
        assert(Array.isArray(anchor.log) && anchor.log.length > 0, 'Complete canonical public history required');
        assert.equal(typeof anchor.newTurn, 'boolean', 'Turn-boundary metadata required');
        const purchases = [];
        while (ownBuy(anchor.log.at(-1), seat)) {
            const entry = anchor.log.pop(), move = entry.move, resource = move.data?.resource;
            assert(c.RES.includes(resource), 'Unsupported resource in public history');
            assert.deepEqual(Object.keys(move.data), ['resource'], 'Only standard Germany market purchases');
            assert(!move.fromSupply, 'Supply purchases are outside the Germany anchor scope');
            const marketKey = resource + 'Market', heldKey = resource + 'Left';
            const prices = anchor[resource + 'Prices'], player = anchor.players[seat];
            const index = prices.length - anchor[marketKey] - 1;
            assert(Number.isInteger(index) && index >= 0 && index < prices.length, 'Market cannot be rewound');
            const price = prices[index];
            assert(Number.isInteger(price) && price > 0 && player[heldKey] > 0, 'Invalid purchase history');
            player[heldKey]--;
            anchor[marketKey]++;
            player.money += price;
            if (anchor.options.trackTotalSpent) {
                assert(Number.isInteger(player.totalSpentResources) && player.totalSpentResources >= price);
                player.totalSpentResources -= price;
            }
            purchases.unshift({move: clone(move), price});
        }
        assert(anchor.log.length > 0, 'History is missing the resource-turn boundary');
        assert.equal(current.newTurn, purchases.length === 0, 'Purchase history and turn boundary disagree');
        if (purchases.length) {
            anchor.newTurn = true;
            // Germany retains this field across turns. Recover the preceding
            // public purchase rather than borrowing this turn's last resource.
            const previous = anchor.log.findLast(entry => entry.type === 'move' && entry.move?.name === 'BuyResource');
            if (previous) anchor.chosenResource = previous.move.data.resource;
            else delete anchor.chosenResource;
        }
        anchor.players[seat].availableMoves = c.E.availableMoves(anchor, anchor.players[seat]);
        const prepared = preparePolicy({...request, state: anchor});

        // Check the inverse against forward engine transitions and the actual
        // current observation/menu. This also rejects impossible logged buys.
        const replay = clone(anchor), metadata = {cardsLeft: current.cardsLeft, nextCardWeak: current.nextCardWeak};
        for (const purchase of purchases) {
            const action = {name: purchase.move.name, data: clone(purchase.move.data)};
            assert(c.allLegal(replay, seat).some(move => isDeepStrictEqual(move, action)), 'Illegal reconstructed purchase');
            const before = replay.players[seat].money;
            c.E.move(replay, clone(purchase.move), seat);
            Object.assign(replay, metadata);
            assert.equal(before - replay.players[seat].money, purchase.price);
            assert.equal(replay.phase, 'Resources');
            assert.deepEqual(replay.currentPlayers, [seat]);
        }
        assert.deepEqual(preparePolicy({...request, state: replay}), preparePolicy({...request, state: current}),
            'Reconstructed turn does not reproduce the current public observation');
        for (const resource of c.RES) {
            assert.equal(replay[resource + 'Market'], current[resource + 'Market']);
            assert.equal(replay.players[seat][resource + 'Left'], current.players[seat][resource + 'Left']);
        }
        assert.equal(replay.players[seat].money, current.players[seat].money);
        assert.equal(replay.players[seat].totalSpentResources, current.players[seat].totalSpentResources);
        return {...prepared, resourceTurnAnchor: {
            revision: REVISION, round: anchor.round, step: anchor.step, player: seat,
            purchasesRewound: purchases.length, costRewound: purchases.reduce((sum, p) => sum + p.price, 0),
            boundaryLogLength: anchor.log.length, historyRequired: 'complete-canonical-public-log',
            qualification_eligible: false,
        }};
    }
    return {prepare};
}

module.exports = {revision: REVISION, createResourceTurnAnchor};
