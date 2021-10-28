import { range } from 'lodash';
import { GameState, Phase, Player, PowerPlantType, ResourceType } from './gamestate';
import { MoveName } from './move';
import prices from './prices';

export interface AvailableMoves {
    [MoveName.ChoosePowerPlant]?: number[];
    [MoveName.Bid]?: number[];
    [MoveName.DiscardPowerPlant]?: number[];
    [MoveName.DiscardResources]?: ResourceType[];
    [MoveName.BuyResource]?: {
        resource: ResourceType;
        price: number;
    }[];
    [MoveName.Build]?: { name: string; price: number }[];
    [MoveName.UsePowerPlant]?: {
        powerPlant: number;
        resourcesSpent: ResourceType[];
        citiesPowered: number;
    }[];
    [MoveName.Pass]?: boolean[];
    [MoveName.Undo]?: boolean[];
}

export function availableMoves(G: GameState, player: Player): AvailableMoves {
    const moves = {};

    const lastLog = G.log[G.log.length - 1];
    if (lastLog.type == 'move' && G.currentPlayers.includes(lastLog.player)) moves[MoveName.Undo] = [true];

    switch (G.phase) {
        case Phase.Auction: {
            if (player.powerPlants.length > 4 || (G.players.length > 2 && player.powerPlants.length > 3)) {
                moves[MoveName.DiscardPowerPlant] = player.powerPlants.map((pp) => pp.number);
            } else {
                const toDiscard: ResourceType[] = [];
                let hybridCapacityUsed = Math.max(0, player.oilLeft - player.oilCapacity);
                if (player.coalCapacity + player.hybridCapacity < player.coalLeft + hybridCapacityUsed) {
                    toDiscard.push(ResourceType.Coal);
                }

                hybridCapacityUsed = Math.max(0, player.coalLeft - player.coalCapacity);
                if (player.oilCapacity + player.hybridCapacity < player.oilLeft + hybridCapacityUsed) {
                    toDiscard.push(ResourceType.Oil);
                }

                if (player.garbageCapacity < player.garbageLeft) {
                    toDiscard.push(ResourceType.Garbage);
                }

                if (player.uraniumCapacity < player.uraniumLeft) {
                    toDiscard.push(ResourceType.Uranium);
                }

                if (toDiscard.length > 0) {
                    moves[MoveName.DiscardResources] = toDiscard;
                } else {
                    if (G.chosenPowerPlant == undefined) {
                        const canBid = G.actualMarket.filter((p) => player.money >= p.number);
                        if (canBid.length > 0) {
                            moves[MoveName.ChoosePowerPlant] = canBid.map((p) => p.number);
                        }

                        if (G.round > 1) {
                            moves[MoveName.Pass] = [true];
                        }
                    } else {
                        moves[MoveName.Bid] = range(
                            G.currentBid ? G.currentBid + 1 : G.chosenPowerPlant.number,
                            player.money + 1
                        );

                        if (G.currentBid != null) {
                            moves[MoveName.Pass] = [true];
                        }
                    }
                }
            }

            break;
        }

        case Phase.Resources: {
            const toBuy: { resource: ResourceType }[] = [];

            if (G.coalMarket > 0) {
                const hybridCapacityUsed =
                    player.hybridCapacity > 0 ? Math.max(0, player.oilLeft - player.oilCapacity) : 0;
                const price = prices[ResourceType.Coal][prices[ResourceType.Coal].length - G.coalMarket];
                if (
                    player.money >= price &&
                    player.coalCapacity + player.hybridCapacity > hybridCapacityUsed + player.coalLeft
                ) {
                    toBuy.push({ resource: ResourceType.Coal });
                }
            }

            if (G.oilMarket > 0) {
                const hybridCapacityUsed =
                    player.hybridCapacity > 0 ? Math.max(0, player.coalLeft - player.coalCapacity) : 0;
                const price = prices[ResourceType.Oil][prices[ResourceType.Oil].length - G.oilMarket];
                if (
                    player.money >= price &&
                    player.oilCapacity + player.hybridCapacity > hybridCapacityUsed + player.oilLeft
                ) {
                    toBuy.push({ resource: ResourceType.Oil });
                }
            }

            if (G.garbageMarket > 0) {
                const price = prices[ResourceType.Garbage][prices[ResourceType.Garbage].length - G.garbageMarket];
                if (player.money >= price && player.garbageCapacity > player.garbageLeft) {
                    toBuy.push({ resource: ResourceType.Garbage });
                }
            }

            if (G.uraniumMarket > 0) {
                const price = prices[ResourceType.Uranium][prices[ResourceType.Uranium].length - G.uraniumMarket];
                if (player.money >= price && player.uraniumCapacity > player.uraniumLeft) {
                    toBuy.push({ resource: ResourceType.Uranium });
                }
            }

            if (toBuy.length > 0) {
                moves[MoveName.BuyResource] = toBuy;
            }

            moves[MoveName.Pass] = [true];

            break;
        }

        case Phase.Building: {
            if (player.cities.length < 21) {
                let toBuild =
                    player.cities.length == 0
                        ? G.map.cities.map((c) => ({ name: c.name, price: 0 }))
                        : dijkstra(G, player).map((c) => ({ name: c.name, price: c.price }));

                toBuild.forEach((city) => {
                    const othersCount = G.players.filter((p) => p.cities.find((c) => city.name == c.name)).length;
                    city.price += 10 + othersCount * 5;

                    if (G.step == 1) {
                        if (othersCount > 0) {
                            city.price = 9999;
                        }
                    } else if (G.step == 2) {
                        if (othersCount > 1) {
                            city.price = 9999;
                        }
                    }

                    if (player.cities.find((c) => c.name == city.name)) {
                        city.price = 9999;
                    }
                });

                toBuild = toBuild.filter((c) => c.price <= player.money);

                if (toBuild.length > 0) {
                    moves[MoveName.Build] = toBuild;
                }
            }

            moves[MoveName.Pass] = [true];

            break;
        }

        case Phase.Bureaucracy: {
            const toUse: { powerPlant: number; resourcesSpent: ResourceType[]; citiesPowered: number }[] = [];

            player.powerPlants.forEach((powerPlant) => {
                if (player.powerPlantsNotUsed.includes(powerPlant.number)) {
                    switch (powerPlant.type) {
                        case PowerPlantType.Coal: {
                            if (player.coalLeft >= powerPlant.cost) {
                                toUse.push({
                                    powerPlant: powerPlant.number,
                                    resourcesSpent: new Array(powerPlant.cost).fill(ResourceType.Coal),
                                    citiesPowered: powerPlant.citiesPowered,
                                });
                            }

                            break;
                        }

                        case PowerPlantType.Oil: {
                            if (player.oilLeft >= powerPlant.cost) {
                                toUse.push({
                                    powerPlant: powerPlant.number,
                                    resourcesSpent: new Array(powerPlant.cost).fill(ResourceType.Oil),
                                    citiesPowered: powerPlant.citiesPowered,
                                });
                            }

                            break;
                        }

                        case PowerPlantType.Garbage: {
                            if (player.garbageLeft >= powerPlant.cost) {
                                toUse.push({
                                    powerPlant: powerPlant.number,
                                    resourcesSpent: new Array(powerPlant.cost).fill(ResourceType.Garbage),
                                    citiesPowered: powerPlant.citiesPowered,
                                });
                            }

                            break;
                        }

                        case PowerPlantType.Uranium: {
                            if (player.uraniumLeft >= powerPlant.cost) {
                                toUse.push({
                                    powerPlant: powerPlant.number,
                                    resourcesSpent: new Array(powerPlant.cost).fill(ResourceType.Uranium),
                                    citiesPowered: powerPlant.citiesPowered,
                                });
                            }

                            break;
                        }

                        case PowerPlantType.Wind:
                        case PowerPlantType.Nuclear:
                            toUse.push({
                                powerPlant: powerPlant.number,
                                resourcesSpent: [],
                                citiesPowered: powerPlant.citiesPowered,
                            });

                            break;

                        case PowerPlantType.Hybrid: {
                            if (player.coalLeft + player.oilLeft >= powerPlant.cost) {
                                let resourcesSpentArr: ResourceType[][];
                                if (powerPlant.cost == 1) {
                                    resourcesSpentArr = [[ResourceType.Coal], [ResourceType.Oil]];
                                } else if (powerPlant.cost == 2) {
                                    resourcesSpentArr = [
                                        [ResourceType.Coal, ResourceType.Coal],
                                        [ResourceType.Coal, ResourceType.Oil],
                                        [ResourceType.Oil, ResourceType.Oil],
                                    ];
                                } else {
                                    resourcesSpentArr = [
                                        [ResourceType.Coal, ResourceType.Coal, ResourceType.Coal],
                                        [ResourceType.Coal, ResourceType.Coal, ResourceType.Oil],
                                        [ResourceType.Coal, ResourceType.Oil, ResourceType.Oil],
                                        [ResourceType.Oil, ResourceType.Oil, ResourceType.Oil],
                                    ];
                                }

                                resourcesSpentArr.forEach((resourcesSpent) => {
                                    if (
                                        resourcesSpent.filter((r) => r == ResourceType.Coal).length <=
                                            player.coalLeft &&
                                        resourcesSpent.filter((r) => r == ResourceType.Oil).length <= player.oilLeft
                                    ) {
                                        toUse.push({
                                            powerPlant: powerPlant.number,
                                            resourcesSpent: resourcesSpent,
                                            citiesPowered: powerPlant.citiesPowered,
                                        });
                                    }
                                });
                            }
                        }
                    }
                }
            });

            if (toUse.length > 0) {
                moves[MoveName.UsePowerPlant] = toUse;
            }

            moves[MoveName.Pass] = [true];

            break;
        }
    }

    return moves;
}

