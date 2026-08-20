// The production deploy uploads ONLY dist/powergrid-viewer.umd.min.js and
// dist/powergrid-viewer.css — nothing else from dist/ is served. Any asset emitted
// as a separate file (dist/img/*.svg icons, dist/media/*.mp3 audio) would 404, so
// every static asset must be inlined into the bundles as a data URI.
const INLINE_ASSETS_LIMIT = 10 * 1024 * 1024;

module.exports = {
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
