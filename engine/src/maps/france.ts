import { cloneDeep } from 'lodash';
import seedrandom from 'seedrandom';
import { getPowerPlant } from '../engine';
import { PowerPlant } from '../gamestate';
import { shuffle } from '../utils';
import { GameMap } from './../maps';
import { powerPlants } from './../powerPlants';

export enum Regions {
    Brown = 'brown',
    Purple = 'purple',
    Blue = 'blue',
    Yellow = 'yellow',
    Green = 'green',
    Red = 'red',
}

export enum Cities {
    Calais = 'Calais',
    Lile = 'Lile',
    Amiens = 'Amiens',
    Reims = 'Reims',
    Metz = 'Metz',
    Nancy = 'Nancy',
    Strasbourg = 'Strasbourg',
    Havre = 'Havre',
    Caen = 'Caen',
    Brest = 'Brest',
    Rennes = 'Rennes',
    Lemans = 'Le Mans',
    Angers = 'Angers',
    Rouen = 'Rouen',
    Paris1 = 'Paris 1',
    Paris2 = 'Paris 2',
    Paris3 = 'Paris 3',
    Orleans = 'Orleans',
    Tours = 'Tours',
    Limoges = 'Limoges',
    Clermontferrand = 'Clermont-Ferrand',
    Besancon = 'Besancon',
    Dijon = 'Dijon',
    Lyon = 'Lyon',
    Chamonix = 'Chamonix',
    Mulhouse = 'Mulhouse',
    Grenoble = 'Grenoble',
    Saintetienne = 'Saint-Etienne',
    Nice = 'Nice',
    Toulon = 'Toulon',
    Aimenprovence = 'Aim-En-Provence',
    Marseille = 'Marseille',
    Nimes = 'Nimes',
    Montpellier = 'Montpellier',
    Perpignan = 'Perpignan',
    Nantes = 'Nantes',
    Larochelle = 'La Rochelle',
    Bordeaux = 'Bordeaux',
    Biarritz = 'Biarritz',
    Toulous = 'Toulous',
    Carcassone = 'Carcas Sone',
    Lourdes = 'Lourdes',
}

