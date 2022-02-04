import seedrandom from 'seedrandom';
import { PowerPlant } from './gamestate';
import { map as america, mapRecharged as americaRecharged } from './maps/america';
// import { map as australia } from './maps/australia';
// import { map as badenwurttemberg } from './maps/badenwurttemberg';
// import { map as benelux } from './maps/benelux';
import { map as brazil } from './maps/brazil';
// import { map as centraleurope } from './maps/centraleurope';
// import { map as china } from './maps/china';
import { map as france } from './maps/france';
import { map as germany, mapRecharged as germanyRecharged } from './maps/germany';
// import { map as indian } from './maps/indian';
import { map as italy } from './maps/italy';
// import { map as japan } from './maps/japan';
// import { map as korea } from './maps/korea';
// import { map as middleeast } from './maps/middleeast';
// import { map as northerneurope } from './maps/northerneurope';
// import { map as quebec } from './maps/quebec';
// import { map as russia } from './maps/russia';
// import { map as southafrica } from './maps/southafrica';
import { map as spainportugal } from './maps/spainportugal';
// import { map as ukireland } from './maps/ukireland';

export interface City {
    name: string;
    region: string;
    x: number;
    y: number;
}

export interface Connection {
    nodes: string[];
    cost: number;
}

export interface Polygon {
    region: string;
    points: number[][];
}

export interface Map {
    name: string;
    cities: City[];
    connections: Connection[];
    polygons?: Polygon[];
    layout?: 'Portrait' | 'Landscape';
    adjustRatio?: [number, number];
    viewBox?: [number, number];
    playerOrderPosition?: [number, number];
    cityCountPosition?: [number, number];
    powerPlantMarketPosition?: [number, number];
    mapPosition?: [number, number];
    buttonsPosition?: [number, number];
    playerBoardsPosition?: [number, number];
    supplyPosition?: [number, number];
    roundInfoPosition?: [number, number];
    resupply?: number[][][];
    startingResources?: number[];
    setupDeck?: (
        numPlayers: number,
        variant: string,
        rng: seedrandom.prng
    ) => {
        actualMarket: PowerPlant[];
        futureMarket: PowerPlant[];
        powerPlantsDeck: PowerPlant[];
    };
    mapSpecificRules?: string;
}

export const maps: Map[] = [
    america,
    germany,
    brazil,
    spainportugal,
    france,
    italy,
    // australia,
    // badenwurttemberg,
    // benelux,
    // centraleurope,
    // china,
    // indian,
    // japan,
    // korea,
    // middleeast,
    // northerneurope,
    // quebec,
    // russia,
    // southafrica,
    // ukireland,
];

export const mapsRecharged: Map[] = [
    americaRecharged,
    germanyRecharged,
    brazil,
    spainportugal,
    france,
    italy,
    // australia,
    // badenwurttemberg,
    // benelux,
    // centraleurope,
    // china,
    // indian,
    // japan,
    // korea,
    // middleeast,
    // northerneurope,
    // quebec,
    // russia,
    // southafrica,
    // ukireland,
];
