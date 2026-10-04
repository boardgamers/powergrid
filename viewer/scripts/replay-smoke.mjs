import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';

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