export const map: GameMap = {
    name: 'France',
    cities: [
        { name: Cities.Calais, region: Regions.Brown, x: 661, y: 294 },
        { name: Cities.Lile, region: Regions.Brown, x: 791, y: 328 },
        { name: Cities.Amiens, region: Regions.Brown, x: 700, y: 433 },
        { name: Cities.Reims, region: Regions.Brown, x: 888, y: 531 },
        { name: Cities.Metz, region: Regions.Brown, x: 1076, y: 528 },
        { name: Cities.Nancy, region: Regions.Brown, x: 1078, y: 643 },
        { name: Cities.Strasbourg, region: Regions.Brown, x: 1208, y: 615 },
        { name: Cities.Havre, region: Regions.Purple, x: 487, y: 471 },
        { name: Cities.Caen, region: Regions.Purple, x: 423, y: 567 },
        { name: Cities.Brest, region: Regions.Purple, x: 79, y: 654 },
        { name: Cities.Rennes, region: Regions.Purple, x: 326, y: 695 },
        { name: Cities.Lemans, region: Regions.Purple, x: 516, y: 699 },
        { name: Cities.Angers, region: Regions.Purple, x: 446, y: 798 },
        { name: Cities.Rouen, region: Regions.Purple, x: 598, y: 506 },
        { name: Cities.Paris1, region: Regions.Blue, x: 693, y: 553 },
        { name: Cities.Paris2, region: Regions.Blue, x: 779, y: 566 },
        { name: Cities.Paris3, region: Regions.Blue, x: 722, y: 633 },
        { name: Cities.Orleans, region: Regions.Blue, x: 684, y: 736 },
        { name: Cities.Tours, region: Regions.Blue, x: 564, y: 813 },
        { name: Cities.Limoges, region: Regions.Blue, x: 605, y: 1009 },
        { name: Cities.Clermontferrand, region: Regions.Blue, x: 777, y: 1017 },
        { name: Cities.Besancon, region: Regions.Yellow, x: 1084, y: 828 },
        { name: Cities.Dijon, region: Regions.Yellow, x: 964, y: 801 },
        { name: Cities.Lyon, region: Regions.Yellow, x: 964, y: 973 },
        { name: Cities.Chamonix, region: Regions.Yellow, x: 1153, y: 987 },
        { name: Cities.Mulhouse, region: Regions.Yellow, x: 1180, y: 742 },
        { name: Cities.Grenoble, region: Regions.Yellow, x: 1048, y: 1116 },
        { name: Cities.Saintetienne, region: Regions.Yellow, x: 892, y: 1088 },
        { name: Cities.Nice, region: Regions.Green, x: 1178, y: 1302 },
        { name: Cities.Toulon, region: Regions.Green, x: 1070, y: 1397 },
        { name: Cities.Aimenprovence, region: Regions.Green, x: 1016, y: 1304 },
        { name: Cities.Marseille, region: Regions.Green, x: 954, y: 1369 },
        { name: Cities.Nimes, region: Regions.Green, x: 889, y: 1256 },
        { name: Cities.Montpellier, region: Regions.Green, x: 816, y: 1330 },
        { name: Cities.Perpignan, region: Regions.Green, x: 767, y: 1460 },
        { name: Cities.Nantes, region: Regions.Red, x: 330, y: 833 },
        { name: Cities.Larochelle, region: Regions.Red, x: 379, y: 959 },
        { name: Cities.Bordeaux, region: Regions.Red, x: 435, y: 1148 },
        { name: Cities.Biarritz, region: Regions.Red, x: 345, y: 1328 },
        { name: Cities.Toulous, region: Regions.Red, x: 621, y: 1309 },
        { name: Cities.Carcassone, region: Regions.Red, x: 700, y: 1382 },
        { name: Cities.Lourdes, region: Regions.Red, x: 479, y: 1393 },
    ],
    connections: [
        { nodes: [Cities.Calais, Cities.Havre], cost: 13 },
        { nodes: [Cities.Calais, Cities.Lile], cost: 7 },
        { nodes: [Cities.Calais, Cities.Amiens], cost: 8 },
        { nodes: [Cities.Lile, Cities.Reims], cost: 9 },
        { nodes: [Cities.Havre, Cities.Rouen], cost: 5 },
        { nodes: [Cities.Havre, Cities.Caen], cost: 5 },
        { nodes: [Cities.Caen, Cities.Rennes], cost: 12 },
        { nodes: [Cities.Rennes, Cities.Brest], cost: 16 },
        { nodes: [Cities.Brest, Cities.Nantes], cost: 19 },
        { nodes: [Cities.Rennes, Cities.Nantes], cost: 7 },
        { nodes: [Cities.Rennes, Cities.Angers], cost: 7 },
        { nodes: [Cities.Rennes, Cities.Lemans], cost: 9 },
        { nodes: [Cities.Caen, Cities.Lemans], cost: 10 },
        { nodes: [Cities.Lemans, Cities.Paris3], cost: 10 },
        { nodes: [Cities.Paris3, Cities.Caen], cost: 12 },
        { nodes: [Cities.Caen, Cities.Rouen], cost: 9 },
        { nodes: [Cities.Rouen, Cities.Paris1], cost: 9 },
        { nodes: [Cities.Rouen, Cities.Amiens], cost: 6 },
        { nodes: [Cities.Lile, Cities.Amiens], cost: 7 },
        { nodes: [Cities.Amiens, Cities.Reims], cost: 11 },
        { nodes: [Cities.Reims, Cities.Metz], cost: 12 },
        { nodes: [Cities.Metz, Cities.Strasbourg], cost: 11 },
        { nodes: [Cities.Strasbourg, Cities.Nancy], cost: 10 },
        { nodes: [Cities.Strasbourg, Cities.Mulhouse], cost: 6 },
        { nodes: [Cities.Mulhouse, Cities.Besancon], cost: 8 },
        { nodes: [Cities.Besancon, Cities.Nancy], cost: 14 },
        { nodes: [Cities.Nancy, Cities.Dijon], cost: 15 },
        { nodes: [Cities.Reims, Cities.Nancy], cost: 13 },
        { nodes: [Cities.Nancy, Cities.Paris2], cost: 21 },
        { nodes: [Cities.Paris1, Cities.Paris2], cost: 0 },
        { nodes: [Cities.Paris1, Cities.Paris3], cost: 0 },
        { nodes: [Cities.Paris2, Cities.Dijon], cost: 20 },
        { nodes: [Cities.Dijon, Cities.Orleans], cost: 18 },
        { nodes: [Cities.Orleans, Cities.Lemans], cost: 8 },
        { nodes: [Cities.Lemans, Cities.Tours], cost: 5 },
        { nodes: [Cities.Tours, Cities.Orleans], cost: 7 },
        { nodes: [Cities.Paris1, Cities.Amiens], cost: 9 },
        { nodes: [Cities.Dijon, Cities.Clermontferrand], cost: 19 },
        { nodes: [Cities.Clermontferrand, Cities.Limoges], cost: 12 },
        { nodes: [Cities.Limoges, Cities.Toulous], cost: 19 },
        { nodes: [Cities.Toulous, Cities.Clermontferrand], cost: 24 },
        { nodes: [Cities.Clermontferrand, Cities.Montpellier], cost: 22 },
        { nodes: [Cities.Montpellier, Cities.Nimes], cost: 3 },
        { nodes: [Cities.Saintetienne, Cities.Grenoble], cost: 10 },
        { nodes: [Cities.Grenoble, Cities.Chamonix], cost: 12 },
        { nodes: [Cities.Chamonix, Cities.Besancon], cost: 19 },
        { nodes: [Cities.Besancon, Cities.Dijon], cost: 6 },
        { nodes: [Cities.Dijon, Cities.Lyon], cost: 13 },
        { nodes: [Cities.Lyon, Cities.Clermontferrand], cost: 11 },
        { nodes: [Cities.Saintetienne, Cities.Montpellier], cost: 18 },
        { nodes: [Cities.Saintetienne, Cities.Nimes], cost: 16 },
        { nodes: [Cities.Nimes, Cities.Aimenprovence], cost: 8 },
        { nodes: [Cities.Aimenprovence, Cities.Nice], cost: 8 },
        { nodes: [Cities.Nice, Cities.Toulon], cost: 7 },
        { nodes: [Cities.Toulon, Cities.Marseille], cost: 3 },
        { nodes: [Cities.Marseille, Cities.Aimenprovence], cost: 0 },
        { nodes: [Cities.Nice, Cities.Grenoble], cost: 19 },
        { nodes: [Cities.Grenoble, Cities.Aimenprovence], cost: 17 },
        { nodes: [Cities.Grenoble, Cities.Nimes], cost: 18 },
        { nodes: [Cities.Montpellier, Cities.Toulous], cost: 14 },
        { nodes: [Cities.Toulous, Cities.Bordeaux], cost: 14 },
        { nodes: [Cities.Bordeaux, Cities.Limoges], cost: 13 },
        { nodes: [Cities.Limoges, Cities.Tours], cost: 13 },
        { nodes: [Cities.Tours, Cities.Larochelle], cost: 13 },
        { nodes: [Cities.Larochelle, Cities.Angers], cost: 12 },
        { nodes: [Cities.Angers, Cities.Lemans], cost: 5 },
        { nodes: [Cities.Angers, Cities.Nantes], cost: 5 },
        { nodes: [Cities.Nantes, Cities.Larochelle], cost: 9 },
        { nodes: [Cities.Larochelle, Cities.Bordeaux], cost: 13 },
        { nodes: [Cities.Bordeaux, Cities.Biarritz], cost: 12 },
        { nodes: [Cities.Bordeaux, Cities.Lourdes], cost: 14 },
        { nodes: [Cities.Lourdes, Cities.Biarritz], cost: 9 },
        { nodes: [Cities.Lourdes, Cities.Toulous], cost: 10 },
        { nodes: [Cities.Lourdes, Cities.Carcassone], cost: 15 },
        { nodes: [Cities.Lourdes, Cities.Perpignan], cost: 20 },
        { nodes: [Cities.Perpignan, Cities.Carcassone], cost: 6 },
        { nodes: [Cities.Carcassone, Cities.Toulous], cost: 6 },
        { nodes: [Cities.Carcassone, Cities.Montpellier], cost: 9 },
        { nodes: [Cities.Montpellier, Cities.Perpignan], cost: 11 },
        { nodes: [Cities.Orleans, Cities.Limoges], cost: 19 },
        { nodes: [Cities.Orleans, Cities.Clermontferrand], cost: 18 },
        { nodes: [Cities.Paris3, Cities.Orleans], cost: 7 },
        { nodes: [Cities.Angers, Cities.Tours], cost: 6 },
        { nodes: [Cities.Larochelle, Cities.Limoges], cost: 13 },
        { nodes: [Cities.Nancy, Cities.Metz], cost: 3 },
        { nodes: [Cities.Nancy, Cities.Mulhouse], cost: 12 },
        { nodes: [Cities.Besancon, Cities.Lyon], cost: 16 },
        { nodes: [Cities.Lyon, Cities.Grenoble], cost: 7 },
        { nodes: [Cities.Lyon, Cities.Chamonix], cost: 13 },
        { nodes: [Cities.Lyon, Cities.Saintetienne], cost: 6 },
        { nodes: [Cities.Saintetienne, Cities.Clermontferrand], cost: 10 },
        { nodes: [Cities.Paris2, Cities.Reims], cost: 9 },
        { nodes: [Cities.Paris3, Cities.Paris2], cost: 0 },
    ],
    layout: 'Portrait',
    mapPosition: [50, -100],
    adjustRatio: [0.7, 0.7],
    resupply: [
        [
            [3, 4, 3],
            [4, 5, 3],
            [5, 6, 4],
            [5, 7, 5],
            [7, 9, 6],
        ],
        [
            [2, 2, 4],
            [2, 3, 4],
            [3, 4, 5],
            [4, 5, 6],
            [5, 6, 7],
        ],
        [
            [1, 2, 3],
            [1, 2, 3],
            [2, 3, 4],
            [3, 3, 5],
            [3, 5, 6],
        ],
        [
            [1, 1, 1],
            [1, 1, 1],
            [1, 2, 2],
            [2, 3, 2],
            [2, 3, 3],
        ],
    ],
    startingResources: [24, 18, 6, 8],
    setupDeck(numPlayers: number, variant: string, rng: seedrandom.prng) {
        let powerPlantsDeck = cloneDeep(powerPlants);
        let actualMarket: PowerPlant[];
        let futureMarket: PowerPlant[];

        if (variant == 'original') {
            powerPlantsDeck = powerPlantsDeck.slice(8);
            const powerPlant11 = powerPlantsDeck.splice(0, 1)[0];
            powerPlantsDeck.splice(1, 1)[0];
            const step3 = powerPlantsDeck.pop()!;

            powerPlantsDeck = shuffle(powerPlantsDeck, rng() + '');
            if (numPlayers == 2 || numPlayers == 3) {
                powerPlantsDeck = powerPlantsDeck.slice(8);
            } else if (numPlayers == 4) {
                powerPlantsDeck = powerPlantsDeck.slice(4);
            }

            powerPlantsDeck.unshift(powerPlant11);
            powerPlantsDeck.push(step3);

            actualMarket = [getPowerPlant(3), getPowerPlant(4), getPowerPlant(5), getPowerPlant(6)];
            futureMarket = [getPowerPlant(7), getPowerPlant(8), getPowerPlant(9), getPowerPlant(10)];
        } else {
            // Remove power plant 13
            powerPlantsDeck.splice(10, 1)[0];
            const powerPlant11 = powerPlantsDeck.splice(8, 1)[0];

            let initialPowerPlants = shuffle(powerPlantsDeck.splice(0, 11), rng() + '');
            let initialPlantMarket = initialPowerPlants.splice(0, 7);
            initialPlantMarket.push(powerPlant11);
            initialPlantMarket = initialPlantMarket.sort((a, b) => a.number - b.number);
            actualMarket = initialPlantMarket.slice(0, 4);
            futureMarket = initialPlantMarket.slice(4);

            const first = initialPowerPlants.shift()!;
            const step3 = powerPlantsDeck.pop()!;

            powerPlantsDeck = shuffle(powerPlantsDeck, rng() + '');
            if (numPlayers == 2) {
                powerPlantsDeck = shuffle(powerPlantsDeck.slice(6).concat(initialPowerPlants), rng() + '');
            } else if (numPlayers == 3) {
                initialPowerPlants = initialPowerPlants.slice(1);
                powerPlantsDeck = shuffle(powerPlantsDeck.slice(6).concat(initialPowerPlants), rng() + '');
            } else if (numPlayers == 4) {
                powerPlantsDeck = shuffle(powerPlantsDeck.slice(3).concat(initialPowerPlants), rng() + '');
            } else {
                powerPlantsDeck = shuffle(powerPlantsDeck.concat(initialPowerPlants), rng() + '');
            }

            powerPlantsDeck.unshift(first);
            powerPlantsDeck.push(step3);
        }

        return { actualMarket, futureMarket, powerPlantsDeck };
    },
    mapSpecificRules: 'Remove power plant 13. Put power plant 11 on top of the deck.',
};
