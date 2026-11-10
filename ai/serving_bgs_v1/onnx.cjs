'use strict';
// Node-only serving. The offline exporter/reference is deliberately not imported.
const fs = require('node:fs');
const path = require('node:path');
const { performance } = require('node:perf_hooks');
const { Worker } = require('node:worker_threads');
const { scheduleDeadline } = require('./deadline.cjs');
const { SHAS, loadIdentity, exactKeys, canonical, hash, requireThat } = require('./identity.cjs');

const ORT_VERSION = '1.31.1';
const MAX_MODEL = 4 * 1024 * 1024;
const MAX_REQUEST = 4 * 1024 * 1024;
const CACHE_SIZE = 64;
const HEX64 = /^[0-9a-f]{64}$/;
const FLOAT32_MAX = 3.4028234663852886e38;
const OBS_KEYS = Object.freeze(['schema', 'global', 'players', 'nodes', 'relations', 'actions', 'actionCity', 'prior']);
const INPUT_NAMES = Object.freeze([
    'global',
    'players',
    'nodes',
    'relations',
    'actions',
    'actionCity',
    'prior',
    'nodeMask',
    'playerMask',
    'actionMask',
]);
const RESPONSE_KEYS = ['schema', 'requestId', 'replica', 'checkpointSha256', 'index', 'actionCount'];
const INTERNAL = Symbol('verified ONNX session');

function validateObservation(observation) {
    requireThat(exactKeys(observation, OBS_KEYS) && observation.schema === 'multimap-graph-v1', 'observation-schema');
    function vector(values, length) {
        requireThat(Array.isArray(values) && values.length === length, 'observation-shape');
        for (const value of values) {
            requireThat(
                typeof value === 'number' && Number.isFinite(value) && Math.abs(value) <= FLOAT32_MAX,
                'observation-number'
            );
        }
    }
    function matrix(rows, low, high, width) {
        requireThat(Array.isArray(rows) && rows.length >= low && rows.length <= high, 'observation-shape');
        for (const row of rows) vector(row, width);
        return rows.length;
    }
    // Complete validation precedes every tensor allocation, including masks.
    vector(observation.global, 273);
    const players = matrix(observation.players, 2, 6, 80);
    const nodes = matrix(observation.nodes, 1, 64, 36);
    const actions = matrix(observation.actions, 2, 4096, 34);
    requireThat(Array.isArray(observation.relations) && observation.relations.length === 4, 'observation-shape');
    for (const relation of observation.relations) matrix(relation, nodes, nodes, nodes);
    requireThat(
        Array.isArray(observation.actionCity) && observation.actionCity.length === actions,
        'observation-shape'
    );
    for (const city of observation.actionCity) {
        requireThat(Number.isSafeInteger(city) && city >= -1 && city < nodes, 'observation-city');
    }
    vector(observation.prior, actions);
    let maximum = -Infinity;
    for (const value of observation.prior) {
        requireThat(value >= -20 && value <= 0, 'observation-prior');
        maximum = Math.max(maximum, value);
    }
    requireThat(maximum === 0, 'observation-prior');
    return { players, nodes, actions };
}

function validateRequest(request, replica) {
    requireThat(
        Object.hasOwn(SHAS, replica) &&
            exactKeys(request, ['schema', 'requestId', 'replica', 'observation']) &&
            request.schema === 'pg-replica-serving-request-v1' &&
            request.replica === replica &&
            typeof request.requestId === 'string' &&
            HEX64.test(request.requestId),
        'worker-request'
    );
    return validateObservation(request.observation);
}

// Shared with the host adapter; never imports the retired process transport.
function validateResponse(response, request) {
    requireThat(
        exactKeys(request, ['schema', 'requestId', 'replica', 'observation']) &&
            request.schema === 'pg-replica-serving-request-v1' &&
            Object.hasOwn(SHAS, request.replica) &&
            typeof request.requestId === 'string' &&
            HEX64.test(request.requestId) &&
            exactKeys(response, RESPONSE_KEYS) &&
            response.schema === 'pg-replica-serving-response-v1' &&
            response.requestId === request.requestId &&
            response.replica === request.replica &&
            response.checkpointSha256 === SHAS[request.replica] &&
            Number.isSafeInteger(response.actionCount) &&
            response.actionCount === request.observation?.actions?.length &&
            response.actionCount >= 2 &&
            response.actionCount <= 4096 &&
            Number.isSafeInteger(response.index) &&
            response.index >= 0 &&
            response.index < response.actionCount,
        'worker-response'
    );
    return response.index;
}

