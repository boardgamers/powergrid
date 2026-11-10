'use strict';
// Verify the extracted package under target Node against the retained offline PyTorch reference.
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const { createHash } = require('node:crypto');
const hash = (b) => createHash('sha256').update(b).digest('hex');
async function parity({ packageDirectory, fixturesFile, referenceFile }) {
    assert.equal(process.version, 'v24.22.1');
    const root = path.resolve(packageDirectory),
        rawFixtures = fs.readFileSync(fixturesFile),
        rawReference = fs.readFileSync(referenceFile);
    const fixtures = JSON.parse(rawFixtures),
        reference = JSON.parse(rawReference);
    assert.equal(fixtures.schema, 'pg-serving-engineering-fixtures-v1');
    assert.equal(reference.schema, 'pg-replica-pytorch-reference-v1');
    assert.equal(reference.fixturesInputHashMode, 'raw-file-bytes');
    assert.equal(reference.fixturesInputSha256, hash(rawFixtures));
    const manifest = JSON.parse(fs.readFileSync(path.join(root, 'runtime-manifest.json')));
    const { OnnxPolicy } = require(path.join(root, 'ai/serving_bgs_v1/onnx.cjs'));
    const policy = await OnnxPolicy.create({
        replica: manifest.replica,
        modelDirectory: path.join(root, 'models'),
        exportManifestSha256: manifest.exportManifestSha256,
    });
    const report = {
        schema: 'pg-bgs-target-parity-v1',
        node: process.version,
        replica: manifest.replica,
        fixtureSha256: hash(rawFixtures),
        referenceSha256: hash(rawReference),
        runtimeManifestSha256: hash(fs.readFileSync(path.join(root, 'runtime-manifest.json'))),
        observations: fixtures.fixtures.length,
        exactIndices: 0,
        maxLogitError: 0,
        maxValueError: 0,
        tolerance: { absolute: 2e-5, relative: 1e-6 },
        strengthEvaluation: false,
    };
    try {
        assert.equal(fixtures.fixtures.length, reference.fixtures.length);
        for (const [i, fixture] of fixtures.fixtures.entries()) {
            const gold = reference.fixtures[i];
            assert.equal(gold.id, fixture.id);
            const expected = gold.replicas[manifest.replica],
                result = await policy.evaluate(fixture.observation);
            assert.equal(result.index, expected.index, fixture.id);
            report.exactIndices++;
            assert.equal(result.logits.length, expected.logits.length);
            for (const [i, value] of result.logits.entries()) {
                const error = Math.abs(value - expected.logits[i]);
                assert(error <= 2e-5 + 1e-6 * Math.abs(expected.logits[i]), fixture.id);
                report.maxLogitError = Math.max(report.maxLogitError, error);
            }
            const valueError = Math.abs(result.value - expected.value);
            assert(valueError <= 2e-5 + 1e-6 * Math.abs(expected.value), fixture.id);
            report.maxValueError = Math.max(report.maxValueError, valueError);
        }
    } finally {
        await policy.close();
    }
    return report;
}
module.exports = { parity };
if (require.main === module) {
    const args = process.argv.slice(2);
    assert(
        args.length === 8 &&
            args[0] === '--package' &&
            args[2] === '--fixtures' &&
            args[4] === '--reference' &&
            args[6] === '--output'
    );
    assert(!fs.existsSync(args[7]));
    parity({ packageDirectory: args[1], fixturesFile: args[3], referenceFile: args[5] })
        .then((report) => {
            fs.writeFileSync(args[7], JSON.stringify(report, null, 4) + '\n', { flag: 'wx' });
            console.log(JSON.stringify(report));
        })
        .catch(() => {
            console.error('target-parity-failed');
            process.exitCode = 1;
        });
}
