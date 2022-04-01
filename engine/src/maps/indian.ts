import { cloneDeep } from 'lodash';
import { getPowerPlant } from '../engine';
import { PowerPlant } from '../gamestate';
import { indiaPowerPlants } from '../powerPlants';
import { shuffle } from '../utils';
import { GameMap } from './../maps';

export enum Regions {
    Red = 'red',
    Brown = 'brown',
    Green = 'green',
    Orange = 'orange',
    Yellow = 'yellow',
    Pink = 'pink',
}

export enum Cities {
    Thiruvananthapuram = 'Thiruvananthapuram',
    Madurai = 'Madurai',
    Coimbatore = 'Coimbatore',
    Chennai = 'Chennai',
    Hyderabad = 'Hyderabad',
    Bangalore1 = 'Bangalore 1',
    Bangalore2 = 'Bangalore 2',
    Dibrugarh = 'Dibrugarh',
    Imphal = 'Imphal',
    Aizawi = 'Aizawi',
    Chittagong = 'Chittagong',
    Shillong = 'Shillong',
    Dhaka = 'Dhaka',
    Khulna = 'Khulna',
    Darjeeling = 'Darjeeling',
    Kathmandu = 'Kathmandu',
    Patna = 'Patna',
    Lakhnau = 'Lakhnau',
    Varanasi = 'Varanasi',
    Agra = 'Agra',
    Kanpur = 'Kanpur',
    Srinagar = 'Srinagar',
    Ludhiana = 'Ludhiana',
    Delhi1 = 'Delhi 1',
    Delhi2 = 'Delhi 2',
    Jaipur = 'Jaipur',
    Udaipur = 'Udaipur',
    Ahmedabad = 'Ahmedabad',
    Dhanbad = 'Dhanbad',
    Kolkata = 'Kolkata',
    Bhudaneswar = 'Bhudaneswar',
    Sambalpur = 'Sambalpur',
    Jabalpur = 'Jabalpur',
    Nagpur = 'Nagpur',
    Visakhapatnam = 'Visakhapatnam',
    Goa = 'Goa',
    Pune = 'Pune',
    Surat = 'Surat',
    Indore = 'Indore',
    Bhopal = 'Bhopal',
    Mumbai1 = 'Mumbai 1',
    Mumbai2 = 'Mumbai 2',
}

