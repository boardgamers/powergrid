import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { createServer } from 'node:http';
import { createRequire } from 'node:module';
import { chromium } from 'playwright';

const require = createRequire(import.meta.url);
const engine = require('../../engine/dist/index.js');
const wrapper = require('../../engine/dist/wrapper.js');
const html =
    '<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><style>body{margin:0}</style><link rel="stylesheet" href="/powergrid-viewer.css"><div id="app"></div><script src="/vue.js"></script><script src="/powergrid-viewer.umd.min.js"></script>';
const server = createServer(async (req, res) => {
    try {
        if (req.url === '/') {
            res.setHeader('Content-Type', 'text/html');
            return res.end(html);
        }
        const path =
            req.url === '/vue.js'
                ? require.resolve('vue/dist/vue.min.js')
                : new URL('../dist' + req.url, import.meta.url);
        res.setHeader(
            'Content-Type',
            req.url.endsWith('.css') ? 'text/css; charset=utf-8' : 'text/javascript; charset=utf-8'
        );
        res.end(await readFile(path));
    } catch {
        res.writeHead(404).end();
    }
});
await new Promise((resolve) => server.listen(0, '127.0.0.1', resolve));
const browser = await chromium.launch({ executablePath: process.env.CHROMIUM_EXECUTABLE });

function fixtures(map, players) {
    let state = engine.setup(players, { map, variant: 'original', showMoney: true }, 'stable-layout');
    state.players.forEach((p, i) => (p.name = `Player ${i + 1}`));
    const result = [],
        seen = new Set();
    for (let i = 0; i < 250 && state.round <= 2; i++) {
        const key = `${state.round}/${state.phase}/${!!state.chosenPowerPlant}`;
        if (!seen.has(key)) {
            seen.add(key);
            result.push({ name: key, state: JSON.parse(JSON.stringify(state)) });
        }
        state = wrapper.moveAI(state, state.currentPlayers[0]);
    }
    assert.ok(result.some((f) => f.state.phase === engine.Phase.Building));
    const step3 = JSON.parse(JSON.stringify(result.at(-1).state));
    step3.step = 3;
    step3.chosenPowerPlant = undefined;
    step3.actualMarket = [...step3.actualMarket, ...step3.futureMarket].slice(0, 6);
    step3.futureMarket = [];
    result.push({ name: 'Step 3 market', state: step3 });
    return result;
}

async function scene(page) {
    await page.evaluate(() => window.scrollTo(0, 0));
    return page.evaluate(() => {
        const map = document.querySelector('[data-board-slot="map"]');
        const matrix = map.firstElementChild.getScreenCTM();
        const cards = [...document.querySelectorAll('.player-board')].map((board) => {
            const transform = board.getScreenCTM();
            const p = new DOMPoint(0, 0).matrixTransform(transform);
            return { x: p.x, y: p.y, textPixels: 15 * Math.hypot(transform.a, transform.b) };
        });
        return {
            transform: map.getAttribute('transform'),
            viewBox: document.querySelector('#scene').getAttribute('viewBox'),
            matrix: ['a', 'b', 'c', 'd', 'e', 'f'].map((key) => matrix[key]),
            cityPixels: 50 * Math.hypot(matrix.a, matrix.b),
            cards,
        };
    });
}

