import assert from 'assert';
import { cloneDeep, isEqual, range } from 'lodash';
import seedrandom from 'seedrandom';
import { availableMoves, computeRegionGraph, regionPickable } from './available-moves';
import {
    countHeldPowerPlants,
    GameOptions,
    GameState,
    isUraniumMine,
    Phase,
    Player,
    playerColors,
    PowerPlant,
    PowerPlantType,
    ResourceType,
    resupplyUraniumMine,
    sellUraniumMine,
} from './gamestate';
import { LogMove } from './log';
import { GameMap, maps, mapsRecharged } from './maps';
import { Move, MoveName, Moves } from './move';
import { indiaPowerPlants, powerPlants } from './powerPlants';
import prices from './prices';
import { createRandomizedMap } from './randomizeMap';
import { asserts, shuffle } from './utils';

// Re-exported from gamestate (single source of truth) so existing importers that
// reference engine.playerColors (e.g. the wrapper's factions()) keep working.
export { playerColors };

const citiesToStep2 = [10, 7, 7, 7, 6];
const citiesToStep2BadenWurttemberg = [9, 6, 6, 6, 5];
const citiesToStep2UKIreland = [10, 7, 7, 7, 6];
const citiesToEndGame = [21, 17, 17, 15, 14];
const citiesToEndGameSouthAfrica = [18, 17, 17, 15, 14];
const citiesToStep2Bremen = [5, 5, 5, 5, 4];
const citiesToEndGameBremen = [13, 13, 13, 12, 11];
const citiesToEndGameManhattan = [18, 17, 17, 15, 14];
const cityIncome = [10, 22, 33, 44, 54, 64, 73, 82, 90, 98, 105, 112, 118, 124, 129, 134, 138, 142, 145, 148, 150, 150];
const regionsInPlay = [3, 3, 4, 5, 5];

export function defaultSetupDeck(
    numPlayers: number,
    variant: string,
    rng: seedrandom.prng,
    useNewRechargedSetup: boolean
) {
    let actualMarket: PowerPlant[];
    let futureMarket: PowerPlant[];
    let powerPlantsDeck: PowerPlant[] = cloneDeep(powerPlants);

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
        if (numPlayers == 2) {
            // Recharged 2P removes 1 plug + 5 socket (6 total). The original edition
            // removes 8 — see the variant == 'original' branch above. Confirmed with Mike.
            initialPowerPlants = initialPowerPlants.slice(1);
            powerPlantsDeck = shuffle(powerPlantsDeck.slice(5).concat(initialPowerPlants), rng() + '');
        } else if (numPlayers == 3) {
            initialPowerPlants = initialPowerPlants.slice(2);
            powerPlantsDeck = shuffle(powerPlantsDeck.slice(6).concat(initialPowerPlants), rng() + '');
        } else if (numPlayers == 4) {
            initialPowerPlants = initialPowerPlants.slice(1);
            powerPlantsDeck = shuffle(powerPlantsDeck.slice(3).concat(initialPowerPlants), rng() + '');
        } else if (useNewRechargedSetup) {
            // TODO: This flag exists solely to make old tests pass. We should eventually
            // fix the test and remove the flag.
            powerPlantsDeck = shuffle(powerPlantsDeck.concat(initialPowerPlants), rng() + '');
        }

        powerPlantsDeck.unshift(first);
        powerPlantsDeck.push(step3);
    }

    return { actualMarket, futureMarket, powerPlantsDeck };
}

export function setup(
    numPlayers: number,
    {
        fastBid = false,
        map = 'USA',
        variant = 'original',
        showMoney = false,
        useNewRechargedSetup = true,
        trackTotalSpent = true,
        randomizeMap = false,
        chooseRegions = false,
        chooseColors = false,
    }: GameOptions,
    seed?: string,
    forceDeck?: PowerPlant[],
    forceMap?: GameMap
): GameState {
    seed = seed ?? Math.random().toString();
    const rng = seedrandom(seed);

    const chosenMapRaw =
        variant == 'original' ? maps.find((m) => m.name == map) : mapsRecharged.find((m) => m.name == map);
    if (!chosenMapRaw) {
        throw new Error(`Map "${map}" not found for variant "${variant}"`);
    }
    const chosenMap = cloneDeep(chosenMapRaw);

    let actualMarket: PowerPlant[];
    let futureMarket: PowerPlant[];
    let powerPlantsDeck: PowerPlant[];

    if (forceDeck) {
        powerPlantsDeck = forceDeck;
        actualMarket = powerPlantsDeck.splice(0, 4);
        futureMarket = powerPlantsDeck.splice(0, 4);
    } else {
        if (chosenMap.setupDeck) {
            ({ actualMarket, futureMarket, powerPlantsDeck } = chosenMap.setupDeck(numPlayers, variant, rng));
        } else {
            ({ actualMarket, futureMarket, powerPlantsDeck } = defaultSetupDeck(
                numPlayers,
                variant,
                rng,
                useNewRechargedSetup
            ));
        }
    }

    const players: Player[] = range(numPlayers).map((id) => ({
        id,
        powerPlants: [],
        coalCapacity: 0,
        coalLeft: 0,
        oilCapacity: 0,
        oilLeft: 0,
        garbageCapacity: 0,
        garbageLeft: 0,
        uraniumCapacity: 0,
        uraniumLeft: 0,
        hybridCapacity: 0,
        hybridLeft: 0,
        money: 50,
        housesLeft: 22,
        cities: [],
        powerPlantsNotUsed: [],
        availableMoves: null,
        lastMove: null,
        isDropped: false,
        isAI: false,
        bid: 0,
        passed: false,
        skipAuction: false,
        citiesPowered: 0,
        resourcesUsed: [],
        totalIncome: 0,
        totalSpentCities: 0,
        totalSpentConnections: 0,
        totalSpentPlants: 0,
        totalSpentResources: 0,
        usedFreeJump: false,
    }));

    const p = players.length - 2;

    const playerOrder = range(numPlayers);
    const startingPlayer = playerOrder[0];

    let coalResupply: number[][];
    let oilResupply: number[][];
    let garbageResupply: number[][];
    let uraniumResupply: number[][];
    // Korea: parallel North-side resupply tables (no uranium row).
    let coalResupplyNorth: number[][] | undefined;
    let oilResupplyNorth: number[][] | undefined;
    let garbageResupplyNorth: number[][] | undefined;
    if (chosenMap.resupplyNorth) {
        coalResupplyNorth = chosenMap.resupplyNorth[0];
        oilResupplyNorth = chosenMap.resupplyNorth[1];
        garbageResupplyNorth = chosenMap.resupplyNorth[2];
    }
    if (chosenMap.resupply) {
        coalResupply = chosenMap.resupply[0];
        oilResupply = chosenMap.resupply[1];
        garbageResupply = chosenMap.resupply[2];
        uraniumResupply = chosenMap.resupply[3];
    } else {
        coalResupply = [
            [3, 4, 3],
            [4, 5, 3],
            [5, 6, 4],
            [5, 7, 5],
            [7, 9, 6],
        ];
        oilResupply = [
            [2, 2, 4],
            [2, 3, 4],
            [3, 4, 5],
            [4, 5, 6],
            [5, 6, 7],
        ];
        garbageResupply = [
            [1, 2, 3],
            [1, 2, 3],
            [2, 3, 4],
            [3, 3, 5],
            [3, 5, 6],
        ];
        uraniumResupply = [
            [1, 1, 1],
            [1, 1, 1],
            [1, 2, 2],
            [2, 3, 2],
            [2, 3, 3],
        ];
    }

    if (chosenMap.layout == 'Portrait' || randomizeMap) {
        const isUsaRecharged = chosenMap.name === 'USA' && variant === 'recharged';
        chosenMap.viewBox = chosenMap.viewBox || [1480, 1060];
        chosenMap.adjustRatio = chosenMap.adjustRatio || [1, 1];
        chosenMap.playerOrderPosition = chosenMap.playerOrderPosition || [1160, 160];
        chosenMap.cityCountPosition = chosenMap.cityCountPosition || [0, 0];
        chosenMap.powerPlantMarketPosition = chosenMap.powerPlantMarketPosition || [745, 0];
        chosenMap.actualMarketWidth = chosenMap.actualMarketWidth || 430;
        chosenMap.mapPosition = chosenMap.mapPosition || [0, 0];
        chosenMap.buttonsPosition = chosenMap.buttonsPosition || [1305, 0];
        chosenMap.playerBoardsPosition = chosenMap.playerBoardsPosition || [1105, 240];
        chosenMap.roundInfoPosition = chosenMap.roundInfoPosition || [20, 920];
        chosenMap.supplyPosition = chosenMap.supplyPosition || [isUsaRecharged ? 480 : 675, 920];
    } else {
        chosenMap.viewBox = chosenMap.viewBox || [1465, 860];
        chosenMap.adjustRatio = chosenMap.adjustRatio || [1, 1];
        chosenMap.playerOrderPosition = chosenMap.playerOrderPosition || [1160, 140];
        chosenMap.cityCountPosition = chosenMap.cityCountPosition || [0, 0];
        chosenMap.powerPlantMarketPosition = chosenMap.powerPlantMarketPosition || [745, 0];
        chosenMap.actualMarketWidth = chosenMap.actualMarketWidth || 430;
        chosenMap.mapPosition = chosenMap.mapPosition || [-10, 0];
        chosenMap.buttonsPosition = chosenMap.buttonsPosition || [1305, 0];
        chosenMap.playerBoardsPosition = chosenMap.playerBoardsPosition || [1105, 200];
        chosenMap.roundInfoPosition = chosenMap.roundInfoPosition || [20, 590];
        chosenMap.supplyPosition = chosenMap.supplyPosition || [0, 720];
    }

    let finalMap: GameMap;
    // Set when the chooseRegions option defers region selection to a player draft;
    // consumed after the GameState is built to enter the RegionSelection phase.
    let pendingRegionDraft: { regionsNeeded: number; picked: string[] } | undefined;
    if (randomizeMap) {
        finalMap = createRandomizedMap(chosenMap, regionsInPlay[p], rng);
    } else {
        chosenMap.cities = chosenMap.cities.map((city) => ({
            ...city,
            x: city.x * chosenMap.adjustRatio![0],
            y: city.y * chosenMap.adjustRatio![1],
        }));

        // Region adjacency graph (shared with the chooseRegions draft via
        // available-moves) — single source of truth for what "connected" means.
        const graph = computeRegionGraph(chosenMap);
        const regions = graph.regions;
        const regionsNeeded = Math.min(regionsInPlay[p], regions.length);

        if (chooseRegions && regions.length > regionsNeeded) {
            // Defer region selection to a player draft (the RegionSelection phase).
            // Keep the full map in play for now; finalizeRegions() filters it to the
            // chosen regions once the draft completes, and applies the
            // regionalPowerPlants swap at that point.
            finalMap = chosenMap;
            pendingRegionDraft = { regionsNeeded, picked: [] };
        } else {
            const playRegions = new Set<string>();
            while (playRegions.size != regionsNeeded) {
                const region = regions[Math.floor(rng() * regions.length)];

                // regionPickable enforces connectivity with the UK & Ireland
                // (fresh-landmass) and Australia (any-region) exceptions. A region
                // that is already picked or that would be stranded is rejected, and
                // the loop draws again — see regionPickable for the soft-lock
                // reasoning behind the connectivity requirement.
                if (regionPickable(chosenMap.name, graph, [...playRegions], region)) {
                    playRegions.add(region);

                    // Avoid italy Red Green Blue
                    if (chosenMap.name === 'Italy') {
                        if (playRegions.has('red') && playRegions.has('green') && playRegions.has('blue')) {
                            playRegions.clear();
                        }
                    }
                }
            }

            finalMap = filterMapToRegions(chosenMap, playRegions);
            applyRegionalPowerPlants(chosenMap, playRegions, actualMarket, futureMarket, powerPlantsDeck);
        }
    }

    const coalMarket = chosenMap.startingResources ? chosenMap.startingResources[0] : 24;
    const oilMarket = chosenMap.startingResources ? chosenMap.startingResources[1] : 18;
    const garbageMarket = chosenMap.startingResources ? chosenMap.startingResources[2] : variant == 'original' ? 6 : 9;
    const uraniumMarket = chosenMap.startingResources ? chosenMap.startingResources[3] : 2;

    const totalCoal = chosenMap.startingSupply ? chosenMap.startingSupply[0] : 24;
    const totalOil = chosenMap.startingSupply ? chosenMap.startingSupply[1] : 24;
    const totalGarbage = chosenMap.startingSupply ? chosenMap.startingSupply[2] : 24;
    const totalUranium = chosenMap.startingSupply ? chosenMap.startingSupply[3] : 12;

    // Korea: parallel North-side market and prices. Supply is shared — see below.
    const coalMarketNorth = chosenMap.startingResourcesNorth?.[0];
    const oilMarketNorth = chosenMap.startingResourcesNorth?.[1];
    const garbageMarketNorth = chosenMap.startingResourcesNorth?.[2];

    // Supply pools are shared between both sides for Korea. `startingSupply`
    // represents the TOTAL cubes in the game; the supply pool is whatever is
    // left after both markets are filled.
    const coalSupply = totalCoal - coalMarket - (coalMarketNorth ?? 0);
    const oilSupply = totalOil - oilMarket - (oilMarketNorth ?? 0);
    const garbageSupply = totalGarbage - garbageMarket - (garbageMarketNorth ?? 0);
    const uraniumSupply = totalUranium - uraniumMarket;

    const coalPrices = cloneDeep(chosenMap.coalPrices ?? prices.coal);
    const oilPrices = cloneDeep(chosenMap.oilPrices ?? prices.oil);
    const garbagePrices = cloneDeep(chosenMap.garbagePrices ?? prices.garbage);
    const uraniumPrices = cloneDeep(chosenMap.uraniumPrices ?? prices.uranium);

    const coalPricesNorth = chosenMap.coalPricesNorth ? cloneDeep(chosenMap.coalPricesNorth) : undefined;
    const oilPricesNorth = chosenMap.oilPricesNorth ? cloneDeep(chosenMap.oilPricesNorth) : undefined;
    const garbagePricesNorth = chosenMap.garbagePricesNorth ? cloneDeep(chosenMap.garbagePricesNorth) : undefined;

    const isSouthAfrica = (forceMap || finalMap).name == 'South Africa';

    const G: GameState = {
        map: forceMap || finalMap,
        players,
        playerOrder,
        currentPlayers: [startingPlayer],
        powerPlantsDeck,
        coalSupply,
        oilSupply,
        garbageSupply,
        uraniumSupply,
        // South Africa: separate coal pool below the market. Starts empty;
        // used coal returns here; refill draws from here first.
        coalStorage: isSouthAfrica ? 0 : undefined,
        coalResupply,
        oilResupply,
        garbageResupply,
        uraniumResupply,
        coalMarket,
        oilMarket,
        garbageMarket,
        uraniumMarket,
        // Australia: the separate uranium-mine market starts full (6 prices $2–$7,
        // two tokens each). Undefined on every other map.
        uraniumMineMarket: (forceMap || finalMap).name == 'Australia' ? [2, 2, 2, 2, 2, 2] : undefined,
        coalPrices,
        oilPrices,
        garbagePrices,
        uraniumPrices,
        // Korea: parallel North-side fields. Undefined for non-Korea maps.
        // Supply is shared with the primary `*Supply` fields above.
        coalMarketNorth,
        oilMarketNorth,
        garbageMarketNorth,
        coalResupplyNorth,
        oilResupplyNorth,
        garbageResupplyNorth,
        coalPricesNorth,
        oilPricesNorth,
        garbagePricesNorth,
        actualMarket,
        futureMarket,
        chosenPowerPlant: undefined,
        currentBid: undefined,
        highestBidders: [],
        auctioningPlayer: undefined,
        step: 1,
        phase: Phase.Auction,
        options: {
            fastBid,
            map,
            variant,
            showMoney,
            useNewRechargedSetup,
            trackTotalSpent,
            chooseRegions,
            chooseColors,
        },
        log: [],
        hiddenLog: [],
        seed,
        round: 1,
        auctionSkips: 0,
        citiesToStep2:
            (forceMap || finalMap).name == 'Baden-Württemberg'
                ? citiesToStep2BadenWurttemberg[numPlayers - 2]
                : (forceMap || finalMap).name == 'UK & Ireland'
                ? citiesToStep2UKIreland[numPlayers - 2]
                : (forceMap || finalMap).name == 'Bremen'
                ? citiesToStep2Bremen[numPlayers - 2]
                : citiesToStep2[numPlayers - 2],
        citiesToEndGame:
            (forceMap || finalMap).name == 'South Africa'
                ? citiesToEndGameSouthAfrica[numPlayers - 2]
                : (forceMap || finalMap).name == 'UK & Ireland' && numPlayers == 2
                ? Math.min(citiesToEndGame[numPlayers - 2], (forceMap || finalMap).cities.length)
                : (forceMap || finalMap).name == 'Bremen'
                ? citiesToEndGameBremen[numPlayers - 2]
                : (forceMap || finalMap).name == 'Manhattan'
                ? citiesToEndGameManhattan[numPlayers - 2]
                : citiesToEndGame[numPlayers - 2],
        resourceResupply: [
            `[${coalResupply[p][0]}, ${oilResupply[p][0]}, ${garbageResupply[p][0]}, ${uraniumResupply[p][0]}]`,
            `[${coalResupply[p][1]}, ${oilResupply[p][1]}, ${garbageResupply[p][1]}, ${uraniumResupply[p][1]}]`,
            `[${coalResupply[p][2]}, ${oilResupply[p][2]}, ${garbageResupply[p][2]}, ${uraniumResupply[p][2]}]`,
        ],
        resourceResupplyNorth:
            coalResupplyNorth && oilResupplyNorth && garbageResupplyNorth
                ? [
                      `[${coalResupplyNorth[p][0]}, ${oilResupplyNorth[p][0]}, ${garbageResupplyNorth[p][0]}]`,
                      `[${coalResupplyNorth[p][1]}, ${oilResupplyNorth[p][1]}, ${garbageResupplyNorth[p][1]}]`,
                      `[${coalResupplyNorth[p][2]}, ${oilResupplyNorth[p][2]}, ${garbageResupplyNorth[p][2]}]`,
                  ]
                : undefined,
        paymentTable: cityIncome,
        variant,
        minimunBid: 0,
        plantDiscountActive:
            variant == 'recharged' &&
            (forceMap || finalMap).name != 'China' &&
            (forceMap || finalMap).name != 'Russia' &&
            (forceMap || finalMap).name != 'Baden-Württemberg',
        discardSmallestPlant: false,
        cardsLeft: powerPlantsDeck.length,
        nextCardWeak: variant == 'recharged',
        card39Bought: false,
        knownPowerPlantDeck: actualMarket.concat(futureMarket),
        knownPowerPlantDeckStep3: [],
        powerPlantDeckAfterStep3: undefined,
    } as GameState;

    G.log.push({ type: 'event', event: 'Game Start!' });

    if (G.map.name == 'Middle East') {
        removePlantsForMiddleEastStep1(G);
    }

    // chooseRegions: start in the region draft instead of the auction. The map
    // currently holds every region; finalizeRegions() filters it once the players
    // finish picking.
    if (pendingRegionDraft) {
        G.phase = Phase.RegionSelection;
        G.regionDraft = pendingRegionDraft;
    }

    // chooseColors: players draft their colors first of all. The region draft (if
    // any) stays pending in G.regionDraft and only activates once colors are done
    // (see finalizeColors). The phase set here wins over RegionSelection above.
    if (chooseColors) {
        G.phase = Phase.ColorSelection;
        G.colorDraft = { picked: [] };
    }

    if (G.map.blockSpaces) {
        G.blockedCities = G.map.blockSpaces(numPlayers, G.map.cities, rng);
        if (G.blockedCities.length > 0) {
            G.log.push({
                type: 'event',
                event: `${G.blockedCities.length} building spaces are blocked for ${numPlayers} players.`,
            });
        }
    }

    G.players[startingPlayer].availableMoves = availableMoves(G, G.players[startingPlayer]);

    return G;
}

