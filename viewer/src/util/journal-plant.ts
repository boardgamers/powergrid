import type { GameState } from 'powergrid-engine';
import { getPowerPlant } from 'powergrid-engine/src/engine';
import type { PowerPlant } from 'powergrid-engine/src/gamestate';

export function journalPlant(state: GameState, number: number): PowerPlant | undefined {
    const livePlant = [
        ...state.players.flatMap((player) => player.powerPlants),
        ...state.actualMarket,
        ...state.futureMarket,
    ].find((plant) => plant.number === number);
    if (livePlant) return livePlant;

    // Discarded cards still appear in the journal; reconstruct the regional deck
    // using the same region order as setup, without needing the hidden draw pile.
    let plant = getPowerPlant(number, state.map.name, !!state.options.alternatePowerPlants);
    for (const region of new Set(state.map.cities.map((city) => city.region))) {
        plant = state.map.regionalPowerPlants?.[region]?.find((card) => card.number === number) ?? plant;
    }
    return plant;
}
