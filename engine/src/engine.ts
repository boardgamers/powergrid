import assert from 'assert';
import { cloneDeep, isEqual, range } from 'lodash';
import seedrandom from 'seedrandom';
import { availableMoves } from './available-moves';
import { GameOptions, GameState, Phase, Player, PowerPlant, PowerPlantType, ResourceType } from './gamestate';
import { LogMove } from './log';
import { GameMap, maps, mapsRecharged } from './maps';
import { Move, MoveName, Moves } from './move';
import { indiaPowerPlants, powerPlants } from './powerPlants';
import prices from './prices';
import { asserts, shuffle } from './utils';

export const playerColors = ['limegreen', 'mediumorchid', 'red', 'dodgerblue', 'yellow', 'brown'];

const citiesToStep2 = [10, 7, 7, 7, 6];
const citiesToEndGame = [21, 17, 17, 15, 14];
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
        if (numPlayers == 2 || numPlayers == 3) {
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
        trackTotals: trackTotalSpent = true,
    }: GameOptions,
    seed?: string,
    forceDeck?: PowerPlant[],
    forceMap?: GameMap
): GameState {
    seed = seed ?? Math.random().toString();
    const rng = seedrandom(seed);

    const chosenMap = cloneDeep(
        variant == 'original' ? maps.find((m) => m.name == map)! : mapsRecharged.find((m) => m.name == map)!
    );

    if (chosenMap.layout == 'Portrait') {
        chosenMap.viewBox = chosenMap.viewBox || [1480, 1060];
        chosenMap.adjustRatio = chosenMap.adjustRatio || [1, 1];
        chosenMap.playerOrderPosition = chosenMap.playerOrderPosition || [1160, 160];
        chosenMap.cityCountPosition = chosenMap.cityCountPosition || [0, 0];
        chosenMap.powerPlantMarketPosition = chosenMap.powerPlantMarketPosition || [745, 0];
        chosenMap.mapPosition = chosenMap.mapPosition || [0, 0];
        chosenMap.buttonsPosition = chosenMap.buttonsPosition || [1305, 0];
        chosenMap.playerBoardsPosition = chosenMap.playerBoardsPosition || [1105, 240];
        chosenMap.roundInfoPosition = chosenMap.roundInfoPosition || [20, 920];
        chosenMap.supplyPosition = chosenMap.supplyPosition || [675, 920];
    } else {
        chosenMap.viewBox = chosenMap.viewBox || [1465, 860];
        chosenMap.adjustRatio = chosenMap.adjustRatio || [1, 1];
        chosenMap.playerOrderPosition = chosenMap.playerOrderPosition || [1160, 140];
        chosenMap.cityCountPosition = chosenMap.cityCountPosition || [0, 0];
        chosenMap.powerPlantMarketPosition = chosenMap.powerPlantMarketPosition || [745, 0];
        chosenMap.mapPosition = chosenMap.mapPosition || [-10, 0];
        chosenMap.buttonsPosition = chosenMap.buttonsPosition || [1305, 0];
        chosenMap.playerBoardsPosition = chosenMap.playerBoardsPosition || [1105, 200];
        chosenMap.roundInfoPosition = chosenMap.roundInfoPosition || [20, 590];
        chosenMap.supplyPosition = chosenMap.supplyPosition || [0, 720];
    }

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
    }));

    const playerOrder = range(numPlayers);
    const startingPlayer = playerOrder[0];

    let coalResupply: number[][];
    let oilResupply: number[][];
    let garbageResupply: number[][];
    let uraniumResupply: number[][];
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

    chosenMap.cities = chosenMap.cities.map((city) => ({
        ...city,
        x: city.x * chosenMap.adjustRatio![0],
        y: city.y * chosenMap.adjustRatio![1],
    }));

    const regions = chosenMap.cities
        .filter((c, i) => chosenMap.cities.findIndex((cc) => cc.region == c.region) == i)
        .map((c) => c.region);
    const connections = chosenMap.connections.map((con) =>
        con.nodes.map((n) => chosenMap.cities.find((city) => city.name == n)!.region)
    );
    const regionConnections = regions.map((region) =>
        regions.filter(
            (area2) => region != area2 && connections.some((con) => con.includes(region) && con.includes(area2))
        )
    );

    const playRegions = new Set<string>();
    while (playRegions.size != Math.min(regionsInPlay[players.length - 2], regions.length)) {
        const region = regions[Math.floor(rng() * regions.length)];
        if (playRegions.size == 0 || regionConnections[regions.indexOf(region)].some((con) => playRegions.has(con))) {
            playRegions.add(region);
        }
    }

    const filteredMap = cloneDeep(chosenMap);
    filteredMap.cities = filteredMap.cities.filter((city) => playRegions.has(city.region));
    filteredMap.connections = filteredMap.connections.filter((con) =>
        con.nodes.map((n) => chosenMap.cities.find((city) => city.name == n)!.region).every((r) => playRegions.has(r))
    );

    const p = players.length - 2;

    const coalMarket = chosenMap.startingResources ? chosenMap.startingResources[0] : 24;
    const oilMarket = chosenMap.startingResources ? chosenMap.startingResources[1] : 18;
    const garbageMarket = chosenMap.startingResources ? chosenMap.startingResources[2] : variant == 'original' ? 6 : 9;
    const uraniumMarket = chosenMap.startingResources ? chosenMap.startingResources[3] : 2;

    const totalCoal = chosenMap.startingSupply ? chosenMap.startingSupply[0] : 24;
    const totalOil = chosenMap.startingSupply ? chosenMap.startingSupply[1] : 24;
    const totalGarbage = chosenMap.startingSupply ? chosenMap.startingSupply[2] : 24;
    const totalUranium = chosenMap.startingSupply ? chosenMap.startingSupply[3] : 12;

    const coalSupply = totalCoal - coalMarket;
    const oilSupply = totalOil - oilMarket;
    const garbageSupply = totalGarbage - garbageMarket;
    const uraniumSupply = totalUranium - uraniumMarket;

    const coalPrices = cloneDeep(chosenMap.coalPrices ?? prices.coal);
    const oilPrices = cloneDeep(chosenMap.oilPrices ?? prices.oil);
    const garbagePrices = cloneDeep(chosenMap.garbagePrices ?? prices.garbage);
    const uraniumPrices = cloneDeep(chosenMap.uraniumPrices ?? prices.uranium);

    const G: GameState = {
        map: forceMap || filteredMap,
        players,
        playerOrder,
        currentPlayers: [startingPlayer],
        powerPlantsDeck,
        coalSupply,
        oilSupply,
        garbageSupply,
        uraniumSupply,
        coalResupply,
        oilResupply,
        garbageResupply,
        uraniumResupply,
        coalMarket,
        oilMarket,
        garbageMarket,
        uraniumMarket,
        coalPrices,
        oilPrices,
        garbagePrices,
        uraniumPrices,
        actualMarket,
        futureMarket,
        chosenPowerPlant: undefined,
        currentBid: undefined,
        highestBidders: [],
        auctioningPlayer: undefined,
        step: 1,
        phase: Phase.Auction,
        options: { fastBid, map, variant, showMoney },
        log: [],
        hiddenLog: [],
        seed,
        round: 1,
        auctionSkips: 0,
        citiesToStep2: citiesToStep2[numPlayers - 2],
        citiesToEndGame: citiesToEndGame[numPlayers - 2],
        resourceResupply: [
            `[${coalResupply[p][0]}, ${oilResupply[p][0]}, ${garbageResupply[p][0]}, ${uraniumResupply[p][0]}]`,
            `[${coalResupply[p][1]}, ${oilResupply[p][1]}, ${garbageResupply[p][1]}, ${uraniumResupply[p][1]}]`,
            `[${coalResupply[p][2]}, ${oilResupply[p][2]}, ${garbageResupply[p][2]}, ${uraniumResupply[p][2]}]`,
        ],
        paymentTable: cityIncome,
        variant,
        minimunBid: 0,
        plantDiscountActive: variant == 'recharged',
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

    G.players[startingPlayer].availableMoves = availableMoves(G, G.players[startingPlayer]);

    return G;
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

            G.chosenPowerPlant = getPowerPlant(move.data, G.map.name);
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

                if (G.round == 1) {
                    setPlayerOrder(G);
                }

                if (
                    winningPlayer.powerPlants.length <= 3 ||
                    (G.players.length == 2 && winningPlayer.powerPlants.length == 4)
                ) {
                    addPowerPlant(G);
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
                        G.auctionSkips++;

                        if (G.players.some((p) => !p.skipAuction && !p.isDropped)) {
                            nextPlayerAuction(G);
                        } else {
                            if (G.auctionSkips == G.players.length && G.options.variant == 'original') {
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
                                    (winningPlayer.powerPlants.length > 4 ||
                                        (G.players.length > 2 && winningPlayer.powerPlants.length > 3)) &&
                                    !winningPlayer.isDropped
                                ) {
                                    setCurrentPlayer(G, winningPlayer.id);
                                } else {
                                    addPowerPlant(G);

                                    if (G.players.some((p) => !p.skipAuction)) {
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
                            if (maxCities >= G.citiesToStep2 && G.map.name != 'Middle East') {
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

                                addPowerPlant(G);
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
                                    (player) => (player.targetCitiesPowered = calculateMaxCitiesPowered(player))
                                );

                                // Output log for power outage.
                                if (G.citiesBuiltInCurrentRound! > G.players.length * 2) {
                                    G.log.push({
                                        type: 'event',
                                        event: `Power outage! ${G.citiesBuiltInCurrentRound} built this round, which is more than twice the number of players.`,
                                    });
                                }
                            }

                            if (G.futureMarket.length == 0) {
                                G.step = 3;
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

                    if (G.options.trackTotals) {
                        player.totalIncome += payment;
                    }

                    player.citiesPowered = 0;

                    if (G.map.name == 'India') {
                        player.targetCitiesPowered = 0;
                    }

                    if (G.players.filter((p) => !p.passed && !p.isDropped).length == 0) {
                        const coalResupplyValue = Math.min(
                            G.coalSupply,
                            G.coalResupply![G.players.length - 2][G.step - 1]
                        );
                        G.coalMarket += coalResupplyValue;
                        G.coalSupply -= coalResupplyValue;

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
                            oilResupplyValue = Math.min(G.oilSupply, G.oilResupply![G.players.length - 2][G.step - 1]);
                            G.oilMarket += oilResupplyValue;
                            G.oilSupply -= oilResupplyValue;
                        }

                        const garbageResupplyValue = Math.min(
                            G.garbageSupply,
                            G.garbageResupply![G.players.length - 2][G.step - 1]
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
                                G.uraniumResupply![G.players.length - 2][G.step - 1]
                            );
                            G.uraniumMarket += uraniumResupplyValue;
                            G.uraniumSupply -= uraniumResupplyValue;
                        }

                        G.log.push({
                            type: 'event',
                            event: `Resupplying resources: [${coalResupplyValue}, ${oilResupplyValue}, ${garbageResupplyValue}, ${uraniumResupplyValue}].`,
                        });

                        if (G.map.name == 'Middle East' && G.step == 2 && G.futureMarket.length > 0) {
                            // If we aren't about to enter step 3, discard top two plants instead of one.
                            let powerPlantToPush: PowerPlant = G.futureMarket.pop()!;
                            G.log.push({
                                type: 'event',
                                event: `Putting Power Plant ${powerPlantToPush.number} on the bottom of the deck.`,
                            });
                            G.powerPlantsDeck.push(powerPlantToPush);
                            addPowerPlant(G);

                            powerPlantToPush = G.futureMarket.pop()!;
                            G.log.push({
                                type: 'event',
                                event: `Putting Power Plant ${powerPlantToPush.number} on the bottom of the deck.`,
                            });
                            G.powerPlantsDeck.push(powerPlantToPush);
                            addPowerPlant(G);
                        } else if (G.futureMarket.length > 0) {
                            let powerPlantToPush: PowerPlant | undefined;
                            if (G.map.name == 'Quebec') {
                                // For the Quebec map, ecological plants will never be put on the bottom of the deck.
                                const nonEcoPlants = G.futureMarket.filter(
                                    (pp) => pp.type != PowerPlantType.Wind && pp.type != PowerPlantType.Nuclear
                                );
                                powerPlantToPush = nonEcoPlants.pop();
                                G.futureMarket = G.futureMarket.filter((pp) => pp.number != powerPlantToPush?.number);
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
                        } else if (G.actualMarket.length > 0) {
                            G.log.push({ type: 'event', event: `Discarding Power Plant ${G.actualMarket[0].number}.` });
                            G.actualMarket.shift();
                            addPowerPlant(G);
                        }

                        G.round++;

                        setPlayerOrder(G);

                        G.players.forEach((p) => {
                            p.passed = p.isDropped;
                        });
                        G.auctionSkips = 0;

                        if (G.actualMarket.length > 0) {
                            G.phase = Phase.Auction;

                            if (G.futureMarket.length == 0) {
                                G.step = 3;
                            }

                            G.plantDiscountActive = G.options.variant == 'recharged';
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

                addPowerPlant(G);
                G.players.forEach((p) => {
                    p.bid = 0;
                    p.passed = p.isDropped;
                });

                if (G.players.some((p) => !p.skipAuction)) {
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
                    addPowerPlant(G);
                    G.players.forEach((p) => {
                        p.bid = 0;
                        p.passed = p.isDropped;
                    });

                    if (G.players.some((p) => !p.skipAuction)) {
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
                addPowerPlant(G);
                G.players.forEach((p) => {
                    p.bid = 0;
                    p.passed = p.isDropped;
                });

                if (G.players.some((p) => !p.skipAuction)) {
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

            let price: number;
            switch (move.data.resource) {
                case ResourceType.Coal: {
                    if (G.coalMarket == 0) {
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
                    const oilPrices = G.oilPrices ?? prices[ResourceType.Oil];
                    price = oilPrices[oilPrices.length - G.oilMarket];
                    player.oilLeft++;
                    G.oilMarket--;
                    break;
                }

                case ResourceType.Garbage: {
                    const garbagePrices = G.garbagePrices ?? prices[ResourceType.Garbage];
                    price = garbagePrices[garbagePrices.length - G.garbageMarket];
                    player.garbageLeft++;
                    G.garbageMarket--;
                    break;
                }

                case ResourceType.Uranium: {
                    const uraniumPrices = G.uraniumPrices ?? prices[ResourceType.Uranium];
                    price = uraniumPrices[uraniumPrices.length - G.uraniumMarket];
                    player.uraniumLeft++;
                    G.uraniumMarket--;
                    break;
                }
            }

            player.money -= price;

            if (G.options.trackTotals) {
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

            const position = G.players.filter((p) => p.cities.find((c) => c.name == move.data.name)).length;
            player.cities.push({ name: move.data.name, position });
            player.money -= move.data.price;

            if (G.options.trackTotals) {
                player.totalSpentCities += 10 + position * 5;
                player.totalSpentConnections += move.data.price - (10 + position * 5);
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

            if (G.map.name == 'India') {
                G.citiesBuiltInCurrentRound!++;
            }

            if (G.options.variant == 'original') {
                if (G.actualMarket.length > 0 && player.cities.length >= G.actualMarket[0].number) {
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
                        G.coalSupply++;
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
                    let price: number;
                    switch (lastMove.data.resource) {
                        case ResourceType.Coal:
                            if (lastMove.fromSupply) {
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
                            player.oilLeft--;
                            G.oilMarket++;
                            const oilPrices = G.oilPrices ?? prices[ResourceType.Oil];
                            price = oilPrices[oilPrices.length - G.oilMarket];
                            break;
                        }

                        case ResourceType.Garbage: {
                            player.garbageLeft--;
                            G.garbageMarket++;
                            const garbagePrices = G.garbagePrices ?? prices[ResourceType.Garbage];
                            price = garbagePrices[garbagePrices.length - G.garbageMarket];
                            break;
                        }

                        case ResourceType.Uranium: {
                            player.uraniumLeft--;
                            G.uraniumMarket++;
                            const uraniumPrices = G.uraniumPrices ?? prices[ResourceType.Uranium];
                            price = uraniumPrices[uraniumPrices.length - G.uraniumMarket];
                            break;
                        }
                    }

                    player.money += price;

                    if (G.options.trackTotals) {
                        player.totalSpentResources -= price;
                    }

                    if (G.map.name == 'India') {
                        G.chosenResource = undefined;
                    }

                    G.log.pop();
                    break;
                }

                case MoveName.Build: {
                    player.cities.pop();
                    player.money += lastMove.data.price;

                    const position = G.players.filter((p) => p.cities.find((c) => c.name == lastMove.data.name)).length;

                    if (G.options.trackTotals) {
                        player.totalSpentCities -= 10 + position * 5;
                        player.totalSpentConnections -= lastMove.data.price - (10 + position * 5);
                    }

                    G.log.pop();

                    if (G.map.name == 'India') {
                        G.citiesBuiltInCurrentRound!--;
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
                chosenMove = { name: MoveName.DiscardPowerPlant, data: player.powerPlants[0].number };
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

        if (G.options.variant == 'original') {
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

        if (powerPlant.number == 99) {
            if (G.powerPlantDeckAfterStep3) {
                G.powerPlantsDeck = G.powerPlantDeckAfterStep3;
            } else {
                G.powerPlantsDeck = shuffle(G.powerPlantsDeck, G.seed);
            }

            if (G.phase != Phase.Auction) {
                if (G.map.name == 'Middle East' && G.step == 1) {
                    // Add step 3 card to market, then trigger step 2 process.
                    const market = [...G.actualMarket, ...G.futureMarket, powerPlant];
                    market.sort((a, b) => a.number - b.number);
                    G.actualMarket = market.splice(4);
                    G.futureMarket = market;
                    enterStepTwoMiddleEast(G);
                } else {
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

        const market = [...G.actualMarket, ...G.futureMarket, powerPlant];
        market.sort((a, b) => a.number - b.number);
        if (G.futureMarket.length == 0) {
            G.actualMarket = market.slice(0, 6);
            G.futureMarket = [];
        } else {
            G.actualMarket = market.slice(0, 4);
            G.futureMarket = market.slice(4);
        }

        if (G.map.name == 'Middle East' && G.step == 1) {
            removePlantsForMiddleEastStep1(G);
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
    return `<span style="background-color: ${playerColors[player.id]}; font-weight: bold; padding: 0 3px;">${
        player.name
    }</span>`;
}

export function playersSortedByScore(G: GameState): Player[] {
    console.log(G.players);
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
        player.citiesPowered = calculateMaxCitiesPowered(player);
    });
}

function calculateMaxCitiesPowered(player: Player) {
    const permutations: PowerPlant[][] = [];
    for (let i = 0; i < Math.pow(2, player.powerPlants.length); i++) {
        const perm: PowerPlant[] = [];
        player.powerPlants.forEach((pp, index) => {
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
    G.players.forEach((p) => {
        p.bid = 0;
        p.passed = p.isDropped;
    });

    G.players.forEach((p) => {
        p.skipAuction = false;
    });

    if (G.options.variant == 'recharged') {
        if (G.plantDiscountActive) {
            G.plantDiscountActive = false;
            if (G.actualMarket.length > 0) {
                G.log.push({ type: 'event', event: `Discarding Power Plant ${G.actualMarket[0].number}.` });
                G.actualMarket.shift();
                addPowerPlant(G);
            }
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

    if (G.options.trackTotals) {
        winningPlayer.totalSpentPlants += bid;
    }

    winningPlayer.skipAuction = true;
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
            (winningPlayer.powerPlants.length > 4 || (G.players.length > 2 && winningPlayer.powerPlants.length > 3)) &&
            !winningPlayer.isDropped
        ) {
            setCurrentPlayer(G, winningPlayer.id);
        } else {
            addPowerPlant(G);

            if (G.players.some((p) => !p.skipAuction)) {
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
