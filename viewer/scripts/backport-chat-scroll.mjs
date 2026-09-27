import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { mkdir, writeFile } from 'node:fs/promises';

// Ongoing version-11 games use this older viewer and its matching embedded engine.
// Backport only the shared chat fix; never substitute the current game's rules.
const url = 'https://cdn.jsdelivr.net/npm/powergrid-viewer@2.1.5/dist/powergrid-viewer.umd.min.js';
const response = await fetch(url);
assert.ok(response.ok);
const source = await response.text();
const expected = '3ff7fe9cbf4214d191f882c4a132877ebb90f2a962159d19ff7b7c55d2971800';
assert.equal(createHash('sha256').update(source).digest('hex'), expected, 'Pinned legacy viewer changed');
const distance = 'e.scrollHeight-e.scrollTop-e.clientHeight<32';
assert.equal(source.split(distance).length - 1, 3, 'Journal, unread positioning and chat following');
let patched = source.replaceAll(distance, 'e.scrollHeight-e.scrollTop-e.clientHeight<=1');
const refresh = '||void 0===t||t)){if(m){var o=k().find';
assert.equal(patched.split(refresh).length - 1, 1, 'Chat viewport refresh');
patched = patched.replace(
    refresh,
    '||void 0===t||t)){v&&e.scrollTop!==h&&(p=e.scrollHeight-e.scrollTop-e.clientHeight<=1);if(m){var o=k().find'
);
await mkdir(new URL('../dist/', import.meta.url), { recursive: true });
await writeFile(new URL('../dist/powergrid-viewer-2.1.5-scroll.umd.min.js', import.meta.url), patched);
console.log('Backported chat and journal scrolling to the unchanged version-11 viewer');
