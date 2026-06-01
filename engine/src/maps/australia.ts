// by John and Cici
import { cloneDeep } from 'lodash';
import seedrandom from 'seedrandom';
import { getPowerPlant } from '../engine';
import { PowerPlant } from '../gamestate';
import { shuffle } from '../utils';
import { GameMap } from './../maps';
import { powerPlants } from './../powerPlants';

export enum Regions {
    Pink = 'pink',
    Brown = 'brown',
    Green = 'green',
    Red = 'red',
    Yellow = 'yellow',
}

export enum Cities {
    Hobart = 'Hobart',
    Launceston = 'Launceston',
    Geelong = 'Geelong',
    Melbourne1 = 'Melbourne 1',
    Melbourne2 = 'Melbourne 2',
    Bendigo = 'Bendigo',
    Albury = 'Albury',
    Wollongong = 'Wollongong',
    Mildura = 'Mildura',
    Dubbo = 'Dubbo',
    Canberra = 'Canberra',
    Sydney1 = 'Sydney 1',
    Sydney2 = 'Sydney 2',
    Newcastle = 'Newcastle',
    Toowoomba = 'Toowoomba',
    Goldcoast = 'Gold Coast',
    Brisbane = 'Brisbane',
    Rockhampton = 'Rockhampton',
    Mackay = 'Mackay',
    Townsville = 'Townsville',
    Cairns = 'Cairns',
    Porthedland = 'Port Hedland',
    Broome = 'Broome',
    Albany = 'Albany',
    Bunbury = 'Bunbury',
    Perth = 'Perth',
    Kalgoorlie = 'Kalgoorlie',
    Geraldton = 'Geraldton',
    Darwin = 'Darwin',
    Katherine = 'Katherine',
    Tennantcreek = 'Tennant Creek',
    Alicesprings = 'Alice Springs',
    Portaugusta = 'Port Augusta',
    CooberPedy = 'Coober Pedy',
    Adelaide = 'Adelaide',
}

