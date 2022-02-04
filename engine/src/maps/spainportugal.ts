import { cloneDeep } from 'lodash';
import { getPowerPlant } from '../engine';
import { PowerPlant } from '../gamestate';
import powerPlants from '../powerPlants';
import { shuffle } from '../utils';
import { Map } from './../maps';

export enum Regions {
    Pink = 'pink',
    Brown = 'brown',
    Green = 'green',
    Purple = 'purple',
    Red = 'red',
    Yellow = 'yellow',
}

export enum Cities {
    Gerona = 'Gerona',
    Barcelona = 'Barcelona',
    Tarragona = 'Tarragona',
    Lerida = 'Lerida',
    Castellondelaplana = 'Castellon De La Plana',
    Valencia = 'Valencia',
    Alicante = 'Alicante',
    Sansebastian = 'San Sebastian',
    Pamplona = 'Pamplona',
    Zaragoza = 'Zaragoza',
    Madrid = 'Madrid',
    Logrono = 'Logrono',
    Bilbao = 'Bilbao',
    Santander = 'Santander',
    Gijon = 'Gijon',
    Leon = 'Leon',
    Valladolid = 'Valladolid',
    Salamanca = 'Salamanca',
    Orense = 'Orense',
    Lacoruna = 'La Coruna',
    Santiagodecompostela = 'Santiago De Compostela',
    Cuenca = 'Cuenca',
    Albacete = 'Albacete',
    Murcia = 'Murcia',
    Toledo = 'Toledo',
    Ciudadreal = 'Ciudad Real',
    Caceres = 'Caceres',
    Merida = 'Merida',
    Almeria = 'Almeria',
    Granada = 'Granada',
    Cordoba = 'Cordoba',
    Malaga = 'Malaga',
    Cadiz = 'Cadiz',
    Sevilla = 'Sevilla',
    Huelva = 'Huelva',
    Evora = 'Evora',
    Faro = 'Faro',
    Portimao = 'Portimao',
    Setubal = 'Setubal',
    Lisboa = 'Lisboa',
    Porto = 'Porto',
    Braga = 'Braga',
}

