import './rtl.css';
import { mountLocalization as mount, createTranslator, resolveLocale } from './runtime.js';
export { languages, resolveLocale } from './runtime.js';

const loaders = {
    de: () => import(/* webpackChunkName: "locale-de" */ './de.json'),
    fr: () => import(/* webpackChunkName: "locale-fr" */ './fr.json'),
    pl: () => import(/* webpackChunkName: "locale-pl" */ './pl.json'),
    ro: () => import(/* webpackChunkName: "locale-ro" */ './ro.json'),
    el: () => import(/* webpackChunkName: "locale-el" */ './el.json'),
    hi: () => import(/* webpackChunkName: "locale-hi" */ './hi.json'),
    ru: () => import(/* webpackChunkName: "locale-ru" */ './ru.json'),
    da: () => import(/* webpackChunkName: "locale-da" */ './da.json'),
    'pt-BR': () => import(/* webpackChunkName: "locale-pt-BR" */ './pt-BR.json'),
    ko: () => import(/* webpackChunkName: "locale-ko" */ './ko.json'),
    'zh-TW': () => import(/* webpackChunkName: "locale-zh-TW" */ './zh-TW.json'),
    vi: () => import(/* webpackChunkName: "locale-vi" */ './vi.json'),
    it: () => import(/* webpackChunkName: "locale-it" */ './it.json'),
    nl: () => import(/* webpackChunkName: "locale-nl" */ './nl.json'),
    fa: () => import(/* webpackChunkName: "locale-fa" */ './fa.json'),
};
export const catalogs = { en: {} };
const pending = new Map();
export function loadLocale(value) {
    const locale = resolveLocale(value);
    if (catalogs[locale]) return Promise.resolve(locale);
    if (!pending.has(locale)) {
        pending.set(
            locale,
            loaders[locale]()
                .then((module) => {
                    catalogs[locale] = module.default;
                    translators.delete(locale);
                    return locale;
                })
                .catch((error) => {
                    pending.delete(locale);
                    throw error;
                })
        );
    }
    return pending.get(locale);
}
const translators = new Map();
export function translateText(text, locale = 'en') {
    if (!translators.has(locale)) {
        translators.set(locale, createTranslator(catalogs, locale));
    }
    return translators.get(locale).translate(text);
}
export function mountLocalization(target, locale) {
    const localization = mount(target, catalogs, 'en');
    let revision = 0;
    let ready = Promise.resolve(true);
    function setLocale(value) {
        const attempt = ++revision;
        ready = loadLocale(value)
            .then((loaded) => {
                if (attempt !== revision) return false;
                localization.setLocale(loaded);
                return true;
            })
            .catch((error) => {
                console.warn('Could not load game language', error);
                if (attempt !== revision) return false;
                localization.setLocale('en');
                return true;
            });
        return ready;
    }
    setLocale(locale ?? target.ownerDocument.documentElement.lang ?? 'en');
    return {
        ...localization,
        setLocale,
        get locale() {
            return localization.locale;
        },
        get ready() {
            return ready;
        },
        destroy() {
            revision++;
            localization.destroy();
        },
    };
}
export function localizeTutorial(mountTutorial) {
    return async (target, options) => {
        const localization = mountLocalization(target, options.locale);
        try {
            await localization.ready;
            const dispose = await mountTutorial(target, options);
            localization.refresh();
            return () => {
                localization.destroy();
                dispose?.();
            };
        } catch (error) {
            localization.destroy();
            throw error;
        }
    };
}
