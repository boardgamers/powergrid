// Separate RL environment: frozen bootstrap data generation is unchanged.
const readline = require('node:readline');
const { performance } = require('node:perf_hooks');
const f = require('./features.cjs'),
    teacher = require('./teacher.cjs');
const { start, outcome } = require('./game.cjs');
const protocol = require('./ppo-protocol-v1.json');
let game, spec, steps;
function inputs(g, seat) {
    const moves = f.legal(g, seat),
        observation = f.encode(g, seat, moves);
    const scores = teacher.scores(g, seat, moves, 'geographic');
    const best = Math.max(...scores);
    const bidding = moves.some((a) => a.name === 'Bid');
    const nomination = moves.some((a) => a.name === 'ChoosePowerPlant');
    const temps = protocol.priorTemperatures;
    const temperature = bidding
        ? g.options.fastBid
            ? temps.sealedBid
            : temps.openBid
        : nomination
        ? temps.nomination
        : temps.other;
    observation.prior = scores.map((v) => Math.max(protocol.priorFloor, (v - best) / temperature));
    return observation;
}
function view() {
    while (!f.E.ended(game)) {
        if (steps >= (spec.maxSteps || 4000)) throw Error('RL game capped; never fabricate a terminal label');
        const seat = game.currentPlayers[0],
            moves = f.legal(game, seat);
        if (
            seat === spec.focalSeat &&
            moves.length > 1 &&
            !spec.focalTeacher &&
            protocol.learnedPhases.includes(game.phase)
        ) {
            const began = performance.now(),
                observation = inputs(game, seat);
            return { terminal: false, seat, phase: game.phase, observation, featureMs: performance.now() - began };
        }
        const style = seat === spec.focalSeat ? 'geographic' : spec.opponentStyle || 'economic';
        const action = moves.length === 1 ? moves[0] : teacher.choose(game, seat, moves, style).action;
        f.E.move(game, structuredClone(action), seat);
        steps++;
    }
    return { terminal: true, credit: outcome(game), steps, rounds: game.round };
}
function request(req) {
    if (req.op === 'start') {
        spec = req.spec;
        if (
            !protocol.variants.includes(spec.variant) ||
            !protocol.players.includes(spec.players) ||
            !protocol.fastBids.includes(spec.fastBid)
        )
            throw Error('Unsupported RL configuration');
        if (!protocol.opponentStyles.includes(spec.opponentStyle || 'economic')) throw Error('Unknown RL opponent');
        if (!Number.isInteger(spec.focalSeat) || spec.focalSeat < 0 || spec.focalSeat >= spec.players)
            throw Error('Bad focal seat');
        game = start(spec);
        steps = 0;
        return view();
    }
    if (req.op === 'step') {
        const seat = game.currentPlayers[0],
            moves = f.legal(game, seat);
        if (seat !== spec.focalSeat || !Number.isInteger(req.index) || req.index < 0 || req.index >= moves.length)
            throw Error('Illegal RL action');
        f.E.move(game, structuredClone(moves[req.index]), seat);
        steps++;
        return view();
    }
    throw Error('Unknown RL request');
}
if (require.main === module)
    readline.createInterface({ input: process.stdin }).on('line', (line) => {
        try {
            console.log(JSON.stringify(request(JSON.parse(line))));
        } catch (e) {
            console.log(JSON.stringify({ error: e.stack }));
        }
    });
module.exports = { inputs, request };
