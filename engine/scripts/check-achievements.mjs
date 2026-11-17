import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { achievementManifestSchema, achievementResultsSchema } from '@boardgamers/protocol/achievements';
import wrapper from '../dist/wrapper.js';

// Exercise the published protocol's runtime validators against the compiled BGS
// entry point, not local copies of the contract or TypeScript-only assertions.
const manifest = wrapper.achievementDefinitions();
achievementManifestSchema.parse(manifest);
assert.equal(manifest.revision, 3);
assert.equal(manifest.achievements.length, 36);
const previous = JSON.parse(
    readFileSync(new URL('../../docs/releases/achievements-2.0.33.json', import.meta.url), 'utf8')
).achievementManifest;
const artwork = JSON.parse(readFileSync(new URL('../../art/achievements/manifest.json', import.meta.url), 'utf8'));
assert.deepEqual(
    manifest.achievements.map(({ icon, ...definition }) => definition),
    previous.achievements
);
assert.deepEqual(
    manifest.achievements.map(({ id }) => id),
    artwork.assets.map(({ id }) => id)
);
for (const definition of manifest.achievements) {
    assert.deepEqual(definition.icon, { type: 'asset', key: `achievement-${definition.id}` });
}
for (const fixture of ['GermanyRecharged', 'USAOriginal']) {
    const data = JSON.parse(readFileSync(new URL(`../src/fixtures/${fixture}.json`, import.meta.url), 'utf8'));
    const completed = wrapper.replay(data);
    const results = wrapper.achievements(completed);
    achievementResultsSchema(manifest, completed.players.length).parse(results);
    assert.equal(results.length, completed.players.length);
    assert.deepEqual(
        results.map((result) => result.outcome),
        wrapper.rankings(completed).map((rank) => (rank === 1 ? 'win' : 'loss'))
    );
}
console.log('Published protocol 0.11.0 validates compiled achievement manifest and fixture results.');
