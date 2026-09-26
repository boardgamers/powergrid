import assert from 'node:assert/strict';
import test from 'node:test';
import { readFile } from 'node:fs/promises';
const source = await readFile(new URL('../viewer/src/localization/runtime.js', import.meta.url), 'utf8');
const { createTranslator, resolveLocale } = await import(
    'data:text/javascript;base64,' + Buffer.from(source).toString('base64')
);
const catalogs = {
    nl: {
        Draw: 'Tekenen',
        'Your cash: $': 'Je geld: $',
        Ore: 'Erts',
        east: 'oost',
        '{p0} · ◈ {p1}': '{p0} · ◈ {p1}',
        Round: 'Ronde',
        'Build {p0} for {p1}': 'Bouw voor {p1}: {p0}',
        '{p0} buys {p1}': '{p0} koopt {p1}',
        'Make money by trading': 'Verdien geld door te handelen',
        'Gain {p0} points{p1}': 'Krijg {p0} punten{p1}',
    },
    fr: { Round: 'Manche' },
};
test('regional language preferences select supported catalogues', () => {
    assert.equal(resolveLocale('nl-BE'), 'nl');
    assert.equal(resolveLocale('pt-PT'), 'pt-BR');
    assert.equal(resolveLocale('zh-Hant-TW'), 'zh-TW');
    assert.equal(resolveLocale('zh-CN'), 'en');
    assert.equal(resolveLocale(undefined), 'en');
});
test('dynamic values are reordered while player names stay unchanged', () => {
    const t = createTranslator(catalogs, 'nl');
    t.setNames(['Draw']);
    assert.equal(t.translate('Draw buys 3'), 'Draw koopt 3');
    assert.equal(t.translate('Build 2 for 10'), 'Bouw voor 10: 2');
    assert.equal(t.translate('Draw'), 'Draw');
    assert.equal(t.translate('Gain 2 points'), 'Krijg 2 punten');
});
test('tutorial numbering and whitespace survive translation', () => {
    const t = createTranslator(catalogs, 'nl');
    assert.equal(t.translate('  1/5 · Make money by trading\n'), '  1/5 · Verdien geld door te handelen\n');
    assert.equal(t.translate('Round 2'), 'Ronde 2');
    assert.equal(t.translate('Unknown sentence'), 'Unknown sentence');
});
test('language changes clear caches and preserve the English fallback', () => {
    const t = createTranslator(catalogs, 'nl');
    assert.equal(t.translate('Round'), 'Ronde');
    t.setLocale('fr');
    assert.equal(t.translate('Round'), 'Manche');
    t.setLocale('en');
    assert.equal(t.translate('Round'), 'Round');
});

test('icon-separated values and uppercase labels are localized', () => {
    const t = createTranslator(catalogs, 'nl');
    assert.equal(t.translate('Ore · ◈ 10'), 'Erts · ◈ 10');
    assert.equal(t.translate('EAST'), 'OOST');
});

test('decorative arrows and attached currency values keep their meaning', () => {
    const t = createTranslator(catalogs, 'nl');
    assert.equal(t.translate('Draw →'), 'Tekenen →');
    assert.equal(t.translate('Your cash: $20'), 'Je geld: $20');
});

test('Persian regional tags, prices and journal parameters stay intact', async () => {
    assert.equal(resolveLocale('fa-IR'), 'fa');
    assert.equal(resolveLocale('FA_IR'), 'fa');
    const fa = JSON.parse(await readFile(new URL('../viewer/src/localization/fa.json', import.meta.url), 'utf8'));
    const t = createTranslator({ fa }, 'fa-IR');
    t.setNames(['Power Plant']);
    assert.equal(t.translate('Buy for $25'), 'خرید به قیمت $25');
    assert.equal(t.translate('Power Plant buys 2 Coal for $6.'), 'Power Plant با پرداخت $6، 2 زغال‌سنگ می‌خرد.');
    assert.equal(t.translate('translate(110, 20) scale(2)'), 'translate(110, 20) scale(2)');
    assert.equal(t.translate('Power Plant'), 'Power Plant');
    assert.equal(t.translate('REMAINING'), 'باقی‌مانده');
    t.setLocale('en');
    assert.equal(t.translate('Buy for $25'), 'Buy for $25');
});
