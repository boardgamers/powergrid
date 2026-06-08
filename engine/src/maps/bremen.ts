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
        { name: Cities.Borgfeld, region: Regions.Blue, connectionCost: 15, slotCosts: [8, 14], x: 288, y: 120 },
        { name: Cities.Oberneuland, region: Regions.Blue, connectionCost: 14, slotCosts: [8, 14, 20], x: 372, y: 128 },
        { name: Cities.Osterholz, region: Regions.Blue, connectionCost: 11, slotCosts: [8, 14, 20], x: 456, y: 124 },
        { name: Cities.HornLehe, region: Regions.Blue, connectionCost: 9, slotCosts: [8, 14, 20], x: 336, y: 192 },
        { name: Cities.Vahr, region: Regions.Blue, connectionCost: 6, slotCosts: [8, 14, 20], x: 424, y: 216 },
        // Pink
        { name: Cities.Schwachhausen, region: Regions.Pink, connectionCost: 5, slotCosts: [8, 14, 20], x: 328, y: 240 },
        {
            name: Cities.OstlicheVorstadt,
            region: Regions.Pink,
            connectionCost: 2,
            slotCosts: [8, 14, 20],
            x: 404,
            y: 240,
        },
        { name: Cities.Findorff, region: Regions.Pink, connectionCost: 3, slotCosts: [8, 14], x: 316, y: 282 },
        { name: Cities.Walle, region: Regions.Pink, connectionCost: 6, slotCosts: [8, 14, 20], x: 330, y: 316 },
        { name: Cities.Mitte, region: Regions.Pink, connectionCost: 1, slotCosts: [8, 14, 20], x: 368, y: 288 },
        // Purple
        { name: Cities.Hemelingen, region: Regions.Purple, connectionCost: 8, slotCosts: [8, 14, 20], x: 460, y: 216 },
        { name: Cities.Mahndorf, region: Regions.Purple, connectionCost: 10, slotCosts: [8, 14, 20], x: 520, y: 172 },
        { name: Cities.Neustadt, region: Regions.Purple, connectionCost: 5, slotCosts: [8, 14, 20], x: 488, y: 288 },
        {
            name: Cities.Obervieland,
            region: Regions.Purple,
            connectionCost: 10,
            slotCosts: [8, 14, 20],
            x: 464,
            y: 380,
        },
        { name: Cities.Huchting, region: Regions.Purple, connectionCost: 12, slotCosts: [8, 14], x: 500, y: 424 },
        // Red
        { name: Cities.Hofen, region: Regions.Red, connectionCost: 9, slotCosts: [8, 14, 20], x: 292, y: 396 },
        { name: Cities.Pusdorf, region: Regions.Red, connectionCost: 7, slotCosts: [8, 14, 20], x: 356, y: 348 },
        { name: Cities.Neustadtshafen, region: Regions.Red, connectionCost: 8, slotCosts: [8, 14, 20], x: 388, y: 380 },
        { name: Cities.Strom, region: Regions.Red, connectionCost: 14, slotCosts: [8, 14, 20], x: 432, y: 404 },
        { name: Cities.Seehausen, region: Regions.Red, connectionCost: 14, slotCosts: [8, 14], x: 328, y: 452 },
        // Orange
        { name: Cities.Blockland, region: Regions.Orange, connectionCost: 11, slotCosts: [8, 14, 20], x: 248, y: 224 },
        { name: Cities.Gropelingen, region: Regions.Orange, connectionCost: 8, slotCosts: [8, 14, 20], x: 268, y: 352 },
        { name: Cities.Burglesum, region: Regions.Orange, connectionCost: 13, slotCosts: [8, 14, 20], x: 224, y: 408 },
        { name: Cities.Vegesack, region: Regions.Orange, connectionCost: 10, slotCosts: [8, 14, 20], x: 188, y: 464 },
        { name: Cities.Blumenthal, region: Regions.Orange, connectionCost: 15, slotCosts: [8, 14], x: 136, y: 624 },
    ],
    // Bremen has flat per-district costs (the `connectionCost` on each city), not
    // per-edge costs — so every connection's `cost` is 0 and only encodes which
    // districts border each other. Crossing the Weser/Lesum rivers costs nothing
    // extra (you still pay the destination district's cost), so river borders are
    // ordinary adjacencies here (e.g. Höfen ↔ Gröpelingen). First-pass adjacency
    // read off the board photo — refine against the printed board.
    connections: [
        // Blue (internal)
        { nodes: [Cities.Borgfeld, Cities.Oberneuland], cost: 0 },
        { nodes: [Cities.Oberneuland, Cities.Osterholz], cost: 0 },
        { nodes: [Cities.Borgfeld, Cities.HornLehe], cost: 0 },
        { nodes: [Cities.Oberneuland, Cities.HornLehe], cost: 0 },
        { nodes: [Cities.Oberneuland, Cities.Vahr], cost: 0 },
        { nodes: [Cities.Osterholz, Cities.Vahr], cost: 0 },
        { nodes: [Cities.HornLehe, Cities.Vahr], cost: 0 },
        // Blue → neighbours
        { nodes: [Cities.HornLehe, Cities.Schwachhausen], cost: 0 },
        { nodes: [Cities.Vahr, Cities.OstlicheVorstadt], cost: 0 },
        { nodes: [Cities.Vahr, Cities.Hemelingen], cost: 0 },
        { nodes: [Cities.Osterholz, Cities.Mahndorf], cost: 0 },
        { nodes: [Cities.HornLehe, Cities.Blockland], cost: 0 },
        // Pink (internal)
        { nodes: [Cities.Schwachhausen, Cities.Findorff], cost: 0 },
        { nodes: [Cities.Schwachhausen, Cities.Mitte], cost: 0 },
        { nodes: [Cities.Schwachhausen, Cities.OstlicheVorstadt], cost: 0 },
        { nodes: [Cities.Findorff, Cities.Mitte], cost: 0 },
        { nodes: [Cities.Findorff, Cities.Walle], cost: 0 },
        { nodes: [Cities.Mitte, Cities.Walle], cost: 0 },
        { nodes: [Cities.Mitte, Cities.OstlicheVorstadt], cost: 0 },
        // Pink → neighbours
        { nodes: [Cities.OstlicheVorstadt, Cities.Hemelingen], cost: 0 },
        { nodes: [Cities.Walle, Cities.Gropelingen], cost: 0 },
        { nodes: [Cities.Walle, Cities.Pusdorf], cost: 0 },
        { nodes: [Cities.Mitte, Cities.Pusdorf], cost: 0 },
        { nodes: [Cities.Findorff, Cities.Blockland], cost: 0 },
        // Purple (internal)
        { nodes: [Cities.Hemelingen, Cities.Mahndorf], cost: 0 },
        { nodes: [Cities.Hemelingen, Cities.Neustadt], cost: 0 },
        { nodes: [Cities.Mahndorf, Cities.Neustadt], cost: 0 },
        { nodes: [Cities.Neustadt, Cities.Obervieland], cost: 0 },
        { nodes: [Cities.Neustadt, Cities.Huchting], cost: 0 },
        { nodes: [Cities.Obervieland, Cities.Huchting], cost: 0 },
        // Purple → neighbours
        { nodes: [Cities.Neustadt, Cities.Strom], cost: 0 },
        { nodes: [Cities.Obervieland, Cities.Strom], cost: 0 },
        { nodes: [Cities.Huchting, Cities.Seehausen], cost: 0 },
        // Red (internal)
        { nodes: [Cities.Hofen, Cities.Pusdorf], cost: 0 },
        { nodes: [Cities.Hofen, Cities.Neustadtshafen], cost: 0 },
        { nodes: [Cities.Hofen, Cities.Seehausen], cost: 0 },
        { nodes: [Cities.Pusdorf, Cities.Neustadtshafen], cost: 0 },
        { nodes: [Cities.Neustadtshafen, Cities.Seehausen], cost: 0 },
        { nodes: [Cities.Neustadtshafen, Cities.Strom], cost: 0 },
        { nodes: [Cities.Seehausen, Cities.Strom], cost: 0 },
        // Red → neighbours (Höfen ↔ Gröpelingen crosses the Weser, free)
        { nodes: [Cities.Hofen, Cities.Gropelingen], cost: 0 },
        // Orange (internal)
        { nodes: [Cities.Blockland, Cities.Gropelingen], cost: 0 },
        { nodes: [Cities.Blockland, Cities.Burglesum], cost: 0 },
        { nodes: [Cities.Gropelingen, Cities.Burglesum], cost: 0 },
        { nodes: [Cities.Burglesum, Cities.Vegesack], cost: 0 },
        { nodes: [Cities.Vegesack, Cities.Blumenthal], cost: 0 },
    ],
    layout: 'Portrait',
    // First-pass coords in board-photo space scaled ×0.4; tune adjustRatio /
    // mapPosition against the live render in the viewer session.
    adjustRatio: [1, 1],
    mapPosition: [0, 0],
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
    // Coal fills 1–8, oil 3–8, garbage 3–8, no uranium. 2 each of coal/oil/garbage
    // and all uranium are placed back in the box, so total supply is 22/22/22/0:
    // coal starts 2 short of a full market (the top price slot), oil/garbage hold
    // 4 in reserve each.
    startingResources: [22, 18, 18, 0],
    startingSupply: [22, 22, 22, 0],
    // Bremen plays with fewer power plants. Remove 11, 17, 23, 28, 34, 36, 38, 39,
    // 46 (this includes every nuclear plant); 2–4 players also remove 31 and 50.
    // The opening market is then drawn from the remaining "weak" pool (≤15) per the
    // recharged convention, and NO further player-count deck reduction is applied.
    setupDeck(numPlayers: number, variant: string, rng: seedrandom.prng) {
        const removed = new Set([11, 17, 23, 28, 34, 36, 38, 39, 46]);
        if (numPlayers <= 4) {
            removed.add(31);
            removed.add(50);
        }
        let deck = cloneDeep(powerPlants).filter((pp) => !removed.has(pp.number));
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
        'district. Small districts have only two spaces (8 / 14) and can hold just ' +
        'two networks. The Weser and Lesum rivers can be crossed without extra ' +
        'cost. No nuclear: nuclear power plants and uranium are not used. Step 2 ' +
        'begins once a player has 5 connected districts (4 for 6 players); the game ' +
        'ends when a player connects 13 districts (12 for 5 players, 11 for 6).',
};
