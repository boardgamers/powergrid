'use strict';
// Private, offline artifact tests. Run with the actual pinned Node binary, e.g.:
// "$(cat /tmp/pg-bgs-node-target-path)/node-v24.22.1-linux-x64/bin/node" \
//   --test --test-reporter=tap ai/serving_bgs_v1/test_build.cjs
// Requires the retained private ONNX export, installed build dependencies, GNU tar,
// npm beside Node, and actual v24.20.0 on PATH (or PG_BGS_NODE_24_20). No downloads.
// The separate UID-65534 filesystem check requires root, UID 65534, or passwordless
// sudo. It is NOT an execution/test of the pinned deployment container image.
// Only disposable copies are modified; no frozen source, old serving code, model
// source, dependency installation in the workspace, or publication is touched.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const crypto = require('node:crypto');
const { spawnSync } = require('node:child_process');
const { build, EXPORT_SHA, IMAGE } = require('./build.cjs');
const { loadIdentity } = require('./identity.cjs');
const ROOT = path.resolve(__dirname, '../..');
const MODELS = path.join(ROOT, 'ai/runs/serving-prototype-v1/onnx-final');
const PIN = '8dac4ba18002a38868920875f0201f54200ac1ae062c51da3d615b189ffad543';
const IMAGE_PIN =
    'docker.io/library/node:24.22.1-bookworm-slim@sha256:2dd9a4f758e173b65fee15388f7706af6fb01ef50cf7a2c0538711d67a6981ae';
const VERSIONS = {
    lodash: '4.17.21',
    seedrandom: '3.0.5',
    delaunator: '4.0.1',
    'onnxruntime-node': '1.31.1',
    'onnxruntime-common': '1.31.1',
};
const PORT_FILES = [
    'identity.cjs',
    'manifest.json',
    'adapter.cjs',
    'onnx.cjs',
    'onnx_worker.cjs',
    'deadline.cjs',
    'runtime.cjs',
].map((name) => `ai/serving_bgs_v1/${name}`);
const hash = (raw) => crypto.createHash('sha256').update(raw).digest('hex');
const readJSON = (file) => JSON.parse(fs.readFileSync(file, 'utf8'));

function run(command, args, options = {}) {
    return spawnSync(command, args, {
        cwd: '/',
        env: {},
        encoding: 'utf8',
        timeout: 120000,
        maxBuffer: 1024 * 1024,
        ...options,
    });
}
function succeeded(result, label) {
    // Do not propagate paths, npm diagnostics, native-library output or error stacks
    // into TAP. Failure classification is deliberately a fixed vocabulary.
    assert.equal(result.error === undefined, true, `${label}: process launch/timeout failure`);
    assert.equal(result.signal, null, `${label}: process signal`);
    assert.equal(result.status, 0, `${label}: nonzero exit`);
    assert.equal(result.stderr.length, 0, `${label}: unexpected stderr (suppressed)`);
}
function walk(root) {
    const files = [],
        directories = [];
    function visit(relative) {
        const full = path.join(root, relative),
            stat = fs.lstatSync(full);
        assert.equal(stat.isSymbolicLink(), false, `no package symlink: ${relative}`);
        if (stat.isDirectory()) {
            directories.push(relative);
            for (const name of fs.readdirSync(full).sort()) visit(path.join(relative, name));
        } else {
            assert.equal(stat.isFile(), true, `regular package file: ${relative}`);
            files.push(relative.split(path.sep).join('/'));
        }
    }
    visit('');
    return { files: files.sort(), directories };
}