// Filters a (full) map down to just the chosen regions: keeps only cities in
// those regions and connections whose endpoints are both kept. Returns a new map;
// the input is not mutated.
function filterMapToRegions(map: GameMap, playRegions: Set<string>): GameMap {
    const filteredMap = cloneDeep(map);
    filteredMap.cities = filteredMap.cities.filter((city) => playRegions.has(city.region));
    filteredMap.connections = filteredMap.connections.filter((con) =>
        con.nodes.map((n) => map.cities.find((city) => city.name == n)!.region).every((r) => playRegions.has(r))
    );
    return filteredMap;
}

// Applies the map's regionalPowerPlants overrides for the chosen regions, swapping
// the replacement plants into whichever of the three decks currently hold the
// matching plant numbers. Mutates the passed arrays in place.
function applyRegionalPowerPlants(
    map: GameMap,
    playRegions: Set<string>,
    actualMarket: PowerPlant[],
    futureMarket: PowerPlant[],
    powerPlantsDeck: PowerPlant[]
) {
    if (!map.regionalPowerPlants) {
        return;
    }
    for (const region of playRegions) {
        const replacements = map.regionalPowerPlants[region];
        if (replacements) {
            for (const newPlant of replacements) {
                const swapIn = (arr: PowerPlant[]) => {
                    const idx = arr.findIndex((p) => p.number === newPlant.number);
                    if (idx !== -1) arr[idx] = { ...newPlant };
                };
                swapIn(actualMarket);
                swapIn(futureMarket);
                swapIn(powerPlantsDeck);
            }
        }
    }
}

// Completes the chooseRegions draft: filters the map to the picked regions, applies
// the deferred regionalPowerPlants swap, fixes region-dependent end-game targets,
// and hands off to the auction with the starting player to move.
function finalizeRegions(G: GameState) {
    const playRegions = new Set(G.regionDraft!.picked);
    const fullMap = G.map;

    G.map = filterMapToRegions(fullMap, playRegions);
    applyRegionalPowerPlants(fullMap, playRegions, G.actualMarket, G.futureMarket, G.powerPlantsDeck);
    // knownPowerPlantDeck mirrors actualMarket+futureMarket and must reflect any swap.
    G.knownPowerPlantDeck = G.actualMarket.concat(G.futureMarket);

    // UK & Ireland 2p caps the end-game target at the number of cities actually in
    // play, which is only known once the regions are chosen.
    if (G.map.name == 'UK & Ireland' && G.players.length == 2) {
        G.citiesToEndGame = Math.min(citiesToEndGame[G.players.length - 2], G.map.cities.length);
    }

    G.regionDraft = undefined;
    G.phase = Phase.Auction;
    G.currentPlayers = [G.playerOrder[0]];
}

// Completes the chooseColors draft once every player has a color. Hands off to the
// region draft if one is still pending (chooseColors + chooseRegions), otherwise
// straight to the auction with the starting player to move.
function finalizeColors(G: GameState) {
    G.colorDraft = undefined;
    G.currentPlayers = [G.playerOrder[0]];
    if (G.regionDraft) {
        G.phase = Phase.RegionSelection;
    } else {
        G.phase = Phase.Auction;
    }
}

export function stripSecret(G: GameState, player?: number): GameState {
    return {
        ...G,
        seed: 'secret',
        hiddenLog: [],
        powerPlantsDeck: [],
        players: G.players.map((pl, i) => {
            if (player === i) {
                return pl;
            } else {
                return {
                    ...pl,
                    availableMoves: pl.availableMoves ? {} : null,
                    money: ended(G) || G.options.showMoney ? pl.money : -1,
                    bid: G.options.fastBid ? 0 : pl.bid,
                };
            }
        }),
        log: G.log,
    };
}

export function currentPlayers(G: GameState): number[] {
    return G.currentPlayers;
}

