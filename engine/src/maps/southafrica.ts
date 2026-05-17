// by John and Cici
import { cloneDeep } from 'lodash';
import seedrandom from 'seedrandom';
import { getPowerPlant } from '../engine';
import { PowerPlant } from '../gamestate';
import { shuffle } from '../utils';
import { GameMap } from './../maps';
import { powerPlants } from './../powerPlants';

export enum Regions {
    Orange = 'orange',
    Green = 'green',
    Yellow = 'yellow',
    Brown = 'brown',
    Red = 'red',
}

export enum Cities {
    Zimbabwe = 'Zimbabwe',
    Musina = 'Musina',
    Botswana = 'Botswana',
    Polokwane = 'Polokwane',
    PretoriaN = 'Pretoria N',
    PretoriaS = 'Pretoria S',
    Rustenburg = 'Rustenburg',
    Mozambique = 'Mozambique',
    Mbombela = 'Mbombela',
    Eswatini = 'Eswatini',
    Germiston = 'Germiston',
    JohannesburgN = 'Johannesburg N',
    JohannesburgS = 'Johannesburg S',
    Ladysmith = 'Ladysmith',
    Newcastle = 'Newcastle',
    Pietermaritzburg = 'Pietermaritzburg',
    DurbanN = 'Durban N',
    DurbanS = 'Durban S',
    Mthatha = 'Mthatha',
    Lesotho = 'Lesotho',
    Bloemfontein = 'Bloemfontein',
    Klerksdorp = 'Klerksdorp',
    Welkom = 'Welkom',
    Kuruman = 'Kuruman',
    Kimberly = 'Kimberly',
    Upington = 'Upington',
    Springbok = 'Springbok',
    Namibia = 'Namibia',
    DeAar = 'De Aar',
    BeaufortWest = 'Beaufort West',
    EastLondon = 'East London',
    PortElizabeth = 'Port Elizabeth',
    George = 'George',
    CapeTownN = 'Cape Town N',
    CapeTownS = 'Cape Town S',
}

