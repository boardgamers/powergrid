import { cloneDeep } from 'lodash';
import seedrandom from 'seedrandom';
import { getPowerPlant } from '../engine';
import { PowerPlant, PowerPlantType } from '../gamestate';
import { shuffle } from '../utils';
import { Map } from './../maps';
import powerPlants from './../powerPlants';

export enum Regions {
    Red = 'red',
    Pink = 'pink',
    Purple = 'purple',
    Green = 'green',
    Brown = 'brown',
    Yellow = 'yellow',
}

export enum Cities {
    Parnaiba = 'Parnaiba',
    Fortaleza = 'Fortaleza',
    Sadluis = 'Sadluis',
    Belem = 'Belem',
    Teresina = 'Teresina',
    Imperatriz = 'Imperatriz',
    Maraba = 'Maraba',
    Campinagrande = 'Campina Grande',
    Petrolina = 'Petrolina',
    Natal = 'Natal',
    Joaopessoa = 'Joaopessoa',
    Recife = 'Recife',
    Maceio = 'Maceio',
    Aracaju = 'Aracaju',
    Salvadordabahia = 'Salvador Da Bahia',
    Montesclaros = 'Montes Claros',
    Brasilia = 'Brasilia',
    Palmas = 'Palmas',
    Porangatu = 'Porangatu',
    Goiania = 'Goiania',
    Uberlandia = 'Uberlandia',
    Vitoria = 'Vitoria',
    Riodejaneiro = 'Rio De Janeiro',
    Saogoncalo = 'Sao Goncalo',
    Saopaulo = 'Sao Paulo',
    Guarulhos = 'Guarulhos',
    Campinas = 'Campinas',
    Belohorizonte = 'Belo Horizonte',
    Curitiba = 'Curitiba',
    Florianopolis = 'Florianopolis',
    Portoalecre = 'Porto Alecre',
    Pelotas = 'Pelotas',
    Urucuaiana = 'Urucuaiana',
    Londrina = 'Londrina',
    Campogrande = 'Campo Grande',
    Macapa = 'Macapa',
    Boavista = 'Boavista',
    Manaus = 'Manaus',
    Portovelho = 'Porto Velho',
    Cuiaba = 'Cuiaba',
    Vilhena = 'Vilhena',
    Riobranco = 'Rio Branco',
}

