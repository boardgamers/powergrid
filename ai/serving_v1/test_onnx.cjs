'use strict';
// No games or study replays. Synthetic public tensors plus optional exported models.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const Module = require('node:module');
const { EventEmitter } = require('node:events');
const {
    OnnxPolicy,
    OnnxTransport,
    validateObservation,
    validateRequest,
    validateResponse,
    INPUT_NAMES,
} = require('./onnx.cjs');
const { RequestSession } = require('./onnx_worker.cjs');
const { SHAS, ROOT, hash, canonical, loadIdentity } = require('./identity.cjs');

function observation(P = 2, N = 1, A = 2) {
    return {
        schema: 'multimap-graph-v1',
        global: Array(273).fill(0),
        players: Array.from({ length: P }, () => Array(80).fill(0)),
        nodes: Array.from({ length: N }, () => Array(36).fill(0)),
        relations: Array.from({ length: 4 }, () => Array.from({ length: N }, () => Array(N).fill(0))),
        actions: Array.from({ length: A }, () => Array(34).fill(0)),
        actionCity: Array.from({ length: A }, (_, i) => (i % 2 ? N - 1 : -1)),
        prior: Array.from({ length: A }, (_, i) => (i ? -20 : 0)),
    };
}
function request(id = 1, obs = observation(), replica = 'replica1') {
    return {
        schema: 'pg-replica-serving-request-v1',
        requestId: id.toString(16).padStart(64, '0'),
        replica,
        observation: obs,
    };
}
function response(req, index = 0) {
    return {
        schema: 'pg-replica-serving-response-v1',
        requestId: req.requestId,
        replica: req.replica,
        checkpointSha256: SHAS[req.replica],
        index,
        actionCount: req.observation.actions.length,
    };
}
function options(extra = {}) {
    return {
        replica: 'replica1',
        modelDirectory: '/unused-in-fake-worker',
        exportManifestSha256: 'a'.repeat(64),
        ...extra,
    };
}
function workerFixture({ ready = true, onRequest, failConstructor = false, readyPatch = {} } = {}) {
    const instances = [];
    class FakeWorker extends EventEmitter {
        constructor(filename, opts) {
            super();
            if (failConstructor) throw new Error('private constructor detail');
            this.filename = filename;
            this.options = opts;
            this.sent = [];
            this.terminated = 0;
            this.stdout = new EventEmitter();
            this.stderr = new EventEmitter();
            instances.push(this);
            if (ready)
                queueMicrotask(() =>
                    this.emit('message', {
                        schema: 'pg-replica-serving-ready-v1',
                        replica: opts.workerData.replica,
                        checkpointSha256: SHAS[opts.workerData.replica],
                        manifestSha256: opts.workerData.sourceManifestSha256,
                        ...readyPatch,
                    })
                );
        }
        postMessage(raw) {
            assert.equal(typeof raw, 'string');
            const req = JSON.parse(raw);
            this.sent.push(req);
            if (onRequest) onRequest(this, req);
            else queueMicrotask(() => this.emit('message', response(req)));
        }
        terminate() {
            this.terminated++;
            return Promise.resolve(1);
        }
    }
    return { WorkerConstructor: FakeWorker, instances };
}

