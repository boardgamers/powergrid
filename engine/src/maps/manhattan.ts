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
export enum Regions {
    Manhattan = 'manhattan',
}

// SESSION 3 board (first pass, auto-extracted from the clean board photo
// `viewer/public/powergrid manhattan map.jpg`): 83 building spaces (M1..M83,
// numbered top-to-bottom matching the detection overlay), each with its printed
// building cost in slotCosts and street adjacency in manhattanConnections.
// connectionCost:5 on every space drives the flat-5 transit dijkstra. Coordinates
// are raw photo pixels here; the viewer render config (viewBox/adjustRatio/panels)
// is tuned in Session 4. Prices + links are first-pass and refined live with John.

const manhattanCities: City[] = [
    { name: 'M1', region: Regions.Manhattan, connectionCost: 5, slotCosts: [40], x: 236, y: 129 },
    { name: 'M2', region: Regions.Manhattan, connectionCost: 5, slotCosts: [40], x: 294, y: 132 },
    { name: 'M3', region: Regions.Manhattan, connectionCost: 5, slotCosts: [40], x: 456, y: 135 },
    { name: 'M4', region: Regions.Manhattan, connectionCost: 5, slotCosts: [40], x: 529, y: 137 },
    { name: 'M5', region: Regions.Manhattan, connectionCost: 5, slotCosts: [40], x: 234, y: 236 },
    { name: 'M6', region: Regions.Manhattan, connectionCost: 5, slotCosts: [35], x: 292, y: 236 },
    { name: 'M7', region: Regions.Manhattan, connectionCost: 5, slotCosts: [35], x: 456, y: 238 },
    { name: 'M8', region: Regions.Manhattan, connectionCost: 5, slotCosts: [40], x: 532, y: 239 },
    { name: 'M9', region: Regions.Manhattan, connectionCost: 5, slotCosts: [30], x: 307, y: 318 },
    { name: 'M10', region: Regions.Manhattan, connectionCost: 5, slotCosts: [35], x: 235, y: 340 },
    { name: 'M11', region: Regions.Manhattan, connectionCost: 5, slotCosts: [30], x: 457, y: 340 },
    { name: 'M12', region: Regions.Manhattan, connectionCost: 5, slotCosts: [35], x: 529, y: 344 },
    { name: 'M13', region: Regions.Manhattan, connectionCost: 5, slotCosts: [30], x: 290, y: 367 },
    { name: 'M14', region: Regions.Manhattan, connectionCost: 5, slotCosts: [35], x: 241, y: 420 },
    { name: 'M15', region: Regions.Manhattan, connectionCost: 5, slotCosts: [30], x: 300, y: 421 },
    { name: 'M16', region: Regions.Manhattan, connectionCost: 5, slotCosts: [25], x: 389, y: 422 },
    { name: 'M17', region: Regions.Manhattan, connectionCost: 5, slotCosts: [30], x: 457, y: 423 },
    { name: 'M18', region: Regions.Manhattan, connectionCost: 5, slotCosts: [35], x: 523, y: 423 },
    { name: 'M19', region: Regions.Manhattan, connectionCost: 5, slotCosts: [25], x: 344, y: 431 },
    { name: 'M20', region: Regions.Manhattan, connectionCost: 5, slotCosts: [35], x: 243, y: 480 },
    { name: 'M21', region: Regions.Manhattan, connectionCost: 5, slotCosts: [30], x: 300, y: 481 },
    { name: 'M22', region: Regions.Manhattan, connectionCost: 5, slotCosts: [25], x: 348, y: 482 },
    { name: 'M23', region: Regions.Manhattan, connectionCost: 5, slotCosts: [25], x: 393, y: 483 },
    { name: 'M24', region: Regions.Manhattan, connectionCost: 5, slotCosts: [30], x: 455, y: 484 },
    { name: 'M25', region: Regions.Manhattan, connectionCost: 5, slotCosts: [35], x: 521, y: 485 },
    { name: 'M26', region: Regions.Manhattan, connectionCost: 5, slotCosts: [30], x: 240, y: 539 },
    { name: 'M27', region: Regions.Manhattan, connectionCost: 5, slotCosts: [25], x: 301, y: 540 },
    { name: 'M28', region: Regions.Manhattan, connectionCost: 5, slotCosts: [20], x: 353, y: 541 },
    { name: 'M29', region: Regions.Manhattan, connectionCost: 5, slotCosts: [20], x: 400, y: 541 },
    { name: 'M30', region: Regions.Manhattan, connectionCost: 5, slotCosts: [25], x: 456, y: 542 },
    { name: 'M31', region: Regions.Manhattan, connectionCost: 5, slotCosts: [30], x: 522, y: 543 },
    { name: 'M32', region: Regions.Manhattan, connectionCost: 5, slotCosts: [20], x: 405, y: 588 },
    { name: 'M33', region: Regions.Manhattan, connectionCost: 5, slotCosts: [30], x: 239, y: 605 },
    { name: 'M34', region: Regions.Manhattan, connectionCost: 5, slotCosts: [25], x: 303, y: 605 },
    { name: 'M35', region: Regions.Manhattan, connectionCost: 5, slotCosts: [25], x: 455, y: 606 },
    { name: 'M36', region: Regions.Manhattan, connectionCost: 5, slotCosts: [25], x: 528, y: 607 },
    { name: 'M37', region: Regions.Manhattan, connectionCost: 5, slotCosts: [20], x: 367, y: 609 },
    { name: 'M38', region: Regions.Manhattan, connectionCost: 5, slotCosts: [25], x: 289, y: 680 },
    { name: 'M39', region: Regions.Manhattan, connectionCost: 5, slotCosts: [20], x: 466, y: 680 },
    { name: 'M40', region: Regions.Manhattan, connectionCost: 5, slotCosts: [20], x: 512, y: 680 },
    { name: 'M41', region: Regions.Manhattan, connectionCost: 5, slotCosts: [20], x: 363, y: 681 },
    { name: 'M42', region: Regions.Manhattan, connectionCost: 5, slotCosts: [25], x: 571, y: 681 },
    { name: 'M43', region: Regions.Manhattan, connectionCost: 5, slotCosts: [15], x: 417, y: 682 },
    { name: 'M44', region: Regions.Manhattan, connectionCost: 5, slotCosts: [15], x: 427, y: 740 },
    { name: 'M45', region: Regions.Manhattan, connectionCost: 5, slotCosts: [25], x: 632, y: 740 },
    { name: 'M46', region: Regions.Manhattan, connectionCost: 5, slotCosts: [20], x: 505, y: 741 },
    { name: 'M47', region: Regions.Manhattan, connectionCost: 5, slotCosts: [20], x: 572, y: 741 },
    { name: 'M48', region: Regions.Manhattan, connectionCost: 5, slotCosts: [20], x: 378, y: 745 },
    { name: 'M49', region: Regions.Manhattan, connectionCost: 5, slotCosts: [20], x: 346, y: 761 },
    { name: 'M50', region: Regions.Manhattan, connectionCost: 5, slotCosts: [25], x: 312, y: 775 },
    { name: 'M51', region: Regions.Manhattan, connectionCost: 5, slotCosts: [20], x: 640, y: 784 },
    { name: 'M52', region: Regions.Manhattan, connectionCost: 5, slotCosts: [15], x: 571, y: 787 },
    { name: 'M53', region: Regions.Manhattan, connectionCost: 5, slotCosts: [15], x: 427, y: 790 },
    { name: 'M54', region: Regions.Manhattan, connectionCost: 5, slotCosts: [15], x: 514, y: 790 },
    { name: 'M55', region: Regions.Manhattan, connectionCost: 5, slotCosts: [10], x: 473, y: 794 },
    { name: 'M56', region: Regions.Manhattan, connectionCost: 5, slotCosts: [15], x: 646, y: 821 },
    { name: 'M57', region: Regions.Manhattan, connectionCost: 5, slotCosts: [10], x: 585, y: 827 },
    { name: 'M58', region: Regions.Manhattan, connectionCost: 5, slotCosts: [15], x: 430, y: 832 },
    { name: 'M59', region: Regions.Manhattan, connectionCost: 5, slotCosts: [10], x: 533, y: 833 },
    { name: 'M60', region: Regions.Manhattan, connectionCost: 5, slotCosts: [10], x: 482, y: 834 },
    { name: 'M61', region: Regions.Manhattan, connectionCost: 5, slotCosts: [15], x: 389, y: 851 },
    { name: 'M62', region: Regions.Manhattan, connectionCost: 5, slotCosts: [20], x: 350, y: 852 },
    { name: 'M63', region: Regions.Manhattan, connectionCost: 5, slotCosts: [10], x: 613, y: 859 },
    { name: 'M64', region: Regions.Manhattan, connectionCost: 5, slotCosts: [10], x: 673, y: 860 },
    { name: 'M65', region: Regions.Manhattan, connectionCost: 5, slotCosts: [15], x: 433, y: 871 },
    { name: 'M66', region: Regions.Manhattan, connectionCost: 5, slotCosts: [10], x: 571, y: 873 },
    { name: 'M67', region: Regions.Manhattan, connectionCost: 5, slotCosts: [10], x: 482, y: 874 },
    { name: 'M68', region: Regions.Manhattan, connectionCost: 5, slotCosts: [10], x: 534, y: 885 },
    { name: 'M69', region: Regions.Manhattan, connectionCost: 5, slotCosts: [10], x: 636, y: 892 },
    { name: 'M70', region: Regions.Manhattan, connectionCost: 5, slotCosts: [20], x: 371, y: 895 },
    { name: 'M71', region: Regions.Manhattan, connectionCost: 5, slotCosts: [15], x: 482, y: 914 },
    { name: 'M72', region: Regions.Manhattan, connectionCost: 5, slotCosts: [10], x: 593, y: 915 },
    { name: 'M73', region: Regions.Manhattan, connectionCost: 5, slotCosts: [15], x: 427, y: 920 },
    { name: 'M74', region: Regions.Manhattan, connectionCost: 5, slotCosts: [15], x: 389, y: 934 },
    { name: 'M75', region: Regions.Manhattan, connectionCost: 5, slotCosts: [10], x: 555, y: 937 },
    { name: 'M76', region: Regions.Manhattan, connectionCost: 5, slotCosts: [10], x: 466, y: 950 },
    { name: 'M77', region: Regions.Manhattan, connectionCost: 5, slotCosts: [10], x: 520, y: 962 },
    { name: 'M78', region: Regions.Manhattan, connectionCost: 5, slotCosts: [10], x: 379, y: 983 },
    { name: 'M79', region: Regions.Manhattan, connectionCost: 5, slotCosts: [15], x: 424, y: 986 },
    { name: 'M80', region: Regions.Manhattan, connectionCost: 5, slotCosts: [10], x: 484, y: 993 },
    { name: 'M81', region: Regions.Manhattan, connectionCost: 5, slotCosts: [15], x: 394, y: 1038 },
    { name: 'M82', region: Regions.Manhattan, connectionCost: 5, slotCosts: [15], x: 429, y: 1041 },
    { name: 'M83', region: Regions.Manhattan, connectionCost: 5, slotCosts: [10], x: 478, y: 1041 },
];

