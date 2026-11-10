'use strict';
// PRIVATE, offline engineering conformance. No platform source is vendored here.
// The caller stages the three unchanged upstream files outside Git. This harness
// authenticates their bytes and calls the EXACT shipped index.mjs through them.
const fs = require('node:fs');
const path = require('node:path');
const { createRequire } = require('node:module');
const { createHash } = require('node:crypto');
const { execFileSync } = require('node:child_process');
const { isDeepStrictEqual } = require('node:util');
const { performance } = require('node:perf_hooks');
const { HostClient, HostClientError, LIMITS } = require('./host_client.cjs');

const NAMESPACE = 'pg-bgs-serving-v1';
const TARGET_NODE = 'v24.22.1';
const HOST_SOURCE = Object.freeze({
    repository: 'boardgamers-mono',
    commit: '735f8e6804704572e8042b886cf2af3d9753d550',
    directory: 'apps/game-server/app/engine-host',
    sha256: Object.freeze({
        'host.ts': 'c6dcd5486289a9542dbcbaa205902192e47628f8b072bf5242cded94109b7bd7',
        'host-protocol.ts': '7738c0826b72909a4a2c2511de98730641aa7a5b89d2d76a9f177dbdb871760b',
        'analysis-adapter.ts': '672d5c29c15c053697355f3249c4d1b1b1a2a35657cd6558a84bde2f2e21a496',
    }),
});
const MAPS = ['Germany', 'USA', 'France', 'UK & Ireland'];
const KINDS = ['forced', 'nomination', 'bid', 'Building', 'Resources', 'Bureaucracy'];
const REQUIRED = [
    'init',
    'move',
    'ended',
    'scores',
    'dropPlayer',
    'currentPlayer',
    'logLength',
    'logSlice',
    'moveAI',
    'toSave',
    'replay',
];
const COUNTERS = ['turns', 'learned', 'fixedV2', 'heuristicFallback', 'fallbackTurns', 'circuitOpenEvents'];
class ConformanceError extends Error {
    constructor(code) {
        super(`conformance-${code}`);
        this.name = 'ConformanceError';
        this.code = this.message;
    }
}
function need(value, code) {
    if (!value) throw new ConformanceError(code);
}
function same(actual, expected, code) {
    need(isDeepStrictEqual(actual, expected), code);
}
const digest = (value) => createHash('sha256').update(value).digest('hex');
function json(value) {
    if (value === undefined) return undefined;
    const raw = JSON.stringify(value);
    need(Buffer.byteLength(raw) <= LIMITS.stateBytes, 'json-limit');
    return JSON.parse(raw);
}
function readFile(root, name) {
    need(!path.isAbsolute(name) && !name.split(/[\\/]/).includes('..') && !name.includes('\0'), 'input-name');
    const file = path.join(root, name);
    let part = file;
    while (part !== root) {
        need(!fs.lstatSync(part).isSymbolicLink(), 'input-link');
        part = path.dirname(part);
    }
    need(fs.lstatSync(file).isFile(), 'input-file');
    return fs.readFileSync(file);
}
function inventory(directory) {
    const result = {};
    for (const [name, expected] of Object.entries(HOST_SOURCE.sha256)) {
        const raw = readFile(directory, name);
        need(digest(raw) === expected, 'unchanged-upstream-host');
        result[name] = { sha256: digest(raw), bytes: raw.length };
    }
    return result;
}
function summary(values) {
    const sorted = [...values].sort((a, b) => a - b);
    return {
        n: sorted.length,
        p50: sorted[Math.ceil(sorted.length * 0.5) - 1] ?? null,
        p95: sorted[Math.ceil(sorted.length * 0.95) - 1] ?? null,
        max: sorted.at(-1) ?? null,
    };
}
function sampleProcess(pid) {
    const totals = {
        sampleIntervalMs: 50,
        samples: 0,
        procAvailable: false,
        peakRssBytes: 0,
        peakHighWaterRssBytes: 0,
        peakThreads: 0,
        userCpuTicks: 0,
        systemCpuTicks: 0,
        cpuUnits: 'Linux /proc clock ticks; not CPU quota or CPU utilization',
    };
    function take() {
        try {
            const status = fs.readFileSync(`/proc/${pid}/status`, 'utf8');
            const stat = fs.readFileSync(`/proc/${pid}/stat`, 'utf8');
            const fields = stat
                .slice(stat.lastIndexOf(')') + 2)
                .trim()
                .split(/\s+/);
            const numeric = (key) => Number(status.match(new RegExp(`^${key}:\\s+(\\d+)`, 'm'))?.[1] || 0);
            totals.peakRssBytes = Math.max(totals.peakRssBytes, numeric('VmRSS') * 1024);
            totals.peakHighWaterRssBytes = Math.max(totals.peakHighWaterRssBytes, numeric('VmHWM') * 1024);
            totals.peakThreads = Math.max(totals.peakThreads, numeric('Threads'));
            totals.userCpuTicks = Math.max(totals.userCpuTicks, Number(fields[11]) || 0);
            totals.systemCpuTicks = Math.max(totals.systemCpuTicks, Number(fields[12]) || 0);
            totals.samples++;
            totals.procAvailable = true;
        } catch (_) {
            /* Host may already have exited; no OS paths or errors leave. */
        }
    }
    take();
    const timer = setInterval(take, totals.sampleIntervalMs);
    timer.unref();
    return {
        take,
        stop() {
            take();
            clearInterval(timer);
            return { ...totals };
        },
    };
}