// Mock only the native ORT module, not source/runtime guards or filesystem checks.
// The production API has no model-parser injection hook.
function mockBackend({ output, createHook, names = INPUT_NAMES, version = '1.31.1' } = {}) {
    const calls = { create: [], run: [], tensors: [], released: 0 };
    class Tensor {
        constructor(type, data, dims) {
            this.type = type;
            this.data = data;
            this.dims = dims;
            calls.tensors.push(this);
        }
        dispose() {
            this.disposed = true;
        }
    }
    const ort = {
        Tensor,
        env: { versions: { node: version, common: version } },
        InferenceSession: {
            async create(bytes, opts) {
                calls.create.push({ bytes: Buffer.from(bytes), options: opts });
                createHook?.(bytes);
                return {
                    inputNames: [...names],
                    outputNames: ['logits', 'value'],
                    async run(feeds) {
                        calls.run.push(feeds);
                        if (output) return output(feeds, Tensor);
                        return {
                            logits: new Tensor(
                                'float32',
                                Float32Array.from({ length: feeds.actions.dims[1] }, (_, i) => (i ? 2 : -1)),
                                [1, feeds.actions.dims[1]]
                            ),
                            value: new Tensor('float32', new Float32Array([0.25]), [1]),
                        };
                    },
                    async release() {
                        calls.released++;
                    },
                };
            },
        },
    };
    const filename = path.join(__dirname, 'onnx.cjs');
    const loaded = new Module(filename, module);
    loaded.filename = filename;
    loaded.paths = Module._nodeModulePaths(__dirname);
    const actualRequire = loaded.require.bind(loaded);
    loaded.require = (name) =>
        name === 'onnxruntime-node'
            ? ort
            : name === 'onnxruntime-node/package.json'
            ? { version }
            : actualRequire(name);
    loaded._compile(fs.readFileSync(filename, 'utf8'), filename);
    return { ...loaded.exports, calls };
}
function bundle(t) {
    const modelDirectory = fs.mkdtempSync(path.join(os.tmpdir(), 'pg-onnx-test-'));
    t.after(() => fs.rmSync(modelDirectory, { recursive: true, force: true }));
    const manifest = {
        schema: 'pg-replica-onnx-export-v1',
        sourceManifestSha256: loadIdentity().manifestSha256,
        replicas: {},
    };
    for (const replica of Object.keys(SHAS)) {
        const bytes = Buffer.from(`Synthetic parser fixture for ${replica}, NOT an ONNX model.`);
        const file = `${replica}.onnx`;
        fs.writeFileSync(path.join(modelDirectory, file), bytes);
        manifest.replicas[replica] = {
            file,
            bytes: bytes.length,
            sha256: hash(bytes),
            checkpointSha256: SHAS[replica],
        };
    }
    function save() {
        const raw = JSON.stringify(manifest);
        fs.writeFileSync(path.join(modelDirectory, 'export-manifest.json'), raw);
        return { replica: 'replica1', modelDirectory, exportManifestSha256: hash(raw) };
    }
    return { manifest, save, options: save(), modelDirectory };
}

const errorCode = (code) => (error) => error.code === code;

test('observation validator accepts minimum/maximum dimensions and strict float32 range', () => {
    assert.deepEqual(validateObservation(observation()), { players: 2, nodes: 1, actions: 2 });
    assert.deepEqual(validateObservation(observation(6, 64, 4096)), { players: 6, nodes: 64, actions: 4096 });
    const obs = observation();
    obs.global[0] = 3.4028234663852886e38;
    obs.global[1] = -3.4028234663852886e38;
    validateObservation(obs);
});

test('observation validator rejects shape, hidden keys, booleans, nonfinite and invalid index/prior values', () => {
    const changes = [
        (o) => {
            o.secret = 'no';
        },
        (o) => {
            delete o.schema;
        },
        (o) => {
            o.schema = 'wrong';
        },
        (o) => {
            o.global = new Float32Array(273);
        },
        (o) => {
            o.global.pop();
        },
        (o) => {
            o.global[0] = true;
        },
        (o) => {
            o.global[0] = NaN;
        },
        (o) => {
            o.global[0] = Infinity;
        },
        (o) => {
            o.global[0] = 3.402824e38;
        },
        (o) => {
            delete o.global[2];
        },
        (o) => {
            o.players.length = 1;
        },
        (o) => {
            o.players = Array(7).fill(o.players[0]);
        },
        (o) => {
            o.players[1].pop();
        },
        (o) => {
            o.nodes = [];
        },
        (o) => {
            o.nodes = Array(65).fill(o.nodes[0]);
        },
        (o) => {
            o.actions.pop();
        },
        (o) => {
            o.actions = Array(4097).fill(o.actions[0]);
        },
        (o) => {
            o.actions[0].pop();
        },
        (o) => {
            o.relations.pop();
        },
        (o) => {
            o.relations[0] = [];
        },
        (o) => {
            o.relations[0][0].push(0);
        },
        (o) => {
            o.actionCity = [];
        },
        (o) => {
            o.actionCity[0] = 1;
        },
        (o) => {
            o.actionCity[0] = -2;
        },
        (o) => {
            o.actionCity[0] = 0.1;
        },
        (o) => {
            o.actionCity[0] = false;
        },
        (o) => {
            o.actionCity[0] = '0';
        },
        (o) => {
            o.prior.pop();
        },
        (o) => {
            o.prior[1] = -20.01;
        },
        (o) => {
            o.prior[1] = 0.01;
        },
        (o) => {
            o.prior[0] = -1;
        },
        (o) => {
            o.prior[0] = null;
        },
    ];
    for (const change of changes) {
        const obs = observation();
        change(obs);
        assert.throws(() => validateObservation(obs));
    }
    assert.throws(() => validateObservation(null));
    assert.throws(() => validateRequest({ ...request(), G: {} }, 'replica1'));
    assert.throws(() => validateRequest(request(), 'replica2'));
});

