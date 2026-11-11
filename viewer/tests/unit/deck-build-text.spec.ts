import { expect } from 'chai';
import { deckBuildText, DECK_BUILD_TEMPLATES } from 'powergrid-engine/src/deckBuildText';
import { GameOptions, MapName, Variant } from 'powergrid-engine/src/gamestate';
import { maps } from 'powergrid-engine/src/maps';
import { availableDecks } from 'powergrid-engine/src/powerPlants';
import da from '../../src/localization/da.json';
import de from '../../src/localization/de.json';
import el from '../../src/localization/el.json';
import fa from '../../src/localization/fa.json';
import fr from '../../src/localization/fr.json';
import hi from '../../src/localization/hi.json';
import italian from '../../src/localization/it.json';
import ko from '../../src/localization/ko.json';
import nl from '../../src/localization/nl.json';
import pl from '../../src/localization/pl.json';
import ptBR from '../../src/localization/pt-BR.json';
import ro from '../../src/localization/ro.json';
import ru from '../../src/localization/ru.json';
import { createTranslator } from '../../src/localization/runtime.js';
import vi from '../../src/localization/vi.json';
import zhCN from '../../src/localization/zh-CN.json';
import zhTW from '../../src/localization/zh-TW.json';

const catalogs: Record<string, Record<string, string>> = {
    da,
    de,
    el,
    fa,
    fr,
    hi,
    it: italian,
    ko,
    nl,
    pl,
    'pt-BR': ptBR,
    ro,
    ru,
    vi,
    'zh-CN': zhCN,
    'zh-TW': zhTW,
};

// The plant numbers a sentence was filled with: its template's {pN} values.
const values = (sentence: string): string[] => {
    for (const template of Object.values(DECK_BUILD_TEMPLATES)) {
        const escaped = template.replace(/[.*+?^$()|[\]\\]/g, '\\$&');
        const pattern = new RegExp('^' + escaped.replace(/\{p\d+\}/g, '(.+)') + '$');
        const match = pattern.exec(sentence);
        if (match) return match.slice(1);
    }
    throw new Error(`No template for: ${sentence}`);
};

describe('deck build text translations', () => {
    it('translates every generated sentence, keeping its plant numbers', () => {
        const sentences = new Set<string>();
        for (const map of maps) {
            for (const variant of ['original', 'recharged'] as Variant[]) {
                for (const deck of availableDecks()) {
                    for (const players of [3, 4, 6]) {
                        const options: GameOptions = { map: map.name as MapName, variant, powerPlantDeck: deck };
                        const text = deckBuildText(map.name, options, players);
                        [...text.standard, ...text.map].forEach((s) => sentences.add(s));
                    }
                }
            }
        }
        for (const [locale, catalog] of Object.entries(catalogs)) {
            const t = createTranslator({ [locale]: catalog }, locale);
            for (const sentence of sentences) {
                const translated = t.translate(sentence);
                expect(translated, `${locale}: ${sentence}`).not.to.equal(sentence);
                for (const value of values(sentence)) {
                    expect(translated, `${locale}: ${sentence}`).to.include(value);
                }
            }
        }
    });
});
