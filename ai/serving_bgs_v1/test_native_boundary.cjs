'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const { spawnSync } = require('node:child_process');

test('worker JS stream capture is explicitly NOT native-FD output isolation', () => {
    // Harmless markers only. Native ORT can write the same process descriptors;
    // do not infer suppression of native output from Worker stdout/stderr options.
    const code = `const { Worker } = require('node:worker_threads');
const worker = new Worker("process.stderr.write('js-marker'); require('node:fs').writeSync(2, 'native-fd-marker');", {eval:true,stdout:true,stderr:true});
let captured = ''; worker.stderr.on('data', data => captured += data);
worker.on('exit', code => { if(code) process.exitCode=1; else console.log(JSON.stringify({captured})); });`;
    const result = spawnSync(process.execPath, ['-e', code], { cwd: '/', env: {}, encoding: 'utf8', timeout: 10000 });
    assert.equal(result.status, 0);
    assert.equal(result.stderr, 'native-fd-marker');
    assert.deepEqual(JSON.parse(result.stdout), { captured: 'js-marker' });
});
