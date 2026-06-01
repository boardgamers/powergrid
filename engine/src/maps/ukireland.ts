// by John and Cici
import { cloneDeep } from 'lodash';
import seedrandom from 'seedrandom';
import { getPowerPlant } from '../engine';
import { PowerPlant } from '../gamestate';
import { shuffle } from '../utils';
import { GameMap } from './../maps';
import { powerPlants } from './../powerPlants';

export enum Regions {
    Red = 'red',
    Pink = 'pink',
    Yellow = 'yellow',
    Brown = 'brown',
    Orange = 'orange',
    Green = 'green',
}

export enum Cities {
    Norwich = 'Norwich',
    London1 = 'London 1',
    London2 = 'London 2',
    Brighton = 'Brighton',
    Southampton = 'Southampton',
    Plymouth = 'Plymouth',
    Leicester = 'Leicester',
    Bristol = 'Bristol',
    Newcastleupontyne = 'Newcastle Upon Tyne',
    Leeds = 'Leeds',
    Sheffield = 'Sheffield',
    Nottingham = 'Nottingham',
    Birmingham = 'Birmingham',
    Manchester = 'Manchester',
    Liverpool = 'Liverpool',
    Newportcasnewydd = 'Newport Casnewydd',
    Bangor = 'Bangor',
    Aberystwyth = 'Aberystwyth',
    Swanseaabertawe = 'Swansea Abertawe',
    Cardiffcaerdydd = 'Cardiff Caerdydd',
    Haverfordwesthwlffordd = 'Haverfordwest Hwlffordd',
    Invernessinbhirnis = 'Inverness Inbhir Nis',
    Aberdeenobardheathain = 'Aberdeen Obar Dheathain',
    Dundeedundeach = 'Dundee Dun Deach',
    Perthpeairt = 'Perth Peairt',
    Edinburgh = 'Edinburgh',
    Dumfries = 'Dumfries',
    Glasgow = 'Glasgow',
    Coleraine = 'Coleraine',
    Derry = 'Derry',
    Belfast = 'Belfast',
    Newry = 'Newry',
    Omagh = 'Omagh',
    Sligo = 'Sligo',
    Dublin = 'Dublin',
    Waterford = 'Waterford',
    Cork = 'Cork',
    Athlone = 'Athlone',
    Galway = 'Galway',
    Limerick = 'Limerick',
}

