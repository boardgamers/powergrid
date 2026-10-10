// Read-only root-game auction ledger. No deck, sealed bids or queued plans.
const fs = require('node:fs'), core = require('../core.cjs');
const roots = new WeakSet(), setup = core.E.setup, move = core.E.move;
const plant = p => p && ({number: p.number, type: p.type, cost: p.cost, capacity: p.citiesPowered});
function file() { return process.env.PG_TRACE_PATH + '.auctions.jsonl'; }
Object.defineProperty(core.E, 'setup', {configurable: true, enumerable: true, value: function (...args) {
    const state = setup(...args);
    roots.add(state);
    fs.writeFileSync(file(), '');
    return state;
}});
Object.defineProperty(core.E, 'move', {configurable: true, enumerable: true, value: function (state, action, seat) {
    if (roots.has(state) && state.phase === core.E.Phase.Auction) {
        const player = state.players[seat], bids = player.availableMoves?.Bid || [];
        fs.appendFileSync(file(), JSON.stringify({
            round: state.round, seat, action, sealed: !!state.options.fastBid,
            money: player.money, cities: player.cities.length, capacity: core.capacity(player),
            owned: player.powerPlants.map(plant), chosen: plant(state.chosenPowerPlant),
            market: state.actualMarket.map(plant),
            minimumLegalBid: bids.length ? Math.min(...bids) : null,
            maximumLegalBid: bids.length ? Math.max(...bids) : null,
            legalBidCount: bids.length,
            legalNominations: player.availableMoves?.ChoosePowerPlant || [],
            legalDiscards: player.availableMoves?.DiscardPowerPlant || [],
            opponents: state.players.filter(p => p.id !== seat).map(p => ({
                id: p.id, money: p.money, cities: p.cities.length,
                capacity: core.capacity(p), plants: p.powerPlants.map(plant),
            })),
        }) + '\n');
    }
    return move(state, action, seat);
}});
