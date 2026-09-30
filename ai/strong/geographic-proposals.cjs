// Proposal diversity only: the rules engine and rollout outcomes choose the move.
const graph = require('./public-graph.cjs');
const cache = new WeakMap();
function distances(map, topology) {
    if (cache.has(map)) return cache.get(map);
    const n = topology.nodes.length,
        matrix = Array.from({ length: n }, (_, i) => Array.from({ length: n }, (_, j) => (i === j ? 0 : Infinity)));
    for (const edge of topology.edges) {
        matrix[edge.a][edge.b] = Math.min(matrix[edge.a][edge.b], edge.cost);
        matrix[edge.b][edge.a] = Math.min(matrix[edge.b][edge.a], edge.cost);
    }
    for (let k = 0; k < n; k++)
        for (let i = 0; i < n; i++)
            for (let j = 0; j < n; j++) matrix[i][j] = Math.min(matrix[i][j], matrix[i][k] + matrix[k][j]);
    cache.set(map, matrix);
    return matrix;
}
function rank(g, seat, actions) {
    const topology = graph.encode(g, seat),
        matrix = distances(g.map, topology),
        index = new Map(topology.nodes.map((n, i) => [n.name, i])),
        open = topology.nodes
            .map((node, i) => ({ node, i }))
            .filter(({ node }) => node.openSlots > 0 && !node.owners[0]);
    return actions
        .flatMap((action, i) => {
            if (action.name !== 'Build') return [];
            const at = index.get(action.data.name),
                node = topology.nodes[at],
                growth = open
                    .filter(({ i }) => i !== at)
                    .map(({ i }) => matrix[at][i])
                    .filter(Number.isFinite)
                    .sort((a, b) => a - b)
                    .slice(0, 3);
            const score =
                action.data.price + (growth.length ? growth.reduce((a, b) => a + b, 0) / growth.length : 1000);
            return [{ index: i, region: node.region, island: node.island, score }];
        })
        .sort((a, b) => a.score - b.score || a.index - b.index);
}
module.exports = { rank };
