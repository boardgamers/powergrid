// Run after packaging: node viewer/scripts/action-controls-smoke.mjs
import assert from 'node:assert/strict';
import { chromium } from 'playwright';
import { auctionPreviewServer } from './auction-preview.mjs';

const server = auctionPreviewServer();
await new Promise((resolve) => server.listen(0, '127.0.0.1', resolve));
const browser = await chromium.launch({ executablePath: process.env.CHROMIUM_EXECUTABLE });
try {
    for (const mode of ['your-turn', 'only-pass']) {
        const page = await browser.newPage();
        await page.goto(`http://127.0.0.1:${server.address().port}/?mode=${mode}`);
        const button = page.locator('[data-board-control="pass"]');
        await button.waitFor();
        const appearance = () =>
            button.evaluate((element) => {
                const style = (selector) => {
                    const css = getComputedStyle(element.querySelector(selector));
                    return { fill: css.fill, stroke: css.stroke, width: css.strokeWidth };
                };
                return {
                    phase: style('.phase-background'),
                    divider: style('.button-divider'),
                    phaseIcon: style('[data-phase-icon]'),
                    actionIcon: style('[data-action-icon]'),
                    outline: style('.button-outline'),
                };
            });
        const reference = page.locator('[data-board-control="color-blind"]');
        const referenceStyle = () =>
            reference.locator('.option-background').evaluate((e) => {
                const css = getComputedStyle(e);
                return { fill: css.fill, stroke: css.stroke, width: css.strokeWidth };
            });
        const referenceRest = await referenceStyle();
        await reference.hover();
        const referenceHover = await referenceStyle();
        await page.mouse.move(0, 0);
        const before = await appearance();
        assert.equal(before.phase.fill, referenceRest.fill);
        assert.equal(before.outline.stroke, mode === 'only-pass' ? 'rgb(0, 0, 255)' : 'rgb(0, 0, 0)');
        assert.equal(await page.locator('[data-market-highlight]').count(), mode === 'only-pass' ? 0 : 1);
        const checkHover = async (focused = false) => {
            const after = await appearance();
            assert.equal(after.outline.stroke, 'rgb(255, 255, 255)');
            assert.equal(after.outline.fill, 'none');
            assert.equal(after.phase.fill, focused ? referenceRest.fill : referenceHover.fill);
            assert.equal(after.outline.width, focused ? '3px' : referenceHover.width);
            assert.equal(after.divider.stroke, focused ? before.divider.stroke : 'rgb(89, 102, 108)');
            for (const key of ['phaseIcon', 'actionIcon']) {
                assert.deepEqual(after[key], before[key], `${key} stays unchanged`);
            }
        };
        for (const side of ['[data-phase-icon]', '[data-action-icon]']) {
            await button.locator(side).hover();
            await checkHover();
        }
        await page.mouse.move(0, 0);
        assert.deepEqual(await appearance(), before);
        await button.focus();
        await checkHover(true);
        if (mode === 'your-turn') {
            const plant = page.locator('[data-market-plant="8"]');
            await plant.hover();
            assert.equal(
                await plant
                    .locator(':scope > rect')
                    .first()
                    .evaluate((e) => getComputedStyle(e).stroke),
                'rgb(255, 255, 255)'
            );
        }
        for (const control of ['color-blind', 'plan']) {
            const option = page.locator(`[data-board-control="${control}"]`);
            if (!(await option.count())) continue;
            await option.hover();
            const iconColors = await option
                .locator(':scope > g')
                .first()
                .evaluate((g) =>
                    [...g.querySelectorAll('path, circle, rect')].map((e) => ({
                        stroke: getComputedStyle(e).stroke,
                        fill: getComputedStyle(e).fill,
                    }))
                );
            assert(
                iconColors.every((style) => style.stroke === 'rgb(0, 0, 0)' && style.fill === 'none'),
                `${control} pictograms stay black and unfilled`
            );
        }
        await page.close();
        console.log(`${mode}: hover matches board options; focus and market cues passed`);
    }
    {
        const page = await browser.newPage();
        await page.goto(`http://127.0.0.1:${server.address().port}/?mode=public&text=1`);
        const pass = page.locator('[data-board-control="pass"]');
        const undo = page.locator('[data-board-control="undo"]');
        await pass.locator('[data-action-label]').waitFor();
        assert.equal(await pass.getAttribute('aria-disabled'), 'true');
        assert.equal(await undo.getAttribute('aria-disabled'), 'true');
        const fadedText = await pass.locator('[data-action-label]').evaluate((e) => getComputedStyle(e).fill);
        assert.equal(fadedText, 'rgb(192, 192, 192)');
        await page.locator('[data-board-control="text-actions"]').click();
        await pass.locator('[data-phase-icon]').waitFor();
        const checkDisabled = async () => {
            for (const selector of ['[data-phase-icon]', '[data-action-icon]', '.button-divider']) {
                assert.equal(await pass.locator(selector).evaluate((e) => getComputedStyle(e).stroke), fadedText);
            }
            assert.equal(
                await pass.locator('.phase-background').evaluate((e) => getComputedStyle(e).fill),
                'rgb(220, 220, 220)'
            );
            assert.equal(await pass.locator('.button-outline').evaluate((e) => getComputedStyle(e).strokeWidth), '1px');
            assert.equal(
                await undo.locator('[data-action-icon]').evaluate((e) => getComputedStyle(e).filter),
                'invert(0.75)'
            );
        };
        await checkDisabled();
        await pass.hover();
        await checkDisabled();
        await page.close();
        console.log('Disabled controls: pictograms and divider match faded text, including on hover');
    }
    const page = await browser.newPage();
    await page.goto(`http://127.0.0.1:${server.address().port}/?mode=resources`);
    const phaseButton = page.locator('[data-board-control="pass"]');
    await phaseButton.waitFor();
    const cardsLeft = await page.evaluate(() => document.querySelector('.game').__vue__.G.cardsLeft);
    assert.equal((await page.locator('[data-deck-count]').textContent()).trim(), String(cardsLeft));
    const countIsCentered = await page.locator('[data-deck-count]').evaluate((label) => {
        const card = label.previousElementSibling;
        return (
            Number(label.getAttribute('x')) === Number(card.getAttribute('x')) + 30 &&
            Number(label.getAttribute('y')) === Number(card.getAttribute('y')) + 20
        );
    });
    assert(countIsCentered, 'remaining count is centered on the top card');
    assert(await phaseButton.evaluate((e) => e.classList.contains('skip-action')));
    await page.evaluate(() => {
        const deck = document.querySelector('[data-board-slot="powerPlantDeck"]');
        window.deckSnapshots = [deck.innerHTML];
        window.deckObserver = new MutationObserver(() => window.deckSnapshots.push(deck.innerHTML));
        window.deckObserver.observe(deck, { childList: true, attributes: true, characterData: true, subtree: true });
    });
    const echo = page.waitForResponse((response) => response.url().includes('/move?'));
    await page.evaluate(() => {
        const game = document.querySelector('.game').__vue__;
        game.buyResource(game.G.players[0].availableMoves.BuyResource[0]);
    });
    await echo;
    await page.waitForFunction(
        () => !document.querySelector('[data-board-control="pass"]').classList.contains('skip-action')
    );
    const undo = page.locator('[data-board-control="undo"]');
    const width = (locator) => locator.evaluate((e) => getComputedStyle(e).strokeWidth);
    assert.equal(await width(phaseButton.locator('.button-outline')), '2px');
    assert.equal(await width(undo.locator('.undo-background')), '2px');
    await undo.hover();
    assert.equal(
        await undo.locator('image').evaluate((e) => getComputedStyle(e).filter),
        'none',
        'Undo pictogram stays black'
    );
    await undo.click();
    await page.waitForFunction(() =>
        document.querySelector('[data-board-control="pass"]').classList.contains('skip-action')
    );
    assert.equal(await width(phaseButton.locator('.button-outline')), '2px');
    assert.equal(await width(undo.locator('.undo-background')), '1px', 'disabled undo is thinner');
    const snapshots = await page.evaluate(() => {
        window.deckObserver.disconnect();
        return window.deckSnapshots;
    });
    assert(
        snapshots.every((snapshot) => snapshot === snapshots[0]),
        'draw pile stays unchanged during buy/echo/undo'
    );
    await page.close();
    console.log(
        'Resources: skip → finish → undo → skip; matching enabled borders, thin disabled border, stable draw pile'
    );
    for (const mode of ['building', 'powering']) {
        const page = await browser.newPage();
        await page.goto(`http://127.0.0.1:${server.address().port}/?mode=${mode}`);
        const button = page.locator('[data-board-control="pass"]');
        await button.waitFor();
        assert(await button.evaluate((e) => e.classList.contains('skip-action')));
        assert.equal(
            await button.locator('.button-outline').evaluate((e) => getComputedStyle(e).stroke),
            'rgb(0, 0, 0)'
        );
        if (mode === 'powering') {
            const plant = page.locator('[data-plant-number="3"]');
            const border = plant.locator(':scope > rect').first();
            assert.equal(await border.evaluate((e) => getComputedStyle(e).strokeWidth), '4px');
            assert.equal(await border.evaluate((e) => getComputedStyle(e).stroke), 'rgb(0, 0, 255)');
            await plant.hover();
            assert.equal(await border.evaluate((e) => getComputedStyle(e).stroke), 'rgb(255, 255, 255)');
        }
        const echoed = page.waitForResponse((response) => response.url().includes('/move?'));
        await page.evaluate((mode) => {
            const game = document.querySelector('.game').__vue__;
            const name = mode === 'building' ? 'Build' : 'UsePowerPlant';
            game.sendMove({ name, data: game.G.players[0].availableMoves[name][0] });
        }, mode);
        await echoed;
        await page.waitForFunction(
            () => !document.querySelector('[data-board-control="pass"]').classList.contains('skip-action')
        );
        assert.equal(
            await button.locator('.button-outline').evaluate((e) => getComputedStyle(e).stroke),
            'rgb(0, 0, 255)'
        );
        if (mode === 'powering') {
            assert.equal(
                await page
                    .locator('[data-plant-number="3"] > rect')
                    .first()
                    .evaluate((e) => getComputedStyle(e).strokeWidth),
                '3px'
            );
        }
        await page.locator('[data-board-control="undo"]').click();
        await page.waitForFunction(() =>
            document.querySelector('[data-board-control="pass"]').classList.contains('skip-action')
        );
        await page.close();
        console.log(`${mode}: skip → finish → undo → skip; consistent borders`);
    }
} finally {
    await browser.close();
    await new Promise((resolve) => server.close(resolve));
}
