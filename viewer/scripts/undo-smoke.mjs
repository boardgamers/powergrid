import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';

const require = createRequire(import.meta.url);
const engine = require(fileURLToPath(new URL('../../engine/dist/index.js', import.meta.url)));

// You (seat 0) against two bots in the first auction, as BGS sends it to your viewer.
function auction() {
    let G = engine.setup(3, { map: 'Germany', variant: 'recharged', showMoney: true }, 'undo');
    G.players.forEach((player, index) => {
        player.name = ['You', 'Ada', 'Bob'][index];
    });
    let time = 1;
    const view = () => JSON.parse(JSON.stringify(engine.stripSecret(G, 0)));
    const play = (seat, name, data = G.players[seat].availableMoves.Bid[0]) => {
        G = engine.move(G, { name, data, time: time++ }, seat);
    };
    const choosing = view();
    play(0, 'ChoosePowerPlant', G.players[0].availableMoves.ChoosePowerPlant[1]);
    play(0, 'Bid');
    play(1, 'Bid');
    play(2, 'Bid');
    // Where "Undo my move" brings you back: before your second bid.
    const firstRaise = view();
    play(0, 'Bid');
    play(1, 'Bid');
    play(2, 'Pass', true);
    return { choosing, firstRaise, secondRaise: view() };
}

// BGS's "Undo my move" in games against bots (protocol `undo:available` / `undo`).
export async function checkUndoMove(page) {
    const { choosing, firstRaise, secondRaise } = auction();
    assert.equal(firstRaise.currentBid + 1, 9);
    assert.equal(secondRaise.currentBid + 1, 11);
    const control = page.locator('[data-board-control="undo-move"]');
    const localUndo = page.locator('[data-board-control="undo"]');
    const visor = page.locator('.calculator .visor');
    const label = (text) =>
        page.waitForFunction(
            (text) => document.querySelector('[data-board-control="undo-move"]')?.getAttribute('aria-label') === text,
            text
        );
    const emit = (event, payload) => page.evaluate(([event, payload]) => host.emit(event, payload), [event, payload]);

    await page.evaluate((state) => {
        window.host = window.powergrid.launch('#app');
        window.undoRequests = 0;
        window.undoReady = false;
        host.on('ready', () => (window.undoReady = true));
        host.on('undo', () => window.undoRequests++);
        host.emit('preferences', { sound: false, locale: 'en' });
        host.emit('player', { index: 0 });
        host.emit('state', state);
    }, secondRaise);
    await page.waitForFunction(() => window.undoReady);
    await visor.waitFor();
    assert.equal(await control.count(), 0, 'hidden until BGS offers undo');
    assert.equal(await localUndo.getAttribute('aria-disabled'), 'true');

    await emit('undo:available', true);
    await control.waitFor();
    assert.equal(await control.getAttribute('aria-label'), 'Undo my move');
    assert.equal(await control.locator('title').textContent(), 'Undo my move');
    assert.equal(await control.locator('image').count(), 1, 'uses the undo icon');
    assert.equal(await localUndo.count(), 0, 'takes the place of the empty local Undo');
    assert.equal(await page.locator('[data-board-slot="buttons"] [data-board-control="undo-move"]').count(), 1);
    await emit('preferences', { sound: false, locale: 'fr' });
    await label('Annuler mon coup');
    assert.equal(await control.locator('title').textContent(), 'Annuler mon coup');
    await emit('preferences', { sound: false, locale: 'en' });
    await label('Undo my move');

    // Only on the live board of a seated player.
    await emit('replay:start');
    await control.waitFor({ state: 'detached' });
    await emit('replay:end');
    await control.waitFor();
    await emit('preferences', { sound: false, locale: 'en', analysis: true });
    await control.waitFor({ state: 'detached' });
    await emit('preferences', { sound: false, locale: 'en', analysis: false });
    await control.waitFor();
    await emit('player', {});
    await control.waitFor({ state: 'detached' });
    await emit('player', { index: 0 });
    await control.waitFor();

    // Undo asks BGS, which answers with the earlier state: a bid dialled on the newer
    // position must not survive it.
    assert.equal(await visor.textContent(), '11');
    for (let i = 0; i < 2; i++) await page.locator('.calculator > g').nth(0).click();
    assert.equal(await visor.textContent(), '13');
    await control.click();
    assert.equal(await page.evaluate(() => undoRequests), 1);
    await control.waitFor({ state: 'detached' });
    await emit('state', firstRaise);
    await control.waitFor();
    assert.equal(await visor.textContent(), '9', 'the earlier bid floor, not the dialled bid');
    assert.match(await page.locator('.status-message').textContent(), /your turn to bid/);

    // A turn in progress is taken back by the board's own Undo first.
    await emit('state', choosing);
    await control.waitFor();
    await visor.waitFor({ state: 'detached' });
    await page.locator('[data-tutorial="plants"] g.canClick').first().click();
    await visor.waitFor();
    assert.equal(await control.count(), 0, 'buffered moves are undone locally first');
    assert.equal(await localUndo.getAttribute('aria-disabled'), null, 'the local Undo is enabled');
    await localUndo.click();
    assert.equal(await control.count(), 0, 'a double click on Undo cannot reach the saved move');
    await visor.waitFor({ state: 'detached' });
    await control.waitFor();

    await emit('undo:available', false);
    await control.waitFor({ state: 'detached' });
    assert.equal(await localUndo.getAttribute('aria-disabled'), 'true');
    assert.equal(await page.evaluate(() => undoRequests), 1);
    console.log('powergrid "Undo my move": availability, translation, undo request and rewound state passed');
}