test('defensive response binding validates every field, first index zero, and exact keys', () => {
    const req = request();
    const res = response(req);
    assert.equal(validateResponse(res, req), 0);
    for (const change of [
        { schema: 'bad' },
        { requestId: 'f'.repeat(64) },
        { replica: 'replica2' },
        { checkpointSha256: SHAS.replica2 },
        { index: 2 },
        { index: -1 },
        { index: 0.5 },
        { index: true },
        { actionCount: 3 },
        { logits: [1, 2] },
        { value: 0.5 },
    ]) {
        assert.throws(() => validateResponse({ ...res, ...change }, req), errorCode('worker-response'));
    }
});

test('policy requires explicit replica/directory/trusted export digest before loading native code', async () => {
    for (const opts of [
        undefined,
        {},
        options({ replica: undefined }),
        options({ replica: 'auto' }),
        options({ modelDirectory: '' }),
        options({ modelDirectory: '../model' }),
        options({ exportManifestSha256: undefined }),
        options({ exportManifestSha256: 'A'.repeat(64) }),
    ]) {
        await assert.rejects(OnnxPolicy.create(opts), errorCode('onnx-config'));
    }
    assert.throws(() => new OnnxPolicy(), errorCode('onnx-create-required'));
});

test('policy authenticates owned bytes then feeds ten exact CPU tensors, first argmax and closes', async (t) => {
    const fixture = bundle(t);
    const backend = mockBackend({
        createHook(bytes) {
            fs.writeFileSync(path.join(fixture.modelDirectory, 'replica1.onnx'), 'changed after verification');
            assert.equal(hash(bytes), fixture.manifest.replicas.replica1.sha256);
        },
    });
    const policy = await backend.OnnxPolicy.create(fixture.options);
    t.after(() => policy.close());
    assert.equal(policy.replica, 'replica1');
    assert.equal(policy.checkpointSha256, SHAS.replica1);
    assert.equal(policy.exportManifestSha256, fixture.options.exportManifestSha256);
    assert.deepEqual(backend.calls.create[0].options, {
        executionProviders: ['cpu'],
        intraOpNumThreads: 1,
        interOpNumThreads: 1,
        executionMode: 'sequential',
        enableProfiling: false,
        logSeverityLevel: 3,
    });
    const obs = observation(6, 4, 3);
    obs.global[0] = 0.1;
    const pending = policy.evaluate(obs);
    obs.global[0] = 99;
    assert.deepEqual(await pending, { index: 1, logits: [-1, 2, 2], value: 0.25 });
    const feeds = backend.calls.run[0];
    assert.deepEqual(Object.keys(feeds).sort(), [...INPUT_NAMES].sort());
    for (const [name, dims] of Object.entries({
        global: [1, 273],
        players: [1, 6, 80],
        nodes: [1, 4, 36],
        relations: [1, 4, 4, 4],
        actions: [1, 3, 34],
        actionCity: [1, 3],
        prior: [1, 3],
        nodeMask: [1, 4],
        playerMask: [1, 6],
        actionMask: [1, 3],
    })) {
        assert.deepEqual(feeds[name].dims, dims);
        assert.equal(feeds[name].type, name === 'actionCity' ? 'int64' : name.endsWith('Mask') ? 'bool' : 'float32');
        assert.equal(feeds[name].disposed, true);
    }
    assert.deepEqual([...feeds.actionCity.data], [-1n, 3n, -1n]);
    assert.equal(feeds.global.data[0], Math.fround(0.1));
    for (const name of ['nodeMask', 'playerMask', 'actionMask']) assert.ok([...feeds[name].data].every((v) => v === 1));
    const tensorsBefore = backend.calls.tensors.length;
    const invalid = observation();
    invalid.prior[0] = 1;
    await assert.rejects(policy.evaluate(invalid));
    assert.equal(backend.calls.tensors.length, tensorsBefore, 'invalid observation must allocate no tensors');
    await policy.release();
    await policy.close();
    assert.equal(backend.calls.released, 1);
    assert.equal(policy.closed, true);
    await assert.rejects(policy.evaluate(observation()), errorCode('onnx-closed'));
});

