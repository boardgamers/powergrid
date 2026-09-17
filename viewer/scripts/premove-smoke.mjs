import assert from 'node:assert/strict';
import { mkdir } from 'node:fs/promises';
import { chromium } from 'playwright';
import { premovePreviewServer } from './premove-preview.mjs';

// Real viewer + real wrapper. No component mocks or synthetic game state patches in the browser.
const server = premovePreviewServer();
await new Promise((resolve) => server.listen(0, '127.0.0.1', resolve));
const url = `http://127.0.0.1:${server.address().port}`;
const browser = await chromium.launch({
    headless: true,
    ...(process.env.CHROMIUM_PATH ? { executablePath: process.env.CHROMIUM_PATH } : {}),
});
const screenshots = process.env.SCREENSHOT_DIR;
if (screenshots) await mkdir(screenshots, { recursive: true });
const errors = [];
try {
    const page = await browser.newPage({ viewport: { width: 1440, height: 1080 }, reducedMotion: 'reduce' });
    page.on('pageerror', (error) => errors.push(String(error)));
    let sent = 0;
    page.on('request', (request) => {
        if (new URL(request.url()).pathname === '/move') sent++;
    });
    const button = (name) => page.getByRole('button', { name, exact: true });
    const city = (name) =>
        page.locator('circle.canClick[pointer-events="all"]').filter({
            has: page.locator('title').filter({ hasText: new RegExp(`^${name} — build`) }),
        });
    const card = (area, number) =>
        page
            .locator(`[data-tutorial="${area}"] g.canClick`)
            .filter({
                has: page.locator('text').filter({ hasText: new RegExp(`^${number}$`) }),
            })
            .first();
    const done = () => page.locator('[data-tutorial="turn"] g.enabled').filter({ hasText: 'Done' }).first();
    const ownBoard = () => page.locator('.player-board').filter({ hasText: 'You' }).first();
    const state = async (scenario = 'after-resources', seat = 0) =>
        (await (await fetch(`${url}/state?scenario=${scenario}&seat=${seat}`)).json()).state;
    async function phase(text) {
        await page.waitForFunction(
            (text) => document.querySelector('.status-message')?.textContent.includes(text),
            text
        );
    }
    async function screenshot(name) {
        if (screenshots) {
            await page.evaluate(() => scrollTo(0, 0));
            await page.screenshot({ path: `${screenshots}/${name}.png`, fullPage: true });
        }
    }
    await page.goto(url);
    await button('Plan').waitFor();
    assert.equal(await page.locator('.statusBar .plan-entry').count(), 1, 'entry is in existing black toolbar');
    assert.equal(await page.locator('.round-planner').count(), 0, 'no empty planning toolbar');
    const initial = await state();
    const deckLabel = () =>
        page
            .locator('title')
            .filter({ hasText: /cards left/ })
            .textContent();
    const initialDeck = await deckLabel();
    await screenshot('toolbar');
    await button('Plan').click();
    await phase('Building');
    await city('Osnabrück').click();
    await city('Münster').click();
    assert.match(await ownBoard().textContent(), /Money: \$43/);
    assert.equal(await deckLabel(), initialDeck, 'public deck display survives local city builds');
    await done().click();
    await phase('Powering');
    await card('players', 4).click();
    await card('players', 13).click();
    await done().click();
    await phase('Simulation complete');
    assert.match(await ownBoard().textContent(), /Money: \$76/);
    assert.equal(sent, 0, 'planning never submits real moves');
    assert.deepEqual(await state(), initial, 'live state unchanged by simulation');
    await screenshot('planning');
    await button('Review premoves').click();
    assert.match(await page.getByRole('dialog').innerText(), /Osnabrück · up to \$10/);
    await button('Queue phases').click();
    await page.getByText('Your premoves · round 3', { exact: true }).waitFor();
    assert.equal(sent, 1);
    assert.equal((await state()).automation.plans[0].phases.length, 2);
    assert.deepEqual((await state('after-resources', 1)).automation.plans, {}, 'queue is private');
    await page.reload();
    await button('View on board').waitFor();
    await screenshot('queued');
    await button('View on board').click();
    await phase('Simulation complete');
    await button('Cancel queued moves').click();
    await page.waitForFunction(
        () => !document.querySelector('.round-planner')?.textContent.includes('Saving premoves')
    );
    await phase('Simulation complete');
    assert.equal((await state()).automation.plans[0].phases.length, 0);
    assert.match(await ownBoard().textContent(), /Money: \$76/, 'cancelling keeps local simulation');
    await button('Review premoves').click();
    await button('Queue phases').click();
    await button('Cancel all').waitFor();
    for (let i = 0; i < 2; i++) {
        const response = page.waitForResponse((r) => new URL(r.url()).pathname === '/opponent');
        await button('Finish next opponent phase').click();
        await response;
    }
    let live = await state();
    assert.equal(live.players[0].cities.length, 2);
    assert.equal(live.players[0].money, 43);
    assert.deepEqual(
        live.automation.plans[0].phases.map((p) => p.phase),
        ['Bureaucracy']
    );
    for (let i = 0; i < 2; i++) {
        const response = page.waitForResponse((r) => new URL(r.url()).pathname === '/opponent');
        await button('Finish next opponent phase').click();
        await response;
    }
    live = await state();
    assert.equal(live.players[0].money, 76);
    assert.equal(live.players[0].coalLeft, 0);
    assert.equal(live.automation.increments[0], 2);
    assert.equal(live.automation.plans[0].phases.length, 0);
    console.log('Off-turn plan, budget, private queue, reload, cancel, and execution passed.');

    await page.goto(`${url}/?scenario=auction`);
    await button('Simulate').click();
    const sentBeforeAuction = sent;
    await card('plants', 3).click();
    for (let i = 0; i < 12; i++) await page.locator('.calculator > g').nth(0).click();
    await page.locator('.calculator g').filter({ hasText: 'OK' }).click();
    await phase('Resources');
    assert.match(await ownBoard().textContent(), /Money: \$55/);
    const oil = () =>
        page
            .locator('[data-tutorial="resources"] g.canClick')
            .filter({ has: page.locator('title').filter({ hasText: /^Oil$/ }) })
            .first();
    await oil().click();
    await oil().click();
    await done().click();
    await phase('Building');
    await city('Osnabrück').click();
    assert.match(await ownBoard().textContent(), /Money: \$39/);
    assert.equal(await button('Review premoves').count(), 0, 'assumed purchases cannot be queued');
    await screenshot('auction');
    await button('Start over').click();
    await phase('Auction');
    await button('Continue without buying').click();
    await phase('Resources');
    assert.match(await ownBoard().textContent(), /Money: \$70/);
    assert.equal(sent, sentBeforeAuction);
    assert.equal((await state('auction')).players[0].money, 70);
    console.log('Assumed plant price, fuel purchases, no purchase, and simulation-only restriction passed.');

    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto(`${url}/?scenario=powering`);
    await button('Plan').click();
    await phase('Powering');
    await card('players', 4).click();
    await card('players', 13).click();
    await done().click();
    await phase('Simulation complete');
    assert.match(await ownBoard().textContent(), /Money: \$75/);
    assert.ok(
        await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1),
        'no mobile horizontal overflow'
    );
    await screenshot('mobile');
    await button('Review premoves').click();
    assert.equal(
        await page.getByRole('dialog').getByText('Building', { exact: true }).count(),
        0,
        'powering-only plan'
    );
    await button('Queue phases').click();
    await button('Cancel all').waitFor();
    assert.deepEqual(
        (await state('powering')).automation.plans[0].phases.map((p) => p.phase),
        ['Bureaucracy']
    );
    const cancelled = page.waitForResponse((r) => new URL(r.url()).pathname === '/move');
    await button('Cancel all').click();
    await cancelled;
    await page.locator('.round-planner').waitFor({ state: 'detached' });
    assert.equal(await page.locator('.round-planner').count(), 0, 'empty saved queue has no leftover strip');
    console.log('Mobile powering-only plan passed.');
    assert.deepEqual(errors, [], 'no browser runtime errors');
} finally {
    await browser.close();
    await new Promise((resolve) => server.close(resolve));
}
