import { PowerPlantDeck, SingleDeck } from './gamestate';

// Map rules that name plant numbers, per deck: the standard deck's from each map's
// rules, Deck 1's and Deck 2's from their map-changes sheets (2F-Spiele, 2024). The
// sheets are written for Recharged; Original games use the same numbers, except
// where The New Power Plants rulebook covers the Original edition itself.

type PerDeck<T> = Record<SingleDeck, T>;

const isShuffled = (deck: PowerPlantDeck): deck is 'shuffled' | 'shuffledUnique' =>
    deck == 'shuffled' || deck == 'shuffledUnique';

// The shuffled decks follow every deck's rule at once, for whichever copies were
// dealt: Deck 1's and Deck 2's copies are numbered n.1 and n.2 (see plantCopy).
function forDeck(table: PerDeck<number[]>, deck: PowerPlantDeck): number[] {
    if (!isShuffled(deck)) return table[deck];
    return [...table.standard, ...table.deck1.map((n) => n + 0.1), ...table.deck2.map((n) => n + 0.2)];
}

// Plants out of the game from the start. Manhattan's boxed Step 3 card is handled
// where its deck is built, and so is India's plant in the single decks (see
// plantCatalogue).
export function removedPlants(mapName: string, deck: PowerPlantDeck, numPlayers: number, variant: string): number[] {
    const fewPlayers = numPlayers <= 3;
    switch (mapName) {
        case 'France':
            // The New Power Plants rulebook: on France, simply remove plant 11.
            return forDeck({ standard: [13], deck1: variant == 'original' ? [11] : [10], deck2: [11] }, deck);
        case 'Russia':
            return forDeck({ standard: [6, 14], deck1: [6, 21], deck2: [5, 14] }, deck);
        case 'India':
            return isShuffled(deck) ? forDeck({ standard: [11], deck1: [8], deck2: [13] }, deck) : [];
        case 'Australia':
            return forDeck({ standard: [17], deck1: [19], deck2: [21] }, deck);
        case 'South Africa':
            return forDeck({ standard: [7], deck1: [7], deck2: [10] }, deck);
        case 'Spain & Portugal':
            // Held back until Step 2, then put on top of the deck.
            return spainStep2Plants(deck);
        case 'Bremen': {
            const table: PerDeck<number[]> = {
                standard: [11, 17, 23, 28, 34, 36, 38, 39, 46, ...(numPlayers <= 4 ? [31, 50] : [])],
                deck1: [8, 19, 24, 31, 37, 38, 42, 46, 50, ...(numPlayers <= 4 ? [34, 44] : [])],
                deck2: [13, 21, 32, 33, 34, 37, 38, 46, 50, ...(numPlayers <= 4 ? [22, 44] : [])],
            };
            return forDeck(table, deck);
        }
        case 'Manhattan':
            return fewPlayers
                ? forDeck({ standard: [20, 22, 37], deck1: [16, 28, 38], deck2: [22, 28, 36] }, deck)
                : [];
        case 'China': {
            const table: PerDeck<number[][]> = {
                standard: [
                    [3, 4, 9, 11, 16, 18, 20, 24, 30, 33, 46],
                    [3, 4, 11, 18, 24, 33, 46],
                    [3, 4, 33],
                ],
                deck1: [
                    [1, 2, 8, 12, 15, 22, 27, 28, 32, 36, 42],
                    [1, 2, 8, 15, 27, 32, 36],
                    [1, 2, 32],
                ],
                deck2: [
                    [3, 6, 10, 13, 17, 18, 25, 26, 31, 34, 35],
                    [3, 6, 13, 17, 26, 31, 35],
                    [3, 6, 31],
                ],
            };
            const column = fewPlayers ? 0 : numPlayers == 4 ? 1 : 2;
            return forDeck(
                { standard: table.standard[column], deck1: table.deck1[column], deck2: table.deck2[column] },
                deck
            );
        }
        default:
            return [];
    }
}

// Original edition: the plants placed on top of the deck, topmost first, once the
// eight smallest plants have opened the market. Plants not in the game are skipped.
// The shuffled decks don't stack every deck's top plants: they use the standard deck's.
export function originalTopPlants(mapName: string, deck: PowerPlantDeck): number[] {
    const table = ((): PerDeck<number[]> => {
        switch (mapName) {
            case 'France':
                // The nuclear plant comes up first; Deck 1's (08) already opens the market.
                return { standard: [11], deck1: [], deck2: [13] };
            case 'Brazil':
                // The low biogas plants that don't open the market follow the usual top plant.
                return { standard: [13, 14], deck1: [11], deck2: [13, 14] };
            case 'Quebec':
                return { standard: [13, 18, 22], deck1: [11, 15, 16], deck2: [11, 17, 24] };
            default:
                return { standard: [13], deck1: [11], deck2: [13] };
        }
    })();
    return table[isShuffled(deck) ? 'standard' : deck];
}

// Original Russia: the two plants shuffled into the top five cards, beneath the top
// plant; they are the two plants after the six-plant opening market. The shuffled
// decks take the 7th and 8th smallest dealt plants instead (see maps/russia.ts).
export const RUSSIA_ORIGINAL_NEXT_PLANTS: PerDeck<number[]> = { standard: [10, 11], deck1: [8, 9], deck2: [10, 11] };

// Recharged edition: plants that always open the market; the rest of its eight are
// drawn from the remaining plug cards.
export function rechargedMarketPlants(mapName: string, deck: PowerPlantDeck): number[] {
    switch (mapName) {
        case 'France':
            return forDeck({ standard: [11], deck1: [8], deck2: [13] }, deck);
        case 'Brazil':
            return forDeck({ standard: [6, 14], deck1: [6], deck2: [5, 14] }, deck);
        case 'Quebec':
            // The standard deck's Québec market is drawn from 03–10 plus 13 instead.
            return forDeck({ standard: [], deck1: [11, 15, 16], deck2: [11] }, deck);
        default:
            return [];
    }
}

// Recharged Québec: plants set aside and placed on top of the finished deck, topmost
// first. The standard deck puts them beneath one plug card; Deck 2 on the very top.
// The shuffled decks follow the rule's purpose instead (see maps/quebec.ts).
export const QUEBEC_RECHARGED_TOP_PLANTS: PerDeck<number[]> = { standard: [18, 22], deck1: [], deck2: [17, 24] };

// Spain & Portugal: the ecological plants held back until Step 2, then drawn first.
export const SPAIN_STEP_2_PLANTS: PerDeck<number[]> = {
    standard: [18, 22, 27],
    deck1: [15, 16, 26],
    deck2: [17, 24, 28],
};

// Every copy a game can hold back: in the shuffled decks, all three decks' plants.
export function spainStep2Plants(deck: PowerPlantDeck): number[] {
    return forDeck(SPAIN_STEP_2_PLANTS, deck);
}