export const map: Map = {
    name: 'Spain & Portugal',
    cities: [
        { name: Cities.Gerona, region: Regions.Pink, x: 3728, y: 666 },
        { name: Cities.Barcelona, region: Regions.Pink, x: 3538, y: 848 },
        { name: Cities.Tarragona, region: Regions.Pink, x: 3312, y: 970 },
        { name: Cities.Lerida, region: Regions.Pink, x: 3166, y: 752 },
        { name: Cities.Castellondelaplana, region: Regions.Pink, x: 3010, y: 1284 },
        { name: Cities.Valencia, region: Regions.Pink, x: 2938, y: 1580 },
        { name: Cities.Alicante, region: Regions.Pink, x: 2936, y: 1922 },
        { name: Cities.Sansebastian, region: Regions.Brown, x: 2498, y: 278 },
        { name: Cities.Pamplona, region: Regions.Brown, x: 2648, y: 484 },
        { name: Cities.Zaragoza, region: Regions.Brown, x: 2760, y: 810 },
        { name: Cities.Madrid, region: Regions.Brown, x: 2088, y: 1170 },
        { name: Cities.Logrono, region: Regions.Brown, x: 2310, y: 622 },
        { name: Cities.Bilbao, region: Regions.Brown, x: 2264, y: 226 },
        { name: Cities.Santander, region: Regions.Brown, x: 2022, y: 252 },
        { name: Cities.Gijon, region: Regions.Green, x: 1672, y: 190 },
        { name: Cities.Leon, region: Regions.Green, x: 1604, y: 518 },
        { name: Cities.Valladolid, region: Regions.Green, x: 1850, y: 782 },
        { name: Cities.Salamanca, region: Regions.Green, x: 1564, y: 1032 },
        { name: Cities.Orense, region: Regions.Green, x: 1072, y: 532 },
        { name: Cities.Lacoruna, region: Regions.Green, x: 982, y: 184 },
        { name: Cities.Santiagodecompostela, region: Regions.Green, x: 772, y: 394 },
        { name: Cities.Cuenca, region: Regions.Purple, x: 2464, y: 1300 },
        { name: Cities.Albacete, region: Regions.Purple, x: 2532, y: 1684 },
        { name: Cities.Murcia, region: Regions.Purple, x: 2678, y: 2056 },
        { name: Cities.Toledo, region: Regions.Purple, x: 1920, y: 1400 },
        { name: Cities.Ciudadreal, region: Regions.Purple, x: 1982, y: 1714 },
        { name: Cities.Caceres, region: Regions.Purple, x: 1354, y: 1432 },
        { name: Cities.Merida, region: Regions.Purple, x: 1318, y: 1764 },
        { name: Cities.Almeria, region: Regions.Red, x: 2402, y: 2440 },
        { name: Cities.Granada, region: Regions.Red, x: 2044, y: 2272 },
        { name: Cities.Cordoba, region: Regions.Red, x: 1728, y: 2074 },
        { name: Cities.Malaga, region: Regions.Red, x: 1782, y: 2484 },
        { name: Cities.Cadiz, region: Regions.Red, x: 1290, y: 2552 },
        { name: Cities.Sevilla, region: Regions.Red, x: 1390, y: 2168 },
        { name: Cities.Huelva, region: Regions.Red, x: 1082, y: 2196 },
        { name: Cities.Evora, region: Regions.Yellow, x: 890, y: 1780 },
        { name: Cities.Faro, region: Regions.Yellow, x: 822, y: 2348 },
        { name: Cities.Portimao, region: Regions.Yellow, x: 592, y: 2218 },
        { name: Cities.Setubal, region: Regions.Yellow, x: 578, y: 1864 },
        { name: Cities.Lisboa, region: Regions.Yellow, x: 572, y: 1586 },
        { name: Cities.Porto, region: Regions.Yellow, x: 736, y: 1052 },
        { name: Cities.Braga, region: Regions.Yellow, x: 990, y: 828 },
    ],
    connections: [
        { nodes: [Cities.Huelva, Cities.Faro], cost: 6 },
        { nodes: [Cities.Faro, Cities.Portimao], cost: 4 },
        { nodes: [Cities.Portimao, Cities.Setubal], cost: 12 },
        { nodes: [Cities.Setubal, Cities.Evora], cost: 6 },
        { nodes: [Cities.Evora, Cities.Merida], cost: 9 },
        { nodes: [Cities.Merida, Cities.Sevilla], cost: 14 },
        { nodes: [Cities.Sevilla, Cities.Cadiz], cost: 8 },
        { nodes: [Cities.Cadiz, Cities.Malaga], cost: 12 },
        { nodes: [Cities.Malaga, Cities.Granada], cost: 7 },
        { nodes: [Cities.Granada, Cities.Almeria], cost: 9 },
        { nodes: [Cities.Almeria, Cities.Murcia], cost: 13 },
        { nodes: [Cities.Murcia, Cities.Alicante], cost: 4 },
        { nodes: [Cities.Alicante, Cities.Valencia], cost: 9 },
        { nodes: [Cities.Valencia, Cities.Castellondelaplana], cost: 4 },
        { nodes: [Cities.Albacete, Cities.Almeria], cost: 19 },
        { nodes: [Cities.Albacete, Cities.Murcia], cost: 10 },
        { nodes: [Cities.Albacete, Cities.Alicante], cost: 11 },
        { nodes: [Cities.Albacete, Cities.Valencia], cost: 11 },
        { nodes: [Cities.Albacete, Cities.Cuenca], cost: 8 },
        { nodes: [Cities.Albacete, Cities.Ciudadreal], cost: 13 },
        { nodes: [Cities.Albacete, Cities.Granada], cost: 19 },
        { nodes: [Cities.Albacete, Cities.Toledo], cost: 14 },
        { nodes: [Cities.Toledo, Cities.Madrid], cost: 6 },
        { nodes: [Cities.Madrid, Cities.Cuenca], cost: 11 },
        { nodes: [Cities.Cuenca, Cities.Valencia], cost: 13 },
        { nodes: [Cities.Cuenca, Cities.Castellondelaplana], cost: 14 },
        { nodes: [Cities.Castellondelaplana, Cities.Tarragona], cost: 12 },
        { nodes: [Cities.Toledo, Cities.Caceres], cost: 16 },
        { nodes: [Cities.Caceres, Cities.Merida], cost: 4 },
        { nodes: [Cities.Merida, Cities.Ciudadreal], cost: 16 },
        { nodes: [Cities.Ciudadreal, Cities.Granada], cost: 16 },
        { nodes: [Cities.Granada, Cities.Cordoba], cost: 11 },
        { nodes: [Cities.Cordoba, Cities.Malaga], cost: 11 },
        { nodes: [Cities.Malaga, Cities.Sevilla], cost: 12 },
        { nodes: [Cities.Sevilla, Cities.Cordoba], cost: 8 },
        { nodes: [Cities.Cordoba, Cities.Ciudadreal], cost: 10 },
        { nodes: [Cities.Merida, Cities.Cordoba], cost: 14 },
        { nodes: [Cities.Huelva, Cities.Cadiz], cost: 9 },
        { nodes: [Cities.Huelva, Cities.Sevilla], cost: 6 },
        { nodes: [Cities.Merida, Cities.Huelva], cost: 15 },
        { nodes: [Cities.Huelva, Cities.Evora], cost: 12 },
        { nodes: [Cities.Evora, Cities.Faro], cost: 13 },
        { nodes: [Cities.Faro, Cities.Setubal], cost: 14 },
        { nodes: [Cities.Setubal, Cities.Lisboa], cost: 4 },
        { nodes: [Cities.Lisboa, Cities.Evora], cost: 9 },
        { nodes: [Cities.Lisboa, Cities.Merida], cost: 16 },
        { nodes: [Cities.Caceres, Cities.Ciudadreal], cost: 16 },
        { nodes: [Cities.Toledo, Cities.Cuenca], cost: 13 },
        { nodes: [Cities.Salamanca, Cities.Toledo], cost: 14 },
        { nodes: [Cities.Salamanca, Cities.Madrid], cost: 14 },
        { nodes: [Cities.Salamanca, Cities.Caceres], cost: 13 },
        { nodes: [Cities.Porto, Cities.Lisboa], cost: 18 },
        { nodes: [Cities.Porto, Cities.Salamanca], cost: 19 },
        { nodes: [Cities.Porto, Cities.Caceres], cost: 21 },
        { nodes: [Cities.Caceres, Cities.Lisboa], cost: 19 },
        { nodes: [Cities.Ciudadreal, Cities.Toledo], cost: 7 },
        { nodes: [Cities.Braga, Cities.Porto], cost: 3 },
        { nodes: [Cities.Braga, Cities.Salamanca], cost: 19 },
        { nodes: [Cities.Salamanca, Cities.Valladolid], cost: 7 },
        { nodes: [Cities.Valladolid, Cities.Madrid], cost: 13 },
        { nodes: [Cities.Madrid, Cities.Zaragoza], cost: 19 },
        { nodes: [Cities.Zaragoza, Cities.Lerida], cost: 8 },
        { nodes: [Cities.Lerida, Cities.Tarragona], cost: 6 },
        { nodes: [Cities.Tarragona, Cities.Barcelona], cost: 6 },
        { nodes: [Cities.Lerida, Cities.Castellondelaplana], cost: 13 },
        { nodes: [Cities.Castellondelaplana, Cities.Zaragoza], cost: 15 },
        { nodes: [Cities.Zaragoza, Cities.Cuenca], cost: 16 },
        { nodes: [Cities.Braga, Cities.Valladolid], cost: 24 },
        { nodes: [Cities.Lerida, Cities.Barcelona], cost: 10 },
        { nodes: [Cities.Barcelona, Cities.Gerona], cost: 6 },
        { nodes: [Cities.Gerona, Cities.Lerida], cost: 13 },
        { nodes: [Cities.Lerida, Cities.Pamplona], cost: 17 },
        { nodes: [Cities.Pamplona, Cities.Zaragoza], cost: 11 },
        { nodes: [Cities.Zaragoza, Cities.Logrono], cost: 11 },
        { nodes: [Cities.Logrono, Cities.Madrid], cost: 18 },
        { nodes: [Cities.Santiagodecompostela, Cities.Braga], cost: 11 },
        { nodes: [Cities.Braga, Cities.Orense], cost: 9 },
        { nodes: [Cities.Orense, Cities.Santiagodecompostela], cost: 7 },
        { nodes: [Cities.Santiagodecompostela, Cities.Lacoruna], cost: 4 },
        { nodes: [Cities.Lacoruna, Cities.Gijon], cost: 9 },
        { nodes: [Cities.Gijon, Cities.Santander], cost: 11 },
        { nodes: [Cities.Santander, Cities.Bilbao], cost: 6 },
        { nodes: [Cities.Bilbao, Cities.Sansebastian], cost: 5 },
        { nodes: [Cities.Sansebastian, Cities.Pamplona], cost: 6 },
        { nodes: [Cities.Pamplona, Cities.Logrono], cost: 7 },
        { nodes: [Cities.Logrono, Cities.Sansebastian], cost: 9 },
        { nodes: [Cities.Bilbao, Cities.Logrono], cost: 9 },
        { nodes: [Cities.Logrono, Cities.Santander], cost: 13 },
        { nodes: [Cities.Santander, Cities.Valladolid], cost: 16 },
        { nodes: [Cities.Valladolid, Cities.Logrono], cost: 15 },
        { nodes: [Cities.Leon, Cities.Santander], cost: 13 },
        { nodes: [Cities.Gijon, Cities.Leon], cost: 9 },
        { nodes: [Cities.Leon, Cities.Valladolid], cost: 9 },
        { nodes: [Cities.Valladolid, Cities.Orense], cost: 22 },
        { nodes: [Cities.Orense, Cities.Leon], cost: 14 },
        { nodes: [Cities.Gijon, Cities.Orense], cost: 10 },
        { nodes: [Cities.Orense, Cities.Lacoruna], cost: 6 },
    ],
    layout: 'Portrait',
    adjustRatio: [0.315, 0.315],
    mapPosition: [-135, 60],
    resupply: [
        [
            [3, 4, 2],
            [4, 5, 2],
            [4, 6, 3],
            [4, 7, 3],
            [6, 8, 4],
        ],
        [
            [2, 3, 5],
            [2, 4, 5],
            [3, 5, 6],
            [4, 6, 7],
            [5, 7, 9],
        ],
        [
            [1, 2, 3],
            [1, 2, 3],
            [2, 3, 4],
            [3, 3, 5],
            [3, 5, 6],
        ],
        [
            [0, 2, 1],
            [0, 2, 1],
            [0, 4, 1],
            [0, 5, 1],
            [0, 5, 2],
        ],
    ],
    startingResources: [24, 18, 9, 8],
    setupDeck(numPlayers: number, variant: string, rng: seedrandom.prng) {
        let powerPlantsDeck = cloneDeep(powerPlants);
        let actualMarket: PowerPlant[];
        let futureMarket: PowerPlant[];

        // remove plants 18 22 and 27
        powerPlantsDeck = powerPlantsDeck.filter((pp) => ![18, 22, 27].includes(pp.number));

        if (variant == 'original') {
            powerPlantsDeck = powerPlantsDeck.slice(8);
            const powerPlant13 = powerPlantsDeck.splice(2, 1)[0];
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
            let initialPowerPlants = shuffle(powerPlantsDeck.splice(0, 13), rng() + '');
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
            }

            powerPlantsDeck.unshift(first);
            powerPlantsDeck.push(step3);
        }

        return { actualMarket, futureMarket, powerPlantsDeck };
    },
    mapSpecificRules:
        'Remove power plants 18, 22 and 27 from the deck. Place them on top of the deck at the start of Step 2.\nYou cannot buy a nuclear power plant if you only have cities in Portugal.',
};
