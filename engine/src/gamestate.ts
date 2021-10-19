import { AvailableMoves } from './available-moves';
import { LogItem } from './log';
import { Move } from './move';

export interface GameOptions {
    fastBid?: boolean;
}

export interface City {
    name: string;
    area: string;
    x: number;
    y: number;
}

export interface Connection {
    from: string;
    to: string;
    cost: number;
}

export interface Map {
    name: string;
    cities: City[];
    connections: Connection[];
}

export enum ResourceType {
    Coal = 'coal',
    Oil = 'oil',
    Garbage = 'garbage',
    Uranium = 'uranium',
}

export enum PowerPlantType {
    Coal,
    Oil,
    Garbage,
    Uranium,
    Hybrid,
    Wind,
    Nuclear,
}

export interface PowerPlant {
    number: number;
    type: PowerPlantType;
    cost: number;
    citiesPowered: number;
}

export interface CityPosition {
    name: string;
    position: number;
}

export interface Player {
    id: number;
    name?: string;
    powerPlants: PowerPlant[];
    coalCapacity: number;
    coalLeft: number;
    oilCapacity: number;
    oilLeft: number;
    garbageCapacity: number;
    garbageLeft: number;
    uraniumCapacity: number;
    uraniumLeft: number;
    hybridCapacity: number;
    money: number;
    housesLeft: number;
    cities: CityPosition[];
    powerPlantsNotUsed: number[];
    availableMoves: AvailableMoves | null;
    lastMove: Move | null;
    isDropped: boolean;
    bid: number;
    isAI: boolean;
    passed: boolean;
    skipAuction: boolean;
    citiesPowered: number;
}

export enum Phase {
    Order = 'order',
    Auction = 'auction',
    Resources = 'resources',
    Building = 'building',
    Bureaucracy = 'bureaucracy',
    GameEnd = 'gameEnd',
}

// export interface HousePiece {
//     id: `H${number}`;
// }

// export interface CoalPiece {
//     id: `C${number}`;
// }

// export interface OilPiece {
//     id: `O${number}`;
// }

// export interface GarbagePiece {
//     id: `G${number}`;
// }

// export interface UraniumPiece {
//     id: `U${number}`;
// }

export interface GameState {
    map: Map;
    players: Player[];
    playerOrder: number[];
    currentPlayers: number[];
    powerPlantsDeck: PowerPlant[];
    coalSupply: number;
    oilSupply: number;
    garbageSupply: number;
    uraniumSupply: number;
    coalMarket: number;
    oilMarket: number;
    garbageMarket: number;
    uraniumMarket: number;
    actualMarket: PowerPlant[];
    futureMarket: PowerPlant[];
    chosenPowerPlant: PowerPlant | undefined;
    currentBid: number | undefined;
    auctioningPlayer: number | undefined;
    highestBidders: number[];
    step: number;
    phase: Phase;
    options: GameOptions;
    log: LogItem[];
    hiddenLog: LogItem[];
    seed: string;
    round: number;
    auctionSkips: number;
}
