import assert from 'assert';
import { cloneDeep, isEqual, range } from 'lodash';
import seedrandom from 'seedrandom';
import { availableMoves } from './available-moves';
import powerPlants from './powerPlants';
import map from './map';
import { GameOptions, GameState, Phase, Player, ResourceType } from './gamestate';
import { GameEventName, LogItem } from './log';
import { Move, MoveName, Moves } from './move';
import { asserts, shuffle } from './utils';

const playerColors = ['dodgerblue', 'red', 'yellow', 'limegreen', 'mediumorchid'];

export function setup(numPlayers: number, { fastBid = false }: GameOptions, seed?: string): GameState {
    seed = seed ?? Math.random().toString();
    const rng = seedrandom(seed);

    let powerPlantsDeck = cloneDeep(powerPlants);
    powerPlantsDeck = powerPlantsDeck.slice(8);
    const powerPlant13 = powerPlantsDeck.splice(2, 1)[0];
    powerPlantsDeck = shuffle(powerPlantsDeck, rng() + '');
    if (numPlayers == 2 || numPlayers == 3) {
        powerPlantsDeck = powerPlantsDeck.slice(8);
    } else if (numPlayers == 4) {
        powerPlantsDeck = powerPlantsDeck.slice(4);
    }

    powerPlantsDeck.unshift(powerPlant13);

    const players: Player[] = range(numPlayers).map((id) => ({
        id,
        powerPlants: [],
        coalCapacity: 0, coalLeft: 0,
        oilCapacity: 0, oilLeft: 0,
        garbageCapacity: 0, garbageLeft: 0,
        uraniumCapacity: 0, uraniumLeft: 0,
        money: 50,
        housesLeft: 22,
        cities: [],
        powerPlantsUsed: [],
        availableMoves: null,
        lastMove: null,
        isDropped: false,
        isAI: false,
        bid: 0,
        passed: false,
        skipAuction: false,
        citiesPowered: 0
    }));

    const playerOrder = shuffle(range(numPlayers), rng() + '');
    const startingPlayer = playerOrder[0];

    const G: GameState = {
        map,
        players,
        playerOrder,
        currentPlayers: [startingPlayer],
        powerPlantsDeck,
        coalSupply: 0,
        oilSupply: 6,
        garbageSupply: 18,
        uraniumSupply: 10,
        coalMarket: 24,
        oilMarket: 18,
        garbageMarket: 6,
        uraniumMarket: 2,
        actualMarket: [3, 4, 5, 6],
        futureMarket: [7, 8, 9, 10],
        chosenPowerPlant: 0,
        currentBid: 0,
        highestBidders: [],
        auctioningPlayer: undefined,
        step: 1,
        phase: Phase.Auction,
        options: { fastBid },
        log: [],
        hiddenLog: [],
        seed,
        round: 1,
        auctionSkips: 0
    } as GameState;

    G.log.push({ type: 'event', event: { name: GameEventName.GameStart } });

    G.players[startingPlayer].availableMoves = availableMoves(G, G.players[startingPlayer]);

    return G;
}

export function stripSecret(G: GameState, player?: number): GameState {
    return {
        ...G,
        seed: 'secret',
        hiddenLog: [],
        players: G.players.map((pl, i) => {
            if (player === i) {
                return pl;
            } else {
                return {
                    ...pl,
                    availableMoves: pl.availableMoves ? {} : null,
                    money: ended(G) ? pl.money : 0
                };
            }
        }),
        log: G.log,
    };
}

export function currentPlayers(G: GameState): number[] {
    return G.currentPlayers;
}

