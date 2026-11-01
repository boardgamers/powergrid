import type { GameState, PowerPlant } from './gamestate';

/** The Recharged discount also applies when deciding whether a plant can be nominated. */
export function minimumPlantBid(G: GameState, plant: PowerPlant): number {
    return G.options.variant === 'recharged' && G.plantDiscountActive && plant.number === G.actualMarket[0]?.number
        ? 1
        : // The shuffled decks number extra copies 46.1, 46.2: bids start at the printed number.
          Math.floor(plant.number);
}
