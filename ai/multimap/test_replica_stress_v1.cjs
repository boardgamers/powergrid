// Offline synthetic engine fixtures only; no games/models/network or scientific evidence.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const crypto = require('node:crypto');
const { execFileSync } = require('node:child_process');
const x = require('./replica_stress_game_v1.cjs');
const maps = ['Germany', 'USA', 'France', 'UK & Ireland'];
const policies = ['replica1', 'replica2', 'ppo2'];
const cells = maps.flatMap((map) =>
    [2, 3, 4, 5, 6].flatMap((players) =>
        ['original', 'recharged'].flatMap((variant) =>
            [false, true].map((fastBid) => ({ map, players, variant, fastBid }))
        )
    )
);
const smokeScopes = new Set([
    'Germany|2|recharged|1',
    'Germany|6|recharged|1',
    'USA|3|recharged|1',
    'USA|5|original|1',
    'France|4|recharged|0',
    'France|2|original|1',
    'UK & Ireland|5|recharged|1',
    'UK & Ireland|6|original|0',
]);
function spec(ci, panel = 'mixed', policy = 'replica1', focalSeat = 0, smoke = false, deal = 0) {
    const s = { ...cells[ci], panel, policy, focalSeat, smoke, deal, maxSteps: 4000 };
    s.cell = `${s.map}|${s.players}|${s.variant}|${Number(s.fastBid)}`;
    s.seed = `pg-multimap-replica-stress-20261109-v1${smoke ? ':smoke' : ''}:${panel}:${s.cell}:${deal}`;
    const weak = ['ppo0', 'ppo1', 'ppo2', 'teacherV2', ...(s.map === 'Germany' ? ['reference'] : [])];
    s.controllers = Array.from({ length: s.players }, (_, seat) => {
        if (seat === focalSeat) return policy;
        if (panel === 'strong') return s.map === 'Germany' ? 'reference' : 'expert24';
        const i = ci + deal + ((seat - focalSeat + s.players) % s.players) - 1;
        return i % 2 ? 'ppo-placeholder' : 'expert24';
    });
    for (let seat = 0; seat < s.players; seat++)
        if (seat !== focalSeat && panel === 'mixed') {
            const i = ci + deal + ((seat - focalSeat + s.players) % s.players) - 1;
            s.controllers[seat] = i % 2 ? weak[Math.floor(i / 2) % weak.length] : 'expert24';
        }
    return s;
}
function syntheticBridge(protocol = x.protocol) {
    const seen = [];
    const moves = [{ name: 'a' }, { name: 'b' }];
    const state = (s) => ({
        events: Array.from({ length: s.players }, (_, seat) => x.PHASES.map((phase) => ({ seat, phase }))).flat(),
        at: 0,
        currentPlayers: [0],
        phase: 'Auction',
        round: 1,
        players: s.players,
    });
    const engine = {
        ended: (g) => g.at === g.events.length,
        move(g, move, seat) {
            assert.equal(g.events[g.at].seat, seat);
            assert(moves.some((m) => m.name === move.name));
            g.at++;
            if (g.events[g.at]) {
                g.currentPlayers = [g.events[g.at].seat];
                g.phase = g.events[g.at].phase;
            }
        },
    };
    const input = (family) => (g, seat) => {
        seen.push([family, seat, g.phase]);
        return { prior: [0, -1], actions: [[], []], family };
    };
    const fixed = (family) => ({
        choose(g, seat) {
            seen.push([family, seat, g.phase]);
            return { action: moves[0] };
        },
    });
    const stubs = {
        './features.cjs': { E: engine, legal: () => moves },
        './teacher.cjs': fixed('v1-fixed'),
        './teacher_v2.cjs': fixed('v2-fixed'),
        './expert_game.cjs': { inputs: input('v2') },
        './game_rl.cjs': { inputs: input('v1') },
        './game.cjs': { start: state, outcome: (g) => Array(g.players).fill(1 / g.players) },
        './reference_game.cjs': {
            ENGINE_VERSION: '2.0.22',
            hiddenInvariant: () => ({ public: true }),
            atomicIndex(legal, move) {
                const i = legal.findIndex((m) => m.name === move.name);
                assert(i >= 0);
                return i;
            },
        },
        './replica-stress-protocol-v1.json': protocol,
    };
    const module = { exports: {} };
    const localRequire = (name) => (Object.hasOwn(stubs, name) ? stubs[name] : require(name));
    const code = fs.readFileSync(path.join(__dirname, 'replica_stress_game_v1.cjs'), 'utf8');
    vm.runInNewContext('(function(require,module,__dirname){' + code + '\n})', {
        structuredClone,
        Buffer,
        console,
        Object,
        Array,
    })(localRequire, module, __dirname);
    return { bridge: module.exports, seen };
}

