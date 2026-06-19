// by John and Cici
import { cloneDeep } from 'lodash';
import seedrandom from 'seedrandom';
import { shuffle } from '../utils';
import { City, Connection, GameMap } from './../maps';
import { powerPlants } from './../powerPlants';

// Manhattan (RIO 686 Bremen/Manhattan expansion) is unlike every other board:
//  • A SINGLE region. Every building space holds exactly ONE house, at its printed
//    building cost (10–40 Elektro) — modelled as slotCosts:[price] (length 1 caps
//    occupancy at one; the value is the build price).
//  • The game NEVER leaves Step 1 (the Step 3 card is boxed at setup; Step 2 is
//    suppressed in engine.ts). Resource refill is therefore flat all game.
//  • Connections are a flat 5 Elektro per space you TRANSIT through (not per edge):
//    your first house may be any empty space (building cost only); a space adjacent
//    to your network costs only its building cost; otherwise pay 5 × (spaces
//    transited) + the target's building cost. We set connectionCost:5 on every
//    space so the build-cost dijkstra charges 5 on entry, and engine.ts refunds the
//    target's own 5 (you build on it, you don't transit it).
//
// PLACEHOLDER GEOMETRY (Session 1): the grid below is a throwaway just large enough
// to exercise setup, single-occupancy, flat-5 transit and the end-game threshold.
// The real ~80-space board (printed prices + street adjacency, read from the board
// photo `viewer/public/powergrid manhattan map.jpg`) is authored in Session 3.

export enum Regions {
    Manhattan = 'manhattan',
}

const GRID_COLS = 4;
const GRID_ROWS = 5;
// North (uptown, by Central Park) is expensive, south (downtown) is cheap — the
// real board grades 40 → 10; this placeholder mirrors that by row.
const rowPrices = [40, 30, 20, 15, 10];

const placeholderCities: City[] = [];
const placeholderConnections: Connection[] = [];
for (let r = 0; r < GRID_ROWS; r++) {
    for (let c = 0; c < GRID_COLS; c++) {
        const id = r * GRID_COLS + c + 1;
        const name = `M${id}`;
        placeholderCities.push({
            name,
            region: Regions.Manhattan,
            connectionCost: 5,
            slotCosts: [rowPrices[r]],
            x: 120 + c * 130,
            y: 110 + r * 130,
        });
        if (c < GRID_COLS - 1) {
            placeholderConnections.push({ nodes: [name, `M${id + 1}`], cost: 0 });
        }
        if (r < GRID_ROWS - 1) {
            placeholderConnections.push({ nodes: [name, `M${id + GRID_COLS}`], cost: 0 });
        }
    }
}

export const map: GameMap = {
    name: 'Manhattan',
    cities: placeholderCities,
    connections: placeholderConnections,
    layout: 'Portrait',
    // Flat refill (single-column Manhattan cards): the game only runs in Step 1, so
    // only the Step-1 entry is ever read — all three columns are filled identically.
    // Indexed [resource][playerCount-2][step-1]. 2P and 3P rows are identical.
    resupply: [
        // Coal
        [
            [4, 4, 4],
            [4, 4, 4],
            [5, 5, 5],
            [6, 6, 6],
            [7, 7, 7],
        ],
        // Oil
        [
            [3, 3, 3],
            [3, 3, 3],
            [4, 4, 4],
            [5, 5, 5],
            [6, 6, 6],
        ],
        // Garbage
        [
            [2, 2, 2],
            [2, 2, 2],
            [3, 3, 3],
            [4, 4, 4],
            [5, 5, 5],
        ],
        // Uranium — Manhattan DOES use uranium
        [
            [1, 1, 1],
            [1, 1, 1],
            [2, 2, 2],
            [2, 2, 2],
            [3, 3, 3],
        ],
    ],
    // Fill: coal 3–8 (18), oil 3–8 (18), garbage 6–8 (9), uranium 10–16 (4).
    // Standard recharged price tracks (no custom *Prices arrays → engine defaults).
    startingResources: [18, 18, 9, 4],
    startingSupply: [24, 24, 24, 12],
    // Custom deck prep. The Step 3 card and the player-count plant removals go to the
    // BOX (they never return). The recharged "plug" cards (the 13 plants numbered
    // ≤ 15): box 4, keep 9 on top of the stack; the opening 8-card market is drawn
    // from them. "Socket" cards (> 15) form the rest of the stack. The deck-depletion
    // market lifecycle (separate-pile reshuffle → all-buyable → shrink) is Session 2.
    setupDeck(numPlayers: number, variant: string, rng: seedrandom.prng) {
        const boxed = new Set<number>();
        if (numPlayers <= 3) {
            boxed.add(20);
            boxed.add(22);
            boxed.add(37);
        }
        const deck = cloneDeep(powerPlants).filter((pp) => !boxed.has(pp.number));
        // Last entry of the master list is the Step 3 card → boxed (dropped), so the
        // game can never advance out of Step 1.
        deck.pop();

        const plug = shuffle(
            deck.filter((pp) => pp.number <= 15),
            rng() + ''
        );
        const socket = shuffle(
            deck.filter((pp) => pp.number > 15),
            rng() + ''
        );
        plug.splice(0, 4); // four plug cards to the box
        // Nine plug cards remain on top; draw the topmost 8 → market (ascending).
        const initialMarket = plug.splice(0, 8).sort((a, b) => a.number - b.number);
        const actualMarket = initialMarket.slice(0, 4);
        const futureMarket = initialMarket.slice(4);
        // One leftover plug card sits on top of the socket stack.
        const powerPlantsDeck = [...plug, ...socket];
        return { actualMarket, futureMarket, powerPlantsDeck };
    },
    mapSpecificRules:
        'Single region, one house per space: every building space holds just one ' +
        'house at its printed building cost (10–40 Elektro). The game runs only in ' +
        'Step 1 until the end. Connections: your first house may be any empty space ' +
        '(pay only its building cost); a space directly adjacent to your network ' +
        'costs only its building cost; otherwise pay a flat 5 Elektro for each space ' +
        'you transit through (blocked spaces, or spaces you choose not to connect) ' +
        'plus the building cost of the target space. Uranium is used. With fewer ' +
        'players, some spaces are blocked at setup (4 players block 14 spaces; 2–3 ' +
        'players block 28). In the physical game the players mutually choose which ' +
        'spaces to block; here the system selects them automatically for your ' +
        'convenience. The game ends when a player has connected 18 spaces ' +
        '(17 for 3–4 players, 15 for 5, 14 for 6).',
};
