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
        const state = JSON.parse(
            JSON.stringify(engine.setup(3, { map: 'Germany', variant: 'recharged', showMoney: true }, '17'))
        );
        state.players.forEach((player, index) => {
            player.name = ['You', 'Ada', 'Bob'][index];
        });
        await page.evaluate((state) => {
            window.host = window.powergrid.launch('#app');
            host.emit('preferences', { locale: 'fr', sound: false });
            host.emit('player', { index: 0 });
            host.emit('state', state);
        }, state);
        await page.waitForFunction(() =>
            document.querySelector('.modal-body')?.textContent.includes('Un joueur par ville')
        );
        const rules = await page.locator('.modal-body').innerText();
        assert.match(rules, /Acheter des ressources au marché, dans l’ordre inverse des joueurs/);
        assert.match(
            rules,
            /La partie se termine après la phase de construction où un joueur atteint au moins 17 villes\./
        );
        assert.match(rules, /la centrale au numéro le plus élevé/);
        assert.doesNotMatch(rules, /Buy Resources|One player|Game ends after|inverser/);
        if (width === 390) {
            await page.waitForFunction(() =>
                document.querySelector('[data-tutorial="resources"]')?.textContent.includes('RESTANTS')
            );
            const labels = {
                de: 'ÜBRIG',
                nl: 'OVER',
                it: 'RIMASTI',
                'pt-BR': 'RESTANTES',
                pl: 'POZOSTAŁO',
                ro: 'RĂMASE',
                da: 'TILBAGE',
                el: 'ΑΠΟΜΕΝΟΥΝ',
                ru: 'ОСТАЛОСЬ',
                hi: 'शेष',
                ko: '남은 수',
                'zh-TW': '剩餘',
                vi: 'CÒN LẠI',
            };
            for (const [locale, label] of Object.entries(labels)) {
                await page.evaluate((locale) => host.emit('preferences', { locale, sound: false }), locale);
                await page.waitForFunction(
                    (label) => document.querySelector('[data-tutorial="resources"]')?.textContent.includes(label),
                    label
                );
            }
        }
        assert.deepEqual(errors, []);
        await page.close();
        console.log(`Complete rules and remaining stock labels: ${width}px passed`);
    }
} finally {
    await browser.close();
    await new Promise((resolve) => server.close(resolve));
}