function config(options) {
    requireThat(
        options &&
            Object.hasOwn(SHAS, options.replica) &&
            typeof options.modelDirectory === 'string' &&
            options.modelDirectory.length > 0 &&
            !options.modelDirectory.includes('\0') &&
            !options.modelDirectory.split(/[\\/]/).includes('..') &&
            typeof options.exportManifestSha256 === 'string' &&
            HEX64.test(options.exportManifestSha256),
        'onnx-config'
    );
    return {
        replica: options.replica,
        modelDirectory: path.resolve(options.modelDirectory),
        exportManifestSha256: options.exportManifestSha256,
    };
}

function safeRead(file, limit, expectedBytes) {
    // No links in any component; on Linux, walk pinned directory descriptors so
    // a concurrent directory rename/link swap cannot redirect a later open.
    // Other platforms still require a host-controlled model directory. Digest
    // verification always authenticates the same privately held bytes loaded by ORT.
    const absolute = path.resolve(file);
    const parts = absolute.slice(path.parse(absolute).root.length).split(path.sep);
    const descriptors = [];
    let parent = path.parse(absolute).root;
    try {
        for (const part of parts.slice(0, -1)) {
            const next = path.join(parent, part);
            requireThat(!fs.lstatSync(next).isSymbolicLink(), 'onnx-file-link');
            const fd = fs.openSync(
                next,
                fs.constants.O_RDONLY |
                    (fs.constants.O_DIRECTORY || 0) |
                    (fs.constants.O_NOFOLLOW || 0) |
                    (fs.constants.O_NONBLOCK || 0)
            );
            descriptors.push(fd);
            requireThat(fs.fstatSync(fd).isDirectory(), 'onnx-file-directory');
            parent = process.platform === 'linux' ? `/proc/self/fd/${fd}` : next;
        }
        const target = path.join(parent, parts.at(-1));
        requireThat(!fs.lstatSync(target).isSymbolicLink(), 'onnx-file-link');
        const fd = fs.openSync(
            target,
            fs.constants.O_RDONLY | (fs.constants.O_NOFOLLOW || 0) | (fs.constants.O_NONBLOCK || 0)
        );
        descriptors.push(fd);
        const before = fs.fstatSync(fd);
        requireThat(
            before.isFile() &&
                before.nlink === 1 &&
                before.size > 0 &&
                before.size <= limit &&
                (expectedBytes === undefined || before.size === expectedBytes),
            'onnx-file-size'
        );
        const raw = Buffer.alloc(before.size + 1);
        let size = 0;
        while (size < raw.length) {
            const count = fs.readSync(fd, raw, size, raw.length - size, null);
            if (!count) break;
            size += count;
        }
        const after = fs.fstatSync(fd);
        requireThat(
            size === before.size &&
                after.size === before.size &&
                after.nlink === 1 &&
                after.mtimeMs === before.mtimeMs &&
                after.ctimeMs === before.ctimeMs,
            'onnx-file-changed'
        );
        return raw.subarray(0, size);
    } finally {
        for (const fd of descriptors.reverse()) fs.closeSync(fd);
    }
}

function loadBundle(options, identity) {
    const rawManifest = safeRead(path.join(options.modelDirectory, 'export-manifest.json'), 128 * 1024);
    requireThat(hash(rawManifest) === options.exportManifestSha256, 'onnx-manifest-checksum');
    const manifest = JSON.parse(rawManifest);
    requireThat(
        manifest &&
            manifest.schema === 'pg-replica-onnx-export-v1' &&
            // The unchanged export authenticates its research inputs, not this separately versioned Node port.
            manifest.sourceManifestSha256 === identity.exportSourceManifestSha256 &&
            exactKeys(manifest.replicas, ['replica1', 'replica2']),
        'onnx-manifest-identity'
    );
    for (const [replica, checkpointSha256] of Object.entries(SHAS)) {
        const entry = manifest.replicas[replica];
        requireThat(
            entry &&
                entry.file === `${replica}.onnx` &&
                entry.checkpointSha256 === checkpointSha256 &&
                typeof entry.sha256 === 'string' &&
                HEX64.test(entry.sha256) &&
                Number.isSafeInteger(entry.bytes) &&
                entry.bytes > 0 &&
                entry.bytes <= MAX_MODEL,
            'onnx-model-identity'
        );
    }
    const entry = manifest.replicas[options.replica];
    const bytes = safeRead(path.join(options.modelDirectory, entry.file), MAX_MODEL, entry.bytes);
    requireThat(hash(bytes) === entry.sha256, 'onnx-model-checksum');
    return bytes; // Never expose this buffer or reopen its pathname for inference.
}

