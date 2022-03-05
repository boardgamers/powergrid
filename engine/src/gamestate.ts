import { AvailableMoves } from './available-moves';
import { LogItem } from './log';
import { GameMap } from './maps';
import { Move } from './move';

export type MapName = 'USA' | 'Germany' | 'Brazil' | 'Spain & Portugal' | 'France' | 'Italy' | 'Quebec' | 'Middle East';
// | 'Australia'
// | 'Baden-Württemberg'
// | 'Benelux'
// | 'Central Europe'
// | 'China'
// | 'Indian'
// | 'Japan'
// | 'Korea'
// | 'Northern Europe'
// | 'Russia'
// | 'South Africa'
// | 'UK & Ireland'
export type Variant = 'original' | 'recharged';

export interface GameOptions {
    fastBid?: boolean;
    map?: MapName;
    variant?: Variant;
    showMoney?: boolean;
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
    map: GameMap;
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
    coalResupply?: number[][];
    oilResupply?: number[][];
    garbageResupply?: number[][];
    uraniumResupply?: number[][];
    oilPrices: number[]; // Adjust oil price for Middle East map.
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
    knownPowerPlantDeck: PowerPlant[];
    knownPowerPlantDeckStep3: PowerPlant[];
    powerPlantDeckAfterStep3: PowerPlant[] | undefined;
}
