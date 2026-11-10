'use strict';
// Separately versioned Node port identity. Never relax or rewrite a research guard.
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const ROOT = path.resolve(__dirname, '../..');
const SHAS = Object.freeze({
    replica1: '7918c5ceec29ee181721eaaa3a38f63fd94cf0248c34d192e0b3f65960c729e5',
    replica2: '89d03f5b23fd6d088e175d32ff9c90ff88bd947f7e8b17d508b1b2f641a037fa',
});
const hash = (raw) => crypto.createHash('sha256').update(raw).digest('hex');
function requireThat(value, code) {
    if (!value) throw Object.assign(new Error(code), { code });
}
function freeze(value) {
    if (value && typeof value === 'object') {
        Object.values(value).forEach(freeze);
        Object.freeze(value);
    }
    return value;
}
function noLinks(file) {
    let current = path.resolve(file);
    for (;;) {
        requireThat(!fs.lstatSync(current).isSymbolicLink(), 'source-link');
        const parent = path.dirname(current);
        if (parent === current) return;
        current = parent;
    }
}
// Pure validation seam: tests can reject malformed manifests without rewriting frozen files.
function validateManifest(manifest, nodeVersion = process.version) {
    requireThat(
        exactKeys(manifest, [
            'schema',
            'replicas',
            'sourceFiles',
            'runtimes',
            'originalResearchManifestSha256',
            'exportManifestSha256',
        ]) && manifest.schema === 'pg-replica-bgs-source-v1',
        'manifest-schema'
    );
    requireThat(exactKeys(manifest.replicas, ['replica1', 'replica2']), 'manifest-roles');
    for (const [role, sha] of Object.entries(SHAS)) {
        requireThat(
            manifest.replicas[role]?.sha256 === sha && manifest.replicas[role]?.bytes === 793281,
            'checkpoint-pin'
        );
    }
    requireThat(
        hash(canonical(manifest.replicas)) === '95315cd0c837ccc0d58170574ad89bc8312afdcaa8e77b6b4e27a0e0853be96d',
        'checkpoint-pin'
    );
    requireThat(
        manifest.originalResearchManifestSha256 ===
            '8197fb7e35ed25a924d75e99eafcc140827b46ab441341bb14cd398c832b9f93' &&
            manifest.exportManifestSha256 === '8dac4ba18002a38868920875f0201f54200ac1ae062c51da3d615b189ffad543',
        'export-source-pin'
    );
    // Development loader only. The packaged entry independently requires v24.22.1 before imports.
    requireThat(
        exactKeys(manifest.runtimes, ['node', 'developmentNode', 'engine', 'ort']) &&
            manifest.runtimes.node === 'v24.22.1' &&
            manifest.runtimes.developmentNode === 'v24.20.0' &&
            manifest.runtimes.engine === '2.0.22' &&
            manifest.runtimes.ort === '1.31.1' &&
            [manifest.runtimes.node, manifest.runtimes.developmentNode].includes(nodeVersion),
        'runtime-version'
    );
    requireThat(
        manifest.sourceFiles && typeof manifest.sourceFiles === 'object' && !Array.isArray(manifest.sourceFiles),
        'source-inventory'
    );
    const entries = Object.entries(manifest.sourceFiles);
    requireThat(entries.length === 56, 'source-inventory');
    for (const [name, checksum] of entries) {
        requireThat(
            !path.isAbsolute(name) &&
                !name.includes('\\') &&
                !name.includes('\0') &&
                name.split('/').every((part) => part && part !== '.' && part !== '..'),
            'source-path'
        );
        requireThat(typeof checksum === 'string' && /^[0-9a-f]{64}$/.test(checksum), 'source-pin');
    }
    // Exact names AND original digests: 42 engine JS files plus 14 frozen JS/JSON inputs.
    // No Python, TypeScript source or circular hashes of these separately authenticated ports.
    requireThat(
        hash(canonical(manifest.sourceFiles)) === 'a73c03c0f3498607cf2f91aac22930c9cc5a1c38105962b3b5fd7cebbd799956',
        'source-inventory'
    );
}
function loadIdentity() {
    noLinks(path.join(__dirname, 'manifest.json'));
    const raw = fs.readFileSync(path.join(__dirname, 'manifest.json'));
    requireThat(raw.length < 128 * 1024, 'manifest-size');
    const manifest = JSON.parse(raw);
    validateManifest(manifest);
    for (const [name, checksum] of Object.entries(manifest.sourceFiles)) {
        const file = path.join(ROOT, name);
        noLinks(file);
        requireThat(fs.statSync(file).isFile() && hash(fs.readFileSync(file)) === checksum, 'source-identity');
    }
    return freeze({
        manifest,
        manifestSha256: hash(raw),
        exportSourceManifestSha256: manifest.originalResearchManifestSha256,
    });
}
function exactKeys(value, keys) {
    return (
        value !== null &&
        typeof value === 'object' &&
        !Array.isArray(value) &&
        Object.keys(value).sort().join('|') === [...keys].sort().join('|')
    );
}
function canonical(value) {
    if (Array.isArray(value)) return '[' + value.map(canonical).join(',') + ']';
    if (value && typeof value === 'object') {
        return (
            '{' +
            Object.keys(value)
                .sort()
                .map((k) => JSON.stringify(k) + ':' + canonical(value[k]))
                .join(',') +
            '}'
        );
    }
    requireThat(
        value === null ||
            typeof value === 'string' ||
            typeof value === 'boolean' ||
            (typeof value === 'number' && Number.isFinite(value)),
        'non-json-value'
    );
    return JSON.stringify(value);
}
// Engine states are persisted JSON. Normalize omitted optional fields just as the host does.
function cloneState(value) {
    const raw = JSON.stringify(value, function (key, item) {
        requireThat(typeof item !== 'number' || Number.isFinite(item), 'non-json-value');
        requireThat(!['symbol', 'bigint'].includes(typeof item), 'non-json-value');
        // Fresh engine maps may carry setupDeck functions (France). Like the platform's
        // JSON round-trip, omit object-only helpers; they are never inference inputs.
        requireThat((item !== undefined && typeof item !== 'function') || !Array.isArray(this), 'non-json-value');
        return item;
    });
    requireThat(typeof raw === 'string' && Buffer.byteLength(raw) <= 8 * 1024 * 1024, 'state-size');
    return JSON.parse(raw);
}
module.exports = {
    ROOT,
    SHAS,
    hash,
    requireThat,
    freeze,
    loadIdentity,
    exactKeys,
    canonical,
    cloneState,
    validateManifest,
};
