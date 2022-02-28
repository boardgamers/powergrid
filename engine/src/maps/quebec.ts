import { cloneDeep } from 'lodash';
import { getPowerPlant } from '../engine';
import { PowerPlant, PowerPlantType } from '../gamestate';
import powerPlants from '../powerPlants';
import { shuffle } from '../utils';
import { GameMap } from './../maps';

export enum Regions {
    Green = 'green',
    Brown = 'brown',
    Pink = 'pink',
    Red = 'red',
    Yellow = 'yellow',
    Purple = 'purple',
}

export enum Cities {
    Septiles = 'Sept-Iles',
    Portcartier = 'Port-Cartier',
    Baiecomeau = 'Baie-Comeau',
    Chicoutimi = 'Chicoutimi',
    Alma = 'Alma',
    Roberval = 'Roberval',
    Jonquiere = 'Jonquiere',
    Gaspe = 'Gaspe',
    Steannedesmonts = 'Ste-Anne-Des-Monts',
    Matane = 'Matane',
    Rimouski = 'Rimouski',
    Pointealacroix = 'Pointe-A-La-Croix',
    Riviereduloup = 'Riviere-Du-Loup',
    Montmagny = 'Montmagny',
    Stgeorges = 'St-Georges',
    Sherbrooke = 'Sherbrooke',
    Victoriaville = 'Victoriaville',
    Stsimeon = 'St-Simeon',
    Charlesbourg = 'Charlesbourg',
    Quebec = 'Quebec',
    Beauport = 'Beauport',
    Granby = 'Granby',
    Sthyacinthe = 'St-Hyacinthe',
    Brossard = 'Brossard',
    Valleyfield = 'Valleyfield',
    Vaudreuildorion = 'Vaudreuil-Dorion',
    Montreal = 'Montreal',
    Pointeclaire = 'Pointe-Claire',
    Shawinigan = 'Shawinigan',
    Troisrivieres = 'Trois-Rivieres',
    Drummondville = 'Drummond-Ville',
    Repentigny = 'Repentigny',
    Longueuil = 'Longueuil',
    Laval = 'Laval',
    Lachute = 'Lachute',
    Amos = 'Amos',
    Valdor = 'Val-Dor',
    Rouynnoranda = 'Rouyn-Noranda',
    Montlaurier = 'Mont-Laurier',
    Maniwaki = 'Maniwaki',
    Gatineau = 'Gatineau',
    Hull = 'Hull',
}

