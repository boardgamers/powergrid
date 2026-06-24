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
    | 'Japan'
    | 'Australia'
    | 'Bremen'
    | 'Manhattan';
export type Variant = 'original' | 'recharged';

export interface GameOptions {
    fastBid?: boolean;
    map?: MapName;
    variant?: Variant;
    showMoney?: boolean;
    useNewRechargedSetup?: boolean;
    trackTotalSpent?: boolean;
    randomizeMap?: boolean;
    // When set, the regions in play are drafted by the players at the start of
    // the game (each picks in turn) instead of being chosen randomly at setup.
    chooseRegions?: boolean;
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
    RegionSelection = 'Region Selection',
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
    // Australia: the separate 12-slot uranium "mine" market. Six price columns
    // ($2–$7), two slots each, indexed 0→$2 … 5→$7. Each entry is the number of
    // uranium tokens (0–2) in that column. Undefined on every other map.
    uraniumMineMarket?: number[];
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
    // Present only while phase == RegionSelection (chooseRegions option). Tracks
    // how many regions must be drafted and which have been picked so far. Cleared
    // once the draft completes and the map is filtered to the chosen regions.
    regionDraft?: { regionsNeeded: number; picked: string[] };
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
    // Manhattan market lifecycle (see applyManhattanMarketLifecycle in engine.ts).
    // The "separate pile" of plants set aside from the future market each round —
    // recyclable (reshuffled into a new deck at the first depletion), NOT boxed.
    manhattanRecyclePile?: PowerPlant[];
    // Which deck-depletion stage Manhattan's market is in: 0 = before the first
    // depletion (peel two to the recycle pile each round), 1 = between the first
    // and second depletions (rotate one to the deck bottom each round), 2 = after
    // the second depletion (whole market buyable, box the smallest each round).
    manhattanDepletion?: number;
    // Names of building spaces blocked at setup (Manhattan player-count scaling).
    // Blocked spaces stay in the connection graph — they are transitable (flat-5
    // per space) but can never hold a house. Chosen by GameMap.blockSpaces.
    blockedCities?: string[];
}

// Australia: the uranium power plants are replaced by "uranium mines". They are
// bought in the normal auctions but do not power cities and do not count toward
// the 3-power-plant hand limit (they DO still count for player order). On
// Australia every remaining uranium-type plant is a mine (plant 17 is removed at
// deck setup), so the type check alone identifies them.
export function isUraniumMine(G: GameState, plant: PowerPlant): boolean {
    return G.map.name === 'Australia' && plant.type === PowerPlantType.Uranium;
}

// Number of a player's plants that count toward the 3-plant hand limit — i.e.
// excluding Australia's uranium mines. On every other map this equals
// powerPlants.length.
export function countHeldPowerPlants(G: GameState, player: Player): number {
    return player.powerPlants.filter((pp) => !isUraniumMine(G, pp)).length;
}

// Australia uranium "mine" market. Six price columns ($2–$7), two slots each.
// The board starts full ([2,2,2,2,2,2]); selling PLACES tokens on the highest
// empty slots, the resource refill REMOVES them from the cheapest filled slots.
export const URANIUM_MINE_PRICES = [2, 3, 4, 5, 6, 7];

// Index of the highest-priced column that still has an empty slot, or -1 if the
// market is completely full.
function highestEmptyUraniumSlot(market: number[]): number {
    for (let i = market.length - 1; i >= 0; i--) {
        if (market[i] < 2) {
            return i;
        }
    }
    return -1;
}

// Sell one player's uranium-mine output during Bureaucracy. The player earns the
// highest available (empty-slot) price times the total cities their mines could
// power — using each mine card's PRINTED power number, not the player's actual
// built network — then places one token per mine on the highest empty slots
// (top-down). Returns income/price/mine-count/cities for logging. No-op (income 0)
// when the player holds no mines or the market is already full. The
// `uraniumMineMarket` guard restricts this to Australia — undefined on other maps.
export function sellUraniumMine(
    G: GameState,
    player: Player
): { income: number; price: number; mines: number; cities: number } {
    if (!G.uraniumMineMarket) {
        return { income: 0, price: 0, mines: 0, cities: 0 };
    }
    const mines = player.powerPlants.filter((pp) => isUraniumMine(G, pp));
    if (mines.length === 0) {
        return { income: 0, price: 0, mines: 0, cities: 0 };
    }
    const totalCities = mines.reduce((sum, mine) => sum + mine.citiesPowered, 0);
    const slot = highestEmptyUraniumSlot(G.uraniumMineMarket);
    if (slot < 0) {
        // Market full — no empty slot to sell into this round.
        return { income: 0, price: 0, mines: mines.length, cities: totalCities };
    }
    const price = URANIUM_MINE_PRICES[slot];
    const income = price * totalCities;
    player.money += income;
    if (G.options.trackTotalSpent) {
        player.totalIncome += income;
    }
    // Place one token per mine on the highest empty slots, filling top-down.
    for (let placed = 0; placed < mines.length; placed++) {
        const target = highestEmptyUraniumSlot(G.uraniumMineMarket);
        if (target < 0) {
            break;
        }
        G.uraniumMineMarket[target]++;
    }
    return { income, price, mines: mines.length, cities: totalCities };
}

// The resource refill REMOVES `count` uranium tokens from the cheapest filled
// slots first. Returns the number actually removed (capped by tokens present).
export function resupplyUraniumMine(G: GameState, count: number): number {
    if (!G.uraniumMineMarket) {
        return 0;
    }
    let removed = 0;
    for (let k = 0; k < count; k++) {
        let idx = -1;
        for (let i = 0; i < G.uraniumMineMarket.length; i++) {
            if (G.uraniumMineMarket[i] > 0) {
                idx = i;
                break;
            }
        }
        if (idx < 0) {
            break;
        }
        G.uraniumMineMarket[idx]--;
        removed++;
    }
    return removed;
}
