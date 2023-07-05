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
    if (lastLog.type == 'move' && G.currentPlayers.includes(player.id)) {
        if (lastLog.player == player.id && player.lastMove?.name != MoveName.Pass) {
            moves[MoveName.Undo] = [true, false];
        } else if (G.phase == Phase.Bureaucracy && player.lastMove?.name == MoveName.UsePowerPlant) {
            moves[MoveName.Undo] = [true, false];
        }
    }

    switch (G.phase) {
        case Phase.Auction: {
            if (player.powerPlants.length > 4 || (G.players.length > 2 && player.powerPlants.length > 3)) {
                moves[MoveName.DiscardPowerPlant] = player.powerPlants
                    .filter((_, i) => i != player.powerPlants.length - 1)
                    .map((pp) => pp.number);
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
                        let canBid = G.actualMarket.filter((p) => player.money >= p.number);

                        // No nuclear plants for Portugal
                        if (G.map.name == 'Spain & Portugal') {
                            const playerCities = player.cities.map(
                                (c) => G.map.cities.find((c_) => c_.name == c.name)!
                            );
                            if (playerCities.every((c) => c.region == 'yellow')) {
                                canBid = canBid.filter((p) => p.type != PowerPlantType.Uranium);
                            }
                        }

                        // Nuclear plants for Central Europe are only allowed for players with cities in:
                        // Czechia (green), Slovakia (brown), Hungary (purple)
                        if (G.map.name == 'Central Europe') {
                            const validCities = player.cities
                                .map((c) => G.map.cities.find((c_) => c_.name == c.name)!)
                                .filter((c) => c.region == 'green' || c.region == 'brown' || c.region == 'purple');

                            if (validCities.length == 0) {
                                canBid = canBid.filter((p) => p.type != PowerPlantType.Uranium);
                            }
                        }

                        if (canBid.length > 0) {
                            moves[MoveName.ChoosePowerPlant] = canBid.map((p) => p.number);
                        }

                        if (G.round > 1) {
                            moves[MoveName.Pass] = [true];
                        }
                    } else {
                        if (G.options.fastBid) {
                            if (G.minimunBid <= player.money) {
                                moves[MoveName.Bid] = range(G.minimunBid, player.money + 1);
                            }
                        } else {
                            if (G.currentBid) {
                                if (G.currentBid < player.money) {
                                    moves[MoveName.Bid] = range(G.currentBid + 1, player.money + 1);
                                }
                            } else {
                                moves[MoveName.Bid] = range(G.minimunBid, player.money + 1);
                            }
                        }

                        // No nuclear plants for Portugal
                        if (G.map.name == 'Spain & Portugal') {
                            const playerCities = player.cities.map(
                                (c) => G.map.cities.find((c_) => c_.name == c.name)!
                            );
                            if (
                                playerCities.every((c) => c.region == 'yellow') &&
                                G.chosenPowerPlant.type == PowerPlantType.Uranium
                            ) {
                                moves[MoveName.Bid] = undefined;
                            }
                        }

                        if (G.options.fastBid) {
                            if (player.id != G.auctioningPlayer) {
                                moves[MoveName.Pass] = [true];
                            }
                        } else {
                            if (G.currentBid != null) {
                                moves[MoveName.Pass] = [true];
                            }
                        }
                    }
                }
            }

            break;
        }

        case Phase.Resources: {
            if (G.map.name == 'India' && G.chosenResource !== undefined) {
                moves[MoveName.Pass] = [true];
                break;
            }

            const toBuy: { resource: ResourceType }[] = [];
            let maxPriceAvailable: number;
            if (G.map.maxPriceAvailable) {
                maxPriceAvailable = G.map.maxPriceAvailable[G.step - 1];
            } else {
                maxPriceAvailable = 16;
            }

            if (G.coalMarket > 0) {
                const hybridCapacityUsed =
                    player.hybridCapacity > 0 ? Math.max(0, player.oilLeft - player.oilCapacity) : 0;
                const coalPrices = G.coalPrices ?? prices[ResourceType.Coal];
                const price = coalPrices[coalPrices.length - G.coalMarket];

                if (
                    player.money >= price &&
                    player.coalCapacity + player.hybridCapacity > hybridCapacityUsed + player.coalLeft &&
                    price <= maxPriceAvailable
                ) {
                    toBuy.push({ resource: ResourceType.Coal });
                }
            } else {
                if (G.options.variant == 'recharged' && G.map.name == 'USA' && G.coalSupply > 0) {
                    const hybridCapacityUsed =
                        player.hybridCapacity > 0 ? Math.max(0, player.oilLeft - player.oilCapacity) : 0;
                    if (
                        player.money >= 8 &&
                        player.coalCapacity + player.hybridCapacity > hybridCapacityUsed + player.coalLeft
                    ) {
                        toBuy.push({ resource: ResourceType.Coal });
                    }
                }
            }

            if (G.oilMarket > 0) {
                const hybridCapacityUsed =
                    player.hybridCapacity > 0 ? Math.max(0, player.coalLeft - player.coalCapacity) : 0;
                const oilPrices = G.oilPrices ?? prices[ResourceType.Oil];
                const price = oilPrices[oilPrices.length - G.oilMarket];

                if (
                    player.money >= price &&
                    player.oilCapacity + player.hybridCapacity > hybridCapacityUsed + player.oilLeft &&
                    price <= maxPriceAvailable
                ) {
                    toBuy.push({ resource: ResourceType.Oil });
                }
            }

            if (G.garbageMarket > 0) {
                const garbagePrices = G.garbagePrices ?? prices[ResourceType.Garbage];
                let price = garbagePrices[garbagePrices.length - G.garbageMarket];

                // $1 cheaper for players in Wien in Central Europe
                if (G.map.name == 'Central Europe') {
                    const wienCity = player.cities.filter((c) => c.name == 'Wien');
                    if (wienCity?.length > 0) {
                        price--;
                    }
                }

                if (
                    player.money >= price &&
                    player.garbageCapacity > player.garbageLeft &&
                    price <= maxPriceAvailable
                ) {
                    toBuy.push({ resource: ResourceType.Garbage });
                }
            }

            if (G.uraniumMarket > 0) {
                const uraniumPrices = G.uraniumPrices ?? prices[ResourceType.Uranium];
                const price = uraniumPrices[uraniumPrices.length - G.uraniumMarket];
                if (
                    player.money >= price &&
                    player.uraniumCapacity > player.uraniumLeft &&
                    price <= maxPriceAvailable
                ) {
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

                    if (othersCount == G.step) {
                        city.price = 9999;
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

            // For India map, players must power as many cities as possible.
            if (G.map.name != 'India' || player.citiesPowered >= player.targetCitiesPowered! || player.isAI) {
                moves[MoveName.Pass] = [true];
            }
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
