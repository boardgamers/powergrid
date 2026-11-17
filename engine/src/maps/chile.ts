// Chile, designed by Mike Isom (draft, in testing). The board itself is generated into chile-board.ts.
import { cloneDeep } from 'lodash';
import seedrandom from 'seedrandom';
import { PowerPlant, PowerPlantDeck, PowerPlantType, SingleDeck } from '../gamestate';
import { shuffle } from '../utils';
import { originalTopPlants, removedPlants } from './../deckChanges';
import { GameMap } from './../maps';
import { dealtCatalogue, isPlugPlant, plantCatalogue } from './../powerPlants';
import { chileCities, chileConnections, chileGates } from './chile-board';

/** No nuclear power in Chile: the standard deck's uranium plants are out of the game. Fusion plant 50 stays. */
export const chileRemovedPlants = [11, 17, 23, 28, 34, 39];
/**
 * The three largest ecological plants of each single deck, set aside at setup; they go on top of the draw stack when
 * Step 3 begins (smallest on top). Deck 1's 44 is fusion, not ecological.
 */
export const chileSetAsidePlants: Record<SingleDeck, number[]> = {
    standard: [33, 37, 44],
    deck1: [26, 32, 39],
    deck2: [31, 36, 44],
};

const isShuffledDeck = (deck: PowerPlantDeck) => deck == 'shuffled' || deck == 'shuffledUnique';

/**
 * The plants Chile sets aside from the plants dealt (uranium already out): each single deck's own three; with the
 * shuffled decks, the three largest ecological plants dealt, whichever deck they came from (all of them, when a
 * sampled deck deals three or fewer). Smallest first, the order they go on top of the deck.
 */
export function chileSetAsideFrom(dealt: PowerPlant[], deck: PowerPlantDeck): PowerPlant[] {
    if (!isShuffledDeck(deck)) {
        return chileSetAsidePlants[deck as SingleDeck].map((n) => dealt.find((pp) => pp.number == n)!);
    }
    return dealt
        .filter((pp) => pp.type == PowerPlantType.Wind)
        .sort((a, b) => a.number - b.number)
        .slice(-3);
}

/** Chile, Step 3 began: the set-aside plants, read back from the log's Step 3 event (smallest first). */
export function chileSetAsideFromLog(log: { type: string; event?: string }[]): number[] | undefined {
    for (const entry of log) {
        const match = /^Step 3: power plants ([\d., ]+) go on top of the deck\.$/.exec(entry.event ?? '');
        if (match) return match[1].split(', ').map(Number);
    }
    return undefined;
}

