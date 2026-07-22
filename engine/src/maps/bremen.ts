// by John and Cici
import { cloneDeep } from 'lodash';
import seedrandom from 'seedrandom';
import { getPowerPlant } from '../engine';
import { PowerPlant } from '../gamestate';
import { shuffle } from '../utils';
import { GameMap } from './../maps';
import { powerPlants } from './../powerPlants';

export enum Regions {
    Blue = 'blue',
    Pink = 'pink',
    Purple = 'purple',
    Red = 'red',
    Orange = 'orange',
}

export enum Cities {
    Borgfeld = 'Borgfeld',
    Oberneuland = 'Oberneuland',
    Osterholz = 'Osterholz',
    HornLehe = 'Horn-Lehe',
    Vahr = 'Vahr',
    Schwachhausen = 'Schwachhausen',
    OstlicheVorstadt = 'Östliche Vorstadt',
    Findorff = 'Findorff',
    Walle = 'Walle',
    Mitte = 'Mitte',
    Hemelingen = 'Hemelingen',
    Mahndorf = 'Mahndorf',
    Neustadt = 'Neustadt',
    Obervieland = 'Obervieland',
    Huchting = 'Huchting',
    Hofen = 'Höfen',
    Pusdorf = 'Pusdorf',
    Neustadtshafen = 'Neustadtshafen',
    Strom = 'Strom',
    Seehausen = 'Seehausen',
    Blockland = 'Blockland',
    Gropelingen = 'Gröpelingen',
    Burglesum = 'Burglesum',
    Vegesack = 'Vegesack',
    Blumenthal = 'Blumenthal',
}