function dijkstra(G: GameState, player: Player): { name: string; price: number }[] {
    const nodes = G.map.cities.map((c) => ({
        name: c.name,
        price: player.cities.find((city) => city.name == c.name) ? 0 : 9999,
        visited: false,
    }));

    let currentNode = nodes.find((n) => n.name == player.cities[0].name)!;
    currentNode.price = 0;

    while (nodes.some((n) => !n.visited)) {
        const currentConnections = G.map.connections.filter((c) => c.nodes.includes(currentNode.name));
        currentConnections.forEach((connection) => {
            const otherName = connection.nodes.filter((n) => n != currentNode.name)[0];
            const otherNode = nodes.find((n) => n.name == otherName)!;
            const price = player.cities.find((c) => c.name == otherNode.name) ? 0 : currentNode.price + connection.cost;
            if (!otherNode.visited && otherNode.price > price) {
                otherNode.price = price;
            }
        });

        currentNode.visited = true;

        if (!nodes.some((n) => !n.visited)) {
            break;
        }

        currentNode = nodes.reduce((a, b) => {
            if (a.visited) {
                return b;
            }

            if (b.visited) {
                return a;
            }

            if (a.price <= b.price) {
                return a;
            }

            return b;
        });

        if (currentNode.price > player.money) {
            break;
        }
    }

    return nodes;
}