export const map: GameMap = {
    name: 'India',
    cities: [
        { name: Cities.Thiruvananthapuram, region: Regions.Red, x: 217, y: 868 },
        { name: Cities.Madurai, region: Regions.Red, x: 230, y: 829 },
        { name: Cities.Coimbatore, region: Regions.Red, x: 197, y: 797 },
        { name: Cities.Chennai, region: Regions.Red, x: 289, y: 740 },
        { name: Cities.Hyderabad, region: Regions.Red, x: 232, y: 618 },
        { name: Cities.Bangalore1, region: Regions.Red, x: 205, y: 710 },
        { name: Cities.Bangalore2, region: Regions.Red, x: 205, y: 735 },
        { name: Cities.Dibrugarh, region: Regions.Brown, x: 669, y: 328 },
        { name: Cities.Imphal, region: Regions.Brown, x: 658, y: 392 },
        { name: Cities.Aizawi, region: Regions.Brown, x: 625, y: 427 },
        { name: Cities.Chittagong, region: Regions.Brown, x: 589, y: 483 },
        { name: Cities.Shillong, region: Regions.Brown, x: 586, y: 395 },
        { name: Cities.Dhaka, region: Regions.Brown, x: 548, y: 432 },
        { name: Cities.Khulna, region: Regions.Brown, x: 528, y: 468 },
        { name: Cities.Darjeeling, region: Regions.Green, x: 496, y: 333 },
        { name: Cities.Kathmandu, region: Regions.Green, x: 418, y: 307 },
        { name: Cities.Patna, region: Regions.Green, x: 416, y: 373 },
        { name: Cities.Lakhnau, region: Regions.Green, x: 310, y: 338 },
        { name: Cities.Varanasi, region: Regions.Green, x: 350, y: 385 },
        { name: Cities.Agra, region: Regions.Green, x: 228, y: 335 },
        { name: Cities.Kanpur, region: Regions.Green, x: 269, y: 373 },
        { name: Cities.Srinagar, region: Regions.Orange, x: 135, y: 115 },
        { name: Cities.Ludhiana, region: Regions.Orange, x: 186, y: 215 },
        { name: Cities.Delhi1, region: Regions.Orange, x: 190, y: 281 },
        { name: Cities.Delhi2, region: Regions.Orange, x: 190, y: 303 },
        { name: Cities.Jaipur, region: Regions.Orange, x: 158, y: 341 },
        { name: Cities.Udaipur, region: Regions.Orange, x: 105, y: 410 },
        { name: Cities.Ahmedabad, region: Regions.Orange, x: 75, y: 456 },
        { name: Cities.Dhanbad, region: Regions.Yellow, x: 424, y: 427 },
        { name: Cities.Kolkata, region: Regions.Yellow, x: 463, y: 477 },
        { name: Cities.Bhudaneswar, region: Regions.Yellow, x: 428, y: 533 },
        { name: Cities.Sambalpur, region: Regions.Yellow, x: 376, y: 494 },
        { name: Cities.Jabalpur, region: Regions.Yellow, x: 293, y: 478 },
        { name: Cities.Nagpur, region: Regions.Yellow, x: 250, y: 510 },
        { name: Cities.Visakhapatnam, region: Regions.Yellow, x: 358, y: 597 },
        { name: Cities.Goa, region: Regions.Pink, x: 109, y: 677 },
        { name: Cities.Pune, region: Regions.Pink, x: 133, y: 587 },
        { name: Cities.Surat, region: Regions.Pink, x: 80, y: 510 },
        { name: Cities.Indore, region: Regions.Pink, x: 160, y: 476 },
        { name: Cities.Bhopal, region: Regions.Pink, x: 208, y: 437 },
        { name: Cities.Mumbai1, region: Regions.Pink, x: 58, y: 570 },
        { name: Cities.Mumbai2, region: Regions.Pink, x: 58, y: 593 },
    ],
    connections: [
        { nodes: [Cities.Srinagar, Cities.Ludhiana], cost: 15 },
        { nodes: [Cities.Ludhiana, Cities.Delhi1], cost: 9 },
        { nodes: [Cities.Delhi1, Cities.Delhi2], cost: 0 },
        { nodes: [Cities.Delhi2, Cities.Jaipur], cost: 7 },
        { nodes: [Cities.Delhi2, Cities.Agra], cost: 6 },
        { nodes: [Cities.Jaipur, Cities.Bhopal], cost: 12 },
        { nodes: [Cities.Jaipur, Cities.Kanpur], cost: 12 },
        { nodes: [Cities.Agra, Cities.Lakhnau], cost: 8 },
        { nodes: [Cities.Lakhnau, Cities.Kathmandu], cost: 15 },
        { nodes: [Cities.Kathmandu, Cities.Darjeeling], cost: 13 },
        { nodes: [Cities.Darjeeling, Cities.Shillong], cost: 12 },
        { nodes: [Cities.Shillong, Cities.Patna], cost: 18 },
        { nodes: [Cities.Patna, Cities.Kathmandu], cost: 10 },
        { nodes: [Cities.Imphal, Cities.Dibrugarh], cost: 11 },
        { nodes: [Cities.Dibrugarh, Cities.Shillong], cost: 9 },
        { nodes: [Cities.Shillong, Cities.Imphal], cost: 12 },
        { nodes: [Cities.Imphal, Cities.Aizawi], cost: 7 },
        { nodes: [Cities.Shillong, Cities.Dhaka], cost: 10 },
        { nodes: [Cities.Dhaka, Cities.Khulna], cost: 6 },
        { nodes: [Cities.Khulna, Cities.Kolkata], cost: 3 },
        { nodes: [Cities.Dhanbad, Cities.Dhaka], cost: 14 },
        { nodes: [Cities.Jabalpur, Cities.Sambalpur], cost: 13 },
        { nodes: [Cities.Sambalpur, Cities.Nagpur], cost: 13 },
        { nodes: [Cities.Nagpur, Cities.Visakhapatnam], cost: 17 },
        { nodes: [Cities.Visakhapatnam, Cities.Sambalpur], cost: 12 },
        { nodes: [Cities.Jabalpur, Cities.Kanpur], cost: 11 },
        { nodes: [Cities.Varanasi, Cities.Jabalpur], cost: 11 },
        { nodes: [Cities.Kanpur, Cities.Varanasi], cost: 8 },
        { nodes: [Cities.Varanasi, Cities.Patna], cost: 5 },
        { nodes: [Cities.Patna, Cities.Lakhnau], cost: 11 },
        { nodes: [Cities.Kanpur, Cities.Bhopal], cost: 13 },
        { nodes: [Cities.Ahmedabad, Cities.Bhopal], cost: 11 },
        { nodes: [Cities.Bhopal, Cities.Udaipur], cost: 11 },
        { nodes: [Cities.Udaipur, Cities.Jaipur], cost: 9 },
        { nodes: [Cities.Ahmedabad, Cities.Surat], cost: 7 },
        { nodes: [Cities.Ahmedabad, Cities.Indore], cost: 8 },
        { nodes: [Cities.Indore, Cities.Surat], cost: 10 },
        { nodes: [Cities.Mumbai1, Cities.Mumbai2], cost: 0 },
        { nodes: [Cities.Mumbai2, Cities.Pune], cost: 4 },
        { nodes: [Cities.Pune, Cities.Hyderabad], cost: 13 },
        { nodes: [Cities.Pune, Cities.Nagpur], cost: 17 },
        { nodes: [Cities.Pune, Cities.Indore], cost: 15 },
        { nodes: [Cities.Goa, Cities.Coimbatore], cost: 18 },
        { nodes: [Cities.Bangalore1, Cities.Bangalore2], cost: 0 },
        { nodes: [Cities.Bangalore2, Cities.Coimbatore], cost: 9 },
        { nodes: [Cities.Coimbatore, Cities.Thiruvananthapuram], cost: 10 },
        { nodes: [Cities.Thiruvananthapuram, Cities.Madurai], cost: 7 },
        { nodes: [Cities.Madurai, Cities.Chennai], cost: 12 },
        { nodes: [Cities.Chennai, Cities.Bangalore1], cost: 9 },
        { nodes: [Cities.Bangalore1, Cities.Hyderabad], cost: 14 },
        { nodes: [Cities.Hyderabad, Cities.Goa], cost: 15 },
        { nodes: [Cities.Goa, Cities.Bangalore2], cost: 14 },
        { nodes: [Cities.Mumbai2, Cities.Goa], cost: 11 },
        { nodes: [Cities.Indore, Cities.Nagpur], cost: 10 },
        { nodes: [Cities.Sambalpur, Cities.Dhanbad], cost: 8 },
        { nodes: [Cities.Sambalpur, Cities.Bhudaneswar], cost: 7 },
        { nodes: [Cities.Bhudaneswar, Cities.Kolkata], cost: 11 },
        { nodes: [Cities.Kolkata, Cities.Dhanbad], cost: 9 },
        { nodes: [Cities.Dhanbad, Cities.Patna], cost: 8 },
        { nodes: [Cities.Nagpur, Cities.Hyderabad], cost: 12 },
        { nodes: [Cities.Hyderabad, Cities.Visakhapatnam], cost: 13 },
        { nodes: [Cities.Visakhapatnam, Cities.Chennai], cost: 17 },
        { nodes: [Cities.Chittagong, Cities.Aizawi], cost: 7 },
        { nodes: [Cities.Dhaka, Cities.Aizawi], cost: 8 },
        { nodes: [Cities.Dhaka, Cities.Chittagong], cost: 7 },
        { nodes: [Cities.Patna, Cities.Darjeeling], cost: 11 },
        { nodes: [Cities.Visakhapatnam, Cities.Bhudaneswar], cost: 12 },
        { nodes: [Cities.Udaipur, Cities.Ahmedabad], cost: 6 },
        { nodes: [Cities.Madurai, Cities.Coimbatore], cost: 6 },
        { nodes: [Cities.Bangalore2, Cities.Madurai], cost: 10 },
        { nodes: [Cities.Bhopal, Cities.Jabalpur], cost: 8 },
        { nodes: [Cities.Bhopal, Cities.Nagpur], cost: 7 },
        { nodes: [Cities.Bhopal, Cities.Indore], cost: 4 },
        { nodes: [Cities.Surat, Cities.Mumbai1], cost: 6 },
        { nodes: [Cities.Agra, Cities.Kanpur], cost: 8 },
        { nodes: [Cities.Kanpur, Cities.Lakhnau], cost: 3 },
        { nodes: [Cities.Lakhnau, Cities.Varanasi], cost: 7 },
    ],
    layout: 'Portrait',
    mapPosition: [200, -60],
    adjustRatio: [1.25, 1.25],
    resupply: [
        [
            [4, 5, 4],
            [5, 6, 4],
            [6, 7, 5],
            [7, 8, 6],
            [8, 10, 7],
        ],
        [
            [1, 2, 2],
            [2, 2, 2],
            [2, 3, 3],
            [3, 4, 4],
            [4, 5, 5],
        ],
        [
            [1, 3, 4],
            [1, 3, 4],
            [3, 4, 6],
            [4, 5, 7],
            [4, 7, 9],
        ],
        [
            [1, 1, 1],
            [1, 1, 1],
            [1, 2, 1],
            [2, 2, 2],
            [2, 3, 2],
        ],
    ],
    startingResources: [24, 21, 21, 7], // Prices begin at: coal 1 Elektro, oil 2 Elektro, garbage 2 Elektro and uranium 6 Elektro. 
    startingSupply: [24, 24, 24, 8], // Use only 8 uranium instead of 12
    maxPriceAvailable: [3, 5, 16],
    setupDeck(numPlayers: number, variant: string, rng: seedrandom.prng) {
        let powerPlantsDeck = cloneDeep(indiaPowerPlants);
        let actualMarket: PowerPlant[];
        let futureMarket: PowerPlant[];

        // The rest is identical to the normal deck setup.
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
    
            actualMarket = [getPowerPlant(3, 'India'), getPowerPlant(4, 'India'), getPowerPlant(5, 'India'), getPowerPlant(6, 'India')];
            futureMarket = [getPowerPlant(7, 'India'), getPowerPlant(8, 'India'), getPowerPlant(9, 'India'), getPowerPlant(10, 'India')];
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
    
        console.log(actualMarket);
        console.log(futureMarket);
        console.log(powerPlantsDeck);

        return { actualMarket, futureMarket, powerPlantsDeck };
    },
    mapSpecificRules:
        'The power grid will suffer a power outage if too many cities are built in one round, penalizing players based on their number of cities.\nThe resource market is limited in steps 1 and 2.\nGarbage plants are less efficient.\nPlayers must power as many cities as possible.'
};