export function move(G: GameState, move: Move, playerNumber: number, fake?: boolean): GameState {
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

            G.chosenPowerPlant = move.data.powerPlant;
            G.currentBid = player.bid = move.data.startingPrice;

            G.log.push({
                type: 'move',
                player: playerNumber,
                move,
                simple: `${player.name} chooses power plant ${move.data.powerPlant} to initiate an auction`,
                pretty: `${playerNameHTML(player)} chooses power plant ${move.data.powerPlant} to initiate an auction`,
            });

            break;
        }

        case MoveName.Bid: {
            asserts<Moves.MoveBid>(move);

            G.currentBid = player.bid = move.data.price;

            G.log.push({
                type: 'move',
                player: playerNumber,
                move,
                simple: `${player.name} bids $${move.data.price}`,
                pretty: `${playerNameHTML(player)} bids ${move.data.price}`,
            });

            nextPlayerAuction(G);

            break;
        }

        case MoveName.Pass: {
            asserts<Moves.MovePass>(move);

            switch (G.phase) {
                case Phase.Auction: {
                    if (G.chosenPowerPlant == 0) {
                        player.skipAuction = true;
                        G.auctionSkips++;

                        if (G.players.some(p => !p.skipAuction)) {
                            nextPlayerAuction(G);
                        } else {
                            if (G.auctionSkips == G.players.length) {
                                G.actualMarket.shift();
                                addPowerPlant(G);
                            }

                            G.phase = Phase.Resources;
                            G.currentPlayers = [G.playerOrder[G.players.length - 1]];
                        }
                    } else {
                        player.passed = true;

                        const notPassed = G.players.filter(p => !p.passed && !p.skipAuction);
                        if (notPassed.length == 1) {
                            const winningPlayer = notPassed[0];
                            winningPlayer.powerPlants.push(powerPlants.find(p => p.number == G.chosenPowerPlant)!);
                            winningPlayer.money -= winningPlayer.bid;
                            winningPlayer.skipAuction = true;

                            if (winningPlayer.powerPlants.length > 4 || (G.players.length > 2 && winningPlayer.powerPlants.length > 3)) {
                                G.currentPlayers = [winningPlayer.id];
                            } else {
                                if (G.players.some(p => !p.skipAuction)) {
                                    nextPlayerAuction(G);

                                    G.chosenPowerPlant = G.currentBid = 0;
                                    G.players.forEach(p => { p.bid = 0; p.passed = false; });
                                } else {
                                    G.phase = Phase.Resources;
                                    G.currentPlayers = [G.playerOrder[G.players.length - 1]];
                                }
                            }
                        } else {
                            nextPlayerAuction(G);
                        }
                    }

                    break;
                }

                case Phase.Resources: {
                    break;
                }

                case Phase.Building: {
                    break;
                }

                case Phase.Bureaucracy: {
                    break;
                }
            }

            G.log.push({
                type: 'move',
                player: playerNumber,
                move,
                simple: `${player.name} passes`,
                pretty: `${playerNameHTML(player)} passes`,
            });

            break;
        }

        case MoveName.DiscardPowerPlant: {
            asserts<Moves.MoveDiscardPowerPlant>(move);

            player.powerPlants = player.powerPlants.filter(p => p.number != move.data.powerPlant);

            if (player.coalCapacity >= player.coalLeft &&
                player.oilCapacity >= player.oilLeft &&
                player.garbageCapacity >= player.garbageLeft &&
                player.uraniumCapacity >= player.uraniumLeft) {
                if (G.players.some(p => !p.skipAuction)) {
                    nextPlayerAuction(G);

                    G.chosenPowerPlant = G.currentBid = 0;
                    G.players.forEach(p => { p.bid = 0; p.passed = false; });
                } else {
                    G.phase = Phase.Resources;
                    G.currentPlayers = [G.playerOrder[G.players.length - 1]];
                }
            }

            G.log.push({
                type: 'move',
                player: playerNumber,
                move,
                simple: `${player.name} discards power plant ${move.data.powerPlant}`,
                pretty: `${playerNameHTML(player)} discards power plant ${move.data.powerPlant}`,
            });

            break;
        }

        case MoveName.DiscardResources: {
            asserts<Moves.MoveDiscardResources>(move);

            let discardedCoal = 0;
            let discardedOil = 0;
            move.data.resourcesDiscarded.forEach(resource => {
                switch (resource) {
                    case ResourceType.Coal:
                        player.coalLeft--;
                        G.coalSupply++;
                        discardedCoal++;
                        break;

                    case ResourceType.Oil:
                        player.oilLeft--;
                        G.oilSupply++;
                        discardedOil++;
                        break;
                }
            });

            if (G.players.some(p => !p.skipAuction)) {
                nextPlayerAuction(G);

                G.chosenPowerPlant = G.currentBid = 0;
                G.players.forEach(p => { p.bid = 0; p.passed = false; });
            } else {
                G.phase = Phase.Resources;
                G.currentPlayers = [G.playerOrder[G.players.length - 1]];
            }

            let discardedStr = '';
            if (discardedOil == 0) {
                discardedStr = `${discardedCoal} coal`;
            } else {
                if (discardedCoal == 0) {
                    discardedStr = `${discardedOil} oil`;
                } else {
                    discardedStr = `${discardedCoal} coal and ${discardedOil} oil`;
                }
            }

            G.log.push({
                type: 'move',
                player: playerNumber,
                move,
                simple: `${player.name} discards resources: ${discardedStr}`,
                pretty: `${playerNameHTML(player)} discards resources: ${discardedStr}`,
            });

            break;
        }

        case MoveName.BuyResource: {
            asserts<Moves.MoveBuyResource>(move);
            switch (move.data.resource) {
                case ResourceType.Coal:
                    player.coalLeft++;
                    G.coalMarket--;
                    break;

                case ResourceType.Oil:
                    player.oilLeft++;
                    G.oilMarket--;
                    break;

                case ResourceType.Garbage:
                    player.garbageLeft++;
                    G.garbageMarket--;
                    break;

                case ResourceType.Uranium:
                    player.uraniumLeft++;
                    G.uraniumMarket--;
                    break;
            }

            player.money -= move.data.price;

            G.log.push({
                type: 'move',
                player: playerNumber,
                move,
                simple: `${player.name} buys ${move.data.resource} for ${move.data.price}`,
                pretty: `${playerNameHTML(player)} buys ${move.data.resource} for ${move.data.price}`,
            });

            break;
        }

        case MoveName.Build: {
            asserts<Moves.MoveBuild>(move);
            break;
        }

        case MoveName.UsePowerPlant: {
            asserts<Moves.MoveUsePowerPlant>(move);
            break;
        }

        case MoveName.Undo: {
            asserts<Moves.MoveUndo>(move);

            const lastLog = G.log[G.log.length - 1];
            if (lastLog.type == 'move' && G.currentPlayers.includes(lastLog.player) && !fake) {
                G.log.pop();
                G = reconstructState(getBaseState(G), G.log);
            }

            return G;
        }
    }

    player.availableMoves = null;
    player.lastMove = move;

    G.currentPlayers.forEach((p) => (G.players[p].availableMoves = availableMoves(G, G.players[p])));

    return G;
}