export const map: GameMap = {
    name: 'South Africa',
    cities: [
        { name: Cities.Zimbabwe, region: Regions.Orange, x: 903, y: 50, singleOccupancy: true },
        { name: Cities.Musina, region: Regions.Orange, x: 874, y: 134 },
        { name: Cities.Botswana, region: Regions.Orange, x: 560, y: 187, singleOccupancy: true },
        { name: Cities.Polokwane, region: Regions.Orange, x: 802, y: 189 },
        { name: Cities.PretoriaN, region: Regions.Orange, x: 759, y: 261 },
        { name: Cities.PretoriaS, region: Regions.Orange, x: 759, y: 291 },
        { name: Cities.Rustenburg, region: Regions.Orange, x: 632, y: 232 },
        { name: Cities.Mozambique, region: Regions.Green, x: 1011, y: 170, singleOccupancy: true },
        { name: Cities.Mbombela, region: Regions.Green, x: 891, y: 275 },
        { name: Cities.Eswatini, region: Regions.Green, x: 926, y: 351, singleOccupancy: true },
        { name: Cities.Germiston, region: Regions.Green, x: 836, y: 351 },
        { name: Cities.JohannesburgN, region: Regions.Green, x: 753, y: 343 },
        { name: Cities.JohannesburgS, region: Regions.Green, x: 754, y: 371 },
        { name: Cities.Ladysmith, region: Regions.Green, x: 823, y: 456 },
        { name: Cities.Newcastle, region: Regions.Yellow, x: 957, y: 478 },
        { name: Cities.Pietermaritzburg, region: Regions.Yellow, x: 851, y: 511 },
        { name: Cities.DurbanN, region: Regions.Yellow, x: 894, y: 563 },
        { name: Cities.DurbanS, region: Regions.Yellow, x: 893, y: 592 },
        { name: Cities.Mthatha, region: Regions.Yellow, x: 791, y: 663 },
        { name: Cities.Lesotho, region: Regions.Yellow, x: 759, y: 523, singleOccupancy: true },
        { name: Cities.Bloemfontein, region: Regions.Yellow, x: 656, y: 509 },
        { name: Cities.Klerksdorp, region: Regions.Brown, x: 660, y: 362 },
        { name: Cities.Welkom, region: Regions.Brown, x: 652, y: 431 },
        { name: Cities.Kuruman, region: Regions.Brown, x: 499, y: 386 },
        { name: Cities.Kimberly, region: Regions.Brown, x: 564, y: 496 },
        { name: Cities.Upington, region: Regions.Brown, x: 378, y: 453 },
        { name: Cities.Springbok, region: Regions.Brown, x: 211, y: 530 },
        { name: Cities.Namibia, region: Regions.Brown, x: 189, y: 311, singleOccupancy: true },
        { name: Cities.DeAar, region: Regions.Red, x: 539, y: 665 },
        { name: Cities.BeaufortWest, region: Regions.Red, x: 427, y: 705 },
        { name: Cities.EastLondon, region: Regions.Red, x: 722, y: 750 },
        { name: Cities.PortElizabeth, region: Regions.Red, x: 600, y: 811 },
        { name: Cities.George, region: Regions.Red, x: 439, y: 811 },
        { name: Cities.CapeTownN, region: Regions.Red, x: 233, y: 783 },
        { name: Cities.CapeTownS, region: Regions.Red, x: 231, y: 812 },
    ],
    connections: [
        { nodes: [Cities.Springbok, Cities.Namibia], cost: 30 },
        { nodes: [Cities.Bloemfontein, Cities.Lesotho], cost: 30 },
        { nodes: [Cities.Germiston, Cities.Eswatini], cost: 30 },
        { nodes: [Cities.Mbombela, Cities.Mozambique], cost: 30 },
        { nodes: [Cities.Botswana, Cities.Rustenburg], cost: 30 },
        { nodes: [Cities.Zimbabwe, Cities.Musina], cost: 30 },
        { nodes: [Cities.CapeTownS, Cities.CapeTownN], cost: 0 },
        { nodes: [Cities.CapeTownS, Cities.George], cost: 16 },
        { nodes: [Cities.George, Cities.PortElizabeth], cost: 12 },
        { nodes: [Cities.PortElizabeth, Cities.EastLondon], cost: 13 },
        { nodes: [Cities.EastLondon, Cities.Mthatha], cost: 8 },
        { nodes: [Cities.Mthatha, Cities.DurbanS], cost: 13 },
        { nodes: [Cities.DurbanS, Cities.DurbanN], cost: 0 },
        { nodes: [Cities.DurbanN, Cities.Pietermaritzburg], cost: 3 },
        { nodes: [Cities.DurbanN, Cities.Newcastle], cost: 9 },
        { nodes: [Cities.Newcastle, Cities.Pietermaritzburg], cost: 9 },
        { nodes: [Cities.Pietermaritzburg, Cities.Ladysmith], cost: 5 },
        { nodes: [Cities.Ladysmith, Cities.Newcastle], cost: 10 },
        { nodes: [Cities.Bloemfontein, Cities.Mthatha], cost: 18 },
        { nodes: [Cities.Bloemfontein, Cities.EastLondon], cost: 22 },
        { nodes: [Cities.EastLondon, Cities.DeAar], cost: 22 },
        { nodes: [Cities.DeAar, Cities.PortElizabeth], cost: 18 },
        { nodes: [Cities.George, Cities.DeAar], cost: 17 },
        { nodes: [Cities.DeAar, Cities.BeaufortWest], cost: 10 },
        { nodes: [Cities.BeaufortWest, Cities.George], cost: 8 },
        { nodes: [Cities.BeaufortWest, Cities.CapeTownN], cost: 22 },
        { nodes: [Cities.CapeTownN, Cities.Springbok], cost: 22 },
        { nodes: [Cities.Springbok, Cities.BeaufortWest], cost: 24 },
        { nodes: [Cities.DeAar, Cities.Springbok], cost: 26 },
        { nodes: [Cities.Springbok, Cities.Upington], cost: 16 },
        { nodes: [Cities.Upington, Cities.DeAar], cost: 16 },
        { nodes: [Cities.DeAar, Cities.Bloemfontein], cost: 13 },
        { nodes: [Cities.Bloemfontein, Cities.Kimberly], cost: 6 },
        { nodes: [Cities.Kimberly, Cities.DeAar], cost: 10 },
        { nodes: [Cities.Kimberly, Cities.Upington], cost: 14 },
        { nodes: [Cities.Kimberly, Cities.Welkom], cost: 9 },
        { nodes: [Cities.Welkom, Cities.Bloemfontein], cost: 6 },
        { nodes: [Cities.Bloemfontein, Cities.Ladysmith], cost: 19 },
        { nodes: [Cities.Mthatha, Cities.Pietermaritzburg], cost: 12 },
        { nodes: [Cities.Upington, Cities.Kuruman], cost: 11 },
        { nodes: [Cities.Musina, Cities.Polokwane], cost: 8 },
        { nodes: [Cities.Polokwane, Cities.PretoriaN], cost: 11 },
        { nodes: [Cities.PretoriaN, Cities.PretoriaS], cost: 0 },
        { nodes: [Cities.PretoriaS, Cities.JohannesburgN], cost: 2 },
        { nodes: [Cities.JohannesburgN, Cities.JohannesburgS], cost: 0 },
        { nodes: [Cities.JohannesburgS, Cities.Germiston], cost: 1 },
        { nodes: [Cities.JohannesburgN, Cities.Mbombela], cost: 13 },
        { nodes: [Cities.Mbombela, Cities.Germiston], cost: 13 },
        { nodes: [Cities.PretoriaN, Cities.Mbombela], cost: 13 },
        { nodes: [Cities.Mbombela, Cities.Polokwane], cost: 10 },
        { nodes: [Cities.Musina, Cities.Mbombela], cost: 15 },
        { nodes: [Cities.PretoriaN, Cities.Rustenburg], cost: 4 },
        { nodes: [Cities.Rustenburg, Cities.JohannesburgN], cost: 4 },
        { nodes: [Cities.JohannesburgN, Cities.Klerksdorp], cost: 7 },
        { nodes: [Cities.Klerksdorp, Cities.Welkom], cost: 5 },
        { nodes: [Cities.Bloemfontein, Cities.JohannesburgS], cost: 16 },
        { nodes: [Cities.Kuruman, Cities.Rustenburg], cost: 18 },
        { nodes: [Cities.Klerksdorp, Cities.Kuruman], cost: 12 },
        { nodes: [Cities.Kuruman, Cities.Kimberly], cost: 8 },
        { nodes: [Cities.JohannesburgS, Cities.Ladysmith], cost: 13 },
        { nodes: [Cities.Ladysmith, Cities.Germiston], cost: 13 },
    ],

    // Resupply per South Africa refill summary cards. Indexed as
    // [resource][playerCount-2][step-1]. Note: 2P and 3P rows are intentionally
    // identical on the printed cards (same pattern as North America).
    resupply: [
        // Coal
        [
            [4, 7, 5], // 2P
            [4, 7, 5], // 3P
            [5, 8, 6], // 4P
            [6, 9, 7], // 5P
            [7, 10, 8], // 6P
        ],
        // Oil
        [
            [1, 2, 1], // 2P
            [1, 2, 1], // 3P
            [2, 3, 2], // 4P
            [2, 4, 3], // 5P
            [4, 5, 4], // 6P
        ],
        // Garbage
        [
            [1, 3, 3], // 2P
            [1, 3, 3], // 3P
            [2, 4, 4], // 4P
            [3, 4, 5], // 5P
            [3, 6, 6], // 6P
        ],
        // Uranium
        [
            [1, 1, 2], // 2P
            [1, 1, 2], // 3P
            [2, 2, 3], // 4P
            [2, 3, 3], // 5P
            [2, 3, 4], // 6P
        ],
    ],
    layout: 'Landscape',
    // Cities authored at photo-coord scale (~1200x863). First-pass fit into the
    // standard 1500x800 landscape viewBox — tune after first render.
    adjustRatio: [0.9, 0.75],
    mapPosition: [70, 50],
    mapRotation: 0,
    // SA uses the engine default 8-price market (24 coal / 24 oil / 24 garbage
    // slots + 12 uranium 1–8 + 10/12/14/16), so we don't override coal/oil/
    // garbage/uranium Prices. Only the starting fill differs:
    //   coal    1–8 full     = 24
    //   oil     4–8          = 15
    //   garbage 5–8          = 12
    //   uranium 12–16 only   = 3
    startingResources: [24, 15, 12, 3],
    // Total cubes in the game (used cubes return here; refill draws from here).
    // For SA, USED coal goes to the separate coalStorage pool instead — see
    // GameState.coalStorage and the UsePowerPlant/resupply branches in engine.ts.
    startingSupply: [24, 24, 24, 12],
    // SA removes oil power plant 07 from the deck; the rest follows the standard
    // recharged/original deck setup. With 07 gone the "starter pool" is one
    // plant shorter (12 instead of 13 for recharged; future market shifts to
    // 8/9/10/11 instead of 7/8/9/10 for original).
    setupDeck(numPlayers: number, variant: string, rng: seedrandom.prng) {
        let powerPlantsDeck = cloneDeep(powerPlants).filter((pp) => pp.number !== 7);
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
            futureMarket = [getPowerPlant(8), getPowerPlant(9), getPowerPlant(10), getPowerPlant(11)];
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
        'Coal storage: there is a separate storage space below the resource market, ' +
        'empty at game start. Coal used to power plants returns to this storage space ' +
        '(not the main supply). The resource-market refill draws coal from storage ' +
        'first, then from the main supply. Players can always buy coal for $8 from ' +
        'the storage space (in addition to the standard market price). ' +
        'Metropolises: Cape Town, Durban, Johannesburg and Pretoria each consist of ' +
        'two cities (N and S) connected by a 0-cost edge. ' +
        'Cross-border connections: the six 30-Elektro connections to neighboring ' +
        'countries (Namibia, Botswana, Zimbabwe, Mozambique, Eswatini, Lesotho) are ' +
        'available from the start of the game. The 30 Elektro is the complete cost ' +
        '— no house-base cost is added on top. Only a single player can build on ' +
        'each cross-border space (cap of 1 instead of the standard 3). ' +
        'Power plant 07 is removed from the deck.',
};