// Real child imports are cwd-independent and receive an empty environment. For
// negative cases the load tripwire both counts and prevents CJS/native execution
// if verification regresses; checking an error alone would miss "load then fail".
const PROBE = String.raw`
import fs from 'node:fs';
import path from 'node:path';
import Module, { createRequire } from 'node:module';
import { pathToFileURL } from 'node:url';
const [root, mode] = process.argv.slice(1);
const rejectLoads = mode === 'reject';
let packageLoads = 0, nativeLoads = 0;
const originalLoad = Module._load;
Module._load = function (request, parent, ...rest) {
    if (parent?.filename?.startsWith(root + path.sep) || request.startsWith(root + path.sep)) {
        packageLoads++;
        if (rejectLoads) throw Error('probe-load-tripwire');
    }
    return originalLoad.call(this, request, parent, ...rest);
};
const originalDlopen = process.dlopen;
process.dlopen = function (...args) {
    nativeLoads++;
    if (rejectLoads) throw Error('probe-native-tripwire');
    return originalDlopen.apply(this, args);
};
const info = { version: process.version, cwd: process.cwd(), envKeys: Object.keys(process.env).length,
    uid: process.getuid(), gid: process.getgid() };
try {
    const entry = path.join(root, 'index.mjs');
    const api = await import(pathToFileURL(entry).href);
    const wrapper = createRequire(entry)('./engine/dist/wrapper.js');
    const names = Object.keys(wrapper).sort();
    const status = api.aiStatus();
    const snapshot = JSON.stringify(status);
    const exposed = api.aiStatus();
    exposed.replica = 'changed';
    exposed.diagnostics.turns = 999;
    exposed.diagnostics.extra = true;
    console.log(JSON.stringify({ ...info, ok: true, exports: Object.keys(api).sort(), wrapperExports: names,
        unchangedExports: names.filter((name) => name !== 'moveAI').every((name) => api[name] === wrapper[name]),
        replacedMoveAI: typeof api.moveAI === 'function' && api.moveAI !== wrapper.moveAI,
        status, statusDetached: JSON.stringify(api.aiStatus()) === snapshot, packageLoads, nativeLoads }));
} catch (error) {
    const allowed = ['Package manifest identity', 'Package runtime identity', 'Package inventory identity',
        'Package file identity', 'Package file link', 'runtime-source-identity', 'probe-load-tripwire', 'probe-native-tripwire'];
    const codes = ['ENOENT', 'EISDIR', 'ERR_MODULE_NOT_FOUND', 'EACCES'];
    const reason = allowed.includes(error?.message) ? error.message : codes.includes(error?.code) ? error.code : 'unexpected';
    console.log(JSON.stringify({ ...info, ok: false, reason, packageLoads, nativeLoads }));
}
`;
function probe(root, { node = process.execPath, reject = false, asNobody = false } = {}) {
    const args = ['--input-type=module', '-e', PROBE, root, reject ? 'reject' : 'healthy'];
    let result;
    if (asNobody && process.getuid() !== 0 && process.getuid() !== 65534) {
        result = run('/usr/bin/sudo', [
            '-n',
            '-u',
            '#65534',
            '-g',
            '#65534',
            '--',
            '/usr/bin/env',
            '-i',
            node,
            ...args,
        ]);
    } else {
        result = run(node, args, asNobody ? { uid: 65534, gid: 65534 } : {});
    }
    succeeded(result, 'isolated import');
    // JSON.parse does not include child output in an assertion failure.
    let value;
    try {
        value = JSON.parse(result.stdout);
    } catch (_) {
        assert.fail('isolated import: invalid report');
    }
    assert.equal(value.cwd, '/');
    assert.equal(value.envKeys, 0);
    return value;
}
function rejected(root, reason, options = {}) {
    const result = probe(root, { ...options, reject: true });
    assert.equal(result.ok, false, 'import must reject');
    assert.equal(result.reason, reason);
    assert.equal(result.packageLoads, 0, 'reject before any package module loads');
    assert.equal(result.nativeLoads, 0, 'reject before native code loads');
}
function healthy(root, replica, expectedExports, options = {}) {
    const result = probe(root, options);
    assert.equal(result.ok, true, `healthy import (${result.reason || 'accepted'})`);
    assert.equal(result.version, 'v24.22.1');
    assert.deepEqual(result.wrapperExports, expectedExports);
    assert.deepEqual(result.exports, [...expectedExports, 'aiStatus'].sort());
    assert.equal(result.unchangedExports, true, 'all exports except moveAI retain wrapper identity');
    assert.equal(result.replacedMoveAI, true);
    assert.equal(result.statusDetached, true, 'aiStatus returns detached observations');
    assert.deepEqual(result.status, {
        replica,
        state: 'idle',
        circuitReason: null,
        activeCalls: 0,
        limits: { startupMs: 2000, inferenceMs: 1000, turnMs: 3000, fallbackMs: 1000, maxActiveCalls: 8 },
        diagnostics: { turns: 0, learned: 0, fixedV2: 0, heuristicFallback: 0, fallbackTurns: 0, circuitOpenEvents: 0 },
    });
    assert.equal(result.nativeLoads, 0, 'import/status must not start native inference');
    return result;
}
function modifiedFile(root, name, modify, check) {
    const file = path.join(root, name),
        original = fs.readFileSync(file);
    try {
        modify(file, Buffer.from(original));
        check();
    } finally {
        fs.rmSync(file, { force: true, recursive: true });
        fs.writeFileSync(file, original, { flag: 'wx', mode: 0o644 });
    }
}
function developmentNode() {
    const candidates = process.env.PG_BGS_NODE_24_20
        ? [process.env.PG_BGS_NODE_24_20]
        : (process.env.PATH || '')
              .split(path.delimiter)
              .filter(Boolean)
              .map((dir) => path.resolve(dir, 'node'));
    for (const candidate of candidates) {
        const result = run(candidate, ['--version']);
        if (result.status === 0 && result.stdout.trim() === 'v24.20.0') return candidate;
    }
    assert.fail('actual Node v24.20.0 required on PATH or PG_BGS_NODE_24_20; never spoof process.version');
}

