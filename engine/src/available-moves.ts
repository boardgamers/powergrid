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
        // Korea: which side's market this buy option draws from.
        // Omitted on all other maps.
        side?: 'north' | 'south';
        // South Africa: $8 flat buy from the coal storage pool below the market.
        // Distinct from the regular market buy (which can also be offered alongside).
        fromStorage?: boolean;
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

                        // No nuclear plants for Republic of Ireland (Green region) on UK&I.
                        // The restriction lifts as soon as the player has any non-Green city
                        // (Scotland/Wales/England/Northern Ireland = Brown/Yellow/Red/Pink/Orange).
                        if (G.map.name == 'UK & Ireland') {
                            const playerCities = player.cities.map(
                                (c) => G.map.cities.find((c_) => c_.name == c.name)!
                            );
                            if (playerCities.every((c) => c.region == 'green')) {
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

                        // Nuclear plants for Central Europe are only allowed for players with cities in:
                        // Czechia (green), Slovakia (brown), Hungary (purple)
                        if (G.map.name == 'Central Europe') {
                            const validCities = player.cities
                                .map((c) => G.map.cities.find((c_) => c_.name == c.name)!)
                                .filter((c) => c.region == 'green' || c.region == 'brown' || c.region == 'purple');

                            if (validCities.length == 0 && G.chosenPowerPlant.type == PowerPlantType.Uranium) {
                                moves[MoveName.Bid] = undefined;
                            }
                        }

                        // No nuclear plants for Republic of Ireland (Green region) on UK&I.
                        if (G.map.name == 'UK & Ireland') {
                            const playerCities = player.cities.map(
                                (c) => G.map.cities.find((c_) => c_.name == c.name)!
                            );
                            if (
                                playerCities.every((c) => c.region == 'green') &&
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

            const toBuy: { resource: ResourceType; side?: 'north' | 'south'; fromStorage?: boolean }[] = [];
            let maxPriceAvailable: number;
            if (G.map.maxPriceAvailable) {
                maxPriceAvailable = G.map.maxPriceAvailable[G.step - 1];
            } else {
                maxPriceAvailable = 16;
            }

            // Korea: each side is offered separately, tagged with the side. The
            // player's chosenSide locks them to one side once they make a buy.
            const isKorea = G.coalResupplyNorth !== undefined;
            const allowSouth = !isKorea || G.chosenSide !== 'north';
            const allowNorth = isKorea && G.chosenSide !== 'south';

            if (allowSouth && G.coalMarket > 0) {
                const hybridCapacityUsed =
                    player.hybridCapacity > 0 ? Math.max(0, player.oilLeft - player.oilCapacity) : 0;
                const coalPrices = G.coalPrices ?? prices[ResourceType.Coal];
                const price = coalPrices[coalPrices.length - G.coalMarket];

                if (
                    player.money >= price &&
                    player.coalCapacity + player.hybridCapacity > hybridCapacityUsed + player.coalLeft &&
                    price <= maxPriceAvailable
                ) {
                    toBuy.push(
                        isKorea ? { resource: ResourceType.Coal, side: 'south' } : { resource: ResourceType.Coal }
                    );
                }
            } else if (allowSouth) {
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

            // South Africa: $8 flat coal from the storage pool below the market.
            // Always available alongside the regular market option (not gated on
            // market being empty), as long as there are cubes in storage.
            if (allowSouth && G.coalStorage !== undefined && G.coalStorage > 0) {
                const hybridCapacityUsed =
                    player.hybridCapacity > 0 ? Math.max(0, player.oilLeft - player.oilCapacity) : 0;
                if (
                    player.money >= 8 &&
                    player.coalCapacity + player.hybridCapacity > hybridCapacityUsed + player.coalLeft &&
                    8 <= maxPriceAvailable
                ) {
                    toBuy.push({ resource: ResourceType.Coal, fromStorage: true });
                }
            }

            if (allowNorth && G.coalMarketNorth! > 0) {
                const hybridCapacityUsed =
                    player.hybridCapacity > 0 ? Math.max(0, player.oilLeft - player.oilCapacity) : 0;
                const coalPrices = G.coalPricesNorth!;
                const price = coalPrices[coalPrices.length - G.coalMarketNorth!];

                if (
                    player.money >= price &&
                    player.coalCapacity + player.hybridCapacity > hybridCapacityUsed + player.coalLeft &&
                    price <= maxPriceAvailable
                ) {
                    toBuy.push({ resource: ResourceType.Coal, side: 'north' });
                }
            }

            if (allowSouth && G.oilMarket > 0) {
                const hybridCapacityUsed =
                    player.hybridCapacity > 0 ? Math.max(0, player.coalLeft - player.coalCapacity) : 0;
                const oilPrices = G.oilPrices ?? prices[ResourceType.Oil];
                const price = oilPrices[oilPrices.length - G.oilMarket];

                if (
                    player.money >= price &&
                    player.oilCapacity + player.hybridCapacity > hybridCapacityUsed + player.oilLeft &&
                    price <= maxPriceAvailable
                ) {
                    toBuy.push(
                        isKorea ? { resource: ResourceType.Oil, side: 'south' } : { resource: ResourceType.Oil }
                    );
                }
            }

            if (allowNorth && G.oilMarketNorth! > 0) {
                const hybridCapacityUsed =
                    player.hybridCapacity > 0 ? Math.max(0, player.coalLeft - player.coalCapacity) : 0;
                const oilPrices = G.oilPricesNorth!;
                const price = oilPrices[oilPrices.length - G.oilMarketNorth!];

                if (
                    player.money >= price &&
                    player.oilCapacity + player.hybridCapacity > hybridCapacityUsed + player.oilLeft &&
                    price <= maxPriceAvailable
                ) {
                    toBuy.push({ resource: ResourceType.Oil, side: 'north' });
                }
            }

            if (allowSouth && G.garbageMarket > 0) {
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
                    toBuy.push(
                        isKorea ? { resource: ResourceType.Garbage, side: 'south' } : { resource: ResourceType.Garbage }
                    );
                }
            }

            if (allowNorth && G.garbageMarketNorth! > 0) {
                const garbagePrices = G.garbagePricesNorth!;
                const price = garbagePrices[garbagePrices.length - G.garbageMarketNorth!];

                if (
                    player.money >= price &&
                    player.garbageCapacity > player.garbageLeft &&
                    price <= maxPriceAvailable
                ) {
                    toBuy.push({ resource: ResourceType.Garbage, side: 'north' });
                }
            }

            // Uranium is South only (or non-Korea maps).
            if (allowSouth && G.uraniumMarket > 0) {
                const uraniumPrices = G.uraniumPrices ?? prices[ResourceType.Uranium];
                const price = uraniumPrices[uraniumPrices.length - G.uraniumMarket];
                if (
                    player.money >= price &&
                    player.uraniumCapacity > player.uraniumLeft &&
                    price <= maxPriceAvailable
                ) {
                    toBuy.push(
                        isKorea ? { resource: ResourceType.Uranium, side: 'south' } : { resource: ResourceType.Uranium }
                    );
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
                const isJapan = G.map.name === 'Japan';
                const japanStartingCities = isJapan ? new Set(G.map.startingCities ?? []) : new Set<string>();

                let toBuild: { name: string; price: number }[];
                if (player.cities.length == 0) {
                    // Japan: first house must go in one of the 6 designated starting cities.
                    const candidates = isJapan
                        ? G.map.cities.filter((c) => japanStartingCities.has(c.name))
                        : G.map.cities;
                    toBuild = candidates.map((c) => ({ name: c.name, price: 0 }));
                } else if (isJapan && G.round === 1) {
                    // Japan round 1: any additional house must also be a starting city.
                    // Players cannot extend to adjacent non-starting cities until round 2.
                    toBuild = G.map.cities
                        .filter((c) => japanStartingCities.has(c.name))
                        .map((c) => ({ name: c.name, price: 0 }));
                } else {
                    toBuild = dijkstra(G, player).map((c) => ({ name: c.name, price: c.price }));

                    // Japan: a player may start a second disconnected network at any available
                    // starting city, paying only the slot cost (no connection fee).
                    if (
                        isJapan &&
                        countNetworks(
                            G.map.connections,
                            player.cities.map((c) => c.name)
                        ) < 2
                    ) {
                        toBuild.forEach((city) => {
                            if (japanStartingCities.has(city.name)) {
                                city.price = 0;
                            }
                        });
                    }
                }

                toBuild.forEach((city) => {
                    const cityData = G.map.cities.find((c) => c.name == city.name)!;
                    const othersCount = G.players.filter((p) => p.cities.find((c) => city.name == c.name)).length;

                    // Transregional cities (e.g. Strasbourg on Baden-Württemberg) are only open
                    // in Step 2 onward. The slot fee is replaced by a flat 15 (Step 2) or 20
                    // (Step 3); the dijkstra connection cost from the player's existing network
                    // is still paid on top.
                    if (cityData.transregional) {
                        if (G.step < 2) {
                            city.price = 9999;
                            return;
                        }
                        city.price += G.step == 3 ? 20 : 15;

                        if (othersCount == G.step) {
                            city.price = 9999;
                        }

                        if (player.cities.find((c) => c.name == city.name)) {
                            city.price = 9999;
                        }
                        return;
                    }

                    // UK & Ireland: starting a network on an island where the player has
                    // no city yet pays the first-house base + crossIslandSurcharge. There
                    // is no sea edge so dijkstra reports the target city as unreachable
                    // (price=9999); we override here. The first build ever (player.cities
                    // empty) goes through the normal first-build path and pays no surcharge.
                    if (cityData.island && G.map.crossIslandSurcharge !== undefined && player.cities.length > 0) {
                        const playerIslands = new Set(
                            player.cities
                                .map((c) => G.map.cities.find((mc) => mc.name == c.name)?.island)
                                .filter((i): i is string => !!i)
                        );
                        if (!playerIslands.has(cityData.island)) {
                            city.price = 10 + othersCount * 5 + G.map.crossIslandSurcharge;

                            if (othersCount == G.step) {
                                city.price = 9999;
                            }

                            if (player.cities.find((c) => c.name == city.name)) {
                                city.price = 9999;
                            }
                            return;
                        }
                    }

                    // South Africa's cross-border foreign-country spaces: cap at 1 occupant
                    // ever, and the dijkstra path cost (30 via the cross-border edge) is the
                    // complete cost — no 10+position*5 house base is added. Players cannot
                    // start in one of these (you have to build INTO South Africa first).
                    if (cityData.singleOccupancy) {
                        if (player.cities.length == 0) {
                            city.price = 9999;
                            return;
                        }
                        if (othersCount >= 1) {
                            city.price = 9999;
                            return;
                        }
                        if (player.cities.find((c) => c.name == city.name)) {
                            city.price = 9999;
                        }
                        return;
                    }

                    const slotCosts = cityData.slotCosts;
                    const maxSlotsThisStep = cityData.stepSlots ? cityData.stepSlots[G.step - 1] : G.step;
                    const totalSlots = slotCosts ? slotCosts.length : 3;

                    if (othersCount >= maxSlotsThisStep || othersCount >= totalSlots) {
                        city.price = 9999;
                    } else {
                        city.price += slotCosts ? slotCosts[othersCount] : 10 + othersCount * 5;
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

function countNetworks(connections: { nodes: string[] }[], cityNames: string[]): number {
    const citySet = new Set(cityNames);
    const visited = new Set<string>();
    let count = 0;
    for (const city of cityNames) {
        if (visited.has(city)) continue;
        count++;
        const stack = [city];
        while (stack.length > 0) {
            const current = stack.pop()!;
            if (visited.has(current)) continue;
            visited.add(current);
            for (const conn of connections) {
                if (conn.nodes.includes(current)) {
                    const neighbor = conn.nodes.find((n) => n !== current)!;
                    if (citySet.has(neighbor) && !visited.has(neighbor)) {
                        stack.push(neighbor);
                    }
                }
            }
        }
    }
    return count;
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
