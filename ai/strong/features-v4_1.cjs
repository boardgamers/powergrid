// Append-only schema 4.1: all five held plants and capacity-aware auction cues.
const base = require('./features-v4.cjs'), eco = require('./economics-v4_1.cjs');
const FEATURE_REVISION = '4.1-five-plants', STATE_DIM = 1215, ACTION_DIM = 100;
function extras(g, playerOrder) {
    return Array.from({length: 6}, (_, i) => {
        const p = g.players[playerOrder[i]], pp = p?.powerPlants[4];
        if (p?.powerPlants.length > 5) throw Error('Schema 4.1 supports at most five held plants');
        return pp ? [pp.number / 50, pp.cost / 4, pp.citiesPowered / 8,
            ...Array.from({length: 7}, (_, type) => +(pp.type === type)),
            +p.powerPlantsNotUsed.includes(pp.number)] : Array(11).fill(0);
    }).flat();
}
function extend(g, observation) {
    return {...observation, state: [...observation.state, ...extras(g, observation.playerOrder)],
        layout: {...observation.layout, extraPlayer: 11}};
}
function observe(g, seat, geometry) {
    return extend(g, base.observe(g, seat, geometry));
}
function encode(g, seat) {
    const x = extend(g, base.encode(g, seat));
    const affected = g.players.length === 2 && g.players[seat].powerPlants.length === 3 &&
        x.moves.some(a => a.name === 'ChoosePowerPlant' || a.name === 'Bid');
    const raw = affected ? eco.scores(g, seat, x.moves) : null, best = raw ? Math.max(...raw) : null;
    // Retain the old prior/teacher and action prefix. New cues are learned inputs,
    // not a forced residual prior or purported expert supervision.
    return {...x, featureRevision: FEATURE_REVISION,
        actions: x.actions.map((row, i) => [...row,
            raw ? Math.max(-10, Math.min(10, raw[i] / 10)) : row[74], raw ? +(raw[i] === best) : row[75]])};
}
module.exports = {SCHEMA: 4, FEATURE_REVISION, STATE_DIM, ACTION_DIM, MAX_PLAYERS: 6, observe, encode};
