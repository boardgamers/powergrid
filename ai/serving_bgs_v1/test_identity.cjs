'use strict';
// Source/port boundary tests only: no games, research replays, Python or checkpoint loading.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const Module = require('node:module');
const { EventEmitter } = require('node:events');
const { ROOT, SHAS, hash, canonical, cloneState, loadIdentity, validateManifest } = require('./identity.cjs');
const { OnnxTransport, INPUT_NAMES } = require('./onnx.cjs');
const RESEARCH_SHA = '8197fb7e35ed25a924d75e99eafcc140827b46ab441341bb14cd398c832b9f93';
const EXPORT_SHA = '8dac4ba18002a38868920875f0201f54200ac1ae062c51da3d615b189ffad543';
const manifestFile = path.join(__dirname, 'manifest.json');
const readManifest = () => JSON.parse(fs.readFileSync(manifestFile));
const errorCode = (code) => (error) => error.code === code;

function temporary(t) {
    const root = fs.mkdtempSync(path.join(fs.realpathSync(os.tmpdir()), 'pg-bgs-identity-'));
    t.after(() => fs.rmSync(root, { recursive: true, force: true }));
    return root;
}
function sourceTree(t) {
    const root = temporary(t);
    const files = [
        'ai/serving_bgs_v1/identity.cjs',
        'ai/serving_bgs_v1/manifest.json',
        ...Object.keys(readManifest().sourceFiles),
    ];
    for (const name of files) {
        const target = path.join(root, name);
        fs.mkdirSync(path.dirname(target), { recursive: true });
        fs.copyFileSync(path.join(ROOT, name), target);
    }
    const identity = require(path.join(root, 'ai/serving_bgs_v1/identity.cjs'));
    return { root, files, identity };
}

test('Node manifest is exactly the original inventory minus four Python files and wrapper.ts', () => {
    const originalRaw = fs.readFileSync(path.join(__dirname, '../serving_v1/manifest.json'));
    assert.equal(hash(originalRaw), RESEARCH_SHA);
    const original = JSON.parse(originalRaw);
    const manifest = readManifest();
    assert.deepEqual(manifest.replicas, original.replicas);
    const removed = Object.keys(original.sourceFiles).filter((name) => !Object.hasOwn(manifest.sourceFiles, name));
    assert.deepEqual(removed, [
        'ai/multimap/data.py',
        'ai/multimap/expert_policy.py',
        'ai/multimap/model.py',
        'ai/multimap/residual.py',
        'engine/wrapper.ts',
    ]);
    const expected = { ...original.sourceFiles };
    removed.forEach((name) => delete expected[name]);
    assert.deepEqual(manifest.sourceFiles, expected);
    const files = Object.keys(manifest.sourceFiles);
    assert.equal(files.length, 56);
    assert.equal(files.filter((name) => name.startsWith('engine/dist/') && name.endsWith('.js')).length, 42);
    assert.ok(files.every((name) => /\.(?:cjs|js|json)$/.test(name)));
    assert.ok(files.every((name) => !name.includes('/serving_')));
    assert.equal(manifest.originalResearchManifestSha256, RESEARCH_SHA);
    assert.equal(manifest.exportManifestSha256, EXPORT_SHA);
    assert.deepEqual(manifest.runtimes, {
        node: 'v24.22.1',
        developmentNode: 'v24.20.0',
        engine: '2.0.22',
        ort: '1.31.1',
    });
});

test('loaded identity exposes actual Node manifest digest, distinct frozen export provenance, and frozen data', () => {
    const identity = loadIdentity();
    assert.deepEqual(Object.keys(identity).sort(), ['exportSourceManifestSha256', 'manifest', 'manifestSha256']);
    assert.equal(identity.manifestSha256, hash(fs.readFileSync(manifestFile)));
    assert.equal(identity.exportSourceManifestSha256, RESEARCH_SHA);
    assert.notEqual(identity.manifestSha256, RESEARCH_SHA);
    assert.notEqual(identity.manifestSha256, EXPORT_SHA);
    assert.ok(Object.isFrozen(identity));
    assert.ok(Object.isFrozen(identity.manifest.sourceFiles));
    assert.ok(Object.isFrozen(identity.manifest.replicas.replica1));
    assert.throws(() => {
        identity.manifest.runtimes.node = 'v0.0.0';
    }, TypeError);
});

