// by John and Cici
import { cloneDeep } from 'lodash';
import seedrandom from 'seedrandom';
import { PowerPlantType } from '../gamestate';
import { shuffle } from '../utils';
import { GameMap } from './../maps';
import { powerPlants } from './../powerPlants';

export enum Regions {
    Pink = 'pink', // UK / Ireland / Low Countries
    Red = 'red', // France / Iberia
    Brown = 'brown', // Central North (Germany / Czech / Poland-south)
    Yellow = 'yellow', // Alpine / Italy / Hungary
    Orange = 'orange', // Scandinavia / Baltic
    Blue = 'blue', // Eastern Europe (incl. Bucureşti)
    Green = 'green', // Balkans / Turkey
}

export enum Cities {
    // Pink — UK / Ireland / Low Countries
    Glasgow = 'Glasgow',
    Dublin = 'Dublin',
    Birmingham = 'Birmingham',
    London = 'London',
    Randstad = 'Randstad',
    Vlaanderen = 'Vlaanderen',
    RheinRuhr = 'Rhein-Ruhr',

    // Red — France / Iberia
    Paris = 'Paris',
    Bordeaux = 'Bordeaux',
    Lyon = 'Lyon',
    Marseille = 'Marseille',
    Lisboa = 'Lisboa',
    Madrid = 'Madrid',
    Barcelona = 'Barcelona',

    // Brown — Central North
    Bremen = 'Bremen',
    Berlin = 'Berlin',
    RheinMain = 'Rhein-Main',
    Stuttgart = 'Stuttgart',
    Praha = 'Praha',
    Katowice = 'Katowice',
    München = 'München',

    // Yellow — Alpine / Italy / Hungary
    Zürich = 'Zürich',
    Milano = 'Milano',
    Roma = 'Roma',
    Napoli = 'Napoli',
    Wien = 'Wien',
    Budapest = 'Budapest',
    Zagreb = 'Zagreb',

    // Orange — Scandinavia / Baltic
    Oslo = 'Oslo',
    Stockholm = 'Stockholm',
    Helsinki = 'Helsinki',
    Tallinn = 'Tallinn',
    Kobenhavn = 'København',
    Riga = 'Riga',
    StPetersburg = 'St. Petersburg',

    // Blue — Eastern Europe
    Minsk = 'Minsk',
    Moskwa = 'Moskwa',
    Warszawa = 'Warszawa',
    Kyjiv = 'Kyjiv',
    Kharkiv = 'Kharkiv',
    Odessa = 'Odessa',
    Bucuresti = 'Bucureşti',

    // Green — Balkans / Turkey
    Beograd = 'Beograd',
    Sofia = 'Sofia',
    Tirana = 'Tirana',
    Athina = 'Athina',
    Istanbul = 'Istanbul',
    Izmir = 'Izmir',
    Ankara = 'Ankara',
}