let regionReframes = 0;
try {
    for (const [map, players, width, height, locale] of [
        ['Benelux', 5, 1834, 920, 'en'],
        ['Germany', 6, 1920, 1080, 'en'],
        ['Australia', 4, 1366, 768, 'en'],
        ['Bremen', 6, 1400, 900, 'de'],
        ['Europe', 5, 1600, 900, 'fr'],
        ['Korea', 4, 1440, 900, 'en'],
    ]) {
        const page = await browser.newPage({ viewport: { width, height } });
        const errors = [];
        page.on('pageerror', (e) => errors.push(e.message));
        await page.goto(`http://127.0.0.1:${server.address().port}/`);
        assert.deepEqual(errors, [], 'viewer bundle loads');
        await page.evaluate((locale) => {
            window.host = powergrid.launch('#app');
            host.emit('preferences', { sound: false, locale, fitToScreen: true });
            host.emit('player', { index: 0 });
        }, locale);
        let baseline;
        const states = fixtures(map, players);
        for (const fixture of states) {
            await page.evaluate((state) => {
                host.emit('player', { index: state.currentPlayers[0] });
                host.emit('state', state);
            }, fixture.state);
            await page.waitForTimeout(450);
            const current = await scene(page);
            assert.ok(
                current.cards.every((card) => card.textPixels >= 11.24),
                `${map}: readable player cards`
            );
            assert.equal(new Set(current.cards.map((p) => p.x.toFixed(2))).size, 1, `${map}: one player column`);
            assert.ok(
                current.cards.every((p, i) => i === 0 || p.y > current.cards[i - 1].y),
                `${map}: cards ordered vertically`
            );
            if (baseline) {
                assert.equal(current.transform, baseline.transform, `${map}: map transform changed at ${fixture.name}`);
                assert.equal(current.viewBox, baseline.viewBox, `${map}: canvas changed at ${fixture.name}`);
                current.matrix.forEach((v, i) =>
                    assert.ok(
                        Math.abs(v - baseline.matrix[i]) < 0.1,
                        `${map}: city screen positions changed at ${fixture.name} (matrix ${i}: ${baseline.matrix[i]} -> ${v})`
                    )
                );
            } else baseline = current;
            const auctionOverlap = await page.evaluate(() => {
                const calculator = document.querySelector('.calculator');
                if (!calculator) return false;
                const a = calculator.getBoundingClientRect();
                const b = document.querySelector('[data-board-slot="map"]').getBoundingClientRect();
                return (
                    Math.min(a.right, b.right) > Math.max(a.left, b.left) &&
                    Math.min(a.bottom, b.bottom) > Math.max(a.top, b.top)
                );
            });
            assert.equal(auctionOverlap, false, `${map}: bid controls stay clear of the network`);
        }
        const longStatus = JSON.parse(JSON.stringify(states.at(-1).state));
        longStatus.currentPlayers = [0];
        longStatus.log.push({
            type: 'event',
            event: 'An opponent has connected several cities across the network. '.repeat(12),
        });
        await page.evaluate((state) => {
            host.emit('player', { index: 1 });
            host.emit('state', state);
        }, longStatus);
        await page.waitForTimeout(450);
        assert.match(await page.locator('.status-message').textContent(), /An opponent has connected/);
        assert.deepEqual(
            (await scene(page)).matrix,
            baseline.matrix,
            `${map}: long status text does not move the board`
        );
        await page.evaluate(
            (locale) => host.emit('preferences', { locale, sound: false, showUnselectedRegions: false }),
            locale
        );
        await page.waitForTimeout(100);
        assert.deepEqual((await scene(page)).matrix, baseline.matrix, `${map}: decorative regions do not move cities`);
        await page.setViewportSize({ width: width - 240, height });
        await page.waitForTimeout(450);
        const resized = await scene(page);
        assert.notDeepEqual(resized.matrix, baseline.matrix, `${map}: still adapts to window resize`);
        await page.setViewportSize({ width: 390, height: 844 });
        await page.waitForTimeout(450);
        assert.equal(await page.locator('.game.stacked').count(), 1, `${map}: mobile layout still works`);
        assert.equal(new Set((await scene(page)).cards.map((p) => p.x.toFixed(2))).size, 1);
        await page.setViewportSize({ width, height });
        await page.waitForTimeout(450);
        assert.equal(await page.locator('.game.stacked').count(), 0, `${map}: returns to desktop`);
        assert.equal(new Set((await scene(page)).cards.map((p) => p.x.toFixed(2))).size, 1);
        await page.locator('#scene').screenshot({ path: `/tmp/powergrid-stable-${map.toLowerCase()}.png` });
        const beforeRegions = await scene(page);
        const reduced = JSON.parse(JSON.stringify(states[0].state));
        const excluded = reduced.map.cities[0].region;
        reduced.map.cities = reduced.map.cities.filter((city) => city.region !== excluded);
        const names = new Set(reduced.map.cities.map((city) => city.name));
        reduced.map.connections = reduced.map.connections.filter((connection) =>
            connection.nodes.every((name) => names.has(name))
        );
        if (reduced.map.cities.length) {
            await page.evaluate((state) => host.emit('state', state), reduced);
            await page.waitForTimeout(450);
            // Removing an interior region can leave the map's extents unchanged.
            // Across the fixtures, boundary changes must still trigger reframing.
            if ((await scene(page)).transform !== beforeRegions.transform) regionReframes++;
        }
        assert.deepEqual(errors, [], `${map}: no browser errors`);
        await page.close();
        console.log(
            `${map}, ${players} players, ${locale}: ${
                states.length
            } state changes stable; resize and mobile passed; ${baseline.cityPixels.toFixed(
                1
            )}px circular city diameter, ${baseline.cards[0].textPixels.toFixed(1)}px card text`
        );
    }
    assert.ok(regionReframes > 0, 'changing the selected network still reframes the map when its bounds require it');

    // Read actual CSS pixels after SVG viewBox scaling and fitToScreen styles.
    // Unit-space sizes alone miss the CSS max-height shrinking the entire board.
    for (const [map, players, width, height] of [
        ['Germany', 6, 1920, 700],
        ['Benelux', 6, 1366, 600],
        ['Australia', 4, 1366, 600],
    ]) {
        const page = await browser.newPage({ viewport: { width, height } });
        const states = fixtures(map, players);
        await page.goto(`http://127.0.0.1:${server.address().port}/`);
        await page.evaluate((state) => {
            window.host = powergrid.launch('#app');
            host.emit('preferences', { sound: false, fitToScreen: true });
            host.emit('player', { index: 0 });
            host.emit('state', state);
        }, states[0].state);
        await page.waitForTimeout(450);
        const initial = await scene(page);
        assert.ok(initial.cityPixels >= 35.99, `${map}: 36px cities on short desktops (${initial.cityPixels})`);
        assert.ok(
            initial.cards.every((card) => card.textPixels >= 11.24),
            `${map}: readable single-column cards`
        );
        assert.equal(new Set(initial.cards.map((card) => card.x.toFixed(2))).size, 1);
        const svgHeight = await page.locator('#scene').evaluate((svg) => svg.getBoundingClientRect().height);
        assert.ok(svgHeight > height, `${map}: allows scrolling instead of shrinking everything to fit`);
        await page.evaluate(
            (state) => host.emit('state', state),
            states.find((f) => f.state.phase === engine.Phase.Building).state
        );
        await page.waitForTimeout(450);
        assert.deepEqual((await scene(page)).matrix, initial.matrix, `${map}: short-screen map remains stable`);
        await page.locator('#scene').screenshot({ path: `/tmp/powergrid-readable-${map.toLowerCase()}.png` });
        await page.close();
        console.log(
            `${map}, ${width}×${height}: ${initial.cityPixels.toFixed(1)}px cities, readable cards, stable map`
        );
    }
} finally {
    await browser.close();
    await new Promise((resolve) => server.close(resolve));
}
