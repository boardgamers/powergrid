import { cloneDeep } from 'lodash';
import { GameMap } from './../maps';
import { PowerPlant } from '../gamestate';
import { powerPlants } from '../powerPlants';
import { getPowerPlant } from '../engine';
import { shuffle } from '../utils';

export enum Regions {
    Green = 'green',
    Pink = 'pink',
    Red = 'red',
    Yellow = 'yellow',
    Purple = 'purple',
    Brown = 'brown',
}

export enum Cities {
    Murmansk = 'Murmansk',
    Arkhangelsk = 'Arkhangelsk',
    Syktyvkar = 'Syktyvkar',
    Kirov = 'Kirov',
    Kazan = 'Kazan',
    Cheboksary = 'Cheboksary',
    Ulyanovsk = 'Ulyanovsk',
    Tula = 'Tula',
    Kaliningrad = 'Kaliningrad',
    Ryazan = 'Ryazan',
    Nizhnynovgorod = 'Nizhny Novgorod',
    Moscow = 'Moscow',
    Stpetersburg = 'St Petersburg',
    Yaroslavl = 'Yaroslavl',
    Chita = 'Chita',
    Bratsk = 'Bratsk',
    Krasnoyarsk = 'Krasnoyarsk',
    Kemerovd = 'Kemerovd',
    Novokuznetsk = 'Novokuznetsk',
    Irkutsk = 'Irkutsk',
    Ulanude = 'Ulan Ude',
    Norilsk = 'Norilsk',
    Surgut = 'Surgut',
    Tyumen = 'Tyumen',
    Tomsk = 'Tomsk',
    Novosibirsk = 'Novosibirsk',
    Barnaul = 'Barnaul',
    Omsk = 'Omsk',
    Chelyabinsk = 'Chelyabinsk',
    Ufa = 'Ufa',
    Perm = 'Perm',
    Yekaterinburg = 'Yekaterinburg',
    Orenburg = 'Orenburg',
    Naberezhnyechelny = 'Naberezhnye Chelny',
    Samara = 'Samara',
    Astrakhan = 'Astrakhan',
    Makhachkala = 'Makhachkala',
    Saratov = 'Saratov',
    Volgograd = 'Volgograd',
    Krasnodar = 'Krasnodar',
    Rostov = 'Rostov',
    Voronezh = 'Voronezh',
}

