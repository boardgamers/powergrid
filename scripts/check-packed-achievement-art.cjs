// Usage: node scripts/check-packed-achievement-art.cjs /absolute/installed/node_modules
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const modules = path.resolve(process.argv[2]);
const wrapper = require(path.join(modules, 'powergrid-engine/dist/wrapper.js'));
const { achievementManifestSchema, achievementResultsSchema } = require(require.resolve('@boardgamers/protocol/achievements', { paths: [modules] }));
const old = require('../docs/releases/achievements-2.0.33.json').achievementManifest;
const art = require('../art/achievements/manifest.json');
const manifest = wrapper.achievementDefinitions();
assert.equal(require(path.join(modules, 'powergrid-engine/package.json')).version, '2.0.34');
achievementManifestSchema.parse(manifest);
assert.equal(manifest.revision, 3);
assert.deepEqual(manifest.achievements.map(({ icon, ...rest }) => rest), old.achievements);
assert.deepEqual(manifest.achievements.map(({ icon }) => icon), art.assets.map(({ key }) => ({ type: 'asset', key })));
for (const fixture of ['GermanyRecharged', 'USAOriginal']) {
    const data = JSON.parse(fs.readFileSync(path.join(__dirname, '../engine/src/fixtures', fixture + '.json')));
    const completed = wrapper.replay(data);
    const results = wrapper.achievements(completed);
    achievementResultsSchema(manifest, completed.players.length).parse(results);
    assert.equal(results.length, completed.players.length);
    assert.deepEqual(results.map((r) => r.outcome), wrapper.rankings(completed).map((rank) => rank === 1 ? 'win' : 'loss'));
}
console.log('Exact installed 2.0.34 tarball: 36 stable refs, revision 3, published schema and two replay fixtures pass.');