export const map: GameMap = {
    name: 'Australia',
    layout: 'Landscape',
    adjustRatio: [0.33, 0.33],
    mapPosition: [40, -30],
    mapRotation: 180,
    cities: [
        { name: Cities.Hobart, region: Regions.Pink, x: 540, y: 467 },
        { name: Cities.Launceston, region: Regions.Pink, x: 720, y: 500 },
        { name: Cities.Geelong, region: Regions.Pink, x: 988, y: 712 },
        { name: Cities.Melbourne1, region: Regions.Pink, x: 790, y: 650 },
        { name: Cities.Melbourne2, region: Regions.Pink, x: 790, y: 790 },
        { name: Cities.Bendigo, region: Regions.Pink, x: 1052, y: 870 },
        { name: Cities.Albury, region: Regions.Brown, x: 810, y: 983 },
        { name: Cities.Wollongong, region: Regions.Brown, x: 530, y: 1080 },
        { name: Cities.Mildura, region: Regions.Pink, x: 1185, y: 1010 },
        { name: Cities.Dubbo, region: Regions.Brown, x: 891, y: 1364 },
        { name: Cities.Canberra, region: Regions.Brown, x: 804, y: 1188 },
        { name: Cities.Sydney1, region: Regions.Brown, x: 550, y: 1230 },
        { name: Cities.Sydney2, region: Regions.Brown, x: 550, y: 1380 },
        { name: Cities.Newcastle, region: Regions.Brown, x: 530, y: 1545 },
        { name: Cities.Toowoomba, region: Regions.Green, x: 1010, y: 1660 },
        { name: Cities.Goldcoast, region: Regions.Green, x: 660, y: 1730 },
        { name: Cities.Brisbane, region: Regions.Green, x: 740, y: 1885 },
        { name: Cities.Rockhampton, region: Regions.Green, x: 1040, y: 1987 },
        { name: Cities.Mackay, region: Regions.Green, x: 1260, y: 2101 },
        { name: Cities.Townsville, region: Regions.Green, x: 1445, y: 2193 },
        { name: Cities.Cairns, region: Regions.Green, x: 1652, y: 2209 },
        { name: Cities.Porthedland, region: Regions.Red, x: 2741, y: 2002 },
        { name: Cities.Broome, region: Regions.Red, x: 2503, y: 2175 },
        { name: Cities.Albany, region: Regions.Red, x: 2400, y: 850 },
        { name: Cities.Bunbury, region: Regions.Red, x: 2700, y: 1030 },
        { name: Cities.Perth, region: Regions.Red, x: 2680, y: 1230 },
        { name: Cities.Kalgoorlie, region: Regions.Red, x: 2177, y: 1295 },
        { name: Cities.Geraldton, region: Regions.Red, x: 2747, y: 1557 },
        { name: Cities.Darwin, region: Regions.Yellow, x: 2264, y: 2016 },
        { name: Cities.Katherine, region: Regions.Yellow, x: 2105, y: 1947 },
        { name: Cities.Tennantcreek, region: Regions.Yellow, x: 1905, y: 1736 },
        { name: Cities.Alicesprings, region: Regions.Yellow, x: 1803, y: 1512 },
        { name: Cities.Portaugusta, region: Regions.Yellow, x: 1520, y: 1094 },
        { name: Cities.CooberPedy, region: Regions.Yellow, x: 1850, y: 1232 },
        { name: Cities.Adelaide, region: Regions.Yellow, x: 1430, y: 863 },
    ],
    connections: [
        { nodes: [Cities.Broome, Cities.Porthedland], cost: 13 },
        { nodes: [Cities.Kalgoorlie, Cities.Geraldton], cost: 16 },
        { nodes: [Cities.Geraldton, Cities.Perth], cost: 9 },
        { nodes: [Cities.Perth, Cities.Kalgoorlie], cost: 12 },
        { nodes: [Cities.Kalgoorlie, Cities.Albany], cost: 16 },
        { nodes: [Cities.Albany, Cities.Perth], cost: 9 },
        { nodes: [Cities.Perth, Cities.Bunbury], cost: 4 },
        { nodes: [Cities.Bunbury, Cities.Albany], cost: 6 },
        { nodes: [Cities.Cairns, Cities.Townsville], cost: 9 },
        { nodes: [Cities.Townsville, Cities.Mackay], cost: 9 },
        { nodes: [Cities.Mackay, Cities.Rockhampton], cost: 8 },
        { nodes: [Cities.Rockhampton, Cities.Toowoomba], cost: 15 },
        { nodes: [Cities.Toowoomba, Cities.Brisbane], cost: 5 },
        { nodes: [Cities.Brisbane, Cities.Rockhampton], cost: 15 },
        { nodes: [Cities.Brisbane, Cities.Goldcoast], cost: 2 },
        { nodes: [Cities.Goldcoast, Cities.Toowoomba], cost: 6 },
        { nodes: [Cities.Goldcoast, Cities.Newcastle], cost: 15 },
        { nodes: [Cities.Newcastle, Cities.Sydney2], cost: 4 },
        { nodes: [Cities.Sydney2, Cities.Sydney1], cost: 0 },
        { nodes: [Cities.Newcastle, Cities.Dubbo], cost: 10 },
        { nodes: [Cities.Dubbo, Cities.Toowoomba], cost: 18 },
        { nodes: [Cities.Sydney1, Cities.Wollongong], cost: 2 },
        { nodes: [Cities.Sydney1, Cities.Canberra], cost: 8 },
        { nodes: [Cities.Canberra, Cities.Dubbo], cost: 11 },
        { nodes: [Cities.Canberra, Cities.Newcastle], cost: 10 },
        { nodes: [Cities.Dubbo, Cities.Mildura], cost: 16 },
        { nodes: [Cities.Mildura, Cities.Canberra], cost: 16 },
        { nodes: [Cities.Canberra, Cities.Albury], cost: 7 },
        { nodes: [Cities.Mildura, Cities.Bendigo], cost: 7 },
        { nodes: [Cities.Bendigo, Cities.Melbourne2], cost: 3 },
        { nodes: [Cities.Melbourne2, Cities.Albury], cost: 9 },
        { nodes: [Cities.Mildura, Cities.Adelaide], cost: 8 },
        { nodes: [Cities.Adelaide, Cities.Portaugusta], cost: 7 },
        { nodes: [Cities.Portaugusta, Cities.CooberPedy], cost: 11 },
        { nodes: [Cities.Mildura, Cities.Portaugusta], cost: 11 },
        { nodes: [Cities.Adelaide, Cities.Geelong], cost: 13 },
        { nodes: [Cities.Geelong, Cities.Bendigo], cost: 5 },
        { nodes: [Cities.Bendigo, Cities.Albury], cost: 6 },
        { nodes: [Cities.Wollongong, Cities.Melbourne1], cost: 19 },
        { nodes: [Cities.Melbourne1, Cities.Launceston], cost: 19 },
        { nodes: [Cities.Launceston, Cities.Hobart], cost: 5 },
        { nodes: [Cities.Melbourne1, Cities.Geelong], cost: 2 },
        { nodes: [Cities.Melbourne2, Cities.Melbourne1], cost: 0 },
        { nodes: [Cities.CooberPedy, Cities.Alicesprings], cost: 13 },
        { nodes: [Cities.Alicesprings, Cities.Tennantcreek], cost: 10 },
        { nodes: [Cities.Tennantcreek, Cities.Katherine], cost: 14 },
        { nodes: [Cities.Katherine, Cities.Darwin], cost: 6 },
    ],

    // Resupply per Australia refill summary cards. Indexed as
    // [resource][playerCount-2][step-1]. Uranium is left at 0 here: Australia has
    // no uranium row in the MAIN market — uranium is bought/sold in a separate
    // 12-slot uranium market whose (negative) resupply is handled by that market
    // module, not this table. See mapSpecificRules and session-3 work.
    resupply: [
        // Coal
        [
            [3, 5, 4], // 2P
            [4, 6, 4], // 3P
            [4, 7, 5], // 4P
            [5, 9, 6], // 5P
            [7, 10, 7], // 6P
        ],
        // Oil
        [
            [1, 2, 3], // 2P
            [1, 2, 3], // 3P
            [2, 3, 4], // 4P
            [3, 3, 5], // 5P
            [3, 5, 6], // 6P
        ],
        // Garbage
        [
            [1, 2, 3], // 2P
            [1, 2, 3], // 3P
            [2, 3, 4], // 4P
            [3, 3, 5], // 5P
            [3, 5, 6], // 6P
        ],
        // Uranium — handled by the separate uranium market (session 3), not here.
        [
            [0, 0, 0], // 2P
            [0, 0, 0], // 3P
            [0, 0, 0], // 4P
            [0, 0, 0], // 5P
            [0, 0, 0], // 6P
        ],
    ],
    // Uranium-mine market refill: tokens REMOVED from the cheapest filled slots
    // each round, per the Australia refill summary cards. Indexed [players-2][step-1].
    uraniumMineResupply: [
        [1, 2, 3], // 2P
        [1, 2, 3], // 3P
        [2, 2, 4], // 4P
        [2, 3, 5], // 5P
        [3, 3, 6], // 6P
    ],
    // Main market start fill (no uranium row): coal 1–8 full, oil 3–8, garbage
    // 4–8 ⇒ 3 cubes per active price slot. Uranium starts at 0 in the main
    // market — it lives in the separate uranium market.
    startingResources: [24, 18, 15, 0],
    // Total cubes available to the main market. Uranium supply is 0 here; the
    // uranium market owns its own 12 tokens.
    startingSupply: [24, 24, 24, 0],
    // Australia removes uranium power plant #17 from the deck (the other five
    // uranium plants — 11/23/28/34/39 — stay in and become "uranium mines").
    // Everything else follows the standard recharged/original deck setup, exactly
    // as South Africa does for plant 07.
    setupDeck(numPlayers: number, variant: string, rng: seedrandom.prng) {
        let powerPlantsDeck = cloneDeep(powerPlants).filter((pp) => pp.number !== 17);
        let actualMarket: PowerPlant[];
        let futureMarket: PowerPlant[];

        if (variant == 'original') {
            powerPlantsDeck = powerPlantsDeck.slice(8);
            const powerPlant13Idx = powerPlantsDeck.findIndex((pp) => pp.number == 13);
            const powerPlant13 = powerPlantsDeck.splice(powerPlant13Idx, 1)[0];
            const step3 = powerPlantsDeck.pop()!;

            powerPlantsDeck = shuffle(powerPlantsDeck, rng() + '');
            if (numPlayers == 2 || numPlayers == 3) {
                powerPlantsDeck = powerPlantsDeck.slice(8);
            } else if (numPlayers == 4) {
                powerPlantsDeck = powerPlantsDeck.slice(4);
            }

            powerPlantsDeck.unshift(powerPlant13);
            powerPlantsDeck.push(step3);

            actualMarket = [getPowerPlant(3), getPowerPlant(4), getPowerPlant(5), getPowerPlant(6)];
            futureMarket = [getPowerPlant(7), getPowerPlant(8), getPowerPlant(9), getPowerPlant(10)];
        } else {
            let initialPowerPlants = shuffle(powerPlantsDeck.splice(0, 12), rng() + '');
            let initialPlantMarket = initialPowerPlants.splice(0, 8);
            initialPlantMarket = initialPlantMarket.sort((a, b) => a.number - b.number);
            actualMarket = initialPlantMarket.slice(0, 4);
            futureMarket = initialPlantMarket.slice(4);

            const first = initialPowerPlants.shift()!;
            const step3 = powerPlantsDeck.pop()!;

            powerPlantsDeck = shuffle(powerPlantsDeck, rng() + '');
            if (numPlayers == 2 || numPlayers == 3) {
                initialPowerPlants = initialPowerPlants.slice(2);
                powerPlantsDeck = shuffle(powerPlantsDeck.slice(6).concat(initialPowerPlants), rng() + '');
            } else if (numPlayers == 4) {
                initialPowerPlants = initialPowerPlants.slice(1);
                powerPlantsDeck = shuffle(powerPlantsDeck.slice(3).concat(initialPowerPlants), rng() + '');
            } else {
                powerPlantsDeck = shuffle(powerPlantsDeck.concat(initialPowerPlants), rng() + '');
            }

            powerPlantsDeck.unshift(first);
            powerPlantsDeck.push(step3);
        }

        return { actualMarket, futureMarket, powerPlantsDeck };
    },
    mapSpecificRules:
        'Uranium mines: the five uranium power plants (11, 23, 28, 34, 39) are ' +
        'replaced by uranium mines. Power plant 17 is removed from the deck. Mines ' +
        'are bought in the normal power-plant auctions but do not power cities and ' +
        'do not count toward the 3-power-plant hand limit (a player may hold any ' +
        'number of mines plus up to 3 power plants). Mines DO count for player order. ' +
        'Instead of powering cities, during Bureaucracy each mine produces uranium ' +
        'for sale on the separate uranium market. ' +
        'Uranium market: a separate market of 12 slots (prices $2–$7, two slots each), ' +
        'all filled at game start. When selling, a player earns the highest available ' +
        '(empty-slot) price times the total cities their mines could power, then places ' +
        'one uranium token per mine on the highest empty slots. The resource-market ' +
        'refill REMOVES uranium tokens from the cheapest filled slots. Selling happens ' +
        'AUTOMATICALLY during Bureaucracy, in reverse turn order (the last player in ' +
        'turn order sells first). The printed rules let a player decline to sell; for ' +
        'simplicity this implementation always sells, so no player action is required. ' +
        'Unlike city income, uranium income is still paid in the final round. ' +
        'Main resource market: there is no uranium row — coal, oil and garbage only. ' +
        'Step 3 CO2 tax: when Step 3 begins, the six cheapest tokens of each resource ' +
        'move into new $9 and $10 spaces, and the $1 and $2 spaces become inactive for ' +
        'the rest of the game (the market shifts up by $2). ' +
        'General connection: any single build may connect a city for a flat 20 Elektro ' +
        'instead of the shortest-path connection cost, and this may be used multiple ' +
        'times in one turn. ' +
        'Metropolises: Melbourne and Sydney each consist of two cities (1 and 2) ' +
        'connected by a 0-cost edge. ' +
        'Regions need not be adjacent: any combination of regions may be in play.',
};