export const map: GameMap = {
    name: 'Russia',
    cities: [
        { name: Cities.Murmansk, region: Regions.Green, x: 1574, y: 351 },
        { name: Cities.Arkhangelsk, region: Regions.Green, x: 1456, y: 695 },
        { name: Cities.Syktyvkar, region: Regions.Green, x: 1669, y: 1005 },
        { name: Cities.Kirov, region: Regions.Green, x: 1457, y: 1172 },
        { name: Cities.Kazan, region: Regions.Green, x: 1378, y: 1478 },
        { name: Cities.Cheboksary, region: Regions.Green, x: 1200, y: 1328 },
        { name: Cities.Ulyanovsk, region: Regions.Green, x: 884, y: 1448 },
        { name: Cities.Tula, region: Regions.Pink, x: 485, y: 1077 },
        { name: Cities.Kaliningrad, region: Regions.Pink, x: 394, y: 606 },
        { name: Cities.Ryazan, region: Regions.Pink, x: 793, y: 1193 },
        { name: Cities.Nizhnynovgorod, region: Regions.Pink, x: 1129, y: 1116 },
        { name: Cities.Moscow, region: Regions.Pink, x: 763, y: 961 },
        { name: Cities.Stpetersburg, region: Regions.Pink, x: 883, y: 597 },
        { name: Cities.Yaroslavl, region: Regions.Pink, x: 1018, y: 915 },
        { name: Cities.Chita, region: Regions.Red, x: 4168, y: 2048 },
        { name: Cities.Bratsk, region: Regions.Red, x: 3599, y: 1808 },
        { name: Cities.Krasnoyarsk, region: Regions.Red, x: 3230, y: 1930 },
        { name: Cities.Kemerovd, region: Regions.Red, x: 2953, y: 1987 },
        { name: Cities.Novokuznetsk, region: Regions.Red, x: 3041, y: 2159 },
        { name: Cities.Irkutsk, region: Regions.Red, x: 3721, y: 2162 },
        { name: Cities.Ulanude, region: Regions.Red, x: 4030, y: 2228 },
        { name: Cities.Norilsk, region: Regions.Yellow, x: 3001, y: 856 },
        { name: Cities.Surgut, region: Regions.Yellow, x: 2348, y: 1411 },
        { name: Cities.Tyumen, region: Regions.Yellow, x: 2060, y: 1627 },
        { name: Cities.Tomsk, region: Regions.Yellow, x: 2773, y: 1835 },
        { name: Cities.Novosibirsk, region: Regions.Yellow, x: 2647, y: 2005 },
        { name: Cities.Barnaul, region: Regions.Yellow, x: 2662, y: 2191 },
        { name: Cities.Omsk, region: Regions.Yellow, x: 2195, y: 1957 },
        { name: Cities.Chelyabinsk, region: Regions.Purple, x: 1768, y: 1865 },
        { name: Cities.Ufa, region: Regions.Purple, x: 1472, y: 1907 },
        { name: Cities.Perm, region: Regions.Purple, x: 1688, y: 1388 },
        { name: Cities.Yekaterinburg, region: Regions.Purple, x: 1757, y: 1620 },
        { name: Cities.Orenburg, region: Regions.Purple, x: 1250, y: 1997 },
        { name: Cities.Naberezhnyechelny, region: Regions.Purple, x: 1427, y: 1709 },
        { name: Cities.Samara, region: Regions.Purple, x: 1132, y: 1701 },
        { name: Cities.Astrakhan, region: Regions.Brown, x: 619, y: 2092 },
        { name: Cities.Makhachkala, region: Regions.Brown, x: 317, y: 2262 },
        { name: Cities.Saratov, region: Regions.Brown, x: 808, y: 1661 },
        { name: Cities.Volgograd, region: Regions.Brown, x: 589, y: 1795 },
        { name: Cities.Krasnodar, region: Regions.Brown, x: 260, y: 1865 },
        { name: Cities.Rostov, region: Regions.Brown, x: 311, y: 1658 },
        { name: Cities.Voronezh, region: Regions.Brown, x: 485, y: 1409 },
    ],
    connections: [
        { nodes: [Cities.Kaliningrad, Cities.Stpetersburg], cost: 15 },
        { nodes: [Cities.Stpetersburg, Cities.Murmansk], cost: 19 },
        { nodes: [Cities.Murmansk, Cities.Arkhangelsk], cost: 15 },
        { nodes: [Cities.Arkhangelsk, Cities.Stpetersburg], cost: 14 },
        { nodes: [Cities.Tula, Cities.Kaliningrad], cost: 20 },
        { nodes: [Cities.Tula, Cities.Moscow], cost: 3 },
        { nodes: [Cities.Moscow, Cities.Ryazan], cost: 3 },
        { nodes: [Cities.Ryazan, Cities.Voronezh], cost: 5 },
        { nodes: [Cities.Voronezh, Cities.Tula], cost: 5 },
        { nodes: [Cities.Tula, Cities.Stpetersburg], cost: 13 },
        { nodes: [Cities.Stpetersburg, Cities.Moscow], cost: 10 },
        { nodes: [Cities.Moscow, Cities.Yaroslavl], cost: 0 },
        { nodes: [Cities.Yaroslavl, Cities.Nizhnynovgorod], cost: 4 },
        { nodes: [Cities.Nizhnynovgorod, Cities.Moscow], cost: 7 },
        { nodes: [Cities.Yaroslavl, Cities.Stpetersburg], cost: 9 },
        { nodes: [Cities.Yaroslavl, Cities.Arkhangelsk], cost: 12 },
        { nodes: [Cities.Arkhangelsk, Cities.Syktyvkar], cost: 10 },
        { nodes: [Cities.Syktyvkar, Cities.Surgut], cost: 21 },
        { nodes: [Cities.Perm, Cities.Syktyvkar], cost: 8 },
        { nodes: [Cities.Syktyvkar, Cities.Kirov], cost: 6 },
        { nodes: [Cities.Syktyvkar, Cities.Nizhnynovgorod], cost: 11 },
        { nodes: [Cities.Nizhnynovgorod, Cities.Arkhangelsk], cost: 15 },
        { nodes: [Cities.Nizhnynovgorod, Cities.Cheboksary], cost: 3 },
        { nodes: [Cities.Cheboksary, Cities.Ulyanovsk], cost: 4 },
        { nodes: [Cities.Ulyanovsk, Cities.Voronezh], cost: 11 },
        { nodes: [Cities.Voronezh, Cities.Volgograd], cost: 8 },
        { nodes: [Cities.Volgograd, Cities.Saratov], cost: 6 },
        { nodes: [Cities.Saratov, Cities.Samara], cost: 5 },
        { nodes: [Cities.Samara, Cities.Ulyanovsk], cost: 3 },
        { nodes: [Cities.Ulyanovsk, Cities.Kazan], cost: 3 },
        { nodes: [Cities.Kazan, Cities.Samara], cost: 4 },
        { nodes: [Cities.Samara, Cities.Naberezhnyechelny], cost: 5 },
        { nodes: [Cities.Cheboksary, Cities.Kazan], cost: 2 },
        { nodes: [Cities.Cheboksary, Cities.Kirov], cost: 5 },
        { nodes: [Cities.Kirov, Cities.Kazan], cost: 5 },
        { nodes: [Cities.Kazan, Cities.Perm], cost: 8 },
        { nodes: [Cities.Kazan, Cities.Naberezhnyechelny], cost: 3 },
        { nodes: [Cities.Naberezhnyechelny, Cities.Ufa], cost: 4 },
        { nodes: [Cities.Ufa, Cities.Orenburg], cost: 6 },
        { nodes: [Cities.Orenburg, Cities.Samara], cost: 6 },
        { nodes: [Cities.Orenburg, Cities.Naberezhnyechelny], cost: 7 },
        { nodes: [Cities.Ufa, Cities.Chelyabinsk], cost: 8 },
        { nodes: [Cities.Chelyabinsk, Cities.Yekaterinburg], cost: 3 },
        { nodes: [Cities.Yekaterinburg, Cities.Perm], cost: 5 },
        { nodes: [Cities.Perm, Cities.Kirov], cost: 6 },
        { nodes: [Cities.Chelyabinsk, Cities.Tyumen], cost: 5 },
        { nodes: [Cities.Tyumen, Cities.Surgut], cost: 10 },
        { nodes: [Cities.Syktyvkar, Cities.Tyumen], cost: 17 },
        { nodes: [Cities.Tyumen, Cities.Yekaterinburg], cost: 5 },
        { nodes: [Cities.Chelyabinsk, Cities.Omsk], cost: 13 },
        { nodes: [Cities.Omsk, Cities.Tyumen], cost: 9 },
        { nodes: [Cities.Tyumen, Cities.Tomsk], cost: 19 },
        { nodes: [Cities.Tomsk, Cities.Surgut], cost: 15 },
        { nodes: [Cities.Tomsk, Cities.Novosibirsk], cost: 4 },
        { nodes: [Cities.Novosibirsk, Cities.Barnaul], cost: 4 },
        { nodes: [Cities.Barnaul, Cities.Omsk], cost: 11 },
        { nodes: [Cities.Omsk, Cities.Novosibirsk], cost: 10 },
        { nodes: [Cities.Omsk, Cities.Tomsk], cost: 12 },
        { nodes: [Cities.Rostov, Cities.Krasnodar], cost: 4 },
        { nodes: [Cities.Krasnodar, Cities.Volgograd], cost: 9 },
        { nodes: [Cities.Volgograd, Cities.Astrakhan], cost: 6 },
        { nodes: [Cities.Krasnodar, Cities.Makhachkala], cost: 14 },
        { nodes: [Cities.Makhachkala, Cities.Astrakhan], cost: 8 },
        { nodes: [Cities.Makhachkala, Cities.Volgograd], cost: 11 },
        { nodes: [Cities.Rostov, Cities.Volgograd], cost: 7 },
        { nodes: [Cities.Ryazan, Cities.Ulyanovsk], cost: 9 },
        { nodes: [Cities.Ulyanovsk, Cities.Saratov], cost: 6 },
        { nodes: [Cities.Saratov, Cities.Voronezh], cost: 8 },
        { nodes: [Cities.Rostov, Cities.Voronezh], cost: 9 },
        { nodes: [Cities.Naberezhnyechelny, Cities.Perm], cost: 6 },
        { nodes: [Cities.Naberezhnyechelny, Cities.Yekaterinburg], cost: 8 },
        { nodes: [Cities.Ufa, Cities.Yekaterinburg], cost: 6 },
        { nodes: [Cities.Chita, Cities.Ulanude], cost: 6 },
        { nodes: [Cities.Ulanude, Cities.Irkutsk], cost: 6 },
        { nodes: [Cities.Irkutsk, Cities.Novokuznetsk], cost: 21 },
        { nodes: [Cities.Novokuznetsk, Cities.Kemerovd], cost: 3 },
        { nodes: [Cities.Kemerovd, Cities.Tomsk], cost: 3 },
        { nodes: [Cities.Novosibirsk, Cities.Novokuznetsk], cost: 5 },
        { nodes: [Cities.Novokuznetsk, Cities.Barnaul], cost: 6 },
        { nodes: [Cities.Kemerovd, Cities.Krasnoyarsk], cost: 7 },
        { nodes: [Cities.Krasnoyarsk, Cities.Novokuznetsk], cost: 7 },
        { nodes: [Cities.Krasnoyarsk, Cities.Irkutsk], cost: 17 },
        { nodes: [Cities.Krasnoyarsk, Cities.Bratsk], cost: 10 },
        { nodes: [Cities.Bratsk, Cities.Tomsk], cost: 17 },
        { nodes: [Cities.Bratsk, Cities.Irkutsk], cost: 10 },
        { nodes: [Cities.Bratsk, Cities.Ulanude], cost: 14 },
        { nodes: [Cities.Tomsk, Cities.Norilsk], cost: 24 },
        { nodes: [Cities.Norilsk, Cities.Bratsk], cost: 29 },
        { nodes: [Cities.Norilsk, Cities.Surgut], cost: 19 },
    ],
    adjustRatio: [0.25, 0.25],
    resupply: [
        [
            [2, 2, 4],
            [2, 3, 4],
            [3, 4, 5],
            [4, 5, 6],
            [5, 6, 7],
        ],
        [
            [3, 4, 3],
            [3, 4, 3],
            [5, 6, 4],
            [5, 7, 5],
            [7, 9, 6],
        ],
        [
            [2, 2, 3],
            [2, 2, 3],
            [3, 3, 4],
            [4, 3, 5],
            [4, 5, 6],
        ],
        [
            [1, 1, 1],
            [1, 1, 1],
            [1, 2, 2],
            [2, 3, 2],
            [2, 3, 3],
        ],
    ],
    startingResources: [18, 24, 0, 7],
    setupDeck(numPlayers: number, variant: string, rng: seedrandom.prng) {
        let powerPlantsDeck = cloneDeep(powerPlants);
        let actualMarket: PowerPlant[] = [];
        let futureMarket: PowerPlant[] = [];
        const step3 = powerPlantsDeck.pop()!;

        if (variant == 'original') {
            // Set actual and future markets (plant 6 is skipped).
            actualMarket = powerPlantsDeck.filter((p: PowerPlant) => p.number >= 3 && p.number <= 5);
            futureMarket = powerPlantsDeck.filter((p: PowerPlant) => p.number >= 7 && p.number <= 9);

            // Set aside plants 10, 11, 13.
            let plant10 = getPowerPlant(10);
            let plant11 = getPowerPlant(11);
            let plant13 = getPowerPlant(13);

            // Shuffle rest of plants (skipping plant 14).
            let mainPlants = powerPlantsDeck.filter((p: PowerPlant) => p.number == 12 || p.number >= 15);
            let mainPlantsShuffled = shuffle(mainPlants, rng() + '');

            // Remove random set of plants based on number of players.
            if (numPlayers == 2 || numPlayers == 3) {
                mainPlantsShuffled = mainPlantsShuffled.slice(8);
            } else if (numPlayers == 4) {
                mainPlantsShuffled = mainPlantsShuffled.slice(4);
            }

            // Shuffle top 3 plants from main deck with plants 10 and 11, and place on top of deck.
            let topPlants = mainPlantsShuffled.slice(0, 3).concat(plant10, plant11);
            topPlants = shuffle(topPlants, rng() + '');

            // Place plant 13 on top of deck, shuffled cards with 10 and 11 next, then the rest of the deck, then the step 3 card.
            powerPlantsDeck = [plant13].concat(topPlants, mainPlantsShuffled.slice(3), step3);
        } else {
            let initialPlants = powerPlantsDeck.filter((p) => p.number <= 15 && p.number != 6 && p.number != 14);
            let initialPlantsShuffled = shuffle(initialPlants, rng() + '');

            let mainPlants = powerPlantsDeck.filter((p) => p.number >= 16);
            let mainPlantsShuffled = shuffle(mainPlants, rng() + '');

            if (numPlayers == 2) {
                mainPlantsShuffled = mainPlantsShuffled.slice(6);
            } else if (numPlayers == 3) {
                mainPlantsShuffled = mainPlantsShuffled.slice(8);
            } else if (numPlayers == 4) {
                mainPlantsShuffled = mainPlantsShuffled.slice(4);
            }

            let initialPlantMarket = initialPlantsShuffled.slice(0, 6);
            let otherInitialPlants = initialPlantsShuffled.slice(6);
            initialPlantMarket = initialPlantMarket.sort((a, b) => a.number - b.number);
            actualMarket = initialPlantMarket.slice(0, 3);
            futureMarket = initialPlantMarket.slice(3);
            powerPlantsDeck = otherInitialPlants.concat(mainPlantsShuffled, step3);
        }

        return { actualMarket, futureMarket, powerPlantsDeck };
    },
    // TODO: Remove smallest power plant the first time someone does not put a plant up for auction
    // TODO: Add summary of key rule differences
};
