import assert from 'assert';
import { cloneDeep, isEqual, range } from 'lodash';
import seedrandom from 'seedrandom';
import { availableMoves } from './available-moves';
import { GameOptions, GameState, Phase, Player, PowerPlant, PowerPlantType, ResourceType } from './gamestate';
import { LogItem } from './log';
import { maps, mapsRecharged } from './maps';
import { Move, MoveName, Moves } from './move';
import powerPlants from './powerPlants';
import prices from './prices';
import { asserts, shuffle } from './utils';

export const playerColors = ['limegreen', 'mediumorchid', 'red', 'dodgerblue', 'yellow', 'brown'];

const coalResupply = [
    [3, 4, 3],
    [4, 5, 3],
    [5, 6, 4],
    [5, 7, 5],
    [7, 9, 6],
];
const oilResupply = [
    [2, 2, 4],
    [2, 3, 4],
    [3, 4, 5],
    [4, 5, 6],
    [5, 6, 7],
];
const garbageResupply = [
    [1, 2, 3],
    [1, 2, 3],
    [2, 3, 4],
    [3, 3, 5],
    [3, 5, 6],
];
const uraniumResupply = [
    [1, 1, 1],
    [1, 1, 1],
    [1, 2, 2],
    [2, 3, 2],
    [2, 3, 3],
];
const citiesToStep2 = [10, 7, 7, 7, 6];
const citiesToEndGame = [21, 17, 17, 15, 14];
const cityIncome = [10, 22, 33, 44, 54, 64, 73, 82, 90, 98, 105, 112, 118, 124, 129, 134, 138, 142, 145, 148, 150, 150];
const regionsInPlay = [3, 3, 4, 5, 5];

export function setup(
    numPlayers: number,
    { fastBid = false, map = 'USA', variant = 'original', showMoney = false }: GameOptions,
    seed?: string
): GameState {
    seed = seed ?? Math.random().toString();
    const rng = seedrandom(seed);

    let actualMarket: PowerPlant[];
    let futureMarket: PowerPlant[];

    let powerPlantsDeck = cloneDeep(powerPlants);
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
        }

        powerPlantsDeck.unshift(first);
        powerPlantsDeck.push(step3);
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
    }));

    const playerOrder = range(numPlayers);
    const startingPlayer = playerOrder[0];

    const chosenMap =
        variant == 'original' ? maps.find((m) => m.name == map)! : mapsRecharged.find((m) => m.name == map)!;

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
    while (playRegions.size != regionsInPlay[players.length - 2]) {
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

    const G: GameState = {
        map: filteredMap,
        players,
        playerOrder,
        currentPlayers: [startingPlayer],
        powerPlantsDeck,
        coalSupply: 0,
        oilSupply: 6,
        garbageSupply: variant == 'original' ? 18 : 15,
        uraniumSupply: 10,
        coalMarket: 24,
        oilMarket: 18,
        garbageMarket: variant == 'original' ? 6 : 9,
        uraniumMarket: 2,
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
    } as GameState;

    G.log.push({ type: 'event', event: 'Game Start!' });

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
                };
            }
        }),
        log: G.log,
    };
}

export function currentPlayers(G: GameState): number[] {
    return G.currentPlayers;
}