function makeFeeds(ort, observation, dimensions) {
    const { players: P, nodes: N, actions: A } = dimensions;
    function tensor(name, dims, depth) {
        const data = new Float32Array(dims.reduce((a, b) => a * b, 1));
        let offset = 0;
        function copy(values, remaining) {
            if (remaining === 1) {
                data.set(values, offset);
                offset += values.length;
            } else for (const row of values) copy(row, remaining - 1);
        }
        copy(observation[name], depth);
        return new ort.Tensor('float32', data, dims);
    }
    return {
        global: tensor('global', [1, 273], 1),
        players: tensor('players', [1, P, 80], 2),
        nodes: tensor('nodes', [1, N, 36], 2),
        relations: tensor('relations', [1, 4, N, N], 3),
        actions: tensor('actions', [1, A, 34], 2),
        prior: tensor('prior', [1, A], 1),
        actionCity: new ort.Tensor('int64', BigInt64Array.from(observation.actionCity, BigInt), [1, A]),
        nodeMask: new ort.Tensor('bool', new Uint8Array(N).fill(1), [1, N]),
        playerMask: new ort.Tensor('bool', new Uint8Array(P).fill(1), [1, P]),
        actionMask: new ort.Tensor('bool', new Uint8Array(A).fill(1), [1, A]),
    };
}

function decodeOutputs(outputs, actionCount) {
    requireThat(exactKeys(outputs, ['logits', 'value']), 'onnx-output');
    for (const [name, dims] of [
        ['logits', [1, actionCount]],
        ['value', [1]],
    ]) {
        const tensor = outputs[name];
        requireThat(
            tensor &&
                tensor.type === 'float32' &&
                Array.isArray(tensor.dims) &&
                tensor.dims.length === dims.length &&
                dims.every((n, i) => tensor.dims[i] === n) &&
                tensor.data instanceof Float32Array &&
                tensor.data.length === dims.at(-1),
            'onnx-output'
        );
        for (const value of tensor.data) requireThat(Number.isFinite(value), 'onnx-output');
    }
    const logits = Array.from(outputs.logits.data);
    const value = outputs.value.data[0];
    requireThat(value >= 0 && value <= 1, 'onnx-output');
    let index = 0;
    for (let i = 1; i < actionCount; i++) if (logits[i] > logits[index]) index = i;
    return { index, logits, value }; // First maximum, no sampling, calibration or reranking.
}

