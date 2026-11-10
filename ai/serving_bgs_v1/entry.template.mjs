// Generated package entry: this template is never a BGS publication command.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { fileURLToPath } from 'node:url';
import { createRequire } from 'node:module';
const root = path.dirname(fileURLToPath(import.meta.url));
const digest = (raw) => crypto.createHash('sha256').update(raw).digest('hex');
const raw = fs.readFileSync(path.join(root, 'runtime-manifest.json'));
if (digest(raw) !== '__RUNTIME_MANIFEST_SHA256__') throw Error('Package manifest identity');
const manifest = JSON.parse(raw);
if (process.version !== manifest.targetNode || process.platform !== manifest.platform || process.arch !== manifest.arch)
    throw Error('Package runtime identity');
// Reject extra resolution shadows too, not just mutations of listed files.
const expectedFiles = new Set([...Object.keys(manifest.files), 'index.mjs', 'runtime-manifest.json']);
const expectedDirectories = new Set(['']);
for (const name of expectedFiles) {
    for (let directory = path.dirname(name); directory !== '.'; directory = path.dirname(directory))
        expectedDirectories.add(directory);
}
function verifyTree(relative = '') {
    for (const item of fs.readdirSync(path.join(root, relative), { withFileTypes: true })) {
        const name = path.join(relative, item.name);
        if (item.isDirectory() && expectedDirectories.has(name)) verifyTree(name);
        else if (item.isFile() && expectedFiles.delete(name)) continue;
        else throw Error('Package inventory identity');
    }
}
verifyTree();
if (expectedFiles.size) throw Error('Package inventory identity');
for (const [name, pin] of Object.entries(manifest.files)) {
    const file = path.join(root, name);
    let p = file;
    while (p !== root) {
        if (fs.lstatSync(p).isSymbolicLink()) throw Error('Package file link');
        p = path.dirname(p);
    }
    const raw = fs.readFileSync(file);
    if (raw.length !== pin.bytes || digest(raw) !== pin.sha256) throw Error('Package file identity');
}
const require = createRequire(import.meta.url);
const wrapper = require('./engine/dist/wrapper.js');
const { createRuntime } = require('./ai/serving_bgs_v1/runtime.cjs');
const diagnostics = { turns: 0, learned: 0, fixedV2: 0, heuristicFallback: 0, fallbackTurns: 0, circuitOpenEvents: 0 };
const runtime = createRuntime(
    {
        replica: manifest.replica,
        modelDirectory: path.join(root, 'models'),
        exportManifestSha256: manifest.exportManifestSha256,
    },
    {
        onDiagnostic(event) {
            if (event.event === 'circuit-open') diagnostics.circuitOpenEvents++;
            if (event.event === 'turn-complete') {
                diagnostics.turns++;
                diagnostics.fallbackTurns += +event.fallback;
                for (const key of ['learned', 'fixedV2', 'heuristicFallback']) diagnostics[key] += event.counts[key];
            }
        },
    }
);
// __WRAPPER_EXPORTS__
// Private test observability only. No game identifiers, states, moves or tensors.
export const aiStatus = () => ({ ...runtime.getStatus(), diagnostics: { ...diagnostics } });
