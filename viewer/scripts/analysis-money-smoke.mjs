import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
const require = createRequire(import.meta.url);
const engine = require('../../engine/dist/index.js');
export async function checkAnalysisMoney(page) {
    const state = JSON.parse(
        JSON.stringify(engine.setup(3, { map: 'Germany', variant: 'recharged', showMoney: true }, 'money'))
    );
    state.players.forEach((p, i) => (p.name = ['You', 'Ada', 'Bob'][i]));
    const actor = state.currentPlayers[0];
    const emit = (event, payload) => page.evaluate(([e, p]) => host.emit(e, p), [event, payload]);
    await page.evaluate(
        ({ state, actor }) => {
            window.host = window.powergrid.launch('#app');
            window.moneyMoves = [];
            host.on('move', (move) => window.moneyMoves.push(move));
            host.emit('preferences', { sound: false, locale: 'en' });
            host.emit('player', { index: actor });
            host.emit('state', state);
        },
        { state, actor }
    );
    await page.locator('.player-board').first().waitFor();
    assert.equal(await page.locator('[data-money-player]').count(), 0, 'live game has no editing');
    await emit('preferences', { analysis: true, sound: false, locale: 'en' });
    await page.locator('[data-money-player]').first().waitFor();
    assert.equal(await page.locator('[data-money-player]').count(), 3);
    for (const target of [actor, (actor + 1) % 3]) {
        const edit = page.locator(`[data-money-player="${target}"]`);
        await edit.focus();
        await page.keyboard.press('Enter');
        const input = page.locator('#analysis-money-input');
        await input.waitFor();
        assert.equal(await input.inputValue(), String(state.players[target].money));
        const save = page.locator('.analysis-money-form button[type="submit"]');
        for (const value of ['-1', '0.5', '10000', '']) {
            await input.fill(value);
            assert.equal(await save.isDisabled(), true);
        }
        await page.locator('.analysis-money-form button[type="button"]').click();
        assert.equal(await page.evaluate(() => moneyMoves.length), target === actor ? 0 : 1);
        await edit.click();
        await input.fill('123');
        await save.click();
        assert.equal(await save.isDisabled(), true);
        assert.deepEqual(await page.evaluate(() => moneyMoves[moneyMoves.length - 1]), [
            { name: 'SetAnalysisMoney', data: { player: target, money: 123 } },
        ]);
        assert.ok(
            (await page.locator('.player-board').allTextContents()).some((text) =>
                text.includes(`$${state.players[target].money}`)
            ),
            'no optimistic change'
        );
        state.players[target].money = 123;
        await emit('state', state);
        await input.waitFor({ state: 'detached' });
    }
    // Matching host rejection re-enables submission without mutating money.
    await page.locator(`[data-money-player="${actor}"]`).click();
    await page.locator('#analysis-money-input').fill('456');
    await page.locator('.analysis-money-form button[type="submit"]').click();
    await page.evaluate(() =>
        host.emit('move:result', { ok: false, move: moneyMoves[moneyMoves.length - 1], error: 'rejected' })
    );
    await page.locator('.analysis-money-form [role="alert"]').waitFor();
    assert.equal(await page.locator('.analysis-money-form button[type="submit"]').isDisabled(), false);
    await page.keyboard.press('Escape');
    await page.locator('#analysis-money-input').waitFor({ state: 'detached' });
    // BGS can reject a change silently (host error only, no move:result/state).
    // Explicit Close/Escape asks for the host's cached view, never retries the edit.
    await page.evaluate((state) => {
        window.moneyFetches = 0;
        window.moneyCachedState = state;
        host.on('fetchState', () => {
            moneyFetches++;
            host.emit('state', JSON.parse(JSON.stringify(moneyCachedState)));
        });
    }, state);
    for (const escape of [false, true]) {
        const before = await page.evaluate(() => moneyMoves.length);
        await page.locator(`[data-money-player="${actor}"]`).click();
        await page.locator('#analysis-money-input').fill('789');
        await page.locator('.analysis-money-form button[type="submit"]').click();
        const close = page.locator('.analysis-money-form button[type="button"]');
        assert.equal(await close.textContent(), 'Close and refresh');
        assert.equal(await page.evaluate(() => moneyFetches), escape ? 1 : 0, 'no automatic refresh');
        if (escape) await page.keyboard.press('Escape');
        else await close.click();
        await page.locator('#analysis-money-input').waitFor({ state: 'detached' });
        await page.locator(`[data-money-player="${actor}"]`).waitFor();
        assert.equal(await page.evaluate(() => moneyMoves.length), before + 1, 'no automatic retry');
        assert.equal(await page.evaluate(() => moneyFetches), escape ? 2 : 1);
        await page.locator(`[data-money-player="${actor}"]`).click();
        assert.equal(await page.locator('#analysis-money-input').inputValue(), String(state.players[actor].money));
        await page.keyboard.press('Escape');
    }
    // Closing never cancels the request: a delayed successful response still applies.
    state.players[actor].money = 789;
    await emit('state', state);
    await page.locator(`[data-money-player="${actor}"]`).click();
    assert.equal(await page.locator('#analysis-money-input').inputValue(), '789');
    await page.keyboard.press('Escape');
    assert.equal(await page.evaluate(() => moneyFetches), 2, 'unsent edits do not fetch');
    await emit('player', { index: (actor + 1) % 3 });
    assert.equal(await page.locator('[data-money-player]').count(), 0, 'inactive controlled seat cannot edit');
    await emit('player', {});
    assert.equal(await page.locator('[data-money-player]').count(), 0, 'spectator cannot edit');
}