// Bremen prices each district as a flat node cost (`connectionCost`); building a
// house costs 8 / 14 / 20 Elektro (the small districts have only two spaces,
// 8 / 14, so only two players can ever connect them).
export const map: GameMap = {
    name: 'Bremen',
    cities: [
        // Blue
        { name: Cities.Borgfeld, region: Regions.Blue, connectionCost: 15, slotCosts: [8, 14], x: 645, y: 273 },
        { name: Cities.Oberneuland, region: Regions.Blue, connectionCost: 14, slotCosts: [8, 14, 20], x: 652, y: 342 },
        { name: Cities.Osterholz, region: Regions.Blue, connectionCost: 11, slotCosts: [8, 14, 20], x: 660, y: 434 },
        { name: Cities.HornLehe, region: Regions.Blue, connectionCost: 9, slotCosts: [8, 14, 20], x: 572, y: 322 },
        { name: Cities.Vahr, region: Regions.Blue, connectionCost: 6, slotCosts: [8, 14, 20], x: 583, y: 376 },
        // Pink
        { name: Cities.Schwachhausen, region: Regions.Pink, connectionCost: 5, slotCosts: [8, 14, 20], x: 517, y: 357 },
        {
            name: Cities.OstlicheVorstadt,
            region: Regions.Pink,
            connectionCost: 2,
            slotCosts: [8, 14, 20],
            x: 536,
            y: 409,
        },
        { name: Cities.Findorff, region: Regions.Pink, connectionCost: 3, slotCosts: [8, 14], x: 488, y: 311 },
        { name: Cities.Walle, region: Regions.Pink, connectionCost: 6, slotCosts: [8, 14, 20], x: 438, y: 342 },
        { name: Cities.Mitte, region: Regions.Pink, connectionCost: 1, slotCosts: [8, 14, 20], x: 472, y: 388 },
        // Purple
        { name: Cities.Hemelingen, region: Regions.Purple, connectionCost: 8, slotCosts: [8, 14, 20], x: 600, y: 453 },
        { name: Cities.Mahndorf, region: Regions.Purple, connectionCost: 10, slotCosts: [8, 14, 20], x: 666, y: 499 },
        { name: Cities.Neustadt, region: Regions.Purple, connectionCost: 5, slotCosts: [8, 14, 20], x: 464, y: 452 },
        {
            name: Cities.Obervieland,
            region: Regions.Purple,
            connectionCost: 10,
            slotCosts: [8, 14, 20],
            x: 529,
            y: 479,
        },
        { name: Cities.Huchting, region: Regions.Purple, connectionCost: 12, slotCosts: [8, 14], x: 386, y: 442 },
        // Red
        { name: Cities.Hofen, region: Regions.Red, connectionCost: 9, slotCosts: [8, 14, 20], x: 352, y: 272 },
        { name: Cities.Pusdorf, region: Regions.Red, connectionCost: 7, slotCosts: [8, 14, 20], x: 399, y: 386 },
        { name: Cities.Neustadtshafen, region: Regions.Red, connectionCost: 8, slotCosts: [8, 14, 20], x: 375, y: 340 },
        { name: Cities.Strom, region: Regions.Red, connectionCost: 14, slotCosts: [8, 14, 20], x: 328, y: 393 },
        { name: Cities.Seehausen, region: Regions.Red, connectionCost: 14, slotCosts: [8, 14], x: 290, y: 321 },
        // Orange
        { name: Cities.Blockland, region: Regions.Orange, connectionCost: 11, slotCosts: [8, 14, 20], x: 476, y: 251 },
        { name: Cities.Gropelingen, region: Regions.Orange, connectionCost: 8, slotCosts: [8, 14, 20], x: 426, y: 280 },
        { name: Cities.Burglesum, region: Regions.Orange, connectionCost: 13, slotCosts: [8, 14, 20], x: 337, y: 197 },
        { name: Cities.Vegesack, region: Regions.Orange, connectionCost: 10, slotCosts: [8, 14, 20], x: 248, y: 170 },
        { name: Cities.Blumenthal, region: Regions.Orange, connectionCost: 15, slotCosts: [8, 14], x: 154, y: 135 },
    ],
    // Bremen has flat per-district costs (the `connectionCost` on each city), not
    // per-edge costs — so every connection's `cost` is 0 and only encodes which
    // districts border each other. Crossing the Weser/Lesum rivers costs nothing
    // extra (you still pay the destination district's cost), so river borders are
    // ordinary adjacencies here.
    // WIP (S2 borders pass): reset to trusted internal skeletons for Blue/Red/Orange
    // only. Pink + Purple internals and ALL inter-region links (incl. the Höfen↔
    // Gröpelingen Weser crossing) were cleared, to be rebuilt against the board.
    connections: [
        // Blue (internal)
        { nodes: [Cities.Borgfeld, Cities.Oberneuland], cost: 0 },
        { nodes: [Cities.Oberneuland, Cities.Osterholz], cost: 0 },
        { nodes: [Cities.Borgfeld, Cities.HornLehe], cost: 0 },
        { nodes: [Cities.Oberneuland, Cities.HornLehe], cost: 0 },
        { nodes: [Cities.Oberneuland, Cities.Vahr], cost: 0 },
        { nodes: [Cities.Osterholz, Cities.Vahr], cost: 0 },
        { nodes: [Cities.HornLehe, Cities.Vahr], cost: 0 },
        // Blue → neighbours (S2 rebuild)
        { nodes: [Cities.HornLehe, Cities.Schwachhausen], cost: 0 },
        { nodes: [Cities.HornLehe, Cities.Findorff], cost: 0 },
        { nodes: [Cities.Vahr, Cities.Hemelingen], cost: 0 },
        { nodes: [Cities.Osterholz, Cities.Mahndorf], cost: 0 },
        // Red (internal)
        { nodes: [Cities.Hofen, Cities.Neustadtshafen], cost: 0 },
        { nodes: [Cities.Hofen, Cities.Seehausen], cost: 0 },
        { nodes: [Cities.Pusdorf, Cities.Neustadtshafen], cost: 0 },
        { nodes: [Cities.Neustadtshafen, Cities.Seehausen], cost: 0 },
        { nodes: [Cities.Neustadtshafen, Cities.Strom], cost: 0 },
        { nodes: [Cities.Seehausen, Cities.Strom], cost: 0 },
        // Orange (internal)
        { nodes: [Cities.Blockland, Cities.Gropelingen], cost: 0 },
        { nodes: [Cities.Blockland, Cities.Burglesum], cost: 0 },
        { nodes: [Cities.Gropelingen, Cities.Burglesum], cost: 0 },
        { nodes: [Cities.Burglesum, Cities.Vegesack], cost: 0 },
        { nodes: [Cities.Vegesack, Cities.Blumenthal], cost: 0 },
        // Purple (internal, S2 rebuild)
        { nodes: [Cities.Mahndorf, Cities.Hemelingen], cost: 0 },
        { nodes: [Cities.Hemelingen, Cities.Obervieland], cost: 0 },
        { nodes: [Cities.Obervieland, Cities.Neustadt], cost: 0 },
        { nodes: [Cities.Neustadt, Cities.Huchting], cost: 0 },
        // Purple → neighbours (S2 rebuild)
        { nodes: [Cities.Hemelingen, Cities.OstlicheVorstadt], cost: 0 },
        { nodes: [Cities.Obervieland, Cities.OstlicheVorstadt], cost: 0 },
        { nodes: [Cities.Neustadt, Cities.Mitte], cost: 0 },
        { nodes: [Cities.Neustadt, Cities.OstlicheVorstadt], cost: 0 },
        { nodes: [Cities.Huchting, Cities.Strom], cost: 0 },
        { nodes: [Cities.Huchting, Cities.Pusdorf], cost: 0 },
        // Pink (internal, S2 rebuild)
        { nodes: [Cities.Findorff, Cities.Walle], cost: 0 },
        { nodes: [Cities.Findorff, Cities.Mitte], cost: 0 },
        { nodes: [Cities.Findorff, Cities.Schwachhausen], cost: 0 },
        { nodes: [Cities.Schwachhausen, Cities.OstlicheVorstadt], cost: 0 },
        { nodes: [Cities.Schwachhausen, Cities.Mitte], cost: 0 },
        { nodes: [Cities.Walle, Cities.Mitte], cost: 0 },
        { nodes: [Cities.Mitte, Cities.OstlicheVorstadt], cost: 0 },
        // Red (internal, S2 rebuild)
        { nodes: [Cities.Strom, Cities.Pusdorf], cost: 0 },
        // Cross-region (S2 rebuild)
        { nodes: [Cities.Vahr, Cities.Schwachhausen], cost: 0 }, // blue–pink
        { nodes: [Cities.Blockland, Cities.HornLehe], cost: 0 }, // orange–blue
        { nodes: [Cities.Hemelingen, Cities.Osterholz], cost: 0 }, // purple–blue
        { nodes: [Cities.Hofen, Cities.Gropelingen], cost: 0 }, // red–orange (Weser crossing)
        { nodes: [Cities.Hofen, Cities.Burglesum], cost: 0 }, // red–orange
        { nodes: [Cities.Burglesum, Cities.Seehausen], cost: 0 }, // orange–red
        { nodes: [Cities.Walle, Cities.Gropelingen], cost: 0 }, // pink–orange
        { nodes: [Cities.Walle, Cities.Blockland], cost: 0 }, // pink–orange
        { nodes: [Cities.Findorff, Cities.Blockland], cost: 0 }, // pink–orange
        { nodes: [Cities.Walle, Cities.Hofen], cost: 0 }, // pink–red
        { nodes: [Cities.Walle, Cities.Neustadtshafen], cost: 0 }, // pink–red
        { nodes: [Cities.Walle, Cities.Pusdorf], cost: 0 }, // pink–red
        { nodes: [Cities.Pusdorf, Cities.Neustadt], cost: 0 }, // red–purple
    ],
    layout: 'Landscape',
    // Coords authored in landscape (~768×576 space) by clicking the board photo in
    // the viewer; scaled up here to fill the 1500×800 canvas with the panels to the
    // right/top. (The board photo is EXIF-rotated 90° CW, so landscape is native.)
    adjustRatio: [1.75, 1.75],
    mapPosition: [-120, -140],
    mapRotation: 0,
    // Resupply read from the printed Bremen refill cards. Indexed
    // [resource][playerCount-2][step-1]. 2P and 3P rows are identical. No uranium.
    resupply: [
        // Coal
        [
            [4, 5, 3], // 2P
            [4, 5, 3], // 3P
            [5, 6, 4], // 4P
            [5, 7, 5], // 5P
            [7, 9, 6], // 6P
        ],
        // Oil
        [
            [2, 3, 4], // 2P
            [2, 3, 4], // 3P
            [3, 4, 5], // 4P
            [4, 5, 6], // 5P
            [5, 6, 7], // 6P
        ],
        // Garbage
        [
            [1, 2, 1], // 2P
            [1, 2, 1], // 3P
            [2, 3, 2], // 4P
            [3, 3, 3], // 5P
            [3, 5, 3], // 6P
        ],
        // Uranium — Bremen has none
        [
            [0, 0, 0],
            [0, 0, 0],
            [0, 0, 0],
            [0, 0, 0],
            [0, 0, 0],
        ],
    ],
    // The printed market track holds only TWO cubes per resource at $7 and $8
    // (three everywhere else): 22 slots per resource, matching the 22-cube
    // supply exactly — which is why 2 of each go back in the box.
    coalPrices: [1, 1, 1, 2, 2, 2, 3, 3, 3, 4, 4, 4, 5, 5, 5, 6, 6, 6, 7, 7, 8, 8],
    oilPrices: [1, 1, 1, 2, 2, 2, 3, 3, 3, 4, 4, 4, 5, 5, 5, 6, 6, 6, 7, 7, 8, 8],
    garbagePrices: [1, 1, 1, 2, 2, 2, 3, 3, 3, 4, 4, 4, 5, 5, 5, 6, 6, 6, 7, 7, 8, 8],
    // Coal fills 1–8 (a full 22-cube market), oil 3–8 and garbage 3–8 (16 cubes
    // each, 6 in reserve), no uranium.
    startingResources: [22, 16, 16, 0],
    startingSupply: [22, 22, 22, 0],
    // Bremen plays with fewer power plants. Remove 11, 17, 23, 28, 34, 36, 38, 39,
    // 46 — every uranium-burning plant (11/17/23/28/34/39) plus the three plants that
    // power 7 cities (36/38/46); 2–4 players also remove 31 and 50. The opening
    // market is then drawn from the remaining "weak" pool (≤15) per the recharged
    // convention — 8 open the market, one goes on top of the deck and the leftovers
    // are shuffled in — and NO further player-count deck reduction is applied.
    setupDeck(numPlayers: number, variant: string, rng: seedrandom.prng) {
        const removed = new Set([11, 17, 23, 28, 34, 36, 38, 39, 46]);
        if (numPlayers <= 4) {
            removed.add(31);
            removed.add(50);
        }
        const deck = cloneDeep(powerPlants).filter((pp) => !removed.has(pp.number));
        // The Step 3 card is the last entry of the master list and is never removed.
        const step3 = deck.pop()!;

        let actualMarket: PowerPlant[];
        let futureMarket: PowerPlant[];

        if (variant == 'original') {
            // Fixed opening market 3–6 / 7–10 (none of these are removed on Bremen).
            actualMarket = [getPowerPlant(3), getPowerPlant(4), getPowerPlant(5), getPowerPlant(6)];
            futureMarket = [getPowerPlant(7), getPowerPlant(8), getPowerPlant(9), getPowerPlant(10)];
            const inMarket = new Set([3, 4, 5, 6, 7, 8, 9, 10]);
            const plant13 = deck.find((pp) => pp.number == 13)!;
            let rest = deck.filter((pp) => !inMarket.has(pp.number) && pp.number != 13);
            rest = shuffle(rest, rng() + '');
            rest.unshift(plant13);
            rest.push(step3);
            return { actualMarket, futureMarket, powerPlantsDeck: rest };
        }

        // Recharged: the opening 8 plants come from the ≤15 weak pool.
        const weak = shuffle(
            deck.filter((pp) => pp.number <= 15),
            rng() + ''
        );
        let rest = deck.filter((pp) => pp.number > 15);
        const initialMarket = weak.splice(0, 8).sort((a, b) => a.number - b.number);
        actualMarket = initialMarket.slice(0, 4);
        futureMarket = initialMarket.slice(4);
        const first = weak.shift()!; // one weak plant guaranteed near the top of the deck
        rest = shuffle(rest.concat(weak), rng() + ''); // leftover weak plants fold back in
        rest.unshift(first);
        rest.push(step3);
        return { actualMarket, futureMarket, powerPlantsDeck: rest };
    },
    mapSpecificRules:
        'Flat district costs: instead of connection costs between cities, each ' +
        'district has a single cost. Connecting a new district to your network ' +
        'costs the sum of the district costs along the cheapest path from your ' +
        'network (you pay for each district entered, including ones you only pass ' +
        'through), plus the cheapest building cost (8 / 14 / 20 Elektro) in the new ' +
        'district. (on your 1st placement if A has 1 and B has 3 then A to B is ' +
        '8+3+8=19, and B to A is 8+1+8=17, meaning it is asymmetrical) Small ' +
        'districts have only two spaces (8 / 14) and can hold just two networks.\n' +
        'No uranium: uranium is never sold, and every plant that burns it is removed ' +
        'from the game. Plant 50 needs no fuel, so it stays in the deck with 5 or 6 ' +
        'players.\n' +
        'Deck preparation: power plants 11, 17, 23, 28, 34, 36, 38, 39 and 46 are ' +
        'removed before setup — the six uranium plants plus the three plants that ' +
        'power 7 cities. With 2 to 4 players, plants 31 and 50 are removed as well. ' +
        'No further power plants are removed for the number of players. The opening ' +
        'market of eight is then drawn from the low plants (numbered 15 or less); of ' +
        'the low plants left over, one is placed on top of the draw deck and the rest ' +
        'are shuffled into it, with the Step 3 card on the bottom.\n' +
        'Step 2 begins once a player has 5 connected districts (4 for 6 players); the ' +
        'game ends when a player connects 13 districts (12 for 5 players, 11 for 6).',
};
