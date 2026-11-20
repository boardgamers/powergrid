import type { GameState, Move, Player } from 'powergrid-engine';
import { move as applyMove, MoveName } from 'powergrid-engine';
import { alpineCitiesOwned, alpineEligible } from 'powergrid-engine/src/available-moves';
import { isUraniumMine, Phase } from 'powergrid-engine/src/gamestate';

/**
 * Every fuel-free plant, each move taken from the engine's offer AFTER the previous one is applied: an offer can
 * change once another plant fires (SwitzerlandCustom's Alpine +1 is shared out among the green plants).
 */
export function freePlantMoves(state: GameState, seat: number): Move[] {
    if (state.phase !== Phase.Bureaucracy || !state.currentPlayers.includes(seat)) return [];
    const moves: Move[] = [];
    let current = state;
    for (;;) {
        const data = (current.players[seat].availableMoves?.UsePowerPlant || []).find(
            (offer) => offer.resourcesSpent.length === 0
        );
        if (!data) return moves;
        const action: Move = { name: MoveName.UsePowerPlant, data };
        moves.push(action);
        // The engine changes the state it is given: work on a copy, never the live game.
        current = applyMove(JSON.parse(JSON.stringify(current)), action, seat);
        if (current.phase !== Phase.Bureaucracy || !current.currentPlayers.includes(seat)) return moves;
    }
}

export function poweredCities(state: GameState, player: Player): number {
    // Pass resets citiesPowered; the used cards keep the result visible until the next round.
    const used = player.powerPlants.filter(
        (plant) => !isUraniumMine(state, plant) && !player.powerPlantsNotUsed.includes(plant.number)
    );
    const output =
        used.reduce((total, plant) => total + plant.citiesPowered, 0) +
        // SwitzerlandCustom: +1 per green plant used, up to the Alpine cities owned.
        Math.min(alpineCitiesOwned(state, player), used.filter(alpineEligible).length);
    return Math.min(player.cities.length, output);
}

export function canAutoFinishPowering(state: GameState, seat: number): boolean {
    if (state.phase !== Phase.Bureaucracy || !state.currentPlayers.includes(seat)) return false;
    const player = state.players[seat];
    return (
        !!player.availableMoves?.Pass &&
        (player.citiesPowered >= player.cities.length || !player.availableMoves.UsePowerPlant?.length)
    );
}