test('development loader accepts only explicitly pinned production/development versions and runtime metadata', () => {
    const manifest = readManifest();
    for (const version of ['v24.22.1', 'v24.20.0']) assert.doesNotThrow(() => validateManifest(manifest, version));
    for (const version of ['v24.22.0', 'v24.22.2', 'v24.20.1', 'v22.22.1', '24.22.1', null]) {
        assert.throws(() => validateManifest(manifest, version), errorCode('runtime-version'));
    }
    for (const field of ['node', 'developmentNode', 'engine', 'ort']) {
        const changed = readManifest();
        changed.runtimes[field] = 'untrusted';
        assert.throws(() => validateManifest(changed, 'untrusted'), errorCode('runtime-version'));
    }
    for (const runtimes of [null, [], { ...manifest.runtimes, python: '3.12.8' }]) {
        assert.throws(() => validateManifest({ ...manifest, runtimes }), errorCode('runtime-version'));
    }
});

test('manifest schema, checkpoint metadata and original export provenance are pinned', () => {
    for (const manifest of [
        null,
        [],
        {},
        { ...readManifest(), extra: true },
        { ...readManifest(), schema: 'pg-replica-serving-manifest-v1' },
    ]) {
        assert.throws(() => validateManifest(manifest), errorCode('manifest-schema'));
    }
    for (const replicas of [null, [], {}, { ...readManifest().replicas, replica3: {} }]) {
        assert.throws(() => validateManifest({ ...readManifest(), replicas }), errorCode('manifest-roles'));
    }
    for (const field of [
        'sha256',
        'bytes',
        'configSha256',
        'update',
        'schema',
        'width',
        'bound',
        'stage',
        'priorAsActionFeature',
    ]) {
        const manifest = readManifest();
        manifest.replicas.replica1[field] = 'changed';
        assert.throws(() => validateManifest(manifest), errorCode('checkpoint-pin'));
    }
    for (const field of ['originalResearchManifestSha256', 'exportManifestSha256']) {
        const manifest = readManifest();
        manifest[field] = '0'.repeat(64);
        assert.throws(() => validateManifest(manifest), errorCode('export-source-pin'));
    }
});

test('source guard rejects missing, extra, substituted and self-rehashed inventory entries', () => {
    const changes = [
        (m) => {
            m.sourceFiles = null;
        },
        (m) => {
            m.sourceFiles = [];
        },
        (m) => {
            delete m.sourceFiles['ai/core.cjs'];
        },
        (m) => {
            m.sourceFiles['extra.js'] = '0'.repeat(64);
        },
        (m) => {
            delete m.sourceFiles['ai/core.cjs'];
            m.sourceFiles['ai/multimap/model.py'] = '0'.repeat(64);
        },
        (m) => {
            m.sourceFiles['ai/core.cjs'] = '0'.repeat(64);
        },
        (m) => {
            m.sourceFiles['engine/dist/src/maps/france.js'] = '0'.repeat(64);
        },
    ];
    for (const change of changes) {
        const manifest = readManifest();
        change(manifest);
        assert.throws(() => validateManifest(manifest), errorCode('source-inventory'));
    }
    for (const checksum of [null, 0, '0'.repeat(63), 'A'.repeat(64)]) {
        const manifest = readManifest();
        manifest.sourceFiles['ai/core.cjs'] = checksum;
        assert.throws(() => validateManifest(manifest), errorCode('source-pin'));
    }
});

test('source guard rejects absolute, traversal, ambiguous and NUL paths before filesystem access', () => {
    for (const name of [
        '/tmp/source.js',
        '../source.js',
        'ai/../source.js',
        'ai/./core.cjs',
        'ai//core.cjs',
        'ai\\core.cjs',
        '',
        'ai/core.cjs\0',
    ]) {
        const manifest = readManifest();
        delete manifest.sourceFiles['ai/core.cjs'];
        manifest.sourceFiles[name] = '0'.repeat(64);
        assert.throws(() => validateManifest(manifest), errorCode('source-path'));
    }
});