export const map: Map = {
    name: 'Brazil',
    cities: [
        { name: Cities.Parnaiba, region: Regions.Red, x: 855, y: 458 },
        { name: Cities.Fortaleza, region: Regions.Red, x: 961, y: 478 },
        { name: Cities.Sadluis, region: Regions.Red, x: 772, y: 418 },
        { name: Cities.Belem, region: Regions.Red, x: 655, y: 378 },
        { name: Cities.Teresina, region: Regions.Red, x: 846, y: 548 },
        { name: Cities.Imperatriz, region: Regions.Red, x: 697, y: 535 },
        { name: Cities.Maraba, region: Regions.Red, x: 581, y: 492 },
        { name: Cities.Campinagrande, region: Regions.Pink, x: 976, y: 587 },
        { name: Cities.Petrolina, region: Regions.Pink, x: 872, y: 648 },
        { name: Cities.Natal, region: Regions.Pink, x: 1061, y: 518 },
        { name: Cities.Joaopessoa, region: Regions.Pink, x: 1097, y: 576 },
        { name: Cities.Recife, region: Regions.Pink, x: 1083, y: 637 },
        { name: Cities.Maceio, region: Regions.Pink, x: 1040, y: 699 },
        { name: Cities.Aracaju, region: Regions.Pink, x: 995, y: 750 },
        { name: Cities.Salvadordabahia, region: Regions.Purple, x: 960, y: 808 },
        { name: Cities.Montesclaros, region: Regions.Purple, x: 795, y: 847 },
        { name: Cities.Brasilia, region: Regions.Purple, x: 671, y: 817 },
        { name: Cities.Palmas, region: Regions.Purple, x: 648, y: 663 },
        { name: Cities.Porangatu, region: Regions.Purple, x: 598, y: 762 },
        { name: Cities.Goiania, region: Regions.Purple, x: 601, y: 889 },
        { name: Cities.Uberlandia, region: Regions.Purple, x: 646, y: 964 },
        { name: Cities.Vitoria, region: Regions.Green, x: 910, y: 971 },
        { name: Cities.Riodejaneiro, region: Regions.Green, x: 795, y: 1076 },
        { name: Cities.Saogoncalo, region: Regions.Green, x: 843, y: 1033 },
        { name: Cities.Saopaulo, region: Regions.Green, x: 721, y: 1134 },
        { name: Cities.Guarulhos, region: Regions.Green, x: 678, y: 1089 },
        { name: Cities.Campinas, region: Regions.Green, x: 629, y: 1037 },
        { name: Cities.Belohorizonte, region: Regions.Green, x: 771, y: 960 },
        { name: Cities.Curitiba, region: Regions.Brown, x: 615, y: 1144 },
        { name: Cities.Florianopolis, region: Regions.Brown, x: 665, y: 1214 },
        { name: Cities.Portoalecre, region: Regions.Brown, x: 590, y: 1281 },
        { name: Cities.Pelotas, region: Regions.Brown, x: 551, y: 1346 },
        { name: Cities.Urucuaiana, region: Regions.Brown, x: 444, y: 1250 },
        { name: Cities.Londrina, region: Regions.Brown, x: 516, y: 1075 },
        { name: Cities.Campogrande, region: Regions.Brown, x: 440, y: 983 },
        { name: Cities.Macapa, region: Regions.Yellow, x: 561, y: 317 },
        { name: Cities.Boavista, region: Regions.Yellow, x: 308, y: 269 },
        { name: Cities.Manaus, region: Regions.Yellow, x: 258, y: 466 },
        { name: Cities.Portovelho, region: Regions.Yellow, x: 238, y: 620 },
        { name: Cities.Cuiaba, region: Regions.Yellow, x: 432, y: 850 },
        { name: Cities.Vilhena, region: Regions.Yellow, x: 328, y: 741 },
        { name: Cities.Riobranco, region: Regions.Yellow, x: 87, y: 666 },
    ],
    connections: [
        { nodes: [Cities.Boavista, Cities.Macapa], cost: 22 },
        { nodes: [Cities.Macapa, Cities.Belem], cost: 10 },
        { nodes: [Cities.Belem, Cities.Sadluis], cost: 10 },
        { nodes: [Cities.Sadluis, Cities.Imperatriz], cost: 9 },
        { nodes: [Cities.Belem, Cities.Imperatriz], cost: 9 },
        { nodes: [Cities.Belem, Cities.Maraba], cost: 9 },
        { nodes: [Cities.Macapa, Cities.Maraba], cost: 16 },
        { nodes: [Cities.Maraba, Cities.Manaus], cost: 22 },
        { nodes: [Cities.Macapa, Cities.Manaus], cost: 18 },
        { nodes: [Cities.Boavista, Cities.Manaus], cost: 13 },
        { nodes: [Cities.Boavista, Cities.Riobranco], cost: 30 },
        { nodes: [Cities.Riobranco, Cities.Manaus], cost: 23 },
        { nodes: [Cities.Manaus, Cities.Portovelho], cost: 15 },
        { nodes: [Cities.Portovelho, Cities.Riobranco], cost: 10 },
        { nodes: [Cities.Riobranco, Cities.Vilhena], cost: 18 },
        { nodes: [Cities.Portovelho, Cities.Vilhena], cost: 12 },
        { nodes: [Cities.Manaus, Cities.Vilhena], cost: 21 },
        { nodes: [Cities.Vilhena, Cities.Cuiaba], cost: 10 },
        { nodes: [Cities.Vilhena, Cities.Maraba], cost: 31 },
        { nodes: [Cities.Maraba, Cities.Imperatriz], cost: 4 },
        { nodes: [Cities.Sadluis, Cities.Teresina], cost: 8 },
        { nodes: [Cities.Teresina, Cities.Imperatriz], cost: 11 },
        { nodes: [Cities.Imperatriz, Cities.Palmas], cost: 9 },
        { nodes: [Cities.Palmas, Cities.Maraba], cost: 10 },
        { nodes: [Cities.Maraba, Cities.Porangatu], cost: 17 },
        { nodes: [Cities.Porangatu, Cities.Goiania], cost: 8 },
        { nodes: [Cities.Porangatu, Cities.Vilhena], cost: 23 },
        { nodes: [Cities.Cuiaba, Cities.Porangatu], cost: 16 },
        { nodes: [Cities.Porangatu, Cities.Palmas], cost: 8 },
        { nodes: [Cities.Palmas, Cities.Brasilia], cost: 13 },
        { nodes: [Cities.Brasilia, Cities.Porangatu], cost: 6 },
        { nodes: [Cities.Brasilia, Cities.Goiania], cost: 4 },
        { nodes: [Cities.Goiania, Cities.Cuiaba], cost: 15 },
        { nodes: [Cities.Sadluis, Cities.Parnaiba], cost: 5 },
        { nodes: [Cities.Parnaiba, Cities.Teresina], cost: 5 },
        { nodes: [Cities.Parnaiba, Cities.Fortaleza], cost: 7 },
        { nodes: [Cities.Fortaleza, Cities.Natal], cost: 8 },
        { nodes: [Cities.Natal, Cities.Joaopessoa], cost: 3 },
        { nodes: [Cities.Joaopessoa, Cities.Recife], cost: 2 },
        { nodes: [Cities.Recife, Cities.Maceio], cost: 3 },
        { nodes: [Cities.Maceio, Cities.Aracaju], cost: 3 },
        { nodes: [Cities.Aracaju, Cities.Salvadordabahia], cost: 4 },
        { nodes: [Cities.Natal, Cities.Campinagrande], cost: 4 },
        { nodes: [Cities.Fortaleza, Cities.Teresina], cost: 10 },
        { nodes: [Cities.Teresina, Cities.Petrolina], cost: 12 },
        { nodes: [Cities.Petrolina, Cities.Palmas], cost: 19 },
        { nodes: [Cities.Petrolina, Cities.Brasilia], cost: 22 },
        { nodes: [Cities.Petrolina, Cities.Montesclaros], cost: 19 },
        { nodes: [Cities.Montesclaros, Cities.Salvadordabahia], cost: 16 },
        { nodes: [Cities.Salvadordabahia, Cities.Petrolina], cost: 10 },
        { nodes: [Cities.Petrolina, Cities.Campinagrande], cost: 12 },
        { nodes: [Cities.Petrolina, Cities.Aracaju], cost: 11 },
        { nodes: [Cities.Vitoria, Cities.Salvadordabahia], cost: 16 },
        { nodes: [Cities.Montesclaros, Cities.Vitoria], cost: 14 },
        { nodes: [Cities.Vitoria, Cities.Saogoncalo], cost: 6 },
        { nodes: [Cities.Vitoria, Cities.Belohorizonte], cost: 9 },
        { nodes: [Cities.Belohorizonte, Cities.Montesclaros], cost: 8 },
        { nodes: [Cities.Montesclaros, Cities.Brasilia], cost: 9 },
        { nodes: [Cities.Brasilia, Cities.Uberlandia], cost: 8 },
        { nodes: [Cities.Uberlandia, Cities.Goiania], cost: 7 },
        { nodes: [Cities.Goiania, Cities.Campogrande], cost: 16 },
        { nodes: [Cities.Campogrande, Cities.Cuiaba], cost: 13 },
        { nodes: [Cities.Campogrande, Cities.Londrina], cost: 10 },
        { nodes: [Cities.Campogrande, Cities.Uberlandia], cost: 13 },
        { nodes: [Cities.Uberlandia, Cities.Londrina], cost: 12 },
        { nodes: [Cities.Londrina, Cities.Campinas], cost: 9 },
        { nodes: [Cities.Campinas, Cities.Uberlandia], cost: 9 },
        { nodes: [Cities.Uberlandia, Cities.Belohorizonte], cost: 10 },
        { nodes: [Cities.Uberlandia, Cities.Brasilia], cost: 8 },
        { nodes: [Cities.Brasilia, Cities.Belohorizonte], cost: 14 },
        { nodes: [Cities.Belohorizonte, Cities.Saogoncalo], cost: 7 },
        { nodes: [Cities.Saogoncalo, Cities.Riodejaneiro], cost: 0 },
        { nodes: [Cities.Riodejaneiro, Cities.Saopaulo], cost: 7 },
        { nodes: [Cities.Saopaulo, Cities.Guarulhos], cost: 0 },
        { nodes: [Cities.Guarulhos, Cities.Campinas], cost: 0 },
        { nodes: [Cities.Campinas, Cities.Curitiba], cost: 6 },
        { nodes: [Cities.Curitiba, Cities.Londrina], cost: 7 },
        { nodes: [Cities.Saopaulo, Cities.Florianopolis], cost: 9 },
        { nodes: [Cities.Florianopolis, Cities.Curitiba], cost: 4 },
        { nodes: [Cities.Londrina, Cities.Urucuaiana], cost: 18 },
        { nodes: [Cities.Urucuaiana, Cities.Pelotas], cost: 9 },
        { nodes: [Cities.Pelotas, Cities.Portoalecre], cost: 4 },
        { nodes: [Cities.Portoalecre, Cities.Urucuaiana], cost: 10 },
        { nodes: [Cities.Londrina, Cities.Portoalecre], cost: 16 },
        { nodes: [Cities.Portoalecre, Cities.Curitiba], cost: 11 },
        { nodes: [Cities.Portoalecre, Cities.Florianopolis], cost: 7 },
        { nodes: [Cities.Guarulhos, Cities.Belohorizonte], cost: 10 },
        { nodes: [Cities.Maceio, Cities.Campinagrande], cost: 6 },
        { nodes: [Cities.Petrolina, Cities.Fortaleza], cost: 14 },
        { nodes: [Cities.Recife, Cities.Campinagrande], cost: 3 },
    ],
    layout: 'Portrait',
    adjustRatio: [0.85, 0.85],
    mapPosition: [-20, -130],
    resupply: [
        [
            [1, 2, 3],
            [1, 2, 3],
            [2, 3, 4],
            [3, 3, 5],
            [3, 5, 6],
        ],
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
            [1, 1, 1],
            [1, 1, 1],
            [1, 2, 2],
            [2, 3, 2],
            [2, 3, 3],
        ],
    ],
    startingResources: [24, 18, 6, 2],
    setupDeck(numPlayers: number, variant: string, rng: seedrandom.prng) {
        let powerPlantsDeck = cloneDeep(powerPlants);
        let actualMarket: PowerPlant[];
        let futureMarket: PowerPlant[];

        // remove garbage power plants
        const garbagePlants = powerPlantsDeck.filter((pp) => pp.type == PowerPlantType.Garbage && pp.number > 14);

        if (variant == 'original') {
            powerPlantsDeck = powerPlantsDeck.slice(8);
            const powerPlant13 = powerPlantsDeck.splice(2, 1)[0];
            const powerPlant14 = powerPlantsDeck.splice(2, 1)[0];
            const step3 = powerPlantsDeck.pop()!;

            powerPlantsDeck = shuffle(
                powerPlantsDeck.filter((pp) => pp.type != PowerPlantType.Garbage),
                rng() + ''
            );
            if (numPlayers == 2 || numPlayers == 3) {
                powerPlantsDeck = powerPlantsDeck.slice(8);
            } else if (numPlayers == 4) {
                powerPlantsDeck = powerPlantsDeck.slice(4);
            }

            powerPlantsDeck = powerPlantsDeck.concat(garbagePlants);
            powerPlantsDeck = shuffle(powerPlantsDeck, rng() + '');

            powerPlantsDeck.unshift(powerPlant14);
            powerPlantsDeck.unshift(powerPlant13);
            powerPlantsDeck.push(step3);

            actualMarket = [getPowerPlant(3), getPowerPlant(4), getPowerPlant(5), getPowerPlant(6)];
            futureMarket = [getPowerPlant(7), getPowerPlant(8), getPowerPlant(9), getPowerPlant(10)];
        } else {
            const powerPlant6 = powerPlantsDeck.splice(3, 1)[0];
            const powerPlant14 = powerPlantsDeck.splice(10, 1)[0];

            let initialPowerPlants = shuffle(powerPlantsDeck.splice(0, 11), rng() + '');
            let initialPlantMarket = initialPowerPlants.splice(0, 6);
            initialPlantMarket.push(powerPlant6, powerPlant14);
            initialPlantMarket = initialPlantMarket.sort((a, b) => a.number - b.number);
            actualMarket = initialPlantMarket.slice(0, 4);
            futureMarket = initialPlantMarket.slice(4);

            const first = initialPowerPlants.shift()!;
            const step3 = powerPlantsDeck.pop()!;

            powerPlantsDeck = shuffle(
                powerPlantsDeck.filter((pp) => pp.type != PowerPlantType.Garbage),
                rng() + ''
            );
            if (numPlayers == 2 || numPlayers == 3) {
                initialPowerPlants = initialPowerPlants.slice(2);
                powerPlantsDeck = shuffle(powerPlantsDeck.slice(6).concat(initialPowerPlants), rng() + '');
            } else if (numPlayers == 4) {
                initialPowerPlants = initialPowerPlants.slice(1);
                powerPlantsDeck = shuffle(powerPlantsDeck.slice(3).concat(initialPowerPlants), rng() + '');
            }

            powerPlantsDeck = powerPlantsDeck.concat(garbagePlants);
            powerPlantsDeck = shuffle(powerPlantsDeck, rng() + '');

            powerPlantsDeck.unshift(first);
            powerPlantsDeck.push(step3);
        }

        return { actualMarket, futureMarket, powerPlantsDeck };
    },
    mapSpecificRules: 'Play with all garbage power plants.',
};