export function move(G: GameState, move: Move, playerNumber: number, isUndo = false): GameState {
    const player = G.players[playerNumber];
    const available = player.availableMoves?.[move.name];

    updateGameState(G);

    assert(G.currentPlayers.includes(playerNumber), 'It is not your turn!');
    assert(available, 'You are not allowed to run the command ' + move.name);

    // Fix for issue 8: can't undo because of a move (discaring the pp you just bought) that is now invalid
    if (
        !isUndo ||
        move.name != MoveName.DiscardPowerPlant ||
        player.powerPlants[player.powerPlants.length - 1].number != move.data
    ) {
        assert(
            available.some((x) => isEqual(x, move.data)),
            'Wrong argument for the command ' + move.name
        );
    }

    switch (move.name) {
        case MoveName.ChoosePowerPlant: {
            asserts<Moves.MoveChoosePowerPlant>(move);

            // Pull from actualMarket so regionalPowerPlants overrides survive
            // selection — canonical getPowerPlant() lookup would lose them.
            G.chosenPowerPlant = G.actualMarket.find((p) => p.number === move.data)!;
            G.auctioningPlayer = player.id;

            if (move.data == 39) {
                G.card39Bought = true;
            }

            if (
                G.options.variant == 'recharged' &&
                G.plantDiscountActive &&
                G.chosenPowerPlant.number == G.actualMarket[0].number
            ) {
                G.minimunBid = 1;
                G.plantDiscountActive = false;
                move.usedPlantDiscount = true;
            } else {
                G.minimunBid = move.data;
            }

            const notPassed = G.players.filter((p) => !p.skipAuction && !p.isDropped);
            if (notPassed.length == 1) {
                G.log.push({
                    type: 'move',
                    player: playerNumber,
                    move,
                    simple: `${player.name} chooses Power Plant ${move.data}.`,
                    pretty: `${playerNameHTML(player)} chooses Power Plant <b>${move.data}</b>.`,
                });

                const winningPlayer = notPassed[0];
                endAuction(G, winningPlayer, G.minimunBid);

                if (G.discountBonusPlayer != undefined) {
                    // Manhattan: the buyer of the discounted plant gets another
                    // purchase. They are still the only eligible bidder, so re-prompt
                    // them (they may also Pass to decline). Refill the market for the
                    // plant they just took — UNLESS that purchase put them over the
                    // plant limit: then they must discard first and the discard handler
                    // does the refill, so refilling here too would draw a second plant
                    // for one purchase and grow the market past 8.
                    const overPlantLimit =
                        countHeldPowerPlants(G, winningPlayer) > 4 ||
                        (G.players.length > 2 && countHeldPowerPlants(G, winningPlayer) > 3);
                    if (!overPlantLimit) {
                        addPowerPlant(G);
                    }
                    setCurrentPlayer(G, G.discountBonusPlayer);
                } else if (
                    countHeldPowerPlants(G, winningPlayer) <= 3 ||
                    (G.players.length == 2 && countHeldPowerPlants(G, winningPlayer) == 4)
                ) {
                    if (G.map.name != 'China' || G.step == 3) {
                        addPowerPlant(G);
                    }

                    toResourcesPhase(G);
                }
            } else {
                G.log.push({
                    type: 'move',
                    player: playerNumber,
                    move,
                    simple: `${player.name} chooses Power Plant ${move.data} to initiate an auction.`,
                    pretty: `${playerNameHTML(player)} chooses Power Plant <b>${move.data}</b> to initiate an auction.`,
                });

                if (G.options.fastBid) {
                    G.currentPlayers = G.playerOrder.filter(
                        (p) => !G.players[p].skipAuction && !G.players[p].isDropped
                    );
                }
            }

            break;
        }

        case MoveName.Bid: {
            asserts<Moves.MoveBid>(move);

            if (G.options.fastBid) {
                G.hiddenLog.push({
                    type: 'move',
                    player: playerNumber,
                    move,
                    simple: `${player.name} bids $${move.data}.`,
                    pretty: `${playerNameHTML(player)} bids <span style="color: green">$${move.data}</span>.`,
                });

                fastAuction(G, player, move.data);
            } else {
                G.currentBid = player.bid = move.data;

                G.log.push({
                    type: 'move',
                    player: playerNumber,
                    move,
                    simple: `${player.name} bids $${move.data}.`,
                    pretty: `${playerNameHTML(player)} bids <span style="color: green">$${move.data}</span>.`,
                });

                nextPlayerClockwise(G);
            }

            break;
        }

        case MoveName.ChooseRegion: {
            asserts<Moves.MoveChooseRegion>(move);

            G.regionDraft!.picked.push(move.data);

            G.log.push({
                type: 'move',
                player: playerNumber,
                move,
                simple: `${player.name} chooses region ${move.data}.`,
                pretty: `${playerNameHTML(player)} chooses region <b>${move.data}</b>.`,
            });

            if (G.regionDraft!.picked.length >= G.regionDraft!.regionsNeeded) {
                finalizeRegions(G);
            } else {
                // Next picker, in seating order, wrapping around.
                const order = G.playerOrder;
                G.currentPlayers = [order[(order.indexOf(playerNumber) + 1) % order.length]];
            }

            break;
        }

        case MoveName.ChooseColor: {
            asserts<Moves.MoveChooseColor>(move);

            player.color = move.data;
            G.colorDraft!.picked.push(move.data);

            G.log.push({
                type: 'move',
                player: playerNumber,
                move,
                simple: `${player.name} chooses ${move.data}.`,
                pretty: `${playerNameHTML(player)} chooses <b>${move.data}</b>.`,
            });

            if (G.colorDraft!.picked.length >= G.players.length) {
                finalizeColors(G);
            } else {
                // Next picker, in seating order (each player picks exactly once).
                G.currentPlayers = [G.playerOrder[G.colorDraft!.picked.length]];
            }

            break;
        }

        case MoveName.Pass: {
            asserts<Moves.MovePass>(move);

            if (!G.options.fastBid || G.phase != Phase.Auction || !G.chosenPowerPlant) {
                G.log.push({
                    type: 'move',
                    player: playerNumber,
                    move,
                    simple: `${player.name} passes.`,
                    pretty: `${playerNameHTML(player)} passes.`,
                });
            }

            switch (G.phase) {
                case Phase.Auction: {
                    if (G.chosenPowerPlant == undefined) {
                        player.skipAuction = true;

                        // Manhattan: passing here declines the discount bonus purchase.
                        if (G.discountBonusPlayer == player.id) {
                            G.discountBonusPlayer = undefined;
                        }

                        G.auctionSkips++;
                        if (G.auctionSkips == 1 && G.map.name == 'Russia' && G.actualMarket?.length > 0) {
                            G.log.push({
                                type: 'event',
                                event: `First pass, removing lowest numbered Power Plant (${G.actualMarket[0].number}).`,
                            });

                            G.actualMarket.shift();
                            addPowerPlant(G);
                        }

                        if (G.players.some((p) => !p.skipAuction && !p.isDropped)) {
                            nextPlayerAuction(G);
                        } else {
                            if (G.auctionSkips == G.players.length && G.map.name == 'Baden-Württemberg') {
                                // Baden-Württemberg: remove the two lowest plants when no one buys.
                                // This applies regardless of variant.
                                const removed: number[] = [];
                                for (let i = 0; i < 2 && G.actualMarket.length > 0; i++) {
                                    removed.push(G.actualMarket[0].number);
                                    G.actualMarket.shift();
                                    addPowerPlant(G);
                                }
                                G.log.push({
                                    type: 'event',
                                    event: `Everyone passed, removing the two lowest numbered Power Plants (${removed.join(
                                        ', '
                                    )}).`,
                                });
                            } else if (
                                G.auctionSkips == G.players.length &&
                                G.options.variant == 'original' &&
                                G.map.name != 'China' &&
                                G.map.name != 'Russia'
                            ) {
                                G.log.push({
                                    type: 'event',
                                    event: `Everyone passed, removing lowest numbered Power Plant (${G.actualMarket[0].number}).`,
                                });

                                G.actualMarket.shift();
                                addPowerPlant(G);
                            }

                            toResourcesPhase(G);
                        }
                    } else {
                        if (G.options.fastBid) {
                            G.hiddenLog.push({
                                type: 'move',
                                player: playerNumber,
                                move,
                                simple: `${player.name} passes.`,
                                pretty: `${playerNameHTML(player)} passes.`,
                            });

                            fastAuction(G, player, 0);
                        } else {
                            player.passed = true;

                            const notPassed = G.players.filter((p) => !p.passed && !p.skipAuction && !p.isDropped);
                            if (notPassed.length == 1) {
                                const winningPlayer = notPassed[0];
                                endAuction(G, winningPlayer, winningPlayer.bid);

                                if (
                                    (countHeldPowerPlants(G, winningPlayer) > 4 ||
                                        (G.players.length > 2 && countHeldPowerPlants(G, winningPlayer) > 3)) &&
                                    !winningPlayer.isDropped
                                ) {
                                    setCurrentPlayer(G, winningPlayer.id);
                                } else {
                                    if (G.map.name != 'China' || G.step == 3) {
                                        addPowerPlant(G);
                                    }

                                    if (G.players.some((p) => !p.skipAuction && !p.isDropped)) {
                                        G.players.forEach((p) => {
                                            p.bid = 0;
                                            p.passed = p.isDropped;
                                        });

                                        nextPlayerAuction(G, true);
                                    } else {
                                        toResourcesPhase(G);
                                    }
                                }
                            } else {
                                nextPlayerClockwise(G);
                            }
                        }
                    }

                    break;
                }

                case Phase.Resources: {
                    if (G.map.name == 'India') {
                        if (G.chosenResource) {
                            G.chosenResource = undefined;
                        } else {
                            player.passed = true;
                        }
                    } else {
                        player.passed = true;
                    }

                    // Korea: end of this player's buying turn — clear the side lock
                    // so the next player can pick freely.
                    if (G.map.name == 'Korea') {
                        G.chosenSide = undefined;
                    }

                    if (G.players.filter((p) => !p.passed && !p.isDropped).length == 0) {
                        G.players.forEach((p) => {
                            p.passed = p.isDropped;
                        });
                        G.phase = Phase.Building;

                        if (G.map.name == 'India') {
                            G.citiesBuiltInCurrentRound = 0;
                        }

                        setCurrentPlayer(G, G.playerOrder[G.players.length - 1]);

                        if (G.players[G.currentPlayers[0]].isDropped && G.players.some((p) => !p.isDropped)) {
                            G.players[G.currentPlayers[0]].passed = true;
                            nextPlayerReverse(G);
                        }
                    } else {
                        nextPlayerReverse(G);
                    }

                    if (G.map.name == 'India') {
                        while (G.players[G.currentPlayers[0]].passed) {
                            nextPlayerReverse(G);
                        }
                    }

                    break;
                }

                case Phase.Building: {
                    player.passed = true;

                    if (G.players.filter((p) => !p.passed && !p.isDropped).length == 0) {
                        const maxCities = Math.max(...G.players.map((p) => p.cities.length));
                        if (G.step == 1) {
                            // Step 1 is single-occupancy, so the sum of player city
                            // counts equals the number of cities with a house. When
                            // that hits map.cities.length, every Step 1 slot is full
                            // and Step 2 needs to fire even if no player reached
                            // citiesToStep2 (can happen on small maps / small region
                            // counts where the threshold is unreachable).
                            const totalCitiesBuilt = G.players.reduce((sum, p) => sum + p.cities.length, 0);
                            const allStep1HousesFilled = totalCitiesBuilt >= G.map.cities.length;
                            if (
                                (maxCities >= G.citiesToStep2 || allStep1HousesFilled) &&
                                G.map.name != 'Middle East' &&
                                G.map.name != 'Manhattan'
                            ) {
                                const powerPlant = G.actualMarket.shift()!;
                                G.log.push({
                                    type: 'event',
                                    event: `Starting Step 2, Power Plant ${powerPlant?.number} discarded.`,
                                });
                                G.step = 2;

                                // Spain & Portugal: put plants 18, 22 and 27 on top
                                if (G.map.name == 'Spain & Portugal') {
                                    if (!G.powerPlantsDeck.find((p) => p.number == 18)) {
                                        G.powerPlantsDeck.unshift(getPowerPlant(27));
                                        G.powerPlantsDeck.unshift(getPowerPlant(22));
                                        G.powerPlantsDeck.unshift(getPowerPlant(18));
                                    }
                                }

                                if (G.map.name == 'Europe') {
                                    // Europe: do NOT draw a replacement from the deck.
                                    // The future market shrinks from 5 to 4; reorganize
                                    // the remaining 8 plants so actual stays at 4.
                                    const market = [...G.actualMarket, ...G.futureMarket];
                                    market.sort((a, b) => a.number - b.number);
                                    G.actualMarket = market.slice(0, 4);
                                    G.futureMarket = market.slice(4);
                                } else {
                                    addPowerPlant(G);
                                }
                            }
                        }

                        if (maxCities >= G.citiesToEndGame) {
                            G.phase = Phase.GameEnd;
                            G.currentPlayers = [];
                            calculateCitiesPowered(G);

                            // Include payouts in phase 5 if there is a power outage in India.
                            if (G.map.name == 'India' && G.citiesBuiltInCurrentRound! > G.players.length * 2) {
                                G.players.forEach((player) => {
                                    const payment = G.paymentTable[player.citiesPowered] - 3 * player.cities.length;
                                    player.money += Math.max(payment, 0);
                                    player.totalIncome += Math.max(payment, 0);
                                });
                            }

                            // Australia: uranium income still pays in the final round
                            // (unlike city income). Players sell in REVERSE turn order
                            // (last player first); the market is not refilled afterwards.
                            if (G.uraniumMineMarket) {
                                [...G.playerOrder].reverse().forEach((idx) => {
                                    const seller = G.players[idx];
                                    const sale = sellUraniumMine(G, seller);
                                    if (sale.mines > 0 && sale.income > 0) {
                                        const who = seller.name ?? `Player ${seller.id}`;
                                        G.log.push({
                                            type: 'event',
                                            event: `${who} sells uranium for ${sale.income} Elektro (${sale.cities} cities × $${sale.price}, ${sale.mines} mine(s)).`,
                                        });
                                    }
                                });
                            }

                            G.log.push({ type: 'event', event: 'Game Ended!' });
                        } else {
                            G.players.forEach((p) => {
                                p.passed = p.isDropped;
                                p.powerPlantsNotUsed = p.powerPlants.map((pp) => pp.number);
                            });
                            G.phase = Phase.Bureaucracy;
                            G.currentPlayers = G.playerOrder.filter(
                                (p) => !G.players[p].passed && !G.players[p].isDropped
                            );

                            if (G.map.name == 'India') {
                                // Compute the maximum number of cities each player can power.
                                G.players.forEach(
                                    (player) => (player.targetCitiesPowered = calculateMaxCitiesPowered(G, player))
                                );

                                // Output log for power outage.
                                if (G.citiesBuiltInCurrentRound! > G.players.length * 2) {
                                    G.log.push({
                                        type: 'event',
                                        event: `Power outage! ${G.citiesBuiltInCurrentRound} built this round, which is more than twice the number of players.`,
                                    });
                                }
                            }

                            if (G.map.name == 'China' && G.step <= 2) {
                                rebuildPlantMarketForChina(G);
                            } else if (G.futureMarket.length == 0 && G.map.name != 'Manhattan') {
                                // Manhattan never advances to Step 3 — its empty future
                                // market is the all-buyable endgame stage, handled by the
                                // market lifecycle, not a step change.
                                G.step = 3;
                                applyAustraliaStep3Shift(G);
                            }
                        }
                    } else {
                        nextPlayerReverse(G);
                    }

                    break;
                }

                case Phase.Bureaucracy: {
                    player.passed = true;
                    const citiesPowered: number = Math.min(player.cities.length, player.citiesPowered);
                    let payment: number = G.paymentTable[citiesPowered];

                    // For the India map, if the number of cities built in the current round is more than twice
                    // the number of players, each player is penalized three Elektro per city (power outage).
                    if (G.map.name == 'India' && G.citiesBuiltInCurrentRound! > G.players.length * 2) {
                        payment -= 3 * player.cities.length;
                        payment = Math.max(payment, 0); // No negative income
                    }

                    player.money += payment;

                    if (G.options.trackTotalSpent) {
                        player.totalIncome += payment;
                    }

                    player.citiesPowered = 0;

                    if (G.map.name == 'India') {
                        player.targetCitiesPowered = 0;
                    }

                    if (G.players.filter((p) => !p.passed && !p.isDropped).length == 0) {
                        // Australia: the uranium-mine market resolves once everyone
                        // has finished Bureaucracy. Players sell in REVERSE turn order
                        // — the player last in turn order sells first, getting first
                        // dibs on the highest empty price (the same trailing-player
                        // advantage as the resource and building phases). Then the
                        // resource refill removes tokens from the cheap end.
                        if (G.uraniumMineMarket) {
                            [...G.playerOrder].reverse().forEach((idx) => {
                                const seller = G.players[idx];
                                const sale = sellUraniumMine(G, seller);
                                if (sale.mines > 0) {
                                    const who = seller.name ?? `Player ${seller.id}`;
                                    G.log.push({
                                        type: 'event',
                                        event:
                                            sale.income > 0
                                                ? `${who} sells uranium for ${sale.income} Elektro (${sale.cities} cities × $${sale.price}, ${sale.mines} mine(s)).`
                                                : `${who}'s uranium mines earn nothing (market full).`,
                                    });
                                }
                            });
                            const removed = resupplyUraniumMine(
                                G,
                                G.map.uraniumMineResupply![G.players.length - 2][G.step - 1]
                            );
                            if (removed > 0) {
                                G.log.push({
                                    type: 'event',
                                    event: `Removing ${removed} uranium from the mine market (cheapest slots).`,
                                });
                            }
                        }

                        // Resupply is also capped by remaining market capacity (the
                        // prices array length minus current market size). Without
                        // this, smaller markets like Korea's can overflow past the
                        // number of slots and break price lookups.
                        const coalCapSouth = (G.coalPrices?.length ?? prices[ResourceType.Coal].length) - G.coalMarket;
                        const oilCapSouth = (G.oilPrices?.length ?? prices[ResourceType.Oil].length) - G.oilMarket;
                        const garbageCapSouth =
                            (G.garbagePrices?.length ?? prices[ResourceType.Garbage].length) - G.garbageMarket;
                        const uraniumCapSouth =
                            (G.uraniumPrices?.length ?? prices[ResourceType.Uranium].length) - G.uraniumMarket;

                        // Korea: North restocks FIRST from the shared supply pool, then
                        // South takes whatever remains. If supply runs short, South gets less.
                        let coalResupplyNorthValue = 0;
                        let oilResupplyNorthValue = 0;
                        let garbageResupplyNorthValue = 0;
                        if (G.coalResupplyNorth) {
                            const coalCapNorth = G.coalPricesNorth!.length - G.coalMarketNorth!;
                            const oilCapNorth = G.oilPricesNorth!.length - G.oilMarketNorth!;
                            const garbageCapNorth = G.garbagePricesNorth!.length - G.garbageMarketNorth!;

                            coalResupplyNorthValue = Math.min(
                                G.coalSupply,
                                G.coalResupplyNorth[G.players.length - 2][G.step - 1],
                                coalCapNorth
                            );
                            G.coalMarketNorth! += coalResupplyNorthValue;
                            G.coalSupply -= coalResupplyNorthValue;

                            oilResupplyNorthValue = Math.min(
                                G.oilSupply,
                                G.oilResupplyNorth![G.players.length - 2][G.step - 1],
                                oilCapNorth
                            );
                            G.oilMarketNorth! += oilResupplyNorthValue;
                            G.oilSupply -= oilResupplyNorthValue;

                            garbageResupplyNorthValue = Math.min(
                                G.garbageSupply,
                                G.garbageResupplyNorth![G.players.length - 2][G.step - 1],
                                garbageCapNorth
                            );
                            G.garbageMarketNorth! += garbageResupplyNorthValue;
                            G.garbageSupply -= garbageResupplyNorthValue;
                        }

                        // South Africa pulls from coalStorage first, then coalSupply.
                        // Other maps just pull from coalSupply.
                        let coalResupplyValue: number;
                        if (G.coalStorage !== undefined) {
                            const wantCoal = Math.min(G.coalResupply![G.players.length - 2][G.step - 1], coalCapSouth);
                            const fromStorage = Math.min(G.coalStorage, wantCoal);
                            const fromSupply = Math.min(G.coalSupply, wantCoal - fromStorage);
                            coalResupplyValue = fromStorage + fromSupply;
                            G.coalMarket += coalResupplyValue;
                            G.coalStorage -= fromStorage;
                            G.coalSupply -= fromSupply;
                        } else {
                            coalResupplyValue = Math.min(
                                G.coalSupply,
                                G.coalResupply![G.players.length - 2][G.step - 1],
                                coalCapSouth
                            );
                            G.coalMarket += coalResupplyValue;
                            G.coalSupply -= coalResupplyValue;
                        }

                        let oilResupplyValue: number;
                        if (G.map.name == 'Middle East') {
                            if (G.oilMarket == 0) {
                                G.oilPrices = prices[ResourceType.Oil];
                            }

                            oilResupplyValue = G.oilResupply![G.players.length - 2][G.step - 1];
                            for (let i = 0; i < oilResupplyValue; i++) {
                                if (G.oilSupply > 0) {
                                    G.oilMarket++;
                                    G.oilSupply--;
                                } else {
                                    // If we have more oil to stock than is in the supply, we shift the prices downward.
                                    G.oilPrices!.pop()!;
                                    G.oilPrices!.unshift(1);
                                }
                            }
                        } else {
                            oilResupplyValue = Math.min(
                                G.oilSupply,
                                G.oilResupply![G.players.length - 2][G.step - 1],
                                oilCapSouth
                            );
                            G.oilMarket += oilResupplyValue;
                            G.oilSupply -= oilResupplyValue;
                        }

                        const garbageResupplyValue = Math.min(
                            G.garbageSupply,
                            G.garbageResupply![G.players.length - 2][G.step - 1],
                            garbageCapSouth
                        );
                        G.garbageMarket += garbageResupplyValue;
                        G.garbageSupply -= garbageResupplyValue;

                        let uraniumResupplyValue = 0;
                        if (
                            G.options.variant != 'recharged' ||
                            (G.options.map != 'Germany' && G.options.map != 'Italy') ||
                            !G.card39Bought
                        ) {
                            uraniumResupplyValue = Math.min(
                                G.uraniumSupply,
                                G.uraniumResupply![G.players.length - 2][G.step - 1],
                                uraniumCapSouth
                            );
                            G.uraniumMarket += uraniumResupplyValue;
                            G.uraniumSupply -= uraniumResupplyValue;
                        }

                        if (G.coalResupplyNorth) {
                            G.log.push({
                                type: 'event',
                                event: `Resupplying resources — North: [${coalResupplyNorthValue}, ${oilResupplyNorthValue}, ${garbageResupplyNorthValue}], South: [${coalResupplyValue}, ${oilResupplyValue}, ${garbageResupplyValue}, ${uraniumResupplyValue}].`,
                            });
                        } else {
                            G.log.push({
                                type: 'event',
                                event: `Resupplying resources: [${coalResupplyValue}, ${oilResupplyValue}, ${garbageResupplyValue}, ${uraniumResupplyValue}].`,
                            });
                        }

                        if (G.map.name == 'Manhattan') {
                            // Manhattan's market is driven by deck depletions, not by a
                            // step change. Its whole bureaucracy market behaviour lives in
                            // the lifecycle helper, replacing the generic refill below.
                            applyManhattanMarketLifecycle(G);
                        } else if (G.map.name == 'Middle East' && G.step == 2 && G.futureMarket.length > 0) {
                            // If we aren't about to enter step 3, discard top two plants instead of one.
                            let powerPlantToPush: PowerPlant = G.futureMarket.pop()!;
                            G.log.push({
                                type: 'event',
                                event: `Putting Power Plant ${powerPlantToPush.number} on the bottom of the deck.`,
                            });
                            G.powerPlantsDeck.push(powerPlantToPush);
                            addPowerPlant(G);

                            // If Step 3 was drawn above, futureMarket will be empty so use actualMarket instead
                            powerPlantToPush = G.futureMarket.length ? G.futureMarket.pop()! : G.actualMarket.pop()!;
                            G.log.push({
                                type: 'event',
                                event: `Putting Power Plant ${powerPlantToPush.number} on the bottom of the deck.`,
                            });
                            G.powerPlantsDeck.push(powerPlantToPush);
                            addPowerPlant(G);
                        } else if (G.futureMarket.length > 0) {
                            if (
                                G.map.name == 'Benelux' &&
                                (G.options.variant == 'original' || G.discardSmallestPlant)
                            ) {
                                const removedPlant = G.actualMarket[0];
                                G.log.push({
                                    type: 'event',
                                    event: `Removing smallest plant, Power Plant ${removedPlant.number}.`,
                                });
                                G.actualMarket.shift();
                                addPowerPlant(G);
                                G.discardSmallestPlant = false;
                            }

                            let powerPlantToPush: PowerPlant | undefined;
                            if (G.map.name == 'Quebec') {
                                // For the Quebec map, ecological plants will never be put on the bottom of the deck.
                                const nonEcoPlants = G.futureMarket.filter((pp) => pp.type != PowerPlantType.Wind);
                                powerPlantToPush = nonEcoPlants.pop();

                                if (powerPlantToPush) {
                                    G.futureMarket = G.futureMarket.filter(
                                        (pp) => pp.number != powerPlantToPush?.number
                                    );
                                } else {
                                    const nonEcoPlants = G.actualMarket.filter((pp) => pp.type != PowerPlantType.Wind);
                                    powerPlantToPush = nonEcoPlants.pop();

                                    if (powerPlantToPush) {
                                        G.actualMarket = G.actualMarket.filter(
                                            (pp) => pp.number != powerPlantToPush?.number
                                        );
                                    }
                                }
                            } else {
                                powerPlantToPush = G.futureMarket.pop()!;
                            }

                            // This check covers the rare case in which a Quebec game might have a futures market consisting of
                            // all ecological plants. In that case, we do not draw a new plant.
                            if (powerPlantToPush) {
                                G.log.push({
                                    type: 'event',
                                    event: `Putting Power Plant ${powerPlantToPush.number} on the bottom of the deck.`,
                                });
                                G.powerPlantsDeck.push(powerPlantToPush);
                                addPowerPlant(G);
                            }
                        } else if (G.actualMarket.length > 0 && (G.map.name != 'China' || G.step == 3)) {
                            G.log.push({ type: 'event', event: `Discarding Power Plant ${G.actualMarket[0].number}.` });
                            G.actualMarket.shift();
                            addPowerPlant(G);
                        }

                        G.round++;

                        if (G.map.name != 'Baden-Württemberg') {
                            // Baden-Württemberg: player order is determined AFTER the auction phase, not before it.
                            setPlayerOrder(G);
                        }

                        G.players.forEach((p) => {
                            p.passed = p.isDropped;
                        });
                        G.auctionSkips = 0;

                        if (G.actualMarket.length > 0) {
                            G.phase = Phase.Auction;

                            if (G.futureMarket.length == 0 && G.map.name != 'China' && G.map.name != 'Manhattan') {
                                G.step = 3;
                                applyAustraliaStep3Shift(G);
                            }

                            G.plantDiscountActive =
                                G.options.variant == 'recharged' &&
                                G.map.name != 'China' &&
                                G.map.name != 'Russia' &&
                                G.map.name != 'Baden-Württemberg';
                            setCurrentPlayer(G, G.playerOrder[0]);
                        } else {
                            toResourcesPhase(G);
                        }
                    } else {
                        G.currentPlayers = G.playerOrder.filter((p) => !G.players[p].passed && !G.players[p].isDropped);
                    }

                    break;
                }
            }

            break;
        }

        case MoveName.DiscardPowerPlant: {
            asserts<Moves.MoveDiscardPowerPlant>(move);

            if (!move.extra) {
                G.log.push({
                    type: 'move',
                    player: playerNumber,
                    move,
                    simple: `${player.name} discards Power Plant ${move.data}.`,
                    pretty: `${playerNameHTML(player)} discards Power Plant <b>${move.data}</b>.`,
                });
            }

            const powerPlant = player.powerPlants.find((p) => p.number == move.data)!;
            player.powerPlants = player.powerPlants.filter((p) => p.number != move.data);

            updatePlayerCapacity(player);

            if (move.extra) {
                const discarded: string[] = [];
                switch (powerPlant.type) {
                    case PowerPlantType.Coal:
                        G.coalSupply += move.extra[0];
                        player.coalLeft -= move.extra[0];
                        discarded.push(move.extra[0] + ' Coal');
                        break;

                    case PowerPlantType.Oil:
                        G.oilSupply += move.extra[0];
                        player.oilLeft -= move.extra[0];
                        discarded.push(move.extra[0] + ' Oil');
                        break;

                    case PowerPlantType.Garbage:
                        G.garbageSupply += move.extra[0];
                        player.garbageLeft -= move.extra[0];
                        discarded.push(move.extra[0] + ' Garbage');
                        break;

                    case PowerPlantType.Uranium:
                        G.uraniumSupply += move.extra[0];
                        player.uraniumLeft -= move.extra[0];
                        discarded.push(move.extra[0] + ' Uranium');
                        break;

                    case PowerPlantType.Hybrid:
                        if (move.extra[0] > 0) {
                            G.coalSupply += move.extra[0];
                            player.coalLeft -= move.extra[0];
                            discarded.push(move.extra[0] + ' Coal');
                        }

                        if (move.extra[1] > 0) {
                            G.oilSupply += move.extra[1];
                            player.oilLeft -= move.extra[1];
                            discarded.push(move.extra[1] + ' Oil');
                        }

                        break;
                }

                G.log.push({
                    type: 'move',
                    player: playerNumber,
                    move,
                    simple: `${player.name} discards Power Plant ${move.data} and ${discarded.join(', ')}.`,
                    pretty: `${playerNameHTML(player)} discards Power Plant <b>${move.data}</b> and ${discarded.join(
                        ', '
                    )}.`,
                });

                if (G.map.name != 'China' || G.step == 3) {
                    addPowerPlant(G);
                }

                G.players.forEach((p) => {
                    p.bid = 0;
                    p.passed = p.isDropped;
                });

                if (G.players.some((p) => !p.skipAuction && !p.isDropped)) {
                    nextPlayerAuction(G, true);
                } else {
                    toResourcesPhase(G);
                }
            } else {
                const toDiscard: ResourceType[] = [];
                let hybridCapacityUsed =
                    player.hybridCapacity > 0 ? Math.max(0, player.oilLeft - player.oilCapacity) : 0;
                if (player.coalCapacity + player.hybridCapacity < player.coalLeft + hybridCapacityUsed) {
                    toDiscard.push(ResourceType.Coal);
                }

                hybridCapacityUsed = player.hybridCapacity > 0 ? Math.max(0, player.coalLeft - player.coalCapacity) : 0;
                if (player.oilCapacity + player.hybridCapacity < player.oilLeft + hybridCapacityUsed) {
                    toDiscard.push(ResourceType.Oil);
                }

                if (player.garbageLeft > player.garbageCapacity) {
                    G.garbageSupply += player.garbageLeft - player.garbageCapacity;
                    player.garbageLeft = player.garbageCapacity;
                }

                if (player.uraniumLeft > player.uraniumCapacity) {
                    G.uraniumSupply += player.uraniumLeft - player.uraniumCapacity;
                    player.uraniumLeft = player.uraniumCapacity;
                }

                if (toDiscard.length == 1) {
                    if (toDiscard[0] == ResourceType.Coal) {
                        G.coalSupply += player.coalLeft - player.coalCapacity;
                        player.coalLeft = player.coalCapacity;
                    } else if (toDiscard[0] == ResourceType.Oil) {
                        G.oilSupply += player.oilLeft - player.oilCapacity;
                        player.oilLeft = player.oilCapacity;
                    }

                    toDiscard.pop();
                }

                if (toDiscard.length == 0) {
                    if (G.map.name != 'China' || G.step == 3) {
                        addPowerPlant(G);
                    }
                    G.players.forEach((p) => {
                        p.bid = 0;
                        p.passed = p.isDropped;
                    });

                    if (G.players.some((p) => !p.skipAuction && !p.isDropped)) {
                        nextPlayerAuction(G, true);
                    } else {
                        toResourcesPhase(G);
                    }
                }
            }

            break;
        }

        case MoveName.DiscardResources: {
            asserts<Moves.MoveDiscardResources>(move);

            G.log.push({
                type: 'move',
                player: playerNumber,
                move,
                simple: `${player.name} discarded a ${move.data}.`,
                pretty: `${playerNameHTML(player)} discarded a <b>${move.data}</b>.`,
            });

            if (move.data == ResourceType.Coal) {
                player.coalLeft--;
                G.coalSupply++;
            } else if (move.data == ResourceType.Oil) {
                player.oilLeft--;
                G.oilSupply++;
            }

            const toDiscard: ResourceType[] = [];
            let hybridCapacityUsed = player.hybridCapacity > 0 ? Math.max(0, player.oilLeft - player.oilCapacity) : 0;
            if (player.coalCapacity + player.hybridCapacity < player.coalLeft + hybridCapacityUsed) {
                toDiscard.push(ResourceType.Coal);
            }

            hybridCapacityUsed = player.hybridCapacity > 0 ? Math.max(0, player.coalLeft - player.coalCapacity) : 0;
            if (player.oilCapacity + player.hybridCapacity < player.oilLeft + hybridCapacityUsed) {
                toDiscard.push(ResourceType.Oil);
            }

            if (toDiscard.length == 1) {
                if (toDiscard[0] == ResourceType.Coal) {
                    player.coalLeft--;
                } else if (toDiscard[0] == ResourceType.Oil) {
                    player.oilLeft--;
                }

                toDiscard.pop();
            }

            if (toDiscard.length == 0) {
                if (G.map.name != 'China' || G.step == 3) {
                    addPowerPlant(G);
                }
                G.players.forEach((p) => {
                    p.bid = 0;
                    p.passed = p.isDropped;
                });

                if (G.players.some((p) => !p.skipAuction && !p.isDropped)) {
                    nextPlayerAuction(G, true);
                } else {
                    toResourcesPhase(G);
                }
            }

            break;
        }

        case MoveName.BuyResource: {
            asserts<Moves.MoveBuyResource>(move);
            G.chosenResource = move.data.resource;

            // Korea: lock the player to the side of their first buy this turn.
            // Subsequent buys must come from the same side until they pass.
            if (move.data.side) {
                G.chosenSide = move.data.side;
            }

            const isNorth = move.data.side === 'north';

            let price: number;
            switch (move.data.resource) {
                case ResourceType.Coal: {
                    if (isNorth) {
                        const coalPrices = G.coalPricesNorth!;
                        price = coalPrices[coalPrices.length - G.coalMarketNorth!];
                        player.coalLeft++;
                        G.coalMarketNorth!--;
                    } else if (move.data.fromStorage) {
                        // South Africa: $8 flat from the storage pool below the market.
                        price = 8;
                        player.coalLeft++;
                        G.coalStorage!--;
                    } else if (G.coalMarket == 0) {
                        price = 8;
                        player.coalLeft++;
                        G.coalSupply--;
                        move.fromSupply = true;
                    } else {
                        const coalPrices = G.coalPrices ?? prices[ResourceType.Coal];
                        price = coalPrices[coalPrices.length - G.coalMarket];
                        player.coalLeft++;
                        G.coalMarket--;
                    }

                    break;
                }

                case ResourceType.Oil: {
                    if (isNorth) {
                        const oilPrices = G.oilPricesNorth!;
                        price = oilPrices[oilPrices.length - G.oilMarketNorth!];
                        player.oilLeft++;
                        G.oilMarketNorth!--;
                    } else {
                        const oilPrices = G.oilPrices ?? prices[ResourceType.Oil];
                        price = oilPrices[oilPrices.length - G.oilMarket];
                        player.oilLeft++;
                        G.oilMarket--;
                    }
                    break;
                }

                case ResourceType.Garbage: {
                    if (isNorth) {
                        const garbagePrices = G.garbagePricesNorth!;
                        price = garbagePrices[garbagePrices.length - G.garbageMarketNorth!];
                        player.garbageLeft++;
                        G.garbageMarketNorth!--;
                    } else {
                        const garbagePrices = G.garbagePrices ?? prices[ResourceType.Garbage];
                        price = garbagePrices[garbagePrices.length - G.garbageMarket];

                        // $1 cheaper for players in Wien in Central Europe
                        if (G.map.name == 'Central Europe') {
                            const wienCity = player.cities.filter((c) => c.name == 'Wien');
                            if (wienCity?.length > 0) {
                                price--;
                            }
                        }

                        player.garbageLeft++;
                        G.garbageMarket--;
                    }
                    break;
                }

                case ResourceType.Uranium: {
                    // Uranium is only available from the South market (or non-Korea maps).
                    const uraniumPrices = G.uraniumPrices ?? prices[ResourceType.Uranium];
                    price = uraniumPrices[uraniumPrices.length - G.uraniumMarket];
                    player.uraniumLeft++;
                    G.uraniumMarket--;
                    break;
                }
            }

            player.money -= price;

            if (G.options.trackTotalSpent) {
                player.totalSpentResources += price;
            }

            G.log.push({
                type: 'move',
                player: playerNumber,
                move,
                simple: `${player.name} buys ${move.data.resource} for $${price}.`,
                pretty: `${playerNameHTML(player)} buys <b>${
                    move.data.resource
                }</b> for <span style="color: green">$${price}</span>.`,
            });

            break;
        }

        case MoveName.Build: {
            asserts<Moves.MoveBuild>(move);

            // Japan: detect free jump.
            // Round 1: any second starting-city build uses the jump.
            // Round 2+: the player explicitly opted in via freeJump:true on the move.
            let isJapanFreeJump = false;
            if (G.map.name === 'Japan' && !player.usedFreeJump && player.cities.length >= 1) {
                if (G.round === 1 && G.map.startingCities) {
                    const startingCities = new Set(G.map.startingCities);
                    if (startingCities.has(move.data.name)) {
                        isJapanFreeJump = true;
                    }
                } else if (move.data.freeJump) {
                    isJapanFreeJump = true;
                }
            }

            const position = G.players.filter((p) => p.cities.find((c) => c.name == move.data.name)).length;
            player.cities.push({ name: move.data.name, position });
            player.money -= move.data.price;

            if (G.options.trackTotalSpent) {
                const cityData = G.map.cities.find((c) => c.name == move.data.name)!;
                if (cityData.singleOccupancy) {
                    // SA cross-border: no house base — full price is "connection".
                    player.totalSpentConnections += move.data.price;
                } else {
                    player.totalSpentCities += 10 + position * 5;
                    player.totalSpentConnections += move.data.price - (10 + position * 5);
                }
            }

            G.log.push({
                type: 'move',
                player: playerNumber,
                move,
                simple: `${player.name} builds on ${move.data.name} for $${move.data.price}.`,
                pretty: `${playerNameHTML(player)} builds on <b>${move.data.name}</b> for <span style="color: green">$${
                    move.data.price
                }</span>.`,
            });

            if (isJapanFreeJump) {
                player.usedFreeJump = true;
            }

            if (G.map.name == 'India') {
                G.citiesBuiltInCurrentRound!++;
            }

            if (G.options.variant == 'original') {
                if (
                    G.actualMarket.length > 0 &&
                    player.cities.length >= G.actualMarket[0].number &&
                    G.map.name != 'China' &&
                    G.map.name != 'Russia' &&
                    G.map.name != 'Baden-Württemberg'
                ) {
                    G.actualMarket.shift();
                    addPowerPlant(G);
                }
            }

            break;
        }

        case MoveName.UsePowerPlant: {
            asserts<Moves.MoveUsePowerPlant>(move);

            player.powerPlantsNotUsed = player.powerPlantsNotUsed.filter((x) => x != move.data.powerPlant);
            move.data.resourcesSpent.forEach((resourceType) => {
                switch (resourceType) {
                    case ResourceType.Coal:
                        player.coalLeft--;
                        // SA: used coal returns to the separate storage pool below the market.
                        if (G.coalStorage !== undefined) {
                            G.coalStorage++;
                        } else {
                            G.coalSupply++;
                        }
                        break;

                    case ResourceType.Oil:
                        player.oilLeft--;
                        G.oilSupply++;
                        break;

                    case ResourceType.Garbage:
                        player.garbageLeft--;
                        G.garbageSupply++;
                        break;

                    case ResourceType.Uranium:
                        player.uraniumLeft--;
                        G.uraniumSupply++;
                        break;
                }
            });

            player.citiesPowered += move.data.citiesPowered;

            G.log.push({
                type: 'move',
                player: playerNumber,
                move,
                simple: `${player.name} uses Power Plant ${move.data.powerPlant}.`,
                pretty: `${playerNameHTML(player)} uses Power Plant <b>${move.data.powerPlant}</b>.`,
            });

            break;
        }

        case MoveName.Undo: {
            asserts<Moves.MoveUndo>(move);

            const lastMove = player.lastMove;
            switch (lastMove?.name) {
                case MoveName.ChoosePowerPlant: {
                    if (lastMove.data == 39) {
                        G.card39Bought = false;
                    }

                    if (lastMove.usedPlantDiscount) {
                        G.plantDiscountActive = true;
                    }

                    G.chosenPowerPlant = undefined;
                    G.auctioningPlayer = undefined;

                    G.currentPlayers = [player.id];

                    G.log.pop();

                    break;
                }

                case MoveName.BuyResource: {
                    const undoIsNorth = lastMove.data.side === 'north';
                    let price: number;
                    switch (lastMove.data.resource) {
                        case ResourceType.Coal:
                            if (undoIsNorth) {
                                player.coalLeft--;
                                G.coalMarketNorth!++;
                                const coalPrices = G.coalPricesNorth!;
                                price = coalPrices[coalPrices.length - G.coalMarketNorth!];
                            } else if (lastMove.data.fromStorage) {
                                price = 8;
                                player.coalLeft--;
                                G.coalStorage!++;
                            } else if (lastMove.fromSupply) {
                                price = 8;
                                player.coalLeft--;
                                G.coalSupply++;
                            } else {
                                player.coalLeft--;
                                G.coalMarket++;
                                const coalPrices = G.coalPrices ?? prices[ResourceType.Coal];
                                price = coalPrices[coalPrices.length - G.coalMarket];
                            }

                            break;

                        case ResourceType.Oil: {
                            if (undoIsNorth) {
                                player.oilLeft--;
                                G.oilMarketNorth!++;
                                const oilPrices = G.oilPricesNorth!;
                                price = oilPrices[oilPrices.length - G.oilMarketNorth!];
                            } else {
                                player.oilLeft--;
                                G.oilMarket++;
                                const oilPrices = G.oilPrices ?? prices[ResourceType.Oil];
                                price = oilPrices[oilPrices.length - G.oilMarket];
                            }
                            break;
                        }

                        case ResourceType.Garbage: {
                            if (undoIsNorth) {
                                player.garbageLeft--;
                                G.garbageMarketNorth!++;
                                const garbagePrices = G.garbagePricesNorth!;
                                price = garbagePrices[garbagePrices.length - G.garbageMarketNorth!];
                            } else {
                                player.garbageLeft--;
                                G.garbageMarket++;
                                const garbagePrices = G.garbagePrices ?? prices[ResourceType.Garbage];
                                price = garbagePrices[garbagePrices.length - G.garbageMarket];

                                // $1 cheaper for players in Wien in Central Europe
                                if (G.map.name == 'Central Europe') {
                                    const wienCity = player.cities.filter((c) => c.name == 'Wien');
                                    if (wienCity?.length > 0) {
                                        price--;
                                    }
                                }
                            }

                            break;
                        }

                        case ResourceType.Uranium: {
                            // Uranium is only available from the South market (or non-Korea maps).
                            player.uraniumLeft--;
                            G.uraniumMarket++;
                            const uraniumPrices = G.uraniumPrices ?? prices[ResourceType.Uranium];
                            price = uraniumPrices[uraniumPrices.length - G.uraniumMarket];
                            break;
                        }
                    }

                    player.money += price;

                    if (G.options.trackTotalSpent) {
                        player.totalSpentResources -= price;
                    }

                    if (G.map.name == 'India') {
                        G.chosenResource = undefined;
                    }

                    G.log.pop();

                    // Korea: keep chosenSide locked while the player still has
                    // outstanding BuyResource moves this phase, but clear it once
                    // the last one is undone so they can switch sides again.
                    if (G.map.name == 'Korea' && G.chosenSide) {
                        let stillCommitted = false;
                        for (let i = G.log.length - 1; i >= 0; i--) {
                            const entry = G.log[i];
                            if (entry.type !== 'move') continue;
                            stillCommitted = entry.player === playerNumber && entry.move.name === MoveName.BuyResource;
                            break;
                        }
                        if (!stillCommitted) {
                            G.chosenSide = undefined;
                        }
                    }
                    break;
                }

                case MoveName.Build: {
                    // Japan: was this specific build the move that consumed the free jump?
                    // Round 1: the player's second starting-city build auto-uses the jump.
                    // Round 2+: the build carried freeJump:true. Decided before the city is
                    // popped (the round-1 check needs the pre-pop city count). The jump is
                    // returned only when *this* move spent it — never re-derived from topology.
                    let undoJapanFreeJump = false;
                    if (G.map.name === 'Japan' && player.usedFreeJump) {
                        if (
                            G.round === 1 &&
                            player.cities.length >= 2 &&
                            (G.map.startingCities?.includes(lastMove.data.name) ?? false)
                        ) {
                            undoJapanFreeJump = true;
                        } else if (lastMove.data.freeJump) {
                            undoJapanFreeJump = true;
                        }
                    }

                    player.cities.pop();
                    player.money += lastMove.data.price;

                    const position = G.players.filter((p) => p.cities.find((c) => c.name == lastMove.data.name)).length;

                    if (G.options.trackTotalSpent) {
                        player.totalSpentCities -= 10 + position * 5;
                        player.totalSpentConnections -= lastMove.data.price - (10 + position * 5);
                    }

                    G.log.pop();

                    if (G.map.name == 'India') {
                        G.citiesBuiltInCurrentRound!--;
                    }

                    // Japan: return the free jump only if this build was the one that spent it.
                    if (undoJapanFreeJump) {
                        player.usedFreeJump = false;
                    }

                    break;
                }

                case MoveName.UsePowerPlant: {
                    player.powerPlantsNotUsed.push(lastMove.data.powerPlant);
                    lastMove.data.resourcesSpent.forEach((resourceType) => {
                        switch (resourceType) {
                            case ResourceType.Coal:
                                player.coalLeft++;
                                G.coalSupply--;
                                break;

                            case ResourceType.Oil:
                                player.oilLeft++;
                                G.oilSupply--;
                                break;

                            case ResourceType.Garbage:
                                player.garbageLeft++;
                                G.garbageSupply--;
                                break;

                            case ResourceType.Uranium:
                                player.uraniumLeft++;
                                G.uraniumSupply--;
                                break;
                        }
                    });

                    player.citiesPowered -= lastMove.data.citiesPowered;

                    const reverseLog = G.log.slice().reverse();
                    const index =
                        G.log.length - reverseLog.findIndex((l) => l.type == 'move' && l.player == player.id) - 1;
                    G.log.splice(index, 1);

                    break;
                }
            }
        }
    }

    player.availableMoves = null;

    if (move.name == MoveName.Undo) {
        const reverseLog = G.log.slice().reverse();
        const logMove = reverseLog.find((m) => m.type == 'move' && m.player == player.id) as LogMove;
        player.lastMove = logMove?.move;
    } else {
        player.lastMove = move;
    }

    G.cardsLeft = G.powerPlantsDeck.length;
    G.nextCardWeak = G.options.variant == 'recharged' && G.cardsLeft > 0 && G.powerPlantsDeck[0].number <= 15;

    G.currentPlayers.forEach((p) => (G.players[p].availableMoves = availableMoves(G, G.players[p])));

    return G;
}

