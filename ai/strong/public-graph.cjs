// Explicit map topology for multi-map policy work. Only public game fields are read.
function encode(g, seat) {
    const order = Array.from({ length: g.players.length }, (_, i) => (seat + i) % g.players.length);
    const cities = [...g.map.cities].sort((a, b) => a.name.localeCompare(b.name));
    const index = new Map(cities.map((c, i) => [c.name, i]));
    const regions = [...new Set(cities.map((c) => c.region || 'main'))].sort(),
        islands = [...new Set(cities.map((c) => c.island || 'main'))].sort();
    const nodes = cities.map((city) => {
        const owners = order.map((id) => +g.players[id].cities.some((c) => c.name === city.name)),
            occupied = owners.reduce((a, b) => a + b, 0);
        const capacity = city.singleOccupancy ? 1 : city.slotCosts?.length ?? 3,
            slots = city.singleOccupancy ? 1 : city.stepSlots?.[g.step - 1] ?? g.step;
        const permanentBlocked = !!g.blockedCities?.includes(city.name),
            available = !permanentBlocked && !(city.transregional && g.step < 2);
        return {
            name: city.name,
            region: regions.indexOf(city.region || 'main'),
            island: islands.indexOf(city.island || 'main'),
            owners,
            openSlots: available ? Math.max(0, Math.min(capacity, slots) - occupied) : 0,
            futureSlots: permanentBlocked ? 0 : Math.max(0, capacity - occupied),
            slotCosts: city.slotCosts || [10, 15, 20],
            stepSlots: city.stepSlots || [1, 2, 3],
            transregional: !!city.transregional,
            nuclearBanned: !!g.map.noUraniumRegions?.includes(city.region),
            blocked: permanentBlocked,
        };
    });
    const edges = g.map.connections
        .filter((e) => e.nodes.every((n) => index.has(n)))
        .map((e) => ({ a: index.get(e.nodes[0]), b: index.get(e.nodes[1]), cost: e.cost }));
    return {
        nodes,
        edges,
        regions,
        islands,
        crossIslandSurcharge: g.map.crossIslandSurcharge || 0,
        playerOrder: order.map((id) => g.playerOrder.indexOf(id)),
        currentPlayers: order.map((id) => g.currentPlayers.includes(id)),
        players: order.map((id) => ({
            cities: g.players[id].cities.length,
            money: g.players[id].money,
            powerPlants: g.players[id].powerPlants.map((p) => ({
                number: p.number,
                type: p.type,
                cost: p.cost,
                citiesPowered: p.citiesPowered,
            })),
            fuel: ['coal', 'oil', 'garbage', 'uranium'].map((r) => g.players[id][r + 'Left']),
        })),
    };
}
module.exports = { encode };
