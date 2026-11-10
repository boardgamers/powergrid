'use strict';
// Separate local prototype identity. Never relax or rewrite a research guard.
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
function loadIdentity() {
    noLinks(path.join(__dirname, 'manifest.json'));
    const raw = fs.readFileSync(path.join(__dirname, 'manifest.json'));
    requireThat(raw.length < 128 * 1024, 'manifest-size');
    const manifest = JSON.parse(raw);
    requireThat(manifest.schema === 'pg-replica-serving-manifest-v1', 'manifest-schema');
    requireThat(Object.keys(manifest.replicas).sort().join(',') === 'replica1,replica2', 'manifest-roles');
    for (const [role, sha] of Object.entries(SHAS)) {
        requireThat(
            manifest.replicas[role].sha256 === sha && manifest.replicas[role].bytes === 793281,
            'checkpoint-pin'
        );
    }
    requireThat(process.version === manifest.runtimes.node && manifest.runtimes.engine === '2.0.22', 'runtime-version');
    const entries = Object.entries(manifest.sourceFiles);
    requireThat(entries.length > 42 && entries.length < 256, 'source-inventory');
    for (const [name, checksum] of entries) {
        requireThat(!path.isAbsolute(name) && !name.split('/').includes('..') && !name.includes('\\'), 'source-path');
        const file = path.join(ROOT, name);
        noLinks(file);
        requireThat(fs.statSync(file).isFile() && hash(fs.readFileSync(file)) === checksum, 'source-identity');
    }
    return freeze({ manifest, manifestSha256: hash(raw) });
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
module.exports = { ROOT, SHAS, hash, requireThat, freeze, loadIdentity, exactKeys, canonical, cloneState };