test('standalone source tree needs no research directory, Python/TypeScript files or checkpoint bytes', (t) => {
    const tree = sourceTree(t);
    assert.equal(tree.files.length, 58);
    assert.ok(tree.files.every((name) => /\.(?:cjs|js|json)$/.test(name)));
    assert.equal(fs.existsSync(path.join(tree.root, 'ai/serving_v1')), false);
    assert.equal(fs.existsSync(path.join(tree.root, 'ai/multimap/model.py')), false);
    assert.equal(tree.identity.loadIdentity().manifestSha256, loadIdentity().manifestSha256);
    fs.appendFileSync(path.join(tree.root, 'ai/core.cjs'), '\n// tamper\n');
    assert.throws(() => tree.identity.loadIdentity(), errorCode('source-identity'));
});

test('source and manifest symlinks, including linked directory components, are rejected', (t) => {
    const tree = sourceTree(t);
    const file = path.join(tree.root, 'ai/core.cjs');
    fs.renameSync(file, file + '.original');
    fs.symlinkSync(file + '.original', file);
    assert.throws(() => tree.identity.loadIdentity(), errorCode('source-link'));
    fs.unlinkSync(file);
    fs.renameSync(file + '.original', file);
    const directory = path.join(tree.root, 'engine/dist');
    fs.renameSync(directory, directory + '.original');
    fs.symlinkSync(directory + '.original', directory, 'dir');
    assert.throws(() => tree.identity.loadIdentity(), errorCode('source-link'));
    fs.unlinkSync(directory);
    fs.renameSync(directory + '.original', directory);
    const manifest = path.join(tree.root, 'ai/serving_bgs_v1/manifest.json');
    fs.renameSync(manifest, manifest + '.original');
    fs.symlinkSync(manifest + '.original', manifest);
    assert.throws(() => tree.identity.loadIdentity(), errorCode('source-link'));
});

test('non-file/missing sources and oversized manifests fail closed', (t) => {
    const tree = sourceTree(t);
    const file = path.join(tree.root, 'ai/core.cjs');
    fs.unlinkSync(file);
    assert.throws(() => tree.identity.loadIdentity(), errorCode('ENOENT'));
    fs.mkdirSync(file);
    assert.throws(() => tree.identity.loadIdentity(), errorCode('source-identity'));
    fs.writeFileSync(path.join(tree.root, 'ai/serving_bgs_v1/manifest.json'), ' '.repeat(128 * 1024));
    assert.throws(() => tree.identity.loadIdentity(), errorCode('manifest-size'));
});

test('adapter, worker, deadline, canonicalization and state cloning are unchanged ports', () => {
    for (const name of ['adapter.cjs', 'onnx_worker.cjs', 'deadline.cjs']) {
        assert.equal(
            fs.readFileSync(path.join(__dirname, name), 'utf8'),
            fs.readFileSync(path.join(__dirname, '../serving_v1', name), 'utf8')
        );
    }
    const oldIdentity = require('../serving_v1/identity.cjs');
    assert.equal(canonical.toString(), oldIdentity.canonical.toString());
    assert.equal(cloneState.toString(), oldIdentity.cloneState.toString());
    const oldOnnx = fs.readFileSync(path.join(__dirname, '../serving_v1/onnx.cjs'), 'utf8');
    assert.equal(
        fs.readFileSync(path.join(__dirname, 'onnx.cjs'), 'utf8'),
        oldOnnx
            .replace(
                'manifest.sourceManifestSha256 === identity.manifestSha256 &&',
                '// The unchanged export authenticates its research inputs, not this separately versioned Node port.\n            manifest.sourceManifestSha256 === identity.exportSourceManifestSha256 &&'
            )
            .replace(
                '// Never forward library chatter or retain its contents.',
                '// Discard JS worker stream output. Native writes to fd 1/2 bypass these\n            // listeners; this is not native-output isolation (see test_native_boundary.cjs).'
            )
    );
});