test('bundle authentication rejects checksum, identity, size, traversal and links before parsing', async (t) => {
    const scenarios = {
        'wrong trusted manifest digest': (f) => ({ ...f.options, exportManifestSha256: '0'.repeat(64) }),
        'source identity': (f) => {
            f.manifest.sourceManifestSha256 = '0'.repeat(64);
            return f.save();
        },
        'checkpoint identity': (f) => {
            f.manifest.replicas.replica1.checkpointSha256 = SHAS.replica2;
            return f.save();
        },
        'other role checkpoint identity': (f) => {
            f.manifest.replicas.replica2.checkpointSha256 = SHAS.replica1;
            return f.save();
        },
        'path traversal': (f) => {
            f.manifest.replicas.replica1.file = '../replica1.onnx';
            return f.save();
        },
        'missing role': (f) => {
            delete f.manifest.replicas.replica2;
            return f.save();
        },
        'oversized metadata': (f) => {
            f.manifest.replicas.replica1.bytes = 4 * 1024 * 1024 + 1;
            return f.save();
        },
        'model checksum': (f) => {
            f.manifest.replicas.replica1.sha256 = '0'.repeat(64);
            return f.save();
        },
        'model size': (f) => {
            fs.appendFileSync(path.join(f.modelDirectory, 'replica1.onnx'), 'x');
            return f.options;
        },
        'symlink model': (f) => {
            fs.renameSync(path.join(f.modelDirectory, 'replica1.onnx'), path.join(f.modelDirectory, 'real.onnx'));
            fs.symlinkSync('real.onnx', path.join(f.modelDirectory, 'replica1.onnx'));
            return f.options;
        },
        'hardlink model': (f) => {
            fs.linkSync(path.join(f.modelDirectory, 'replica1.onnx'), path.join(f.modelDirectory, 'alias.onnx'));
            return f.options;
        },
        'directory model': (f) => {
            fs.unlinkSync(path.join(f.modelDirectory, 'replica1.onnx'));
            fs.mkdirSync(path.join(f.modelDirectory, 'replica1.onnx'));
            return f.options;
        },
        'symlink manifest': (f) => {
            fs.renameSync(
                path.join(f.modelDirectory, 'export-manifest.json'),
                path.join(f.modelDirectory, 'real.json')
            );
            fs.symlinkSync('real.json', path.join(f.modelDirectory, 'export-manifest.json'));
            return f.options;
        },
        'symlink directory': (f) => {
            const link = `${f.modelDirectory}-link`;
            fs.symlinkSync(f.modelDirectory, link);
            t.after(() => fs.unlinkSync(link));
            return { ...f.options, modelDirectory: link };
        },
    };
    for (const [name, mutate] of Object.entries(scenarios)) {
        await t.test(name, async (child) => {
            const fixture = bundle(child);
            const backend = mockBackend();
            await assert.rejects(backend.OnnxPolicy.create(mutate(fixture)));
            assert.equal(backend.calls.create.length, 0);
        });
    }
});