export function moveAI(G: GameState, playerNumber: number): GameState {
    const player = G.players[playerNumber];
    const availableMoves = player.availableMoves;
    let chosenMove: Move = { name: MoveName.Pass, data: true };

    switch (G.phase) {
        case Phase.RegionSelection: {
            if (availableMoves?.ChooseRegion && availableMoves.ChooseRegion.length > 0) {
                chosenMove = { name: MoveName.ChooseRegion, data: chooseRandom(availableMoves.ChooseRegion) };
            }

            break;
        }

        case Phase.ColorSelection: {
            if (availableMoves?.ChooseColor && availableMoves.ChooseColor.length > 0) {
                chosenMove = { name: MoveName.ChooseColor, data: chooseRandom(availableMoves.ChooseColor) };
            }

            break;
        }

        case Phase.Auction: {
            if (availableMoves?.ChoosePowerPlant) {
                if (
                    !availableMoves.Pass ||
                    (Math.random() > 0.5 && player.money - availableMoves.ChoosePowerPlant[0] >= 20)
                ) {
                    chosenMove = {
                        name: MoveName.ChoosePowerPlant,
                        data: chooseRandom(availableMoves.ChoosePowerPlant),
                    };
                } else {
                    chosenMove = { name: MoveName.Pass, data: true };
                }
            } else if (availableMoves?.Bid) {
                if (
                    !availableMoves.Pass ||
                    (availableMoves.Bid.length > 0 &&
                        Math.random() > 0.5 &&
                        player.money - availableMoves?.Bid[0] >= 15)
                ) {
                    if (G.options.fastBid) {
                        const bid = Math.floor((Math.random() * availableMoves.Bid.length) / 2);
                        chosenMove = { name: MoveName.Bid, data: availableMoves?.Bid[bid] };
                    } else {
                        chosenMove = { name: MoveName.Bid, data: availableMoves?.Bid[0] };
                    }
                } else {
                    chosenMove = { name: MoveName.Pass, data: true };
                }
            } else if (availableMoves?.DiscardPowerPlant) {
                // Pick from the offered candidates: the oldest-held plant can be an
                // Australia uranium mine or the just-bought plant, neither of which
                // is legal to discard — and dropPlayer() replays this prompt via
                // moveAI, so an illegal pick would throw inside the drop path.
                chosenMove = { name: MoveName.DiscardPowerPlant, data: Math.min(...availableMoves.DiscardPowerPlant) };
            } else if (availableMoves?.DiscardResources) {
                chosenMove = { name: MoveName.DiscardResources, data: chooseRandom(availableMoves.DiscardResources) };
            }

            break;
        }

        case Phase.Resources: {
            if (availableMoves?.BuyResource && player.money > 20) {
                const buyCoal = availableMoves.BuyResource.find((r) => r.resource == ResourceType.Coal);
                const buyOil = availableMoves.BuyResource.find((r) => r.resource == ResourceType.Oil);
                const buyGarbage = availableMoves.BuyResource.find((r) => r.resource == ResourceType.Garbage);
                const buyUranium = availableMoves.BuyResource.find((r) => r.resource == ResourceType.Uranium);

                if (buyCoal && player.coalLeft < (player.coalCapacity + player.hybridCapacity) / 2) {
                    chosenMove = { name: MoveName.BuyResource, data: buyCoal };
                } else if (buyOil && player.oilLeft < (player.oilCapacity + player.hybridCapacity) / 2) {
                    chosenMove = { name: MoveName.BuyResource, data: buyOil };
                } else if (buyGarbage && player.garbageLeft < player.garbageCapacity / 2) {
                    chosenMove = { name: MoveName.BuyResource, data: buyGarbage };
                } else if (buyUranium && player.uraniumLeft < player.uraniumCapacity / 2) {
                    chosenMove = { name: MoveName.BuyResource, data: buyUranium };
                }
            }

            break;
        }

        case Phase.Building: {
            const capacity = player.powerPlants.map((pp) => pp.citiesPowered).reduce((a, b) => a + b);

            if (availableMoves?.Build && (player.money >= 30 || capacity > player.cities.length)) {
                const minPrice = availableMoves.Build.sort((a, b) => a.price - b.price)[0].price;
                const cheapestCities = availableMoves.Build.filter((x) => x.price == minPrice);
                chosenMove = { name: MoveName.Build, data: chooseRandom(cheapestCities) };
            }

            break;
        }

        case Phase.Bureaucracy: {
            if (availableMoves?.UsePowerPlant && player.cities.length > player.citiesPowered) {
                chosenMove = {
                    name: MoveName.UsePowerPlant,
                    data: availableMoves.UsePowerPlant.sort((a, b) => a.citiesPowered - b.citiesPowered)[0],
                };
            }

            break;
        }
    }

    console.log('ai move', chosenMove);
    return move(G, chosenMove, playerNumber);
}

