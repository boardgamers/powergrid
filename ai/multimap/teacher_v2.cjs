// Opt-in deterministic mechanics repairs, NOT a demonstrated strength upgrade.
// The frozen v1 teacher and diagnostic callers remain unchanged.
const f = require('./features.cjs');
const eco = require('./economics_v2.cjs');
const SCHEMA = 'multimap-teacher-v2';
const plantValue = eco.plantValue;
function scores(g, seat, actions = f.legal(g, seat), style = 'geographic') {
    const raw = eco.scores(g, seat, actions, style === 'rush' ? 'rush' : 'economic');
    if (!['geographic', 'economic', 'rush'].includes(style)) throw Error('Unknown teacher');
    const p = g.players[seat];
    return actions.map((a, i) => {
        // Neither geographic preferences nor UK entry safety may override the
        // economics finish guard. -30 is reserved for a rejected Build.
        if (a.name === 'Build' && raw[i] === -30) return raw[i];
        if (a.name === 'Build' && g.map.crossIslandSurcharge && p.cities.length > 0) {
            const ownedIslands = new Set(p.cities.map((c) => g.map.cities.find((x) => x.name === c.name).island));
            const openIslands = new Set(
                g.map.cities
                    .filter((c) => !g.players.some((q) => q.cities.some((x) => x.name === c.name)))
                    .map((c) => c.island)
            );
            const missing = [...openIslands].filter((island) => !ownedIslands.has(island));
            if (missing.length) {
                const island = g.map.cities.find((c) => c.name === a.data.name).island;
                return missing.includes(island) ? 100 - a.data.price * 0.1 : -20;
            }
        }
        if (a.name === 'Build' && style === 'geographic') {
            const adjacent = g.map.connections.filter((e) => e.nodes.includes(a.data.name));
            const opportunity = adjacent.reduce((sum, e) => {
                const other = e.nodes.find((n) => n !== a.data.name);
                if (p.cities.some((c) => c.name === other)) return sum;
                const occupied = g.players.filter((q) => q.cities.some((c) => c.name === other)).length;
                return sum + (occupied < g.step ? 1 : 0.2) / (1 + e.cost / 10);
            }, 0);
            return raw[i] + Math.min(3, opportunity) * 0.35;
        }
        return raw[i];
    });
}
function choose(g, seat, actions = f.legal(g, seat), style = 'geographic', rng = () => 0.5) {
    const values = scores(g, seat, actions, style);
    if (!values.every(Number.isFinite)) throw Error('Nonfinite v2 teacher');
    let best = -Infinity,
        index = -1;
    values.forEach((v, i) => {
        v += rng() * 1e-6;
        if (v > best) {
            best = v;
            index = i;
        }
    });
    return { index, action: actions[index], values };
}
module.exports = { SCHEMA, plantValue, scores, choose };
