const test = require('node:test');
const assert = require('node:assert/strict');
const search = require('./search.cjs');
const fixture = require('./fixtures/search-horizon-six-player.json');

test('optional paired outcomes preserve decisions and distinguish capped continuations', () => {
    for (const maxSteps of [1200, 2400]) {
        const options = { ...fixture.options, maxSteps };
        const before = JSON.stringify(fixture.state);
        const plain = search.choose(fixture.state, fixture.seat, options);
        const detailed = search.choose(fixture.state, fixture.seat, { ...options, includeSamples: true });
        const { sampleOutcomes, ...rest } = detailed;
        assert.deepEqual(rest, plain);
        assert.equal(JSON.stringify(fixture.state), before);
        let capped = 0, count = 0;
        for (const [index, values] of Object.entries(sampleOutcomes)) {
            assert.equal(values.length, options.samples);
            assert.equal(values.filter((v) => v !== null).reduce((a, b) => a + b, 0), plain.values[index]);
            capped += values.filter((v) => v === null).length;
            count += values.length;
        }
        assert.equal(capped, plain.truncated);
        assert.equal(count, plain.evaluations);
        assert.equal(capped, maxSteps === 1200 ? 1 : 0);
    }
});

test('fixed continuation policies share scenarios and reproduce mixed-policy samples', () => {
    const options = { ...fixture.options, samples: 2, maxSteps: 2400, includeSamples: true };
    const mixed = search.choose(fixture.state, fixture.seat, options);
    const economic = search.choose(fixture.state, fixture.seat, { ...options, continuation: 'economic' });
    const heuristic = search.choose(fixture.state, fixture.seat, { ...options, continuation: 'heuristic' });
    for (const k of Object.keys(mixed.sampleOutcomes)) {
        assert.equal(mixed.sampleOutcomes[k][0], economic.sampleOutcomes[k][0]);
        assert.equal(mixed.sampleOutcomes[k][1], heuristic.sampleOutcomes[k][1]);
    }
    assert.throws(() => search.choose(fixture.state, fixture.seat, { continuation: 'unknown' }), /Invalid continuation/);
});
