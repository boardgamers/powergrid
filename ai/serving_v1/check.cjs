'use strict';
// Node-only parity/turn smoke harness. It never runs Python or evaluates game winners.
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const { randomBytes } = require('node:crypto');
const { performance } = require('node:perf_hooks');
const { OnnxPolicy, OnnxTransport, validateResponse } = require('./onnx.cjs');
const { ReplicaBot, MemoryHost } = require('./adapter.cjs');
const { makeFixtures, NAMESPACE } = require('./fixtures.cjs');
const { loadIdentity, SHAS, hash, canonical, cloneState, requireThat } = require('./identity.cjs');
const wrapper = require('../../engine/dist/wrapper.js');
const ABS = 2e-5,
    REL = 1e-6;
function stats(values) {
    const sorted = [...values].sort((a, b) => a - b);
    return {
        n: sorted.length,
        p50: sorted[Math.ceil(sorted.length * 0.5) - 1],
        p95: sorted[Math.ceil(sorted.length * 0.95) - 1],
        max: sorted.at(-1),
    };
}
async function check({ modelDirectory, exportManifestSha256, fixturesFile, referenceFile }) {
    for (const file of [fixturesFile, referenceFile])
        requireThat(fs.statSync(file).size < 16 * 1024 * 1024, 'reference-size');
    const identity = loadIdentity(),
        referenceBytes = fs.readFileSync(referenceFile),
        fixtureBytes = fs.readFileSync(fixturesFile);
    requireThat(referenceBytes.length < 16 * 1024 * 1024 && fixtureBytes.length < 16 * 1024 * 1024, 'reference-size');
    const reference = JSON.parse(referenceBytes);
    requireThat(
        reference.schema === 'pg-replica-pytorch-reference-v1' &&
            reference.sourceManifestSha256 === identity.manifestSha256 &&
            reference.fixturesInputHashMode === 'raw-file-bytes' &&
            reference.fixturesInputSha256 === hash(fixtureBytes),
        'reference-identity'
    );
    const fixtures = makeFixtures(),
        observations = fixtures.filter((x) => x.observation);
    const supplied = JSON.parse(fixtureBytes);
    assert.equal(supplied.schema, 'pg-serving-engineering-fixtures-v1');
    assert.equal(supplied.namespace, NAMESPACE);
    assert.deepEqual(
        supplied.fixtures.map(({ id, observation }) => ({ id, observation })),
        observations.map(({ id, observation }) => ({ id, observation }))
    );
    assert.deepEqual(
        reference.fixtures.map((x) => x.id),
        observations.map((x) => x.id)
    );
    const report = {
        schema: 'pg-node-serving-check-v1',
        namespace: NAMESPACE,
        strengthEvaluation: false,
        weightsChanged: false,
        productionPython: false,
        bgsDeployed: false,
        targetHostValidated: false,
        sourceManifestSha256: identity.manifestSha256,
        exportManifestSha256,
        referenceSha256: hash(referenceBytes),
        fixturesInputSha256: hash(fixtureBytes),
        observationSha256: hash(canonical(observations.map((x) => ({ id: x.id, observation: x.observation })))),
        tolerance: { absolute: ABS, relative: REL, selectedIndex: 'exact' },
        runtimes: { node: process.version, ort: '1.31.1', platform: process.platform, arch: process.arch },
        scope: {
            maps: [...new Set(fixtures.map((x) => x.map))],
            players: [...new Set(fixtures.map((x) => x.players))],
            variants: ['original', 'recharged'],
            fastBid: [false, true],
            independentStrengthObservations: 0,
            fixtures: fixtures.length,
            tensorFixtures: observations.length,
            normallyLearnedTensorFixtures: observations.filter((x) =>
                ['nomination', 'bid', 'Building'].includes(x.kind)
            ).length,
        },
        replicas: {},
    };
    for (const replica of Object.keys(SHAS)) {
        assert.equal(reference.replicas[replica].checkpointSha256, SHAS[replica]);
        const before = process.memoryUsage().rss,
            started = performance.now();
        const transport = new OnnxTransport({ replica, modelDirectory, exportManifestSha256 });
        let policy;
        try {
            await transport.ready;
            const coldStartMs = performance.now() - started,
                residentAfterWorkerReady = process.memoryUsage().rss;
            policy = await OnnxPolicy.create({ replica, modelDirectory, exportManifestSha256 });
            const requestMs = [],
                turnMs = [],
                firstActions = [];
            let maxLogitError = 0,
                maxValueError = 0,
                actionsValidated = 0,
                learnedRequests = 0;
            for (const [i, fixture] of observations.entries()) {
                const expected = reference.fixtures[i].replicas[replica],
                    actual = await policy.evaluate(fixture.observation);
                assert.equal(actual.index, expected.index, `${replica}/${fixture.id}: ONNX argmax`);
                assert.equal(actual.logits.length, expected.logits.length);
                for (let j = 0; j < actual.logits.length; j++) {
                    const delta = Math.abs(actual.logits[j] - expected.logits[j]);
                    assert(delta <= ABS + REL * Math.abs(expected.logits[j]), `${replica}/${fixture.id}: logits`);
                    maxLogitError = Math.max(maxLogitError, delta);
                }
                maxValueError = Math.max(maxValueError, Math.abs(actual.value - expected.value));
                assert(Math.abs(actual.value - expected.value) <= ABS + REL * Math.abs(expected.value));
                const request = {
                    schema: 'pg-replica-serving-request-v1',
                    requestId: randomBytes(32).toString('hex'),
                    replica,
                    observation: fixture.observation,
                };
                const start = performance.now(),
                    response = await transport.request(request);
                requestMs.push(performance.now() - start);
                assert.equal(
                    validateResponse(response, request),
                    expected.index,
                    `${replica}/${fixture.id}: worker argmax`
                );
                firstActions.push({ id: fixture.id, index: response.index });
            }
            const bot = new ReplicaBot({ replica, transport });
            for (const fixture of fixtures) {
                const host = new MemoryHost();
                host.add(fixture.id, fixture.state);
                const start = performance.now();
                const request = { gameId: fixture.id, revision: 0, player: fixture.player };
                const receipt = await host.play(bot, request);
                turnMs.push(performance.now() - start);
                assert.equal(receipt.diagnostics.fallback, false, `${replica}/${fixture.id}: unexpected fallback`);
                const saved = host.snapshot(fixture.id);
                assert.equal(saved.revision, 1);
                assert.deepEqual(cloneState(wrapper.replay(cloneState(saved.state))), saved.state);
                assert.strictEqual(await host.play(bot, request), receipt);
                assert.equal(host.snapshot(fixture.id).revision, 1);
                actionsValidated += receipt.moves.length;
                learnedRequests += receipt.diagnostics.counts.learned;
            }
            report.replicas[replica] = {
                checkpointSha256: SHAS[replica],
                tensorComparisons: observations.length,
                exactIndices: observations.length,
                maxLogitError,
                maxValueError,
                coldStartMs,
                roundTripMs: stats(requestMs),
                committedTurnMs: stats(turnMs),
                turnsValidated: fixtures.length,
                actionsValidated,
                learnedRequests,
                fallbacks: 0,
                indexDigest: hash(canonical(firstActions)),
                memory: {
                    beforeWorkerRssBytes: before,
                    afterWorkerReadyRssBytes: residentAfterWorkerReady,
                    checkProcessRssBytes: process.memoryUsage().rss,
                    processMaxRssKiB: process.resourceUsage().maxRSS,
                },
            };
        } finally {
            transport.close();
            if (policy) await policy.close();
        }
    }
    return report;
}
module.exports = { check };
if (require.main === module) {
    const args = process.argv.slice(2);
    requireThat(
        args.length === 10 &&
            args[0] === '--models' &&
            args[2] === '--manifest-sha' &&
            args[4] === '--fixtures' &&
            args[6] === '--reference' &&
            args[8] === '--output',
        'check-arguments'
    );
    const output = path.resolve(args[9]);
    requireThat(!fs.existsSync(output), 'check-output-exists');
    check({ modelDirectory: args[1], exportManifestSha256: args[3], fixturesFile: args[5], referenceFile: args[7] })
        .then((report) => {
            fs.writeFileSync(output, JSON.stringify(report, null, 4) + '\n', { flag: 'wx', mode: 0o600 });
            console.log(JSON.stringify({ status: 'passed', replicas: report.replicas }));
        })
        .catch(() => {
            console.error('serving-check-failed');
            process.exitCode = 1;
        });
}
