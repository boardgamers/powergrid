'use strict';
const { performance } = require('node:perf_hooks');
// Node truncates fractional timer delays. Never treat an early callback as expiry.
function scheduleDeadline(deadline, expired) {
    let timer,
        cancelled = false;
    function wake() {
        if (cancelled) return;
        const remaining = deadline - performance.now();
        if (remaining > 0) timer = setTimeout(wake, Math.ceil(remaining));
        else expired();
    }
    timer = setTimeout(wake, Math.max(1, Math.ceil(deadline - performance.now())));
    return {
        cancel() {
            cancelled = true;
            clearTimeout(timer);
        },
    };
}
module.exports = { scheduleDeadline };