function inspectArtifact(directory, record, replica, identity, exported) {
    const root = path.join(directory, 'package'),
        { files, directories } = walk(root);
    const raw = fs.readFileSync(path.join(root, 'runtime-manifest.json'));
    const manifest = JSON.parse(raw),
        metadata = readJSON(path.join(root, 'package.json'));
    assert.equal(manifest.schema, 'pg-private-bgs-package-v1');
    assert.equal(manifest.replica, replica);
    assert.equal(manifest.targetNode, 'v24.22.1');
    assert.equal(manifest.targetImage, IMAGE_PIN);
    assert.equal(manifest.platform, 'linux');
    assert.equal(manifest.arch, 'x64');
    assert.equal(manifest.exportManifestSha256, PIN);
    assert.equal(manifest.researchSourceManifestSha256, exported.sourceManifestSha256);
    assert.equal(manifest.servingSourceManifestSha256, identity.manifestSha256);
    assert.deepEqual(
        Object.keys(manifest.files).sort(),
        files.filter((name) => !['index.mjs', 'runtime-manifest.json'].includes(name))
    );
    for (const [name, pin] of Object.entries(manifest.files)) {
        const bytes = fs.readFileSync(path.join(root, name));
        assert.deepEqual(pin, { sha256: hash(bytes), bytes: bytes.length }, `authenticated bytes: ${name}`);
    }
    // identity.cjs/test_identity.cjs own the exact path-inventory policy. Reuse
    // their authenticated 56 entries; never rewrite source to exercise that guard.
    const frozen = Object.keys(identity.manifest.sourceFiles).sort();
    assert.equal(frozen.length, 56);
    const ownFiles = [
        ...frozen,
        ...PORT_FILES,
        'engine/LICENSE',
        'models/export-manifest.json',
        'models/replica1.onnx',
        'models/replica2.onnx',
        'package.json',
        'index.mjs',
        'runtime-manifest.json',
    ].sort();
    assert.deepEqual(
        files.filter((name) => !name.startsWith('node_modules/')),
        ownFiles
    );
    for (const [name, sha] of Object.entries(identity.manifest.sourceFiles))
        assert.equal(manifest.files[name].sha256, sha);
    // The MIT notice accompanies the frozen engine, but is not a 57th code-identity entry.
    for (const name of [...PORT_FILES, 'engine/LICENSE'])
        assert.equal(manifest.files[name].sha256, hash(fs.readFileSync(path.join(ROOT, name))));
    for (const role of ['replica1', 'replica2']) {
        assert.deepEqual(manifest.files[`models/${role}.onnx`], {
            sha256: exported.replicas[role].sha256,
            bytes: exported.replicas[role].bytes,
        });
    }
    assert.equal(manifest.files['models/export-manifest.json'].sha256, PIN);
    assert.equal(metadata.name, `powergrid-private-ai-${replica}`);
    assert.equal(metadata.version, '0.0.0-test.1');
    assert.equal(metadata.private, true);
    assert.equal(metadata.type, 'module');
    assert.equal(metadata.main, 'index.mjs');
    assert.deepEqual(metadata.engines, { node: '24.22.1' });
    assert.deepEqual(metadata.dependencies, VERSIONS);
    assert.deepEqual([...metadata.bundledDependencies].sort(), Object.keys(VERSIONS).sort());
    assert.equal(Object.hasOwn(metadata, 'scripts'), false);
    assert.deepEqual(fs.readdirSync(path.join(root, 'node_modules')).sort(), Object.keys(VERSIONS).sort());
    assert.deepEqual(Object.keys(manifest.dependencies).sort(), Object.keys(VERSIONS).sort());
    for (const [name, version] of Object.entries(VERSIONS)) {
        const entries = files.filter((file) => file.startsWith(`node_modules/${name}/`));
        assert.deepEqual(manifest.dependencies[name], { version, files: entries.length });
        assert.equal(readJSON(path.join(root, 'node_modules', name, 'package.json')).version, version);
    }
    for (const name of files) {
        assert.equal(
            /\.(?:py|pyc|pyo|pt|pth|ckpt|safetensors|pkl|pickle|ts|tsx)$/i.test(name),
            false,
            `no training/source file: ${name}`
        );
        assert.equal(
            /(?:^|\/)(?:\.git|\.env|\.npmrc|__pycache__|checkpoints?|runs|adm-zip|global-agent)(?:\/|$)/i.test(name),
            false
        );
        assert.equal(fs.statSync(path.join(root, name)).mode & 0o7777, 0o644, `regular-file mode: ${name}`);
    }
    for (const name of directories)
        assert.equal(fs.statSync(path.join(root, name)).mode & 0o7777, 0o755, 'traversable package directory');
    const native = files.filter((name) => /\.node$|\.so(?:\.\d+)*$/.test(name));
    assert.deepEqual(native, [
        'node_modules/onnxruntime-node/bin/napi-v6/linux/x64/libonnxruntime.so.1',
        'node_modules/onnxruntime-node/bin/napi-v6/linux/x64/onnxruntime_binding.node',
    ]);
    const bytes = files.reduce((sum, name) => sum + fs.statSync(path.join(root, name)).size, 0);
    assert.ok(files.length <= 1400, 'source-built package file budget');
    assert.ok(bytes < 80 * 1024 * 1024, 'source-built package byte budget');
    assert.equal(record.schema, 'pg-private-bgs-build-v1');
    assert.equal(record.replica, replica);
    assert.equal(record.packageName, metadata.name);
    assert.equal(record.packageFiles, files.length);
    assert.equal(record.packageBytes, bytes);
    assert.equal(record.entryPoint, 'index.mjs');
    assert.equal(record.runtimeManifestSha256, hash(raw));
    assert.equal(record.entrySha256, hash(fs.readFileSync(path.join(root, 'index.mjs'))));
    assert.equal(record.published, false);
    assert.deepEqual(readJSON(path.join(directory, 'build.json')), record);
    for (const name of ['build.cjs', 'entry.template.mjs'])
        assert.equal(record.sourceFiles[name], hash(fs.readFileSync(path.join(__dirname, name))));
    const entry = fs.readFileSync(path.join(root, 'index.mjs'), 'utf8');
    assert.ok(entry.includes(`'${hash(raw)}'`), 'entry embeds literal manifest hash');
    assert.equal(entry.includes('__RUNTIME_MANIFEST_SHA256__'), false);
    assert.equal(entry.includes('__WRAPPER_EXPORTS__'), false);
    const tarball = path.join(directory, record.tarball);
    assert.equal(fs.statSync(tarball).size, record.tarballBytes);
    assert.equal(hash(fs.readFileSync(tarball)), record.tarballSha256);
    const listing = run('/usr/bin/tar', ['-tzf', tarball]);
    succeeded(listing, 'tar inventory');
    const tarNames = listing.stdout.trim().split('\n');
    assert.equal(new Set(tarNames).size, tarNames.length, 'no duplicate tar members');
    assert.deepEqual(
        tarNames.sort(),
        [
            ...files.map((name) => `package/${name}`),
            ...directories.map((name) => (name ? `package/${name}/` : 'package/')),
        ].sort()
    );
    return { root, manifest, record, tarball };
}

