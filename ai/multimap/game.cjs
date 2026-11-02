// JSON-lines environment. Raw game states never cross the process boundary.
const readline = require('node:readline');
const crypto = require('node:crypto');
const f = require('./features.cjs'),
    teacher = require('./teacher.cjs');
const seedrandom = require(require.resolve('seedrandom', { paths: [__dirname + '/../../engine'] }));
const protocol = require('./protocol.json');
function start(spec) {
    if (!f.MAPS.includes(spec.map)) throw Error('Unsupported map');
    return f.E.setup(
        spec.players,
        { map: spec.map, variant: spec.variant, fastBid: spec.fastBid, showMoney: true },
        spec.seed
    );
}
function outcome(g) {
    if (!f.E.ended(g)) throw Error('Cannot label nonterminal game');
    const top = f.E.playersSortedByScore(g)[0];
    const winners = g.players.map(
        (p) =>
            +(p.citiesPowered === top.citiesPowered && p.money === top.money && p.cities.length === top.cities.length)
    );
    return winners.map((x) => x / winners.reduce((a, b) => a + b, 0));
}
function collect(spec) {
    const g = start(spec),
        rng = seedrandom(spec.seed + ':policy'),
        sampleRng = seedrandom(spec.seed + ':reservoir');
    const buckets = {},
        seen = {},
        styles = ['geographic', 'economic', 'rush'];
    const behavior = g.players.map((_, i) => styles[(i + (spec.deal || 0)) % styles.length]);
    let steps = 0,
        relations;
    while (!f.E.ended(g)) {
        if (steps >= (spec.maxSteps || protocol.maxSteps)) throw Error(`Game capped: ${spec.seed}`);
        const seat = g.currentPlayers[0],
            moves = f.legal(g, seat),
            phase = g.phase;
        const decision = teacher.choose(g, seat, moves, behavior[seat], rng);
        if (moves.length > 1) {
            const count = (seen[phase] = (seen[phase] || 0) + 1);
            const bucket = buckets[phase] || (buckets[phase] = []),
                limit = spec.samplesPerPhase ?? protocol.samplesPerPhase;
            const replace = bucket.length < limit ? bucket.length : Math.floor(sampleRng() * count);
            if (replace < limit) {
                const encoded = f.encode(g, seat, moves);
                relations = encoded.relations;
                delete encoded.relations;
                const labels = teacher.scores(g, seat, moves, 'geographic'),
                    best = Math.max(...labels);
                const targets = labels.map((v) => +(best - v < 1e-7));
                bucket[replace] = { ...encoded, targets, seat, step: steps, phase };
            }
        }
        f.E.move(g, structuredClone(decision.action), seat);
        steps++;
    }
    const credit = outcome(g),
        rows = Object.values(buckets)
            .flat()
            .sort((a, b) => a.step - b.step);
    for (const row of rows) {
        row.value = credit[row.seat];
        // A public feature fingerprint catches identical observations across split namespaces.
        row.fingerprint = crypto
            .createHash('sha256')
            .update(JSON.stringify([row.global, row.players, row.nodes, relations, row.actions]))
            .digest('hex');
    }
    return { spec, steps, rounds: g.round, credit, behavior, relations, rows, terminal: true };
}
let live = null,
    liveSpec = null,
    steps = 0;
function view() {
    while (!f.E.ended(live) && liveSpec.focalSeat !== undefined) {
        if (steps >= (liveSpec.maxSteps || protocol.maxSteps)) throw Error('Evaluation game capped');
        const seat = live.currentPlayers[0],
            moves = f.legal(live, seat);
        if (seat === liveSpec.focalSeat && moves.length > 1 && !liveSpec.focalTeacher) break;
        const style = seat === liveSpec.focalSeat ? liveSpec.focalTeacher || 'geographic' : 'economic';
        const action = moves.length === 1 ? moves[0] : teacher.choose(live, seat, moves, style).action;
        f.E.move(live, structuredClone(action), seat);
        steps++;
    }
    if (f.E.ended(live)) return { terminal: true, credit: outcome(live), steps, rounds: live.round };
    if (steps >= (liveSpec.maxSteps || protocol.maxSteps)) throw Error('Evaluation game capped');
    const seat = live.currentPlayers[0],
        moves = f.legal(live, seat);
    return { terminal: false, seat, observation: f.encode(live, seat, moves) };
}
function request(req) {
    if (req.op === 'collect') return collect(req.spec);
    if (req.op === 'start') {
        liveSpec = req.spec;
        live = start(req.spec);
        steps = 0;
        return view();
    }
    if (req.op === 'step') {
        const seat = live.currentPlayers[0],
            moves = f.legal(live, seat);
        const index = req.teacher ? teacher.choose(live, seat, moves, req.teacher).index : req.index;
        if (!Number.isInteger(index) || index < 0 || index >= moves.length) throw Error('Illegal policy index');
        f.E.move(live, structuredClone(moves[index]), seat);
        steps++;
        return view();
    }
    throw Error('Unknown request');
}
if (require.main === module) {
    const rl = readline.createInterface({ input: process.stdin });
    rl.on('line', (line) => {
        try {
            console.log(JSON.stringify(request(JSON.parse(line))));
        } catch (e) {
            console.log(JSON.stringify({ error: e.stack }));
        }
    });
}
module.exports = { start, outcome, collect };
