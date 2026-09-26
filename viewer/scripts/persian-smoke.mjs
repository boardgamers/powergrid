import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { chromium } from 'playwright';
import { previewServer } from './tutorial-preview.mjs';

const require = createRequire(import.meta.url);
const engine = require('../../engine/dist/index.js');
const server = previewServer();
await new Promise((resolve) => server.listen(0, '127.0.0.1', resolve));
const browser = await chromium.launch({
    executablePath: process.env.CHROMIUM_EXECUTABLE || process.env.CHROMIUM_PATH,
});
const errors = [];
try {
    for (const width of [390, 1400]) {
        const page = await browser.newPage({ viewport: { width, height: 900 }, reducedMotion: 'reduce' });
        page.on('pageerror', (error) => errors.push(error.message));
        await page.goto(`http://127.0.0.1:${server.address().port}/`);
        await page.locator('#scene').waitFor();
        for (const chapter of ['auctions', 'resources', 'network', 'income', 'upgrades', 'steps', 'final-round']) {
            await page.evaluate(async (chapter) => {
                await powergrid.launchTutorial('#app', {
                    chapter,
                    locale: 'fa-IR',
                    onProgress: (value) => (window.progress = value),
                });
            }, chapter);
            await page.getByRole('button', { name: 'بازگشت به آغاز', exact: true }).waitFor();
            const prose = await page.locator('.bgs-tutorial-body').innerText();
            assert.match(prose, /[\u0600-\u06ff]/u, `${chapter}: Persian explanation`);
            assert.doesNotMatch(prose, /Click |You |Your |Choose |Build |power plants/);
            assert.equal(
                await page.locator('.bgs-tutorial-guide').evaluate((el) => getComputedStyle(el).direction),
                'rtl'
            );
            assert.equal(await page.locator('#scene').evaluate((el) => getComputedStyle(el).direction), 'ltr');
            assert.ok(
                await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1),
                `${chapter}: no horizontal overflow at ${width}px`
            );
        }
        // Exercise an actual tutorial decision under translated accessible labels.
        await page.evaluate(async () => {
            localStorage.clear();
            await powergrid.launchTutorial('#app', { chapter: 'resources', locale: 'fa-IR' });
        });
        await page.getByRole('button', { name: 'ادامه', exact: true }).click();
        const coal = () => page.locator('[data-tutorial="resources"] g.canClick').first();
        await coal().click();
        await page.waitForFunction(() =>
            document.querySelector('.bgs-tutorial-body')?.textContent.includes('زغال‌سنگ دوم')
        );
        await coal().click();
        await page.getByRole('button', { name: '$3', exact: true }).click();
        await page.waitForFunction(() =>
            document.querySelector('.bgs-tutorial-feedback')?.textContent.includes('درست است!')
        );

        const state = JSON.parse(
            JSON.stringify(engine.setup(3, { map: 'Germany', variant: 'recharged', showMoney: true }, '17'))
        );
        state.players.forEach((player, i) => {
            player.name = ['Power Plant', 'Ada', 'Bob'][i];
        });
        await page.evaluate((state) => {
            window.host = powergrid.launch('#app');
            host.emit('preferences', { locale: 'en', sound: false });
            host.emit('player', { index: 0 });
            host.emit('state', state);
        }, state);
        await page.waitForFunction(() =>
            document.querySelector('.modal-body')?.textContent.includes('One player per city')
        );
        const geometry = () =>
            page
                .locator('[data-tutorial="map"]')
                .evaluate((el) =>
                    [...el.querySelectorAll('path,circle,rect')].map((node) =>
                        ['id', 'd', 'cx', 'cy', 'x', 'y', 'width', 'height', 'transform'].map((attr) =>
                            node.getAttribute(attr)
                        )
                    )
                );
        const before = await geometry();
        await page.evaluate(() => host.emit('preferences', { locale: 'fa-IR', sound: false }));
        await page.waitForFunction(() =>
            document.querySelector('.modal-body')?.textContent.includes('یک بازیکن در هر شهر')
        );
        assert.equal(
            await page
                .locator('.modal-content')
                .first()
                .evaluate((el) => getComputedStyle(el).direction),
            'rtl'
        );
        assert.equal(await page.locator('#scene').evaluate((el) => getComputedStyle(el).direction), 'ltr');
        assert.deepEqual(await geometry(), before, 'language changes preserve every board geometry attribute');
        assert.ok(
            await page.locator('[data-bgs-player]').filter({ hasText: 'Power Plant' }).count(),
            'player name is unchanged'
        );
        await page.evaluate(() => host.emit('preferences', { locale: 'en', sound: false }));
        await page.waitForFunction(() =>
            document.querySelector('.modal-body')?.textContent.includes('One player per city')
        );
        assert.equal(
            await page
                .locator('.modal-content')
                .first()
                .evaluate((el) => getComputedStyle(el).direction),
            'ltr'
        );
        assert.deepEqual(await geometry(), before);
        await page.close();
        console.log(
            `Persian tutorials, interactive fuel buying, locale switching and board geometry: ${width}px passed`
        );
    }
    assert.deepEqual(errors, []);
} finally {
    await browser.close();
    await new Promise((resolve) => server.close(resolve));
}
