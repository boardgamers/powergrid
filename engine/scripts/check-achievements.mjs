import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { achievementManifestSchema, achievementResultsSchema } from '@boardgamers/protocol/achievements';
import wrapper from '../dist/wrapper.js';

// Exercise the published protocol's runtime validators against the compiled BGS
// entry point, not local copies of the contract or TypeScript-only assertions.
const manifest = wrapper.achievementDefinitions();
achievementManifestSchema.parse(manifest);
assert.equal(manifest.revision, 1);
assert.equal(manifest.achievements.length, 16);
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
