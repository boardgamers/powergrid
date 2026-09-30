// Diagnostic preload only: return the original decision, and retry capped searches separately.
const fs = require('node:fs');
const search = require('./search.cjs');
const choose = search.choose;
search.choose = function (g, seat, options) {
    const original = choose(g, seat, options);
    if (original.truncated) {
        const extended = choose(g, seat, { ...options, maxSteps: 2400 });
        const record = { seat, options, original, extended, state: g };
        fs.appendFileSync(process.env.SEARCH_DIAGNOSTIC_PATH, JSON.stringify(record) + '\n');
        console.error(
            JSON.stringify({
                diagnostic: 'search_horizon',
                seed: options.seed,
                original_truncated: original.truncated,
                extended_truncated: extended.truncated,
                original_index: original.index,
                extended_index: extended.index,
            })
        );
    }
    return original;
};
