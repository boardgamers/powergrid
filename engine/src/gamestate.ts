import { AvailableMoves } from './available-moves';
import { LogItem } from './log';
import { GameMap } from './maps';
import { Move } from './move';

export type MapName =
    | 'USA'
    | 'Germany'
    | 'Brazil'
    | 'Spain & Portugal'
    | 'France'
    | 'Italy'
    | 'Quebec'
    | 'Middle East'
    | 'India'
    | 'China'
    | 'Benelux'
    | 'Russia'
    | 'Central Europe'
    | 'Baden-Württemberg'
    | 'Northern Europe'
    | 'Korea'
    | 'Europe'
    | 'North America'
    | 'South Africa'
    | 'UK & Ireland'
    | 'Japan';
// | 'Australia'
export type Variant = 'original' | 'recharged';

export interface GameOptions {
    fastBid?: boolean;
    map?: MapName;
    variant?: Variant;
    showMoney?: boolean;
    useNewRechargedSetup?: boolean;
    trackTotalSpent?: boolean;
    randomizeMap?: boolean;
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
    Step3,
}

export interface PowerPlant {
    number: number;
    type: PowerPlantType;
    cost: number;
    citiesPowered: number;
    storage?: number;
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
    targetCitiesPowered?: number;
    resourcesUsed: ResourceType[];
    totalIncome: number;
    totalSpentCities: number;
    totalSpentConnections: number;
    totalSpentPlants: number;
    totalSpentResources: number;
    ranking?: number;
    usedFreeJump?: boolean;
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
    // South Africa: coal used to power plants returns here instead of coalSupply.
    // Market refills draw from this pool first, then fall back to coalSupply.
    // Players can always buy a coal cube from here for $8 (on top of the normal
    // market). Undefined on non-SA maps.
    coalStorage?: number;
    coalMarket: number;
    oilMarket: number;
    garbageMarket: number;
    uraniumMarket: number;
    coalResupply?: number[][];
    oilResupply?: number[][];
    garbageResupply?: number[][];
    uraniumResupply?: number[][];
    // Korea: parallel North-side markets and resupply tables. The primary
    // `*Market`/`*Resupply` fields above act as the South side. The supply pools
    // (`coalSupply` etc.) are SHARED — used cubes return there and both sides
    // restock from the same pool, with North restocking first.
    // North has no uranium track (nuclear plants are banned on the North side).
    coalMarketNorth?: number;
    oilMarketNorth?: number;
    garbageMarketNorth?: number;
    coalResupplyNorth?: number[][];
    oilResupplyNorth?: number[][];
    garbageResupplyNorth?: number[][];
    // Korea: per-side price arrays. Each side's market has different slot counts
    // per price space, so the price arrays differ. (No uranium on the North side.)
    coalPricesNorth?: number[];
    oilPricesNorth?: number[];
    garbagePricesNorth?: number[];
    coalPrices?: number[];
    oilPrices?: number[];
    garbagePrices?: number[];
    uraniumPrices?: number[];
    actualMarket: PowerPlant[];
    futureMarket: PowerPlant[];
    chosenPowerPlant: PowerPlant | undefined;
    chosenResource?: ResourceType | undefined; // Used for India map, where only one resource can be bought at a time.
    // Korea: locked to the side a player bought their first resource from this turn.
    // All subsequent buys this turn must be from the same side. Cleared when the player passes.
    chosenSide?: 'north' | 'south';
    currentBid: number | undefined;
    auctioningPlayer: number | undefined;
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
    citiesBuiltInCurrentRound?: number; // In India, if the players build too many cities in a single round, a power outage will occur.
    resourceResupply: string[];
    resourceResupplyNorth?: string[]; // Korea: per-step North resupply, parallel to resourceResupply (no uranium).
    paymentTable: number[];
    minimunBid: number;
    plantDiscountActive: boolean;
    discardSmallestPlant: boolean; // For Benelux map, there are times when we remove the smallest plant.
    nextCardWeak: boolean;
    cardsLeft: number;
    card39Bought: boolean;
    knownPowerPlantDeck: PowerPlant[];
    knownPowerPlantDeckStep3: PowerPlant[];
    powerPlantDeckAfterStep3: PowerPlant[] | undefined;
}