test('pinned runtime and model interface fail closed', async (t) => {
    const fixture = bundle(t);
    const wrongVersion = mockBackend({ version: '1.31.0' });
    await assert.rejects(wrongVersion.OnnxPolicy.create(fixture.options), errorCode('onnx-runtime-version'));
    assert.equal(wrongVersion.calls.create.length, 0);
    const wrongNames = mockBackend({ names: INPUT_NAMES.slice(1) });
    await assert.rejects(wrongNames.OnnxPolicy.create(fixture.options), errorCode('onnx-model-interface'));
    assert.equal(wrongNames.calls.released, 1);
});

test('malformed, nonfinite, wrong-shaped and out-of-range model outputs are rejected', async (t) => {
    const fixture = bundle(t);
    const changes = [
        (o) => {
            delete o.value;
        },
        (o) => {
            o.extra = {};
        },
        (o) => {
            o.logits.dims = [2];
        },
        (o) => {
            o.logits.data = new Float64Array([1, 2]);
        },
        (o) => {
            o.logits.data[0] = NaN;
        },
        (o) => {
            o.logits.data[1] = Infinity;
        },
        (o) => {
            o.value.type = 'float64';
        },
        (o) => {
            o.value.dims = [1, 1];
        },
        (o) => {
            o.value.data[0] = -0.1;
        },
        (o) => {
            o.value.data[0] = 1.1;
        },
    ];
    for (const change of changes) {
        const backend = mockBackend({
            output(feeds, Tensor) {
                const out = {
                    logits: new Tensor('float32', new Float32Array([1, 2]), [1, 2]),
                    value: new Tensor('float32', new Float32Array([0.5]), [1]),
                };
                change(out);
                return out;
            },
        });
        const policy = await backend.OnnxPolicy.create(fixture.options);
        await assert.rejects(policy.evaluate(observation()), errorCode('onnx-output'));
        await policy.close();
    }
});

test('worker retry cache is 64-entry LRU, exact duplicate idempotent, changed payload fatal', async () => {
    let evaluations = 0;
    const session = new RequestSession({
        replica: 'replica1',
        checkpointSha256: SHAS.replica1,
        async evaluate() {
            evaluations++;
            return { index: 0 };
        },
    });
    const first = request();
    const one = await session.handle(first);
    one.index = 1;
    assert.equal((await session.handle(first)).index, 0);
    assert.equal(evaluations, 1);
    const conflict = request();
    conflict.observation.global[0] = 1;
    await assert.rejects(session.handle(conflict), errorCode('worker-request-conflict'));
    for (let i = 2; i <= 64; i++) await session.handle(request(i));
    await session.handle(first); // Touch id 1, so id 2 is the next LRU eviction.
    await session.handle(request(65));
    assert.equal(evaluations, 65);
    await session.handle(first);
    assert.equal(evaluations, 65);
    await session.handle(request(2));
    assert.equal(evaluations, 66);
});

test('transport binds startup, detaches input, coalesces duplicate requests and returns full response', async (t) => {
    const fixture = workerFixture();
    const transport = new OnnxTransport(options(fixture));
    t.after(() => transport.close());
    const req = request();
    const p = transport.request(req);
    const duplicate = transport.request(req);
    req.observation.global[0] = 8;
    const ready = await transport.ready;
    assert.equal(ready.replica, 'replica1');
    assert.equal(ready.checkpointSha256, SHAS.replica1);
    const res = await p;
    assert.deepEqual(await duplicate, res);
    assert.deepEqual(res, response(request()));
    assert.equal(fixture.instances[0].sent.length, 1);
    assert.equal(fixture.instances[0].sent[0].observation.global[0], 0);
    assert.equal(fixture.instances[0].options.workerData.exportManifestSha256, 'a'.repeat(64));
    assert.ok(fixture.instances[0].filename.endsWith('onnx_worker.cjs'));
    assert.deepEqual(await transport.request(request()), res);
    assert.equal(fixture.instances[0].sent.length, 1);
    assert.equal(Object.isFrozen(res), true);
    assert.equal(transport.replica, 'replica1');
    transport.close();
    transport.close();
    assert.equal(fixture.instances[0].terminated, 1);
    assert.equal(transport.closed, true);
    await assert.rejects(transport.request(request(2)), errorCode('worker-closed'));
});

