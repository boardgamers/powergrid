// Build engine and viewer first; exercises the same wrapper-backed interactive demo.
import assert from 'node:assert/strict';
import { chromium } from 'playwright';
import { auctionPreviewServer } from './auction-preview.mjs';
const server = auctionPreviewServer();
await new Promise((resolve) => server.listen(0, '127.0.0.1', resolve));
const base = `http://127.0.0.1:${server.address().port}`;
const browser = await chromium.launch({ executablePath: process.env.CHROMIUM_EXECUTABLE });
try {
    const page = await browser.newPage();
    const errors = [];
    page.on('pageerror', (error) => errors.push(error.message));
    for (const phase of ['fuel', 'city']) {
        const setting = phase === 'fuel' ? 'autoPassResources' : 'autoPassBuilding';
        for (const [money, optIn] of [
            ['hidden', false],
            ['hidden', true],
            ['public', false],
        ]) {
            const mode = `${phase}-${money}`;
            await fetch(`${base}/reset?mode=${mode}`, { method: 'POST', body: '{}' });
            await page.goto(`${base}/?mode=${mode}`);
            const control = page.locator(`[data-auto-pass-setting="${setting}"]`);
            await control.waitFor();
            assert.equal(await page.locator('[data-auto-pass-setting]').count(), 1, 'own-player only');
            assert.match(
                await control.locator('title').textContent(),
                money === 'public' ? /Always on/ : /reveal hidden money/
            );
            assert.equal(await control.getAttribute('role'), money === 'public' ? 'note' : 'checkbox');
            if (optIn) {
                const saved = page.waitForResponse((r) => r.url().includes('/setting'));
                await control.focus();
                await page.keyboard.press('Space');
                const data = await (await saved).json();
                assert.equal(data.settings[setting], true);
                await page.waitForFunction(
                    (s) =>
                        document.querySelector(`[data-auto-pass-setting="${s}"]`)?.getAttribute('aria-checked') ===
                        'true',
                    setting
                );
            }
            const moved = page.waitForResponse((r) => r.url().includes('/opponent'));
            await page.locator('#opponent').click();
            const data = await (await moved).json();
            assert.equal(data.error, undefined);
            assert.equal(
                data.state.currentPlayers.includes(0),
                money === 'hidden' && !optIn,
                `${mode} opt-in ${optIn}`
            );
            assert.equal(await page.locator('#error').textContent(), '');
        }
    }
    for (const money of ['hidden', 'public']) {
        const mode = `fuel-${money}-impossible`;
        await fetch(`${base}/reset?mode=${mode}`, { method: 'POST', body: '{}' });
        await page.goto(`${base}/?mode=${mode}`);
        await page.locator('[data-auto-pass-setting]').waitFor();
        const moved = page.waitForResponse((r) => r.url().includes('/opponent'));
        await page.locator('#opponent').click();
        const data = await (await moved).json();
        assert.equal(data.error, undefined);
        assert.equal(data.state.currentPlayers.includes(0), false, 'public impossibility skips without opt-in');
        assert.equal(data.settings.autoPassResources, false);
    }
    // The wrapper replaces the entire settings object. The preview, like the
    // host's serialized updateGameSetting helper, must merge individual edits.
    await fetch(`${base}/reset?mode=fuel-hidden`, { method: 'POST', body: '{}' });
    for (const name of ['autoPassBids', 'autoPassBuilding', 'autoPassResources']) {
        const response = await fetch(`${base}/setting?mode=fuel-hidden`, {
            method: 'POST',
            body: JSON.stringify({ name, value: true }),
        });
        const data = await response.json();
        assert.deepEqual(data.state.currentPlayers, [2], 'setting write must not advance turns');
    }
    const preserved = await (await fetch(`${base}/state?mode=fuel-hidden`)).json();
    assert.deepEqual(preserved.settings, { autoPassBids: true, autoPassResources: true, autoPassBuilding: true });
    assert.deepEqual(errors, []);
    console.log('Phase auto-pass browser smoke: 8 wrapper-backed scenarios passed.');
} finally {
    await browser.close();
    await new Promise((resolve) => server.close(resolve));
}
