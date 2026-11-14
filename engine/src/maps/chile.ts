// Chile, designed by Mike Isom (draft, in testing). The board itself is generated into chile-board.ts.
import { cloneDeep } from 'lodash';
import seedrandom from 'seedrandom';
import { PowerPlant } from '../gamestate';
import { shuffle } from '../utils';
import { GameMap } from './../maps';
import { powerPlants } from './../powerPlants';
import { chileCities, chileConnections, chileGates, chileViewBox } from './chile-board';

/** No nuclear power in Chile: the standard deck's uranium plants are out of the game. Fusion plant 50 stays. */
export const chileRemovedPlants = [11, 17, 23, 28, 34, 39];
/** The three largest ecological plants, set aside at setup; they go on top of the draw stack when Step 3 begins. */
export const chileSetAsidePlants = [33, 37, 44];

export const map: GameMap = {
    name: 'Chile',
    cities: chileCities,
    connections: chileConnections,
    step3Connections: chileGates,
    // The two northern regions, each holding a gate, are always in play.
    fixedRegions: ['brown', 'yellow'],
    setAsidePlants: chileSetAsidePlants,
    viewBox: chileViewBox,
    // Central market (the engine's main market). [resource][players-2][step-1]; 2P copies 3P. The Step 3 column is
    // the merged market's restock.
    resupply: [
        // Coal
        [
            [2, 3, 3],
            [2, 3, 3],
            [3, 4, 4],
            [3, 5, 5],
            [4, 6, 6],
        ],
        // Oil
        [
            [1, 1, 4],
            [1, 1, 4],
            [2, 1, 5],
            [2, 1, 6],
            [3, 1, 7],
        ],
        // Garbage
        [
            [1, 2, 3],
            [1, 2, 3],
            [2, 3, 4],
            [3, 3, 5],
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
            [2, 3, 0],
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
    // The standard deck without its uranium plants and the set-aside plants, built as usual except that no plants are
    // removed for the number of players.
    setupDeck(numPlayers: number, variant: string, rng: seedrandom.prng) {
        const out = new Set([...chileRemovedPlants, ...chileSetAsidePlants]);
        let deck: PowerPlant[] = cloneDeep(powerPlants).filter((pp) => !out.has(pp.number));
        const step3 = deck.pop()!;
        let actualMarket: PowerPlant[];
        let futureMarket: PowerPlant[];

        if (variant == 'original') {
            const market = deck.splice(0, 8); // 3-10
            actualMarket = market.slice(0, 4);
            futureMarket = market.slice(4);
            const plant13 = deck.splice(
                deck.findIndex((pp) => pp.number == 13),
                1
            )[0];
            deck = shuffle(deck, rng() + '');
            deck.unshift(plant13);
        } else {
            // The plug-back plants 3-15 (12 of them without 11): eight open the market, one goes on top of the deck
            // and the other three are shuffled into it.
            const initial = shuffle(
                deck.splice(
                    0,
                    deck.findIndex((pp) => pp.number > 15)
                ),
                rng() + ''
            );
            const market = initial.splice(0, 8).sort((a, b) => a.number - b.number);
            actualMarket = market.slice(0, 4);
            futureMarket = market.slice(4);
            const first = initial.shift()!;
            deck = shuffle(shuffle(deck, rng() + '').concat(initial), rng() + '');
            deck.unshift(first);
        }
        deck.push(step3);
        return { actualMarket, futureMarket, powerPlantsDeck: deck };
    },
    mapSpecificRules:
        'Chile has two separate resource markets: North and Central. Until Step 3, you may only buy from the market of the grid your cities are in; if you have no cities, choose one market for that turn.\n' +
        'There is no uranium: all uranium power plants are removed and there is no uranium market. No power plants are removed for the number of players.\n' +
        'The three largest ecological power plants are set aside at setup.\n' +
        'Both markets share one supply. During bureaucracy, North restocks first, then Central. Garbage is only restocked in the Central market. In Step 2, oil restocks only 1 per market.\n' +
        'Gated connections cannot be built across until Step 3. Salta (Argentina) holds one city, costs $10 plus the connection, and cannot be your first city.\n' +
        'Step 3: the two markets merge into one, the gated connections open, the set-aside ecological plants go on top of the deck, and every ecological plant (except fusion) powers one additional city.',
};
