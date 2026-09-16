import assert from 'node:assert/strict';
import { chromium } from 'playwright';
import { previewServer } from './tutorial-preview.mjs';

const server = previewServer();
await new Promise((resolve) => server.listen(0, '127.0.0.1', resolve));
const url = `http://127.0.0.1:${server.address().port}`;
const browser = await chromium.launch({
    headless: true,
    ...(process.env.CHROMIUM_PATH ? { executablePath: process.env.CHROMIUM_PATH } : {}),
});
const errors = [];
try {
    for (const width of [1280, 390]) {
        const context = await browser.newContext({ viewport: { width, height: 900 }, reducedMotion: 'reduce' });
        const page = await context.newPage();
        page.on('pageerror', (error) => errors.push(String(error)));
        page.on('console', (message) => {
            if (message.type() === 'error') errors.push(message.text());
        });
        async function ready() {
            await page.waitForFunction(
                () => document.querySelector('button[aria-label="Back to start"]')?.disabled === false
            );
        }
        async function click(locator) {
            await locator.click();
            await ready();
        }
        const button = (name) => page.getByRole('button', { name, exact: true });
        const card = (area, number) =>
            page
                .locator(`[data-tutorial="${area}"] g.canClick`)
                .filter({ has: page.locator('text').filter({ hasText: new RegExp(`^${number}$`) }) })
                .first();
        const city = (name) =>
            page
                .locator('circle.canClick[pointer-events="all"]')
                .filter({ has: page.locator('title').filter({ hasText: new RegExp(`^${name}`) }) });
        const done = () => page.locator('[data-tutorial="turn"] g.enabled').filter({ hasText: 'Done' }).first();
        const fuel = () => page.locator('[data-tutorial="resources"] g.canClick').first();
        async function start(chapter) {
            await page.goto(`${url}/?chapter=${chapter}`);
            await page.locator('#scene').waitFor();
            await ready();
            const rect = await page.locator('#scene').boundingBox();
            assert.ok(rect.width > 300 && rect.height > 100, 'the actual game board is rendered');
            assert.ok(
                await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1),
                'no horizontal overflow'
            );
        }
        async function completed(chapter) {
            await page.waitForFunction(() => window.progress?.completed === true);
            await page.reload();
            await page.waitForFunction(() => window.progress?.completed === true);
            assert.equal(await button('Continue').count(), 0, 'no extra Continue at completion');
            if (chapter !== 'final-round') assert.equal(await button('Next chapter').isVisible(), true);
            await click(button('Previous step'));
            assert.equal(await page.evaluate(() => window.progress.completed), false);
        }
        await start('auctions');
        await click(button('Continue'));
        await click(card('plants', 4));
        await click(page.locator('.calculator g').filter({ hasText: 'OK' }));
        await click(page.locator('.calculator g').filter({ hasText: 'OK' }));
        await click(button('Watch the remaining auctions'));
        await completed('auctions');

        await start('resources');
        await click(button('Continue'));
        await click(fuel());
        await click(fuel());
        await click(button('$2'));
        assert.equal(await page.getByRole('alert').isVisible(), true);
        await click(button('$3'));
        assert.match(await page.locator('.bgs-tutorial-feedback').innerText(), /Correct!/);
        await click(fuel());
        await click(fuel());
        await click(done());
        await completed('resources');

        await start('network');
        await click(city('Essen'));
        await click(city('Duisburg'));
        await click(button('$12'));
        await click(city('Dusseldorf'));
        await click(done());
        await completed('network');

        await start('income');
        await click(card('players', 4));
        await click(card('players', 13));
        await page.waitForTimeout(1100); // The ordinary viewer briefly locks Done after powering.
        await click(done());
        await click(button('Watch income and market upkeep'));
        await click(button('You'));
        await completed('income');

        await start('upgrades');
        await click(card('plants', 25));
        await click(page.getByRole('button').filter({ hasText: /25/ }));
        await click(card('players', 4));
        await completed('upgrades');

        await start('steps');
        await click(city('Kassel'));
        await click(done());
        await click(button('No'));
        await click(button('Finish the round'));
        await click(button('All 6'));
        await completed('steps');

        await start('final-round');
        await click(button('Continue'));
        await click(page.locator('[data-tutorial="map"] circle.canClick[pointer-events="all"]').first());
        await click(button('Ada'));
        await click(done());
        // The normal game's score overlay may be open; it must not prevent completion.
        await page.waitForFunction(() => window.progress?.completed === true);
        assert.match(await page.locator('.bgs-tutorial-body').innerText(), /Ada wins with 16/);
        await page.screenshot({ path: `/tmp/powergrid-tutorial-${width}.png`, fullPage: true });
        assert.deepEqual(errors, []);
        console.log(`Seven chapters completed through the real viewer at ${width}px`);
        await context.close();
    }
} finally {
    await browser.close();
    await new Promise((resolve) => server.close(resolve));
}