// Same bounded mechanics as serving_v1's engineering generator, but using ONLY
// the shipped engine/helpers and a fresh namespace. No old study/replay roots,
// old serving_v1 runtime-version guard, frozen fixture file or trained outcomes.
function makeFixtures(f, teacher) {
    const fixtures = [],
        matrix = [];
    for (const [mi, map] of MAPS.entries()) {
        for (const [ci, [variant, fastBid]] of [
            ['original', false],
            ['original', true],
            ['recharged', false],
            ['recharged', true],
        ].entries()) {
            const players = [2, 3, 4, 5, 6][(mi + ci) % 5];
            const seed = `${NAMESPACE}:fixture:${mi}:${ci}`;
            const options = { map, variant, fastBid, showMoney: true };
            const g = f.E.setup(players, options, seed);
            const initial = json(g);
            const seen = new Set();
            let steps = 0;
            for (; steps < 800 && !f.E.ended(g) && seen.size < KINDS.length; steps++) {
                const player = g.currentPlayers[0],
                    legal = f.legal(g, player);
                const kind =
                    legal.length === 1
                        ? 'forced'
                        : legal.some((m) => m.name === 'ChoosePowerPlant')
                        ? 'nomination'
                        : legal.some((m) => m.name === 'Bid')
                        ? 'bid'
                        : g.phase;
                if (g.newTurn !== false && KINDS.includes(kind) && !seen.has(kind)) {
                    seen.add(kind);
                    fixtures.push({
                        id: `${mi}-${ci}-${kind}`,
                        caseId: `${mi}-${ci}`,
                        map,
                        players,
                        variant,
                        fastBid,
                        kind,
                        player,
                        state: json(g),
                    });
                }
                f.E.move(g, json(teacher.choose(g, player, legal, 'geographic').action), player);
            }
            need(
                KINDS.every((kind) => seen.has(kind)),
                'fixture-coverage'
            );
            matrix.push({ id: `${mi}-${ci}`, map, players, variant, fastBid, seed, options, initial, steps });
        }
    }
    need(fixtures.length === 96 && matrix.length === 16, 'fixture-count');
    return { fixtures, matrix };
}
function decisions(state) {
    return [...state.log, ...(state.hiddenLog || [])]
        .filter((event) => event.type === 'move')
        .map((event) => ({ player: event.player, name: event.move.name, data: event.move.data }));
}
function statusView(raw, replica) {
    need(
        raw && raw.replica === replica && ['idle', 'starting', 'ready', 'fallback', 'closed'].includes(raw.state),
        'status-shape'
    );
    need(raw.circuitReason === null && raw.activeCalls === 0, 'status-health');
    same(
        raw.limits,
        { startupMs: 2000, inferenceMs: 1000, turnMs: 3000, fallbackMs: 1000, maxActiveCalls: 8 },
        'status-limits'
    );
    need(
        raw.diagnostics &&
            COUNTERS.every((name) => Number.isSafeInteger(raw.diagnostics[name]) && raw.diagnostics[name] >= 0),
        'status-counters'
    );
    // Do not copy an open-ended status payload into evidence.
    return {
        replica: raw.replica,
        state: raw.state,
        circuitReason: null,
        activeCalls: 0,
        diagnostics: Object.fromEntries(COUNTERS.map((name) => [name, raw.diagnostics[name]])),
    };
}
function delta(after, before) {
    const result = Object.fromEntries(
        COUNTERS.map((name) => [name, after.diagnostics[name] - before.diagnostics[name]])
    );
    need(
        Object.values(result).every((value) => value >= 0),
        'counter-regression'
    );
    return result;
}
function supportedCounts(counts, turns) {
    need(
        counts.turns === turns &&
            counts.fallbackTurns === 0 &&
            counts.heuristicFallback === 0 &&
            counts.circuitOpenEvents === 0,
        'supported-fallback-or-turn-count'
    );
}

