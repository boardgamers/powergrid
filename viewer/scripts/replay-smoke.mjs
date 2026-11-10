import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { createRequire } from 'node:module';

const require = createRequire(import.meta.url);
const engine = require('../../engine/dist/index.js');
const wrapper = require('../../engine/dist/wrapper.js');

// Public replay must count unseen cards as well as recorded draws, including
// plants returned to the bottom before the Step 3 shuffle.
export async function checkReplayDeckCount(page) {
    const fixture = JSON.parse(await readFile(new URL('../../engine/src/fixtures/USAOriginal.json', import.meta.url)));
    for (const to of [200, 400]) {
        // Fresh document: destroyed Vue roots can remain in the sandbox DOM.
        await page.reload();
        const live = wrapper.replay(fixture, { to });
        const state = JSON.parse(JSON.stringify(engine.stripSecret(live)));
        // Mount this historical checkpoint as a standalone snapshot, not a
        // tentative move response (the viewer deliberately ignores those on load).
        state.newTurn = true;
        const indices = state.log
            .map((entry, index) => ({ entry, index }))
            .filter(({ entry }) => entry.type === 'move')
            .map(({ index }) => index);
        await page.evaluate((state) => {
            window.host = window.powergrid.launch('#app');
            host.emit('preferences', { sound: false });
            host.emit('player', {});
            host.emit('state', state);
        }, state);
        const expectCount = async (count) => {
            await page.waitForFunction(
                (count) => document.querySelector('.game')?.__vue__?.G?.cardsLeft === count,
                count
            );
            if (count > 0) {
                await page.waitForFunction(
                    (count) => document.querySelector('[data-deck-count]')?.textContent.trim() === String(count),
                    count
                );
            } else assert.equal(await page.locator('[data-deck-count]').count(), 0);
        };
        await expectCount(live.cardsLeft);
        await page.evaluate(() => host.emit('replay:start'));
        for (const position of [indices.length, indices.length - 1, 1, indices.length - 1, indices.length]) {
            const expected = wrapper.replay(live, { to: indices[position - 1] + 1 }).cardsLeft;
            await page.evaluate((position) => host.emit('replay:to', position), position);
            await expectCount(expected);
        }
        console.log(
            `Replay deck count: round ${live.round}, step ${live.step}, ${live.cardsLeft} cards; latest/back/start/repeated seeks passed`
        );
    }
}

// Public spectator snapshot of MHABKH0215, with player names anonymized.
// Move 331 draws the Step 3 card during Middle East's Step 1 -> Step 2 transition.
export async function checkMiddleEastReplay(page) {
    const state = JSON.parse(await readFile(new URL('../tests/fixtures/middle-east-replay.json', import.meta.url)));
    const end = state.log.filter((item) => item.type === 'move').length;
    await page.evaluate((state) => {
        window.host = window.powergrid.launch('#app');
        window.replayInfo = null;
        window.replayMoves = [];
        window.replayReady = false;
        window.replaySource = state;
        window.replaySourceBefore = JSON.stringify(state);
        host.on('ready', () => {
            window.replayReady = true;
        });
        host.on('replay:info', (info) => {
            window.replayInfo = info;
        });
        host.on('move', (move) => {
            window.replayMoves.push(move);
        });
        host.emit('preferences', { sound: false, locale: 'en' });
        host.emit('player', {});
        host.emit('state', state);
    }, state);
    await page.waitForFunction(() => window.replayReady);
    await page.evaluate(() => host.emit('replay:start'));
    assert.deepEqual(await page.evaluate(() => replayInfo), { start: 1, current: end, end });

    // Exercise the bundled viewer handler at every position, including sealed
    // bids which are temporarily stored in hiddenLog during reconstruction.
    const failures = await page.evaluate((end) => {
        const failures = [];
        for (let current = 1; current <= end; current++) {
            host.emit('replay:to', current);
            if (replayInfo.current !== current || replayInfo.end !== end) failures.push(current);
        }
        return failures;
    }, end);
    assert.deepEqual(failures, [], 'every replay position is reachable');

    // Scrub across the boundary more than once: no recorded draw may be consumed
    // from the saved source state by an earlier reconstruction.
    for (const [current, round, step] of [
        [330, 6, 1],
        [331, 7, 2],
        [end, 9, 2],
        [1, 1, 1],
        [331, 7, 2],
        [end, 9, 2],
    ]) {
        await page.evaluate((current) => host.emit('replay:to', current), current);
        assert.deepEqual(await page.evaluate(() => replayInfo), { start: 1, current, end });
        await page.waitForFunction(
            ({ round, step }) => {
                const text = document.querySelector('#scene')?.textContent;
                return text?.includes(`Round: ${round}`) && text.includes(`Step: ${step}`);
            },
            { round, step }
        );
    }
    assert.deepEqual(await page.evaluate(() => replayMoves), [], 'replay never submits game moves');
    assert.equal(await page.evaluate(() => JSON.stringify(replaySource) === replaySourceBefore), true);
    console.log(`powergrid Middle East replay: all ${end} positions and repeated Step 2 crossings passed`);
}
