'use strict';
// Offline private test-package assembly. No registry publication, install scripts or model conversion.
const fs = require('node:fs');
const path = require('node:path');
const { createRequire } = require('node:module');
const { execFileSync } = require('node:child_process');
const crypto = require('node:crypto');
const ROOT = path.resolve(__dirname, '../..');
const EXPORT_SHA = '8dac4ba18002a38868920875f0201f54200ac1ae062c51da3d615b189ffad543';
const IMAGE =
    'docker.io/library/node:24.22.1-bookworm-slim@sha256:2dd9a4f758e173b65fee15388f7706af6fb01ef50cf7a2c0538711d67a6981ae';
const hash = (b) => crypto.createHash('sha256').update(b).digest('hex');
function need(ok, code) {
    if (!ok) throw Error(code);
}
function build({ replica, models, output }) {
    need(['replica1', 'replica2'].includes(replica), 'Explicit replica required');
    const destination = path.resolve(output);
    need(!fs.existsSync(destination), 'Output must be new');
    // Resolve only installed, already-reviewed dependencies. Never use npm install during assembly.
    const source = require('./identity.cjs').loadIdentity().manifest;
    const rawExport = fs.readFileSync(path.join(models, 'export-manifest.json'));
    need(hash(rawExport) === EXPORT_SHA, 'Unreviewed model export');
    const exported = JSON.parse(rawExport),
        files = new Map();
    function add(name, raw) {
        need(
            !path.isAbsolute(name) && !name.split('/').includes('..') && !name.includes('\\') && !files.has(name),
            'Invalid package path'
        );
        need(Buffer.isBuffer(raw), 'Expected immutable bytes');
        files.set(name, raw);
    }
    function copy(name, expected) {
        const file = path.join(ROOT, name);
        need(fs.lstatSync(file).isFile(), 'Expected regular source');
        const raw = fs.readFileSync(file);
        if (expected) need(hash(raw) === expected, `Changed frozen source ${name}`);
        add(name, raw);
    }
    for (const [name, sha] of Object.entries(source.sourceFiles)) copy(name, sha);
    copy('engine/LICENSE');
    for (const name of [
        'identity.cjs',
        'manifest.json',
        'adapter.cjs',
        'onnx.cjs',
        'onnx_worker.cjs',
        'deadline.cjs',
        'runtime.cjs',
    ])
        copy(`ai/serving_bgs_v1/${name}`);
    for (const [role, entry] of Object.entries(exported.replicas)) {
        need(entry.file === `${role}.onnx`, 'Model name');
        const raw = fs.readFileSync(path.join(models, entry.file));
        need(raw.length === entry.bytes && hash(raw) === entry.sha256, 'Changed ONNX bytes');
        add(`models/${entry.file}`, raw);
    }
    add('models/export-manifest.json', rawExport);
    const engineRequire = createRequire(path.join(ROOT, 'engine/package.json'));
    const onnxRequire = createRequire(path.join(__dirname, 'package.json'));
    function packageRoot(name, from) {
        let dir = path.dirname(from.resolve(name));
        for (;;) {
            const p = path.join(dir, 'package.json');
            if (fs.existsSync(p) && JSON.parse(fs.readFileSync(p)).name === name) return dir;
            need(path.dirname(dir) !== dir, 'Dependency root missing');
            dir = path.dirname(dir);
        }
    }
    const nativeRoot = packageRoot('onnxruntime-node', onnxRequire);
    const nativeRequire = createRequire(path.join(nativeRoot, 'package.json'));
    const versions = {
        lodash: '4.17.21',
        seedrandom: '3.0.5',
        delaunator: '4.0.1',
        'onnxruntime-node': '1.31.1',
        'onnxruntime-common': '1.31.1',
    };
    const dependencies = {};
    for (const [name, version] of Object.entries(versions)) {
        const directory = packageRoot(
            name,
            name === 'onnxruntime-node' ? onnxRequire : name === 'onnxruntime-common' ? nativeRequire : engineRequire
        );
        const metadata = JSON.parse(fs.readFileSync(path.join(directory, 'package.json')));
        need(metadata.version === version, 'Dependency version drift');
        let count = 0;
        function walk(dir, prefix = '') {
            for (const item of fs
                .readdirSync(dir, { withFileTypes: true })
                .sort((a, b) => a.name.localeCompare(b.name))) {
                const relative = prefix + item.name;
                need(!item.isSymbolicLink(), 'Dependency link');
                if (item.isDirectory()) {
                    if (['node_modules', 'test', 'tests', 'coverage', '.github'].includes(item.name)) continue;
                    if (
                        name === 'onnxruntime-node' &&
                        !['bin', 'bin/napi-v6', 'bin/napi-v6/linux', 'bin/napi-v6/linux/x64', 'dist'].includes(relative)
                    )
                        continue;
                    if (name === 'onnxruntime-common' && !['dist', 'dist/cjs'].includes(relative)) continue;
                    walk(path.join(dir, item.name), relative + '/');
                } else if (item.isFile()) {
                    if (
                        !(
                            /\.(js|cjs|json|node)$/.test(relative) ||
                            relative.endsWith('libonnxruntime.so.1') ||
                            /^(LICENSE|COPYING|ThirdPartyNotices)/i.test(relative)
                        )
                    )
                        continue;
                    // Never ship installers, CUDA download tools or ESM/browser distributions.
                    if (
                        name.startsWith('onnxruntime-') &&
                        relative.includes('/') &&
                        !relative.startsWith('dist/') &&
                        !relative.startsWith('bin/')
                    )
                        continue;
                    add(`node_modules/${name}/${relative}`, fs.readFileSync(path.join(dir, item.name)));
                    count++;
                }
            }
        }
        walk(directory);
        dependencies[name] = { version, files: count };
    }
    const packageName = `powergrid-private-ai-${replica}`;
    add(
        'package.json',
        Buffer.from(
            JSON.stringify(
                {
                    name: packageName,
                    version: '0.0.0-test.1',
                    private: true,
                    type: 'module',
                    main: 'index.mjs',
                    engines: { node: '24.22.1' },
                    // Native deps are already materialized. BGS installs with --ignore-scripts.
                    dependencies: versions,
                    bundledDependencies: Object.keys(versions),
                },
                null,
                4
            ) + '\n'
        )
    );
    const exports = Object.keys(require(path.join(ROOT, 'engine/dist/wrapper.js'))).sort();
    need(
        exports.every((name) => /^[A-Za-z][A-Za-z0-9]*$/.test(name)),
        'Unexpected export'
    );
    const runtimeManifest = {
        schema: 'pg-private-bgs-package-v1',
        replica,
        targetNode: 'v24.22.1',
        targetImage: IMAGE,
        platform: 'linux',
        arch: 'x64',
        exportManifestSha256: EXPORT_SHA,
        researchSourceManifestSha256: exported.sourceManifestSha256,
        servingSourceManifestSha256: hash(files.get('ai/serving_bgs_v1/manifest.json')),
        dependencies,
        files: Object.fromEntries(
            [...files].sort(([a], [b]) => a.localeCompare(b)).map(([n, b]) => [n, { sha256: hash(b), bytes: b.length }])
        ),
    };
    const rawManifest = Buffer.from(JSON.stringify(runtimeManifest, null, 4) + '\n');
    add('runtime-manifest.json', rawManifest);
    // Entry is the trusted root: its literal expected manifest hash authenticates everything imported below.
    const template = fs.readFileSync(path.join(__dirname, 'entry.template.mjs'), 'utf8');
    need(
        template.split('__RUNTIME_MANIFEST_SHA256__').length === 2 &&
            template.split('// __WRAPPER_EXPORTS__').length === 2,
        'Entry template markers'
    );
    const entry = template
        .replace('__RUNTIME_MANIFEST_SHA256__', hash(rawManifest))
        .replace(
            '// __WRAPPER_EXPORTS__',
            exports
                .map((name) => `export const ${name} = ${name === 'moveAI' ? 'runtime.moveAI' : `wrapper.${name}`};`)
                .join('\n')
        );
    add('index.mjs', Buffer.from(entry));
    const bytes = [...files.values()].reduce((n, b) => n + b.length, 0);
    need(files.size <= 1400 && bytes < 80 * 1024 * 1024, 'Package budget');
    fs.mkdirSync(destination, { recursive: true });
    const packageDirectory = path.join(destination, 'package');
    fs.mkdirSync(packageDirectory);
    for (const [name, raw] of files) {
        const target = path.join(packageDirectory, name);
        fs.mkdirSync(path.dirname(target), { recursive: true });
        fs.writeFileSync(target, raw, { flag: 'wx', mode: 0o644 });
        fs.chmodSync(target, 0o644);
    }
    // Normalize directory permissions too: umask must not change tar identity or UID-65534 readability.
    function normalizeDirectories(directory) {
        fs.chmodSync(directory, 0o755);
        for (const item of fs.readdirSync(directory, { withFileTypes: true }))
            if (item.isDirectory()) normalizeDirectories(path.join(directory, item.name));
    }
    normalizeDirectories(packageDirectory);
    // Deterministic npm-shaped archive with no private tokens, checkpoint/Python/worktree files.
    const tarball = path.join(destination, `${packageName}-0.0.0-test.1.tgz`);
    execFileSync('tar', [
        '--sort=name',
        '--mtime=@0',
        '--owner=0',
        '--group=0',
        '--numeric-owner',
        '-czf',
        tarball,
        '-C',
        destination,
        'package',
    ]);
    const record = {
        schema: 'pg-private-bgs-build-v1',
        replica,
        packageName,
        version: '0.0.0-test.1',
        entryPoint: 'index.mjs',
        packageFiles: files.size,
        packageBytes: bytes,
        targetImage: IMAGE,
        sourceFiles: Object.fromEntries(
            ['build.cjs', 'entry.template.mjs'].map((n) => [n, hash(fs.readFileSync(path.join(__dirname, n)))])
        ),
        runtimeManifestSha256: hash(rawManifest),
        entrySha256: hash(files.get('index.mjs')),
        tarball: path.basename(tarball),
        tarballBytes: fs.statSync(tarball).size,
        tarballSha256: hash(fs.readFileSync(tarball)),
        published: false,
    };
    fs.writeFileSync(path.join(destination, 'build.json'), JSON.stringify(record, null, 4) + '\n', {
        flag: 'wx',
        mode: 0o600,
    });
    return record;
}
module.exports = { build, IMAGE, EXPORT_SHA };
if (require.main === module) {
    const args = process.argv.slice(2);
    need(
        args.length === 6 && args[0] === '--replica' && args[2] === '--models' && args[4] === '--output',
        'Build arguments'
    );
    console.log(JSON.stringify(build({ replica: args[1], models: args[3], output: args[5] })));
}
