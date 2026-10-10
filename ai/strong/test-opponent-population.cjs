const test = require('node:test');
const assert = require('node:assert/strict');
const { POPULATION, populationRoles, isNeuralRole } = require('./opponent-population.cjs');

test('two-player arms have identical opponents; larger tables differ only in opponent assignment', () => {
    let heterogeneousTables = 0;
    for (let id = 0; id < 600; id++) {
        for (let n = 2; n <= 6; n++) {
            const seat = id % n;
            const a = populationRoles('population_homogeneous', n, seat, 'population-test', id);
            const b = populationRoles('population_heterogeneous', n, seat, 'population-test', id);
            assert.equal(a[seat], 'learner');
            assert.equal(b[seat], 'learner');
            assert.equal(a[(seat + 1) % n], b[(seat + 1) % n]);
            assert.equal(a.every(x => x === 'learner'), b.every(x => x === 'learner'));
            if (n === 2) assert.deepEqual(a, b);
            else if (new Set(b.filter(x => x !== 'learner')).size > 1) heterogeneousTables++;
            assert.ok(new Set(a.filter(x => x !== 'learner')).size <= 1);
        }
    }
    assert.ok(heterogeneousTables > 1000);
});

test('population retains every family and self-play without defaulting unknown roles to a bot', () => {
    const seen = new Set();
    let selfplay = 0;
    for (let id = 0; id < 2000; id++) {
        const roles = populationRoles('population_heterogeneous', 6, 0, 'coverage', id);
        roles.forEach(x => seen.add(x));
        selfplay += roles.every(x => x === 'learner');
    }
    assert.deepEqual([...seen].sort(), ['learner', ...POPULATION].sort());
    assert.ok(selfplay > 190 && selfplay < 310);
    assert.equal(isNeuralRole('frozen0'), true);
    assert.equal(isNeuralRole('snapshot2'), true);
    assert.equal(isNeuralRole('frozen3'), false);
    assert.throws(() => populationRoles('bad', 3, 0, 'x', 0), /Unknown population mode/);
});
