import { AvailableMoves } from './available-moves';
import { LogItem } from './log';
import { Cities, Regions } from './maps';
import { Move } from './move';

export interface GameOptions {
    fastBid?: boolean;
    map?: 'USA' | 'Germany';
    variant?: 'original' | 'recharged';
}

export interface City {
    name: Cities;
    region: Regions;
    x: number;
    y: number;
}

export interface Connection {
    nodes: Cities[];
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
    resourcesUsed: ResourceType[];
}

export enum Phase {
    Order = 'Order',
    Auction = 'Auction',
    Resources = 'Resources',
    Building = 'Building',
    Bureaucracy = 'Bureaucracy',
    GameEnd = 'Game End',
}

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
    citiesToStep2: number;
    citiesToEndGame: number;
    resourceResupply: string[];
    paymentTable: number[];
    minimunBid: number;
    plantDiscountActive: boolean;
    nextCardWeak: boolean;
    cardsLeft: number;
    card39Bought: boolean;
}