function chooseRandom(moves: any[]) {
    return moves[Math.floor(Math.random() * moves.length)];
}

export function ended(G: GameState): boolean {
    return G.phase == Phase.GameEnd;
}

export function scores(G: GameState): number[] {
    return ended(G) ? G.players.map((p) => p.citiesPowered) : G.players.map((_) => 0);
}

export function reconstructState(gameState: GameState, to?: number): GameState {
    const initialState = getBaseState(gameState);
    const G = cloneDeep(initialState);

    if (to != undefined && gameState.seed == 'secret') {
        if (gameState.knownPowerPlantDeck) {
            G.map = gameState.map;
            G.powerPlantsDeck = cloneDeep(gameState.knownPowerPlantDeck);
            G.actualMarket = G.powerPlantsDeck.splice(0, 4);
            G.futureMarket = G.powerPlantsDeck.splice(0, 4);
            G.players[G.currentPlayers[0]].availableMoves = availableMoves(G, G.players[G.currentPlayers[0]]);
            G.powerPlantDeckAfterStep3 = gameState.knownPowerPlantDeckStep3;
            G.knownPowerPlantDeck = G.actualMarket.concat(G.futureMarket);
        }
    }

    const log = to != null ? gameState.log.slice(0, to) : gameState.log;
    for (const item of log) {
        switch (item.type) {
            case 'event': {
                if (item.event.endsWith('was dropped')) {
                    const playerNum = +item.event.split(' ')[1];
                    G.players[playerNum].isDropped = true;
                }

                break;
            }

            case 'move': {
                move(G, item.move, item.player, true);
                break;
            }
        }
    }

    return G;
}