const manhattanConnections: Connection[] = [
    { nodes: ['M1', 'M2'], cost: 0 },
    { nodes: ['M1', 'M5'], cost: 0 },
    { nodes: ['M2', 'M6'], cost: 0 },
    { nodes: ['M3', 'M4'], cost: 0 },
    { nodes: ['M3', 'M7'], cost: 0 },
    { nodes: ['M4', 'M8'], cost: 0 },
    { nodes: ['M5', 'M6'], cost: 0 },
    { nodes: ['M5', 'M10'], cost: 0 },
    { nodes: ['M6', 'M9'], cost: 0 },
    { nodes: ['M7', 'M8'], cost: 0 },
    { nodes: ['M7', 'M11'], cost: 0 },
    { nodes: ['M8', 'M12'], cost: 0 },
    { nodes: ['M9', 'M13'], cost: 0 },
    { nodes: ['M10', 'M13'], cost: 0 },
    { nodes: ['M10', 'M14'], cost: 0 },
    { nodes: ['M11', 'M12'], cost: 0 },
    { nodes: ['M11', 'M17'], cost: 0 },
    { nodes: ['M12', 'M18'], cost: 0 },
    { nodes: ['M13', 'M15'], cost: 0 },
    { nodes: ['M14', 'M15'], cost: 0 },
    { nodes: ['M14', 'M20'], cost: 0 },
    { nodes: ['M15', 'M19'], cost: 0 },
    { nodes: ['M15', 'M21'], cost: 0 },
    { nodes: ['M16', 'M17'], cost: 0 },
    { nodes: ['M16', 'M19'], cost: 0 },
    { nodes: ['M16', 'M23'], cost: 0 },
    { nodes: ['M17', 'M18'], cost: 0 },
    { nodes: ['M17', 'M24'], cost: 0 },
    { nodes: ['M18', 'M25'], cost: 0 },
    { nodes: ['M19', 'M22'], cost: 0 },
    { nodes: ['M20', 'M21'], cost: 0 },
    { nodes: ['M20', 'M26'], cost: 0 },
    { nodes: ['M21', 'M22'], cost: 0 },
    { nodes: ['M21', 'M27'], cost: 0 },
    { nodes: ['M22', 'M23'], cost: 0 },
    { nodes: ['M22', 'M28'], cost: 0 },
    { nodes: ['M23', 'M24'], cost: 0 },
    { nodes: ['M23', 'M29'], cost: 0 },
    { nodes: ['M24', 'M25'], cost: 0 },
    { nodes: ['M24', 'M30'], cost: 0 },
    { nodes: ['M25', 'M31'], cost: 0 },
    { nodes: ['M26', 'M27'], cost: 0 },
    { nodes: ['M26', 'M33'], cost: 0 },
    { nodes: ['M27', 'M28'], cost: 0 },
    { nodes: ['M27', 'M34'], cost: 0 },
    { nodes: ['M28', 'M29'], cost: 0 },
    { nodes: ['M28', 'M37'], cost: 0 },
    { nodes: ['M29', 'M30'], cost: 0 },
    { nodes: ['M29', 'M32'], cost: 0 },
    { nodes: ['M30', 'M31'], cost: 0 },
    { nodes: ['M30', 'M35'], cost: 0 },
    { nodes: ['M31', 'M36'], cost: 0 },
    { nodes: ['M32', 'M35'], cost: 0 },
    { nodes: ['M32', 'M37'], cost: 0 },
    { nodes: ['M33', 'M34'], cost: 0 },
    { nodes: ['M33', 'M38'], cost: 0 },
    { nodes: ['M34', 'M37'], cost: 0 },
    { nodes: ['M34', 'M38'], cost: 0 },
    { nodes: ['M35', 'M36'], cost: 0 },
    { nodes: ['M35', 'M39'], cost: 0 },
    { nodes: ['M36', 'M40'], cost: 0 },
    { nodes: ['M36', 'M42'], cost: 0 },
    { nodes: ['M37', 'M41'], cost: 0 },
    { nodes: ['M37', 'M43'], cost: 0 },
    { nodes: ['M38', 'M41'], cost: 0 },
    { nodes: ['M38', 'M50'], cost: 0 },
    { nodes: ['M39', 'M40'], cost: 0 },
    { nodes: ['M39', 'M43'], cost: 0 },
    { nodes: ['M39', 'M46'], cost: 0 },
    { nodes: ['M40', 'M42'], cost: 0 },
    { nodes: ['M40', 'M46'], cost: 0 },
    { nodes: ['M41', 'M43'], cost: 0 },
    { nodes: ['M41', 'M48'], cost: 0 },
    { nodes: ['M41', 'M49'], cost: 0 },
    { nodes: ['M42', 'M45'], cost: 0 },
    { nodes: ['M42', 'M47'], cost: 0 },
    { nodes: ['M43', 'M44'], cost: 0 },
    { nodes: ['M44', 'M48'], cost: 0 },
    { nodes: ['M44', 'M53'], cost: 0 },
    { nodes: ['M44', 'M55'], cost: 0 },
    { nodes: ['M45', 'M47'], cost: 0 },
    { nodes: ['M45', 'M51'], cost: 0 },
    { nodes: ['M46', 'M47'], cost: 0 },
    { nodes: ['M46', 'M54'], cost: 0 },
    { nodes: ['M46', 'M55'], cost: 0 },
    { nodes: ['M47', 'M52'], cost: 0 },
    { nodes: ['M48', 'M49'], cost: 0 },
    { nodes: ['M48', 'M53'], cost: 0 },
    { nodes: ['M48', 'M61'], cost: 0 },
    { nodes: ['M49', 'M50'], cost: 0 },
    { nodes: ['M49', 'M61'], cost: 0 },
    { nodes: ['M50', 'M62'], cost: 0 },
    { nodes: ['M51', 'M52'], cost: 0 },
    { nodes: ['M51', 'M56'], cost: 0 },
    { nodes: ['M52', 'M54'], cost: 0 },
    { nodes: ['M52', 'M57'], cost: 0 },
    { nodes: ['M52', 'M59'], cost: 0 },
    { nodes: ['M53', 'M55'], cost: 0 },
    { nodes: ['M53', 'M58'], cost: 0 },
    { nodes: ['M54', 'M55'], cost: 0 },
    { nodes: ['M54', 'M59'], cost: 0 },
    { nodes: ['M55', 'M60'], cost: 0 },
    { nodes: ['M56', 'M57'], cost: 0 },
    { nodes: ['M56', 'M63'], cost: 0 },
    { nodes: ['M56', 'M64'], cost: 0 },
    { nodes: ['M57', 'M59'], cost: 0 },
    { nodes: ['M57', 'M63'], cost: 0 },
    { nodes: ['M57', 'M66'], cost: 0 },
    { nodes: ['M58', 'M60'], cost: 0 },
    { nodes: ['M58', 'M61'], cost: 0 },
    { nodes: ['M58', 'M65'], cost: 0 },
    { nodes: ['M59', 'M60'], cost: 0 },
    { nodes: ['M59', 'M66'], cost: 0 },
    { nodes: ['M59', 'M68'], cost: 0 },
    { nodes: ['M60', 'M67'], cost: 0 },
    { nodes: ['M61', 'M62'], cost: 0 },
    { nodes: ['M61', 'M65'], cost: 0 },
    { nodes: ['M61', 'M73'], cost: 0 },
    { nodes: ['M62', 'M70'], cost: 0 },
    { nodes: ['M63', 'M64'], cost: 0 },
    { nodes: ['M63', 'M66'], cost: 0 },
    { nodes: ['M63', 'M69'], cost: 0 },
    { nodes: ['M64', 'M69'], cost: 0 },
    { nodes: ['M65', 'M67'], cost: 0 },
    { nodes: ['M65', 'M73'], cost: 0 },
    { nodes: ['M66', 'M68'], cost: 0 },
    { nodes: ['M66', 'M72'], cost: 0 },
    { nodes: ['M67', 'M68'], cost: 0 },
    { nodes: ['M67', 'M71'], cost: 0 },
    { nodes: ['M68', 'M71'], cost: 0 },
    { nodes: ['M68', 'M75'], cost: 0 },
    { nodes: ['M69', 'M72'], cost: 0 },
    { nodes: ['M70', 'M73'], cost: 0 },
    { nodes: ['M70', 'M74'], cost: 0 },
    { nodes: ['M71', 'M73'], cost: 0 },
    { nodes: ['M71', 'M76'], cost: 0 },
    { nodes: ['M72', 'M75'], cost: 0 },
    { nodes: ['M73', 'M74'], cost: 0 },
    { nodes: ['M73', 'M76'], cost: 0 },
    { nodes: ['M73', 'M79'], cost: 0 },
    { nodes: ['M74', 'M78'], cost: 0 },
    { nodes: ['M74', 'M79'], cost: 0 },
    { nodes: ['M75', 'M77'], cost: 0 },
    { nodes: ['M76', 'M77'], cost: 0 },
    { nodes: ['M76', 'M79'], cost: 0 },
    { nodes: ['M76', 'M80'], cost: 0 },
    { nodes: ['M77', 'M80'], cost: 0 },
    { nodes: ['M78', 'M79'], cost: 0 },
    { nodes: ['M78', 'M81'], cost: 0 },
    { nodes: ['M79', 'M80'], cost: 0 },
    { nodes: ['M79', 'M82'], cost: 0 },
    { nodes: ['M80', 'M83'], cost: 0 },
    { nodes: ['M81', 'M82'], cost: 0 },
    { nodes: ['M82', 'M83'], cost: 0 },
];

