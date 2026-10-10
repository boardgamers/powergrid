const fs = require('node:fs'), readline = require('node:readline'), assert = require('node:assert/strict'),
    full = require('./features-v4_1.cjs'), control = require('./features-v4_1_control.cjs');
(async () => {
    const [input, output] = process.argv.slice(2); let positions = 0, nonzeroExtraStates = 0;
    for await (const line of readline.createInterface({input: fs.createReadStream(input)})) {
        const {request} = JSON.parse(line), expected = full.encode(request.state, request.player),
            actual = control.encode(request.state, request.player);
        assert.equal(actual.featureRevision, '4.1-five-plants-zero-inputs');
        assert.equal(actual.state.length, 1215);
        assert.ok(actual.actions.every(row => row.length === 100));
        assert.deepEqual(actual.state.slice(0, 1149), expected.state.slice(0, 1149));
        assert.deepEqual(actual.actions.map(row => row.slice(0, 98)), expected.actions.map(row => row.slice(0, 98)));
        assert.deepEqual(actual.state.slice(1149), Array(66).fill(0));
        assert.ok(actual.actions.every(row => row[98] === 0 && row[99] === 0));
        for (const key of ['moves', 'teacher', 'prior', 'seat', 'playerMask', 'playerOrder'])
            assert.deepEqual(actual[key], expected[key]);
        nonzeroExtraStates += +expected.state.slice(1149).some(value => value !== 0);
        positions++;
    }
    assert.equal(positions, 2553); assert.equal(nonzeroExtraStates, 8);
    const result = {positions, nonzeroExtraStates, oldInputsIdentical: true, newInputsAlwaysZeroInControl: true};
    fs.writeFileSync(output, JSON.stringify(result, null, 2) + '\n'); console.log(JSON.stringify(result));
})().catch(error => {console.error(error);process.exitCode=1;});