test('transport conflicts poison all pending requests, including conflicting completed ids', async (t) => {
    const fixture = workerFixture({ onRequest() {} });
    const transport = new OnnxTransport(options(fixture));
    t.after(() => transport.close());
    await transport.ready;
    const pending = transport.request(request());
    const pendingCheck = assert.rejects(pending, errorCode('worker-request-conflict'));
    const changed = request();
    changed.observation.global[0] = 1;
    await assert.rejects(transport.request(changed), errorCode('worker-request-conflict'));
    await pendingCheck;
    assert.equal(transport.closed, true);
    const completedFixture = workerFixture();
    const completed = new OnnxTransport(options(completedFixture));
    t.after(() => completed.close());
    await completed.request(request());
    await assert.rejects(completed.request(changed), errorCode('worker-request-conflict'));
    assert.equal(completed.closed, true);
});

test('transport counts all pending callers against eight-request bound', async (t) => {
    const fixture = workerFixture({ onRequest() {} });
    const transport = new OnnxTransport(options(fixture));
    t.after(() => transport.close());
    await transport.ready;
    const pending = Array.from({ length: 8 }, (_, i) => transport.request(request(i + 1)));
    const results = Promise.allSettled(pending);
    await assert.rejects(transport.request(request(9)), errorCode('worker-queue-full'));
    assert.equal(transport.closed, false);
    transport.close();
    assert.ok((await results).every((r) => r.status === 'rejected' && r.reason.code === 'worker-closed'));
});

test('transport request deadline includes startup/queue time, poisons once, and ignores late output', async (t) => {
    const fixture = workerFixture({ ready: false });
    const transport = new OnnxTransport(options({ ...fixture, startupMs: 500 }));
    t.after(() => transport.close());
    await assert.rejects(transport.request(request(), { timeoutMs: 20 }), errorCode('worker-timeout'));
    await assert.rejects(transport.ready, errorCode('worker-timeout'));
    assert.equal(transport.closed, true);
    assert.equal(fixture.instances[0].sent.length, 0);
    fixture.instances[0].emit('message', response(request()));
    assert.equal(fixture.instances[0].terminated, 1);
    await assert.rejects(transport.request(request()), errorCode('worker-closed'));
});

test('inference timeout and shortest duplicate deadline poison the worker', async (t) => {
    const fixture = workerFixture({ onRequest() {} });
    const transport = new OnnxTransport(options(fixture));
    t.after(() => transport.close());
    await transport.ready;
    const first = transport.request(request(), { timeoutMs: 500 });
    const firstCheck = assert.rejects(first, errorCode('worker-timeout'));
    await assert.rejects(transport.request(request(), { timeoutMs: 15 }), errorCode('worker-timeout'));
    await firstCheck;
    assert.equal(fixture.instances[0].sent.length, 1);
    assert.equal(transport.closed, true);
});

test('startup timeout, construction failure, wrong ready identity and explicit early close settle ready', async (t) => {
    for (const [fixture, expected] of [
        [workerFixture({ ready: false }), 'worker-startup-timeout'],
        [workerFixture({ failConstructor: true }), 'worker-thread'],
        [workerFixture({ readyPatch: { manifestSha256: '0'.repeat(64) } }), 'worker-protocol'],
        [workerFixture({ readyPatch: { checkpointSha256: SHAS.replica2 } }), 'worker-protocol'],
        [workerFixture({ readyPatch: { replica: 'replica2' } }), 'worker-protocol'],
        [workerFixture({ readyPatch: { extra: 1 } }), 'worker-protocol'],
    ]) {
        const transport = new OnnxTransport(options({ ...fixture, startupMs: 15 }));
        t.after(() => transport.close());
        await assert.rejects(transport.ready, errorCode(expected));
        assert.equal(transport.closed, true);
    }
    const fixture = workerFixture({ ready: false });
    const transport = new OnnxTransport(options(fixture));
    transport.close();
    await assert.rejects(transport.ready, errorCode('worker-closed'));
});

