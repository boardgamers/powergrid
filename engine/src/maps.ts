import seedrandom from 'seedrandom';
import { PowerPlant } from './gamestate';
import { map as america, mapRecharged as americaRecharged } from './maps/america';
// import { map as australia } from './maps/australia';
import { map as badenwurttemberg } from './maps/badenwurttemberg';
import { map as benelux } from './maps/benelux';
import { map as brazil } from './maps/brazil';
import { map as centraleurope } from './maps/centraleurope';
import { map as china } from './maps/china';
import { map as europe } from './maps/europe';
import { map as france } from './maps/france';
import { map as germany, mapRecharged as germanyRecharged } from './maps/germany';
import { map as indian } from './maps/indian';
import { map as italy } from './maps/italy';
// import { map as japan } from './maps/japan';
import { map as korea } from './maps/korea';
import { map as middleeast } from './maps/middleeast';
import { map as northamerica } from './maps/northamerica';
import { map as northerneurope } from './maps/northerneurope';
import { map as quebec } from './maps/quebec';
import { map as russia } from './maps/russia';
import { map as spainportugal } from './maps/spainportugal';
// import { map as southafrica } from './maps/southafrica';
// import { map as ukireland } from './maps/ukireland';

export interface City {
    name: string;
    region: string;
    x: number;
    y: number;
    // Transregional cities (e.g. Strasbourg on Baden-Württemberg) only open in Step 2,
    // and connecting to them costs a fixed price (transregionalConnectionCost on the GameMap)
    // instead of the normal dijkstra path cost.
    transregional?: boolean;
}

export interface Connection {
    nodes: string[];
    cost: number;
}

export interface Polygon {
    region: string;
    points: number[][];
}

export interface GameMap {
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
    actualMarketWidth?: number;
    mapPosition?: [number, number];
    // Optional rotation in degrees (clockwise) applied around the centroid of
    // the city coordinates. Useful for fitting non-rectangular maps into the
    // viewBox (e.g., Europe).
    mapRotation?: number;
    buttonsPosition?: [number, number];
    playerBoardsPosition?: [number, number];
    supplyPosition?: [number, number];
    roundInfoPosition?: [number, number];
    resupply?: number[][][];
    startingResources?: number[];
    startingSupply?: number[];
    // Korea: parallel North-side resupply / starting tables. Indexed as
    // [resource][playerCount-2][step-1] for resupplyNorth, and [coal, oil, garbage]
    // for the starting arrays (no uranium row — North bans nuclear).
    resupplyNorth?: number[][][];
    startingResourcesNorth?: number[];
    coalPricesNorth?: number[];
    oilPricesNorth?: number[];
    garbagePricesNorth?: number[];
    maxPriceAvailable?: number[]; // For India, only limited sections of the supply are available in step 1 and 2.
    coalPrices?: number[];
    oilPrices?: number[];
    garbagePrices?: number[];
    uraniumPrices?: number[];
    setupDeck?: (
        numPlayers: number,
        variant: string,
        rng: seedrandom.prng
    ) => {
        actualMarket: PowerPlant[];
        futureMarket: PowerPlant[];
        powerPlantsDeck: PowerPlant[];
    };
    regionalPowerPlants?: Record<string, PowerPlant[]>;
    mapSpecificRules?: string;
    // Dev-only: when set, the viewer renders an `<image>` backdrop behind the
    // map and logs click positions (in local SVG coords) to the console as
    // ready-to-paste `{ name, region, x, y }` lines. Intended for authoring
    // city coordinates against a photo of the printed board. Set `adjustRatio`
    // to [1,1] and `mapRotation` to 0 while picking so the logged coords are
    // in the same space you'll save them in.
    devBackdrop?: { src: string; width: number; height: number; opacity?: number };
}

export const maps: GameMap[] = [
    america,
    germany,
    brazil,
    spainportugal,
    france,
    indian,
    italy,
    quebec,
    middleeast,
    china,
    benelux,
    russia,
    centraleurope,
    badenwurttemberg,
    northerneurope,
    korea,
    europe,
    northamerica,
    // australia,
    // japan,
    // southafrica,
    // ukireland,
];

export const mapsRecharged: GameMap[] = [
    americaRecharged,
    germanyRecharged,
    brazil,
    spainportugal,
    france,
    indian,
    italy,
    quebec,
    middleeast,
    china,
    benelux,
    russia,
    centraleurope,
    badenwurttemberg,
    northerneurope,
    korea,
    europe,
    northamerica,
    // australia,
    // china,
    // japan,
    // southafrica,
    // ukireland,
];