export const map: GameMap = {
    name: 'UK & Ireland',
    cities: [
        { name: Cities.Norwich, region: Regions.Red, island: 'gb', x: 646, y: 702 },
        { name: Cities.London1, region: Regions.Red, island: 'gb', x: 554, y: 756 },
        { name: Cities.London2, region: Regions.Red, island: 'gb', x: 550, y: 780 },
        { name: Cities.Brighton, region: Regions.Red, island: 'gb', x: 537, y: 837 },
        { name: Cities.Southampton, region: Regions.Red, island: 'gb', x: 451, y: 805 },
        { name: Cities.Plymouth, region: Regions.Red, island: 'gb', x: 312, y: 814 },
        { name: Cities.Leicester, region: Regions.Red, island: 'gb', x: 540, y: 680 },
        { name: Cities.Bristol, region: Regions.Red, island: 'gb', x: 425, y: 762 },
        { name: Cities.Newcastleupontyne, region: Regions.Pink, island: 'gb', x: 550, y: 414 },
        { name: Cities.Leeds, region: Regions.Pink, island: 'gb', x: 559, y: 541 },
        { name: Cities.Sheffield, region: Regions.Pink, island: 'gb', x: 530, y: 590 },
        { name: Cities.Nottingham, region: Regions.Pink, island: 'gb', x: 531, y: 632 },
        { name: Cities.Birmingham, region: Regions.Pink, island: 'gb', x: 465, y: 663 },
        { name: Cities.Manchester, region: Regions.Pink, island: 'gb', x: 479, y: 543 },
        { name: Cities.Liverpool, region: Regions.Pink, island: 'gb', x: 433, y: 576 },
        { name: Cities.Newportcasnewydd, region: Regions.Yellow, island: 'gb', x: 425, y: 722 },
        { name: Cities.Bangor, region: Regions.Yellow, island: 'gb', x: 348, y: 574 },
        { name: Cities.Aberystwyth, region: Regions.Yellow, island: 'gb', x: 357, y: 639 },
        { name: Cities.Swanseaabertawe, region: Regions.Yellow, island: 'gb', x: 346, y: 706 },
        { name: Cities.Cardiffcaerdydd, region: Regions.Yellow, island: 'gb', x: 357, y: 741 },
        { name: Cities.Haverfordwesthwlffordd, region: Regions.Yellow, island: 'gb', x: 303, y: 673 },
        { name: Cities.Invernessinbhirnis, region: Regions.Brown, island: 'gb', x: 479, y: 208 },
        { name: Cities.Aberdeenobardheathain, region: Regions.Brown, island: 'gb', x: 588, y: 245 },
        { name: Cities.Dundeedundeach, region: Regions.Brown, island: 'gb', x: 552, y: 286 },
        { name: Cities.Perthpeairt, region: Regions.Brown, island: 'gb', x: 489, y: 307 },
        { name: Cities.Edinburgh, region: Regions.Brown, island: 'gb', x: 494, y: 350 },
        { name: Cities.Dumfries, region: Regions.Brown, island: 'gb', x: 441, y: 417 },
        { name: Cities.Glasgow, region: Regions.Brown, island: 'gb', x: 422, y: 335 },
        { name: Cities.Coleraine, region: Regions.Orange, island: 'ie', x: 330, y: 367 },
        { name: Cities.Derry, region: Regions.Orange, island: 'ie', x: 256, y: 362 },
        { name: Cities.Belfast, region: Regions.Orange, island: 'ie', x: 342, y: 421 },
        { name: Cities.Newry, region: Regions.Orange, island: 'ie', x: 298, y: 462 },
        { name: Cities.Omagh, region: Regions.Orange, island: 'ie', x: 260, y: 403 },
        { name: Cities.Sligo, region: Regions.Green, island: 'ie', x: 181, y: 411 },
        { name: Cities.Dublin, region: Regions.Green, island: 'ie', x: 274, y: 530 },
        { name: Cities.Waterford, region: Regions.Green, island: 'ie', x: 210, y: 611 },
        { name: Cities.Cork, region: Regions.Green, island: 'ie', x: 114, y: 626 },
        { name: Cities.Athlone, region: Regions.Green, island: 'ie', x: 200, y: 489 },
        { name: Cities.Galway, region: Regions.Green, island: 'ie', x: 112, y: 486 },
        { name: Cities.Limerick, region: Regions.Green, island: 'ie', x: 122, y: 546 },
    ],
    connections: [
        { nodes: [Cities.Nottingham, Cities.Leicester], cost: 4 },
        { nodes: [Cities.London1, Cities.London2], cost: 0 },
        { nodes: [Cities.London2, Cities.Brighton], cost: 6 },
        { nodes: [Cities.Brighton, Cities.Southampton], cost: 7 },
        { nodes: [Cities.Southampton, Cities.Plymouth], cost: 19 },
        { nodes: [Cities.Plymouth, Cities.Bristol], cost: 14 },
        { nodes: [Cities.Bristol, Cities.Newportcasnewydd], cost: 7 },
        { nodes: [Cities.Cardiffcaerdydd, Cities.Swanseaabertawe], cost: 7 },
        { nodes: [Cities.Swanseaabertawe, Cities.Newportcasnewydd], cost: 8 },
        { nodes: [Cities.Newportcasnewydd, Cities.Cardiffcaerdydd], cost: 3 },
        { nodes: [Cities.Bristol, Cities.Southampton], cost: 11 },
        { nodes: [Cities.Southampton, Cities.London2], cost: 9 },
        { nodes: [Cities.London2, Cities.Bristol], cost: 14 },
        { nodes: [Cities.London1, Cities.Newportcasnewydd], cost: 16 },
        { nodes: [Cities.Haverfordwesthwlffordd, Cities.Aberystwyth], cost: 9 },
        { nodes: [Cities.Haverfordwesthwlffordd, Cities.Swanseaabertawe], cost: 8 },
        { nodes: [Cities.Swanseaabertawe, Cities.Aberystwyth], cost: 11 },
        { nodes: [Cities.Aberystwyth, Cities.Bangor], cost: 11 },
        { nodes: [Cities.Bangor, Cities.Liverpool], cost: 9 },
        { nodes: [Cities.Liverpool, Cities.Aberystwyth], cost: 16 },
        { nodes: [Cities.Aberystwyth, Cities.Newportcasnewydd], cost: 14 },
        { nodes: [Cities.Aberystwyth, Cities.Birmingham], cost: 16 },
        { nodes: [Cities.Birmingham, Cities.Liverpool], cost: 12 },
        { nodes: [Cities.Birmingham, Cities.Newportcasnewydd], cost: 9 },
        { nodes: [Cities.London1, Cities.Norwich], cost: 11 },
        { nodes: [Cities.Norwich, Cities.Leicester], cost: 12 },
        { nodes: [Cities.Leicester, Cities.London1], cost: 10 },
        { nodes: [Cities.London1, Cities.Birmingham], cost: 13 },
        { nodes: [Cities.Birmingham, Cities.Leicester], cost: 6 },
        { nodes: [Cities.Birmingham, Cities.Nottingham], cost: 7 },
        { nodes: [Cities.Nottingham, Cities.Sheffield], cost: 6 },
        { nodes: [Cities.Sheffield, Cities.Leeds], cost: 5 },
        { nodes: [Cities.Leeds, Cities.Manchester], cost: 8 },
        { nodes: [Cities.Manchester, Cities.Sheffield], cost: 8 },
        { nodes: [Cities.Sheffield, Cities.Liverpool], cost: 12 },
        { nodes: [Cities.Liverpool, Cities.Nottingham], cost: 15 },
        { nodes: [Cities.Manchester, Cities.Dumfries], cost: 18 },
        { nodes: [Cities.Manchester, Cities.Newcastleupontyne], cost: 15 },
        { nodes: [Cities.Newcastleupontyne, Cities.Dumfries], cost: 12 },
        { nodes: [Cities.Dumfries, Cities.Edinburgh], cost: 12 },
        { nodes: [Cities.Edinburgh, Cities.Newcastleupontyne], cost: 13 },
        { nodes: [Cities.Newcastleupontyne, Cities.Leeds], cost: 13 },
        { nodes: [Cities.Dumfries, Cities.Glasgow], cost: 11 },
        { nodes: [Cities.Glasgow, Cities.Edinburgh], cost: 7 },
        { nodes: [Cities.Glasgow, Cities.Perthpeairt], cost: 10 },
        { nodes: [Cities.Perthpeairt, Cities.Dundeedundeach], cost: 3 },
        { nodes: [Cities.Glasgow, Cities.Invernessinbhirnis], cost: 20 },
        { nodes: [Cities.Invernessinbhirnis, Cities.Perthpeairt], cost: 14 },
        { nodes: [Cities.Invernessinbhirnis, Cities.Dundeedundeach], cost: 14 },
        { nodes: [Cities.Invernessinbhirnis, Cities.Aberdeenobardheathain], cost: 15 },
        { nodes: [Cities.Aberdeenobardheathain, Cities.Dundeedundeach], cost: 10 },
        { nodes: [Cities.Limerick, Cities.Cork], cost: 12 },
        { nodes: [Cities.Cork, Cities.Waterford], cost: 8 },
        { nodes: [Cities.Waterford, Cities.Limerick], cost: 11 },
        { nodes: [Cities.Limerick, Cities.Galway], cost: 10 },
        { nodes: [Cities.Galway, Cities.Sligo], cost: 10 },
        { nodes: [Cities.Sligo, Cities.Derry], cost: 10 },
        { nodes: [Cities.Derry, Cities.Coleraine], cost: 6 },
        { nodes: [Cities.Coleraine, Cities.Belfast], cost: 8 },
        { nodes: [Cities.Belfast, Cities.Newry], cost: 6 },
        { nodes: [Cities.Newry, Cities.Dublin], cost: 10 },
        { nodes: [Cities.Dublin, Cities.Waterford], cost: 13 },
        { nodes: [Cities.Galway, Cities.Athlone], cost: 8 },
        { nodes: [Cities.Athlone, Cities.Sligo], cost: 9 },
        { nodes: [Cities.Athlone, Cities.Limerick], cost: 9 },
        { nodes: [Cities.Limerick, Cities.Dublin], cost: 16 },
        { nodes: [Cities.Dublin, Cities.Athlone], cost: 9 },
        { nodes: [Cities.Athlone, Cities.Newry], cost: 12 },
        { nodes: [Cities.Athlone, Cities.Omagh], cost: 14 },
        { nodes: [Cities.Omagh, Cities.Newry], cost: 8 },
        { nodes: [Cities.Omagh, Cities.Belfast], cost: 10 },
        { nodes: [Cities.Belfast, Cities.Derry], cost: 10 },
        { nodes: [Cities.Omagh, Cities.Derry], cost: 5 },
        { nodes: [Cities.Omagh, Cities.Sligo], cost: 10 },
    ],
    layout: 'Portrait',
    // Stub coords are at photo scale (x range ~110-650, y range ~200-840 — taller
    // than wide). First-pass fit into the default portrait viewBox — tune after
    // first render against the printed board.
    adjustRatio: [1.1, 1.1],
    mapPosition: [10, -75],
    mapRotation: 0,
    // Resupply table read from the printed UK & Ireland refill summary cards.
    // Indexed [resource][playerCount-2][step-1]. Note: 2P and 3P rows are NOT
    // identical on this map (unlike NA / SA), except for the Garbage row.
    resupply: [
        // Coal
        [
            [3, 4, 3], // 2P
            [3, 5, 3], // 3P
            [4, 6, 4], // 4P
            [4, 7, 5], // 5P
            [6, 8, 6], // 6P
        ],
        // Oil
        [
            [2, 3, 2], // 2P
            [2, 4, 2], // 3P
            [3, 5, 3], // 4P
            [4, 6, 4], // 5P
            [5, 7, 5], // 6P
        ],
        // Garbage
        [
            [1, 2, 2], // 2P
            [1, 2, 2], // 3P
            [2, 3, 3], // 4P
            [3, 3, 5], // 5P
            [3, 5, 5], // 6P
        ],
        // Uranium
        [
            [1, 1, 1], // 2P
            [1, 2, 1], // 3P
            [1, 3, 1], // 4P
            [2, 4, 2], // 5P
            [2, 4, 3], // 6P
        ],
    ],
    // Standard 8-price market (no overrides). Starting fill from the rulebook:
    //   coal    1-8 full = 24
    //   oil     3-8      = 18
    //   garbage 5-8      = 12
    //   uranium none     = 0
    startingResources: [24, 18, 12, 0],
    startingSupply: [24, 24, 24, 12],
    // Two-network mechanic: 20 Elektro surcharge to start a network on an
    // island where the player has no city. The cross-island build skips the
    // dijkstra path (there is no sea edge) and pays house base + 20.
    crossIslandSurcharge: 20,
    // Step 3 is placed 3rd from last in the deck (two plants below it) so Step
    // 3 starts earlier than on most maps. Otherwise standard recharged/original
    // deck prep.
    setupDeck(numPlayers: number, variant: string, rng: seedrandom.prng) {
        let powerPlantsDeck = cloneDeep(powerPlants);
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
            // UK&I: Step 3 sits 3rd from last (two plants below it).
            powerPlantsDeck.splice(powerPlantsDeck.length - 2, 0, step3);

            actualMarket = [getPowerPlant(3), getPowerPlant(4), getPowerPlant(5), getPowerPlant(6)];
            futureMarket = [getPowerPlant(7), getPowerPlant(8), getPowerPlant(9), getPowerPlant(10)];
        } else {
            let initialPowerPlants = shuffle(powerPlantsDeck.splice(0, 13), rng() + '');
            let initialPlantMarket = initialPowerPlants.splice(0, 8);
            initialPlantMarket = initialPlantMarket.sort((a, b) => a.number - b.number);
            actualMarket = initialPlantMarket.slice(0, 4);
            futureMarket = initialPlantMarket.slice(4);

            const first = initialPowerPlants.shift()!;
            const step3 = powerPlantsDeck.pop()!;

            powerPlantsDeck = shuffle(powerPlantsDeck, rng() + '');
            if (numPlayers == 2) {
                // Recharged 2P removes 1 plug + 5 socket (was incorrectly lumped with 3P).
                initialPowerPlants = initialPowerPlants.slice(1);
                powerPlantsDeck = shuffle(powerPlantsDeck.slice(5).concat(initialPowerPlants), rng() + '');
            } else if (numPlayers == 3) {
                initialPowerPlants = initialPowerPlants.slice(2);
                powerPlantsDeck = shuffle(powerPlantsDeck.slice(6).concat(initialPowerPlants), rng() + '');
            } else if (numPlayers == 4) {
                initialPowerPlants = initialPowerPlants.slice(1);
                powerPlantsDeck = shuffle(powerPlantsDeck.slice(3).concat(initialPowerPlants), rng() + '');
            } else {
                powerPlantsDeck = shuffle(powerPlantsDeck.concat(initialPowerPlants), rng() + '');
            }

            powerPlantsDeck.unshift(first);
            // UK&I: Step 3 sits 3rd from last (two plants below it). The engine's
            // standard Step 3 trigger already reshuffles plants below + discard
            // into the new face-down deck, so we only need the placement here.
            powerPlantsDeck.splice(powerPlantsDeck.length - 2, 0, step3);
        }

        return { actualMarket, futureMarket, powerPlantsDeck };
    },
    mapSpecificRules:
        'Two networks: Ireland (Green and Orange regions) and Great Britain ' +
        '(Red, Pink, Yellow, Brown) have no sea connection. A player may run ' +
        'one network on each island. Starting a second network on the other ' +
        'island costs an extra 20 Elektro on top of the normal first-house cost. ' +
        'Nuclear restriction: a player whose network is entirely in the Republic ' +
        'of Ireland (Green region) cannot bid on or auction a nuclear power plant ' +
        'until they build a city in Scotland, Wales, England, or Northern Ireland. ' +
        'Early Step 3: the Step 3 card is placed 3rd from last in the deck (two ' +
        'plants below it). Step 2 begins when a player connects their 7th city ' +
        '(6th for 6 players).',
};