export function moveAI(G: GameState, playerNumber: number): GameState {
    return move(G, { name: MoveName.Pass, data: true }, playerNumber);
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

export function nextPlayer(G: GameState) {
    const index = G.playerOrder.indexOf(G.currentPlayers[0]);
    G.currentPlayers = [G.playerOrder[(index + 1) % G.players.length]];

    if (G.players[G.currentPlayers[0]].isDropped && G.players.some((p) => !p.isDropped)) nextPlayer(G);
}

export function nextPlayerReverse(G: GameState) {
    const index = G.playerOrder.indexOf(G.currentPlayers[0]);
    G.currentPlayers = [G.playerOrder[(index - 1 + G.players.length) % G.players.length]];

    if (G.players[G.currentPlayers[0]].isDropped && G.players.some((p) => !p.isDropped)) nextPlayerReverse(G);
}

export function nextPlayerAuction(G: GameState) {
    const index = G.playerOrder.indexOf(G.currentPlayers[0]);
    G.currentPlayers = [G.playerOrder[(index + 1) % G.players.length]];

    if (G.players[G.currentPlayers[0]].isDropped && G.players.some((p) => !p.isDropped)) {
        G.players[G.currentPlayers[0]].skipAuction = true;
        nextPlayerAuction(G);
    }

    if (G.players[G.currentPlayers[0]].skipAuction && G.players.some((p) => !p.skipAuction)) {
        nextPlayerAuction(G);
    }
}

function addPowerPlant(G: GameState) {
    const powerPlant = G.powerPlantsDeck.shift()!;
    const market = [...G.actualMarket, ...G.futureMarket, powerPlant.number];
    market.sort();
    if (G.step == 3) {
        G.actualMarket = market;
    } else {
        G.actualMarket = market.slice(0, 4);
        G.futureMarket = market.slice(4);
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
    return `<span style="background-color: ${playerColors[player.id]}; font-weight: bold; padding: 0 3px;">${player.name
        }</span>`;
}