export const map: GameMap = {
    name: 'Europe',
    cities: [
        // Pink — UK / Ireland / Low Countries
        { name: Cities.Glasgow, region: Regions.Pink, x: 490, y: 510 },
        { name: Cities.Dublin, region: Regions.Pink, x: 390, y: 660 },
        { name: Cities.Birmingham, region: Regions.Pink, x: 485, y: 695 },
        { name: Cities.London, region: Regions.Pink, x: 545, y: 800 },
        { name: Cities.Randstad, region: Regions.Pink, x: 770, y: 770 },
        { name: Cities.Vlaanderen, region: Regions.Pink, x: 700, y: 830 },
        { name: Cities.RheinRuhr, region: Regions.Pink, x: 845, y: 860 },

        // Red — France / Iberia
        { name: Cities.Paris, region: Regions.Red, x: 730, y: 920 },
        { name: Cities.Bordeaux, region: Regions.Red, x: 655, y: 1095 },
        { name: Cities.Lyon, region: Regions.Red, x: 785, y: 1100 },
        { name: Cities.Marseille, region: Regions.Red, x: 815, y: 1240 },
        { name: Cities.Barcelona, region: Regions.Red, x: 650, y: 1280 },
        { name: Cities.Madrid, region: Regions.Red, x: 435, y: 1335 },
        { name: Cities.Lisboa, region: Regions.Red, x: 255, y: 1335 },

        // Brown — Central North (Germany / Czech / Poland-south)
        { name: Cities.Bremen, region: Regions.Brown, x: 1010, y: 770 },
        { name: Cities.Berlin, region: Regions.Brown, x: 1180, y: 800 },
        { name: Cities.RheinMain, region: Regions.Brown, x: 970, y: 920 },
        { name: Cities.Stuttgart, region: Regions.Brown, x: 995, y: 1000 },
        { name: Cities.München, region: Regions.Brown, x: 1100, y: 1050 },
        { name: Cities.Praha, region: Regions.Brown, x: 1235, y: 940 },
        { name: Cities.Katowice, region: Regions.Brown, x: 1380, y: 940 },

        // Yellow — Alpine / Italy / Hungary
        { name: Cities.Zürich, region: Regions.Yellow, x: 1010, y: 1100 },
        { name: Cities.Milano, region: Regions.Yellow, x: 1075, y: 1180 },
        { name: Cities.Roma, region: Regions.Yellow, x: 1180, y: 1310 },
        { name: Cities.Napoli, region: Regions.Yellow, x: 1235, y: 1430 },
        { name: Cities.Wien, region: Regions.Yellow, x: 1265, y: 1080 },
        { name: Cities.Budapest, region: Regions.Yellow, x: 1390, y: 1080 },
        { name: Cities.Zagreb, region: Regions.Yellow, x: 1300, y: 1180 },

        // Orange — Scandinavia / Baltic
        { name: Cities.Oslo, region: Regions.Orange, x: 1015, y: 365 },
        { name: Cities.Stockholm, region: Regions.Orange, x: 1170, y: 415 },
        { name: Cities.Helsinki, region: Regions.Orange, x: 1395, y: 360 },
        { name: Cities.Tallinn, region: Regions.Orange, x: 1410, y: 470 },
        { name: Cities.Riga, region: Regions.Orange, x: 1395, y: 575 },
        { name: Cities.Kobenhavn, region: Regions.Orange, x: 1180, y: 660 },
        { name: Cities.StPetersburg, region: Regions.Orange, x: 1620, y: 460 },

        // Blue — Eastern Europe
        { name: Cities.Warszawa, region: Regions.Blue, x: 1500, y: 815 },
        { name: Cities.Minsk, region: Regions.Blue, x: 1610, y: 815 },
        { name: Cities.Moskwa, region: Regions.Blue, x: 1830, y: 600 },
        { name: Cities.Kyjiv, region: Regions.Blue, x: 1690, y: 980 },
        { name: Cities.Kharkiv, region: Regions.Blue, x: 1860, y: 980 },
        { name: Cities.Odessa, region: Regions.Blue, x: 1720, y: 1100 },
        { name: Cities.Bucuresti, region: Regions.Blue, x: 1610, y: 1175 },

        // Green — Balkans / Turkey
        { name: Cities.Beograd, region: Regions.Green, x: 1390, y: 1175 },
        { name: Cities.Sofia, region: Regions.Green, x: 1505, y: 1240 },
        { name: Cities.Tirana, region: Regions.Green, x: 1370, y: 1330 },
        { name: Cities.Athina, region: Regions.Green, x: 1480, y: 1450 },
        { name: Cities.Istanbul, region: Regions.Green, x: 1665, y: 1335 },
        { name: Cities.Izmir, region: Regions.Green, x: 1730, y: 1430 },
        { name: Cities.Ankara, region: Regions.Green, x: 1850, y: 1380 },
    ],
    connections: [
        // Pink — UK / Ireland / Low Countries
        { nodes: [Cities.Dublin, Cities.Glasgow], cost: 17 },
        { nodes: [Cities.Glasgow, Cities.Birmingham], cost: 13 },
        { nodes: [Cities.Dublin, Cities.Birmingham], cost: 15 },
        { nodes: [Cities.Birmingham, Cities.London], cost: 4 },
        { nodes: [Cities.London, Cities.Vlaanderen], cost: 15 },
        { nodes: [Cities.London, Cities.Randstad], cost: 18 },
        { nodes: [Cities.Randstad, Cities.Vlaanderen], cost: 4 },
        { nodes: [Cities.Vlaanderen, Cities.RheinRuhr], cost: 4 },
        { nodes: [Cities.Randstad, Cities.RheinRuhr], cost: 4 },

        // Red — France / Iberia (internal)
        { nodes: [Cities.Paris, Cities.Bordeaux], cost: 12 },
        { nodes: [Cities.Paris, Cities.Lyon], cost: 11 },
        { nodes: [Cities.Bordeaux, Cities.Lyon], cost: 12 },
        { nodes: [Cities.Lyon, Cities.Marseille], cost: 8 },
        { nodes: [Cities.Bordeaux, Cities.Marseille], cost: 12 },
        { nodes: [Cities.Marseille, Cities.Barcelona], cost: 11 },
        { nodes: [Cities.Bordeaux, Cities.Barcelona], cost: 15 },
        { nodes: [Cities.Bordeaux, Cities.Madrid], cost: 15 },
        { nodes: [Cities.Madrid, Cities.Barcelona], cost: 14 },
        { nodes: [Cities.Madrid, Cities.Lisboa], cost: 13 },

        // Red ↔ Pink
        { nodes: [Cities.Paris, Cities.London], cost: 16 },
        { nodes: [Cities.Paris, Cities.Vlaanderen], cost: 7 },
        { nodes: [Cities.Paris, Cities.RheinRuhr], cost: 10 },

        // Brown — Central North (internal)
        { nodes: [Cities.Bremen, Cities.Berlin], cost: 6 },
        { nodes: [Cities.Bremen, Cities.RheinMain], cost: 9 },
        { nodes: [Cities.Berlin, Cities.RheinMain], cost: 10 },
        { nodes: [Cities.Berlin, Cities.Praha], cost: 7 },
        { nodes: [Cities.RheinMain, Cities.Praha], cost: 10 },
        { nodes: [Cities.RheinMain, Cities.München], cost: 6 },
        { nodes: [Cities.RheinMain, Cities.Stuttgart], cost: 3 },
        { nodes: [Cities.Stuttgart, Cities.München], cost: 5 },
        { nodes: [Cities.München, Cities.Praha], cost: 6 },
        { nodes: [Cities.Praha, Cities.Katowice], cost: 8 },

        // Brown ↔ Pink
        { nodes: [Cities.Bremen, Cities.Randstad], cost: 8 },
        { nodes: [Cities.Bremen, Cities.Vlaanderen], cost: 10 },
        { nodes: [Cities.RheinMain, Cities.Vlaanderen], cost: 6 },
        { nodes: [Cities.RheinMain, Cities.RheinRuhr], cost: 3 },

        // Brown ↔ Red
        { nodes: [Cities.Stuttgart, Cities.Paris], cost: 14 },

        // Yellow — Alpine / Italy / Hungary (internal)
        { nodes: [Cities.Zürich, Cities.Milano], cost: 11 },
        { nodes: [Cities.Milano, Cities.Zagreb], cost: 17 },
        { nodes: [Cities.Milano, Cities.Roma], cost: 19 },
        { nodes: [Cities.Roma, Cities.Napoli], cost: 7 },
        { nodes: [Cities.Wien, Cities.Budapest], cost: 5 },
        { nodes: [Cities.Wien, Cities.Zagreb], cost: 8 },
        { nodes: [Cities.Budapest, Cities.Zagreb], cost: 7 },

        // Yellow ↔ Red
        { nodes: [Cities.Paris, Cities.Zürich], cost: 14 },
        { nodes: [Cities.Lyon, Cities.Zürich], cost: 14 },
        { nodes: [Cities.Lyon, Cities.Milano], cost: 11 },
        { nodes: [Cities.Marseille, Cities.Milano], cost: 13 },

        // Yellow ↔ Brown
        { nodes: [Cities.Zürich, Cities.München], cost: 8 },
        { nodes: [Cities.Zürich, Cities.Stuttgart], cost: 5 },
        { nodes: [Cities.München, Cities.Wien], cost: 9 },
        { nodes: [Cities.Praha, Cities.Wien], cost: 7 },
        { nodes: [Cities.Wien, Cities.Katowice], cost: 8 },
        { nodes: [Cities.Budapest, Cities.Katowice], cost: 11 },

        // Orange — Scandinavia / Baltic (internal)
        { nodes: [Cities.Oslo, Cities.Kobenhavn], cost: 17 },
        { nodes: [Cities.Oslo, Cities.Stockholm], cost: 13 },
        { nodes: [Cities.Stockholm, Cities.Kobenhavn], cost: 18 },
        { nodes: [Cities.Stockholm, Cities.Helsinki], cost: 21 },
        { nodes: [Cities.Helsinki, Cities.StPetersburg], cost: 11 },
        { nodes: [Cities.Tallinn, Cities.StPetersburg], cost: 9 },
        { nodes: [Cities.Tallinn, Cities.Riga], cost: 7 },
        { nodes: [Cities.Riga, Cities.StPetersburg], cost: 13 },

        // Orange ↔ Brown
        { nodes: [Cities.Kobenhavn, Cities.Bremen], cost: 12 },
        { nodes: [Cities.Kobenhavn, Cities.Berlin], cost: 15 },

        // Blue — Eastern Europe (internal)
        { nodes: [Cities.Warszawa, Cities.Minsk], cost: 10 },
        { nodes: [Cities.Warszawa, Cities.Kyjiv], cost: 14 },
        { nodes: [Cities.Minsk, Cities.Moskwa], cost: 14 },
        { nodes: [Cities.Minsk, Cities.Kyjiv], cost: 10 },
        { nodes: [Cities.Moskwa, Cities.Kharkiv], cost: 16 },
        { nodes: [Cities.Kyjiv, Cities.Kharkiv], cost: 9 },
        { nodes: [Cities.Kyjiv, Cities.Odessa], cost: 9 },
        { nodes: [Cities.Kharkiv, Cities.Odessa], cost: 13 },
        { nodes: [Cities.Odessa, Cities.Bucuresti], cost: 10 },

        // Blue ↔ Brown
        { nodes: [Cities.Berlin, Cities.Warszawa], cost: 11 },
        { nodes: [Cities.Praha, Cities.Warszawa], cost: 11 },
        { nodes: [Cities.Katowice, Cities.Warszawa], cost: 5 },

        // Blue ↔ Orange
        { nodes: [Cities.Kobenhavn, Cities.Warszawa], cost: 25 },
        { nodes: [Cities.Riga, Cities.Warszawa], cost: 12 },
        { nodes: [Cities.Riga, Cities.Minsk], cost: 8 },
        { nodes: [Cities.Riga, Cities.Moskwa], cost: 18 },
        { nodes: [Cities.StPetersburg, Cities.Moskwa], cost: 14 },

        // Blue ↔ Yellow
        { nodes: [Cities.Kyjiv, Cities.Budapest], cost: 21 },
        { nodes: [Cities.Odessa, Cities.Budapest], cost: 25 },
        { nodes: [Cities.Bucuresti, Cities.Budapest], cost: 16 },

        // Green — Balkans / Turkey (internal)
        { nodes: [Cities.Beograd, Cities.Sofia], cost: 11 },
        { nodes: [Cities.Beograd, Cities.Tirana], cost: 15 },
        { nodes: [Cities.Sofia, Cities.Tirana], cost: 13 },
        { nodes: [Cities.Sofia, Cities.Athina], cost: 17 },
        { nodes: [Cities.Sofia, Cities.Istanbul], cost: 13 },
        { nodes: [Cities.Tirana, Cities.Athina], cost: 16 },
        { nodes: [Cities.Istanbul, Cities.Izmir], cost: 8 },
        { nodes: [Cities.Istanbul, Cities.Ankara], cost: 9 },
        { nodes: [Cities.Izmir, Cities.Ankara], cost: 10 },

        // Green ↔ Blue
        { nodes: [Cities.Bucuresti, Cities.Beograd], cost: 12 },
        { nodes: [Cities.Bucuresti, Cities.Sofia], cost: 9 },
        { nodes: [Cities.Bucuresti, Cities.Istanbul], cost: 13 },

        // Green ↔ Yellow
        { nodes: [Cities.Beograd, Cities.Zagreb], cost: 9 },
        { nodes: [Cities.Beograd, Cities.Napoli], cost: 18 },
        { nodes: [Cities.Beograd, Cities.Budapest], cost: 10 },
        { nodes: [Cities.Tirana, Cities.Napoli], cost: 25 },
    ],
    layout: 'Landscape',
    // Coords were authored against the printed board (~1860x1450). The map area
    // in the default landscape viewBox is roughly 0..1100 x 0..720 (player boards
    // start at x=1105, resource market at y=720). Shrink uniformly to fit and
    // shift up-left so the map sits in the top-left of that area.
    adjustRatio: [0.5, 0.5],
    mapPosition: [-30, -50],
    // Slight clockwise tilt — fits the map's NW-tall / SE-tall extents into the
    // available area better than the un-rotated layout.
    mapRotation: 10,
    // Resupply table verified with John from the Europe refill summary cards.
    // Indexed [resource][playerCount-2][step-1].
    resupply: [
        // Coal
        [
            [2, 6, 2], // 2P
            [2, 6, 2], // 3P
            [3, 7, 4], // 4P
            [3, 8, 4], // 5P
            [5, 10, 5], // 6P
        ],
        // Oil
        [
            [2, 2, 3], // 2P
            [2, 2, 3], // 3P
            [3, 3, 4], // 4P
            [4, 3, 5], // 5P
            [4, 5, 6], // 6P
        ],
        // Garbage
        [
            [2, 3, 5], // 2P
            [2, 3, 5], // 3P
            [3, 4, 5], // 4P
            [3, 5, 7], // 5P
            [4, 6, 8], // 6P
        ],
        // Uranium
        [
            [1, 1, 2], // 2P
            [1, 1, 2], // 3P
            [1, 2, 2], // 4P
            [2, 3, 3], // 5P
            [2, 3, 4], // 6P
        ],
    ],
    // Europe uses price spaces 1–9 (not the standard 1–8 with uranium ending at 16);
    // every resource — including uranium — caps at price 9.
    //
    // Per-price slot counts (verified with John from the board):
    //   Coal    [4,4,4,2,2,2,2,2,2]  total 24 market slots
    //   Oil     [2,2,2,2,2,2,2,2,4]  total 20 market slots
    //   Garbage [3,3,3,3,3,3,3,3,0]  total 24 market slots
    //   Uranium [1,1,1,1,1,1,2,2,2]  total 12 market slots
    //
    // Oil note: market capacity is 20 but we keep the total cube count at 24 for now
    // (per Mike's guidance while he tries to reach 2F-Spiele). This means oil can
    // overflow back to the supply pile and a player holding 1–2 oil on power plants
    // can briefly leave the market with oil still available at price 1. If the
    // publisher confirms otherwise, drop startingSupply oil from 24 to 20.
    coalPrices: [1, 1, 1, 1, 2, 2, 2, 2, 3, 3, 3, 3, 4, 4, 5, 5, 6, 6, 7, 7, 8, 8, 9, 9],
    oilPrices: [1, 1, 2, 2, 3, 3, 4, 4, 5, 5, 6, 6, 7, 7, 8, 8, 9, 9, 9, 9],
    garbagePrices: [1, 1, 1, 2, 2, 2, 3, 3, 3, 4, 4, 4, 5, 5, 5, 6, 6, 6, 7, 7, 7, 8, 8, 8],
    uraniumPrices: [1, 2, 3, 4, 5, 6, 7, 7, 8, 8, 9, 9],
    // Initial market fill from the rules (coal 2–9, oil 3–9, garbage 3–8, uranium 8–9):
    //   coal    = 4+4+2+2+2+2+2+2 = 20
    //   oil     = 2+2+2+2+2+2+4   = 16
    //   garbage = 3+3+3+3+3+3     = 18
    //   uranium = 2+2             = 4
    startingResources: [20, 16, 18, 4],
    // Total cubes in the game (used cubes return here; refill draws from here).
    startingSupply: [24, 24, 24, 12],
    // Europe market setup: shuffle the deck, draw 9 plants, place the 4 lowest in
    // the current market and the 5 next in the future market, with the Step 3 card
    // buried at the bottom of the deck.
    //
    // The rules call for the New Power Plants Set 2 deck ("plug-back" cards) and a
    // rule against placing a plug-back card on top of the deck — both are no-ops
    // here since this engine ships only one power-plant set. Revisit if/when Set 2
    // is added.
    //
    // The Step 2 trigger for Europe is handled in engine.ts (special branch): it
    // removes the lowest plant from the current market once, then re-sorts the
    // remaining 8 plants into 4 actual + 4 future without drawing from the deck.
    setupDeck(numPlayers: number, variant: string, rng: seedrandom.prng) {
        let powerPlantsDeck = cloneDeep(powerPlants);

        const step3Index = powerPlantsDeck.findIndex((p) => p.type === PowerPlantType.Step3);
        const step3 = powerPlantsDeck.splice(step3Index, 1)[0];

        powerPlantsDeck = shuffle(powerPlantsDeck, rng() + '');

        const initialPlants = powerPlantsDeck.splice(0, 9).sort((a, b) => a.number - b.number);
        const actualMarket = initialPlants.slice(0, 4);
        const futureMarket = initialPlants.slice(4); // 5 plants

        powerPlantsDeck.push(step3);

        return { actualMarket, futureMarket, powerPlantsDeck };
    },
    mapSpecificRules:
        'Europe uses the New Power Plants Set 2 deck (cards with a plug on the back). ' +
        'The power plant market starts as 4 current + 5 future power plants (9 total). ' +
        'When Step 2 begins, remove the lowest-numbered plant from the current market from the game once and do not replace it; the future market then has 4 plants instead of 5.',
};