// Mock only native parsing, preserving the real source and model-file guards.
function mockedPolicy() {
    const filename = path.join(__dirname, 'onnx.cjs');
    const loaded = new Module(filename, module);
    loaded.filename = filename;
    loaded.paths = Module._nodeModulePaths(__dirname);
    const actualRequire = loaded.require.bind(loaded);
    let parses = 0;
    const ort = {
        env: { versions: { node: '1.31.1', common: '1.31.1' } },
        InferenceSession: {
            async create() {
                parses++;
                return { inputNames: [...INPUT_NAMES], outputNames: ['logits', 'value'], async release() {} };
            },
        },
    };
    loaded.require = (name) =>
        name === 'onnxruntime-node'
            ? ort
            : name === 'onnxruntime-node/package.json'
            ? { version: '1.31.1' }
            : actualRequire(name);
    loaded._compile(fs.readFileSync(filename, 'utf8'), filename);
    return { OnnxPolicy: loaded.exports.OnnxPolicy, parses: () => parses };
}

test('ONNX export authenticates research source identity while policy reports the actual runtime identity', async (t) => {
    const modelDirectory = temporary(t);
    const identity = loadIdentity();
    const manifest = { schema: 'pg-replica-onnx-export-v1', sourceManifestSha256: RESEARCH_SHA, replicas: {} };
    for (const replica of Object.keys(SHAS)) {
        const bytes = Buffer.from(`Synthetic identity fixture for ${replica}, not a model.`);
        fs.writeFileSync(path.join(modelDirectory, `${replica}.onnx`), bytes);
        manifest.replicas[replica] = {
            file: `${replica}.onnx`,
            sha256: hash(bytes),
            bytes: bytes.length,
            checkpointSha256: SHAS[replica],
        };
    }
    function options() {
        const raw = JSON.stringify(manifest);
        fs.writeFileSync(path.join(modelDirectory, 'export-manifest.json'), raw);
        return { replica: 'replica1', modelDirectory, exportManifestSha256: hash(raw) };
    }
    const backend = mockedPolicy();
    const policy = await backend.OnnxPolicy.create(options());
    assert.equal(policy.manifestSha256, identity.manifestSha256);
    assert.equal(policy.checkpointSha256, SHAS.replica1);
    assert.equal(backend.parses(), 1);
    await policy.close();
    manifest.sourceManifestSha256 = identity.manifestSha256;
    await assert.rejects(backend.OnnxPolicy.create(options()), errorCode('onnx-manifest-identity'));
    assert.equal(backend.parses(), 1);
});

test('transport binds worker startup and ready messages to the new source digest, not research provenance', async () => {
    const identity = loadIdentity();
    for (const readyDigest of [identity.manifestSha256, RESEARCH_SHA]) {
        let workerDigest;
        class FakeWorker extends EventEmitter {
            constructor(filename, { workerData }) {
                super();
                workerDigest = workerData.sourceManifestSha256;
                assert.equal(filename, path.join(__dirname, 'onnx_worker.cjs'));
                queueMicrotask(() =>
                    this.emit('message', {
                        schema: 'pg-replica-serving-ready-v1',
                        replica: 'replica1',
                        checkpointSha256: SHAS.replica1,
                        manifestSha256: readyDigest,
                    })
                );
            }
            terminate() {
                return Promise.resolve(0);
            }
        }
        const transport = new OnnxTransport({
            replica: 'replica1',
            modelDirectory: '/unused-in-fake-worker',
            exportManifestSha256: EXPORT_SHA,
            WorkerConstructor: FakeWorker,
        });
        try {
            assert.equal(workerDigest, identity.manifestSha256);
            if (readyDigest === identity.manifestSha256) {
                assert.equal((await transport.ready).manifestSha256, identity.manifestSha256);
            } else {
                await assert.rejects(transport.ready, errorCode('worker-protocol'));
                assert.equal(transport.closed, true);
            }
        } finally {
            transport.close();
        }
    }
});
