// Append public auction pricing; the parent menu, priors and feature prefix stay intact.
const FEATURE_REVISION = '4.4-auction-discount', STATE_DIM = 1218, ACTION_DIM = 103;

function openingBid(g, plant) {
    return g.options.variant === 'recharged' && g.plantDiscountActive &&
        plant.number === g.actualMarket[0]?.number ? 1 : plant.number;
}

function extend(g, parent) {
    if (typeof g.plantDiscountActive !== 'boolean')
        throw Error('Schema 4.4 requires the public plantDiscountActive flag');
    if (parent.featureRevision !== '4.3-strategic-correction' || parent.state.length !== 1217 ||
        parent.actions.length !== parent.moves.length || parent.actions.some(a => a.length !== 101))
        throw Error('Schema 4.4 requires an unchanged schema 4.3 parent');
    return {...parent, featureRevision: FEATURE_REVISION,
        state: [...parent.state, +g.plantDiscountActive],
        actions: parent.actions.map((a, i) => {
            const move = parent.moves[i];
            if (move.name !== 'ChoosePowerPlant') return [...a, 0, 0];
            const plant = g.actualMarket.find(p => p.number === move.data);
            if (!plant) throw Error('Nominated plant absent from the actual market');
            const price = openingBid(g, plant);
            // Opening bid is not an immediate purchase cost or the eventual winning bid.
            return [...a, price / 50, (plant.number - price) / 50];
        })};
}

function encode(g, seat) {
    return extend(g, require('./features-v4_3.cjs').encode(g, seat));
}

module.exports = {SCHEMA: 4, FEATURE_REVISION, STATE_DIM, ACTION_DIM, MAX_PLAYERS: 6,
    openingBid, extend, encode};