export const map: GameMap = {
    name: 'Quebec',
    cities: [
        { name: Cities.Septiles, region: Regions.Green, x: 3524, y: 228 },
        { name: Cities.Portcartier, region: Regions.Green, x: 3328, y: 370 },
        { name: Cities.Baiecomeau, region: Regions.Green, x: 3066, y: 630 },
        { name: Cities.Chicoutimi, region: Regions.Green, x: 2392, y: 898 },
        { name: Cities.Alma, region: Regions.Green, x: 2172, y: 844 },
        { name: Cities.Roberval, region: Regions.Green, x: 1944, y: 950 },
        { name: Cities.Jonquiere, region: Regions.Green, x: 2240, y: 1052 },
        { name: Cities.Gaspe, region: Regions.Brown, x: 4014, y: 808 },
        { name: Cities.Steannedesmonts, region: Regions.Brown, x: 3512, y: 708 },
        { name: Cities.Matane, region: Regions.Brown, x: 3244, y: 808 },
        { name: Cities.Rimouski, region: Regions.Brown, x: 2990, y: 946 },
        { name: Cities.Pointealacroix, region: Regions.Brown, x: 3492, y: 1094 },
        { name: Cities.Riviereduloup, region: Regions.Brown, x: 2780, y: 1208 },
        { name: Cities.Montmagny, region: Regions.Brown, x: 2522, y: 1534 },
        { name: Cities.Stgeorges, region: Regions.Pink, x: 2506, y: 1836 },
        { name: Cities.Sherbrooke, region: Regions.Pink, x: 2242, y: 2128 },
        { name: Cities.Victoriaville, region: Regions.Pink, x: 2178, y: 1822 },
        { name: Cities.Stsimeon, region: Regions.Pink, x: 2576, y: 1146 },
        { name: Cities.Charlesbourg, region: Regions.Pink, x: 2246, y: 1434 },
        { name: Cities.Quebec, region: Regions.Pink, x: 2302, y: 1536 },
        { name: Cities.Beauport, region: Regions.Pink, x: 2196, y: 1524 },
        { name: Cities.Granby, region: Regions.Red, x: 1974, y: 2160 },
        { name: Cities.Sthyacinthe, region: Regions.Red, x: 1796, y: 2038 },
        { name: Cities.Brossard, region: Regions.Red, x: 1790, y: 2296 },
        { name: Cities.Valleyfield, region: Regions.Red, x: 1576, y: 2306 },
        { name: Cities.Vaudreuildorion, region: Regions.Red, x: 1414, y: 2186 },
        { name: Cities.Montreal, region: Regions.Red, x: 1624, y: 2052 },
        { name: Cities.Pointeclaire, region: Regions.Red, x: 1510, y: 2060 },
        { name: Cities.Shawinigan, region: Regions.Yellow, x: 1864, y: 1448 },
        { name: Cities.Troisrivieres, region: Regions.Yellow, x: 1918, y: 1650 },
        { name: Cities.Drummondville, region: Regions.Yellow, x: 1984, y: 1886 },
        { name: Cities.Repentigny, region: Regions.Yellow, x: 1696, y: 1820 },
        { name: Cities.Longueuil, region: Regions.Yellow, x: 1598, y: 1964 },
        { name: Cities.Laval, region: Regions.Yellow, x: 1512, y: 1990 },
        { name: Cities.Lachute, region: Regions.Yellow, x: 1364, y: 1944 },
        { name: Cities.Amos, region: Regions.Purple, x: 492, y: 868 },
        { name: Cities.Valdor, region: Regions.Purple, x: 570, y: 1098 },
        { name: Cities.Rouynnoranda, region: Regions.Purple, x: 236, y: 1028 },
        { name: Cities.Montlaurier, region: Regions.Purple, x: 1180, y: 1630 },
        { name: Cities.Maniwaki, region: Regions.Purple, x: 964, y: 1760 },
        { name: Cities.Gatineau, region: Regions.Purple, x: 1076, y: 2096 },
        { name: Cities.Hull, region: Regions.Purple, x: 862, y: 2104 },
    ],
    connections: [
        { nodes: [Cities.Maniwaki, Cities.Montlaurier], cost: 5 },
        { nodes: [Cities.Maniwaki, Cities.Valdor], cost: 24 },
        { nodes: [Cities.Valdor, Cities.Amos], cost: 8 },
        { nodes: [Cities.Amos, Cities.Rouynnoranda], cost: 9 },
        { nodes: [Cities.Rouynnoranda, Cities.Valdor], cost: 12 },
        { nodes: [Cities.Hull, Cities.Maniwaki], cost: 15 },
        { nodes: [Cities.Hull, Cities.Gatineau], cost: 0 },
        { nodes: [Cities.Gatineau, Cities.Montlaurier], cost: 16 },
        { nodes: [Cities.Montlaurier, Cities.Lachute], cost: 18 },
        { nodes: [Cities.Shawinigan, Cities.Troisrivieres], cost: 3 },
        { nodes: [Cities.Troisrivieres, Cities.Drummondville], cost: 9 },
        { nodes: [Cities.Drummondville, Cities.Victoriaville], cost: 6 },
        { nodes: [Cities.Victoriaville, Cities.Stgeorges], cost: 10 },
        { nodes: [Cities.Stgeorges, Cities.Sherbrooke], cost: 15 },
        { nodes: [Cities.Sherbrooke, Cities.Granby], cost: 8 },
        { nodes: [Cities.Granby, Cities.Sthyacinthe], cost: 4 },
        { nodes: [Cities.Sthyacinthe, Cities.Drummondville], cost: 6 },
        { nodes: [Cities.Troisrivieres, Cities.Victoriaville], cost: 9 },
        { nodes: [Cities.Victoriaville, Cities.Sherbrooke], cost: 9 },
        { nodes: [Cities.Sherbrooke, Cities.Drummondville], cost: 9 },
        { nodes: [Cities.Sthyacinthe, Cities.Repentigny], cost: 7 },
        { nodes: [Cities.Sthyacinthe, Cities.Brossard], cost: 5 },
        { nodes: [Cities.Brossard, Cities.Valleyfield], cost: 8 },
        { nodes: [Cities.Valleyfield, Cities.Vaudreuildorion], cost: 4 },
        { nodes: [Cities.Gatineau, Cities.Lachute], cost: 14 },
        { nodes: [Cities.Montlaurier, Cities.Shawinigan], cost: 28 },
        { nodes: [Cities.Shawinigan, Cities.Beauport], cost: 14 },
        { nodes: [Cities.Beauport, Cities.Troisrivieres], cost: 15 },
        { nodes: [Cities.Troisrivieres, Cities.Repentigny], cost: 13 },
        { nodes: [Cities.Repentigny, Cities.Longueuil], cost: 3 },
        { nodes: [Cities.Laval, Cities.Lachute], cost: 6 },
        { nodes: [Cities.Vaudreuildorion, Cities.Pointeclaire], cost: 3 },
        { nodes: [Cities.Montreal, Cities.Brossard], cost: 4 },
        { nodes: [Cities.Laval, Cities.Longueuil], cost: 0 },
        { nodes: [Cities.Pointeclaire, Cities.Montreal], cost: 0 },
        { nodes: [Cities.Montreal, Cities.Longueuil], cost: 0 },
        { nodes: [Cities.Pointeclaire, Cities.Laval], cost: 0 },
        { nodes: [Cities.Beauport, Cities.Charlesbourg], cost: 0 },
        { nodes: [Cities.Charlesbourg, Cities.Quebec], cost: 0 },
        { nodes: [Cities.Quebec, Cities.Beauport], cost: 0 },
        { nodes: [Cities.Victoriaville, Cities.Beauport], cost: 12 },
        { nodes: [Cities.Quebec, Cities.Stgeorges], cost: 12 },
        { nodes: [Cities.Stgeorges, Cities.Montmagny], cost: 12 },
        { nodes: [Cities.Montmagny, Cities.Riviereduloup], cost: 16 },
        { nodes: [Cities.Jonquiere, Cities.Charlesbourg], cost: 21 },
        { nodes: [Cities.Montmagny, Cities.Quebec], cost: 5 },
        { nodes: [Cities.Stsimeon, Cities.Charlesbourg], cost: 18 },
        { nodes: [Cities.Drummondville, Cities.Granby], cost: 4 },
        { nodes: [Cities.Roberval, Cities.Shawinigan], cost: 25 },
        { nodes: [Cities.Jonquiere, Cities.Stsimeon], cost: 16 },
        { nodes: [Cities.Roberval, Cities.Jonquiere], cost: 10 },
        { nodes: [Cities.Jonquiere, Cities.Alma], cost: 4 },
        { nodes: [Cities.Alma, Cities.Chicoutimi], cost: 4 },
        { nodes: [Cities.Jonquiere, Cities.Chicoutimi], cost: 0 },
        { nodes: [Cities.Chicoutimi, Cities.Baiecomeau], cost: 23 },
        { nodes: [Cities.Stsimeon, Cities.Baiecomeau], cost: 23 },
        { nodes: [Cities.Baiecomeau, Cities.Portcartier], cost: 16 },
        { nodes: [Cities.Septiles, Cities.Portcartier], cost: 6 },
        { nodes: [Cities.Riviereduloup, Cities.Rimouski], cost: 12 },
        { nodes: [Cities.Rimouski, Cities.Matane], cost: 11 },
        { nodes: [Cities.Matane, Cities.Pointealacroix], cost: 15 },
        { nodes: [Cities.Matane, Cities.Steannedesmonts], cost: 10 },
        { nodes: [Cities.Pointealacroix, Cities.Steannedesmonts], cost: 16 },
        { nodes: [Cities.Steannedesmonts, Cities.Gaspe], cost: 21 },
        { nodes: [Cities.Gaspe, Cities.Pointealacroix], cost: 25 },
    ],
    layout: 'Portrait',
    adjustRatio: [0.25, 0.35],
    mapPosition: [-20, 75],
    resupply: [
        [
            [3, 3, 3],
            [4, 4, 3],
            [5, 4, 4],
            [5, 5, 5],
            [7, 6, 6],
        ],
        [
            [2, 2, 3],
            [2, 3, 3],
            [3, 4, 4],
            [4, 5, 4],
            [5, 6, 5],
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
    startingResources: [21, 21, 6, 2],
    setupDeck(numPlayers: number, variant: string, rng: seedrandom.prng) {
        let powerPlantsDeck = cloneDeep(powerPlants);
        let actualMarket: PowerPlant[];
        let futureMarket: PowerPlant[];

        if (variant == 'original') {
            // No ecological plants will be discarded.
            // 13, 18, 22 will be set aside and placed on top of the deck.
            let setAsidePlants = powerPlantsDeck.filter((pp) => [13, 18, 22].includes(pp.number));
            let otherEcoPlants = powerPlantsDeck.filter((pp) => (pp.type == PowerPlantType.Wind || pp.type == PowerPlantType.Nuclear)
                && ![13, 18, 22].includes(pp.number));
            let nonEcoPlantsDeck = powerPlantsDeck.filter((pp) => pp.type != PowerPlantType.Wind && pp.type != PowerPlantType.Nuclear);    

            // Remove first eight plants for actual and future market.
            powerPlantsDeck = nonEcoPlantsDeck.slice(8);
            actualMarket = [getPowerPlant(3), getPowerPlant(4), getPowerPlant(5), getPowerPlant(6)];
            futureMarket = [getPowerPlant(7), getPowerPlant(8), getPowerPlant(9), getPowerPlant(10)];            

            // Set aside Step 3 card.
            const step3 = powerPlantsDeck.pop()!;

            // Remove random plants - this does not include any ecological plants.
            powerPlantsDeck = shuffle(powerPlantsDeck, rng() + '');
            if (numPlayers == 2 || numPlayers == 3) {
                powerPlantsDeck = powerPlantsDeck.slice(8);
            } else if (numPlayers == 4) {
                powerPlantsDeck = powerPlantsDeck.slice(4);
            }

            // Put back ecological plants and shuffle again.
            powerPlantsDeck = powerPlantsDeck.concat(otherEcoPlants);
            powerPlantsDeck = shuffle(powerPlantsDeck, rng() + '');

            // Put 13, 18, 22 on top of deck.
            powerPlantsDeck  = setAsidePlants.concat(powerPlantsDeck);

            // Put Step 3 card on the bottom.
            powerPlantsDeck.push(step3);
        } else { 
            // No ecological plants will be discarded.
            // For recharged 2 player, remove a random 1 from 3-15 and random 5 from 16-50.
            // For recharged 3 player, remove a random 2 from 3-15 and random 6 from 16-50.
            // For recharged 4 player, remove a random 1 from 3-15 and random 3 from 16-50.
            // Once you have the deck, for recharged the starting 8 are a random 8 from 3-15 (including 13),
            // then a random one from 3-15 on top, then 18, then 22, then the rest of the deck.
            const step3 = powerPlantsDeck.pop()!;
            let powerPlantsDeckLow = powerPlantsDeck.filter((pp) => pp.number >= 3 && pp.number <= 10);
            let plant13 = powerPlantsDeck.filter((pp) => pp.number == 13);
            let otherInitialEcoPlants = powerPlantsDeck.filter((pp) => pp.number == 18 || pp.number == 22);
            let otherEcoPlants = powerPlantsDeck.filter((pp) => ![13, 18, 22].includes(pp.number) && (pp.type == PowerPlantType.Wind || pp.type == PowerPlantType.Nuclear));
            let otherPlants1 = powerPlantsDeck.filter((pp) => pp.type != PowerPlantType.Wind && pp.number >= 11 && pp.number <= 15);
            let otherPlants2 = powerPlantsDeck.filter((pp) => pp.type != PowerPlantType.Wind && pp.type != PowerPlantType.Nuclear && pp.number >= 16);
            if (numPlayers == 2) {
                otherPlants1 = shuffle(otherPlants1, rng() + '').slice(1);
                otherPlants2 = shuffle(otherPlants2, rng() + '').slice(5);
            } else if (numPlayers == 3) {
                otherPlants1 = shuffle(otherPlants1, rng() + '').slice(2);
                otherPlants2 = shuffle(otherPlants2, rng() + '').slice(6);
            } else if (numPlayers == 4) {
                otherPlants1 = shuffle(otherPlants1, rng() + '').slice(1);
                otherPlants2 = shuffle(otherPlants2, rng() + '').slice(3);
            }

            let initialPowerPlantOptions = shuffle(powerPlantsDeckLow.concat(plant13).concat(otherPlants1), rng() + '');
            console.log('Initial deck', initialPowerPlantOptions);
            let initialPlantMarket = initialPowerPlantOptions.splice(0, 8);
            initialPlantMarket = initialPlantMarket.sort((a, b) => a.number - b.number);
            actualMarket = initialPlantMarket.splice(0, 4);
            futureMarket = initialPlantMarket;

            let topOfDeck = initialPowerPlantOptions.splice(0, 1);
            console.log('Top of deck', topOfDeck);
            powerPlantsDeck = initialPowerPlantOptions.concat(otherEcoPlants).concat(otherPlants2);
            powerPlantsDeck = shuffle(powerPlantsDeck, rng() + '');
            powerPlantsDeck = topOfDeck.concat(otherInitialEcoPlants).concat(powerPlantsDeck).concat([step3]);
        }

        console.log('Next deck', powerPlantsDeck);
        return { actualMarket, futureMarket, powerPlantsDeck };
    },
    mapSpecificRules:
        'Put power plants 13, 18, 22 on top of the deck. Ecological power plants will never be put on the bottom of the deck.',
};