function updatePlayerCapacity(player: Player) {
    player.coalCapacity =
        player.oilCapacity =
        player.garbageCapacity =
        player.uraniumCapacity =
        player.hybridCapacity =
            0;

    player.powerPlants.forEach((powerPlant) => {
        switch (powerPlant.type) {
            case PowerPlantType.Coal: {
                player.coalCapacity += powerPlant.cost * 2;
                break;
            }

            case PowerPlantType.Oil: {
                player.oilCapacity += powerPlant.cost * 2;
                break;
            }

            case PowerPlantType.Garbage: {
                if (powerPlant.storage) {
                    // For the India map, garbage plants have cost one higher, but have no additional storage.
                    player.garbageCapacity += powerPlant.storage;
                } else {
                    player.garbageCapacity += powerPlant.cost * 2;
                }

                break;
            }

            case PowerPlantType.Uranium: {
                player.uraniumCapacity += powerPlant.cost * 2;
                break;
            }

            case PowerPlantType.Hybrid: {
                player.hybridCapacity += powerPlant.cost * 2;
                break;
            }
        }
    });
}

function addPowerPlant(G: GameState) {
    let powerPlant = G.powerPlantsDeck.shift();

    if (powerPlant) {
        if (G.step == 3) {
            if (G.knownPowerPlantDeckStep3) {
                G.knownPowerPlantDeckStep3.push(powerPlant);
            }
        } else {
            if (G.knownPowerPlantDeck) {
                G.knownPowerPlantDeck.push(powerPlant);
            }
        }

        if (G.options.variant == 'original' && G.map.name != 'China') {
            const maxCities = Math.max(...G.players.map((p) => p.cities.length));
            while (powerPlant.number <= maxCities) {
                G.log.push({
                    type: 'event',
                    event: `Power plant ${powerPlant?.number} discarded.`,
                });

                if (G.powerPlantsDeck.length > 0) {
                    powerPlant = G.powerPlantsDeck.shift()!;

                    if (G.step == 3) {
                        if (G.knownPowerPlantDeckStep3) {
                            G.knownPowerPlantDeckStep3.push(powerPlant);
                        }
                    } else {
                        if (G.knownPowerPlantDeck) {
                            G.knownPowerPlantDeck.push(powerPlant);
                        }
                    }
                } else {
                    break;
                }
            }
        }

        let skipAdd = false;
        if (powerPlant.number == 99) {
            if (G.powerPlantDeckAfterStep3) {
                G.powerPlantsDeck = G.powerPlantDeckAfterStep3;
            } else if (G.map.name == 'China') {
                G.step = 3;
            } else {
                G.powerPlantsDeck = shuffle(G.powerPlantsDeck, G.seed);
            }

            if (G.phase != Phase.Auction) {
                if (G.map.name == 'Middle East' && G.step == 1) {
                    // Add step 3 card to market, then trigger step 2 process.
                    const market = [...G.actualMarket, ...G.futureMarket, powerPlant];
                    market.sort((a, b) => a.number - b.number);
                    G.actualMarket = market.slice(0, 4);
                    G.futureMarket = market.slice(4);
                    enterStepTwoMiddleEast(G);
                    skipAdd = true;
                } else {
                    if (G.map.name == 'UK & Ireland' && G.step == 1) {
                        // UK&I: Step 3 sits 3rd from last in the deck, so it can
                        // surface before any player hits citiesToStep2. Fire Step
                        // 2 here so its rules register before Step 3 takes over.
                        G.log.push({
                            type: 'event',
                            event: 'Starting Step 2 (Step 3 card drawn before Step 2 threshold).',
                        });
                        G.step = 2;
                    }
                    const powerPlantDiscarded = G.actualMarket.shift();
                    G.log.push({
                        type: 'event',
                        event: `Step 3 will begin next phase, Power Plant ${powerPlantDiscarded?.number} discarded.`,
                    });

                    const market = [...G.actualMarket, ...G.futureMarket];
                    market.sort((a, b) => a.number - b.number);
                    G.actualMarket = market;
                    G.futureMarket = [];
                }
            }
        } else {
            if (G.plantDiscountActive && powerPlant.number < G.actualMarket[0].number) {
                G.log.push({
                    type: 'event',
                    event: `Power Plant ${powerPlant.number} drawn from the deck and discarded.`,
                });
                G.plantDiscountActive = false;
                addPowerPlant(G);
                return;
            } else {
                G.log.push({ type: 'event', event: `Power Plant ${powerPlant.number} drawn from the deck.` });
            }
        }

        if (G.map.name == 'China' && powerPlant.type != PowerPlantType.Step3) {
            const market = [...G.actualMarket, powerPlant];
            market.sort((a, b) => a.number - b.number);
            G.actualMarket = market;
        } else {
            if (!skipAdd) {
                const market = [...G.actualMarket, ...G.futureMarket, powerPlant];
                market.sort((a, b) => a.number - b.number);
                if (G.futureMarket.length == 0) {
                    if (G.map.name == 'Russia') {
                        // Only four plants in market.
                        G.actualMarket = market.slice(0, 4);
                        G.futureMarket = [];
                    } else {
                        G.actualMarket = market.slice(0, 6);
                        G.futureMarket = [];
                    }
                } else {
                    if (G.map.name == 'Russia') {
                        // Only 3 plants in actual market and 3 in future market.
                        G.actualMarket = market.slice(0, 3);
                        G.futureMarket = market.slice(3);
                    } else if (G.map.name == 'Benelux' && market[4].type == PowerPlantType.Wind) {
                        // Add extra ecological plant to actual market.
                        G.actualMarket = market.slice(0, 5);
                        G.futureMarket = market.slice(5);
                    } else {
                        G.actualMarket = market.slice(0, 4);
                        G.futureMarket = market.slice(4);
                    }
                }

                if (G.map.name == 'Middle East' && G.step == 1) {
                    removePlantsForMiddleEastStep1(G);
                }
            }
        }
    }
}

