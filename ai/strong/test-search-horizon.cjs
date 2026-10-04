const test = require('node:test'),
    assert = require('node:assert/strict');
const search = require('./search.cjs');
const fixture = require('./fixtures/search-horizon-six-player.json');
test('six-player search completes the continuation that exceeded the old horizon', () => {
    const old = search.choose(fixture.state, fixture.seat, { ...fixture.options, maxSteps: 1200 });
    assert.deepEqual(old, fixture.original);
    assert.equal(old.truncated, 1);
    const current = search.choose(fixture.state, fixture.seat, fixture.options);
    assert.deepEqual(current, fixture.extended);
    assert.equal(current.truncated, 0);
});
