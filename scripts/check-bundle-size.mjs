import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { gzipSync } from 'node:zlib';
const entry = await readFile(new URL('../viewer/dist/powergrid-viewer.umd.min.js', import.meta.url));
assert(
    entry.length < 1500000,
    `Viewer grew to ${entry.length} bytes: check eager catalogs and duplicated dependencies`
);
assert(gzipSync(entry).length < 400000, 'Compressed viewer exceeds 400 KB');
console.log(`Viewer: ${entry.length} bytes, ${gzipSync(entry).length} gzip bytes`);