// Manhattan never leaves Step 1, so the usual "future market empties → Step 3"
// machinery is guarded off for it. Instead the power-plant market is driven by
// DECK DEPLETIONS, in three stages tracked by G.manhattanDepletion (0 → 1 → 2).
// This replaces the generic Bureaucracy market refill for Manhattan and runs once
// per Bureaucracy round:
//
//   Stage 0 — before the first depletion. The two highest-numbered future-market
//     plants are set aside each round on a SEPARATE recycle pile (not boxed: they
//     come back) and the market is refilled from the deck, steadily draining it.
//   First depletion (deck runs dry while a recycle pile exists): the recycle pile
//     is reshuffled into a fresh deck and the market refilled. → stage 1.
//   Stage 1 — between the depletions. One highest future plant rotates to the
//     bottom of the deck each round; the deck cycles through exactly once and is
//     drained the rest of the way by ordinary auction purchases.
//   Second depletion (deck runs dry again): the entire market collapses into the
//     actual market, so every plant becomes buyable (Step-3-like, but still
//     Step 1). → stage 2.
//   Stage 2 — endgame churn. The single cheapest market plant is removed from the
//     game each round, shrinking the market until it (or the game) ends.
export function applyManhattanMarketLifecycle(G: GameState) {
    G.manhattanRecyclePile ??= [];
    G.manhattanDepletion ??= 0;

    // Pull the single highest-numbered plant out of the future market.
    const popBiggestFuture = (): PowerPlant | undefined => {
        if (G.futureMarket.length == 0) {
            return undefined;
        }
        G.futureMarket.sort((a, b) => a.number - b.number);
        return G.futureMarket.pop();
    };

    // Draw from the deck until the market holds `size` plants (or the deck is
    // empty), then keep it sorted with the cheapest four buyable (actual market)
    // and the rest visible-but-not-buyable (future market).
    const refillMarketTo = (size: number) => {
        while (G.actualMarket.length + G.futureMarket.length < size && G.powerPlantsDeck.length > 0) {
            const drawn = G.powerPlantsDeck.shift()!;
            if (G.knownPowerPlantDeck) {
                G.knownPowerPlantDeck.push(drawn);
            }
            G.log.push({ type: 'event', event: `Power Plant ${drawn.number} drawn from the deck.` });
            G.futureMarket.push(drawn);
        }
        const market = [...G.actualMarket, ...G.futureMarket].sort((a, b) => a.number - b.number);
        G.actualMarket = market.slice(0, 4);
        G.futureMarket = market.slice(4);
    };

    if (G.manhattanDepletion == 0) {
        for (let i = 0; i < 2; i++) {
            const plant = popBiggestFuture();
            if (!plant) {
                break;
            }
            G.manhattanRecyclePile.push(plant);
            G.log.push({
                type: 'event',
                event: `Setting Power Plant ${plant.number} aside on the recycle pile.`,
            });
        }
        refillMarketTo(8);

        if (G.powerPlantsDeck.length == 0 && G.manhattanRecyclePile.length > 0) {
            G.powerPlantsDeck = shuffle(G.manhattanRecyclePile, G.seed + ':manhattan-depletion-1');
            G.manhattanRecyclePile = [];
            G.manhattanDepletion = 1;
            G.log.push({
                type: 'event',
                event: 'The draw deck is empty — reshuffling the recycle pile into a new deck.',
            });
            refillMarketTo(8);
        }
    } else if (G.manhattanDepletion == 1) {
        const plant = popBiggestFuture();
        if (plant) {
            G.powerPlantsDeck.push(plant);
            G.log.push({
                type: 'event',
                event: `Putting Power Plant ${plant.number} on the bottom of the deck.`,
            });
        }
        refillMarketTo(8);

        if (G.powerPlantsDeck.length == 0) {
            G.manhattanDepletion = 2;
            const market = [...G.actualMarket, ...G.futureMarket].sort((a, b) => a.number - b.number);
            G.actualMarket = market;
            G.futureMarket = [];
            G.log.push({
                type: 'event',
                event: 'The deck is empty for the second time — the entire market is now buyable.',
            });
        }
    } else {
        // Stage 2. Collapse any stragglers into the buyable market (defensive), then
        // box the single cheapest plant for the game's final churn.
        if (G.futureMarket.length > 0) {
            const market = [...G.actualMarket, ...G.futureMarket].sort((a, b) => a.number - b.number);
            G.actualMarket = market;
            G.futureMarket = [];
        }
        if (G.actualMarket.length > 0) {
            const removed = G.actualMarket.shift()!;
            G.log.push({
                type: 'event',
                event: `Removing the smallest plant, Power Plant ${removed.number}, from the game.`,
            });
        }
    }
}

// During step 1 for the Middle East map, we remove garbage and uranium plants from the actual market.
// If the number is 6, 11, or 14, the plant is removed from the game. Otherwise, it's put under the deck.
function removePlantsForMiddleEastStep1(G: GameState) {
    let plantToRemove: PowerPlant | undefined = G.actualMarket.find(
        (pp: PowerPlant) => pp.type == PowerPlantType.Garbage || pp.type == PowerPlantType.Uranium
    );

    while (plantToRemove) {
        removePowerPlant(G, plantToRemove);

        if ([6, 11, 14].includes(plantToRemove.number)) {
            G.log.push({
                type: 'event',
                event: `Removing Power Plant ${plantToRemove.number} from game.`,
            });
        } else {
            G.powerPlantsDeck.push(plantToRemove);
            G.log.push({
                type: 'event',
                event: `Sending Power Plant ${plantToRemove.number} to the bottom of the deck.`,
            });
        }

        // Prevent infinite loop cycling through power plants.
        const availableFuturePlants = G.futureMarket.filter(
            (pp) => pp.type != PowerPlantType.Garbage && pp.type != PowerPlantType.Uranium
        );
        const nextFuturePlantNumber = availableFuturePlants.length > 0 ? availableFuturePlants[0].number : 100;
        if (
            G.powerPlantsDeck.filter(
                (pp) =>
                    (pp.type != PowerPlantType.Garbage && pp.type != PowerPlantType.Uranium) ||
                    pp.number > nextFuturePlantNumber
            ).length == 0
        ) {
            G.log.push({
                type: 'event',
                event: 'No suitable power plants available to draw.',
            });
            break;
        }

        addPowerPlant(G);
        plantToRemove = G.actualMarket.find(
            (pp: PowerPlant) => pp.type == PowerPlantType.Garbage || pp.type == PowerPlantType.Uranium
        );
    }
}

function enterStepTwoMiddleEast(G: GameState) {
    // Shuffle deck of remaining power plants and put step 3 card back underneath.
    const step3 = G.futureMarket.pop()!;
    G.powerPlantsDeck = shuffle(G.powerPlantsDeck, G.seed);
    G.powerPlantsDeck.push(step3);

    // Draw new plant to replace step 3 card.
    addPowerPlant(G);

    // Discard two lowest power plants from current market.
    G.log.push({
        type: 'event',
        event: 'Step 2 will begin next phase, discarding two power plants.',
    });
    G.step = 2;

    const powerPlantDiscarded1 = G.actualMarket.shift();
    if (powerPlantDiscarded1) {
        G.log.push({
            type: 'event',
            event: `Power Plant ${powerPlantDiscarded1.number} discarded to start step 2.`,
        });
        addPowerPlant(G);
    }

    const powerPlantDiscarded2 = G.actualMarket.shift();
    if (powerPlantDiscarded2) {
        G.log.push({
            type: 'event',
            event: `Power Plant ${powerPlantDiscarded2.number} discarded to start step 2.`,
        });
        addPowerPlant(G);
    }
}

// Australia CO2 tax: when Step 3 begins, the $1 and $2 resource spaces close for
// the rest of the game and the six cheapest tokens of each resource move to the
// new $9 and $10 spaces — i.e. the active price scale shifts up by $2. Because
// the engine prices a market of M cubes as prices[length - M] (cubes sit at the
// expensive end), swapping the price arrays to the $3–$10 scale reprices the
// existing cubes exactly as the physical relocation does, for both full and
// partially-depleted markets — the market counts and supply pools are untouched.
// Idempotent and Australia-only, so it is safe to call at every Step 3 entry.
export function applyAustraliaStep3Shift(G: GameState) {
    if (G.map.name !== 'Australia') {
        return;
    }
    if (G.coalPrices && G.coalPrices[0] === 3) {
        return; // already shifted this game
    }
    const shifted = [3, 3, 3, 4, 4, 4, 5, 5, 5, 6, 6, 6, 7, 7, 7, 8, 8, 8, 9, 9, 9, 10, 10, 10];
    G.coalPrices = [...shifted];
    G.oilPrices = [...shifted];
    G.garbagePrices = [...shifted];
    G.log.push({
        type: 'event',
        event: 'CO2 tax (Step 3): the $1 and $2 resource spaces close; the six cheapest tokens of each resource move to the new $9 and $10 spaces.',
    });
}

function rebuildPlantMarketForChina(G: GameState) {
    /*At the beginning of phase 5, the players fill the power plant market with new power plants. Depending on the
number of players, the players always add a minimum of 1, 2, or 3 power plants to the market from the supply:
with 2 and 3 players, add at least 1 power plant.
with 4 and 5 players, add at least 2 power plants.
with 6 players, add at least 3 power plants.
The players add more than the minimum if the number of plants in the market is still more than 1 less than the number of players.
Exception: with 2 players, add plants until there are 2 in the market.*/
    let minPlantsToAdd = 0;
    if (G.players.length == 2 || G.players.length == 3) {
        minPlantsToAdd = 1;
    } else if (G.players.length == 4 || G.players.length == 5) {
        minPlantsToAdd = 2;
    } else if (G.players.length == 6) {
        minPlantsToAdd = 3;
    }

    const currentActualSize = G.actualMarket.length;
    const minSize = G.players.length - 1;
    const numPlantsToAdd = Math.max(minPlantsToAdd, minSize - currentActualSize);
    for (let i = 0; i < numPlantsToAdd; i++) {
        if (G.step == 3) {
            break;
        } else {
            addPowerPlant(G);
        }
    }

    // Special rule to move the market for two players
    while (G.players.length == 2 && G.actualMarket.length < 2 && G.step != 3) {
        addPowerPlant(G);
    }

    if (G.step == 3) {
        G.actualMarket = G.actualMarket.filter((pp) => pp.type != PowerPlantType.Step3);
        while (G.actualMarket.length < 4 && G.powerPlantsDeck.length > 0) {
            addPowerPlant(G);
        }
    } else {
        // Target size is one less than number of players, or 2 for a 2-player game.
        const targetSize = Math.max(2, G.players.length - 1);
        while (G.actualMarket.length > targetSize) {
            G.actualMarket.shift();
        }
    }
}

function removePowerPlant(G: GameState, powerPlant: PowerPlant) {
    G.actualMarket.splice(
        G.actualMarket.findIndex((pp) => pp.number == powerPlant.number),
        1
    );
}

export function getPowerPlant(num: number, mapName = ''): PowerPlant {
    if (mapName == 'India') {
        return indiaPowerPlants.find((p) => p.number == num)!;
    } else {
        return powerPlants.find((p) => p.number == num)!;
    }
}

function getBaseState(G: GameState): GameState {
    const baseState = setup(G.players.length, G.options, G.seed);
    baseState.players.forEach((player, i) => {
        player.name = G.players[i].name;
        player.isAI = G.players[i].isAI;
    });

    return baseState;
}

function playerNameHTML(player) {
    return `<span style="background-color: ${
        player.color ?? playerColors[player.id]
    }; font-weight: bold; padding: 0 3px;">${player.name}</span>`;
}

