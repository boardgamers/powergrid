// Map-derived territory features. Region and island labels come from the engine.
function orderAfterBuild(g, seat) {
    return g.players
        .map((p) => ({
            id: p.id,
            cities: p.cities.length + (p.id === seat ? 1 : 0),
            plant: Math.max(0, ...p.powerPlants.map((x) => x.number)),
        }))
        .sort((a, b) => b.cities - a.cities || b.plant - a.plant)
        .map((p) => p.id);
}
function territories(g, seat) {
    const order = Array.from({ length: g.players.length }, (_, i) => (seat + i) % g.players.length);
    const groups = (key) =>
        [...new Set(g.map.cities.map((c) => c[key] || 'main'))].sort().map((name) => {
            const cities = g.map.cities.filter((c) => (c[key] || 'main') === name);
            let empty = 0,
                open = 0,
                totalFree = 0;
            for (const city of cities) {
                const occupied = g.players.filter((p) => p.cities.some((c) => c.name === city.name)).length;
                const slots = city.singleOccupancy ? 1 : city.stepSlots?.[g.step - 1] ?? g.step,
                    capacity = city.singleOccupancy ? 1 : city.slotCosts?.length ?? 3;
                const blocked = g.blockedCities?.includes(city.name) || (city.transregional && g.step < 2);
                empty += +(!occupied && !blocked);
                open += blocked ? 0 : Math.max(0, Math.min(slots, capacity) - occupied);
                totalFree += blocked ? 0 : Math.max(0, capacity - occupied);
            }
            return {
                name,
                size: cities.length,
                empty,
                open,
                totalFree,
                owned: order.map(
                    (id) => g.players[id].cities.filter((c) => cities.some((x) => x.name === c.name)).length
                ),
            };
        });
    return { regions: groups('region'), islands: groups('island') };
}
function stateFeatures(g, seat, context) {
    const t = context || territories(g, seat),
        v = [];
    for (const [groups, max] of [
        [t.regions, 8],
        [t.islands, 4],
    ])
        for (let i = 0; i < max; i++) {
            const x = groups[i];
            v.push(
                ...(x
                    ? [x.size / 64, x.empty / 64, x.open / 64, x.totalFree / 128, ...x.owned.map((n) => n / 22)]
                    : Array(4 + g.players.length).fill(0))
            );
        }
    v.push((g.map.crossIslandSurcharge || 0) / 100);
    return v;
}
function actionFeatures(g, seat, action, context) {
    const order = Array.from({ length: g.players.length }, (_, i) => (seat + i) % g.players.length),
        newOrder = orderAfterBuild(g, seat);
    if (action.name !== 'Build') return Array(4 + 3 * g.players.length).fill(0);
    const city = g.map.cities.find((c) => c.name === action.data.name),
        t = context || territories(g, seat),
        region = t.regions.find((x) => x.name === (city.region || 'main')),
        island = t.islands.find((x) => x.name === (city.island || 'main'));
    return [
        ...order.map((id) => newOrder.indexOf(id) / Math.max(1, g.players.length - 1)),
        ...region.owned.map((n) => n / 22),
        ...island.owned.map((n) => n / 22),
        region.open / 64,
        island.open / 64,
        +(island.owned[0] === 0),
        g.map.connections.filter((e) => e.nodes.includes(city.name)).length / 8,
    ];
}
module.exports = { territories, stateFeatures, actionFeatures, orderAfterBuild };
