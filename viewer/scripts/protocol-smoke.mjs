import { checkHostPresentation } from './host-presentation-smoke.mjs';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { createServer } from 'node:http';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
import { chromium } from 'playwright';

const game = 'powergrid';
const require = createRequire(import.meta.url);
const repo = new URL('../../', import.meta.url);
const engine = require(fileURLToPath(new URL('engine/dist/index.js', repo)));
const html =
    '<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><link rel="stylesheet" href="/bundle.css"><div id="app"></div><script src="/vue.js"></script>' +
    '<script src="/bundle.js"></script>';
const server = createServer(async (req, res) => {
    try {
        const bundle = `viewer/dist/${game}-viewer.umd.min.js`;
        const css = `viewer/dist/${game}-viewer.css`;
        const files = {
            '/bundle.js': fileURLToPath(new URL(bundle, repo)),
            '/bundle.css': fileURLToPath(new URL(css, repo)),
            '/vue.js': require.resolve('vue/dist/vue.min.js'),
        };
        if (req.url === '/') {
            res.setHeader('Content-Type', 'text/html');
            res.end(html);
        } else if (files[req.url]) {
            res.setHeader('Content-Type', req.url.endsWith('.css') ? 'text/css' : 'text/javascript; charset=utf-8');
            res.end(await readFile(files[req.url]));
        } else {
            res.statusCode = 404;
            res.end();
        }
    } catch (error) {
        res.statusCode = 500;
        res.end(String(error));
    }
});
await new Promise((resolve) => server.listen(0, '127.0.0.1', resolve));
const browser = await chromium.launch({ executablePath: process.env.CHROMIUM_EXECUTABLE });
try {
    for (const width of [390, 1400]) {
        const page = await browser.newPage({ viewport: { width, height: 900 } });
        const errors = [];
        page.on('pageerror', (error) => errors.push(error.message));
        await page.goto(`http://127.0.0.1:${server.address().port}/`);
        assert.deepEqual(errors, [], 'bundle loads without browser errors');
        let state = engine.setup(3, { map: 'Germany', variant: 'recharged', showMoney: true }, '17');
        state = JSON.parse(JSON.stringify(state));
        state.players.forEach((player, index) => {
            player.name = ['You', 'Ada Lovelace', 'Bob'][index];
        });
        const id = (value) => value.toString(16).padStart(24, '0');
        const messages = Array.from({ length: 35 }, (_, i) => ({
            _id: id(i + 1),
            type: 'text',
            author: 'Bob',
            playerIndex: 2,
            text: `Earlier message ${i + 1}`,
            createdAt: '2026-09-13T12:00:00Z',
        }));
        await page.evaluate(
            ({ game, state, messages }) => {
                window.globalName = game;
                window.readyCount = 0;
                window.receipts = [];
                window.sent = [];
                window.playerClicks = [];
                window.fetches = 0;
                window.host = window[window.globalName].launch('#app');
                host.on('ready', () => readyCount++);
                host.on('fetchState', () => fetches++);
                host.on('chat:read', (payload) => receipts.push(payload));
                host.on('chat:send', (payload) => sent.push(payload));
                host.on('player:clicked', (payload) => playerClicks.push(payload));
                host.emit('preferences', { sound: false });
                host.emit('player', { index: 0 });
                host.emit('state', state);
                host.emit('chat:state', {
                    canSend: true,
                    mentions: [
                        { id: 'self', name: 'You', playerIndex: 0 },
                        { id: 'ada', name: 'Ada Lovelace', playerIndex: 1 },
                        { id: 'bob', name: 'Bob', playerIndex: 2 },
                    ],
                });
                host.emit('chat:messages', messages);
            },
            { game, state, messages }
        );
        await page.waitForFunction(() => readyCount === 1);
        const panel = page.locator('.bgs-game-chat');
        const input = panel.locator('input');
        const list = panel.locator('.chat-messages');
        await panel.scrollIntoViewIfNeeded();
        await page.waitForFunction(() => {
            const el = document.querySelector('.chat-messages');
            return el && Math.abs(el.scrollHeight - el.scrollTop - el.clientHeight) < 3;
        });
        assert.equal(await panel.locator('summary').textContent(), 'Chat', 'old history is not unread');
        const shortcut = page.locator('.chat-shortcut');
        if (width === 390) {
            await page.locator('.game-feed-tabs button').filter({ hasText: 'Journal' }).click();
            await page.waitForTimeout(300);
            assert.equal(await shortcut.isHidden(), true, 'no floating shortcut without unread chat');
            await page.locator('.game-feed-tabs button').filter({ hasText: 'Chat' }).click();
            await page.waitForFunction(() => document.querySelector('.journal-and-chat').dataset.feed === 'chat');
        }
        await input.fill('@');
        assert.deepEqual(await panel.locator('.chat-suggestions button').allTextContents(), ['@Ada Lovelace', '@Bob']);
        await input.press('Enter');
        assert.equal(await input.inputValue(), '@"Ada Lovelace" ');
        assert.equal(await page.evaluate(() => sent.length), 0, 'selecting a mention does not send');
        await input.fill('@"Ada Lovelace" hello');
        await input.press('Enter');
        assert.equal(await page.evaluate(() => sent.length), 1);
        await input.fill('next draft');
        await page.evaluate(() => host.emit('chat:result', { requestId: sent[0].requestId, ok: true }));
        assert.equal(await input.inputValue(), 'next draft', 'ack preserves a newer draft');
        await input.press('Enter');
        await page.evaluate(() =>
            host.emit('chat:result', { requestId: sent[1].requestId, ok: false, error: 'Try again' })
        );
        assert.equal(await input.inputValue(), 'next draft');
        assert.match(await panel.locator('.chat-status').textContent(), /Try again/);
        if (width === 390) {
            await page.locator('.game-feed-tabs button').filter({ hasText: 'Journal' }).click();
        }
        await panel.evaluate((el) => {
            el.open = false;
        });
        await page.evaluate(() => window.scrollTo(0, 0));
        const incoming = {
            _id: id(40),
            type: 'text',
            author: 'Ada Lovelace',
            playerIndex: 1,
            text: '@You see https://example.com',
            segments: [
                { kind: 'mention', name: 'You', id: 'self' },
                { kind: 'text', text: ' see ' },
                { kind: 'link', text: 'example', url: 'https://example.com' },
            ],
        };
        await page.evaluate((incoming) => {
            host.emit('chat:appended', [incoming]);
            host.emit('chat:appended', [incoming]);
        }, incoming);
        assert.match(await panel.locator('summary').textContent(), /1 unread/);
        assert.equal(await list.locator('article').count(), 36, 'duplicate append is ignored');
        await page.evaluate((messages) => host.emit('chat:messages', messages), [...messages, incoming]);
        assert.match(
            await panel.locator('summary').textContent(),
            /1 unread/,
            'history refresh preserves known unread'
        );
        await page.waitForFunction(() => !document.querySelector('.chat-shortcut').hidden);
        assert.match(await shortcut.textContent(), /Chat\s*1$/, 'shortcut shows the unread count');
        const shortcutBox = await shortcut.boundingBox();
        assert.equal(
            Math.round(width - (shortcutBox.x + shortcutBox.width)),
            89,
            'shortcut is anchored bottom-right, just left of the settings gear'
        );
        const covered = await page.evaluate(
            (b) =>
                Array.from(document.querySelectorAll('#scene g.button'))
                    .map((g) => g.getBoundingClientRect())
                    .filter((r) => r.left < b.x + b.width && r.right > b.x && r.top < b.y + b.height && r.bottom > b.y)
                    .length,
            shortcutBox
        );
        assert.equal(covered, 0, 'shortcut covers no game buttons');
        const link = list.locator('a');
        assert.equal(await link.getAttribute('href'), 'https://example.com');
        assert.match(await link.getAttribute('rel'), /noopener/);
        await page.evaluate(
            (incoming) =>
                host.emit('chat:updated', [{ ...incoming, text: '<img src=x onerror=alert(1)>', segments: undefined }]),
            incoming
        );
        assert.equal(await list.locator('article').last().locator('img').count(), 0);
        assert.match(await list.locator('article').last().textContent(), /<img/);
        await page.evaluate((incoming) => host.emit('chat:updated', [incoming]), incoming);
        await shortcut.click();
        await page.waitForFunction(() => {
            const chat = document.querySelector('.bgs-game-chat');
            const rect = chat.getBoundingClientRect();
            return (
                chat.open &&
                document.querySelector('.journal-and-chat').dataset.feed === 'chat' &&
                rect.top < innerHeight &&
                rect.bottom > 0
            );
        });
        await list.evaluate((el) => {
            el.scrollTop = el.scrollHeight;
            el.dispatchEvent(new Event('scroll'));
        });
        await list.locator('.chat-mention').click();
        assert.deepEqual(await page.evaluate(() => playerClicks), [{ index: 0 }]);
        await page.waitForFunction(() => receipts.some((r) => r.messageId === '000000000000000000000028'));
        await page.waitForFunction(() => document.querySelector('.chat-shortcut').hidden);
        const receiptCount = await page.evaluate(() => receipts.length);
        await list.evaluate((el) => {
            el.scrollTop = 0;
            el.dispatchEvent(new Event('scroll'));
            el.scrollTop = el.scrollHeight;
            el.dispatchEvent(new Event('scroll'));
        });
        await page.waitForTimeout(650);
        assert.equal(await page.evaluate(() => receipts.length), receiptCount, 'scrolling does not repeat read events');
        await page.evaluate(() => host.emit('chat:deleted', ['000000000000000000000028']));
        assert.equal(await list.locator('article').count(), 35);
        await page.evaluate((state) => {
            host.emit('state', state);
            host.emit('state:updated');
        }, state);
        await page.waitForFunction(() => fetches > 0);
        assert.equal(await page.evaluate(() => readyCount), 1, 'ready fires once');
        await page.evaluate(
            (state) => host.emit('gamelog', { start: 0, data: { state: { ...state, newTurn: false } } }),
            state
        );
        await page.waitForTimeout(100);
        assert.equal(
            await page.evaluate(() => fetches),
            1,
            'tentative move state is rendered without fetching a committed state'
        );

        await page.evaluate(() => {
            window.translationsRequested = [];
            host.on('chat:translate', (request) => {
                translationsRequested.push(request);
                host.emit('chat:translation', { ...request, ok: true, text: 'Bonjour <img src=x>', language: 'en' });
            });
            host.emit('chat:state', {
                canSend: true,
                translationTarget: 'fr',
                translationLabels: {
                    translate: 'Traduire',
                    translating: 'Traduction…',
                    translated: 'Traduit',
                    original: 'Voir l’original',
                    error: 'Indisponible',
                    retry: 'Réessayer',
                },
            });
            host.emit('chat:messages', [
                { _id: '000000000000000000000070', type: 'text', text: 'Hello', language: 'en' },
            ]);
        });
        await page.locator('.chat-translate').click();
        await page.getByRole('button', { name: 'Traduit · Voir l’original', exact: true }).waitFor();
        assert.equal(await page.evaluate(() => translationsRequested.length), 1);
        assert.equal(await page.locator('[data-message-id="000000000000000000000070"] img').count(), 0);
        assert.match(
            await page.locator('[data-message-id="000000000000000000000070"]').textContent(),
            /Bonjour <img src=x>/
        );
        await page.locator('.chat-translate').click();
        assert.match(await page.locator('[data-message-id="000000000000000000000070"]').textContent(), /Hello/);
        assert.equal(
            await page.evaluate(() => translationsRequested.length),
            1,
            'showing original needs no new request'
        );
        await page.evaluate(() => host.emit('preferences', { sound: false, analysis: true }));
        await page.waitForFunction(() => !document.querySelector('.chat-translate')?.getBoundingClientRect().height);
        await page.screenshot({ path: '/tmp/powergrid-analysis-' + width + '.png', fullPage: true });
        await page.evaluate(() => host.emit('preferences', { sound: false, analysis: false }));
        await page.screenshot({ path: `/tmp/${game}-protocol-${width}.png`, fullPage: true });
        await page.evaluate(
            ({ state, incoming }) => {
                const old = host;
                host = window[globalName].launch('#app');
                host.emit('preferences', { sound: false });
                host.emit('player', { index: 0 });
                host.emit('state', state);
                host.emit('chat:state', { canSend: true });
                old.emit('chat:appended', [incoming]);
            },
            { state, incoming }
        );
        assert.equal(await page.locator('.bgs-game-chat').count(), 1);
        assert.equal(await page.locator('.chat-messages article').count(), 0, 'relaunch detaches old chat');
        assert.deepEqual(errors, [], 'no browser errors');
        // Reloaded history uses BGS's saved watermark, not just live append events.
        await page.locator('.bgs-game-chat').evaluate((el) => {
            el.open = false;
        });
        await page.evaluate(() => {
            window.restoredReceipts = [];
            host.on('chat:read', (payload) => restoredReceipts.push(payload));
            host.emit('chat:state', { canSend: true, readState: { userId: 'self', lastReadAt: 1000 } });
            host.emit('chat:messages', [
                { _id: '000000010000000000000001', type: 'text', authorId: 'bob', text: 'Already read' },
                { _id: '000000020000000000000001', type: 'text', authorId: 'bob', text: 'Unread after reload' },
                { _id: '000000030000000000000001', type: 'text', authorId: 'self', text: 'My own message' },
                { _id: '000000040000000000000001', type: 'system', text: 'Game started' },
            ]);
        });
        await page.waitForFunction(() => /1 unread/.test(document.querySelector('.bgs-game-chat summary').textContent));
        await page.waitForTimeout(650);
        assert.equal(
            await page.evaluate(() => restoredReceipts.length),
            0,
            'hidden chat does not mark restored history read'
        );
        await page.locator('.chat-shortcut').click();
        await page.waitForFunction(() => restoredReceipts.length > 0);
        assert.doesNotMatch(
            await page.locator('.bgs-game-chat summary').textContent(),
            /unread/,
            'opening chat clears restored unread'
        );
        await page.evaluate(() => {
            window.preferenceUpdates = [];
            host.on('update:preference', (value) => preferenceUpdates.push(value));
            host.emit('preferences', { sound: false, colorBlind: true });
        });
        await page.waitForFunction(
            () => document.querySelector('.color-blind-toggle')?.getAttribute('aria-pressed') === 'true'
        );
        const owners = await page.locator('.house-owner text').allTextContents();
        assert.deepEqual([...new Set(owners.map((t) => t.trim()))].sort(), ['1', '2', '3']);
        assert.match(await page.locator('.player-board [data-bgs-player="1"]').textContent(), /2 · Ada Lovelace/);
        const regions = await page.locator('.region-labels text').allTextContents();
        assert.equal(regions.length, state.map.cities.length);
        assert.equal(new Set(regions).size, new Set(state.map.cities.map((city) => city.region)).size);
        await page.locator('#scene').screenshot({ path: `/tmp/powergrid-color-blind-${width}.png` });
        await page.getByRole('button', { name: 'Color-blind mode', exact: true }).click();
        await page.waitForFunction(() => !document.querySelector('.house-owner'));
        assert.equal(await page.locator('.region-labels').count(), 0);
        assert.doesNotMatch(await page.locator('.player-board [data-bgs-player="1"]').textContent(), /2 ·/);
        assert.deepEqual(await page.evaluate(() => preferenceUpdates), [{ name: 'colorBlind', value: false }]);
        await checkHostPresentation(page, 'host', `/tmp/powergrid-board-thumbnail-${width}.png`);
        assert.deepEqual(errors, []);
        await page.close();
        console.log(`${game} ${width}px: protocol/chat smoke passed`);
    }
} finally {
    await browser.close();
    await new Promise((resolve) => server.close(resolve));
}
