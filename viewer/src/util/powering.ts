import type { GameState, Move, Player } from 'powergrid-engine';
import { MoveName } from 'powergrid-engine';
import { isUraniumMine, Phase } from 'powergrid-engine/src/gamestate';

export function freePlantMoves(state: GameState, seat: number): Move[] {
    if (state.phase !== Phase.Bureaucracy || !state.currentPlayers.includes(seat)) return [];
    const player = state.players[seat];
    return (player.availableMoves?.UsePowerPlant || [])
        .filter((move) => move.resourcesSpent.length === 0)
        .map((data) => ({ name: MoveName.UsePowerPlant, data }));
}

export function poweredCities(state: GameState, player: Player): number {
    // Pass resets citiesPowered; the used cards keep the result visible until the next round.
    const output = player.powerPlants
        .filter((plant) => !isUraniumMine(state, plant) && !player.powerPlantsNotUsed.includes(plant.number))
        .reduce((total, plant) => total + plant.citiesPowered, 0);
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