export const map: GameMap = {
    name: 'Manhattan',
    cities: manhattanCities,
    connections: manhattanConnections,
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
    // Player-count scaling = blocked spaces (transitable but unbuildable). 5–6
    // players use the full board. 4 players block 14 spaces (one colour's worth);
    // 2–3 players block 28 (two colours). The blocked spaces are chosen at random
    // within fixed cost tiers — the printed rule has players mutually agree, so the
    // engine picks for them:
    //   per colour:  3×10  3×15  2×20  2×25  2×30  2×35   (= 14; 40 is never blocked)
    // The Session-3 board carries every tier (counts: 10×16, 15×16, 20×15, 25×10,
    // 30×13, 35×7, 40×6), so the per-tier pick is exact (slice(0, count) always has
    // enough candidates for both the 14-space and 28-space cases).
    blockSpaces(numPlayers: number, cities: City[], rng: seedrandom.prng): string[] {
        if (numPlayers >= 5) {
            return [];
        }
        const perColour: Record<number, number> = { 10: 3, 15: 3, 20: 2, 25: 2, 30: 2, 35: 2 };
        const colours = numPlayers === 4 ? 1 : 2; // 2–3 players block two colours' worth
        const blocked: string[] = [];
        for (const [priceStr, perColourCount] of Object.entries(perColour)) {
            const price = Number(priceStr);
            const count = perColourCount * colours;
            const candidates = shuffle(
                cities.filter((c) => c.slotCosts && c.slotCosts[0] === price).map((c) => c.name),
                rng() + ''
            );
            blocked.push(...candidates.slice(0, count));
        }
        return blocked;
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