export function move(G: GameState, move: Move, playerNumber: number): GameState {
    const player = G.players[playerNumber];
    const available = player.availableMoves?.[move.name];

    assert(G.currentPlayers.includes(playerNumber), 'It is not your turn!');
    assert(available, 'You are not allowed to run the command ' + move.name);
    assert(
        available.some((x) => isEqual(x, move.data)),
        'Wrong argument for the command ' + move.name
    );

    switch (move.name) {
        case MoveName.ChoosePowerPlant: {
            asserts<Moves.MoveChoosePowerPlant>(move);

            G.chosenPowerPlant = getPowerPlant(move.data);

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
            } else {
                G.minimunBid = move.data;
            }

            const notPassed = G.players.filter((p) => !p.skipAuction);
            if (notPassed.length == 1) {
                G.log.push({
                    type: 'move',
                    player: playerNumber,
                    move,
                    simple: `${player.name} chooses Power Plant ${move.data}`,
                    pretty: `${playerNameHTML(player)} chooses Power Plant <b>${move.data}</b>`,
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
                    simple: `${player.name} chooses Power Plant ${move.data} to initiate an auction`,
                    pretty: `${playerNameHTML(player)} chooses Power Plant <b>${move.data}</b> to initiate an auction`,
                });
            }

            break;
        }

        case MoveName.Bid: {
            asserts<Moves.MoveBid>(move);

            G.currentBid = player.bid = move.data;

            G.log.push({
                type: 'move',
                player: playerNumber,
                move,
                simple: `${player.name} bids $${move.data}`,
                pretty: `${playerNameHTML(player)} bids <span style="color: green">$${move.data}</span>`,
            });

            nextPlayerClockwise(G);

            break;
        }

        case MoveName.Pass: {
            asserts<Moves.MovePass>(move);

            G.log.push({
                type: 'move',
                player: playerNumber,
                move,
                simple: `${player.name} passes`,
                pretty: `${playerNameHTML(player)} passes`,
            });

            switch (G.phase) {
                case Phase.Auction: {
                    if (G.chosenPowerPlant == undefined) {
                        player.skipAuction = true;
                        G.auctionSkips++;

                        if (G.players.some((p) => !p.skipAuction)) {
                            nextPlayerAuction(G);
                        } else {
                            if (G.auctionSkips == G.players.length) {
                                G.log.push({
                                    type: 'event',
                                    event: `Everyone passed, removing lowest numbered Power Plant (${G.actualMarket[0].number})`,
                                });
                                G.actualMarket.shift();
                                addPowerPlant(G);
                            }

                            toResourcesPhase(G);
                        }
                    } else {
                        player.passed = true;

                        const notPassed = G.players.filter((p) => !p.passed && !p.skipAuction);
                        if (notPassed.length == 1) {
                            const winningPlayer = notPassed[0];
                            endAuction(G, winningPlayer, winningPlayer.bid);

                            if (
                                winningPlayer.powerPlants.length > 4 ||
                                (G.players.length > 2 && winningPlayer.powerPlants.length > 3)
                            ) {
                                G.currentPlayers = [winningPlayer.id];
                            } else {
                                addPowerPlant(G);

                                if (G.players.some((p) => !p.skipAuction)) {
                                    G.players.forEach((p) => {
                                        p.bid = 0;
                                        p.passed = false;
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

                    break;
                }

                case Phase.Resources: {
                    player.passed = true;

                    if (G.players.filter((p) => !p.passed).length == 0) {
                        G.players.forEach((p) => {
                            p.passed = false;
                        });
                        G.phase = Phase.Building;
                        G.currentPlayers = [G.playerOrder[G.players.length - 1]];
                    } else {
                        nextPlayerReverse(G);
                    }

                    break;
                }

                case Phase.Building: {
                    player.passed = true;

                    if (G.players.filter((p) => !p.passed).length == 0) {
                        const maxCities = Math.max(...G.players.map((p) => p.cities.length));
                        if (G.step == 1) {
                            if (maxCities >= G.citiesToStep2) {
                                const powerPlant = G.actualMarket.shift()!;
                                G.log.push({
                                    type: 'event',
                                    event: `Starting Step 2, power plant ${powerPlant?.number} discarded`,
                                });
                                G.step = 2;
                                addPowerPlant(G);
                            }
                        }

                        if (maxCities >= G.citiesToEndGame) {
                            G.phase = Phase.GameEnd;
                            G.currentPlayers = [];
                            calculateCitiesPowered(G);
                            G.log.push({ type: 'event', event: 'Game Ended!' });
                        } else {
                            G.players.forEach((p) => {
                                p.passed = false;
                                p.powerPlantsNotUsed = p.powerPlants.map((pp) => pp.number);
                            });
                            G.phase = Phase.Bureaucracy;
                            G.currentPlayers = G.playerOrder;

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

                    player.money += G.paymentTable[Math.min(player.cities.length, player.citiesPowered)];
                    player.citiesPowered = 0;

                    if (G.players.filter((p) => !p.passed).length == 0) {
                        const coalResupplyValue = Math.min(
                            G.coalSupply,
                            coalResupply[G.players.length - 2][G.step - 1]
                        );
                        G.coalMarket += coalResupplyValue;
                        G.coalSupply -= coalResupplyValue;

                        const oilResupplyValue = Math.min(G.oilSupply, oilResupply[G.players.length - 2][G.step - 1]);
                        G.oilMarket += oilResupplyValue;
                        G.oilSupply -= oilResupplyValue;

                        const garbageResupplyValue = Math.min(
                            G.garbageSupply,
                            garbageResupply[G.players.length - 2][G.step - 1]
                        );
                        G.garbageMarket += garbageResupplyValue;
                        G.garbageSupply -= garbageResupplyValue;

                        let uraniumResupplyValue = 0;
                        if (G.options.variant != 'recharged' || G.options.map != 'Germany' || !G.card39Bought) {
                            uraniumResupplyValue = Math.min(
                                G.uraniumSupply,
                                uraniumResupply[G.players.length - 2][G.step - 1]
                            );
                            G.uraniumMarket += uraniumResupplyValue;
                            G.uraniumSupply -= uraniumResupplyValue;
                        }

                        G.log.push({
                            type: 'event',
                            event: `Resupplying resources: [${coalResupplyValue}, ${oilResupplyValue}, ${garbageResupplyValue}, ${uraniumResupplyValue}]`,
                        });

                        if (G.futureMarket.length > 0) {
                            const powerPlant = G.futureMarket.pop()!;
                            G.log.push({
                                type: 'event',
                                event: `Putting Power Plant ${powerPlant.number} on the bottom of the deck`,
                            });
                            G.powerPlantsDeck.push(powerPlant);
                        } else if (G.actualMarket.length > 0) {
                            G.log.push({ type: 'event', event: `Discarding Power Plant ${G.actualMarket[0].number}` });
                            G.actualMarket.shift();
                        }

                        addPowerPlant(G);

                        G.round++;

                        setPlayerOrder(G);

                        G.players.forEach((p) => {
                            p.passed = false;
                        });
                        G.auctionSkips = 0;

                        if (G.actualMarket.length > 0) {
                            G.phase = Phase.Auction;

                            if (G.futureMarket.length == 0) {
                                G.step = 3;
                            }

                            G.plantDiscountActive = G.options.variant == 'recharged';
                            G.currentPlayers = [G.playerOrder[0]];
                        } else {
                            toResourcesPhase(G);
                        }
                    } else {
                        G.currentPlayers = G.playerOrder.filter((p) => !G.players[p].passed);
                    }

                    break;
                }
            }

            break;
        }

        case MoveName.DiscardPowerPlant: {
            asserts<Moves.MoveDiscardPowerPlant>(move);

            player.powerPlants = player.powerPlants.filter((p) => p.number != move.data);

            updatePlayerCapacity(player);

            const toDiscard: ResourceType[] = [];
            let hybridCapacityUsed = player.hybridCapacity > 0 ? Math.max(0, player.oilLeft - player.oilCapacity) : 0;
            if (player.coalCapacity + player.hybridCapacity < player.coalLeft + hybridCapacityUsed) {
                toDiscard.push(ResourceType.Coal);
            }

            hybridCapacityUsed = player.hybridCapacity > 0 ? Math.max(0, player.coalLeft - player.coalCapacity) : 0;
            if (player.oilCapacity + player.hybridCapacity < player.oilLeft + hybridCapacityUsed) {
                toDiscard.push(ResourceType.Oil);
            }

            player.garbageLeft = Math.min(player.garbageLeft, player.garbageCapacity);
            player.uraniumLeft = Math.min(player.uraniumLeft, player.uraniumCapacity);

            if (toDiscard.length == 1) {
                if (toDiscard[0] == ResourceType.Coal) {
                    player.coalLeft = player.coalCapacity;
                } else if (toDiscard[0] == ResourceType.Oil) {
                    player.oilLeft = player.oilCapacity;
                }

                toDiscard.pop();
            }

            if (toDiscard.length == 0) {
                addPowerPlant(G);
                G.players.forEach((p) => {
                    p.bid = 0;
                    p.passed = false;
                });

                if (G.players.some((p) => !p.skipAuction)) {
                    nextPlayerAuction(G, true);
                } else {
                    toResourcesPhase(G);
                }
            }

            G.log.push({
                type: 'move',
                player: playerNumber,
                move,
                simple: `${player.name} discards Power Plant ${move.data}`,
                pretty: `${playerNameHTML(player)} discards Power Plant <b>${move.data}</b>`,
            });

            break;
        }

        case MoveName.DiscardResources: {
            asserts<Moves.MoveDiscardResources>(move);

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
                    p.passed = false;
                });

                if (G.players.some((p) => !p.skipAuction)) {
                    nextPlayerAuction(G, true);
                } else {
                    toResourcesPhase(G);
                }
            }

            G.log.push({
                type: 'move',
                player: playerNumber,
                move,
                simple: `${player.name} discarded a ${move.data}`,
                pretty: `${playerNameHTML(player)} discarded a <b>${move.data}</b>`,
            });

            break;
        }

        case MoveName.BuyResource: {
            asserts<Moves.MoveBuyResource>(move);

            let price;
            switch (move.data.resource) {
                case ResourceType.Coal:
                    if (G.coalMarket == 0) {
                        price = 8;
                        player.coalLeft++;
                        G.coalSupply--;
                    } else {
                        price = prices[move.data.resource][prices[move.data.resource].length - G.coalMarket];
                        player.coalLeft++;
                        G.coalMarket--;
                    }

                    break;

                case ResourceType.Oil:
                    price = prices[move.data.resource][prices[move.data.resource].length - G.oilMarket];
                    player.oilLeft++;
                    G.oilMarket--;
                    break;

                case ResourceType.Garbage:
                    price = prices[move.data.resource][prices[move.data.resource].length - G.garbageMarket];
                    player.garbageLeft++;
                    G.garbageMarket--;
                    break;

                case ResourceType.Uranium:
                    price = prices[move.data.resource][prices[move.data.resource].length - G.uraniumMarket];
                    player.uraniumLeft++;
                    G.uraniumMarket--;
                    break;
            }

            player.money -= price;

            G.log.push({
                type: 'move',
                player: playerNumber,
                move,
                simple: `${player.name} buys ${move.data.resource} for $${price}`,
                pretty: `${playerNameHTML(player)} buys <b>${
                    move.data.resource
                }</b> for <span style="color: green">$${price}</span>`,
            });

            break;
        }

        case MoveName.Build: {
            asserts<Moves.MoveBuild>(move);

            const position = G.players.filter((p) => p.cities.find((c) => c.name == move.data.name)).length;
            player.cities.push({ name: move.data.name, position });
            player.money -= move.data.price;

            if (G.options.variant == 'original') {
                if (G.actualMarket.length > 0 && player.cities.length >= G.actualMarket[0].number) {
                    G.actualMarket.shift();
                    addPowerPlant(G);
                }
            }

            G.log.push({
                type: 'move',
                player: playerNumber,
                move,
                simple: `${player.name} builds on ${move.data.name} for $${move.data.price}`,
                pretty: `${playerNameHTML(player)} builds on <b>${move.data.name}</b> for <span style="color: green">$${
                    move.data.price
                }</span>`,
            });

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
                simple: `${player.name} uses Power Plant ${move.data.powerPlant}`,
                pretty: `${playerNameHTML(player)} uses Power Plant <b>${move.data.powerPlant}</b>`,
            });

            break;
        }

        case MoveName.Undo: {
            asserts<Moves.MoveUndo>(move);

            const lastLog = G.log[G.log.length - 1];
            if (lastLog.type == 'move' && G.currentPlayers.includes(lastLog.player)) {
                G.log.pop();
                G = reconstructState(getBaseState(G), G.log);
            }

            return G;
        }
    }

    player.availableMoves = null;
    player.lastMove = move;

    G.cardsLeft = G.powerPlantsDeck.length;
    G.nextCardWeak = G.options.variant == 'recharged' && G.cardsLeft > 0 && G.powerPlantsDeck[0].number <= 15;

    G.currentPlayers.forEach((p) => (G.players[p].availableMoves = availableMoves(G, G.players[p])));

    console.log('deck', G.powerPlantsDeck);

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
                if (!availableMoves.Pass || (Math.random() > 0.5 && player.money - availableMoves?.Bid[0] >= 15)) {
                    chosenMove = { name: MoveName.Bid, data: availableMoves?.Bid[0] };
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

export function reconstructState(initialState: GameState, log: LogItem[]): GameState {
    const G = cloneDeep(initialState);

    for (const item of log) {
        switch (item.type) {
            case 'event': {
                break;
            }

            case 'phase': {
                break;
            }

            case 'move': {
                move(G, item.move, item.player);
                break;
            }
        }
    }

    return G;
}

export function nextPlayerClockwise(G: GameState) {
    const index = G.currentPlayers[0];
    G.currentPlayers = [(index + 1) % G.players.length];

    if (G.players[G.currentPlayers[0]].isDropped && G.players.some((p) => !p.isDropped)) {
        G.players[G.currentPlayers[0]].skipAuction = true;
        nextPlayerClockwise(G);
    }

    if (
        (G.players[G.currentPlayers[0]].skipAuction || G.players[G.currentPlayers[0]].passed) &&
        G.players.some((p) => !p.skipAuction && !p.passed)
    ) {
        nextPlayerClockwise(G);
    }
}

export function nextPlayerReverse(G: GameState) {
    const index = G.playerOrder.indexOf(G.currentPlayers[0]);
    G.currentPlayers = [G.playerOrder[(index - 1 + G.players.length) % G.players.length]];

    if (G.players[G.currentPlayers[0]].isDropped && G.players.some((p) => !p.isDropped)) nextPlayerReverse(G);
}

export function nextPlayerAuction(G: GameState, reset = false) {
    if (reset) {
        G.currentPlayers = [G.playerOrder[0]];
    } else {
        const index = G.playerOrder.indexOf(G.currentPlayers[0]);
        G.currentPlayers = [G.playerOrder[(index + 1) % G.players.length]];
    }

    if (G.players[G.currentPlayers[0]].isDropped && G.players.some((p) => !p.isDropped)) {
        G.players[G.currentPlayers[0]].skipAuction = true;
        nextPlayerAuction(G);
    }

    if (
        (G.players[G.currentPlayers[0]].skipAuction || G.players[G.currentPlayers[0]].passed) &&
        G.players.some((p) => !p.skipAuction && !p.passed)
    ) {
        nextPlayerAuction(G);
    }
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
                player.garbageCapacity += powerPlant.cost * 2;

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
        const maxCities = Math.max(...G.players.map((p) => p.cities.length));
        while (powerPlant.number <= maxCities) {
            G.log.push({
                type: 'event',
                event: `Power plant ${powerPlant?.number} discarded.`,
            });

            if (G.powerPlantsDeck.length > 0) {
                powerPlant = G.powerPlantsDeck.shift()!;
            } else {
                break;
            }
        }

        if (powerPlant.number == 99) {
            G.powerPlantsDeck = shuffle(G.powerPlantsDeck, G.seed);

            if (G.phase != Phase.Auction) {
                const powerPlantDiscarded = G.actualMarket.shift();
                G.log.push({
                    type: 'event',
                    event: `Step 3 will begin next phase, power plant ${powerPlantDiscarded?.number} discarded.`,
                });

                const market = [...G.actualMarket, ...G.futureMarket];
                market.sort((a, b) => a.number - b.number);
                G.actualMarket = market;
                G.futureMarket = [];
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
    }
}

function removePowerPlant(G: GameState, powerPlant: PowerPlant) {
    G.actualMarket.splice(
        G.actualMarket.findIndex((pp) => pp.number == powerPlant.number),
        1
    );
}

function getPowerPlant(num) {
    return powerPlants.find((p) => p.number == num)!;
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

export function playersSortedByScore(G: GameState) {
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
        player.citiesPowered = 0;

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

        player.citiesPowered = Math.min(player.cities.length, max);
    });
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
        p.passed = false;
    });

    G.players.forEach((p) => {
        p.skipAuction = false;
    });

    if (G.options.variant == 'recharged') {
        if (G.plantDiscountActive) {
            G.plantDiscountActive = false;
            if (G.actualMarket.length > 0) {
                G.log.push({ type: 'event', event: `Discarding Power Plant ${G.actualMarket[0].number}` });
                G.actualMarket.shift();
                addPowerPlant(G);
            }
        }
    }

    if (G.futureMarket.find((pp) => pp.number == 99)) {
        const powerPlantDiscarded = G.actualMarket.shift();
        G.futureMarket.pop();
        G.log.push({ type: 'event', event: `Starting Step 3, power plant ${powerPlantDiscarded?.number} discarded.` });
        G.step = 3;

        G.actualMarket = [...G.actualMarket, ...G.futureMarket];
        G.futureMarket = [];
    }

    G.phase = Phase.Resources;
    G.currentPlayers = [G.playerOrder[G.players.length - 1]];
}

function endAuction(G: GameState, winningPlayer: Player, bid: number) {
    winningPlayer.powerPlants.push(G.chosenPowerPlant!);
    winningPlayer.money -= bid;
    winningPlayer.skipAuction = true;
    updatePlayerCapacity(winningPlayer);

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
