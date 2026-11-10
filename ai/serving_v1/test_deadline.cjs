'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const { performance } = require('node:perf_hooks');
const { setTimeout: sleep } = require('node:timers/promises');
const { scheduleDeadline } = require('./deadline.cjs');
test('fractional deadlines never expire early and cancellation prevents expiration', async () => {
    for (let i = 0; i < 20; i++) {
        const deadline = performance.now() + 2.25;
        const at = await new Promise((resolve) => scheduleDeadline(deadline, () => resolve(performance.now())));
        assert(at >= deadline);
    }
    let expired = false;
    scheduleDeadline(performance.now() + 2, () => {
        expired = true;
    }).cancel();
    await sleep(10);
    assert.equal(expired, false);
});
