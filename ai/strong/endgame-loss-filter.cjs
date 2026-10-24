// Experimental strict loss certificate, not wired into serving or evaluation.
// Germany ends after Building, before fuel is consumed. During this phase a
// player's fuel-supported output cannot rise, and opponents' existing fueled
// cities cannot fall. A strict output gap therefore avoids all money tie cases.
const {isDeepStrictEqual} = require('node:util');

function strictLossBound({phase, threshold, currentPlayer, cityCounts, fuelUpperBound, opponentLowerBound}) {
    if (phase !== 'Building' || !Number.isInteger(threshold) || threshold < 1 ||
        !Array.isArray(cityCounts) || cityCounts.length < 2 || cityCounts.length > 6 ||
        !Number.isInteger(currentPlayer) || currentPlayer < 0 || currentPlayer >= cityCounts.length ||
        cityCounts.some(n => !Number.isInteger(n) || n < 0) ||
        cityCounts.some(n => n >= threshold) || cityCounts[currentPlayer]+1 !== threshold ||
        !Number.isInteger(fuelUpperBound) || fuelUpperBound < 0 ||
        !Number.isInteger(opponentLowerBound) || opponentLowerBound < 0) return false;
    return fuelUpperBound < opponentLowerBound;
}

function createFilter(core, calculateMaxCitiesPowered) {
    return function certificate(g, seat, proposal) {
        if (g.map?.name !== 'Germany' || !['original', 'recharged'].includes(g.options?.variant) ||
            g.options.randomizeMap || g.options.chooseRegions || g.phase !== 'Building' ||
            !g.currentPlayers.includes(seat) || proposal?.name !== 'Build' ||
            !g.players[seat] || g.players.some(p => p.isDropped) ||
            g.players[seat].cities.length+1 !== g.citiesToEndGame ||
            g.players.some(p => p.cities.length >= g.citiesToEndGame)) return null;
        const legal = core.allLegal(g, seat);
        if (!legal.some(a => isDeepStrictEqual(a, proposal))) return null;
        const replacement = legal.find(a => a.name === 'Pass' && a.data === true);
        if (!replacement) return null;
        const player = g.players[seat];
        // Only the city-count cap is relaxed. Fuel, plants and game rules remain
        // exactly as observed. No deck, RNG, bid or future opponent move is read.
        const fuelUpperBound = calculateMaxCitiesPowered(g,
            {...player, cities: Array(core.capacity(player))});
        const opponentLowerBound = Math.max(...g.players.filter((_, i) => i !== seat)
            .map(p => calculateMaxCitiesPowered(g, p)));
        if (!strictLossBound({phase:g.phase, threshold:g.citiesToEndGame, currentPlayer:seat,
            cityCounts:g.players.map(p => p.cities.length), fuelUpperBound, opponentLowerBound})) return null;
        return {reason:'strict-fueled-output-loss', threshold:g.citiesToEndGame,
            fuelUpperBound, opponentLowerBound, replacement:{...replacement},
            qualification_eligible:false};
    };
}

module.exports = {strictLossBound, createFilter};