test('malformed/mismatched/unknown/duplicate output and thread failures poison pending work', async (t) => {
    const faults = [
        (worker, req) => worker.emit('message', { ...response(req), index: 9 }),
        (worker, req) => worker.emit('message', { ...response(req), requestId: 'f'.repeat(64) }),
        (worker, req) => worker.emit('message', { ...response(req), checkpointSha256: SHAS.replica2 }),
        (worker, req) => worker.emit('message', { ...response(req), actionCount: 3 }),
        (worker, req) => worker.emit('message', { ...response(req), extra: true }),
        (worker) => worker.emit('message', null),
        (worker) => worker.emit('message', 'not an object'),
        (worker) => worker.emit('error', new Error('private details')),
        (worker) => worker.emit('exit', 1),
        (worker) => worker.emit('messageerror', new Error('bad clone')),
        (worker) => worker.stdout.emit('data', Buffer.from('do not forward')),
        (worker) => worker.stderr.emit('data', Buffer.from('do not forward')),
    ];
    for (const fault of faults) {
        const fixture = workerFixture({ onRequest: fault });
        const transport = new OnnxTransport(options(fixture));
        t.after(() => transport.close());
        await assert.rejects(transport.request(request()));
        assert.equal(transport.closed, true);
        assert.equal(fixture.instances[0].terminated, 1);
    }
    const fixture = workerFixture();
    const transport = new OnnxTransport(options(fixture));
    t.after(() => transport.close());
    await transport.request(request());
    fixture.instances[0].emit('message', response(request()));
    assert.equal(transport.closed, true, 'unsolicited second output is not a retry');
});

test('late response cannot beat a deadline just because the parent timer has not run yet', async (t) => {
    const fixture = workerFixture({
        onRequest(worker, req) {
            const until = performance.now() + 20;
            while (performance.now() < until) {
                /* deliberately block fake worker */
            }
            worker.emit('message', response(req));
        },
    });
    const transport = new OnnxTransport(options(fixture));
    t.after(() => transport.close());
    await transport.ready;
    await assert.rejects(transport.request(request(), { timeoutMs: 10 }), errorCode('worker-timeout'));
});

test('startup deadline is checked even before its timer callback; write failures poison', async (t) => {
    const fixture = workerFixture({ ready: false });
    const transport = new OnnxTransport(options({ ...fixture, startupMs: 10 }));
    t.after(() => transport.close());
    const until = performance.now() + 15;
    while (performance.now() < until) {
        /* defer timer */
    }
    const worker = fixture.instances[0];
    worker.emit('message', {
        schema: 'pg-replica-serving-ready-v1',
        replica: 'replica1',
        checkpointSha256: SHAS.replica1,
        manifestSha256: worker.options.workerData.sourceManifestSha256,
    });
    await assert.rejects(transport.ready, errorCode('worker-startup-timeout'));
    const broken = workerFixture({
        onRequest() {
            throw new Error('private write failure');
        },
    });
    const brokenTransport = new OnnxTransport(options(broken));
    t.after(() => brokenTransport.close());
    await assert.rejects(brokenTransport.request(request()), errorCode('worker-write'));
    assert.equal(brokenTransport.closed, true);
});

test('actual Node worker startup failure needs no export or Python and has no unhandled rejection', async (t) => {
    const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'pg-onnx-missing-'));
    t.after(() => fs.rmSync(directory, { recursive: true, force: true }));
    const transport = new OnnxTransport(options({ modelDirectory: directory }));
    t.after(() => transport.close());
    // Deliberately leave ready unobserved until startup has already failed.
    await new Promise((resolve) => setTimeout(resolve, 100));
    await assert.rejects(transport.ready, errorCode('worker-protocol'));
    assert.equal(transport.closed, true);
});

