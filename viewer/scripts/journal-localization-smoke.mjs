import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { chromium } from 'playwright';
const root = new URL('../src/localization/', import.meta.url);
const runtime = await readFile(new URL('runtime.js', root), 'utf8');
const journal = await readFile(new URL('journal.js', root), 'utf8');
const locales = ['en', 'fr', 'de', 'nl', 'it', 'pl', 'ro', 'da', 'pt-BR', 'ru', 'el', 'hi', 'ko', 'zh-TW', 'vi'];
const catalogs = Object.fromEntries(
    await Promise.all(
        locales.map(async (lang) => [lang, JSON.parse(await readFile(new URL(`${lang}.json`, root), 'utf8'))])
    )
);
const browser = await chromium.launch({ headless: true });
try {
    const page = await browser.newPage();
    const results = await page.evaluate(
        async ({ runtime, journal, catalogs, locales }) => {
            const load = (s) => import('data:text/javascript;base64,' + btoa(unescape(encodeURIComponent(s))));
            const { createTranslator } = await load(runtime);
            const { localizeJournal } = await load(journal);
            const name = '<span data-bgs-player="0">Build</span>';
            return locales.map((lang) => {
                const tr = createTranslator(catalogs, lang).translate;
                const read = (html) => {
                    const div = document.createElement('div');
                    div.innerHTML = html;
                    return div.textContent;
                };
                const parts = localizeJournal(`${name} uses Power Plant <b>4</b>.`, tr, (n) => ({ number: n }));
                const purchase = localizeJournal(`${name} buys <b>coal</b> for <span>$3</span>.`, tr, () => undefined);
                const text = purchase.map((p) => read(p.html)).join('');
                const expected = tr('{p0} buys {p1} for {p2}.')
                    .replace('{p0}', 'Build')
                    .replace('{p1}', tr('coal'))
                    .replace('{p2}', '$3');
                const plantName = localizeJournal(
                    '<span data-bgs-player="1">Power Plant 3</span> uses Power Plant <b>4</b>.',
                    tr,
                    (n) => ({ number: n })
                );
                const legacyName = localizeJournal(
                    '<span style="color:red">Power Plant 3</span> uses Power Plant 4.',
                    tr,
                    (n) => ({ number: n })
                );
                return {
                    protectedNames: [plantName, legacyName].every((parts) =>
                        parts.some((p) => p.html?.includes('>Power Plant 3</span>'))
                    ),
                    protectedPlants: [plantName, legacyName].map((parts) =>
                        parts.filter((p) => p.plant).map((p) => p.plant.number)
                    ),
                    lang,
                    text,
                    expected,
                    plants: parts.filter((p) => p.plant).map((p) => p.plant.number),
                    name: parts.some((p) => p.html?.includes('>Build</span>')),
                    income: tr('Cities supplied: 3. Income: $44 before map penalties. Houses show connected cities.'),
                };
            });
        },
        { runtime, journal, catalogs, locales }
    );
    for (const r of results) {
        assert.equal(r.protectedNames, true, r.lang + ' plant-like player name');
        assert.deepEqual(r.protectedPlants, [[4], [4]], r.lang + ' only actual plants illustrated');
        assert.equal(r.text, r.expected, r.lang + ' purchase sentence');
        assert.deepEqual(r.plants, [4], r.lang + ' plant preserved');
        assert.equal(r.name, true, r.lang + ' player preserved');
        if (r.lang !== 'en') assert.ok(!r.income.includes('Cities supplied:'), r.lang + ' income tooltip');
    }
    console.log('Whole journal sentences, plant icons, player names and income tooltips passed in all 15 locales.');
} finally {
    await browser.close();
}
