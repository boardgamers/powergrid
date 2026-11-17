// Build the viewer library first. Exercise real DOM localization and glyph bounds.
import assert from 'node:assert/strict';
import { readFile, readdir } from 'node:fs/promises';
import { chromium } from 'playwright';
import { auctionPreviewServer } from './auction-preview.mjs';
const server = auctionPreviewServer();
await new Promise((resolve) => server.listen(0, '127.0.0.1', resolve));
const base = `http://127.0.0.1:${server.address().port}`;
const browser = await chromium.launch({ executablePath: process.env.CHROMIUM_EXECUTABLE });
const directory = new URL('../src/localization/', import.meta.url);
let smallest = { font: Infinity };
let checks = 0;
try {
    for (const width of [390, 1400]) {
        const page = await browser.newPage({ viewport: { width, height: 900 } });
        const errors = [];
        page.on('pageerror', (error) => errors.push(error.message));
        await page.goto(`${base}/?mode=fuel-hidden`);
        await page.locator('[data-auto-pass-setting]').waitFor();
        for (const file of (await readdir(directory)).filter((name) => name.endsWith('.json'))) {
            const locale = file.slice(0, -5);
            const catalog = JSON.parse(await readFile(new URL(file, directory), 'utf8'));
            await page.evaluate((locale) => host.emit('preferences', { locale, sound: false }), locale);
            for (const [mode, phase] of [
                ['hidden', 'auction'],
                ['fuel-hidden', 'resources'],
                ['city-hidden', 'building'],
                ['fuel-hidden', 'resources'],
            ]) {
                const data = await (await fetch(`${base}/state?mode=${mode}`)).json();
                await page.evaluate((data) => {
                    host.emit('settings', data.settings);
                    host.emit('state', data.state);
                }, data);
                const expected = catalog[`Auto-pass if unaffordable (${phase})`];
                await page.waitForFunction((expected) => {
                    const control = document.querySelector('[data-auto-pass-setting]');
                    return (
                        control?.getAttribute('aria-label') === expected &&
                        control.querySelector('[data-action-label]')?.textContent === expected
                    );
                }, expected);
                await page.waitForTimeout(100);
                const bounds = await page.locator('[data-auto-pass-setting]').evaluate((control) => {
                    const label = control.querySelector('[data-action-label]');
                    const box = label.getBBox();
                    const hit = control.querySelector('.auto-pass-hit').getBoundingClientRect();
                    const rendered = label.getBoundingClientRect();
                    const checkbox = control.querySelector('rect[x="10"]').getBoundingClientRect();
                    return {
                        font: Number(label.getAttribute('font-size')),
                        x: box.x + 29,
                        y: box.y,
                        right: box.x + box.width + 29,
                        bottom: box.y + box.height,
                        inside:
                            rendered.left >= hit.left &&
                            rendered.right <= hit.right + 0.1 &&
                            rendered.top >= hit.top &&
                            rendered.bottom <= hit.bottom + 0.1,
                        gap: rendered.left - checkbox.right,
                    };
                });
                assert.ok(bounds.inside && bounds.gap > 0, `${locale}/${width}/${phase}: ${JSON.stringify(bounds)}`);
                assert.ok(
                    bounds.x >= 35.8 && bounds.right <= 342.2 && bounds.y >= 0 && bounds.bottom <= 36,
                    `reserved 36px row; checkbox and right padding: ${locale}/${phase} ${JSON.stringify(bounds)}`
                );
                if (bounds.font < smallest.font) smallest = { ...bounds, locale, width, phase };
                checks++;
            }
        }
        assert.deepEqual(errors, []);
        await page.close();
    }
    console.log(
        `Auto-pass labels: ${checks} phase/locale/viewport checks passed (17 locales, 390/1400px, live phase and locale switching). Smallest: ${JSON.stringify(
            smallest
        )}`
    );
} finally {
    await browser.close();
    await new Promise((resolve) => server.close(resolve));
}
