// The production deploy uploads ONLY dist/powergrid-viewer.umd.min.js and
// dist/powergrid-viewer.css — nothing else from dist/ is served. Any asset emitted
// as a separate file (dist/img/*.svg icons, dist/media/*.mp3 audio) would 404, so
// every static asset must be inlined into the bundles as a data URI.
const INLINE_ASSETS_LIMIT = 10 * 1024 * 1024;

const { dirname, join } = require('path');
const protocolDist = dirname(require.resolve('@boardgamers/protocol/viewer'));

module.exports = {
    transpileDependencies: ['@boardgamers/protocol', 'zod'],
    devServer: {
        // For gitpod, it needs to be disabled
        disableHostCheck: true,
        // The dev server sends no cache directives of its own, only a weak ETag,
        // so a browser is free to heuristically cache the bundle and never
        // revalidate. On desktop this is hidden by DevTools' "disable cache";
        // on a phone it shows up as "your fix didn't deploy" after every edit.
        headers: {
            'Cache-Control': 'no-store',
        },
    },
    chainWebpack: (config) => {
        // App and library builds use different Vue import transforms.
        for (const name of ['js', 'ts', 'tsx', 'vue']) {
            const rule = config.module.rule(name);
            if (rule.uses.has('cache-loader')) {
                rule.use('cache-loader').tap((options) => ({
                    ...options,
                    cacheIdentifier: `${options.cacheIdentifier}:${process.env.VUE_CLI_BUILD_TARGET || 'app'}`,
                }));
            }
        }
        // Engine sources have their own tsconfig; every viewer worker must use
        // the Vue config, including its legacy-decorator setting.
        for (const name of ['ts', 'tsx']) {
            config.module
                .rule(name)
                .use('ts-loader')
                .tap((options) => ({
                    ...options,
                    configFile: join(__dirname, 'tsconfig.json'),
                }));
        }
        // Webpack 4 predates package exports; resolve the published ESM entry points.
        config.resolve.alias.set('@boardgamers/protocol/viewer', join(protocolDist, 'viewer.js'));
        config.resolve.alias.set('@boardgamers/protocol/chat/dom$', join(protocolDist, 'chat-dom.js'));
        config.resolve.alias.set('@boardgamers/protocol/chat$', join(protocolDist, 'chat.js'));
        config.resolve.alias.set('@boardgamers/protocol/tutorial/dom$', join(protocolDist, 'tutorial-dom.js'));
        config.resolve.alias.set('@boardgamers/protocol/tutorial$', join(protocolDist, 'tutorial.js'));
        // vue-cli's svg rule uses plain file-loader (always emits files); replace it
        // with url-loader so the icons are inlined. Reuse the url-loader already
        // resolved for the images rule (it is not hoisted to our node_modules).
        const urlLoader = config.module.rule('images').use('url-loader').get('loader');
        config.module.rule('svg').uses.clear();
        config.module.rule('svg').use('url-loader').loader(urlLoader).options({ limit: INLINE_ASSETS_LIMIT });

        // Raise the inline threshold so audio (and any raster images) inline too
        // instead of falling back to file-loader above 4 KiB.
        for (const ruleName of ['images', 'media']) {
            config.module
                .rule(ruleName)
                .use('url-loader')
                .tap((options) => ({ ...options, limit: INLINE_ASSETS_LIMIT }));
        }
    },
};
