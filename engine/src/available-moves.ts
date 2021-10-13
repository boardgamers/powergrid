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
    [MoveName.Build]?: string[];
    [MoveName.UsePowerPlant]?: {
        powerPlant: number;
        resourcesSpent: ResourceType[];
        citiesPowered: number;
    }[];
    [MoveName.Pass]?: boolean[];
    [MoveName.Undo]?: boolean[];
}

export function availableMoves(G: GameState, player: Player): AvailableMoves {
    const moves = {
        [MoveName.Undo]: [true]
    };

    switch (G.phase) {
        case Phase.Auction: {
            if (player.powerPlants.length > 4 || (G.players.length > 2 && player.powerPlants.length > 3)) {
                moves[MoveName.DiscardPowerPlant] = player.powerPlants;
            } else {
                const toDiscard: ResourceType[] = []
                if (player.coalCapacity < player.coalLeft) {
                    toDiscard.push(ResourceType.Coal);
                }

                if (player.oilCapacity < player.oilLeft) {
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
                    if (G.chosenPowerPlant == null) {
                        moves[MoveName.ChoosePowerPlant] = G.actualMarket;
                    } else {
                        moves[MoveName.Bid] = range(G.currentBid, player.money + 1);

                        if (G.currentBid != null) {
                            moves[MoveName.Pass] = [true];
                        }
                    }
                }
            }

            break;
        }

        case Phase.Resources: {
            const toBuy: { resource: ResourceType; price: number; }[] = [];

            if (G.coalMarket > 0) {
                const price = prices[ResourceType.Coal][prices[ResourceType.Coal].length - G.coalMarket];
                if (player.money >= price) {
                    toBuy.push({ resource: ResourceType.Coal, price });
                }
            }

            if (G.oilMarket > 0) {
                const price = prices[ResourceType.Oil][prices[ResourceType.Oil].length - G.oilMarket];
                if (player.money >= price) {
                    toBuy.push({ resource: ResourceType.Oil, price });
                }
            }

            if (G.garbageMarket > 0) {
                const price = prices[ResourceType.Garbage][prices[ResourceType.Garbage].length - G.garbageMarket];
                if (player.money >= price) {
                    toBuy.push({ resource: ResourceType.Garbage, price });
                }
            }

            if (G.uraniumMarket > 0) {
                const price = prices[ResourceType.Uranium][prices[ResourceType.Uranium].length - G.uraniumMarket];
                if (player.money >= price) {
                    toBuy.push({ resource: ResourceType.Uranium, price });
                }
            }

            if (toBuy.length > 0) {
                moves[MoveName.BuyResource] = toBuy;
            }

            moves[MoveName.Pass] = [true];

            break;
        }

        case Phase.Building: {
            let toBuild = player.cities.length == 0 ?
                G.map.cities.map(c => ({ name: c.name, price: 10 })) :
                dijkstra(G, player);

            toBuild = toBuild.filter(c => c.price <= player.money);

            if (toBuild.length > 0) {
                moves[MoveName.Build] = toBuild;
            }

            moves[MoveName.Pass] = [true];

            break;
        }

        case Phase.Bureaucracy: {
            const toUse: { powerPlant: number; resourcesSpent: ResourceType[]; citiesPowered: number; }[] = [];

            player.powerPlants.forEach(powerPlant => {
                if (!player.powerPlantsUsed.includes(powerPlant.number)) {
                    switch (powerPlant.type) {
                        case PowerPlantType.Coal: {
                            if (player.coalLeft >= powerPlant.cost) {
                                toUse.push({
                                    powerPlant: powerPlant.number,
                                    resourcesSpent: new Array(powerPlant.cost).fill(ResourceType.Coal),
                                    citiesPowered: powerPlant.citiesPowered
                                });
                            }
                        }

                        case PowerPlantType.Oil: {
                            if (player.oilLeft >= powerPlant.cost) {
                                toUse.push({
                                    powerPlant: powerPlant.number,
                                    resourcesSpent: new Array(powerPlant.cost).fill(ResourceType.Oil),
                                    citiesPowered: powerPlant.citiesPowered
                                });
                            }
                        }

                        case PowerPlantType.Garbage: {
                            if (player.garbageLeft >= powerPlant.cost) {
                                toUse.push({
                                    powerPlant: powerPlant.number,
                                    resourcesSpent: new Array(powerPlant.cost).fill(ResourceType.Garbage),
                                    citiesPowered: powerPlant.citiesPowered
                                });
                            }
                        }

                        case PowerPlantType.Uranium: {
                            if (player.uraniumLeft >= powerPlant.cost) {
                                toUse.push({
                                    powerPlant: powerPlant.number,
                                    resourcesSpent: new Array(powerPlant.cost).fill(ResourceType.Uranium),
                                    citiesPowered: powerPlant.citiesPowered
                                });
                            }
                        }

                        case PowerPlantType.Wind:
                        case PowerPlantType.Nuclear:
                            toUse.push({
                                powerPlant: powerPlant.number,
                                resourcesSpent: [],
                                citiesPowered: powerPlant.citiesPowered
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
                                        [ResourceType.Oil, ResourceType.Oil]
                                    ];
                                } else {
                                    resourcesSpentArr = [
                                        [ResourceType.Coal, ResourceType.Coal, ResourceType.Coal],
                                        [ResourceType.Coal, ResourceType.Coal, ResourceType.Oil],
                                        [ResourceType.Coal, ResourceType.Oil, ResourceType.Oil],
                                        [ResourceType.Oil, ResourceType.Oil, ResourceType.Oil]
                                    ];
                                }

                                resourcesSpentArr.forEach(resourcesSpent => {
                                    if (resourcesSpent.filter(r => r == ResourceType.Coal).length <= player.coalLeft &&
                                        resourcesSpent.filter(r => r == ResourceType.Oil).length <= player.oilLeft) {
                                        toUse.push({
                                            powerPlant: powerPlant.number,
                                            resourcesSpent: resourcesSpent,
                                            citiesPowered: powerPlant.citiesPowered
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

function dijkstra(G: GameState, player: Player): { name: string; price: number; }[] {
    const nodes = G.map.cities.map(c => ({ name: c.name, price: 0, visited: false }));

    let currentNode = nodes.find(n => n.name == player.cities[0].name)!;
    currentNode.price = 0;

    while (true) {
        const currentConnections = G.map.connections.filter(c => c.to == currentNode.name || c.from == currentNode.name);
        currentConnections.forEach(connection => {
            const otherNode = nodes.find(n => connection.to == currentNode.name ? n.name == connection.from : n.name == connection.to)!;
            const price = player.cities.find(c => c.name == otherNode.name) ? 0 : currentNode.price + connection.cost;
            if (!otherNode.visited || otherNode.price > price) {
                otherNode.price = price;
            }
        });

        currentNode.visited = true;

        if (!nodes.some(n => !n.visited)) {
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