class OnnxPolicy {
    #session;
    #ort;
    #options;
    #identity;
    #closed = false;
    #tail = Promise.resolve();
    #closing;
    constructor(token, session, ort, options, identity) {
        requireThat(token === INTERNAL, 'onnx-create-required');
        this.#session = session;
        this.#ort = ort;
        this.#options = options;
        this.#identity = identity;
    }
    static async create(options) {
        const checked = config(options);
        const identity = loadIdentity(); // Source guard and pinned Node/engine runtime.
        const bytes = loadBundle(checked, identity); // Authenticated BEFORE any native model parsing.
        requireThat(require('onnxruntime-node/package.json').version === ORT_VERSION, 'onnx-runtime-version');
        const ort = require('onnxruntime-node');
        requireThat(
            ort.env.versions.node === ORT_VERSION && ort.env.versions.common === ORT_VERSION,
            'onnx-runtime-version'
        );
        const session = await ort.InferenceSession.create(bytes, {
            executionProviders: ['cpu'],
            intraOpNumThreads: 1,
            interOpNumThreads: 1,
            executionMode: 'sequential',
            enableProfiling: false,
            logSeverityLevel: 3,
        });
        try {
            requireThat(
                Array.isArray(session.inputNames) &&
                    session.inputNames.length === INPUT_NAMES.length &&
                    [...session.inputNames].sort().join('|') === [...INPUT_NAMES].sort().join('|') &&
                    Array.isArray(session.outputNames) &&
                    [...session.outputNames].sort().join('|') === 'logits|value',
                'onnx-model-interface'
            );
            return new OnnxPolicy(INTERNAL, session, ort, checked, identity);
        } catch (error) {
            await session.release();
            throw error;
        }
    }
    get replica() {
        return this.#options.replica;
    }
    get checkpointSha256() {
        return SHAS[this.replica];
    }
    get manifestSha256() {
        return this.#identity.manifestSha256;
    }
    get exportManifestSha256() {
        return this.#options.exportManifestSha256;
    }
    get closed() {
        return this.#closed;
    }
    evaluate(observation) {
        try {
            requireThat(!this.#closed, 'onnx-closed');
            const dimensions = validateObservation(observation);
            const feeds = makeFeeds(this.#ort, observation, dimensions); // Detach synchronously from caller mutation.
            const result = this.#tail.then(async () => {
                let outputs;
                try {
                    requireThat(!this.#closed, 'onnx-closed');
                    outputs = await this.#session.run(feeds);
                    return decodeOutputs(outputs, dimensions.actions);
                } finally {
                    for (const tensor of Object.values(feeds)) tensor.dispose();
                    if (outputs) for (const tensor of Object.values(outputs)) tensor?.dispose?.();
                }
            });
            this.#tail = result.catch(() => {});
            return result;
        } catch (error) {
            return Promise.reject(error);
        }
    }
    close() {
        if (!this.#closing) {
            this.#closed = true;
            this.#closing = this.#tail.then(() => this.#session.release());
        }
        return this.#closing;
    }
    release() {
        return this.close();
    }
}

function remember(cache, id, value) {
    cache.delete(id);
    cache.set(id, value);
    if (cache.size > CACHE_SIZE) cache.delete(cache.keys().next().value);
}

class OnnxTransport {
    #worker;
    #role;
    #identity;
    #timeoutMs;
    #maxPending;
    #closed = false;
    #readySeen = false;
    #pending = new Map();
    #cache = new Map();
    #pendingCount = 0;
    #startupTimer;
    #startupDeadline;
    #resolveReady;
    #rejectReady;
    constructor(options = {}) {
        const checked = config(options);
        const { timeoutMs = 1000, startupMs = 10000, maxPending = 8, WorkerConstructor = Worker } = options;
        requireThat(
            Number.isSafeInteger(timeoutMs) &&
                timeoutMs >= 10 &&
                timeoutMs <= 5000 &&
                Number.isSafeInteger(startupMs) &&
                startupMs >= 10 &&
                startupMs <= 30000 &&
                Number.isSafeInteger(maxPending) &&
                maxPending >= 1 &&
                maxPending <= 8 &&
                typeof WorkerConstructor === 'function',
            'worker-limits'
        );
        this.#identity = loadIdentity();
        this.#role = checked.replica;
        this.#timeoutMs = timeoutMs;
        this.#maxPending = maxPending;
        this.ready = new Promise((resolve, reject) => {
            this.#resolveReady = resolve;
            this.#rejectReady = reject;
        });
        this.ready.catch(() => {}); // Idle startup failures are observed even if the host never awaits ready.
        this.#startupDeadline = performance.now() + startupMs;
        this.#startupTimer = scheduleDeadline(this.#startupDeadline, () => this.#fail('worker-startup-timeout'));
        try {
            // WorkerConstructor is a test seam, NOT an untrusted per-request option.
            this.#worker = new WorkerConstructor(path.join(__dirname, 'onnx_worker.cjs'), {
                workerData: { ...checked, sourceManifestSha256: this.#identity.manifestSha256 },
                stdout: true,
                stderr: true,
            });
            this.#worker.on('message', (message) => this.#receive(message));
            this.#worker.on('messageerror', () => this.#fail('worker-protocol'));
            this.#worker.on('error', () => this.#fail('worker-thread'));
            this.#worker.on('exit', () => this.#fail('worker-eof'));
            // Discard JS worker stream output. Native writes to fd 1/2 bypass these
            // listeners; this is not native-output isolation (see test_native_boundary.cjs).
            this.#worker.stdout?.on('data', () => this.#fail('worker-output'));
            this.#worker.stderr?.on('data', () => this.#fail('worker-output'));
        } catch (_) {
            this.#fail('worker-thread');
        }
    }
    get replica() {
        return this.#role;
    }
    get closed() {
        return this.#closed;
    }
    #fail(code) {
        if (this.#closed) return;
        this.#closed = true;
        this.#startupTimer?.cancel();
        const error = Object.assign(new Error(code), { code });
        this.#rejectReady(error);
        for (const pending of this.#pending.values()) {
            for (const caller of pending.callers) {
                caller.timer.cancel();
                caller.reject(error);
            }
        }
        this.#pending.clear();
        this.#cache.clear();
        this.#pendingCount = 0;
        // This is lifecycle isolation, NOT a hostile-code sandbox or a guarantee
        // of immediate native-call preemption. No process restart or late reuse.
        try {
            Promise.resolve(this.#worker?.terminate()).catch(() => {});
        } catch (_) {
            /* already terminated */
        }
    }
    #receive(message) {
        if (this.#closed) return; // Late output from a poisoned worker can never be consumed.
        try {
            if (!this.#readySeen) {
                if (performance.now() >= this.#startupDeadline) {
                    this.#fail('worker-startup-timeout');
                    return;
                }
                requireThat(
                    exactKeys(message, ['schema', 'replica', 'checkpointSha256', 'manifestSha256']) &&
                        message.schema === 'pg-replica-serving-ready-v1' &&
                        message.replica === this.#role &&
                        message.checkpointSha256 === SHAS[this.#role] &&
                        message.manifestSha256 === this.#identity.manifestSha256,
                    'worker-ready'
                );
                this.#readySeen = true;
                this.#startupTimer?.cancel();
                this.#resolveReady(Object.freeze(message));
                return;
            }
            const pending = this.#pending.get(message?.requestId);
            requireThat(pending, 'worker-unexpected-response');
            validateResponse(message, pending.request);
            if (pending.callers.some((caller) => performance.now() >= caller.deadline)) {
                this.#fail('worker-timeout');
                return;
            }
            const response = Object.freeze(message);
            this.#pending.delete(message.requestId);
            remember(this.#cache, message.requestId, { payload: pending.payload, response });
            for (const caller of pending.callers) {
                caller.timer.cancel();
                this.#pendingCount--;
                caller.resolve(response);
            }
        } catch (_) {
            this.#fail('worker-protocol');
        }
    }
    request(input, { timeoutMs = this.#timeoutMs } = {}) {
        const started = performance.now();
        try {
            requireThat(!this.#closed, 'worker-closed');
            requireThat(Number.isFinite(timeoutMs) && timeoutMs > 0 && timeoutMs <= 5000, 'worker-deadline');
            validateRequest(input, this.#role);
            const raw = canonical(input); // Also rejects non-JSON numbers; deterministic payload digest.
            requireThat(Buffer.byteLength(raw) <= MAX_REQUEST, 'worker-request-limit');
            const request = JSON.parse(raw);
            const payload = hash(raw);
            const previous = this.#pending.get(request.requestId) || this.#cache.get(request.requestId);
            if (previous && previous.payload !== payload) {
                this.#fail('worker-request-conflict');
                throw Object.assign(new Error('worker-request-conflict'), { code: 'worker-request-conflict' });
            }
            const deadline = started + timeoutMs;
            if (performance.now() >= deadline) {
                this.#fail('worker-timeout');
                throw Object.assign(new Error('worker-timeout'), { code: 'worker-timeout' });
            }
            if (previous?.response) {
                remember(this.#cache, request.requestId, previous);
                return Promise.resolve(previous.response);
            }
            requireThat(this.#pendingCount < this.#maxPending, 'worker-queue-full');
            return new Promise((resolve, reject) => {
                const timer = scheduleDeadline(deadline, () => this.#fail('worker-timeout'));
                const caller = { resolve, reject, timer, deadline };
                this.#pendingCount++;
                if (previous) {
                    previous.callers.push(caller);
                    return;
                }
                this.#pending.set(request.requestId, { request, payload, callers: [caller] });
                this.ready.then(
                    () => {
                        if (this.#closed || !this.#pending.has(request.requestId)) return;
                        if (performance.now() >= deadline) {
                            this.#fail('worker-timeout');
                            return;
                        }
                        try {
                            this.#worker.postMessage(raw);
                        } catch (_) {
                            this.#fail('worker-write');
                        }
                    },
                    () => {}
                );
            });
        } catch (error) {
            return Promise.reject(error);
        }
    }
    close() {
        this.#fail('worker-closed');
    }
}

module.exports = {
    OnnxPolicy,
    OnnxTransport,
    validateObservation,
    validateRequest,
    validateResponse,
    OBS_KEYS,
    INPUT_NAMES,
    MAX_REQUEST,
    CACHE_SIZE,
    remember,
};