export function playersSortedByScore(G: GameState): Player[] {
    return cloneDeep(G.players)
        .sort((p1, p2) => {
            if (p1.citiesPowered == p2.citiesPowered) {
                if (p1.money == p2.money) {
                    return p1.cities.length - p2.cities.length;
                }

                return p1.money - p2.money;
            }

            return p1.citiesPowered - p2.citiesPowered;
        })
        .reverse();
}

function calculateCitiesPowered(G: GameState) {
    G.players.forEach((player) => {
        player.citiesPowered = calculateMaxCitiesPowered(G, player);
    });
}

function calculateMaxCitiesPowered(G: GameState, player: Player) {
    // Australia's uranium mines never power cities, so they are excluded from the
    // powering combinations (this also keeps the 2^n permutation set smaller).
    const countablePlants = player.powerPlants.filter((pp) => !isUraniumMine(G, pp));
    const permutations: PowerPlant[][] = [];
    for (let i = 0; i < Math.pow(2, countablePlants.length); i++) {
        const perm: PowerPlant[] = [];
        countablePlants.forEach((pp, index) => {
            if (i & Math.pow(2, index)) {
                perm.push(pp);
            }
        });
        permutations.push(perm);
    }

    let max = 0;
    permutations.forEach((permutation) => {
        if (isValid(player, permutation)) {
            const citiesPowered = permutation.map((p) => p.citiesPowered).reduce((a, b) => a + b, 0);
            max = Math.max(max, citiesPowered);
        }
    });

    return Math.min(player.cities.length, max);
}

function isValid(player: Player, powerPlants: PowerPlant[]) {
    const coalUsed = powerPlants
        .filter((pp) => pp.type == PowerPlantType.Coal)
        .map((pp) => pp.cost)
        .reduce((a, b) => a + b, 0);
    const oilUsed = powerPlants
        .filter((pp) => pp.type == PowerPlantType.Oil)
        .map((pp) => pp.cost)
        .reduce((a, b) => a + b, 0);
    const garbageUsed = powerPlants
        .filter((pp) => pp.type == PowerPlantType.Garbage)
        .map((pp) => pp.cost)
        .reduce((a, b) => a + b, 0);
    const uraniumUsed = powerPlants
        .filter((pp) => pp.type == PowerPlantType.Uranium)
        .map((pp) => pp.cost)
        .reduce((a, b) => a + b, 0);
    const hybridUsed = powerPlants
        .filter((pp) => pp.type == PowerPlantType.Hybrid)
        .map((pp) => pp.cost)
        .reduce((a, b) => a + b, 0);

    if (
        coalUsed > player.coalLeft ||
        oilUsed > player.oilLeft ||
        garbageUsed > player.garbageLeft ||
        uraniumUsed > player.uraniumLeft
    ) {
        return false;
    }

    if (hybridUsed > player.coalLeft - coalUsed + player.oilLeft - oilUsed) {
        return false;
    }

    return true;
}

function toResourcesPhase(G: GameState) {
    if (G.map.name == 'Baden-Württemberg') {
        // Baden-Württemberg: player order is determined AFTER the auction phase, every round.
        setPlayerOrder(G);
    } else if (G.round == 1) {
        // Round 1 starts in seating order; once the auction ends, reorder by the
        // plants just bought (there are no cities yet). Done here — the single funnel
        // into the resources phase — so EVERY auction-completion path reorders, not
        // just the uncontested ChoosePowerPlant branch. Contested bids and Manhattan's
        // discount-bonus purchase otherwise reach this point with the seating order
        // intact (e.g. the first player keeps moving first regardless of plants bought).
        setPlayerOrder(G);
    }

    G.players.forEach((p) => {
        p.bid = 0;
        p.passed = p.isDropped;
    });

    G.players.forEach((p) => {
        p.skipAuction = false;
    });

    G.discountBonusPlayer = undefined;

    if (G.options.variant == 'recharged') {
        if (G.plantDiscountActive) {
            G.plantDiscountActive = false;
            if (G.actualMarket.length > 0) {
                G.log.push({ type: 'event', event: `Discarding Power Plant ${G.actualMarket[0].number}.` });
                G.actualMarket.shift();
                addPowerPlant(G);
            }
        } else if (G.map.name == 'Benelux') {
            G.discardSmallestPlant = true;
        }
    }

    if (G.futureMarket.find((pp) => pp.number == 99)) {
        if (G.map.name == 'Middle East' && G.step == 1) {
            enterStepTwoMiddleEast(G);
        } else {
            const powerPlantDiscarded = G.actualMarket.shift();
            G.futureMarket.pop();
            G.log.push({
                type: 'event',
                event: `Starting Step 3, Power Plant ${powerPlantDiscarded?.number} discarded.`,
            });
            G.step = 3;
            applyAustraliaStep3Shift(G);

            G.actualMarket = [...G.actualMarket, ...G.futureMarket];
            G.futureMarket = [];
        }
    }

    G.phase = Phase.Resources;
    setCurrentPlayer(G, G.playerOrder[G.players.length - 1]);
}

function endAuction(G: GameState, winningPlayer: Player, bid: number) {
    winningPlayer.powerPlants.push(G.chosenPowerPlant!);
    winningPlayer.money -= bid;

    if (G.options.trackTotalSpent) {
        winningPlayer.totalSpentPlants += bid;
    }

    // Manhattan: buying the discounted power plant (whose minimum bid was lowered to
    // 1) lets the buyer purchase one more plant this phase. Keep them eligible
    // (skipAuction stays false) and remember they are owed the extra purchase, so
    // they may also decline it via Pass even in round 1 — when buying is otherwise
    // mandatory. minimunBid == 1 uniquely marks the discount auction (a normal bid
    // floor is the plant number, always >= 3).
    if (
        G.map.name == 'Manhattan' &&
        G.options.variant == 'recharged' &&
        G.minimunBid == 1 &&
        !winningPlayer.isDropped
    ) {
        G.discountBonusPlayer = winningPlayer.id;
    } else {
        winningPlayer.skipAuction = true;

        // If this win was the bonus purchase itself, the buyer is now done.
        if (G.discountBonusPlayer == winningPlayer.id) {
            G.discountBonusPlayer = undefined;
        }
    }

    updatePlayerCapacity(winningPlayer);

    G.log.push({
        type: 'event',
        event: `${winningPlayer.name} wins the bid and pays ${bid}.`,
        pretty: `${playerNameHTML(winningPlayer)} wins the bid and pays <span style="color: green">$${bid}</span>.`,
    });

    removePowerPlant(G, G.chosenPowerPlant!);
    G.chosenPowerPlant = G.currentBid = undefined;
}

function setPlayerOrder(G: GameState) {
    G.playerOrder = cloneDeep(G.players)
        .sort((a, b) => {
            const citiesA = a.cities.length;
            const citiesB = b.cities.length;

            if (citiesA == citiesB) {
                return (
                    Math.max(...a.powerPlants.map((pp) => pp.number)) -
                    Math.max(...b.powerPlants.map((pp) => pp.number))
                );
            }

            return citiesA - citiesB;
        })
        .map((p) => p.id)
        .reverse();
}

function setCurrentPlayer(G: GameState, playerNum: number) {
    G.currentPlayers = [playerNum];

    if (G.players[playerNum].isDropped && G.players.some((p) => !p.isDropped)) {
        G.players[playerNum].passed = true;
        nextPlayer(G);
    }
}

function nextPlayer(G: GameState) {
    if (G.phase == Phase.Auction) {
        if (G.chosenPowerPlant == undefined) {
            nextPlayerAuction(G);
        } else {
            nextPlayerClockwise(G);
        }
    } else {
        nextPlayerReverse(G);
    }
}

function nextPlayerClockwise(G: GameState) {
    const index = G.currentPlayers[0];
    G.currentPlayers = [(index + 1) % G.players.length];

    if (G.players[G.currentPlayers[0]].isDropped && G.players.some((p) => !p.isDropped)) {
        G.players[G.currentPlayers[0]].passed = true;
        G.players[G.currentPlayers[0]].skipAuction = true;
        nextPlayerClockwise(G);
    }

    if (
        (G.players[G.currentPlayers[0]].skipAuction || G.players[G.currentPlayers[0]].passed) &&
        G.players.some((p) => !p.skipAuction && !p.passed && !p.isDropped)
    ) {
        nextPlayerClockwise(G);
    }
}

function nextPlayerReverse(G: GameState) {
    const index = G.playerOrder.indexOf(G.currentPlayers[0]);
    G.currentPlayers = [G.playerOrder[(index - 1 + G.players.length) % G.players.length]];

    if (G.players[G.currentPlayers[0]].isDropped && G.players.some((p) => !p.isDropped)) {
        G.players[G.currentPlayers[0]].passed = true;
        nextPlayerReverse(G);
    }
}

function nextPlayerAuction(G: GameState, reset = false) {
    let playerNum: number;
    if (reset) {
        playerNum = G.playerOrder[0];
    } else {
        const index = G.playerOrder.indexOf(G.currentPlayers[0]);
        playerNum = G.playerOrder[(index + 1) % G.players.length];
    }

    G.currentPlayers = [playerNum];
    const player = G.players[playerNum];

    if (player.isDropped) {
        player.passed = true;
        player.skipAuction = true;
    }

    if ((player.skipAuction || player.passed) && G.players.some((p) => !p.skipAuction && !p.passed && !p.isDropped)) {
        nextPlayerAuction(G);
    }
}

function updateGameState(G: GameState) {
    if (!G.coalResupply) {
        const map = maps.find((map) => map.name === G.map.name);

        if (map?.resupply) {
            G.coalResupply = map.resupply[0];
            G.oilResupply = map.resupply[1];
            G.garbageResupply = map.resupply[2];
            G.uraniumResupply = map.resupply[3];
        } else {
            G.coalResupply = [
                [3, 4, 3],
                [4, 5, 3],
                [5, 6, 4],
                [5, 7, 5],
                [7, 9, 6],
            ];
            G.oilResupply = [
                [2, 2, 4],
                [2, 3, 4],
                [3, 4, 5],
                [4, 5, 6],
                [5, 6, 7],
            ];
            G.garbageResupply = [
                [1, 2, 3],
                [1, 2, 3],
                [2, 3, 4],
                [3, 3, 5],
                [3, 5, 6],
            ];
            G.uraniumResupply = [
                [1, 1, 1],
                [1, 1, 1],
                [1, 2, 2],
                [2, 3, 2],
                [2, 3, 3],
            ];
        }

        const p = G.players.length - 2;
        G.resourceResupply = [
            `[${G.coalResupply[p][0]}, ${G.oilResupply[p][0]}, ${G.garbageResupply[p][0]}, ${G.uraniumResupply[p][0]}]`,
            `[${G.coalResupply[p][1]}, ${G.oilResupply[p][1]}, ${G.garbageResupply[p][1]}, ${G.uraniumResupply[p][1]}]`,
            `[${G.coalResupply[p][2]}, ${G.oilResupply[p][2]}, ${G.garbageResupply[p][2]}, ${G.uraniumResupply[p][2]}]`,
        ];
        if (G.coalResupplyNorth && G.oilResupplyNorth && G.garbageResupplyNorth) {
            G.resourceResupplyNorth = [
                `[${G.coalResupplyNorth[p][0]}, ${G.oilResupplyNorth[p][0]}, ${G.garbageResupplyNorth[p][0]}]`,
                `[${G.coalResupplyNorth[p][1]}, ${G.oilResupplyNorth[p][1]}, ${G.garbageResupplyNorth[p][1]}]`,
                `[${G.coalResupplyNorth[p][2]}, ${G.oilResupplyNorth[p][2]}, ${G.garbageResupplyNorth[p][2]}]`,
            ];
        }
    }
}

function fastAuction(G: GameState, player: Player, bid: number) {
    player.bid = bid;
    G.currentPlayers = G.currentPlayers.filter((id) => id !== player.id);

    if (G.currentPlayers.length === 0) {
        G.log.push(...G.hiddenLog);
        G.hiddenLog = [];

        const bids = G.players.map((p) => p.bid).filter((b) => b > 0);
        let cost = G.minimunBid;
        const highestBid = Math.max(...bids);
        const highestBidders = G.players.filter((p) => !p.isDropped && p.bid === highestBid);
        let winnerId = highestBidders[0].id;

        if (bids.length > 1) {
            bids.splice(bids.indexOf(highestBid), 1);
            const secondHighestBid = Math.max(...bids);

            // In case of a tie, use turn order
            if (highestBidders.length > 1) {
                let index = G.auctioningPlayer!;

                while (!highestBidders.find((p) => p.id == index)) {
                    index = (index + 1) % G.players.length;
                }

                cost = secondHighestBid;
                winnerId = index;
            } else {
                let index = G.auctioningPlayer!;

                cost = 0;
                while (cost == 0) {
                    if (highestBidders[0].id == index) {
                        cost = secondHighestBid;
                    } else if (G.players[index].bid == secondHighestBid) {
                        cost = secondHighestBid + 1;
                    }

                    index = (index + 1) % G.players.length;
                }
            }
        }

        const winningPlayer = G.players[winnerId];

        endAuction(G, winningPlayer, cost);

        if (
            (countHeldPowerPlants(G, winningPlayer) > 4 ||
                (G.players.length > 2 && countHeldPowerPlants(G, winningPlayer) > 3)) &&
            !winningPlayer.isDropped
        ) {
            setCurrentPlayer(G, winningPlayer.id);
        } else {
            if (G.map.name != 'China' || G.step == 3) {
                addPowerPlant(G);
            }

            if (G.players.some((p) => !p.skipAuction && !p.isDropped)) {
                G.players.forEach((p) => {
                    p.bid = 0;
                    p.passed = p.isDropped;
                });

                nextPlayerAuction(G, true);
            } else {
                toResourcesPhase(G);
            }
        }
    }
}