export const map: GameMap = {
    name: 'Chile',
    cities: chileCities,
    connections: chileConnections,
    step3Connections: chileGates,
    // The two northern regions, each holding a gate, are always in play.
    fixedRegions: ['brown', 'yellow'],
    // Viewer layout: the board (drawn at 2102 x 1795, Chile running down at 36 degrees) at 70%, turned to run left to
    // right across the middle, around the whole board's centre so it sits still whichever regions are in play. Plant
    // market along the top, player boards on the right, North and Central markets side by side underneath.
    layout: 'Landscape',
    adjustRatio: [0.7, 0.7],
    mapRotation: -36,
    mapRotationCenter: [736, 621],
    mapPosition: [50, -20],
    viewBox: [2010, 1100],
    playerBoardsPosition: [1650, 240],
    supplyPosition: [0, 830],
    roundInfoPosition: [1520, 900],
    // Central market (the engine's main market). [resource][players-2][step-1]. The Step 3 column is
    // the merged market's restock.
    resupply: [
        // Coal
        [
            [2, 3, 4],
            [3, 3, 4],
            [3, 4, 5],
            [3, 5, 4],
            [4, 6, 6],
        ],
        // Oil
        [
            [1, 1, 4],
            [1, 1, 4],
            [2, 1, 5],
            [2, 1, 5],
            [3, 1, 7],
        ],
        // Garbage
        [
            [1, 2, 4],
            [1, 2, 4],
            [2, 3, 5],
            [3, 3, 4],
            [3, 5, 6],
        ],
        // Uranium: none
        [
            [0, 0, 0],
            [0, 0, 0],
            [0, 0, 0],
            [0, 0, 0],
            [0, 0, 0],
        ],
    ],
    // North market, restocked first. It has no garbage, and it is gone in Step 3.
    resupplyNorth: [
        // Coal
        [
            [2, 3, 0],
            [1, 3, 0],
            [2, 3, 0],
            [2, 3, 0],
            [3, 4, 0],
        ],
        // Oil
        [
            [1, 1, 0],
            [1, 1, 0],
            [1, 1, 0],
            [2, 1, 0],
            [2, 1, 0],
        ],
        // Garbage: none
        [
            [0, 0, 0],
            [0, 0, 0],
            [0, 0, 0],
            [0, 0, 0],
            [0, 0, 0],
        ],
    ],
    // Central: 12 coal on [1,1,1,1,2,2,2,2] slots per price; 10 oil on spaces 4-8 and 4 garbage on spaces 7-8 of
    // 16-slot tracks. North: 12 coal on [2,2,2,2,1,1,1,1] slots and 8 oil filling an 8-slot track; no garbage track.
    // Markets fill from the expensive end. Supply: 24 each of coal, oil and garbage across both markets; no uranium.
    startingResources: [12, 10, 4, 0],
    startingResourcesNorth: [12, 8, 0],
    startingSupply: [24, 24, 24, 0],
    coalPrices: [1, 2, 3, 4, 5, 5, 6, 6, 7, 7, 8, 8],
    oilPrices: [1, 1, 2, 2, 3, 3, 4, 4, 5, 5, 6, 6, 7, 7, 8, 8],
    garbagePrices: [1, 1, 2, 2, 3, 3, 4, 4, 5, 5, 6, 6, 7, 7, 8, 8],
    coalPricesNorth: [1, 1, 2, 2, 3, 3, 4, 4, 5, 6, 7, 8],
    oilPricesNorth: [1, 2, 3, 4, 5, 6, 7, 8],
    garbagePricesNorth: [],
    // The deck without its uranium plants and the set-aside plants, built as usual except that no plants are removed
    // for the number of players.
    setupDeck(
        numPlayers: number,
        variant: string,
        rng: seedrandom.prng,
        powerPlantDeck: PowerPlantDeck = 'standard',
        _fusionEcological?: boolean,
        sampleShuffled?: boolean
    ) {
        const shuffled = isShuffledDeck(powerPlantDeck);
        const single = powerPlantDeck as SingleDeck;
        const removed = new Set(removedPlants('Chile', powerPlantDeck, numPlayers, variant));
        const dealt = cloneDeep(
            shuffled ? dealtCatalogue('Chile', powerPlantDeck, rng, sampleShuffled) : plantCatalogue('Chile', single)
        ).filter((pp) => !removed.has(pp.number));
        const setAsidePlants = chileSetAsideFrom(dealt, powerPlantDeck);
        let deck: PowerPlant[] = dealt.filter((pp) => !setAsidePlants.includes(pp));
        const step3 = deck.pop()!;
        let actualMarket: PowerPlant[];
        let futureMarket: PowerPlant[];

        if (variant == 'original') {
            const market = deck.splice(0, 8); // The eight smallest: 3-10 in the standard deck
            actualMarket = market.slice(0, 4);
            futureMarket = market.slice(4);
            // The smallest ecological plant left; each single deck names it (Deck 1's 10 opens in the deck, not on top).
            // A shuffled deck may have none left, and then nothing goes on top.
            const topNumber = shuffled
                ? deck.find((pp) => pp.type == PowerPlantType.Wind)?.number
                : originalTopPlants('Chile', single)[0];
            const topIndex = deck.findIndex((pp) => pp.number == topNumber);
            const top = topIndex >= 0 ? deck.splice(topIndex, 1) : [];
            deck = shuffle(deck, rng() + '');
            deck.unshift(...top);
        } else {
            // The plug-back plants (3-15 in the standard deck, 12 of them without 11): eight open the market, one
            // goes on top of the deck and the rest are shuffled into it.
            const initial = shuffle(
                deck.filter((pp) => isPlugPlant(pp, powerPlantDeck)),
                rng() + ''
            );
            deck = deck.filter((pp) => !isPlugPlant(pp, powerPlantDeck));
            const market = initial.splice(0, 8).sort((a, b) => a.number - b.number);
            actualMarket = market.slice(0, 4);
            futureMarket = market.slice(4);
            const first = initial.shift()!;
            deck = shuffle(shuffle(deck, rng() + '').concat(initial), rng() + '');
            deck.unshift(first);
        }
        deck.push(step3);
        return { actualMarket, futureMarket, powerPlantsDeck: deck, setAsidePlants };
    },
    mapSpecificRules:
        'Chile has two separate resource markets: North and Central. Until Step 3, you may only buy from the market of the grid your cities are in; if you have no cities, choose one market for that turn.\n' +
        'There is no uranium: all uranium power plants are removed and there is no uranium market. No power plants are removed for the number of players.\n' +
        'The three largest ecological power plants are set aside at setup.\n' +
        'Both markets share one supply. During bureaucracy, North restocks first, then Central. Garbage is only restocked in the Central market. In Step 2, oil restocks only 1 per market.\n' +
        'Gated connections cannot be built across until Step 3. The border spaces (Salta; with 4-6 players also Tacna and Jujuy) hold one city each, cost $10 plus the connection, and cannot be your first city.\n' +
        'Step 3: the two markets merge into one, the gated connections open, the set-aside ecological plants go on top of the deck, and every ecological plant (except fusion) powers one additional city.',
};