test('invalid and oversized requests never reach worker; limits are explicit', async (t) => {
    const fixture = workerFixture();
    const transport = new OnnxTransport(options(fixture));
    t.after(() => transport.close());
    await transport.ready;
    await assert.rejects(transport.request({ ...request(), G: {} }), errorCode('worker-request'));
    await assert.rejects(transport.request(request(1, observation(), 'replica2')), errorCode('worker-request'));
    await assert.rejects(transport.request({ ...request(), requestId: '1' }), errorCode('worker-request'));
    await assert.rejects(transport.request(request(), { timeoutMs: 0 }), errorCode('worker-deadline'));
    const huge = observation(6, 64, 4096);
    // Valid dimensions and finite float32-representable inputs, but a >4MiB JSON envelope.
    const largeNumber = -0.0000012345678901234567;
    huge.global.fill(largeNumber);
    huge.prior.fill(largeNumber);
    huge.prior[0] = 0;
    for (const field of ['players', 'nodes', 'actions']) for (const row of huge[field]) row.fill(largeNumber);
    for (const relation of huge.relations) for (const row of relation) row.fill(largeNumber);
    assert.ok(Buffer.byteLength(canonical(request(1, huge))) > 4 * 1024 * 1024);
    await assert.rejects(transport.request(request(1, huge)), errorCode('worker-request-limit'));
    assert.equal(fixture.instances[0].sent.length, 0);
    assert.equal(transport.closed, false);
    for (const limits of [
        { timeoutMs: 0 },
        { timeoutMs: 5001 },
        { startupMs: 30001 },
        { maxPending: 9 },
        { maxPending: 0 },
    ]) {
        assert.throws(() => new OnnxTransport(options({ ...fixture, ...limits })), errorCode('worker-limits'));
    }
});

const exportDirectory = process.env.PG_ONNX_TEST_MODELS || path.join(ROOT, 'ai/runs/serving-prototype-v1/onnx-final');
const exportManifestPath = path.join(exportDirectory, 'export-manifest.json');
const hasRealModels =
    fs.existsSync(exportManifestPath) &&
    ['replica1.onnx', 'replica2.onnx'].every((name) => fs.existsSync(path.join(exportDirectory, name)));
test(
    'real exported models: both replicas, variable tensor shapes, worker binding, idempotence',
    { skip: !hasRealModels && 'offline export artifacts are not installed', timeout: 60000 },
    async (t) => {
        // Test fixture convenience only. A deployed host MUST obtain this digest
        // from trusted configuration, never self-authenticate a downloaded bundle.
        const exportManifestSha256 = hash(fs.readFileSync(exportManifestPath));
        for (const replica of Object.keys(SHAS)) {
            await t.test(replica, async (child) => {
                const opts = { replica, modelDirectory: exportDirectory, exportManifestSha256 };
                const policy = await OnnxPolicy.create(opts);
                child.after(() => policy.close());
                const transport = new OnnxTransport({ ...opts, timeoutMs: 5000 });
                child.after(() => transport.close());
                const ready = await transport.ready;
                assert.equal(ready.manifestSha256, loadIdentity().manifestSha256);
                assert.equal(ready.checkpointSha256, SHAS[replica]);
                let id = 1;
                for (const [P, N, A] of [
                    [2, 1, 2],
                    [3, 4, 9],
                    [6, 64, 128],
                    [2, 1, 4096],
                ]) {
                    const obs = observation(P, N, A);
                    const result = await policy.evaluate(obs);
                    assert.equal(result.logits.length, A);
                    assert.ok(result.logits.every(Number.isFinite));
                    assert.ok(result.value >= 0 && result.value <= 1);
                    let first = 0;
                    for (let i = 1; i < A; i++) if (result.logits[i] > result.logits[first]) first = i;
                    assert.equal(result.index, first);
                    const req = request(id++, obs, replica);
                    const res = await transport.request(req);
                    assert.equal(validateResponse(res, req), result.index);
                    assert.deepEqual(await transport.request(req), res);
                    assert.deepEqual(await policy.evaluate(obs), result);
                }
            });
        }
    }
);