test('all 15360 production and 198 fixed smoke specs use independent eight-deal formula', () => {
    let production = 0,
        smokeCount = 0;
    const roots = new Set();
    for (let ci = 0; ci < 80; ci++)
        for (const panel of ['strong', 'mixed'])
            for (let deal = 0; deal < 8; deal++)
                for (let seat = 0; seat < cells[ci].players; seat++)
                    for (const policy of policies) {
                        const s = spec(ci, panel, policy, seat, false, deal);
                        x.validateSpec(s);
                        production++;
                        roots.add(s.seed);
                        assert.deepEqual(x.controllersFor(s), s.controllers);
                        assert(!s.controllers.some((c, i) => i !== seat && c.startsWith('replica')));
                        if (deal === 0 && smokeScopes.has(s.cell)) {
                            x.validateSpec(spec(ci, panel, policy, seat, true));
                            smokeCount++;
                        }
                    }
    assert.equal(production, 15360);
    assert.equal(smokeCount, 198);
    assert.equal(roots.size, 1280);
    const a = spec(21, 'mixed', 'replica1', 0, false, 0),
        b = spec(21, 'mixed', 'replica1', 0, false, 4);
    assert.notDeepEqual(a.controllers, b.controllers); // no deal % 4 regression
});

test('strict scope, focal-only replicas, opponent-only original and no labels/extra fields', () => {
    const good = spec(27, 'strong', 'replica1', 0, true);
    x.validateSpec(good);
    for (const patch of [
        { map: 'Italy' },
        { map: 'Benelux' },
        { seed: 'pg-multimap-stress-20261103-v1:old' },
        { policy: 'expert24' },
        { policy: 'ppo0' },
        { smoke: 1 },
        { fastBid: 0 },
        { deal: 1 },
        { deal: 8 },
        { maxSteps: 3999 },
        { maxSteps: true },
        { players: true },
        { focalSeat: false },
        { training: false },
        { controllers: ['replica1', 'replica2'] },
        { controllers: ['expert24', 'expert24'] },
    ])
        assert.throws(() => x.validateSpec({ ...good, ...patch }));
    assert.throws(() => x.validateSpec(spec(20, 'strong', 'replica1', 0, true)));
    assert.throws(() => x.controllersFor(good, 0));
});

test('independent protocol pins reject changed import object, including bool/int and all six pins', () => {
    for (const alter of [
        (p) => (p.fitting = 0),
        (p) => (p.jobBudget.initialHours.strong = 3),
        (p) => (p.replicas[1].update = 24),
        (p) => (p.expertOpponent.revision = '0'.repeat(40)),
        (p) => p.inferenceModels.reverse(),
        (p) => (p.dealsPerCell = 4),
    ]) {
        const p = structuredClone(x.protocol);
        alter(p);
        assert.throws(() => syntheticBridge(p));
    }
    assert(Object.isFrozen(x.protocol));
    assert(Object.isFrozen(x.protocol.replicas[0]));
});

test('base old-source pins independently match Git 6a7cdc6; old namespace guards remain untouched', () => {
    for (const [name, sha] of Object.entries(x.protocol.frozenSources)) {
        const bytes = execFileSync('git', ['show', `6a7cdc6:ai/multimap/${name}`], {
            cwd: path.join(__dirname, '../..'),
        });
        assert.equal(crypto.createHash('sha256').update(bytes).digest('hex'), sha);
    }
    assert.throws(() => require('./stress_game.cjs').validateSpec(spec(27)));
});

test('synthetic expert24/replica1/replica2 all use v2; PPO uses v1; fixed phases match actual seats', () => {
    for (const policy of policies) {
        const { bridge, seen } = syntheticBridge();
        const s = spec(27, 'strong', policy, 0, true);
        const game = new bridge.StressGame();
        let view = game.start(s);
        let decisions = 0;
        while (!view.terminal) {
            const expected = s.controllers[view.seat].startsWith('ppo') ? 'v1' : 'v2';
            assert.equal(view.observation.family, expected);
            assert.equal(view.controller, s.controllers[view.seat]);
            assert.deepEqual(game.view(), view);
            view = game.step({ op: 'step', index: 1 });
            decisions++;
        }
        assert.equal(decisions, 2 * s.players);
        assert.equal(view.steps, 4 * s.players);
        assert.equal(view.counts[policy].Auction, 1);
        assert.equal(view.counts.expert24.Auction, s.players - 1);
        assert.equal(view.counts.fixedV2.Resources, policy === 'ppo2' ? s.players - 1 : s.players);
        assert.equal(view.counts.fixedV1.Resources, policy === 'ppo2' ? 1 : 0);
        assert(seen.some((v) => v[0] === 'v2-fixed'));
        assert.equal(view.publicChecks.expertAtomicLegal, 0);
        assert.throws(() => game.label());
    }
});

test('synthetic Germany reference owns all phases, atomic bound responses and hard cap', () => {
    const { bridge } = syntheticBridge();
    const game = new bridge.StressGame();
    let view = game.start(spec(3, 'strong', 'replica2', 0, true));
    while (!view.terminal) {
        if (view.kind === 'reference') {
            assert.throws(() =>
                game.step({
                    op: 'step',
                    response: { requestId: 'stale', revision: view.revision, move: { name: 'a' } },
                })
            );
            view = game.step({
                op: 'step',
                response: { requestId: view.request.requestId, revision: view.revision, move: { name: 'a' } },
            });
        } else view = game.step({ op: 'step', index: 0 });
    }
    for (const phase of x.PHASES) assert.equal(view.counts.reference[phase], 1);
    assert.equal(view.publicChecks.hiddenInvariant, 4);
    assert.equal(view.publicChecks.referenceAtomicLegal, 4);
    const capped = new bridge.StressGame();
    capped.start(spec(27, 'strong', 'replica1', 0, true));
    capped.steps = 4000;
    assert.throws(
        () => capped.view(),
        (e) => e.code === 'STRESS_CAPPED'
    );
});