async function execute({ node, host, package: packageDirectory }) {
    need(
        [node, host, packageDirectory].every((p) => typeof p === 'string' && path.isAbsolute(p) && !p.includes('\0')),
        'absolute-inputs'
    );
    host = fs.realpathSync(host);
    packageDirectory = fs.realpathSync(packageDirectory);
    const version = execFileSync(node, ['--version'], {
        cwd: '/',
        env: {},
        encoding: 'utf8',
        timeout: 20000,
        maxBuffer: 1024,
    }).trim();
    need(version === TARGET_NODE, 'target-node');
    const hostFiles = inventory(host);
    const entryRaw = readFile(packageDirectory, 'index.mjs');
    const manifestRaw = readFile(packageDirectory, 'runtime-manifest.json');
    const metadataRaw = readFile(packageDirectory, 'package.json');
    const manifest = JSON.parse(manifestRaw);
    need(
        manifest.schema === 'pg-private-bgs-package-v1' &&
            ['replica1', 'replica2'].includes(manifest.replica) &&
            manifest.targetNode === TARGET_NODE,
        'package-manifest'
    );
    const replica = manifest.replica;
    const metadata = JSON.parse(metadataRaw);
    need(
        metadata.private === true && metadata.main === 'index.mjs' && metadata.engines.node === '24.22.1',
        'package-entry'
    );
    const sources = Object.fromEntries(
        ['host_client.cjs', 'conformance.cjs'].map((name) => [
            name,
            digest(fs.readFileSync(path.join(__dirname, name))),
        ])
    );
    const children = [];
    async function start() {
        const client = new HostClient({
            node,
            hostFile: path.join(host, 'host.ts'),
            entryPoint: path.join(packageDirectory, 'index.mjs'),
        });
        const sampler = sampleProcess(client.pid);
        const record = { client, sampler, resources: null };
        children.push(record);
        await client.ready;
        return record;
    }
    async function finish(record) {
        record.sampler.take();
        const exit = await record.client.close();
        record.resources = record.sampler.stop();
        same(exit, { code: 0, signal: null }, 'host-clean-exit');
    }
    try {
        const primary = await start(),
            client = primary.client;
        // Read helpers only after the EXACT entry has authenticated package bytes
        // inside the real target-Node host. These helpers generate/reference data;
        // no locally imported replacement moveAI is ever invoked.
        const fromPackage = createRequire(path.join(packageDirectory, 'package.json'));
        const wrapper = fromPackage('./engine/dist/wrapper.js');
        const f = fromPackage('./ai/multimap/features.cjs');
        const teacher = fromPackage('./ai/multimap/teacher_v2.cjs');
        const expectedMethods = [
            ...Object.keys(wrapper).filter((key) => typeof wrapper[key] === 'function'),
            'aiStatus',
        ].sort();
        const ready = await client.ready;
        same([...ready.methods].sort(), expectedMethods, 'wrapper-export-preservation');
        need(
            REQUIRED.every((name) => ready.methods.includes(name)),
            'required-exports'
        );
        for (const key of Object.keys(wrapper).filter((key) => typeof wrapper[key] !== 'function')) {
            same(ready.constants[key], json(wrapper[key]), 'wrapper-constant-preservation');
        }
        const readStatus = async (target = client) => statusView(await target.call('aiStatus'), replica);
        const initialStatus = await readStatus();
        need(
            initialStatus.state === 'idle' && COUNTERS.every((key) => initialStatus.diagnostics[key] === 0),
            'fresh-host-status'
        );
        const { fixtures, matrix } = makeFixtures(f, teacher);
        const cold = fixtures.find((fixture) => fixture.kind === 'nomination');
        need(!!cold, 'cold-fixture');
        // Force the first timed move to enter the learned branch (not a forced/fixed turn).
        fixtures.sort((a, b) => Number(b === cold) - Number(a === cold));
        const timing = [],
            results = new Map();
        let moveAICalls = 0,
            sealedVisibleLogChecks = 0,
            atomicActions = 0;
        async function moveAI(target, fixture) {
            const state = json(fixture.state),
                before = json(state);
            const started = performance.now();
            // Exactly the BGS G/player contract: no gameId, revision or model fields.
            const result = await target.call('moveAI', [state, fixture.player]);
            const elapsedMs = performance.now() - started;
            same(state, before, 'caller-input-mutated');
            need(result && result.newTurn === true, 'committed-turn');
            same(result.seed, state.seed, 'game-isolation-seed');
            same(result.options, state.options, 'game-isolation-options');
            need(result.players.length === state.players.length, 'game-isolation-players');
            need(
                !['aiStatus', 'replica', 'diagnostics', 'model', 'modelPath', 'checkpointSha256'].some((key) =>
                    Object.hasOwn(result, key)
                ),
                'state-runtime-fields'
            );
            return { result, elapsedMs };
        }
        async function validateResult(target, fixture, state, track = false) {
            same(await target.call('toSave', [json(state)]), state, 'to-save-exact');
            // All JSON values INCLUDING clocks/timing fields are exact on replay.
            same(await target.call('replay', [json(state)]), state, 'replay-json-exact');
            same(
                await target.call('currentPlayer', [json(state)]),
                json(wrapper.currentPlayer(json(state))),
                'current-player-parity'
            );
            same(await target.call('scores', [json(state)]), json(wrapper.scores(json(state))), 'scores-parity');
            same(await target.call('ended', [json(state)]), wrapper.ended(json(state)), 'ended-parity');
            same(
                await target.call('logLength', [json(state), fixture.player]),
                wrapper.logLength(json(state), fixture.player),
                'log-length-parity'
            );
            for (const player of [fixture.player, -1]) {
                const options = { start: 0, player };
                const slice = await target.call('logSlice', [json(state), options]);
                same(slice, json(wrapper.logSlice(json(state), options)), 'log-slice-parity');
                if (player === -1) need(!Object.hasOwn(slice, 'state'), 'spectator-log-state');
            }
            if (fixture.fastBid && fixture.kind === 'bid' && (state.hiddenLog || []).length > 0) {
                same(state.log, fixture.state.log, 'sealed-visible-log-frozen');
                if (track) sealedVisibleLogChecks++;
            }
            const oldMoves = decisions(fixture.state),
                newMoves = decisions(state);
            same(newMoves.slice(0, oldMoves.length), oldMoves, 'history-prefix');
            need(newMoves.length > oldMoves.length, 'turn-progress');
            if (track) atomicActions += newMoves.length - oldMoves.length;
            const increments = wrapper.timeIncrements(json(state));
            const expected = wrapper.timeIncrements(json(fixture.state));
            expected[fixture.player]++;
            same(increments, expected, 'one-turn-increment');
        }
        for (const item of matrix) {
            const actual = await client.call('init', [item.players, [], item.options, item.seed, null, {}]);
            same(actual, item.initial, 'init-parity');
        }
        // Surface checks for the unchanged non-AI wrapper routes. These disposable
        // states are not passed to the replica and don't alter its counters.
        const base = matrix[0].initial,
            seat = base.currentPlayers[0];
        const tentative = await client.call('move', [json(base), [], seat]);
        need(tentative.newTurn === false, 'tentative-move');
        need((await client.call('toSave', [tentative])) === undefined, 'tentative-to-save');
        const oneMove = f.legal(base, seat)[0];
        const manual = await client.call('move', [json(base), json(oneMove), seat]);
        same(await client.call('replay', [json(manual)]), manual, 'manual-move-replay');
        const dropped = await client.call('dropPlayer', [json(base), (seat + 1) % base.players.length]);
        need(
            dropped.newTurn === true && dropped.players[(seat + 1) % base.players.length].isDropped === true,
            'drop-player'
        );
        same(await client.call('toSave', [json(dropped)]), dropped, 'drop-player-to-save');
        let afterCold;
        for (const fixture of fixtures) {
            const played = await moveAI(client, fixture);
            moveAICalls++;
            timing.push(played.elapsedMs);
            await validateResult(client, fixture, played.result, true);
            results.set(fixture.id, played.result);
            if (fixture === cold) {
                afterCold = await readStatus();
                const counts = delta(afterCold, initialStatus);
                supportedCounts(counts, 1);
                need(counts.learned > 0 && afterCold.state === 'ready', 'cold-learned-branch');
            }
        }
        need(sealedVisibleLogChecks > 0, 'sealed-fixture-coverage');
        const afterTargeted = await readStatus(),
            targetedCounts = delta(afterTargeted, initialStatus);
        supportedCounts(targetedCounts, 96);
        need(targetedCounts.learned > 0 && targetedCounts.fixedV2 > 0, 'targeted-policy-coverage');
        const bursts = [];
        for (const width of [2, 4, 8]) {
            const selected = fixtures.filter((item) => item.kind === 'nomination').slice(0, width);
            need(new Set(selected.map((item) => item.state.seed)).size === width, 'burst-distinct-games');
            const before = await readStatus(),
                started = performance.now();
            const played = await Promise.all(selected.map((item) => moveAI(client, item)));
            moveAICalls += width;
            const elapsedMs = performance.now() - started;
            const after = await readStatus(),
                counts = delta(after, before);
            supportedCounts(counts, width);
            need(counts.learned >= width && after.state === 'ready', 'burst-learned-branch');
            for (const [i, item] of selected.entries()) {
                same(decisions(played[i].result), decisions(results.get(item.id)), 'burst-decision-isolation');
                await validateResult(client, item, played[i].result);
            }
            bursts.push({
                width,
                differentGames: width,
                completedTurns: counts.turns,
                learnedCalls: counts.learned,
                fallbackTurns: counts.fallbackTurns,
                elapsedMs,
                perCallMs: summary(played.map((value) => value.elapsedMs)),
                decisionParity: true,
            });
        }
        const beforeRepeat = await readStatus();
        const repeats = [];
        for (let i = 0; i < 2; i++) {
            const played = await moveAI(client, cold);
            moveAICalls++;
            same(decisions(played.result), decisions(results.get(cold.id)), 'repeat-decision-parity');
            await validateResult(client, cold, played.result);
            repeats.push(played.elapsedMs);
        }
        const repeatCounts = delta(await readStatus(), beforeRepeat);
        supportedCounts(repeatCounts, 2);
        need(repeatCounts.learned >= 2, 'repeat-independent-proposals');
        const supportedFinalStatus = await readStatus();
        supportedCounts(delta(supportedFinalStatus, initialStatus), 112);
        const unsupported = [];
        for (const [name, map, showMoney] of [
            ['hidden-money', 'Germany', false],
            ['outside-map', 'Italy', true],
        ]) {
            const state = await client.call('init', [
                3,
                [],
                { map, variant: 'original', fastBid: false, showMoney },
                `${NAMESPACE}:unsupported:${name}`,
                null,
                {},
            ]);
            const fixture = { state, player: state.currentPlayers[0], fastBid: false, kind: 'unsupported' };
            const before = await readStatus(),
                played = await moveAI(client, fixture);
            moveAICalls++;
            await validateResult(client, fixture, played.result);
            const counts = delta(await readStatus(), before);
            need(
                counts.turns === 1 &&
                    counts.fallbackTurns === 1 &&
                    counts.heuristicFallback > 0 &&
                    counts.learned === 0 &&
                    counts.fixedV2 === 0 &&
                    counts.circuitOpenEvents === 0,
                'unsupported-fallback'
            );
            unsupported.push({
                scope: name,
                map,
                showMoney,
                fallbackTurns: 1,
                learnedCalls: 0,
                heuristicActions: counts.heuristicFallback,
                committed: true,
                replayExact: true,
                elapsedMs: played.elapsedMs,
            });
        }
        const primaryFinalStatus = await readStatus();
        need(primaryFinalStatus.diagnostics.turns === moveAICalls && moveAICalls === 114, 'primary-call-accounting');
        await finish(primary);
        // A genuinely new OS host (not a second API instance in the same process).
        const restarted = await start();
        const restartedInitial = await readStatus(restarted.client);
        need(
            restartedInitial.state === 'idle' && COUNTERS.every((key) => restartedInitial.diagnostics[key] === 0),
            'restart-fresh-status'
        );
        const replayed = await moveAI(restarted.client, cold);
        same(decisions(replayed.result), decisions(results.get(cold.id)), 'restart-decision-parity');
        await validateResult(restarted.client, cold, replayed.result);
        const restartedFinal = await readStatus(restarted.client),
            restartCounts = delta(restartedFinal, restartedInitial);
        supportedCounts(restartCounts, 1);
        need(restartCounts.learned > 0 && restartedFinal.state === 'ready', 'restart-learned-branch');
        await finish(restarted);
        // Identity evidence covers retained, unchanged inputs before AND after use.
        same(inventory(host), hostFiles, 'host-changed-during-run');
        need(
            digest(readFile(packageDirectory, 'index.mjs')) === digest(entryRaw) &&
                digest(readFile(packageDirectory, 'runtime-manifest.json')) === digest(manifestRaw),
            'package-changed-during-run'
        );
        return {
            schema: 'pg-private-bgs-host-conformance-v1',
            namespace: NAMESPACE,
            status: 'passed',
            replica,
            publication: false,
            bgsDeployed: false,
            strengthEvaluation: false,
            independentStrengthObservations: 0,
            actualUnchangedHostValidated: true,
            shippedEntryValidated: true,
            hostSource: { ...HOST_SOURCE, files: hostFiles },
            packageIdentity: {
                entry: 'index.mjs',
                entrySha256: digest(entryRaw),
                runtimeManifestSha256: digest(manifestRaw),
                packageJsonSha256: digest(metadataRaw),
            },
            harnessSourceSha256: sources,
            runtimes: {
                hostNode: version,
                harnessNode: process.version,
                platform: process.platform,
                arch: process.arch,
            },
            isolation: {
                childEnvironmentKeys: 0,
                cwd: '/',
                oldSpaceMiB: 400,
                networkNamespaceEnforced: false,
                readOnlyFilesystemEnforced: false,
                memory512MiBEnforced: false,
                oneCpuQuotaEnforced: false,
                pids64Enforced: false,
                exactProductionSandboxValidated: false,
            },
            protocol: {
                transport: 'stdio-jsonl',
                outputFraming: 'RS+bgs-engine+space',
                readyDeadlineMs: LIMITS.readyMs,
                callDeadlineMs: LIMITS.callMs,
                lineLimitBytes: LIMITS.lineBytes,
                stateLimitBytes: LIMITS.stateBytes,
                inheritedCredentials: false,
                implicitRetries: 0,
                requiredMethods: REQUIRED,
                preservedWrapperMethods: expectedMethods.filter((name) => name !== 'aiStatus'),
            },
            scope: {
                maps: MAPS,
                players: [2, 3, 4, 5, 6],
                variants: ['original', 'recharged'],
                fastBid: [false, true],
                cases: matrix.map(({ id, map, players, variant, fastBid, steps }) => ({
                    id,
                    map,
                    players,
                    variant,
                    fastBid,
                    generationAtomicSteps: steps,
                })),
                targetedPositions: fixtures.length,
                kinds: KINDS,
                fullGames: 0,
                oldStudyInputsUsed: false,
            },
            targeted: {
                committedTurns: 96,
                atomicActions,
                replayJsonExact: 96,
                toSaveExact: 96,
                callerInputsUnchanged: 96,
                wrapperReadParity: 96,
                sealedVisibleLogChecks,
                learnedCalls: targetedCounts.learned,
                fixedV2Actions: targetedCounts.fixedV2,
                fallbackTurns: 0,
                coldReadyMs: client.metrics.readyMs,
                coldMoveMs: timing[0],
                fullTurnMs: summary(timing),
                replayEquality: 'all JSON values exact, including clocks; object property order immaterial',
            },
            concurrency: {
                bursts,
                noCrossGameStateContamination: true,
                workerStarts: null,
                workerStartEvidence: 'not exposed by aiStatus; singleton separately unit-tested, not measured here',
                completedCallCounterChecked: true,
            },
            repeatedState: {
                independentProposals: 2,
                learnedCalls: repeatCounts.learned,
                decisionParity: true,
                durableDeduplicationClaimed: false,
                exactlyOnceClaimed: false,
                perCallMs: summary(repeats),
            },
            unsupported,
            restart: {
                newHostProcess: true,
                coldReadyMs: restarted.client.metrics.readyMs,
                coldMoveMs: replayed.elapsedMs,
                learnedCalls: restartCounts.learned,
                fallbackTurns: 0,
                replayExact: true,
                decisionParity: true,
                comparison: 'move player/name/data sequence; wall-clock fields excluded ONLY for cross-run decisions',
            },
            accounting: {
                primaryMoveAICalls: moveAICalls,
                restartMoveAICalls: 1,
                totalMoveAICalls: moveAICalls + 1,
                supportedPrimaryStatus: supportedFinalStatus,
                primaryFinalStatus,
                restartFinalStatus: restartedFinal,
            },
            resources: {
                primary: primary.resources,
                restart: restarted.resources,
                note: 'External /proc process samples include worker threads; peaks are observed, not enforced sandbox budgets.',
            },
            transport: { primary: client.metrics, restart: restarted.client.metrics },
        };
    } finally {
        for (const record of children) {
            await record.client.close().catch(() => {});
            if (!record.resources) record.resources = record.sampler.stop();
        }
    }
}
async function runConformance(options) {
    try {
        need(
            options &&
                typeof options === 'object' &&
                !Array.isArray(options) &&
                Object.keys(options).every((key) => ['node', 'host', 'package'].includes(key)),
            'arguments'
        );
        return await execute(options);
    } catch (error) {
        if (error instanceof ConformanceError) throw error;
        if (error instanceof HostClientError) throw new ConformanceError(error.code);
        // Engine assertions, native loader output, paths and raw state are private.
        throw new ConformanceError('execution-failed');
    }
}
module.exports = { runConformance, NAMESPACE, HOST_SOURCE };
if (require.main === module) {
    (async () => {
        const args = process.argv.slice(2);
        need(
            args.length === 8 &&
                args[0] === '--node' &&
                args[2] === '--host' &&
                args[4] === '--package' &&
                args[6] === '--output',
            'cli-arguments'
        );
        const output = path.resolve(args[7]);
        // Reserve a new private output BEFORE running. A failure never overwrites
        // another run's evidence and writes only a sanitized failure vocabulary.
        const fd = fs.openSync(output, 'wx', 0o600);
        try {
            const report = await runConformance({
                node: args[1],
                host: path.resolve(args[3]),
                package: path.resolve(args[5]),
            });
            fs.writeFileSync(fd, JSON.stringify(report, null, 4) + '\n');
            process.stdout.write(
                JSON.stringify({
                    schema: report.schema,
                    status: report.status,
                    replica: report.replica,
                    targetedTurns: report.targeted.committedTurns,
                    totalMoveAICalls: report.accounting.totalMoveAICalls,
                    learnedCalls:
                        report.accounting.primaryFinalStatus.diagnostics.learned + report.restart.learnedCalls,
                    supportedFallbackTurns: 0,
                    exactProductionSandboxValidated: false,
                }) + '\n'
            );
        } catch (error) {
            const code = error instanceof ConformanceError ? error.code : 'conformance-output-failed';
            fs.writeFileSync(
                fd,
                JSON.stringify({ schema: 'pg-private-bgs-host-conformance-v1', status: 'failed', code }) + '\n'
            );
            throw new ConformanceError(code.replace(/^conformance-/, ''));
        } finally {
            fs.closeSync(fd);
        }
    })().catch((error) => {
        process.stderr.write(
            JSON.stringify({
                status: 'failed',
                code: error instanceof ConformanceError ? error.code : 'conformance-cli-failed',
            }) + '\n'
        );
        process.exitCode = 1;
    });
}