test('private Node-only package build/import/install contract', { timeout: 300000 }, async (t) => {
    assert.equal(process.version, 'v24.22.1', 'run this suite with the actual target Node, not the development Node');
    assert.equal(process.platform, 'linux');
    assert.equal(process.arch, 'x64');
    const temporary = fs.mkdtempSync(path.join(fs.realpathSync(os.tmpdir()), 'pg-bgs-build-test-'));
    try {
        let identity, exported, devNode;
        await t.test('retained private models and actual runtime prerequisites are mandatory, never skipped', () => {
            assert.equal(EXPORT_SHA, PIN);
            assert.equal(IMAGE, IMAGE_PIN);
            identity = loadIdentity();
            const raw = fs.readFileSync(path.join(MODELS, 'export-manifest.json'));
            assert.equal(hash(raw), PIN);
            exported = JSON.parse(raw);
            assert.deepEqual(Object.keys(exported.replicas).sort(), ['replica1', 'replica2']);
            for (const role of ['replica1', 'replica2']) {
                const file = path.join(MODELS, `${role}.onnx`),
                    pin = exported.replicas[role];
                assert.equal(fs.lstatSync(file).isFile(), true);
                const model = fs.readFileSync(file);
                assert.equal(hash(model), pin.sha256);
                assert.equal(model.length, pin.bytes);
                assert.equal(pin.checkpointSha256, identity.manifest.replicas[role].sha256);
            }
            devNode = developmentNode();
        });
        // Abort setup rather than emitting misleading dependent failures/skips.
        assert.ok(identity && exported && devNode, 'mandatory artifact prerequisites failed');
        await t.test('both roles must be explicit; invalid roles/no CLI default/existing outputs reject', () => {
            for (const replica of [undefined, null, '', 'replica3', 'Replica1', 'replica1,replica2']) {
                const output = path.join(temporary, 'invalid-role');
                assert.throws(() => build({ replica, models: MODELS, output }), /Explicit replica required/);
                assert.equal(fs.existsSync(output), false);
            }
            const cli = run(process.execPath, [
                '--input-type=module',
                '-e',
                `
                import { createRequire } from 'node:module';
                const require = createRequire(import.meta.url);
                process.argv = [process.execPath, ${JSON.stringify(path.join(__dirname, 'build.cjs'))}];
                try { require('node:module')._load(process.argv[1], null, true); process.exitCode = 2; }
                catch (_) { console.log('build-arguments-rejected'); }
            `,
            ]);
            succeeded(cli, 'missing CLI arguments');
            assert.equal(cli.stdout.trim(), 'build-arguments-rejected');
            for (const kind of ['directory', 'file']) {
                const output = path.join(temporary, `existing-${kind}`);
                if (kind === 'directory') fs.mkdirSync(output);
                else fs.writeFileSync(output, 'sentinel');
                assert.throws(() => build({ replica: 'replica1', models: MODELS, output }), /Output must be new/);
                if (kind === 'file') assert.equal(fs.readFileSync(output, 'utf8'), 'sentinel');
                else assert.deepEqual(fs.readdirSync(output), []);
            }
        });
        await t.test('builder rejects missing, altered and self-rehashed model exports without source mutation', () => {
            const models = path.join(temporary, 'bad-models');
            fs.mkdirSync(models);
            for (const name of ['export-manifest.json', 'replica1.onnx', 'replica2.onnx'])
                fs.copyFileSync(path.join(MODELS, name), path.join(models, name));
            const output = path.join(temporary, 'rejected-model-build');
            const attempt = (matcher) => {
                assert.throws(() => build({ replica: 'replica1', models, output }), matcher);
                assert.equal(fs.existsSync(output), false);
            };
            modifiedFile(
                models,
                'export-manifest.json',
                (file) => fs.appendFileSync(file, '\n'),
                () => attempt(/Unreviewed model export/)
            );
            for (const role of ['replica1', 'replica2']) {
                modifiedFile(
                    models,
                    `${role}.onnx`,
                    (file, bytes) => {
                        bytes[0] ^= 1;
                        fs.writeFileSync(file, bytes);
                    },
                    () => attempt(/Changed ONNX bytes/)
                );
                modifiedFile(
                    models,
                    `${role}.onnx`,
                    (file) => fs.unlinkSync(file),
                    () => attempt({ code: 'ENOENT' })
                );
            }
            modifiedFile(
                models,
                'export-manifest.json',
                (file, bytes) => {
                    const changed = JSON.parse(bytes);
                    changed.replicas.replica1.sha256 = '0'.repeat(64);
                    fs.writeFileSync(file, JSON.stringify(changed));
                },
                () => attempt(/Unreviewed model export/)
            );
        });
        const artifacts = {};
        for (const [key, replica] of [
            ['r1', 'replica1'],
            ['r1Again', 'replica1'],
            ['r2', 'replica2'],
        ]) {
            await t.test(
                `build ${key}: exact authenticated inventory, model roles, native files, modes and budgets`,
                () => {
                    const output = path.join(temporary, key);
                    const originalUmask = process.umask(key === 'r1Again' ? 0o077 : 0o022);
                    try {
                        const record = build({ replica, models: MODELS, output });
                        artifacts[key] = inspectArtifact(output, record, replica, identity, exported);
                    } finally {
                        process.umask(originalUmask);
                    }
                }
            );
        }
        assert.ok(artifacts.r1 && artifacts.r1Again && artifacts.r2, 'required builds failed');
        await t.test('umask 022 vs 077 builds have byte-identical deterministic tarballs and build records', () => {
            assert.deepEqual(artifacts.r1.record, artifacts.r1Again.record);
            assert.equal(artifacts.r1.record.tarballSha256, artifacts.r1Again.record.tarballSha256);
            assert.equal(
                fs.readFileSync(artifacts.r1.tarball).equals(fs.readFileSync(artifacts.r1Again.tarball)),
                true
            );
            assert.notEqual(artifacts.r1.record.runtimeManifestSha256, artifacts.r2.record.runtimeManifestSha256);
        });
        const expectedExports = Object.keys(require(path.join(ROOT, 'engine/dist/wrapper.js'))).sort();
        for (const [key, replica] of [
            ['r1', 'replica1'],
            ['r2', 'replica2'],
        ]) {
            await t.test(`${replica}: empty-environment/root-cwd ESM export parity and role-bound aiStatus`, () => {
                healthy(artifacts[key].root, replica, expectedExports);
            });
            await t.test(`${replica}: real development Node v24.20.0 rejects before package loads`, () => {
                rejected(artifacts[key].root, 'Package runtime identity', { node: devNode });
            });
        }
        // Mutate only the second, disposable build, after reproducibility checks.
        const damage = artifacts.r1Again.root;
        const targets = [
            'engine/dist/wrapper.js',
            'ai/core.cjs',
            'ai/serving_bgs_v1/runtime.cjs',
            'node_modules/lodash/lodash.js',
            'models/replica1.onnx',
            'models/replica2.onnx',
            ...Object.keys(artifacts.r1.manifest.files).filter((name) => /\.node$|\.so(?:\.\d+)*$/.test(name)),
        ];
        for (const name of targets) {
            await t.test(`same-length byte tamper rejects before loading: ${name}`, () => {
                modifiedFile(
                    damage,
                    name,
                    (file, bytes) => {
                        bytes[0] ^= 1;
                        fs.writeFileSync(file, bytes);
                    },
                    () => rejected(damage, 'Package file identity')
                );
            });
            await t.test(`missing authenticated file rejects before loading: ${name}`, () => {
                modifiedFile(
                    damage,
                    name,
                    (file) => fs.unlinkSync(file),
                    () => rejected(damage, 'Package inventory identity')
                );
            });
        }
        for (const name of ['models/replica1.onnx', targets.find((file) => file.endsWith('.node'))]) {
            await t.test(`byte-identical model/native symlink rejects: ${name}`, () => {
                const outside = path.join(temporary, 'link-target');
                fs.copyFileSync(path.join(damage, name), outside);
                try {
                    modifiedFile(
                        damage,
                        name,
                        (file) => {
                            fs.unlinkSync(file);
                            fs.symlinkSync(outside, file);
                        },
                        () => rejected(damage, 'Package inventory identity')
                    );
                } finally {
                    fs.rmSync(outside, { force: true });
                }
            });
        }
        await t.test('symlinked model directory rejects before loading despite identical contents', () => {
            const directory = path.join(damage, 'models'),
                outside = path.join(temporary, 'moved-models');
            fs.renameSync(directory, outside);
            try {
                fs.symlinkSync(outside, directory, 'dir');
                rejected(damage, 'Package inventory identity');
            } finally {
                fs.rmSync(directory, { force: true });
                fs.renameSync(outside, directory);
            }
        });
        for (const [name, addedRoot] of [
            ['engine/node_modules/lodash/index.js', 'engine/node_modules'],
            ['engine/dist/src/engine', 'engine/dist/src/engine'],
        ]) {
            await t.test(`extra resolution shadow rejects before loading: ${name}`, () => {
                const originalTree = walk(damage);
                const file = path.join(damage, name),
                    cleanup = path.join(damage, addedRoot);
                assert.equal(fs.existsSync(cleanup), false, 'shadow must not replace authenticated contents');
                try {
                    fs.mkdirSync(path.dirname(file), { recursive: true });
                    fs.writeFileSync(file, "throw Error('shadow must never load');\n", { flag: 'wx' });
                    rejected(damage, 'Package inventory identity');
                } finally {
                    fs.rmSync(cleanup, { recursive: true, force: true });
                }
                assert.deepEqual(walk(damage), originalTree, 'remove shadow and all newly added directories');
            });
        }
        const manifestChanges = {
            whitespace: (raw) => Buffer.concat([raw, Buffer.from('\n')]),
            role: (raw) => {
                const m = JSON.parse(raw);
                m.replica = 'replica2';
                return JSON.stringify(m);
            },
            inventory: (raw) => {
                const m = JSON.parse(raw);
                delete m.files['models/replica1.onnx'];
                return JSON.stringify(m);
            },
            node: (raw) => {
                const m = JSON.parse(raw);
                m.targetNode = 'v24.20.0';
                return JSON.stringify(m);
            },
        };
        for (const [label, change] of Object.entries(manifestChanges)) {
            await t.test(`literal entry hash rejects manifest alteration: ${label}`, () => {
                modifiedFile(
                    damage,
                    'runtime-manifest.json',
                    (file, raw) => fs.writeFileSync(file, change(raw)),
                    () => rejected(damage, 'Package manifest identity')
                );
            });
        }
        await t.test('rehashed tampered model cannot re-authenticate its own manifest', () => {
            modifiedFile(
                damage,
                'models/replica1.onnx',
                (file, raw) => {
                    raw[0] ^= 1;
                    fs.writeFileSync(file, raw);
                },
                () => {
                    modifiedFile(
                        damage,
                        'runtime-manifest.json',
                        (file, raw) => {
                            const m = JSON.parse(raw),
                                bytes = fs.readFileSync(path.join(damage, 'models/replica1.onnx'));
                            m.files['models/replica1.onnx'] = { sha256: hash(bytes), bytes: bytes.length };
                            fs.writeFileSync(file, JSON.stringify(m));
                        },
                        () => rejected(damage, 'Package manifest identity')
                    );
                }
            );
        });
        for (const [name, reason] of [
            ['runtime-manifest.json', 'ENOENT'],
            ['index.mjs', 'ERR_MODULE_NOT_FOUND'],
        ]) {
            await t.test(`missing ${name} rejects import before loading`, () => {
                modifiedFile(
                    damage,
                    name,
                    (file) => fs.unlinkSync(file),
                    () => rejected(damage, reason)
                );
            });
        }
        await t.test('restored disposable artifact has the exact original tree and still imports normally', () => {
            assert.deepEqual(walk(damage), walk(artifacts.r1.root));
            healthy(damage, 'replica1', expectedExports);
        });
        let installed;
        await t.test(
            'both generated tgz aliases install offline with ignored scripts and an isolated initially empty cache',
            () => {
                const stage = path.join(temporary, 'npm-stage'),
                    cache = path.join(temporary, 'npm-cache');
                const home = path.join(temporary, 'npm-home');
                for (const dir of [stage, cache, home]) fs.mkdirSync(dir);
                fs.writeFileSync(
                    path.join(stage, 'package.json'),
                    JSON.stringify({ name: 'private-offline-build-test', version: '0.0.0', private: true })
                );
                const config = path.join(home, 'user.npmrc'),
                    globalConfig = path.join(home, 'global.npmrc');
                fs.writeFileSync(config, '');
                fs.writeFileSync(globalConfig, '');
                assert.deepEqual(fs.readdirSync(cache), []);
                const npm = path.resolve(path.dirname(process.execPath), '../lib/node_modules/npm/bin/npm-cli.js');
                assert.equal(fs.statSync(npm).isFile(), true, 'npm must accompany target Node');
                const result = run(
                    process.execPath,
                    [
                        npm,
                        'install',
                        '--ignore-scripts',
                        '--offline',
                        '--no-audit',
                        '--no-fund',
                        '--no-update-notifier',
                        '--cache',
                        cache,
                        '--userconfig',
                        config,
                        '--globalconfig',
                        globalConfig,
                        `pg-test-r1@file:${artifacts.r1.tarball}`,
                        `pg-test-r2@file:${artifacts.r2.tarball}`,
                    ],
                    {
                        cwd: stage,
                        env: { HOME: home, PATH: `${path.dirname(process.execPath)}:/usr/bin:/bin` },
                    }
                );
                succeeded(result, 'offline npm alias install');
                installed = {
                    r1: path.join(stage, 'node_modules/pg-test-r1'),
                    r2: path.join(stage, 'node_modules/pg-test-r2'),
                };
                for (const [key, replica] of [
                    ['r1', 'replica1'],
                    ['r2', 'replica2'],
                ]) {
                    const root = installed[key],
                        original = artifacts[key].root;
                    const files = walk(root).files;
                    assert.deepEqual(
                        files,
                        walk(original).files,
                        'npm must preserve the complete authenticated artifact'
                    );
                    for (const name of files) {
                        assert.equal(
                            hash(fs.readFileSync(path.join(root, name))),
                            hash(fs.readFileSync(path.join(original, name))),
                            `installed bytes: ${name}`
                        );
                    }
                    healthy(root, replica, expectedExports);
                }
                // These installer-only transitive packages are deliberately absent;
                // five bundled runtime dependencies are sufficient, not a failure.
                const allInstalled = walk(path.join(stage, 'node_modules')).files;
                assert.equal(
                    allInstalled.some((name) => /(?:^|\/)(?:adm-zip|global-agent)(?:\/|$)/.test(name)),
                    false
                );
            }
        );
        assert.ok(installed, 'offline install required for cross-UID check');
        await t.test(
            'separate host-filesystem check: installed packages are readable/importable as UID/GID 65534',
            () => {
                // Do not chmod the target distribution, workspace or package contents.
                // The downloaded binary lives under a private parent, so copy it into
                // this disposable fixture and grant traversal only on the test root.
                const node = path.join(temporary, 'target-node');
                fs.copyFileSync(process.execPath, node, fs.constants.COPYFILE_FICLONE);
                fs.chmodSync(node, 0o755);
                fs.chmodSync(temporary, 0o711);
                try {
                    for (const [key, replica] of [
                        ['r1', 'replica1'],
                        ['r2', 'replica2'],
                    ]) {
                        const result = healthy(installed[key], replica, expectedExports, { node, asNobody: true });
                        assert.equal(result.uid, 65534);
                        assert.equal(result.gid, 65534);
                        for (const name of walk(installed[key]).files)
                            assert.equal(fs.statSync(path.join(installed[key], name)).mode & 0o7777, 0o644);
                    }
                } finally {
                    fs.chmodSync(temporary, 0o700);
                }
            }
        );
        t.diagnostic(
            `build inventory: ${artifacts.r1.record.packageFiles} files, ${artifacts.r1.record.packageBytes} bytes; three builds, two replicas, two offline-installed aliases`
        );
        t.diagnostic(`reproducible replica1 tgz SHA256: ${artifacts.r1.record.tarballSha256}`);
        t.diagnostic(
            'UID/GID 65534 result is host-filesystem evidence only; no container-image or full gameplay conformance claim'
        );
    } finally {
        fs.rmSync(temporary, { recursive: true, force: true });
    }
});
