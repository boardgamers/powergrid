// Run after packaging: node viewer/scripts/action-labels-smoke.mjs
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { chromium } from 'playwright';
import { auctionPreviewServer } from './auction-preview.mjs';

const server = auctionPreviewServer();
await new Promise((resolve) => server.listen(0, '127.0.0.1', resolve));
const origin = `http://127.0.0.1:${server.address().port}`;
const locales = [
    'en',
    'de',
    'fr',
    'pl',
    'ro',
    'el',
    'hi',
    'ru',
    'da',
    'pt-BR',
    'ko',
    'zh-TW',
    'zh-CN',
    'vi',
    'it',
    'nl',
    'fa',
];
const browser = await chromium.launch({ executablePath: process.env.CHROMIUM_EXECUTABLE });
const errors = [];
async function fits(page) {
    await page.waitForFunction(() =>
        [...document.querySelectorAll('[data-action-label]')].every((label) => {
            const border = label.parentElement.querySelector('.turn-action-border');
            const b = label.getBBox();
            return (
                b.x >= 7 &&
                b.x + b.width <= Number(border.getAttribute('width')) - 7 &&
                b.y >= 1 &&
                b.y + b.height <= Number(border.getAttribute('height')) - 1
            );
        })
    );
    const sizes = await page
        .locator('[data-action-label]')
        .evaluateAll((labels) => labels.map((label) => Number(label.getAttribute('font-size'))));
    assert(
        sizes.every((size) => size >= 10),
        `complete labels remain readable: ${sizes}`
    );
}
try {
    for (const width of [390, 1400]) {
        const page = await browser.newPage({ viewport: { width, height: 900 } });
        page.on('pageerror', (error) => errors.push(error.message));
        await page.goto(`${origin}/?mode=your-turn`);
        const toggle = page.locator('[data-board-control="text-actions"]');
        await toggle.waitFor();
        await page.evaluate(() => {
            window.beforeTextMode = JSON.stringify(document.querySelector('.game').__vue__.G);
            window.textModeMoves = [];
            window.host.on('move', (move) => window.textModeMoves.push(move));
        });
        const geometry = await page.locator('[data-board-control="pass"]').boundingBox();
        await toggle.focus();
        await page.keyboard.press('Enter');
        await page.waitForFunction(() => document.querySelector('[data-action-label]'));
        assert.equal(await toggle.getAttribute('aria-pressed'), 'true');
        assert.equal(await page.locator('[data-phase-icon]').count(), 0);
        assert.equal(
            await page.locator('[data-board-control="pass"] [data-action-label]').textContent(),
            'Skip auction'
        );
        await fits(page);
        // All language changes happen through the host, including back to English.
        for (const locale of [...locales, 'en']) {
            const catalog = JSON.parse(await readFile(new URL(`../src/localization/${locale}.json`, import.meta.url)));
            await page.evaluate((locale) => window.host.emit('preferences', { locale }), locale);
            await page.waitForFunction(
                (expected) =>
                    document.querySelector('[data-board-control="pass"] [data-action-label]').textContent === expected,
                catalog['Skip auction']
            );
            await page.waitForFunction(
                (expected) =>
                    document.querySelector('[data-board-control="undo"] [data-action-label]').textContent === expected,
                catalog['Undo last move']
            );
            await fits(page);
        }
        // The enabled map toggle uses the same light surface treatment and dark pictogram.
        const map = page.locator('[data-board-control="unselected-regions"]');
        await map.hover();
        assert.equal(
            await map.locator('.option-background').evaluate((e) => getComputedStyle(e).fill),
            'rgb(192, 192, 192)'
        );
        assert.equal(
            await map
                .locator(':scope > g')
                .first()
                .evaluate((e) => getComputedStyle(e).stroke),
            'rgb(0, 0, 0)'
        );
        await toggle.focus();
        await page.keyboard.press('Space');
        await page.waitForFunction(() => !document.querySelector('[data-action-label]'));
        assert.equal(await toggle.getAttribute('aria-pressed'), 'false');
        const after = await page.locator('[data-board-control="pass"]').boundingBox();
        for (const key of ['x', 'y', 'width', 'height'])
            assert(Math.abs(geometry[key] - after[key]) < 1, `stable ${key}`);
        assert(
            await page.evaluate(
                () => window.beforeTextMode === JSON.stringify(document.querySelector('.game').__vue__.G)
            )
        );
        assert.deepEqual(await page.evaluate(() => window.textModeMoves), []);
        // Host pushes also select presentation, independent of clicking the toolbar.
        await page.evaluate(() => window.host.emit('preferences', { textActions: true }));
        await page.locator('[data-action-label]').first().waitFor();
        await page.evaluate(() => window.host.emit('undo:available', true));
        await page.locator('[data-board-control="undo-move"] [data-action-label]').waitFor();
        assert.equal(
            await page.locator('[data-board-control="undo-move"] [data-action-label]').textContent(),
            'Undo my move'
        );
        await fits(page);
        await page.close();
        console.log(
            `${width}px: Text/Icons, keyboard, host preference, saved-move undo, map hover and all 17 languages passed`
        );
    }
    for (const [mode, move, label] of [
        ['resources', 'BuyResource', 'Finish buying'],
        ['building', 'Build', 'Finish building'],
        ['powering', 'UsePowerPlant', 'Finish powering'],
    ]) {
        const page = await browser.newPage();
        page.on('pageerror', (error) => errors.push(error.message));
        await page.goto(`${origin}/?mode=${mode}&text=1`);
        const actionLabel = page.locator('[data-board-control="pass"] [data-action-label]');
        await actionLabel.waitFor();
        assert.equal(await actionLabel.textContent(), label);
        const echo = page.waitForResponse((r) => r.url().includes('/move?'));
        await page.evaluate((move) => {
            const game = document.querySelector('.game').__vue__;
            game.sendMove({ name: move, data: game.G.players[0].availableMoves[move][0] });
        }, move);
        await echo;
        await page.locator('[data-board-control="undo"].enabled').waitFor();
        await page.locator('[data-board-control="undo"]').click();
        await page.locator('[data-board-control="undo"][aria-disabled="true"]').waitFor();
        assert.equal(await actionLabel.textContent(), label);
        await fits(page);
        await page.close();
        console.log(`${mode}: full action wording and working text-mode Undo passed`);
    }
    assert.deepEqual(errors, []);
} finally {
    await browser.close();
    await new Promise((resolve) => server.close(resolve));
}
