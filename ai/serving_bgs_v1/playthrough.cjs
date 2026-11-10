'use strict';
// Bounded fresh full-game integration runs, NOT a strength comparison or study replay.
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const { createHash } = require('node:crypto');
const { performance } = require('node:perf_hooks');
const { HostClient } = require('./host_client.cjs');
const { HOST_SOURCE } = require('./conformance.cjs');
const hash = (raw) => createHash('sha256').update(raw).digest('hex');
async function playthrough({ node, host, package: directory }) {
    assert.equal(process.version, 'v24.22.1');
    for (const [name, sha] of Object.entries(HOST_SOURCE.sha256))
        assert.equal(hash(fs.readFileSync(path.join(host, name))), sha);
    const manifestRaw = fs.readFileSync(path.join(directory, 'runtime-manifest.json'));
    const manifest = JSON.parse(manifestRaw);
    const client = new HostClient({
        node,
        hostFile: path.join(host, 'host.ts'),
        entryPoint: path.join(directory, 'index.mjs'),
    });
    const report = {
        schema: 'pg-bgs-playthrough-v1',
        node: process.version,
        replica: manifest.replica,
        namespace: 'pg-bgs-serving-v1:playthrough',
        strengthEvaluation: false,
        productionSandboxValidated: false,
        runtimeManifestSha256: hash(manifestRaw),
        sourceSha256: hash(fs.readFileSync(__filename)),
        limits: { games: 8, turnsPerGame: 400, totalWallMs: 540000 },
        games: [],
        turns: 0,
        replayChecks: 0,
        transientMessageChecks: 0,
        replayComparison:
            'All JSON including clocks, except transient pendingMessages intentionally cleared by unchanged wrapper.replay',
        maxMoveMs: 0,
        peakObservedRssBytes: 0,
        peakObservedThreads: 0,
    };
    const started = performance.now();
    function sample() {
        const status = fs.readFileSync(`/proc/${client.pid}/status`, 'utf8');
        report.peakObservedRssBytes = Math.max(
            report.peakObservedRssBytes,
            Number(status.match(/^VmRSS:\s+(\d+)/m)?.[1] || 0) * 1024
        );
        report.peakObservedThreads = Math.max(
            report.peakObservedThreads,
            Number(status.match(/^Threads:\s+(\d+)/m)?.[1] || 0)
        );
    }
    async function checkReplay(state) {
        const expected = structuredClone(state);
        if (Object.hasOwn(expected, 'pendingMessages')) {
            const drained = await client.call('messages', [state]);
            assert.deepEqual(drained.messages, expected.pendingMessages);
            report.transientMessageChecks++;
            delete expected.pendingMessages;
            assert.deepEqual(drained.data, expected);
        }
        assert.deepEqual(await client.call('replay', [state]), expected);
        report.replayChecks++;
    }
    try {
        await client.ready;
        for (const [mi, map] of ['Germany', 'USA', 'France', 'UK & Ireland'].entries()) {
            for (const [ci, [variant, fastBid]] of [
                ['original', false],
                ['recharged', true],
            ].entries()) {
                const players = [2, 3, 4, 5, 6][(mi + ci) % 5];
                const seed = `${report.namespace}:${mi}:${ci}`;
                let state = await client.call('init', [
                    players,
                    [],
                    { map, variant, fastBid, showMoney: true },
                    seed,
                    null,
                    {},
                ]);
                let turns = 0;
                while (!(await client.call('ended', [state]))) {
                    assert(
                        turns < report.limits.turnsPerGame && performance.now() - started < report.limits.totalWallMs,
                        'playthrough-budget'
                    );
                    const current = await client.call('currentPlayer', [state]);
                    const player = Array.isArray(current) ? current[0] : current;
                    assert(Number.isInteger(player));
                    const start = performance.now();
                    const next = await client.call('moveAI', [state, player]);
                    report.maxMoveMs = Math.max(report.maxMoveMs, performance.now() - start);
                    assert.equal(next.newTurn, true);
                    assert.equal(next.seed, seed);
                    assert.notDeepEqual(next, state);
                    state = await client.call('toSave', [next]);
                    assert.deepEqual(state, next);
                    turns++;
                    report.turns++;
                    sample();
                    if (turns % 25 === 0) await checkReplay(state);
                }
                await checkReplay(state);
                report.games.push({
                    map,
                    players,
                    variant,
                    fastBid,
                    seed,
                    turns,
                    ended: true,
                    persistentReplayExact: true,
                });
                const status = await client.call('aiStatus');
                assert.equal(status.circuitReason, null);
                assert.equal(status.diagnostics.fallbackTurns, 0);
                assert.equal(status.diagnostics.turns, report.turns);
            }
        }
        report.status = await client.call('aiStatus');
        assert(report.status.diagnostics.learned > 0 && report.status.diagnostics.fixedV2 > 0);
        report.elapsedMs = performance.now() - started;
        assert.deepEqual(await client.close(), { code: 0, signal: null });
        return report;
    } catch (cause) {
        report.failed = true;
        report.failureKind = cause.code === 'ERR_ASSERTION' ? 'assertion' : 'host-or-runtime';
        report.failureLine = Number(cause.stack?.match(/playthrough\.cjs:(\d+):/)?.[1]) || null;
        const error = new Error('playthrough-failed');
        error.report = report;
        error.cause = cause;
        throw error;
    } finally {
        await client.close();
    }
}
module.exports = { playthrough };
if (require.main === module) {
    const args = process.argv.slice(2);
    assert(
        args.length === 8 &&
            args[0] === '--node' &&
            args[2] === '--host' &&
            args[4] === '--package' &&
            args[6] === '--output'
    );
    const fd = fs.openSync(args[7], 'wx', 0o600);
    playthrough({ node: path.resolve(args[1]), host: path.resolve(args[3]), package: path.resolve(args[5]) })
        .then((report) => {
            fs.writeFileSync(fd, JSON.stringify(report, null, 4) + '\n');
            console.log(
                JSON.stringify({
                    replica: report.replica,
                    games: report.games.length,
                    turns: report.turns,
                    replayChecks: report.replayChecks,
                    fallbackTurns: report.status.diagnostics.fallbackTurns,
                })
            );
        })
        .catch((error) => {
            fs.writeFileSync(
                fd,
                JSON.stringify(error.report || { schema: 'pg-bgs-playthrough-v1', failed: true }, null, 4) + '\n'
            );
            console.error('playthrough-failed');
            process.exitCode = 1;
        })
        .finally(() => fs.closeSync(fd));
}
